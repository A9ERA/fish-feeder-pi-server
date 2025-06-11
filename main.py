#!/usr/bin/env python3
"""
🐟 FISH FEEDER Pi CONTROLLER v3.0
=================================
Complete Pi Controller for Arduino-based Fish Feeding System with Web App Integration
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

# Firebase
import firebase_admin
from firebase_admin import credentials, db

# Camera
import cv2
import threading

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
    
    # Firebase
    FIREBASE_CRED_FILE = "serviceAccountKey.json"
    FIREBASE_DATABASE_URL = "https://fish-feeder-test-1-default-rtdb.asia-southeast1.firebasedatabase.app"
    FIREBASE_ROOT_PATH = "fish_feeder"
    
    # Timing
    SENSOR_READ_INTERVAL = 3
    FIREBASE_SYNC_INTERVAL = 5
    STATUS_BROADCAST_INTERVAL = 10
    
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
                        except:
                            value = 0
                    
                    measurements[measurement_type] = {
                        'value': value,
                        'unit': unit,
                        'timestamp': timestamp
                    }
                
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
                        except:
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

class WebAPI:
    """Flask-based Web API"""
    
    def __init__(self, arduino_mgr, firebase_mgr, camera_mgr, feed_history_mgr, logger):
        self.arduino_mgr = arduino_mgr
        self.firebase_mgr = firebase_mgr
        self.camera_mgr = camera_mgr
        self.feed_history_mgr = feed_history_mgr
        self.logger = logger
        
        self.app = Flask(__name__)
        CORS(self.app)
        
        # Reduce Flask logging
        self.app.logger.setLevel(logging.WARNING)
        
        self._setup_routes()
    
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
                
                # Transform sensor data to Web App format
                transformed_data = {}
                current_time = datetime.now().isoformat()
                
                for sensor_name, measurements in sensor_data.items():
                    if isinstance(measurements, dict):
                        transformed_data[sensor_name] = {
                            'timestamp': current_time,
                            'values': []
                        }
                        
                        for measure_type, data in measurements.items():
                            if isinstance(data, dict) and 'value' in data:
                                transformed_data[sensor_name]['values'].append({
                                    'type': measure_type,
                                    'value': data['value'],
                                    'unit': data.get('unit', ''),
                                    'timestamp': data.get('timestamp', current_time)
                                })
                
                return jsonify({
                    'status': 'success',
                    'timestamp': current_time,
                    'data': transformed_data,
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
                
                # Get timing parameters
                if action in Config.FEED_PRESETS:
                    preset = Config.FEED_PRESETS[action]
                    amount = data.get('amount', preset['amount'])
                    actuator_up = data.get('actuator_up', preset['actuator_up'])
                    actuator_down = data.get('actuator_down', preset['actuator_down'])
                    auger_duration = data.get('auger_duration', preset['auger_duration'])
                    blower_duration = data.get('blower_duration', preset['blower_duration'])
                elif action == 'custom':
                    amount = data.get('amount', 100)
                    actuator_up = data.get('actuator_up', 3)
                    actuator_down = data.get('actuator_down', 2)
                    auger_duration = data.get('auger_duration', 20)
                    blower_duration = data.get('blower_duration', 15)
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
    
    def run(self):
        """Start web server"""
        self.logger.info(f"🌐 Starting web server at http://{Config.WEB_HOST}:{Config.WEB_PORT}")
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
    """Main system controller"""
    
    def __init__(self):
        self.logger = setup_logging()
        self.running = True
        
        # Initialize managers
        self.arduino_mgr = ArduinoManager(self.logger)
        self.firebase_mgr = FirebaseManager(self.logger)
        self.camera_mgr = CameraManager(self.logger)
        self.feed_history_mgr = FeedHistoryManager(self.logger)
        self.web_api = WebAPI(
            self.arduino_mgr, self.firebase_mgr, self.camera_mgr, 
            self.feed_history_mgr, self.logger
        )
        
        # Timing
        self.last_sensor_read = 0
        self.last_firebase_sync = 0
        self.last_status_broadcast = 0
        
        # Signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"🛑 Received signal {signum}, shutting down...")
        self.running = False
    
    def initialize(self):
        """Initialize system"""
        self.logger.info("🚀 Initializing Fish Feeder Controller v3.0...")
        
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
        """Graceful shutdown"""
        self.logger.info("🔄 Shutting down...")
        self.running = False
        
        if self.arduino_mgr:
            self.arduino_mgr.disconnect()
        
        if self.camera_mgr:
            self.camera_mgr.shutdown()
        
        if self.firebase_mgr and self.firebase_mgr.is_connected:
            try:
                self.firebase_mgr.db_ref.child('status').update({
                    'online': False,
                    'last_shutdown': datetime.now().isoformat()
                })
            except:
                pass
        
        self.logger.info("✅ Shutdown completed")

# ==============================================================================
# ENTRY POINT
# ==============================================================================

start_time = time.time()

def main():
    """Main entry point"""
    print("🐟 Fish Feeder Pi Controller v3.0")
    print("==================================")
    
    controller = FishFeederController()
    return controller.run()

if __name__ == "__main__":
    sys.exit(0 if main() else 1) 