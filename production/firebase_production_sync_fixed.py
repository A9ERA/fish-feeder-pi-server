#!/usr/bin/env python3
"""
FIREBASE PRODUCTION SYNC - FIXED VERSION
Arduino → Raspberry Pi → Firebase → Global Web
Supports JSON format from Arduino
"""

import serial
import time
import json
import os
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, db
import threading
import signal
import sys

class ProductionFirebaseSyncFixed:
    def __init__(self):
        # Load environment from config directory
        from dotenv import load_dotenv
        load_dotenv('config/.env')
        
        self.port = os.getenv('SERIAL_PORT', 'COM3')
        self.baud_rate = int(os.getenv('BAUD_RATE', '9600'))
        self.serial_connection = None
        self.firebase_app = None
        self.db_ref = None
        self.running = False
        
        # Production settings
        self.sensor_update_interval = 5  # 5 seconds
        self.relay_status = {'led': False, 'fan': False}
        self.last_sensor_data = {}
        
    def connect_arduino(self):
        """Connect to Arduino"""
        try:
            self.serial_connection = serial.Serial(
                port=self.port,
                baudrate=self.baud_rate,
                timeout=2
            )
            time.sleep(3)  # Arduino reset delay
            print(f"[OK] Arduino connected: {self.port} @ {self.baud_rate}")
            return True
        except Exception as e:
            print(f"[ERROR] Arduino connection failed: {e}")
            return False
    
    def connect_firebase(self):
        """Connect to Firebase"""
        try:
            # Initialize Firebase
            if not firebase_admin._apps:
                cred = credentials.Certificate('config/firebase-key.json')
                firebase_admin.initialize_app(cred, {
                    'databaseURL': 'https://fish-feeder-test-1-default-rtdb.asia-southeast1.firebasedatabase.app/'
                })
            
            # Database reference
            self.db_ref = db.reference('fish-feeder')
            print("[OK] Firebase connected")
            
            # Set system online
            self.set_system_online()
            return True
            
        except Exception as e:
            print(f"[ERROR] Firebase connection failed: {e}")
            print("[TIP] Make sure firebase-key.json exists")
            return False
    
    def set_system_online(self):
        """Set system status as online"""
        try:
            status_data = {
                'relay': self.relay_status,
                'last_update': datetime.now().isoformat(),
                'online': True,
                'response_time_ms': '~100',
                'pi_connected': True,
                'arduino_connected': True
            }
            
            self.db_ref.child('status').set(status_data)
            print("[ONLINE] System set to ONLINE")
            
        except Exception as e:
            print(f"[ERROR] Failed to set online status: {e}")
    
    def read_arduino_sensors(self):
        """Read all sensor data from Arduino - supports JSON format"""
        if not self.serial_connection:
            return None
            
        try:
            # Request sensor data from Arduino
            self.serial_connection.write(b"GET_SENSORS\n")
            self.serial_connection.flush()
            
            # Collect all sensor readings
            sensor_data = {}
            start_time = time.time()
            
            while time.time() - start_time < 3:  # 3 second timeout
                if self.serial_connection.in_waiting > 0:
                    line = self.serial_connection.readline().decode('utf-8', errors='ignore').strip()
                    
                    if line and "[SEND]" in line:
                        try:
                            # Parse JSON format from Arduino
                            json_part = line.split("[SEND] - ", 1)
                            if len(json_part) == 2:
                                # Extract JSON
                                json_str = json_part[1]
                                sensor_json = json.loads(json_str)
                                
                                # Extract data from JSON
                                sensor_name = sensor_json.get('name', '')
                                values = sensor_json.get('value', [])
                                
                                if sensor_name and values:
                                    # Process first value (main sensor reading)
                                    first_value = values[0] if isinstance(values, list) else values
                                    
                                    # Handle NaN values
                                    raw_value = first_value.get('value', 0)
                                    if str(raw_value).lower() == 'nan' or raw_value is None:
                                        continue  # Skip NaN values
                                    
                                    # Convert to Firebase format
                                    current_time = datetime.now().isoformat()
                                    timestamp = int(time.time())
                                    
                                    sensor_data[sensor_name] = {
                                        'values': [{
                                            'type': first_value.get('type', 'unknown'),
                                            'value': float(raw_value) if raw_value != 'nan' else 0.0,
                                            'unit': first_value.get('unit', ''),
                                            'timestamp': current_time
                                        }],
                                        'last_updated': timestamp
                                    }
                                    
                                    print(f"📥 {sensor_name}: {raw_value}{first_value.get('unit', '')}")
                            
                        except (json.JSONDecodeError, ValueError, KeyError) as e:
                            print(f"[WARNING] JSON parse error: {line[:50]}... - {e}")
                            continue
            
            return sensor_data if sensor_data else None
            
        except Exception as e:
            print(f"[ERROR] Arduino read error: {e}")
            return None
    
    def send_sensors_to_firebase(self, sensor_data):
        """Send sensor data to Firebase"""
        try:
            # Update sensors in Firebase
            self.db_ref.child('sensors').update(sensor_data)
            
            # Update last update time
            self.db_ref.child('status/last_update').set(datetime.now().isoformat())
            
            print(f"[DATA] Firebase Update: {len(sensor_data)} sensors @ {datetime.now().strftime('%H:%M:%S')}")
            
            # Detailed sensor feedback - show ALL sensors with organized output
            print("┌── SENSOR DATA SENT TO FIREBASE ──")
            for name, data in sensor_data.items():
                value = data['values'][0]['value']
                unit = data['values'][0]['unit']
                sensor_type = data['values'][0]['type']
                
                # Format output based on sensor type
                if 'TEMP' in name:
                    print(f"│ 🌡️  {name}: {value:.1f}{unit} ({sensor_type})")
                elif 'BATTERY' in name:
                    print(f"│ 🔋 {name}: {value:.1f}{unit} ({sensor_type})")
                elif 'VOLTAGE' in name:
                    print(f"│ ⚡ {name}: {value:.2f}{unit} ({sensor_type})")
                elif 'CURRENT' in name:
                    print(f"│ 🔌 {name}: {value:.3f}{unit} ({sensor_type})")
                elif 'MOISTURE' in name:
                    print(f"│ 💧 {name}: {value:.1f}{unit} ({sensor_type})")
                elif 'HX711' in name:
                    print(f"│ ⚖️  {name}: {value:.1f}{unit} ({sensor_type})")
                else:
                    print(f"│ 📊 {name}: {value}{unit} ({sensor_type})")
            print("└── END SENSOR DATA ──")
            
        except Exception as e:
            print(f"[ERROR] Firebase sensor update failed: {e}")
    
    def check_firebase_commands(self):
        """Check for relay commands from Firebase"""
        try:
            commands = self.db_ref.child('commands').get()
            
            if commands:
                for cmd_id, cmd_data in commands.items():
                    command = cmd_data.get('command')
                    source = cmd_data.get('source', 'unknown')
                    
                    print(f"[CMD] Firebase command: {command} (from {source})")
                    
                    # Execute relay command
                    if self.send_arduino_command(command):
                        # Remove processed command
                        self.db_ref.child('commands').child(cmd_id).delete()
                        print(f"[OK] Command {command} completed and removed")
                    else:
                        print(f"[ERROR] Command {command} failed")
                        
        except Exception as e:
            print(f"[ERROR] Firebase command check failed: {e}")
    
    def send_arduino_command(self, command):
        """Send relay command to Arduino"""
        if not self.serial_connection:
            return False
        
        try:
            # Send command to Arduino
            self.serial_connection.write(f"{command}\n".encode())
            self.serial_connection.flush()
            
            # Wait for response
            time.sleep(0.1)
            
            # Update local relay status
            if command == "R:1":
                self.relay_status = {'led': True, 'fan': False}
            elif command == "R:2":
                self.relay_status = {'led': False, 'fan': True}
            elif command == "R:0":
                self.relay_status = {'led': False, 'fan': False}
            
            # Update Firebase status
            self.db_ref.child('status/relay').set(self.relay_status)
            
            # Enhanced control feedback
            print("┌── CONTROL COMMAND EXECUTED ──")
            print(f"│ 📡 Command: {command}")
            print(f"│ 💡 LED Status: {'🟢 ON' if self.relay_status['led'] else '🔴 OFF'}")
            print(f"│ 💨 FAN Status: {'🟢 ON' if self.relay_status['fan'] else '🔴 OFF'}")
            print(f"│ 🕐 Time: {datetime.now().strftime('%H:%M:%S')}")
            print("└── CONTROL STATUS UPDATED ──")
            return True
            
        except Exception as e:
            print(f"[ERROR] Arduino command failed: {e}")
            return False
    
    def sensor_loop(self):
        """Main sensor reading loop - every 5 seconds"""
        print("[MONITOR] Starting sensor monitoring (5-second intervals)")
        
        while self.running:
            try:
                # Read sensors from Arduino
                sensor_data = self.read_arduino_sensors()
                
                if sensor_data:
                    # Send to Firebase
                    self.send_sensors_to_firebase(sensor_data)
                    self.last_sensor_data = sensor_data
                else:
                    print("[WARNING] No valid sensor data received")
                
                # Wait 5 seconds
                for _ in range(50):  # 5 seconds = 50 * 0.1
                    if not self.running:
                        break
                    time.sleep(0.1)
                
            except Exception as e:
                print(f"[ERROR] Sensor loop error: {e}")
                time.sleep(5)
    
    def command_loop(self):
        """Command checking loop - every 1 second"""
        print("[CONTROL] Starting command monitoring")
        
        while self.running:
            try:
                # Check for Firebase commands
                self.check_firebase_commands()
                
                # Wait 1 second
                for _ in range(10):  # 1 second = 10 * 0.1
                    if not self.running:
                        break
                    time.sleep(0.1)
                
            except Exception as e:
                print(f"[ERROR] Command loop error: {e}")
                time.sleep(1)
    
    def run_production(self):
        """Run production sync with threading"""
        print("[START] STARTING FIXED PRODUCTION FIREBASE SYNC")
        print("=" * 60)
        
        # Connect to systems
        if not self.connect_arduino():
            return False
            
        if not self.connect_firebase():
            return False
        
        print("[OK] All systems connected!")
        print("Sensor updates: Every 5 seconds (JSON format supported)")
        print("Command checks: Every 1 second")
        print("Web access: https://fish-feeder-test-1.web.app")
        print("=" * 60)
        
        self.running = True
        
        # Start threads
        sensor_thread = threading.Thread(target=self.sensor_loop, daemon=True)
        command_thread = threading.Thread(target=self.command_loop, daemon=True)
        
        sensor_thread.start()
        command_thread.start()
        
        try:
            # Keep main thread alive
            while self.running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n[STOP] Shutting down...")
            self.running = False
            
        return True
    
    def cleanup(self):
        """Cleanup connections"""
        self.running = False
        
        try:
            if self.db_ref:
                self.db_ref.child('status/online').set(False)
                self.db_ref.child('status/pi_connected').set(False)
                print("[OFFLINE] System set to OFFLINE")
            
            if self.serial_connection:
                self.serial_connection.close()
                print("[DISCONNECT] Arduino disconnected")
                
        except Exception as e:
            print(f"[WARNING] Cleanup error: {e}")

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print('\n[STOP] Received stop signal')
    sys.exit(0)

def main():
    # Get script directory and change to it
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    print(f"[DIR] Working directory: {script_dir}")
    
    print("FIREBASE PRODUCTION SYNC - FIXED")
    print("=" * 60)
    print("Arduino (JSON) -> Pi -> Firebase -> Global Web")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Supports Arduino JSON format")
    print("=" * 60)
    
    # Handle Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    sync_service = ProductionFirebaseSyncFixed()
    
    try:
        sync_service.run_production()
    except Exception as e:
        print(f"[ERROR] Production error: {e}")
    finally:
        sync_service.cleanup()

if __name__ == "__main__":
    main() 