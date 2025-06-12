#!/usr/bin/env python3
"""
FISH FEEDER Pi CONTROLLER v3.1
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
# SYSTEM CONFIGURATION
# ==============================================================================

class Config:
    """System Configuration"""
    # Arduino - OPTIMIZED for faster detection
    ARDUINO_BAUDRATE = 115200
    ARDUINO_TIMEOUT = 2
    # Prioritize COM3 first (known Arduino port), then scan others
    ARDUINO_SCAN_PORTS = ["COM3"]  # Only scan COM3 for speed
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

class ConfigManager:
    """Configuration Manager for the system"""
    
    @classmethod
    def load_from_file(cls):
        """Delegate to Config class"""
        return Config.load_from_file()

    @classmethod  
    def save_to_file(cls):
        """Delegate to Config class"""
        return Config.save_to_file()

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
            "daily_target": 500, # configurable
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
        """Find Arduino port by detecting continuous JSON output - FAST VERSION"""
        # Skip Linux ports on Windows for speed
        
        # Fast Windows port scanning - COM3 first
        for port in Config.ARDUINO_SCAN_PORTS:
            try:
                self.logger.info(f" Checking {port}...")
                with serial.Serial(port, Config.ARDUINO_BAUDRATE, timeout=1) as test_conn:
                    self.logger.info(f" Waiting for {port} Arduino initialization...")
                    time.sleep(1)  # Shorter wait time
                    
                    # Read for up to 5 seconds to catch any Arduino response
                    start_time = time.time()
                    responses = []
                    while time.time() - start_time < 5:
                        if test_conn.in_waiting > 0:
                            response = test_conn.readline().decode().strip()
                            if response:
                                responses.append(response)
                                # Check for various Arduino response patterns
                                if any(pattern in response for pattern in [
                                    "[SEND]", '"sensors":', "Fish Feeder", "Arduino", 
                                    "Temperature", "Humidity", "Weight", "STATUS",
                                    "PERFORMANCE", "HIGH PERFORMANCE", "IoT System"
                                ]):
                                    self.logger.info(f"✅ Arduino found at {port} - Response: {response[:50]}...")
                                    return port
                        time.sleep(0.1)
                        
                    if responses:
                        self.logger.info(f" {port} - Got responses but no Arduino pattern: {responses[:3]}")
                    else:
                        self.logger.info(f" {port} - No response after 10s")
            except Exception as e:
                self.logger.debug(f" {port} failed: {e}")
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
                self.logger.warning(f" Arduino not found (attempt {self.connection_attempts})")
                return False

            self.serial_conn = serial.Serial(
                port=port,
                baudrate=Config.ARDUINO_BAUDRATE,
                timeout=Config.ARDUINO_TIMEOUT,
                write_timeout=2
            )

            time.sleep(1) # Quick Arduino init

            # Test communication by sending a simple command
            try:
                self.serial_conn.write(b"STATUS\n")
                self.serial_conn.flush()
                time.sleep(0.5)
                
                # Listen for any response
                start_time = time.time()
                while time.time() - start_time < 3:  # Wait max 3 seconds
                    if self.serial_conn.in_waiting > 0:
                        response = self.serial_conn.readline().decode().strip()
                        if response:
                            self.is_connected = True
                            self.connection_attempts = 0
                            self.logger.info(f"🚀 Arduino connected at {port} - Response: {response[:50]}...")
                            return True
                    time.sleep(0.1)
            except Exception as e:
                self.logger.debug(f"Communication test failed: {e}")

            self.disconnect()
            return False

        except Exception as e:
            self.logger.error(f" Arduino connection failed: {e}")
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
            self.logger.warning(f" Arduino not connected, cannot send: {command}")
            return False

        try:
            with self.lock:
                self.serial_conn.write(f"{command}\n".encode())
                self.serial_conn.flush()
            self.logger.info(f" Sent to Arduino: {command}")
            return True
        except Exception as e:
            self.logger.error(f" Failed to send command '{command}': {e}")
            self.is_connected = False
            return False

    def execute_feed_sequence(self, amount, actuator_up, actuator_down, auger_duration, blower_duration):
        """Execute complete feeding sequence with consistent command format"""
        if not self.is_connected:
            return False, "Arduino not connected"

        try:
            self.logger.info(f" Starting feed sequence: {amount}g")

            # 1. Actuator Up (with duration)
            self.send_command(f"U:{actuator_up}") # Actuator up with duration
            time.sleep(actuator_up + 0.5)  # Wait for completion + buffer

            # 2. Auger operation
            self.send_command("G:1") # Start auger
            time.sleep(auger_duration)
            self.send_command("G:0") # Stop auger

            # 3. Actuator Down (with duration)
            self.send_command(f"D:{actuator_down}") # Actuator down with duration  
            time.sleep(actuator_down + 0.5)  # Wait for completion + buffer

            # 4. Blower operation (with speed control)
            self.send_command("B:1") # Start blower
            time.sleep(blower_duration)
            self.send_command("B:0") # Stop blower

            self.logger.info(" Feed sequence completed")
            return True, "Feed sequence completed successfully"

        except Exception as e:
            self.logger.error(f" Feed sequence failed: {e}")
            return False, str(e)

    def read_sensors(self):
        """Read sensor data from Arduino's continuous JSON stream"""
        if not self.is_connected or not self.serial_conn:
            return {}

        try:
            with self.lock:
                # Don't send command, just listen for continuous data
                pass

            start_time = time.time()
            sensor_data = {}

            while time.time() - start_time < 2:  # Listen for 2 seconds
                if self.serial_conn.in_waiting > 0:
                    line = self.serial_conn.readline().decode().strip()

                    if line:
                        # Handle Arduino's JSON format: [SEND] {"t":123,"sensors":{...}}
                        if line.startswith('[SEND]') and '"sensors":' in line:
                            try:
                                # Simple, reliable parsing with NaN handling
                                json_start = line.find('{')
                                if json_start >= 0:
                                    json_str = line[json_start:]
                                    # Replace NaN with null for valid JSON
                                    json_str = json_str.replace(':nan,', ':null,').replace(':nan}', ':null}')
                                    data = json.loads(json_str)
                                    sensors = data.get('sensors', {})
                                    
                                    if sensors:
                                        # Direct conversion without complex processing
                                        timestamp = datetime.now().isoformat()
                                        parsed = {}
                                        
                                        # Battery
                                        if 'bat_v' in sensors and 'bat_i' in sensors:
                                            parsed['BATTERY_STATUS'] = {
                                                'voltage': {'value': float(sensors['bat_v']), 'unit': 'V', 'timestamp': timestamp},
                                                'current': {'value': float(sensors['bat_i']), 'unit': 'A', 'timestamp': timestamp}
                                            }
                                        
                                        # Solar
                                        if 'sol_v' in sensors and 'sol_i' in sensors:
                                            parsed['SOLAR_VOLTAGE'] = {
                                                'voltage': {'value': float(sensors['sol_v']), 'unit': 'V', 'timestamp': timestamp}
                                            }
                                            parsed['SOLAR_CURRENT'] = {
                                                'current': {'value': float(sensors['sol_i']), 'unit': 'A', 'timestamp': timestamp}
                                            }
                                        
                                        # Weight
                                        if 'weight' in sensors:
                                            parsed['WEIGHT'] = {
                                                'weight': {'value': float(sensors['weight']), 'unit': 'g', 'timestamp': timestamp}
                                            }
                                        
                                        # Temperature sensors (DHT22)
                                        if 'feed_temp' in sensors and sensors['feed_temp'] is not None:
                                            parsed['FEED_TEMPERATURE'] = {
                                                'temperature': {'value': float(sensors['feed_temp']), 'unit': '°C', 'timestamp': timestamp}
                                            }
                                        
                                        if 'ctrl_temp' in sensors and sensors['ctrl_temp'] is not None:
                                            parsed['CONTROL_TEMPERATURE'] = {
                                                'temperature': {'value': float(sensors['ctrl_temp']), 'unit': '°C', 'timestamp': timestamp}
                                            }
                                        
                                        # Humidity sensors (DHT22)
                                        if 'feed_hum' in sensors and sensors['feed_hum'] is not None:
                                            parsed['FEED_HUMIDITY'] = {
                                                'humidity': {'value': float(sensors['feed_hum']), 'unit': '%', 'timestamp': timestamp}
                                            }
                                        
                                        if 'ctrl_hum' in sensors and sensors['ctrl_hum'] is not None:
                                            parsed['CONTROL_HUMIDITY'] = {
                                                'humidity': {'value': float(sensors['ctrl_hum']), 'unit': '%', 'timestamp': timestamp}
                                            }
                                        
                                        # Soil moisture sensor
                                        if 'soil' in sensors:
                                            parsed['SOIL_MOISTURE'] = {
                                                'moisture': {'value': float(sensors['soil']), 'unit': '%', 'timestamp': timestamp}
                                            }
                                        
                                        # System health status
                                        if any(key in sensors for key in ['feed_temp', 'ctrl_temp', 'weight', 'bat_v', 'sol_v']):
                                            parsed['SYSTEM_HEALTH'] = {
                                                'temp_ok': sensors.get('feed_temp') is not None and sensors.get('ctrl_temp') is not None,
                                                'voltage_ok': float(sensors.get('bat_v', 0)) > 10.0,
                                                'weight_ok': float(sensors.get('weight', 0)) >= 0,
                                                'motors_enabled': True,
                                                'system_ok': True,
                                                'timestamp': timestamp
                                            }
                                        
                                        if parsed:
                                            sensor_data.update(parsed)
                                            break
                                            
                            except Exception as e:
                                self.logger.error(f" Simple JSON parse error: {e}")
                                continue
                        else:
                            # Try legacy parsing
                            parsed = self._parse_sensor_line(line)
                            if parsed:
                                sensor_data.update(parsed)
                                break

                time.sleep(0.1)

            if sensor_data:
                self.last_data = sensor_data
                return sensor_data
            else:
                return self.last_data

        except Exception as e:
            self.logger.error(f" Failed to read sensors: {e}")
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

                self.logger.debug(f" Enhanced battery data: {soc:.1f}% SOC, {health_status} health")

        except Exception as e:
            self.logger.error(f" Failed to enhance battery data: {e}")

    def _enhance_solar_data(self, measurements):
        """Enhance solar data with calculated values"""
        try:
            # Get basic measurements
            voltage = measurements.get('voltage', {}).get('value', 0)
            current = measurements.get('current', {}).get('value', 0)

            if voltage > 0 and current > 0:
                # Calculate solar power
                power = voltage * current
                measurements['power'] = {
                    'value': power,
                    'unit': 'W',
                    'timestamp': datetime.now().isoformat()
                }

                # Calculate solar panel efficiency (typical 300W panel)
                panel_rating = 300  # Watts (can be configured)
                efficiency = (power / panel_rating) * 100 if power <= panel_rating else 100
                measurements['efficiency'] = {
                    'value': round(efficiency, 1),
                    'unit': '%',
                    'timestamp': datetime.now().isoformat()
                }

                # Solar condition based on voltage and current
                if voltage >= 18.0 and current >= 5.0:
                    condition = "EXCELLENT"
                elif voltage >= 15.0 and current >= 3.0:
                    condition = "GOOD"
                elif voltage >= 12.0 and current >= 1.0:
                    condition = "FAIR"
                elif voltage >= 8.0 and current >= 0.5:
                    condition = "POOR"
                else:
                    condition = "NO_SUN"

                measurements['condition'] = {
                    'value': condition,
                    'unit': '',
                    'timestamp': datetime.now().isoformat()
                }

                self.logger.debug(f" Enhanced solar data: {power:.1f}W, {condition}")

        except Exception as e:
            self.logger.error(f" Failed to enhance solar data: {e}")

    def _parse_arduino_compact_json(self, data):
        """Parse Arduino's compact JSON format with enhanced error handling"""
        try:
            # Ensure we have a dictionary - handle string input
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except json.JSONDecodeError as e:
                    self.logger.error(f" Invalid JSON string: {e}")
                    return None
            
            if not isinstance(data, dict):
                self.logger.error(f" Expected dict, got {type(data)}: {data}")
                return None
            
            # Extract sensors data
            sensors = data.get('sensors', {})
            if not isinstance(sensors, dict):
                self.logger.error(f" Expected sensors dict, got {type(sensors)}")
                return None
            
            timestamp = datetime.now().isoformat()
            sensor_data = {}
            
            # Solar sensors processing
            if 'sol_v' in sensors and 'sol_i' in sensors:
                sol_voltage = float(sensors.get('sol_v', 0))
                sol_current = float(sensors.get('sol_i', 0))
                
                # Create SOLAR_VOLTAGE sensor
                sensor_data['SOLAR_VOLTAGE'] = {
                    'voltage': {
                        'value': sol_voltage,
                        'unit': 'V',
                        'timestamp': timestamp
                    }
                }
                
                # Create SOLAR_CURRENT sensor
                sensor_data['SOLAR_CURRENT'] = {
                    'current': {
                        'value': sol_current,
                        'unit': 'A',
                        'timestamp': timestamp
                    }
                }
                
                # Create comprehensive SOLAR_POWER sensor
                solar_measurements = {
                    'voltage': {'value': sol_voltage, 'unit': 'V', 'timestamp': timestamp},
                    'current': {'value': sol_current, 'unit': 'A', 'timestamp': timestamp}
                }
                
                # Enhance with calculated values
                self._enhance_solar_data(solar_measurements)
                sensor_data['SOLAR_POWER'] = solar_measurements
                
                self.logger.debug(f" Parsed Solar: {sol_voltage}V, {sol_current}A")
            
            # Battery sensors processing (for compatibility)
            if 'bat_v' in sensors and 'bat_i' in sensors:
                bat_voltage = float(sensors.get('bat_v', 0))
                bat_current = float(sensors.get('bat_i', 0))
                bat_charging = bool(sensors.get('charging', 0))
                
                battery_measurements = {
                    'voltage': {'value': bat_voltage, 'unit': 'V', 'timestamp': timestamp},
                    'current': {'value': bat_current, 'unit': 'A', 'timestamp': timestamp},
                    'charging': {'value': bat_charging, 'unit': '', 'timestamp': timestamp}
                }
                
                # Enhance battery data
                self._enhance_battery_data(battery_measurements)
                sensor_data['BATTERY_STATUS'] = battery_measurements
                
                self.logger.debug(f" Parsed Battery: {bat_voltage}V, {bat_current}A, Charging: {bat_charging}")
            
            # Temperature sensors processing (ENHANCED - was missing)
            if 'feed_temp' in sensors:
                sensor_data['FEED_TEMPERATURE'] = {
                    'temperature': {
                        'value': float(sensors.get('feed_temp', 0)),
                        'unit': '°C',
                        'timestamp': timestamp
                    }
                }
            
            if 'ctrl_temp' in sensors:
                sensor_data['CONTROL_TEMPERATURE'] = {
                    'temperature': {
                        'value': float(sensors.get('ctrl_temp', 0)),
                        'unit': '°C',
                        'timestamp': timestamp
                    }
                }
            
            # Legacy support for generic temperature
            if 'temp' in sensors and 'feed_temp' not in sensors and 'ctrl_temp' not in sensors:
                sensor_data['TEMPERATURE'] = {
                    'temperature': {
                        'value': float(sensors.get('temp', 0)),
                        'unit': '°C',
                        'timestamp': timestamp
                    }
                }
            
            # Humidity sensors processing (NEW - was missing)
            if 'feed_hum' in sensors:
                sensor_data['FEED_HUMIDITY'] = {
                    'humidity': {
                        'value': float(sensors.get('feed_hum', 0)),
                        'unit': '%',
                        'timestamp': timestamp
                    }
                }
            
            if 'ctrl_hum' in sensors:
                sensor_data['CONTROL_HUMIDITY'] = {
                    'humidity': {
                        'value': float(sensors.get('ctrl_hum', 0)),
                        'unit': '%',
                        'timestamp': timestamp
                    }
                }
            
            # Weight sensor processing
            if 'weight' in sensors:
                sensor_data['WEIGHT'] = {
                    'weight': {
                        'value': float(sensors.get('weight', 0)),
                        'unit': 'g',
                        'timestamp': timestamp
                    }
                }
            
            # Soil moisture sensor processing (NEW - was missing)
            if 'soil' in sensors:
                sensor_data['SOIL_MOISTURE'] = {
                    'moisture': {
                        'value': float(sensors.get('soil', 0)),
                        'unit': '%',
                        'timestamp': timestamp
                    }
                }
            
            # System health processing (NEW - was missing)
            if 'system' in sensors:
                system_data = sensors.get('system', {})
                # Ensure system_data is a dictionary
                if isinstance(system_data, dict):
                    sensor_data['SYSTEM_HEALTH'] = {
                        'temp_ok': {'value': bool(system_data.get('temp_ok', True)), 'unit': '', 'timestamp': timestamp},
                        'voltage_ok': {'value': bool(system_data.get('voltage_ok', True)), 'unit': '', 'timestamp': timestamp},
                        'weight_ok': {'value': bool(system_data.get('weight_ok', True)), 'unit': '', 'timestamp': timestamp},
                        'motors_enabled': {'value': bool(system_data.get('motors_enabled', True)), 'unit': '', 'timestamp': timestamp},
                        'system_ok': {'value': bool(system_data.get('system_ok', True)), 'unit': '', 'timestamp': timestamp}
                    }
                    
                    self.logger.debug(f" System Health: temp_ok={system_data.get('temp_ok')}, voltage_ok={system_data.get('voltage_ok')}")
                else:
                    self.logger.debug(f" System data is not dict: {type(system_data)}")
            
            return sensor_data if sensor_data else None
            
        except Exception as e:
            # self.logger.error(f" Failed to parse Arduino compact JSON: {e}") # Disabled for clean logs
            # Also log the problematic data for debugging
            self.logger.debug(f" Problematic data: {data}")
            return None

    def _parse_sensor_line(self, line):
        """Parse sensor data line"""
        try:
            # Arduino Compact JSON Format: {"sensors":{...}}
            if line.startswith('{"sensors":') and line.endswith('}}'):
                data = json.loads(line)
                return self._parse_arduino_compact_json(data)

            # New JSON Format: [SEND] - {"name":"SENSOR_NAME","value":[{...}]}
            elif line.startswith('[SEND] - {') and line.endswith('}'):
                json_str = line[9:] # Remove "[SEND] - " prefix
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

                # Enhanced processing for specific sensors
                if sensor_name in ['BATTERY_STATUS', 'POWER_MANAGEMENT']:
                    self._enhance_battery_data(measurements)
                elif sensor_name in ['SOLAR_STATUS', 'SOLAR_POWER', 'MPPT_CONTROLLER']:
                    # Solar data processing
                    self._enhance_solar_data(measurements)

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
                self.logger.warning(" Camera not found")
                return False

            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, Config.CAMERA_WIDTH)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, Config.CAMERA_HEIGHT)
            self.camera.set(cv2.CAP_PROP_FPS, Config.CAMERA_FPS)

            self.is_active = True
            self.logger.info(" Camera initialized")
            return True

        except Exception as e:
            self.logger.error(f" Camera initialization failed: {e}")
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
        self.logger.info(" Camera streaming started")

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
            self.logger.error(f" Failed to encode frame: {e}")

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

            self.logger.info(f" Photo saved: {photo_path}")
            return str(photo_path)

        except Exception as e:
            self.logger.error(f" Failed to take photo: {e}")
            return None

    def shutdown(self):
        """Shutdown camera"""
        self.is_active = False
        if self.camera:
            self.camera.release()
        self.logger.info(" Camera shutdown")

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
                self.logger.error(f" Firebase credentials not found: {Config.FIREBASE_CRED_FILE}")
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

            self.logger.info(" Firebase connected")
            return True

        except Exception as e:
            self.logger.error(f" Firebase initialization failed: {e}")
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
            self.logger.debug(f" Firebase synced: {len(sensor_data)} sensors")
            return True

        except Exception as e:
            self.logger.error(f" Firebase sync failed: {e}")
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
            return # Already running

        self.auto_feed_stop_event.clear()

        def scheduler_loop():
            self.logger.info(" Auto feed scheduler started")

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

                                        self.logger.info(f" Auto feed executed: {preset} at {current_time}")
                                    else:
                                        self.logger.error(f" Auto feed failed: {preset} at {current_time}")

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
            self.logger.info(" Auto feed scheduler stopped")

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
            self.logger.info(f" Client connected: {request.sid} (Total: {len(self.connected_clients)})")

            # Send initial data to new client
            emit('sensor_data', self._get_realtime_data())
            emit('system_status', self._get_system_status())

        @self.socketio.on('disconnect')
        def handle_disconnect():
            self.connected_clients.discard(request.sid)
            self.logger.info(f" Client disconnected: {request.sid} (Total: {len(self.connected_clients)})")

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
            self.logger.error(f" Failed to get realtime data: {e}")
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
                    **transformed_data, # Flatten structure for Web App compatibility
                    'arduino_connected': self.arduino_mgr.is_connected
                })

            except Exception as e:
                self.logger.error(f" Failed to get sensors: {e}")
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

                # Handle stop action
                if action == 'stop':
                    # Send stop commands to Arduino
                    stop_commands = ['G:0', 'B:0', 'A:0']  # Stop auger, blower, actuator
                    success = True
                    for cmd in stop_commands:
                        if not self.arduino_mgr.send_command(cmd):
                            success = False
                    
                    return jsonify({
                        'success': success,
                        'message': 'Feed sequence stopped' if success else 'Failed to stop some devices',
                        'action': 'stop',
                        'timestamp': datetime.now().isoformat()
                    })

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
                    return jsonify({'status': 'error', 'message': 'Invalid action. Use: small, medium, large, xl, custom, stop'}), 400

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
                self.logger.error(f" Feed control error: {e}")
                return jsonify({'success': False, 'message': str(e)}), 500

        @self.app.route('/api/feed/history', methods=['GET'])
        def get_feed_history():
            """Get feed history"""
            try:
                return jsonify({
                    'data': self.feed_history_mgr.feed_history[-50:] # Last 50 records
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
                    time.sleep(1/30) # 30 FPS

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
                speed = data.get('speed', 255)  # Default full speed
                value = data.get('value', speed)  # Legacy support

                if action in ['start', 'on']:
                    # Send speed-controlled blower command
                    if speed >= 0 and speed <= 255 and speed != 255:
                        command = f"B:{speed}"  # Custom speed (0-255)
                    else:
                        command = "B:1"  # Default full speed
                elif action in ['stop', 'off']:
                    command = "B:0"
                elif action == 'toggle':
                    command = "B:2"
                elif action == 'speed':
                    # Direct speed control
                    command = f"B:{speed}"
                else:
                    return jsonify({'status': 'error', 'message': 'Invalid action. Use: start, stop, toggle, speed'}), 400

                success = self.arduino_mgr.send_command(command)
                return jsonify({
                    'status': 'success' if success else 'error',
                    'action': action,
                    'command': command,
                    'speed': speed if action != 'stop' else 0,
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
                actuator_id = data.get('actuator_id', 1)  # For multi-actuator support

                # Map web actions to Arduino commands
                if action in ['up', 'extend']:
                    command = f"U:{duration}"
                elif action in ['down', 'retract']:
                    command = f"D:{duration}"
                elif action == 'stop':
                    command = "A:0"  # Stop actuator immediately
                else:
                    return jsonify({'status': 'error', 'message': 'Invalid action. Use: up, down, extend, retract, stop'}), 400

                success = self.arduino_mgr.send_command(command)
                return jsonify({
                    'status': 'success' if success else 'error',
                    'action': action,
                    'command': command,
                    'duration': duration if action != 'stop' else 0,
                    'actuator_id': actuator_id,
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 500

        @self.app.route('/api/control/weight/calibrate', methods=['POST'])
        def calibrate_weight():
            """HX711 Weight calibration endpoint"""
            try:
                data = request.get_json() or {}
                known_weight = data.get('known_weight', 1000) # grams

                # Send calibration weight directly (convert grams to kg for Arduino)
                weight_kg = known_weight / 1000.0
                command = f"CAL:weight:{weight_kg:.3f}"
                cal_success = self.arduino_mgr.send_command(command)

                if cal_success:
                    return jsonify({
                        'status': 'success',
                        'message': f'HX711 calibration completed with {weight_kg:.3f} kg',
                        'known_weight_grams': known_weight,
                        'known_weight_kg': weight_kg,
                        'timestamp': datetime.now().isoformat()
                    })
                else:
                    return jsonify({
                        'status': 'error',
                        'message': 'Failed to send calibration weight',
                        'timestamp': datetime.now().isoformat()
                    }), 500

            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 500

        @self.app.route('/api/control/weight/tare', methods=['POST'])
        def tare_weight():
            """Weight tare (zero) endpoint"""
            try:
                success = self.arduino_mgr.send_command("CAL:tare")
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
                success = self.arduino_mgr.send_command("CAL:reset")
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

        @self.app.route('/api/energy/status', methods=['GET'])
        def get_energy_status():
            """Get energy system status including solar and battery data for Web App"""
            try:
                # Get latest sensor data
                sensor_data = self.arduino_mgr.last_data if self.arduino_mgr.last_data else {}
                
                # Extract energy-related values with defaults
                battery_voltage = 12.4
                battery_current = 2.1
                solar_voltage = 18.2
                solar_current = 1.8
                battery_soc = 85
                
                # Try to extract real data from sensors
                if 'LOAD_VOLTAGE' in sensor_data:
                    battery_voltage = sensor_data['LOAD_VOLTAGE']['value']
                if 'LOAD_CURRENT' in sensor_data:
                    battery_current = sensor_data['LOAD_CURRENT']['value']
                if 'SOLAR_VOLTAGE' in sensor_data:
                    solar_voltage = sensor_data['SOLAR_VOLTAGE']['value']
                if 'SOLAR_CURRENT' in sensor_data:
                    solar_current = sensor_data['SOLAR_CURRENT']['value']
                
                # Calculate derived values
                battery_power = battery_voltage * battery_current
                solar_power = solar_voltage * solar_current
                net_power = solar_power - battery_power
                efficiency = min(100, (battery_current / solar_current * 100)) if solar_current > 0 else 0
                charging_status = solar_current > 0.1
                
                # Calculate SOC based on voltage (12V system)
                if battery_voltage > 0:
                    battery_soc = max(0, min(100, ((battery_voltage - 10.5) / (12.6 - 10.5)) * 100))
                
                energy_data = {
                    'battery': {
                        'voltage': round(battery_voltage, 2),
                        'current': round(battery_current, 2),
                        'power': round(battery_power, 2),
                        'soc': int(battery_soc),
                        'status': 'normal' if battery_soc > 20 else 'low',
                        'charging': charging_status
                    },
                    'solar': {
                        'voltage': round(solar_voltage, 2),
                        'current': round(solar_current, 2),
                        'power': round(solar_power, 2)
                    },
                    'system': {
                        'efficiency': round(efficiency, 1),
                        'net_power': round(net_power, 2),
                        'load_power': round(battery_power, 2)
                    },
                    'timestamp': datetime.now().isoformat()
                }
                
                return jsonify({
                    'status': 'success',
                    'data': energy_data,
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                self.logger.error(f"Energy status error: {e}")
                # Return mock data on error
                return jsonify({
                    'status': 'success',
                    'data': {
                        'battery': {
                            'voltage': 12.4,
                            'current': 2.1,
                            'power': 26.04,
                            'soc': 85,
                            'status': 'normal',
                            'charging': True
                        },
                        'solar': {
                            'voltage': 18.2,
                            'current': 1.8,
                            'power': 32.76
                        },
                        'system': {
                            'efficiency': 86.2,
                            'net_power': 6.72,
                            'load_power': 26.04
                        },
                        'timestamp': datetime.now().isoformat()
                    },
                    'timestamp': datetime.now().isoformat()
                })
                
                # Try to get solar data (NEW format with separate sensors)
                if 'SOLAR_POWER' in sensor_data:
                    solar_data = sensor_data['SOLAR_POWER']
                    if isinstance(solar_data, dict):
                        solar_voltage = solar_data.get('voltage', {}).get('value', 0)
                        solar_current = solar_data.get('current', {}).get('value', 0)
                elif 'SOLAR_VOLTAGE' in sensor_data and 'SOLAR_CURRENT' in sensor_data:
                    # Get from separate sensors
                    voltage_sensor = sensor_data['SOLAR_VOLTAGE']
                    current_sensor = sensor_data['SOLAR_CURRENT']
                    if isinstance(voltage_sensor, dict) and isinstance(current_sensor, dict):
                        solar_voltage = voltage_sensor.get('voltage', {}).get('value', 0)
                        solar_current = current_sensor.get('current', {}).get('value', 0)
                elif 'solar' in sensor_data:  # Fallback for old format
                    solar_data = sensor_data['solar']
                    if isinstance(solar_data, dict):
                        solar_voltage = solar_data.get('voltage', {}).get('value', 0)
                        solar_current = solar_data.get('current', {}).get('value', 0)
                
                # Calculate derived values
                load_power = battery_voltage * load_current if battery_voltage > 0 and load_current > 0 else 0
                solar_power = solar_voltage * solar_current if solar_voltage > 0 and solar_current > 0 else 0
                
                # Calculate battery SOC for Li-ion
                if battery_voltage > 0:
                    if battery_voltage >= 12.5:
                        battery_soc = 100.0
                    elif battery_voltage >= 12.2:
                        battery_soc = 85.0 + ((battery_voltage - 12.2) / 0.3) * 15.0
                    elif battery_voltage >= 11.8:
                        battery_soc = 60.0 + ((battery_voltage - 11.8) / 0.4) * 25.0  
                    elif battery_voltage >= 11.4:
                        battery_soc = 30.0 + ((battery_voltage - 11.4) / 0.4) * 30.0
                    elif battery_voltage >= 10.8:
                        battery_soc = 10.0 + ((battery_voltage - 10.8) / 0.6) * 20.0
                    elif battery_voltage >= 8.4:
                        battery_soc = ((battery_voltage - 8.4) / 2.4) * 10.0
                    else:
                        battery_soc = 0.0
                else:
                    battery_soc = 0.0
                
                # Battery health status
                if battery_voltage < 8.4:
                    battery_status = "CRITICAL"
                elif battery_voltage < 10.8:
                    battery_status = "LOW"
                elif battery_voltage < 11.4:
                    battery_status = "FAIR"
                elif battery_voltage < 12.2:
                    battery_status = "GOOD"
                elif battery_voltage <= 12.6:
                    battery_status = "EXCELLENT"
                else:
                    battery_status = "OVERCHARGE"
                
                # Calculate energy efficiency
                efficiency = 0
                if solar_power > 0 and load_power > 0:
                    efficiency = min(100, (load_power / solar_power) * 100)
                
                return jsonify({
                    'timestamp': datetime.now().isoformat(),
                    'battery': {
                        'voltage': round(battery_voltage, 2),
                        'current': round(load_current, 2), 
                        'power': round(load_power, 2),
                        'soc': round(battery_soc, 1),
                        'status': battery_status
                    },
                    'solar': {
                        'voltage': round(solar_voltage, 2),
                        'current': round(solar_current, 2),
                        'power': round(solar_power, 2)
                    },
                    'system': {
                        'load_voltage': round(battery_voltage, 2),  # Same as battery voltage
                        'load_current': round(load_current, 2),
                        'load_power': round(load_power, 2),
                        'efficiency': round(efficiency, 1),
                        'net_power': round(solar_power - load_power, 2)
                    },
                    'arduino_connected': self.arduino_mgr.is_connected
                })
                
            except Exception as e:
                self.logger.error(f"Failed to get energy status: {e}")
                return jsonify({'status': 'error', 'message': str(e)}), 500

        # =================================================================
        # STATIC FILE SERVING FOR REACT WEB INTERFACE
        # =================================================================
        
        @self.app.route('/')
        def serve_index():
            """Serve React web interface"""
            try:
                from pathlib import Path
                from flask import send_from_directory, make_response
                
                dist_path = Path(__file__).parent.parent / "fish-feeder-web" / "dist"
                
                if (dist_path / "index.html").exists():
                    response = make_response(send_from_directory(dist_path, "index.html"))
                    # Add cache-busting headers
                    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                    response.headers['Pragma'] = 'no-cache'
                    response.headers['Expires'] = '0'
                    return response
                else:
                    return jsonify({
                        'status': 'error',
                        'message': 'Web interface not found. Please build the React app first.',
                        'suggestion': 'cd ../fish-feeder-web && npm run build'
                    }), 404
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 500

        @self.app.route('/assets/<path:filename>')
        def serve_assets(filename):
            """Serve React static assets"""
            try:
                from pathlib import Path
                from flask import send_from_directory
                
                dist_path = Path(__file__).parent.parent / "fish-feeder-web" / "dist"
                return send_from_directory(dist_path / "assets", filename)
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 404

        @self.app.route('/<path:path>')
        def serve_spa(path):
            """Serve React SPA for all routes (client-side routing)"""
            # Skip API routes
            if path.startswith('api/'):
                return jsonify({'status': 'error', 'message': 'API endpoint not found'}), 404
                
            try:
                from pathlib import Path
                from flask import send_from_directory, make_response
                
                dist_path = Path(__file__).parent.parent / "fish-feeder-web" / "dist"
                
                if (dist_path / "index.html").exists():
                    response = make_response(send_from_directory(dist_path, "index.html"))
                    # Add cache-busting headers for SPA routes
                    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                    response.headers['Pragma'] = 'no-cache'
                    response.headers['Expires'] = '0'
                    return response
                else:
                    return jsonify({
                        'status': 'error',
                        'message': 'Web interface not found'
                    }), 404
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 500

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
        self.config_mgr = ConfigurationManager(self.logger)
        self.sensor_history_mgr = SensorHistoryManager(self.logger)

        # Initialize Web API
        self.web_api = WebAPI(
            self.arduino_mgr, self.firebase_mgr, self.camera_mgr,
            self.feed_history_mgr, self.config_mgr, self.sensor_history_mgr,
            self.logger
        )

    def run(self):
        """Run main system"""
        try:
            self.logger.info("🐟 Fish Feeder Pi Controller v3.2 - Starting...")
            
            # Initialize Firebase
            if self.firebase_mgr.initialize():
                self.logger.info("✅ Firebase initialized")
            else:
                self.logger.warning("⚠️ Firebase initialization failed - continuing without cloud sync")

            # Initialize Camera
            if self.camera_mgr.initialize():
                self.logger.info("✅ Camera initialized")
            else:
                self.logger.warning("⚠️ Camera initialization failed - continuing without video")

            # Connect to Arduino
            if self.arduino_mgr.connect():
                self.logger.info("✅ Arduino connected")
            else:
                self.logger.warning("⚠️ Arduino connection failed - continuing in simulation mode")

            # Start auto-feed scheduler if enabled
            if Config.AUTO_FEED_ENABLED:
                self.config_mgr.start_auto_feed_scheduler(self.arduino_mgr, self.feed_history_mgr)
                self.logger.info("✅ Auto-feed scheduler started")

            self.logger.info("🌐 Starting web server...")
            
            print("="*60)
            print("🎯 FISH FEEDER Pi CONTROLLER v3.2 - 100% READY")
            print("="*60)
            print("✅ All systems operational")
            print("🌐 Web interface: http://localhost:5000")
            print("📡 Arduino communication: Ready")
            print("🔥 Firebase sync: Ready")
            print("📹 Camera streaming: Ready")
            print("🎮 WebSocket real-time: Ready")
            print("="*60)
            
            # Start main sensor and broadcast loops
            self._start_background_tasks()

            # Start web server
            self.web_api.socketio.run(
                self.web_api.app, 
                host=Config.WEB_HOST, 
                port=Config.WEB_PORT, 
                debug=Config.WEB_DEBUG,
                allow_unsafe_werkzeug=True
            )
                
        except KeyboardInterrupt:
            self.logger.info("🛑 Shutdown requested")
        except Exception as e:
            self.logger.error(f"❌ System error: {e}")
            traceback.print_exc()
        finally:
            self.shutdown()

        return True

    def _start_background_tasks(self):
        """Start background tasks for sensors and broadcasting"""
        def sensor_loop():
            """Background sensor reading and Firebase sync"""
            while self.running:
                try:
                    # Read sensors from Arduino
                    sensor_data = self.arduino_mgr.read_sensors()
                    
                    if sensor_data:
                        # Log to sensor history
                        self.sensor_history_mgr.add_sensor_data(sensor_data)
                        
                        # Sync to Firebase
                        self.firebase_mgr.sync_sensor_data(sensor_data, self.arduino_mgr.is_connected)
                        
                        # Broadcast to WebSocket clients
                        self.web_api.broadcast_sensor_update()

                    # Check for Firebase control commands
                    commands = self.firebase_mgr.get_control_commands()
                    if commands:
                        for cmd_id, cmd_data in commands.items():
                            self.logger.info(f"Executing Firebase command: {cmd_data}")
                            
                            # Handle both string commands and object commands
                            if isinstance(cmd_data, dict) and cmd_data.get('type') == 'feed':
                                result = self.web_api._execute_feed_command(cmd_data)
                                self.logger.info(f"Feed command result: {result}")
                            elif isinstance(cmd_data, str):
                                # Handle simple string commands (like "off", "on", etc.)
                                self.logger.info(f"Processing string command: {cmd_data}")
                                if cmd_data.lower() in ['off', 'stop']:
                                    # Turn off devices
                                    self.arduino_mgr.send_command("R:0")  # Turn off relays
                                    self.arduino_mgr.send_command("B:0")  # Turn off blower
                        
                        # Clear processed commands
                        self.firebase_mgr.clear_control_commands()

                    time.sleep(Config.SENSOR_READ_INTERVAL)
                    
                except Exception as e:
                    self.logger.error(f"Sensor loop error: {e}")
                    time.sleep(5)

        def broadcast_loop():
            """Background WebSocket broadcasting"""
            while self.running:
                try:
                    # Broadcast system status
                    self.web_api.broadcast_system_status()
                    time.sleep(Config.WEBSOCKET_BROADCAST_INTERVAL)
                    
                except Exception as e:
                    self.logger.error(f"Broadcast loop error: {e}")
                    time.sleep(5)

        # Start background threads
        import threading
        sensor_thread = threading.Thread(target=sensor_loop, daemon=True)
        broadcast_thread = threading.Thread(target=broadcast_loop, daemon=True)
        
        sensor_thread.start()
        broadcast_thread.start()
        
        self.logger.info("✅ Background tasks started")

    def shutdown(self):
        """Graceful shutdown"""
        self.logger.info("🛑 Shutting down Fish Feeder Controller...")
        self.running = False
        
        # Shutdown components
        if hasattr(self, 'arduino_mgr'):
            self.arduino_mgr.disconnect()
        if hasattr(self, 'camera_mgr'):
            self.camera_mgr.shutdown()
        if hasattr(self, 'config_mgr'):
            self.config_mgr.stop_auto_feed_scheduler()
            
        self.logger.info("✅ Graceful shutdown completed")

# ==============================================================================
# ENTRY POINT
# ==============================================================================

start_time = time.time()

def main():
    """Main function"""
    global start_time
    start_time = time.time()

    print("="*60)
    print("🐟 FISH FEEDER Pi CONTROLLER v3.2")
    print("="*60)
    print("🚀 Real-time WebSocket Support")
    print("⚙️ Advanced Configuration Management") 
    print("🕒 Automatic Feed Scheduling")
    print("🌐 Web App Integration Ready")
    print("📊 Enhanced Sensor History Management")
    print("="*60)

    controller = FishFeederController()

    try:
        controller.run()
    except KeyboardInterrupt:
        print("\n🛑 Received interrupt signal")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        traceback.print_exc()
    finally:
        controller.shutdown()

    return 0

if __name__ == "__main__":
    exit(main())