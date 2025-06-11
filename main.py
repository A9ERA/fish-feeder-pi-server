#!/usr/bin/env python3
"""
🐟 FISH FEEDER Pi CONTROLLER v3.1
=================================
Complete Pi Controller for Arduino-based Fish Feeding System with Web App Integration
+ Real-time WebSocket Support + Advanced Configuration Management + Sensor History Analytics
"""

import sys, json, time, logging, threading, traceback, signal, os, re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path
import uuid

# Core libraries
import serial
import serial.tools.list_ports

# Web framework
from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from flask_socketio import SocketIO, emit, disconnect

# Firebase
import firebase_admin
from firebase_admin import credentials, db

# Camera
import cv2
import threading

# Sensor History Manager
from sensor_history_manager import SensorHistoryManager

# ==============================================================================
# CONFIGURATION
# ==============================================================================

class Config:
    """System Configuration"""
    # Arduino
    ARDUINO_BAUDRATE = 115200
    ARDUINO_TIMEOUT = 2
    ARDUINO_SCAN_PORTS = [f"COM{i}" for i in range(3, 21)]  # Windows
    # ARDUINO_SCAN_PORTS = ["/dev/ttyUSB0", "/dev/ttyACM0", "/dev/ttyUSB1"]  # Linux
    ARDUINO_RECONNECT_INTERVAL = 10
    
    # Web Server
    WEB_HOST = "0.0.0.0"
    WEB_PORT = 5000
    WEB_DEBUG = False
    
    # WebSocket Configuration (NEW)
    WEBSOCKET_ENABLED = True
    WEBSOCKET_PING_TIMEOUT = 60
    WEBSOCKET_PING_INTERVAL = 25
    
    # Firebase
    FIREBASE_CRED_FILE = "serviceAccountKey.json"
    FIREBASE_DATABASE_URL = "https://fish-feeder-test-1-default-rtdb.asia-southeast1.firebasedatabase.app"
    FIREBASE_ROOT_PATH = "fish_feeder"
    
    # Timing
    SENSOR_READ_INTERVAL = 3
    FIREBASE_SYNC_INTERVAL = 5
    STATUS_BROADCAST_INTERVAL = 10
    WEBSOCKET_BROADCAST_INTERVAL = 2  # Real-time updates every 2 seconds
    
    # Camera
    CAMERA_INDEX = 0
    CAMERA_WIDTH = 640
    CAMERA_HEIGHT = 480
    CAMERA_FPS = 30
    
    # Feed Presets (default values)
    FEED_PRESETS = {
        "small": {"amount": 50, "actuator_up": 2, "actuator_down": 2, "auger_duration": 10, "blower_duration": 8},
        "medium": {"amount": 100, "actuator_up": 3, "actuator_down": 2, "auger_duration": 20, "blower_duration": 15},
        "large": {"amount": 200, "actuator_up": 4, "actuator_down": 3, "auger_duration": 40, "blower_duration": 30},
        "xl": {"amount": 1000, "actuator_up": 5, "actuator_down": 4, "auger_duration": 120, "blower_duration": 60}
    }
    
    # Commands
    RELAY_COMMANDS = {
        "led_on": "R:1", "led_off": "R:0", "led_toggle": "R:1",
        "fan_on": "R:2", "fan_off": "R:0", "fan_toggle": "R:2",
        "pump_on": "R:3", "pump_off": "R:0"
    }
    
    # Advanced Configuration (NEW)
    CONFIG_FILE = "config.json"
    AUTO_FEED_ENABLED = False
    AUTO_FEED_SCHEDULE = [
        {"time": "08:00", "preset": "medium", "enabled": True},
        {"time": "14:00", "preset": "small", "enabled": True},
        {"time": "18:00", "preset": "medium", "enabled": True}
    ]
    
    @classmethod
    def load_from_file(cls):
        """Load configuration from file"""
        try:
            if Path(cls.CONFIG_FILE).exists():
                with open(cls.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    
                # Update class attributes from file
                for key, value in config_data.items():
                    if hasattr(cls, key.upper()):
                        setattr(cls, key.upper(), value)
                        
        except Exception as e:
            logging.getLogger(__name__).error(f"Failed to load config: {e}")
    
    @classmethod
    def save_to_file(cls):
        """Save current configuration to file"""
        try:
            config_data = {
                'sensor_read_interval': cls.SENSOR_READ_INTERVAL,
                'firebase_sync_interval': cls.FIREBASE_SYNC_INTERVAL,
                'websocket_broadcast_interval': cls.WEBSOCKET_BROADCAST_INTERVAL,
                'auto_feed_enabled': cls.AUTO_FEED_ENABLED,
                'auto_feed_schedule': cls.AUTO_FEED_SCHEDULE,
                'feed_presets': cls.FEED_PRESETS,
                'camera_settings': {
                    'width': cls.CAMERA_WIDTH,
                    'height': cls.CAMERA_HEIGHT,
                    'fps': cls.CAMERA_FPS
                }
            }
            
            with open(cls.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logging.getLogger(__name__).error(f"Failed to save config: {e}")

# ==============================================================================
# LOGGING SETUP
# ==============================================================================

def setup_logging():
    """Setup logging with daily rotation"""
    # Main logs directory
    Path("logs").mkdir(exist_ok=True)
    
    # Daily sensor logs directory
    today = datetime.now().strftime("%Y-%m-%d")
    daily_log_dir = Path(f"logs/{today}")
    daily_log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("logs/system.log", encoding='utf-8'),
            logging.FileHandler(f"logs/{today}/sensor_log.txt", encoding='utf-8')
        ]
    )
    
    # Reduce noise
    logging.getLogger('firebase_admin').setLevel(logging.WARNING)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    
    return logging.getLogger(__name__)

# ==============================================================================
# FEED HISTORY MANAGER
# ==============================================================================

class FeedHistoryManager:
    """Manage feed history and statistics"""
    
    def __init__(self, logger):
        self.logger = logger
        self.history_file = "logs/feed_history.json"
        self.feed_history = self._load_history()
        
    def _load_history(self):
        """Load feed history from file"""
        try:
            if Path(self.history_file).exists():
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load feed history: {e}")
        return []
    
    def _save_history(self):
        """Save feed history to file"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.feed_history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Failed to save feed history: {e}")
    
    def add_feed_record(self, amount, feed_type, device_timings, video_url=None):
        """Add new feed record"""
        feed_id = f"feed_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        record = {
            "feed_id": feed_id,
            "timestamp": datetime.now().isoformat(),
            "amount": amount,
            "type": feed_type,
            "status": "completed",
            "video_url": video_url or "",
            "duration_seconds": sum(device_timings.values()),
            "device_timings": device_timings
        }
        
        self.feed_history.append(record)
        self._save_history()
        self.logger.info(f"Feed record added: {feed_id}")
        return record
    
    def get_today_statistics(self):
        """Get today's feeding statistics"""
        today = datetime.now().date()
        today_feeds = [
            feed for feed in self.feed_history
            if datetime.fromisoformat(feed['timestamp']).date() == today
        ]
        
        total_amount = sum(feed['amount'] for feed in today_feeds)
        total_feeds = len(today_feeds)
        average_per_feed = total_amount / total_feeds if total_feeds > 0 else 0
        last_feed_time = today_feeds[-1]['timestamp'] if today_feeds else None
        
        return {
            "total_amount_today": total_amount,
            "total_feeds_today": total_feeds,
            "average_per_feed": round(average_per_feed, 1),
            "last_feed_time": last_feed_time,
            "daily_target": 500,  # configurable
            "target_achieved_percentage": round((total_amount / 500) * 100, 1) if total_amount else 0
        }

# ==============================================================================
# ARDUINO MANAGER
# ==============================================================================

class ArduinoManager:
    """Arduino serial communication manager"""
    
    def __init__(self, logger):
        self.logger = logger
        self.serial_conn = None
        self.is_connected = False
        self.last_data = {}
        self.connection_attempts = 0
        self.last_connection_attempt = 0
        self.lock = threading.Lock()
        
    def find_arduino(self):
        """Find Arduino port"""
        # Try Linux/Raspberry Pi ports first
        linux_ports = ["/dev/ttyUSB0", "/dev/ttyACM0", "/dev/ttyUSB1", "/dev/ttyACM1"]
        for port in linux_ports:
            if os.path.exists(port):
                try:
                    with serial.Serial(port, Config.ARDUINO_BAUDRATE, timeout=1) as test_conn:
                        time.sleep(0.5)
                        test_conn.write(b"STATUS\n")
                        time.sleep(0.5)
                        
                        if test_conn.in_waiting > 0:
                            response = test_conn.readline().decode().strip()
                            if response and ("DHT22" in response or "DS18B20" in response or "SEND" in response):
                                self.logger.info(f"✅ Arduino found at {port}")
                                return port
                except:
                    continue
        
        # Fallback to Windows ports
        for port in Config.ARDUINO_SCAN_PORTS:
            try:
                with serial.Serial(port, Config.ARDUINO_BAUDRATE, timeout=1) as test_conn:
                    time.sleep(0.5)
                    test_conn.write(b"STATUS\n")
                    time.sleep(0.5)
                    
                    if test_conn.in_waiting > 0:
                        response = test_conn.readline().decode().strip()
                        if response and ("DHT22" in response or "DS18B20" in response or "SEND" in response):
                            self.logger.info(f"✅ Arduino found at {port}")
                            return port
            except:
                continue
        return None
    
    def connect(self):
        """Connect to Arduino"""
        current_time = time.time()
        
        if current_time - self.last_connection_attempt < Config.ARDUINO_RECONNECT_INTERVAL:
            return False
            
        self.last_connection_attempt = current_time
        self.connection_attempts += 1
        
        self.disconnect()
        
        try:
            port = self.find_arduino()
            if not port:
                self.logger.warning(f"❌ Arduino not found (attempt {self.connection_attempts})")
                return False
            
            self.serial_conn = serial.Serial(
                port=port,
                baudrate=Config.ARDUINO_BAUDRATE,
                timeout=Config.ARDUINO_TIMEOUT,
                write_timeout=2
            )
            
            time.sleep(2)  # Arduino init
            
            # Test communication
            self.serial_conn.write(b"STATUS\n")
            time.sleep(0.5)
            
            if self.serial_conn.in_waiting > 0:
                response = self.serial_conn.readline().decode().strip()
                if response:
                    self.is_connected = True
                    self.connection_attempts = 0
                    self.logger.info(f"✅ Arduino connected at {port}")
                    return True
            
            self.disconnect()
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Arduino connection failed: {e}")
            self.disconnect()
            return False
    
    def disconnect(self):
        """Disconnect Arduino"""
        self.is_connected = False
        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.close()
            except:
                pass
        self.serial_conn = None
    
    def send_command(self, command):
        """Send command to Arduino"""
        if not self.is_connected or not self.serial_conn:
            self.logger.warning(f"⚠️ Arduino not connected, cannot send: {command}")
            return False
        
        try:
            with self.lock:
                self.serial_conn.write(f"{command}\n".encode())
                self.serial_conn.flush()
                self.logger.info(f"📤 Sent to Arduino: {command}")
                return True
        except Exception as e:
            self.logger.error(f"❌ Failed to send command '{command}': {e}")
            self.is_connected = False
            return False
    
    def execute_feed_sequence(self, amount, actuator_up, actuator_down, auger_duration, blower_duration):
        """Execute complete feeding sequence"""
        if not self.is_connected:
            return False, "Arduino not connected"
        
        try:
            self.logger.info(f"🍽️ Starting feed sequence: {amount}g")
            
            # 1. Actuator Up
            self.send_command(f"A:1")  # Actuator up
            time.sleep(actuator_up)
            
            # 2. Auger operation
            self.send_command("G:1")  # Start auger
            time.sleep(auger_duration)
            self.send_command("G:0")  # Stop auger
            
            # 3. Actuator Down  
            self.send_command("A:2")  # Actuator down
            time.sleep(actuator_down)
            
            # 4. Blower operation
            self.send_command("B:1")  # Start blower
            time.sleep(blower_duration)
            self.send_command("B:0")  # Stop blower
            
            self.logger.info("✅ Feed sequence completed")
            return True, "Feed sequence completed successfully"
            
        except Exception as e:
            self.logger.error(f"❌ Feed sequence failed: {e}")
            return False, str(e)
    
    def read_sensors(self):
        """Read sensor data from Arduino"""
        if not self.is_connected or not self.serial_conn:
            return {}

        try:
            with self.lock:
                self.serial_conn.reset_input_buffer()
                self.serial_conn.write(b"S:ALL\n")
                self.serial_conn.flush()

                start_time = time.time()
                sensor_data = {}

                while time.time() - start_time < 3:
                    if self.serial_conn.in_waiting > 0:
                        line = self.serial_conn.readline().decode().strip()

                        if line:
                            parsed = self._parse_sensor_line(line)
                            if parsed:
                                sensor_data.update(parsed)

                    time.sleep(0.1)

                if sensor_data:
                    self.last_data = sensor_data
                    return sensor_data
                else:
                    return self.last_data

        except Exception as e:
            self.logger.error(f"❌ Failed to read sensors: {e}")
            self.is_connected = False
            return self.last_data
    
    def _enhance_battery_data(self, measurements):
        """Enhance battery data with Li-ion 12V 12AH calculations"""
        try:
            # Get basic measurements
            voltage = measurements.get('voltage', {}).get('value', 0)
            current = measurements.get('current', {}).get('value', 0)
            
            if voltage > 0:
                # Calculate Li-ion State of Charge (SOC)
                if voltage >= 12.5:
                    soc = 100.0
                elif voltage >= 12.2:
                    soc = 85.0 + ((voltage - 12.2) / 0.3) * 15.0
                elif voltage >= 11.8:
                    soc = 60.0 + ((voltage - 11.8) / 0.4) * 25.0
                elif voltage >= 11.4:
                    soc = 30.0 + ((voltage - 11.4) / 0.4) * 30.0
                elif voltage >= 10.8:
                    soc = 10.0 + ((voltage - 10.8) / 0.6) * 20.0
                elif voltage >= 8.4:
                    soc = ((voltage - 8.4) / 2.4) * 10.0
                else:
                    soc = 0.0
                
                # Battery health status
                if voltage < 8.4:
                    health_status = "CRITICAL"
                elif voltage < 10.8:
                    health_status = "LOW"
                elif voltage < 11.4:
                    health_status = "FAIR"
                elif voltage < 12.2:
                    health_status = "GOOD"
                elif voltage <= 12.6:
                    health_status = "EXCELLENT"
                else:
                    health_status = "OVERCHARGE"
                
                # Calculate power and efficiency
                power = voltage * current if current > 0 else 0
                
                # Li-ion efficiency based on discharge rate
                if current < 1.0:
                    efficiency = 95.0
                elif current < 5.0:
                    efficiency = 92.0
                elif current < 15.0:
                    efficiency = 88.0
                else:
                    efficiency = 85.0
                
                # Estimated runtime (12AH battery)
                available_capacity = 12.0 * (soc / 100.0)
                runtime = available_capacity / current if current > 0.01 else 999.0
                
                # Add enhanced data
                measurements['soc'] = {'value': round(soc, 1), 'unit': '%', 'timestamp': datetime.now().isoformat()}
                measurements['health_status'] = {'value': health_status, 'unit': '', 'timestamp': datetime.now().isoformat()}
                measurements['power'] = {'value': round(power, 2), 'unit': 'W', 'timestamp': datetime.now().isoformat()}
                measurements['efficiency'] = {'value': round(efficiency, 1), 'unit': '%', 'timestamp': datetime.now().isoformat()}
                measurements['runtime'] = {'value': round(min(runtime, 999), 1), 'unit': 'h', 'timestamp': datetime.now().isoformat()}
                measurements['battery_type'] = {'value': 'Li-ion 12V 12AH', 'unit': '', 'timestamp': datetime.now().isoformat()}
                
                self.logger.debug(f"🔋 Enhanced battery data: {soc:.1f}% SOC, {health_status} health")
                
        except Exception as e:
            self.logger.error(f"❌ Failed to enhance battery data: {e}")
    
    def _parse_sensor_line(self, line):
        """Parse sensor data line"""
        try:
            # New JSON Format: [SEND] - {"name":"SENSOR_NAME","value":[{...}]}
            if line.startswith('[SEND] - {') and line.endswith('}'):
                json_str = line[9:]  # Remove "[SEND] - " prefix
                data = json.loads(json_str)

                sensor_name = data.get('name', '')
                values = data.get('value', [])

                if not sensor_name or not values:
                    return None

                measurements = {}
                for item in values:
                    measurement_type = item.get('type', 'value')
                    value = item.get('value', 0)
                    unit = item.get('unit', '')
                    timestamp = item.get('timestamp', datetime.now().isoformat())

                    # Convert special types
                    if measurement_type == 'charging' and isinstance(value, str):
                        value = value.lower() == 'true'
                    elif measurement_type != 'charging':
                        try:
                            value = float(value)
                        except (ValueError, TypeError):
                            value = 0

                    measurements[measurement_type] = {
                        'value': value,
                        'unit': unit,
                        'timestamp': timestamp
                    }

                # Enhanced battery processing for Li-ion 12V 12AH
                if sensor_name in ['BATTERY_STATUS', 'POWER_MANAGEMENT']:
                    self._enhance_battery_data(measurements)

                return {sensor_name: measurements} if measurements else None
            
            # Legacy Format: "SENSOR_NAME:type=value unit" (keep for compatibility)
            elif ':' in line and '=' in line:
                sensor_name, data_part = line.split(':', 1)
                sensor_name = sensor_name.strip()
                
                measurements = {}
                parts = data_part.strip().split()
                
                i = 0
                while i < len(parts):
                    if '=' in parts[i]:
                        key, value_str = parts[i].split('=', 1)
                        key = key.strip()
                        
                        try:
                            value = float(value_str)
                            unit = parts[i + 1] if i + 1 < len(parts) and '=' not in parts[i + 1] else ""
                            
                            measurements[key] = {
                                'value': value,
                                'unit': unit,
                                'timestamp': datetime.now().isoformat()
                            }
                            
                            i += 2 if unit else 1
                        except (ValueError, TypeError):
                            i += 1
                    else:
                        i += 1
                
                return {sensor_name: measurements} if measurements else None
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Failed to parse line: {line} - {e}")
            return None

# ==============================================================================
# CAMERA MANAGER
# ==============================================================================

class CameraManager:
    """Camera streaming manager"""
    
    def __init__(self, logger):
        self.logger = logger
        self.camera = None
        self.is_active = False
        self.frame = None
        self.lock = threading.Lock()
        self.recording = False
        self.current_video_file = None
        
    def initialize(self):
        """Initialize camera"""
        try:
            self.camera = cv2.VideoCapture(Config.CAMERA_INDEX)
            
            if not self.camera.isOpened():
                self.logger.warning("❌ Camera not found")
                return False
                
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, Config.CAMERA_WIDTH)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, Config.CAMERA_HEIGHT)
            self.camera.set(cv2.CAP_PROP_FPS, Config.CAMERA_FPS)
            
            self.is_active = True
            self.logger.info("✅ Camera initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Camera initialization failed: {e}")
            return False
    
    def start_streaming(self):
        """Start camera streaming in background"""
        if not self.is_active:
            return
            
        def stream_loop():
            while self.is_active:
                try:
                    ret, frame = self.camera.read()
                    if ret:
                        with self.lock:
                            self.frame = frame.copy()
                    time.sleep(1/Config.CAMERA_FPS)
                except:
                    break
        
        thread = threading.Thread(target=stream_loop, daemon=True)
        thread.start()
        self.logger.info("📹 Camera streaming started")
    
    def get_frame(self):
        """Get current frame as JPEG bytes"""
        if not self.is_active or self.frame is None:
            return None
            
        try:
            with self.lock:
                frame_copy = self.frame.copy()
            
            # Convert to JPEG
            ret, buffer = cv2.imencode('.jpg', frame_copy)
            if ret:
                return buffer.tobytes()
                
        except Exception as e:
            self.logger.error(f"❌ Failed to encode frame: {e}")
            
        return None
    
    def take_photo(self):
        """Take a photo and save to file"""
        if not self.is_active or self.frame is None:
            return None
            
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            photo_dir = Path("logs/photos")
            photo_dir.mkdir(exist_ok=True)
            
            photo_path = photo_dir / f"photo_{timestamp}.jpg"
            
            with self.lock:
                cv2.imwrite(str(photo_path), self.frame)
            
            self.logger.info(f"📸 Photo saved: {photo_path}")
            return str(photo_path)
            
        except Exception as e:
            self.logger.error(f"❌ Failed to take photo: {e}")
            return None
    
    def shutdown(self):
        """Shutdown camera"""
        self.is_active = False
        if self.camera:
            self.camera.release()
        self.logger.info("📹 Camera shutdown")

# ==============================================================================
# FIREBASE MANAGER
# ==============================================================================

class FirebaseManager:
    """Firebase Realtime Database manager"""
    
    def __init__(self, logger):
        self.logger = logger
        self.is_connected = False
        self.db_ref = None
        
    def initialize(self):
        """Initialize Firebase"""
        try:
            if not Path(Config.FIREBASE_CRED_FILE).exists():
                self.logger.error(f"❌ Firebase credentials not found: {Config.FIREBASE_CRED_FILE}")
                return False
            
            if not firebase_admin._apps:
                cred = credentials.Certificate(Config.FIREBASE_CRED_FILE)
                firebase_admin.initialize_app(cred, {
                    'databaseURL': Config.FIREBASE_DATABASE_URL
                })
            
            self.db_ref = db.reference(Config.FIREBASE_ROOT_PATH)
            self.is_connected = True
            
            # Test connection
            self.db_ref.child('status/last_startup').set(datetime.now().isoformat())
            
            self.logger.info("✅ Firebase connected")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Firebase initialization failed: {e}")
            return False
    
    def sync_sensor_data(self, sensor_data, arduino_connected):
        """Sync data to Firebase"""
        if not self.is_connected or not self.db_ref:
            return False
        
        try:
            current_time = datetime.now()
            
            firebase_data = {
                'timestamp': current_time.isoformat(),
                'sensors': sensor_data,
                'status': {
                    'online': True,
                    'arduino_connected': arduino_connected,
                    'last_updated': current_time.isoformat(),
                    'sensor_count': len(sensor_data)
                }
            }
            
            self.db_ref.set(firebase_data)
            self.logger.debug(f"📤 Firebase synced: {len(sensor_data)} sensors")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Firebase sync failed: {e}")
            return False
    
    def get_control_commands(self):
        """Get control commands from Firebase"""
        if not self.is_connected or not self.db_ref:
            return {}
        
        try:
            commands = self.db_ref.child('control').get() or {}
            return commands
        except:
            return {}
    
    def clear_control_commands(self):
        """Clear control commands"""
        if not self.is_connected or not self.db_ref:
            return
        
        try:
            self.db_ref.child('control').delete()
        except:
            pass

# ==============================================================================
# WEB API
# ==============================================================================

class ConfigurationManager:
    """Enhanced Configuration Management with Auto-Feed Scheduler"""
    
    def __init__(self, logger):
        self.logger = logger
        self.auto_feed_thread = None
        self.auto_feed_stop_event = threading.Event()
        
    def get_current_config(self):
        """Get current system configuration"""
        return {
            'timing': {
                'sensor_read_interval': Config.SENSOR_READ_INTERVAL,
                'firebase_sync_interval': Config.FIREBASE_SYNC_INTERVAL,
                'websocket_broadcast_interval': Config.WEBSOCKET_BROADCAST_INTERVAL
            },
            'feeding': {
                'auto_feed_enabled': Config.AUTO_FEED_ENABLED,
                'auto_feed_schedule': Config.AUTO_FEED_SCHEDULE,
                'feed_presets': Config.FEED_PRESETS
            },
            'camera': {
                'width': Config.CAMERA_WIDTH,
                'height': Config.CAMERA_HEIGHT,
                'fps': Config.CAMERA_FPS
            },
            'websocket': {
                'enabled': Config.WEBSOCKET_ENABLED,
                'ping_timeout': Config.WEBSOCKET_PING_TIMEOUT,
                'ping_interval': Config.WEBSOCKET_PING_INTERVAL
            }
        }
    
    def update_config(self, new_config):
        """Update configuration dynamically"""
        try:
            # Update timing settings
            if 'timing' in new_config:
                timing = new_config['timing']
                if 'sensor_read_interval' in timing:
                    Config.SENSOR_READ_INTERVAL = max(1, int(timing['sensor_read_interval']))
                if 'firebase_sync_interval' in timing:
                    Config.FIREBASE_SYNC_INTERVAL = max(5, int(timing['firebase_sync_interval']))
                if 'websocket_broadcast_interval' in timing:
                    Config.WEBSOCKET_BROADCAST_INTERVAL = max(1, int(timing['websocket_broadcast_interval']))
            
            # Update feeding settings
            if 'feeding' in new_config:
                feeding = new_config['feeding']
                if 'auto_feed_enabled' in feeding:
                    Config.AUTO_FEED_ENABLED = bool(feeding['auto_feed_enabled'])
                if 'auto_feed_schedule' in feeding:
                    Config.AUTO_FEED_SCHEDULE = feeding['auto_feed_schedule']
                if 'feed_presets' in feeding:
                    Config.FEED_PRESETS.update(feeding['feed_presets'])
            
            # Update camera settings
            if 'camera' in new_config:
                camera = new_config['camera']
                if 'width' in camera:
                    Config.CAMERA_WIDTH = int(camera['width'])
                if 'height' in camera:
                    Config.CAMERA_HEIGHT = int(camera['height'])
                if 'fps' in camera:
                    Config.CAMERA_FPS = int(camera['fps'])
            
            # Save to file
            Config.save_to_file()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update config: {e}")
            return False
    
    def start_auto_feed_scheduler(self, arduino_mgr, feed_history_mgr):
        """Start automatic feeding scheduler"""
        if self.auto_feed_thread and self.auto_feed_thread.is_alive():
            return  # Already running
        
        self.auto_feed_stop_event.clear()
        
        def scheduler_loop():
            self.logger.info("🤖 Auto feed scheduler started")
            
            while not self.auto_feed_stop_event.is_set():
                try:
                    if Config.AUTO_FEED_ENABLED:
                        current_time = datetime.now().strftime("%H:%M")
                        
                        for schedule_item in Config.AUTO_FEED_SCHEDULE:
                            if (schedule_item['enabled'] and 
                                schedule_item['time'] == current_time):
                                
                                preset = schedule_item['preset']
                                
                                if preset in Config.FEED_PRESETS:
                                    preset_data = Config.FEED_PRESETS[preset]
                                    
                                    # Execute feed command
                                    success = arduino_mgr.execute_feed_sequence(
                                        preset_data['amount'],
                                        preset_data['actuator_up'],
                                        preset_data['actuator_down'],
                                        preset_data['auger_duration'],
                                        preset_data['blower_duration']
                                    )
                                    
                                    if success:
                                        # Record feed history
                                        feed_history_mgr.add_feed_record(
                                            preset_data['amount'],
                                            preset,
                                            preset_data
                                        )
                                        
                                        self.logger.info(f"🍽️ Auto feed executed: {preset} at {current_time}")
                                    else:
                                        self.logger.error(f"❌ Auto feed failed: {preset} at {current_time}")
                
                    # Check every minute
                    time.sleep(60)
                    
                except Exception as e:
                    self.logger.error(f"Auto feed scheduler error: {e}")
                    time.sleep(60)
        
        self.auto_feed_thread = threading.Thread(target=scheduler_loop, daemon=True)
        self.auto_feed_thread.start()
    
    def stop_auto_feed_scheduler(self):
        """Stop automatic feeding scheduler"""
        if self.auto_feed_thread:
            self.auto_feed_stop_event.set()
            self.auto_feed_thread.join(timeout=5)
            self.logger.info("🛑 Auto feed scheduler stopped")

class WebAPI:
    """Enhanced Web API with WebSocket support for Fish Feeder Web App"""
    
    def __init__(self, arduino_mgr, firebase_mgr, camera_mgr, feed_history_mgr, config_mgr, sensor_history_mgr, logger):
        self.arduino_mgr = arduino_mgr
        self.firebase_mgr = firebase_mgr
        self.camera_mgr = camera_mgr
        self.feed_history_mgr = feed_history_mgr
        self.sensor_history_mgr = sensor_history_mgr
        self.config_mgr = config_mgr
        self.logger = logger
        
        self.app = Flask(__name__)
        CORS(self.app, origins=[
            "http://localhost:3000",
            "http://localhost:5173", 
            "https://fish-feeder-test-1.web.app",
            "https://fish-feeder-test-1.firebaseapp.com"
        ])
        
        # WebSocket Support (NEW)
        if Config.WEBSOCKET_ENABLED:
            self.socketio = SocketIO(
                self.app, 
                cors_allowed_origins="*",
                ping_timeout=Config.WEBSOCKET_PING_TIMEOUT,
                ping_interval=Config.WEBSOCKET_PING_INTERVAL,
                logger=False,
                engineio_logger=False
            )
            self._setup_websocket_events()
        else:
            self.socketio = None
        
        # Reduce Flask logging
        self.app.logger.setLevel(logging.WARNING)
        
        # Connected clients (for WebSocket)
        self.connected_clients = set()
        
        self._setup_routes()
    
    def _setup_websocket_events(self):
        """Setup WebSocket event handlers"""
        
        @self.socketio.on('connect')
        def handle_connect():
            self.connected_clients.add(request.sid)
            self.logger.info(f"🔌 Client connected: {request.sid} (Total: {len(self.connected_clients)})")
            
            # Send initial data to new client
            emit('sensor_data', self._get_realtime_data())
            emit('system_status', self._get_system_status())
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            self.connected_clients.discard(request.sid)
            self.logger.info(f"🔌 Client disconnected: {request.sid} (Total: {len(self.connected_clients)})")
        
        @self.socketio.on('request_sensor_data')
        def handle_sensor_request():
            """Handle real-time sensor data request"""
            emit('sensor_data', self._get_realtime_data())
        
        @self.socketio.on('request_system_status')
        def handle_status_request():
            """Handle system status request"""
            emit('system_status', self._get_system_status())
        
        @self.socketio.on('feed_command')
        def handle_feed_command(data):
            """Handle real-time feed command via WebSocket"""
            try:
                result = self._execute_feed_command(data)
                emit('feed_result', result)
                
                # Broadcast to all clients
                self.broadcast_to_all('feed_update', {
                    'timestamp': datetime.now().isoformat(),
                    'action': data.get('action', 'unknown'),
                    'status': 'success' if result.get('success') else 'error'
                })
                
            except Exception as e:
                emit('feed_result', {'success': False, 'message': str(e)})
    
    def _get_realtime_data(self):
        """Get current sensor data for real-time updates"""
        try:
            sensor_data = self.arduino_mgr.last_data if self.arduino_mgr.last_data else {}
            
            # Transform to Web App format
            transformed_data = {}
            for sensor_name, measurements in sensor_data.items():
                if isinstance(measurements, dict):
                    sensor_values = {}
                    for measure_type, data in measurements.items():
                        if isinstance(data, dict) and 'value' in data:
                            sensor_values[measure_type] = data['value']
                            if 'unit' in data and measure_type == 'weight':
                                sensor_values['unit'] = data['unit']
                    
                    if sensor_values:
                        transformed_data[sensor_name] = sensor_values
            
            return {
                'timestamp': datetime.now().isoformat(),
                'data': transformed_data,
                'arduino_connected': self.arduino_mgr.is_connected
            }
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get realtime data: {e}")
            return {'error': str(e)}
    
    def _get_system_status(self):
        """Get current system status"""
        return {
            'timestamp': datetime.now().isoformat(),
            'arduino_connected': self.arduino_mgr.is_connected,
            'firebase_connected': self.firebase_mgr.is_connected,
            'camera_active': self.camera_mgr.is_active,
            'websocket_enabled': Config.WEBSOCKET_ENABLED,
            'connected_clients': len(self.connected_clients),
            'auto_feed_enabled': Config.AUTO_FEED_ENABLED,
            'uptime_seconds': time.time() - start_time
        }
    
    def _execute_feed_command(self, data):
        """Execute feed command (used by both HTTP and WebSocket)"""
        try:
            action = data.get('action', '').lower()
            
            if action in Config.FEED_PRESETS:
                preset = Config.FEED_PRESETS[action]
                amount = data.get('amount', preset['amount'])
                actuator_up = data.get('actuator_up', preset['actuator_up'])
                actuator_down = data.get('actuator_down', preset['actuator_down'])
                auger_duration = data.get('auger_duration', data.get('auger_on', preset['auger_duration']))
                blower_duration = data.get('blower_duration', data.get('blower_on', preset['blower_duration']))
            elif action == 'custom':
                amount = data.get('amount', 100)
                actuator_up = data.get('actuator_up', 3)
                actuator_down = data.get('actuator_down', 2)
                auger_duration = data.get('auger_duration', data.get('auger_on', 20))
                blower_duration = data.get('blower_duration', data.get('blower_on', 15))
            else:
                return {'success': False, 'message': 'Invalid action'}
            
            # Execute feed sequence
            success, message = self.arduino_mgr.execute_feed_sequence(
                amount, actuator_up, actuator_down, auger_duration, blower_duration
            )
            
            if success:
                # Record feed history
                device_timings = {
                    'actuator_up': actuator_up,
                    'actuator_down': actuator_down,
                    'auger_duration': auger_duration,
                    'blower_duration': blower_duration
                }
                
                feed_record = self.feed_history_mgr.add_feed_record(
                    amount, 'manual', device_timings
                )
                
                return {
                    'success': True,
                    'message': 'Feed command executed successfully',
                    'feed_record': feed_record,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {'success': False, 'message': message}
                
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def broadcast_to_all(self, event, data):
        """Broadcast data to all connected WebSocket clients"""
        if self.socketio and self.connected_clients:
            self.socketio.emit(event, data)
    
    def broadcast_sensor_update(self):
        """Broadcast sensor updates to all clients"""
        if self.socketio and self.connected_clients:
            realtime_data = self._get_realtime_data()
            self.socketio.emit('sensor_data', realtime_data)
    
    def broadcast_system_status(self):
        """Broadcast system status to all clients"""
        if self.socketio and self.connected_clients:
            status = self._get_system_status()
            self.socketio.emit('system_status', status)
    
    def _setup_routes(self):
        """Setup API routes"""
        
        @self.app.route('/api/health', methods=['GET'])
        def health_check():
            """Health check endpoint for Web App"""
            available_sensors = list(self.arduino_mgr.last_data.keys()) if self.arduino_mgr.last_data else []
            
            return jsonify({
                'status': 'ok',
                'serial_connected': self.arduino_mgr.is_connected,
                'firebase_connected': self.firebase_mgr.is_connected,
                'timestamp': datetime.now().isoformat(),
                'server_info': {
                    'version': '3.0.0',
                    'uptime_seconds': time.time() - start_time
                },
                'sensors_available': available_sensors
            })
        
        @self.app.route('/api/sensors', methods=['GET'])
        def get_all_sensors():
            """Get all sensor data in Web App format"""
            try:
                if self.arduino_mgr.is_connected:
                    sensor_data = self.arduino_mgr.read_sensors()
                else:
                    sensor_data = self.arduino_mgr.last_data
                
                # Transform sensor data to Web App format (SIMPLIFIED)
                transformed_data = {}
                current_time = datetime.now().isoformat()
                
                for sensor_name, measurements in sensor_data.items():
                    if isinstance(measurements, dict):
                        # Web App expected format - flatten the structure
                        sensor_values = {}
                        
                        for measure_type, data in measurements.items():
                            if isinstance(data, dict) and 'value' in data:
                                sensor_values[measure_type] = data['value']
                                # Add unit if available
                                if 'unit' in data and measure_type == 'weight':
                                    sensor_values['unit'] = data['unit']
                        
                        if sensor_values:
                            transformed_data[sensor_name] = sensor_values
                
                return jsonify({
                    'timestamp': current_time,
                    **transformed_data,  # Flatten structure for Web App compatibility
                    'arduino_connected': self.arduino_mgr.is_connected
                })
                
            except Exception as e:
                self.logger.error(f"❌ Failed to get sensors: {e}")
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
        @self.app.route('/api/sensors/<sensor_name>', methods=['GET'])
        def get_sensor_data(sensor_name):
            """Get specific sensor data (Web App format)"""
            try:
                sensor_data = self.arduino_mgr.last_data.get(sensor_name, {})
                
                if not sensor_data:
                    return jsonify({'status': 'error', 'message': 'Sensor not found'}), 404
                
                values = []
                for measure_type, data in sensor_data.items():
                    if isinstance(data, dict) and 'value' in data:
                        values.append({
                            'type': measure_type,
                            'value': data['value'],
                            'unit': data.get('unit', ''),
                            'timestamp': data.get('timestamp', datetime.now().isoformat())
                        })
                
                return jsonify({
                    'sensor_name': sensor_name,
                    'values': values
                })
                
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
        @self.app.route('/api/feed', methods=['POST'])
        def feed_control():
            """Enhanced feed control for Web App"""
            try:
                data = request.get_json() or {}
                action = data.get('action', '').lower()
                
                # Get timing parameters - Handle both Web App and Pi Server naming
                if action in Config.FEED_PRESETS:
                    preset = Config.FEED_PRESETS[action]
                    amount = data.get('amount', preset['amount'])
                    actuator_up = data.get('actuator_up', preset['actuator_up'])
                    actuator_down = data.get('actuator_down', preset['actuator_down'])
                    # Handle both auger_on (Web App) and auger_duration (Pi Server)
                    auger_duration = data.get('auger_duration', data.get('auger_on', preset['auger_duration']))
                    # Handle both blower_on (Web App) and blower_duration (Pi Server)
                    blower_duration = data.get('blower_duration', data.get('blower_on', preset['blower_duration']))
                elif action == 'custom':
                    amount = data.get('amount', 100)
                    actuator_up = data.get('actuator_up', 3)
                    actuator_down = data.get('actuator_down', 2)
                    # Handle both naming conventions
                    auger_duration = data.get('auger_duration', data.get('auger_on', 20))
                    blower_duration = data.get('blower_duration', data.get('blower_on', 15))
                else:
                    return jsonify({'status': 'error', 'message': 'Invalid action'}), 400
                
                # Generate feed ID
                feed_id = f"feed_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                estimated_duration = actuator_up + auger_duration + actuator_down + blower_duration
                
                # Take photo before feeding
                photo_url = self.camera_mgr.take_photo() if self.camera_mgr.is_active else None
                
                # Execute feed sequence
                success, message = self.arduino_mgr.execute_feed_sequence(
                    amount, actuator_up, actuator_down, auger_duration, blower_duration
                )
                
                if success:
                    # Record feed history
                    device_timings = {
                        'actuator_up': actuator_up,
                        'actuator_down': actuator_down,
                        'auger_duration': auger_duration,
                        'blower_duration': blower_duration
                    }
                    
                    self.feed_history_mgr.add_feed_record(
                        amount, 'manual', device_timings, photo_url
                    )
                    
                    return jsonify({
                        'success': True,
                        'message': 'Feed command executed successfully',
                        'feed_id': feed_id,
                        'estimated_duration': estimated_duration,
                        'timestamp': datetime.now().isoformat(),
                        'photo_url': photo_url or ''
                    })
                else:
                    return jsonify({
                        'success': False,
                        'message': message,
                        'feed_id': feed_id,
                        'timestamp': datetime.now().isoformat()
                    }), 500
                    
            except Exception as e:
                self.logger.error(f"❌ Feed control error: {e}")
                return jsonify({'success': False, 'message': str(e)}), 500
        
        @self.app.route('/api/feed/history', methods=['GET'])
        def get_feed_history():
            """Get feed history"""
            try:
                return jsonify({
                    'data': self.feed_history_mgr.feed_history[-50:]  # Last 50 records
                })
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
        @self.app.route('/api/feed/statistics', methods=['GET'])
        def get_feed_statistics():
            """Get feeding statistics"""
            try:
                stats = self.feed_history_mgr.get_today_statistics()
                return jsonify(stats)
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
        @self.app.route('/api/control/relay/<device>', methods=['POST'])
        def control_relay(device):
            """Control relay devices"""
            try:
                data = request.get_json() or {}
                action = data.get('action', '').lower()
                
                if device in ['led', 'fan', 'pump']:
                    command_key = f"{device}_{action}"
                    if command_key in Config.RELAY_COMMANDS:
                        command = Config.RELAY_COMMANDS[command_key]
                        success = self.arduino_mgr.send_command(command)
                        
                        return jsonify({
                            'status': 'success' if success else 'error',
                            'device': device,
                            'action': action,
                            'command': command
                        })
                
                return jsonify({'status': 'error', 'message': 'Invalid device or action'}), 400
                
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
        @self.app.route('/api/control/direct', methods=['POST'])
        def direct_control():
            """Direct Arduino command control"""
            try:
                data = request.get_json() or {}
                command = data.get('command', '').strip()
                
                if not command:
                    return jsonify({'status': 'error', 'message': 'Command is required'}), 400
                
                success = self.arduino_mgr.send_command(command)
                return jsonify({
                    'status': 'success' if success else 'error',
                    'command': command,
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
        @self.app.route('/api/camera/stream', methods=['GET'])
        def camera_stream():
            """Live camera stream"""
            def generate():
                while True:
                    frame = self.camera_mgr.get_frame()
                    if frame:
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                    time.sleep(1/30)  # 30 FPS
            
            return Response(generate(), 
                          mimetype='multipart/x-mixed-replace; boundary=frame')
        
        @self.app.route('/api/camera/status', methods=['GET'])
        def camera_status():
            """Camera status"""
            return jsonify({
                'status': 'success',
                'camera_active': self.camera_mgr.is_active,
                'timestamp': datetime.now().isoformat()
            })
        
        @self.app.route('/api/camera/photo', methods=['POST'])
        def take_photo():
            """Take a photo"""
            try:
                photo_path = self.camera_mgr.take_photo()
                if photo_path:
                    # In production, upload to Google Drive or cloud storage
                    photo_url = f"/photos/{Path(photo_path).name}"
                    
                    return jsonify({
                        'success': True,
                        'photo_url': photo_url,
                        'timestamp': datetime.now().isoformat()
                    })
                else:
                    return jsonify({
                        'success': False,
                        'message': 'Failed to take photo'
                    }), 500
                    
            except Exception as e:
                return jsonify({'success': False, 'message': str(e)}), 500
        
        # Additional Web App Compatible Endpoints
        @self.app.route('/api/control/blower', methods=['POST'])
        def control_blower():
            """Blower control endpoint for Web App compatibility"""
            try:
                data = request.get_json() or {}
                action = data.get('action', '').lower()
                value = data.get('value', 1)
                
                if action == 'on':
                    command = f"B:{value}"
                elif action == 'off':
                    command = "B:0"
                else:
                    return jsonify({'status': 'error', 'message': 'Invalid action'}), 400
                
                success = self.arduino_mgr.send_command(command)
                return jsonify({
                    'status': 'success' if success else 'error',
                    'action': action,
                    'command': command,
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
        @self.app.route('/api/control/actuator', methods=['POST'])
        def control_actuator():
            """Actuator control endpoint for Web App compatibility"""
            try:
                data = request.get_json() or {}
                action = data.get('action', '').lower()
                duration = data.get('duration', 3.0)
                
                if action == 'up':
                    command = f"U:{duration}"
                elif action == 'down':
                    command = f"D:{duration}"
                else:
                    return jsonify({'status': 'error', 'message': 'Invalid action'}), 400
                
                success = self.arduino_mgr.send_command(command)
                return jsonify({
                    'status': 'success' if success else 'error',
                    'action': action,
                    'command': command,
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
        @self.app.route('/api/control/weight/calibrate', methods=['POST'])
        def calibrate_weight():
            """HX711 Weight calibration endpoint"""
            try:
                data = request.get_json() or {}
                known_weight = data.get('known_weight', 1000)  # grams
                
                # First set calibration mode
                mode_success = self.arduino_mgr.send_command("HX:CALIBRATION")
                
                if mode_success:
                    # Send calibration weight (convert grams to kg for Arduino)
                    weight_kg = known_weight / 1000.0
                    command = f"CAL:WEIGHT:{weight_kg:.3f}"
                    cal_success = self.arduino_mgr.send_command(command)
                    
                    if cal_success:
                        # Switch back to auto mode
                        auto_success = self.arduino_mgr.send_command("HX:AUTO")
                        
                        return jsonify({
                            'status': 'success',
                            'message': f'HX711 calibration completed with {weight_kg:.3f} kg',
                            'known_weight_grams': known_weight,
                            'known_weight_kg': weight_kg,
                            'auto_mode_restored': auto_success,
                            'timestamp': datetime.now().isoformat()
                        })
                    else:
                        return jsonify({
                            'status': 'error',
                            'message': 'Failed to send calibration weight',
                            'timestamp': datetime.now().isoformat()
                        }), 500
                else:
                    return jsonify({
                        'status': 'error',
                        'message': 'Failed to enter calibration mode',
                        'timestamp': datetime.now().isoformat()
                    }), 500
                    
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
        @self.app.route('/api/control/weight/tare', methods=['POST'])
        def tare_weight():
            """Weight tare (zero) endpoint"""
            try:
                success = self.arduino_mgr.send_command("CAL:TARE")
                return jsonify({
                    'status': 'success' if success else 'error',
                    'message': f'Tare {"completed" if success else "failed"}',
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
        @self.app.route('/api/control/weight/reset', methods=['POST'])
        def reset_weight_calibration():
            """Reset weight calibration data from EEPROM"""
            try:
                success = self.arduino_mgr.send_command("CAL:RESET")
                return jsonify({
                    'status': 'success' if success else 'error',
                    'message': f'Calibration reset {"completed" if success else "failed"}',
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
        @self.app.route('/api/control/config', methods=['GET', 'POST'])
        def control_config():
            """Enhanced configuration endpoint with real-time updates"""
            try:
                if request.method == 'GET':
                    # Return comprehensive configuration
                    config = self.config_mgr.get_current_config()
                    config['system_status'] = self._get_system_status()
                    return jsonify(config)
                
                elif request.method == 'POST':
                    # Update configuration dynamically
                    data = request.get_json() or {}
                    
                    success = self.config_mgr.update_config(data)
                    
                    if success:
                        # Broadcast config update to WebSocket clients
                        self.broadcast_to_all('config_updated', {
                            'timestamp': datetime.now().isoformat(),
                            'new_config': self.config_mgr.get_current_config()
                        })
                        
                        return jsonify({
                            'status': 'success',
                            'message': 'Configuration updated successfully',
                            'timestamp': datetime.now().isoformat()
                        })
                    else:
                        return jsonify({
                            'status': 'error',
                            'message': 'Failed to update configuration'
                        }), 500
                    
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
        # WebSocket Status Endpoint (NEW)
        @self.app.route('/api/websocket/status', methods=['GET'])
        def websocket_status():
            """Get WebSocket connection status"""
            return jsonify({
                'websocket_enabled': Config.WEBSOCKET_ENABLED,
                'connected_clients': len(self.connected_clients),
                'ping_timeout': Config.WEBSOCKET_PING_TIMEOUT,
                'ping_interval': Config.WEBSOCKET_PING_INTERVAL,
                'broadcast_interval': Config.WEBSOCKET_BROADCAST_INTERVAL,
                'timestamp': datetime.now().isoformat()
            })
        
        # Auto Feed Control Endpoints (NEW)
        @self.app.route('/api/auto-feed/start', methods=['POST'])
        def start_auto_feed():
            """Start automatic feeding scheduler"""
            try:
                Config.AUTO_FEED_ENABLED = True
                Config.save_to_file()
                
                self.config_mgr.start_auto_feed_scheduler(
                    self.arduino_mgr, self.feed_history_mgr
                )
                
                # Broadcast to WebSocket clients
                self.broadcast_to_all('auto_feed_status', {
                    'enabled': True,
                    'schedule': Config.AUTO_FEED_SCHEDULE,
                    'timestamp': datetime.now().isoformat()
                })
                
                return jsonify({
                    'status': 'success',
                    'message': 'Auto feed scheduler started',
                    'schedule': Config.AUTO_FEED_SCHEDULE
                })
                
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
        @self.app.route('/api/auto-feed/stop', methods=['POST'])
        def stop_auto_feed():
            """Stop automatic feeding scheduler"""
            try:
                Config.AUTO_FEED_ENABLED = False
                Config.save_to_file()
                
                self.config_mgr.stop_auto_feed_scheduler()
                
                # Broadcast to WebSocket clients
                self.broadcast_to_all('auto_feed_status', {
                    'enabled': False,
                    'timestamp': datetime.now().isoformat()
                })
                
                return jsonify({
                    'status': 'success',
                    'message': 'Auto feed scheduler stopped'
                })
                
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
        @self.app.route('/api/auto-feed/schedule', methods=['GET', 'POST'])
        def auto_feed_schedule():
            """Get or update auto feed schedule"""
            try:
                if request.method == 'GET':
                    return jsonify({
                        'enabled': Config.AUTO_FEED_ENABLED,
                        'schedule': Config.AUTO_FEED_SCHEDULE
                    })
                
                elif request.method == 'POST':
                    data = request.get_json() or {}
                    
                    if 'schedule' in data:
                        Config.AUTO_FEED_SCHEDULE = data['schedule']
                        Config.save_to_file()
                        
                        # Broadcast update
                        self.broadcast_to_all('auto_feed_schedule_updated', {
                            'schedule': Config.AUTO_FEED_SCHEDULE,
                            'timestamp': datetime.now().isoformat()
                        })
                        
                        return jsonify({
                            'status': 'success',
                            'message': 'Auto feed schedule updated',
                            'schedule': Config.AUTO_FEED_SCHEDULE
                        })
                    
                    return jsonify({'status': 'error', 'message': 'No schedule provided'}), 400
                    
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
        # ==============================================================================
        # SENSOR HISTORY & ANALYTICS API ENDPOINTS
        # ==============================================================================
        
        @self.app.route('/api/sensors/history', methods=['GET'])
        def get_sensor_history():
            """Get historical sensor data for charts"""
            try:
                # Get query parameters
                start_date = request.args.get('start_date')
                end_date = request.args.get('end_date')
                sensors = request.args.getlist('sensors')  # Multiple sensors
                resolution = request.args.get('resolution', 'raw')  # raw, hourly, daily, monthly
                limit = int(request.args.get('limit', 200))  # Performance limit
                
                # Default to last 7 days if no dates provided
                if not start_date or not end_date:
                    end_date_obj = datetime.now()
                    start_date_obj = end_date_obj - timedelta(days=7)
                    start_date = start_date_obj.strftime('%Y-%m-%d')
                    end_date = end_date_obj.strftime('%Y-%m-%d')
                
                # Get historical data
                data = self.sensor_history_mgr.get_historical_data(
                    start_date, end_date, sensors, resolution
                )
                
                # Limit data for performance
                if len(data) > limit:
                    # Sample data evenly
                    step = len(data) // limit
                    data = data[::step][:limit]
                
                return jsonify({
                    'status': 'success',
                    'data': data,
                    'metadata': {
                        'start_date': start_date,
                        'end_date': end_date,
                        'sensors': sensors,
                        'resolution': resolution,
                        'total_records': len(data),
                        'limit_applied': len(data) >= limit
                    }
                })
                
            except Exception as e:
                self.logger.error(f"❌ Sensor history error: {e}")
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
        @self.app.route('/api/sensors/live', methods=['GET'])
        def get_live_sensor_data():
            """Get recent live sensor data for real-time charts"""
            try:
                limit = int(request.args.get('limit', 100))
                
                # Get live data from memory buffer
                live_data = self.sensor_history_mgr.get_live_data(limit)
                
                return jsonify({
                    'status': 'success',
                    'data': live_data,
                    'metadata': {
                        'total_records': len(live_data),
                        'real_time': True,
                        'update_interval': Config.SENSOR_READ_INTERVAL
                    }
                })
                
            except Exception as e:
                self.logger.error(f"❌ Live sensor data error: {e}")
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
        @self.app.route('/api/analytics/energy', methods=['GET'])
        def get_energy_analytics():
            """Get comprehensive energy analytics and recommendations"""
            try:
                days = int(request.args.get('days', 7))  # Default 7 days
                
                # Get energy analytics
                analytics = self.sensor_history_mgr.get_energy_analytics(days)
                
                return jsonify({
                    'status': 'success',
                    'analytics': analytics,
                    'generated_at': datetime.now().isoformat()
                })
                
            except Exception as e:
                self.logger.error(f"❌ Energy analytics error: {e}")
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
        @self.app.route('/api/sensors/summary', methods=['GET'])
        def get_sensor_summary():
            """Get summary of all sensor types and latest values"""
            try:
                summary = self.sensor_history_mgr.get_sensor_summary()
                
                return jsonify({
                    'status': 'success',
                    'summary': summary
                })
                
            except Exception as e:
                self.logger.error(f"❌ Sensor summary error: {e}")
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
        @self.app.route('/api/storage/info', methods=['GET'])
        def get_storage_info():
            """Get NoSQL storage usage information"""
            try:
                storage_info = self.sensor_history_mgr.get_storage_info()
                
                return jsonify({
                    'status': 'success',
                    'storage': storage_info
                })
                
            except Exception as e:
                self.logger.error(f"❌ Storage info error: {e}")
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
        @self.app.route('/api/sensors/export', methods=['POST'])
        def export_sensor_data():
            """Export historical sensor data"""
            try:
                data = request.get_json() or {}
                start_date = data.get('start_date')
                end_date = data.get('end_date')
                format_type = data.get('format', 'json')  # json or csv
                
                if not start_date or not end_date:
                    return jsonify({'status': 'error', 'message': 'start_date and end_date required'}), 400
                
                # Export data
                export_file = self.sensor_history_mgr.export_data(start_date, end_date, format_type)
                
                if export_file:
                    return jsonify({
                        'status': 'success',
                        'message': 'Data exported successfully',
                        'file_path': export_file
                    })
                else:
                    return jsonify({'status': 'error', 'message': 'Export failed'}), 500
                    
            except Exception as e:
                self.logger.error(f"❌ Export error: {e}")
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
        @self.app.route('/api/storage/cleanup', methods=['POST'])
        def cleanup_old_data():
            """Clean up old sensor data based on retention policies"""
            try:
                # Run cleanup
                self.sensor_history_mgr.cleanup_old_data()
                
                # Get updated storage info
                storage_info = self.sensor_history_mgr.get_storage_info()
                
                return jsonify({
                    'status': 'success',
                    'message': 'Data cleanup completed',
                    'storage': storage_info
                })
                
            except Exception as e:
                self.logger.error(f"❌ Cleanup error: {e}")
                return jsonify({'status': 'error', 'message': str(e)}), 500
    
    def run(self):
        """Start web server with WebSocket support"""
        self.logger.info(f"🌐 Starting enhanced web server at http://{Config.WEB_HOST}:{Config.WEB_PORT}")
        
        if self.socketio:
            self.logger.info(f"🔌 WebSocket enabled - Real-time updates active")
            # Start WebSocket server
            self.socketio.run(
                self.app,
                host=Config.WEB_HOST,
                port=Config.WEB_PORT,
                debug=Config.WEB_DEBUG,
                use_reloader=False,
                allow_unsafe_werkzeug=True
            )
        else:
            self.logger.info(f"📡 Standard HTTP server only")
            # Start regular Flask server
            self.app.run(
                host=Config.WEB_HOST,
                port=Config.WEB_PORT,
                debug=Config.WEB_DEBUG,
                threaded=True,
                use_reloader=False
            )

# ==============================================================================
# MAIN CONTROLLER
# ==============================================================================

class FishFeederController:
    """Main system controller with enhanced real-time features"""
    
    def __init__(self):
        self.logger = setup_logging()
        self.running = True
        
        # Load configuration from file
        Config.load_from_file()
        
        # Initialize managers
        self.arduino_mgr = ArduinoManager(self.logger)
        self.firebase_mgr = FirebaseManager(self.logger)
        self.camera_mgr = CameraManager(self.logger)
        self.feed_history_mgr = FeedHistoryManager(self.logger)
        self.config_mgr = ConfigurationManager(self.logger)  # NEW
        self.sensor_history_mgr = SensorHistoryManager(self.logger)  # NEW - NoSQL Data Storage
        self.web_api = WebAPI(
            self.arduino_mgr, self.firebase_mgr, self.camera_mgr, 
            self.feed_history_mgr, self.config_mgr, self.sensor_history_mgr, self.logger  # Updated
        )
        
        # Timing
        self.last_sensor_read = 0
        self.last_firebase_sync = 0
        self.last_status_broadcast = 0
        self.last_websocket_broadcast = 0  # NEW
        
        # Signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"🛑 Received signal {signum}, shutting down...")
        self.running = False
    
    def initialize(self):
        """Initialize system"""
        self.logger.info("🚀 Initializing Fish Feeder Controller v3.1...")
        
        # Initialize Firebase (optional)
        if not self.firebase_mgr.initialize():
            self.logger.warning("⚠️ Firebase failed, continuing in offline mode")
        
        # Initialize Camera (optional)
        if self.camera_mgr.initialize():
            self.camera_mgr.start_streaming()
        else:
            self.logger.warning("⚠️ Camera failed, continuing without camera")
        
        # Try Arduino connection (will retry automatically)
        if not self.arduino_mgr.connect():
            self.logger.warning("⚠️ Arduino not connected, will retry automatically")
        
        # Start auto feed scheduler if enabled
        if Config.AUTO_FEED_ENABLED:
            self.config_mgr.start_auto_feed_scheduler(self.arduino_mgr, self.feed_history_mgr)
        
        self.logger.info("✅ System initialization completed")
        return True
    
    def start_background_tasks(self):
        """Start background tasks"""
        
        def sensor_loop():
            while self.running:
                try:
                    current_time = time.time()
                    
                    # Auto-reconnect Arduino
                    if not self.arduino_mgr.is_connected:
                        if current_time - self.last_sensor_read > Config.ARDUINO_RECONNECT_INTERVAL:
                            self.arduino_mgr.connect()
                    
                    # Read sensors
                    if (self.arduino_mgr.is_connected and 
                        current_time - self.last_sensor_read > Config.SENSOR_READ_INTERVAL):
                        
                        sensor_data = self.arduino_mgr.read_sensors()
                        if sensor_data:
                            self.last_sensor_read = current_time
                            
                            # Log sensor data to daily file
                            self._log_sensor_data(sensor_data)
                            
                            # Save to NoSQL sensor history
                            self.sensor_history_mgr.save_sensor_data(sensor_data)
                    
                    # Firebase sync (if connected)
                    if (self.firebase_mgr.is_connected and 
                        current_time - self.last_firebase_sync > Config.FIREBASE_SYNC_INTERVAL):
                        
                        self.firebase_mgr.sync_sensor_data(
                            self.arduino_mgr.last_data,
                            self.arduino_mgr.is_connected
                        )
                        self.last_firebase_sync = current_time
                    
                    # Process Firebase commands (if connected)
                    if self.firebase_mgr.is_connected:
                        commands = self.firebase_mgr.get_control_commands()
                        if commands:
                            self._process_firebase_commands(commands)
                            self.firebase_mgr.clear_control_commands()
                    
                    # Status broadcast
                    if current_time - self.last_status_broadcast > Config.STATUS_BROADCAST_INTERVAL:
                        self._broadcast_status()
                        self.last_status_broadcast = current_time
                    
                    # WebSocket broadcast (NEW)
                    if (Config.WEBSOCKET_ENABLED and 
                        current_time - self.last_websocket_broadcast > Config.WEBSOCKET_BROADCAST_INTERVAL):
                        self._broadcast_websocket_updates()
                        self.last_websocket_broadcast = current_time
                    
                    time.sleep(1)
                    
                except Exception as e:
                    self.logger.error(f"❌ Background task error: {e}")
                    time.sleep(5)
        
        # Start background thread
        bg_thread = threading.Thread(target=sensor_loop, daemon=True)
        bg_thread.start()
        self.logger.info("🔄 Background tasks started")
    
    def _log_sensor_data(self, sensor_data):
        """Log sensor data to daily file"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            log_file = Path(f"logs/{today}/sensor_log.txt")
            
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'sensors': sensor_data,
                'arduino_connected': self.arduino_mgr.is_connected
            }
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
                
        except Exception as e:
            self.logger.error(f"❌ Failed to log sensor data: {e}")
    
    def _process_firebase_commands(self, commands):
        """Process Firebase commands"""
        for device, action in commands.items():
            try:
                if device in ['led', 'fan', 'pump']:
                    command_key = f"{device}_{action}"
                    if command_key in Config.RELAY_COMMANDS:
                        command = Config.RELAY_COMMANDS[command_key]
                        self.arduino_mgr.send_command(command)
                        self.logger.info(f"🎮 Firebase command: {device} {action}")
                
                elif device == 'feed' and action in Config.FEED_PRESETS:
                    preset = Config.FEED_PRESETS[action]
                    self.arduino_mgr.execute_feed_sequence(
                        preset['amount'], preset['actuator_up'], preset['actuator_down'],
                        preset['auger_duration'], preset['blower_duration']
                    )
                    self.logger.info(f"🍽️ Firebase feed: {action}")
                
                elif device == 'direct_command':
                    self.arduino_mgr.send_command(str(action))
                    self.logger.info(f"📤 Firebase direct: {action}")
                    
            except Exception as e:
                self.logger.error(f"❌ Firebase command error: {e}")
    
    def _broadcast_status(self):
        """Broadcast system status"""
        self.logger.info(f"📊 Status: Arduino={self.arduino_mgr.is_connected}, "
                        f"Firebase={self.firebase_mgr.is_connected}, "
                        f"Camera={self.camera_mgr.is_active}, "
                        f"Sensors={len(self.arduino_mgr.last_data)}")
    
    def _broadcast_websocket_updates(self):
        """Broadcast WebSocket updates"""
        self.logger.info("📡 Broadcasting WebSocket updates")
        self.web_api.broadcast_sensor_update()
        self.web_api.broadcast_system_status()
    
    def run(self):
        """Run main system"""
        try:
            if not self.initialize():
                return False
            
            self.start_background_tasks()
            self.web_api.run()
            
        except KeyboardInterrupt:
            self.logger.info("🛑 Shutdown requested")
        except Exception as e:
            self.logger.error(f"❌ System error: {e}")
            traceback.print_exc()
        finally:
            self.shutdown()
        
        return True
    
    def shutdown(self):
        """Graceful shutdown with WebSocket cleanup"""
        self.logger.info("🛑 Shutting down Fish Feeder Controller...")
        
        try:
            # Stop auto feed scheduler
            if hasattr(self.config_mgr, 'stop_auto_feed_scheduler'):
                self.config_mgr.stop_auto_feed_scheduler()
            
            # Disconnect WebSocket clients
            if hasattr(self.web_api, 'socketio') and self.web_api.socketio:
                self.web_api.socketio.emit('system_shutdown', {
                    'message': 'Server is shutting down',
                    'timestamp': datetime.now().isoformat()
                })
                time.sleep(1)  # Give time for message to send
            
            # Disconnect hardware
            if self.arduino_mgr:
                self.arduino_mgr.disconnect()
            
            # Shutdown camera
            if self.camera_mgr:
                self.camera_mgr.shutdown()
            
            # Save final configuration
            Config.save_to_file()
            
            self.logger.info("✅ Graceful shutdown completed")
            
        except Exception as e:
            self.logger.error(f"❌ Error during shutdown: {e}")
        
        finally:
            self.running = False

# ==============================================================================
# ENTRY POINT
# ==============================================================================

start_time = time.time()

def main():
    """Main function"""
    global start_time
    start_time = time.time()
    
    print("="*60)
    print("🐟 FISH FEEDER Pi CONTROLLER v3.1")
    print("="*60)
    print("✨ Real-time WebSocket Support")
    print("🔧 Advanced Configuration Management") 
    print("🤖 Automatic Feed Scheduling")
    print("📱 Web App Integration Ready")
    print("="*60)
    
    controller = FishFeederController()
    
    try:
        if not controller.initialize():
            print("❌ Failed to initialize system")
            return 1
        
        # Start background tasks
        controller.start_background_tasks()
        
        # Start web server
        controller.run()
        
    except KeyboardInterrupt:
        print("\n🛑 Received interrupt signal")
    except Exception as e:
        controller.logger.error(f"❌ Fatal error: {e}")
        traceback.print_exc()
    finally:
        controller.shutdown()
        
    return 0

if __name__ == "__main__":
    exit(main()) 