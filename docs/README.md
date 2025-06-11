# 🐟 Fish Feeder Pi Controller

**Raspberry Pi MQTT Server with Real-time WebSocket Support & Advanced Feed Management**

## 📋 Overview

The Fish Feeder Pi Controller is the central bridge component that connects the Arduino hardware to the web interface. Built with Python Flask and real-time WebSocket communication, it provides comprehensive system management, sensor data processing, feed history tracking, and remote control capabilities.

## ✨ Key Features

### 🎯 Core Functionality
- **Arduino Bridge**: High-speed serial communication with Arduino Mega 2560
- **Real-time WebSocket**: Live sensor data streaming and bidirectional communication
- **REST API**: Comprehensive HTTP endpoints for web interface integration
- **Feed Management**: Complete feeding system with history, scheduling, and presets
- **Firebase Integration**: Cloud data synchronization and remote monitoring
- **Camera System**: Live video streaming and snapshot capture
- **Auto-scheduler**: Time-based automatic feeding with configurable schedules

### 🔧 Advanced Features
- **Feed History**: JSON-based session logging with filtering and statistics
- **Configuration Manager**: Dynamic system configuration with persistence
- **WebSocket Broadcasting**: Real-time updates to multiple connected clients
- **Error Recovery**: Automatic Arduino reconnection and fault tolerance
- **Video Recording**: Feed session video capture with Google Drive integration
- **Health Monitoring**: System status tracking and performance metrics

### 📡 Communication Protocols
- **Serial**: Arduino communication via USB/UART (115200 baud)
- **WebSocket**: Real-time bidirectional web communication
- **HTTP REST**: Standard API endpoints for web integration
- **Firebase**: Cloud database synchronization
- **MQTT**: Message queuing for distributed systems (extensible)

## 🛠️ System Requirements

### 📟 Hardware Requirements
- **Raspberry Pi 4** (Recommended 4GB+ RAM)
- **MicroSD Card**: 32GB+ Class 10 (for video storage)
- **USB Connection**: Arduino Mega 2560 serial interface
- **Camera Module**: Pi Camera or USB webcam (optional)
- **Network**: WiFi or Ethernet for web access

### 🐍 Software Dependencies
- **Python 3.8+**
- **Flask** - Web framework
- **Flask-SocketIO** - WebSocket support
- **PySerial** - Arduino communication
- **Firebase Admin SDK** - Cloud integration
- **OpenCV** - Camera and video processing

## 🏗️ Architecture Overview

### 📁 Project Structure
```
pi-mqtt-server/
├── main.py                   # Main application entry point
├── requirements.txt          # Python dependencies
├── config.json              # Runtime configuration (auto-generated)
├── serviceAccountKey.json   # Firebase credentials
├── logs/                    # System and sensor logs
│   ├── system.log          # Application logs
│   ├── feed_history.json   # Feed session history
│   ├── feed_sessions/      # Individual session logs
│   └── YYYY-MM-DD/         # Daily sensor logs
└── README.md               # This file
```

### 🔄 Core Components

#### `FishFeederController` (Main Application)
```python
class FishFeederController:
    """Main application controller orchestrating all components"""
    - ArduinoManager: Hardware communication
    - CameraManager: Video streaming and recording
    - FirebaseManager: Cloud data synchronization
    - WebAPI: HTTP/WebSocket server
    - ConfigurationManager: System configuration
    - FeedHistoryManager: Feed session tracking
```

#### `ArduinoManager` (Hardware Interface)
```python
class ArduinoManager:
    """Handles all Arduino communication and command processing"""
    - Auto-discovery and connection
    - Serial command parsing and execution
    - Sensor data collection and parsing
    - Feed sequence coordination
    - Error detection and recovery
```

#### `WebAPI` (Server Interface)
```python
class WebAPI:
    """Flask-based web server with WebSocket support"""
    - REST API endpoints
    - Real-time WebSocket communication
    - Cross-origin resource sharing (CORS)
    - Request validation and error handling
```

## 🚀 Installation & Setup

### 1. 📥 System Prerequisites

#### Update Raspberry Pi
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-venv git -y
```

#### Install System Dependencies
```bash
# Camera support (if using Pi Camera)
sudo apt install python3-picamera -y

# OpenCV dependencies
sudo apt install libopencv-dev python3-opencv -y

# Serial port access
sudo usermod -a -G dialout pi
```

### 2. 🔧 Project Installation

#### Clone Repository
```bash
git clone [repository-url]
cd pi-mqtt-server
```

#### Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# or
# venv\Scripts\activate    # Windows
```

#### Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 3. ⚙️ Configuration

#### Arduino Connection
```bash
# Find Arduino port
ls /dev/tty*
# Look for /dev/ttyUSB0 or /dev/ttyACM0

# Test Arduino connection
python3 -c "
import serial.tools.list_ports
for port in serial.tools.list_ports.comports():
    print(f'{port.device}: {port.description}')
"
```

#### Firebase Setup (Optional)
```bash
# 1. Create Firebase project at https://console.firebase.google.com
# 2. Generate service account key
# 3. Download serviceAccountKey.json to project root
# 4. Update FIREBASE_DATABASE_URL in main.py
```

#### Camera Setup (Optional)
```bash
# Enable Pi Camera
sudo raspi-config
# Interface Options > Camera > Enable

# Test camera
raspistill -o test.jpg
```

### 4. 🔐 Permissions & Security

#### Serial Port Access
```bash
# Add user to dialout group
sudo usermod -a -G dialout $USER

# Logout and login again for changes to take effect
```

#### Firebase Permissions
```bash
# Secure Firebase key file
chmod 600 serviceAccountKey.json
```

## 🎮 Usage & Operation

### 🚀 Starting the Server

#### Basic Startup
```bash
# Navigate to project directory
cd pi-mqtt-server

# Activate virtual environment
source venv/bin/activate

# Run the server
python3 main.py
```

#### Production Startup
```bash
# Run in background with logging
nohup python3 main.py > server.log 2>&1 &

# View real-time logs
tail -f server.log
```

#### Auto-start Service (Systemd)
```bash
# Create service file
sudo nano /etc/systemd/system/fish-feeder.service

# Add service configuration:
[Unit]
Description=Fish Feeder Pi Controller
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/fish-feeder/pi-mqtt-server
ExecStart=/home/pi/fish-feeder/pi-mqtt-server/venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target

# Enable and start service
sudo systemctl enable fish-feeder.service
sudo systemctl start fish-feeder.service

# Check status
sudo systemctl status fish-feeder.service
```

### 📡 API Endpoints

#### System Health & Status
```http
GET /api/health
# Returns: System health and component status

GET /api/sensors
# Returns: All current sensor readings

GET /api/sensors/<sensor_name>
# Returns: Specific sensor data with history
```

#### Feed Control & Management
```http
POST /api/feed
Content-Type: application/json
{
    "preset": "medium",           # small/medium/large/xl
    "custom_amount": 150,         # grams (optional)
    "actuator_up": 3,            # seconds (optional)
    "actuator_down": 2,          # seconds (optional)
    "auger_duration": 20,        # seconds (optional)
    "blower_duration": 15        # seconds (optional)
}

GET /api/feed/history
# Returns: Complete feed history with filters

GET /api/feed/history/filter?start_date=2024-01-01&end_date=2024-12-31&template=medium&alert_type=high_temp
# Returns: Filtered feed history

GET /api/feed/statistics
# Returns: Feed statistics and analytics

GET /api/feed/session/<session_id>
# Returns: Detailed session information
```

#### Device Control
```http
POST /api/control/relay/<device>
# Devices: led, fan, pump
Content-Type: application/json
{ "action": "on|off|toggle" }

POST /api/control/blower
Content-Type: application/json
{ "action": "on|off", "duration": 10 }

POST /api/control/actuator
Content-Type: application/json
{ "action": "up|down", "duration": 3 }

POST /api/control/direct
Content-Type: application/json
{ "command": "G:1" }  # Direct Arduino command
```

#### Weight & Calibration
```http
POST /api/control/weight/calibrate
Content-Type: application/json
{ "weight": 1000 }  # Known weight in grams

POST /api/control/weight/tare
# Zeros the scale

POST /api/control/weight/reset
# Resets calibration to factory defaults
```

#### Camera & Video
```http
GET /api/camera/stream
# Returns: MJPEG video stream

GET /api/camera/status
# Returns: Camera availability and settings

POST /api/camera/photo
# Takes and returns a photo
```

#### Configuration Management
```http
GET /api/control/config
# Returns: Current system configuration

POST /api/control/config
Content-Type: application/json
{
    "sensor_read_interval": 3,
    "firebase_sync_interval": 5,
    "auto_feed_enabled": true,
    "feed_presets": {
        "small": {"amount": 50, "actuator_up": 2, ...}
    }
}
```

#### Auto-Feed Scheduling
```http
POST /api/auto-feed/start
# Starts the auto-feed scheduler

POST /api/auto-feed/stop
# Stops the auto-feed scheduler

GET /api/auto-feed/schedule
# Returns: Current feeding schedule

POST /api/auto-feed/schedule
Content-Type: application/json
{
    "schedule": [
        {"time": "08:00", "preset": "medium", "enabled": true},
        {"time": "18:00", "preset": "large", "enabled": true}
    ]
}
```

### 🔌 WebSocket Events

#### Client → Server Events
```javascript
// Connect to WebSocket
const socket = io('http://pi-ip:5000');

// Request real-time sensor data
socket.emit('request_sensor_data');

// Request system status
socket.emit('request_system_status');

// Send feed command
socket.emit('feed_command', {
    preset: 'medium',
    custom_amount: 120
});
```

#### Server → Client Events
```javascript
// Real-time sensor updates
socket.on('sensor_update', (data) => {
    console.log('Sensor data:', data);
    // Handle sensor data updates
});

// System status updates
socket.on('system_status', (status) => {
    console.log('System status:', status);
    // Handle system status changes
});

// Feed operation updates
socket.on('feed_status', (status) => {
    console.log('Feed status:', status);
    // Handle feeding progress updates
});

// Error notifications
socket.on('error_notification', (error) => {
    console.log('System error:', error);
    // Handle error notifications
});
```

## 📊 Feed History System

### 🗂️ Session Logging

#### Automatic Session Creation
```python
# Feed session structure
{
    "id": "feed_20240321_103000",
    "start_timestamp": "2024-03-21T10:30:00.000Z",
    "end_timestamp": "2024-03-21T10:32:15.000Z",
    "template": "medium",
    "weight_fed": 98.5,
    "target_weight": 100,
    "duration": 135,
    "status": "completed",
    "initial_sensors": {
        "temp": 25.5,
        "humidity": 65.0,
        "water_temp": 24.0,
        "bin_weight": 8.5,
        "voltage": 12.4,
        "battery_percentage": 87.2
    },
    "final_sensors": {
        "temp": 25.3,
        "humidity": 64.8,
        "water_temp": 24.1,
        "bin_weight": 8.4,
        "voltage": 12.3,
        "battery_percentage": 86.8
    },
    "alerts": [
        {
            "type": "high_temp",
            "message": "Temperature exceeded 30°C",
            "timestamp": "2024-03-21T10:31:20.000Z",
            "value": 31.2
        }
    ],
    "video_local": "/videos/feed_20240321_103000.mp4",
    "video_cloud": "https://drive.google.com/file/d/xxx",
    "sensor_readings": [
        {
            "timestamp": "2024-03-21T10:30:30.000Z",
            "weight": 8.48,
            "temp": 25.6,
            "humidity": 64.9
        }
        // ... more readings every 10 seconds
  ]
}
```

#### File Storage Structure
```
logs/
├── feed_history.json           # Master feed history index
├── feed_sessions/              # Individual session files
│   ├── feed_20240321_103000.json
│   ├── feed_20240321_143000.json
│   └── ...
└── videos/                     # Local video storage
    ├── feed_20240321_103000.mp4
    ├── feed_20240321_143000.mp4
    └── ...
```

### 📈 Statistics & Analytics

#### Feed Statistics Calculation
```python
def get_feed_statistics():
    return {
        "total_sessions": 145,
        "total_weight_fed": 12.5,    # kg
        "average_session_duration": 127,  # seconds
        "success_rate": 98.6,        # percentage
        "last_30_days": {
            "sessions": 42,
            "weight_fed": 3.8,
            "alerts": 3
        },
        "alerts_summary": {
            "high_temp": 5,
            "low_battery": 2,
            "low_weight": 1
        },
        "feeding_patterns": {
            "by_hour": {...},
            "by_template": {
                "small": 45,
                "medium": 78,
                "large": 22
            }
        }
    }
```

### 🔍 Filtering & Search

#### Query Parameters
```http
GET /api/feed/history/filter?
    start_date=2024-01-01&
    end_date=2024-12-31&
    template=medium&
    alert_type=high_temp&
    status=completed&
    min_weight=50&
    max_weight=200&
    limit=50&
    offset=0
```

## 🎥 Video Recording System

### 📹 Automatic Recording

#### Feed Session Recording
```python
class VideoRecorder:
    def start_feed_recording(self, session_id):
        """Start recording for feed session"""
        video_path = f"logs/videos/{session_id}.mp4"
        # Start camera recording
        # Record until feeding completes
        
    def upload_to_cloud(self, video_path):
        """Upload video to Google Drive"""
        # Google Drive API integration
        # Return cloud URL
        # Delete local file after upload
```

#### Storage Management
```python
# Video retention policy
MAX_LOCAL_VIDEOS = 10        # Keep 10 most recent locally
CLOUD_BACKUP_ENABLED = True  # Auto-upload to Google Drive
AUTO_DELETE_DAYS = 7         # Delete local files after 7 days
```

## ⚙️ Configuration Management

### 🔧 Dynamic Configuration

#### Configuration Structure
```python
class Config:
    # System Settings
    SENSOR_READ_INTERVAL = 3      # seconds
    FIREBASE_SYNC_INTERVAL = 5    # seconds
    WEBSOCKET_BROADCAST_INTERVAL = 2  # seconds
    
    # Feed Presets
    FEED_PRESETS = {
        "small": {
            "amount": 50,           # grams
            "actuator_up": 2,       # seconds
            "actuator_down": 2,     # seconds
            "auger_duration": 10,   # seconds
            "blower_duration": 8    # seconds
        },
        # ... more presets
    }
    
    # Auto-feed Scheduling
    AUTO_FEED_ENABLED = False
    AUTO_FEED_SCHEDULE = [
        {"time": "08:00", "preset": "medium", "enabled": True},
        {"time": "14:00", "preset": "small", "enabled": True},
        {"time": "18:00", "preset": "medium", "enabled": True}
    ]
    
    # Camera Settings
    CAMERA_WIDTH = 640
    CAMERA_HEIGHT = 480
    CAMERA_FPS = 30
```

#### Runtime Configuration Updates
```python
# Configuration can be updated via API
POST /api/control/config
{
    "sensor_read_interval": 5,
    "feed_presets": {
        "custom": {
            "amount": 75,
            "actuator_up": 2.5,
            "actuator_down": 2,
            "auger_duration": 15,
            "blower_duration": 12
        }
    }
}
```

## 🔧 Advanced Features

### 🕒 Auto-Feed Scheduler

#### Scheduler Implementation
```python
class ConfigurationManager:
    def start_auto_feed_scheduler(self):
        """Start background scheduling thread"""
        def scheduler_loop():
            while self.scheduler_running:
                current_time = datetime.now().strftime("%H:%M")
                
                for schedule_item in self.AUTO_FEED_SCHEDULE:
                    if (schedule_item["time"] == current_time and 
                        schedule_item["enabled"] and
                        not self.is_already_fed_today(schedule_item["time"])):
                        
                        # Execute scheduled feeding
                        self.execute_scheduled_feed(schedule_item)
                
                time.sleep(60)  # Check every minute
```

#### Schedule Configuration
```json
{
    "auto_feed_enabled": true,
    "schedule": [
        {
            "time": "08:00",
            "preset": "medium",
            "enabled": true,
            "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        },
        {
            "time": "18:00",
            "preset": "large",
            "enabled": true,
            "days": ["Saturday", "Sunday"]
        }
    ]
}
```

### 🔄 Error Recovery & Fault Tolerance

#### Arduino Reconnection
```python
class ArduinoManager:
    def auto_reconnect(self):
        """Automatic Arduino reconnection on failure"""
        while not self.connected:
            try:
                self.connect()
                self.logger.info("✅ Arduino reconnected successfully")
                break
            except Exception as e:
                self.logger.error(f"❌ Reconnection failed: {e}")
                time.sleep(self.ARDUINO_RECONNECT_INTERVAL)
```

#### Graceful Error Handling
```python
def handle_sensor_error(self, sensor_name, error):
    """Handle individual sensor failures gracefully"""
    # Log error
    self.logger.error(f"❌ Sensor {sensor_name} error: {error}")
    
    # Mark sensor as failed
    self.sensor_status[sensor_name] = "error"
    
    # Continue operation with remaining sensors
    # Send error notification to web clients
    self.broadcast_error_notification(sensor_name, error)
```

### 📊 Real-time Data Broadcasting

#### WebSocket Data Streaming
```python
class WebAPI:
    def broadcast_sensor_update(self):
        """Broadcast real-time sensor data to all connected clients"""
        sensor_data = self._get_realtime_data()
        self.socketio.emit('sensor_update', sensor_data)
        
    def broadcast_system_status(self):
        """Broadcast system status updates"""
        status = self._get_system_status()
        self.socketio.emit('system_status', status)
```

#### Client-side Integration
```javascript
// Web client receives real-time updates
socket.on('sensor_update', (data) => {
    updateDashboard(data);
    updateCharts(data);
    checkAlerts(data);
});
```

## 🐛 Troubleshooting

### 🔍 Common Issues

#### Arduino Connection Problems
```bash
# Check Arduino connection
ls /dev/tty* | grep -E "(USB|ACM)"

# Test serial communication
python3 -c "
import serial
ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=2)
ser.write(b'STATUS\n')
print(ser.readline())
ser.close()
"

# Check permissions
groups $USER  # Should include 'dialout'
```

#### Python Dependencies Issues
```bash
# Reinstall requirements
pip install --upgrade -r requirements.txt

# Check specific packages
python3 -c "import flask; print(flask.__version__)"
python3 -c "import serial; print(serial.__version__)"
python3 -c "import firebase_admin; print(firebase_admin.__version__)"
```

#### Firebase Connection Issues
```bash
# Verify Firebase credentials
ls -la serviceAccountKey.json
# Should exist and be readable

# Test Firebase connection
python3 -c "
import firebase_admin
from firebase_admin import credentials, db
cred = credentials.Certificate('serviceAccountKey.json')
firebase_admin.initialize_app(cred, {
    'databaseURL': 'YOUR_DATABASE_URL'
})
print('Firebase connected successfully')
"
```

#### Memory & Performance Issues
```bash
# Check system resources
free -h
df -h
top -p $(pgrep -f "python3 main.py")

# Monitor Python memory usage
python3 -c "
import psutil
import os
process = psutil.Process(os.getpid())
print(f'Memory: {process.memory_info().rss / 1024 / 1024:.2f} MB')
"
```

### 🛠️ Diagnostic Commands

#### System Health Check
```python
# Built-in health check endpoint
GET /api/health

# Returns comprehensive system status:
{
    "status": "healthy",
    "components": {
        "arduino": "connected",
        "firebase": "connected",
        "camera": "available",
        "websocket": "active"
    },
    "system": {
        "uptime": 86400,
        "memory_usage": "45.2%",
        "disk_usage": "12.8%",
        "cpu_usage": "23.1%"
    }
}
```

#### Log Analysis
```bash
# System logs
tail -f logs/system.log

# Sensor logs (daily)
tail -f logs/$(date +%Y-%m-%d)/sensor_log.txt

# Feed history
jq '.' logs/feed_history.json | tail -20

# Real-time monitoring
watch -n 1 "curl -s http://localhost:5000/api/health | jq '.'"
```

## 📈 Performance Optimization

### ⚡ System Tuning

#### Memory Optimization
```python
# Limit sensor data history
MAX_SENSOR_HISTORY = 1000  # Keep last 1000 readings per sensor

# Rotate log files
import logging.handlers
handler = logging.handlers.RotatingFileHandler(
    'logs/system.log', maxBytes=10*1024*1024, backupCount=5
)
```

#### Database Optimization
```python
# Batch Firebase updates
firebase_batch = []
# ... collect multiple updates
# Send batch update every 5 seconds instead of individual updates
```

#### Network Optimization
```python
# Compress WebSocket messages
from flask_socketio import emit
emit('sensor_update', data, compress=True)

# Throttle high-frequency updates
last_broadcast = 0
if time.time() - last_broadcast > BROADCAST_INTERVAL:
    broadcast_sensor_update()
    last_broadcast = time.time()
```

## 🔐 Security Considerations

### 🛡️ Security Features

#### Network Security
```python
# CORS configuration
CORS(app, origins=[
    "http://localhost:3000",      # Development
    "https://your-domain.com",    # Production
])

# Rate limiting (extensible)
from flask_limiter import Limiter
limiter = Limiter(key_func=get_remote_address)

@app.route('/api/feed')
@limiter.limit("10 per minute")  # Limit feed commands
def feed_control():
    # Feed control implementation
```

#### Data Protection
```bash
# Secure Firebase credentials
chmod 600 serviceAccountKey.json
chown pi:pi serviceAccountKey.json

# Encrypt sensitive configuration
# (Implementation depends on requirements)
```

#### Access Control
```python
# API key authentication (extensible)
def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if api_key != EXPECTED_API_KEY:
            return jsonify({'error': 'Invalid API key'}), 401
        return f(*args, **kwargs)
    return decorated_function
```

## 📚 API Documentation

### 🔄 Complete REST API Reference

#### Base URL: `http://pi-ip:5000/api`

#### Authentication
```http
# API Key (if enabled)
X-API-Key: your-api-key

# CORS Headers
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, PUT, DELETE
Access-Control-Allow-Headers: Content-Type, X-API-Key
```

#### Response Format
```json
{
    "success": true,
    "data": { ... },
    "error": null,
    "timestamp": "2024-03-21T10:30:00.000Z"
}
```

#### Error Handling
```json
{
    "success": false,
    "data": null,
    "error": {
        "code": "ARDUINO_NOT_CONNECTED",
        "message": "Arduino device is not connected",
        "details": "Check USB connection and restart service"
    },
    "timestamp": "2024-03-21T10:30:00.000Z"
}
```

## 🚀 Future Enhancements

### 🎯 Planned Features
- **Machine Learning**: Feeding pattern optimization based on fish behavior
- **Multi-Device Support**: Manage multiple fish feeders from single Pi
- **Advanced Analytics**: Predictive maintenance and feeding recommendations
- **Cloud Integration**: Complete cloud-native architecture option
- **Mobile App**: Dedicated mobile application for remote monitoring

### 🔧 Technical Improvements
- **Database Migration**: SQLite or PostgreSQL for better data management
- **Microservices**: Split components into independent services
- **Container Support**: Docker deployment for easy scaling
- **API Gateway**: Enhanced security and rate limiting
- **Message Queue**: Redis/RabbitMQ for better component communication

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📞 Support

For technical support and questions:
- **Issues**: Use GitHub Issues for bug reports and feature requests
- **Documentation**: Check the `fish-feeder-web/` README for web interface documentation  
- **Hardware**: Refer to the `fish-feeder-arduino/` README for Arduino setup

---

**🐟 Happy Fish Feeding! 🐟**
