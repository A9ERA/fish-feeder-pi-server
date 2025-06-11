# 🐟 Fish Feeder Pi Controller v3.0

**Raspberry Pi Controller สำหรับระบบให้อาหารปลาอัตโนมัติ พร้อม Web App Integration และระบบกล้องแบบ Real-time**

## 📋 Overview

ระบบควบคุมหลักที่ทำงานบน Raspberry Pi 4 สำหรับการจัดการระบบให้อาหารปลาแบบ IoT พร้อมฟีเจอร์:

- 🔗 **Arduino Communication**: สื่อสารกับ Arduino Mega 2560 ผ่าน Serial USB
- 📹 **Live Camera Stream**: ระบบกล้องแบบ Real-time streaming + Photo capture
- ☁️ **Firebase Integration**: ซิงค์ข้อมูลกับ Cloud Database (Optional)
- 🌐 **Enhanced REST API**: Web API สำหรับ Web App integration
- 📊 **Feed Management**: ระบบจัดการการให้อาหารแบบสมบูรณ์
- 📈 **Statistics & History**: สถิติและประวัติการให้อาหาร
- 💾 **Offline Mode**: ทำงานได้แม้ไม่มี Internet

## 🌐 Web App Integration

ระบบนี้ออกแบบมาเพื่อทำงานร่วมกับ **Fish Feeder Web App**:
- **Live Demo**: https://fish-feeder-test-1.web.app
- **GitHub**: https://github.com/iamotakugot/fish-feeder-web
- **Frontend**: React 18.3.1 + TypeScript + Vite + HeroUI

## 🏗️ System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Arduino Mega   │USB │  Raspberry Pi   │WiFi│    Firebase     │
│  (Sensors &     │────│  (Controller)   │────│  (Cloud DB)     │
│   Actuators)    │    │                 │    │  [Optional]     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        ▲
                                │ Camera                 │
                                ▼                        │
                        ┌─────────────────┐              │
                        │   USB Camera    │              │
                        │ (Live Stream)   │              │
                        └─────────────────┘              │
                                                         │
                        ┌─────────────────┐              │
                        │   Web App       │              │
                        │ (React + TS)    │──────────────┘
                        └─────────────────┘
```

## 🔧 Hardware Requirements

### Raspberry Pi 4
- **Model**: Raspberry Pi 4 (4GB RAM recommended)
- **OS**: Raspberry Pi OS (Bullseye or newer)
- **Storage**: 32GB+ microSD card
- **Camera**: USB Webcam หรือ Pi Camera

### Arduino Mega 2560
- **Connection**: USB cable ต่อกับ Raspberry Pi
- **Sensors**: DHT22 (2x), DS18B20, HX711, ACS712, Soil sensor
- **Actuators**: Relay modules, Auger motor, Blower, Actuator

## 🚀 Installation

### 1. ติดตั้ง Python Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and required packages
sudo apt install python3 python3-pip python3-venv -y
sudo apt install libhdf5-dev libhdf5-serial-dev -y
sudo apt install libatlas-base-dev libjasper-dev -y

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python packages
pip install -r requirements.txt
```

### 2. Setup Firebase (Optional)

1. สร้าง Firebase Project ใน [Firebase Console](https://console.firebase.google.com/)
2. Enable Realtime Database
3. Download Service Account Key และบันทึกเป็น `serviceAccountKey.json`

### 3. เชื่อมต่อ Hardware

```bash
# เช็ค Arduino port
ls /dev/ttyUSB* /dev/ttyACM*

# เช็คกล้อง
lsusb | grep Camera

# ตั้งค่า permissions
sudo usermod -a -G dialout $USER
sudo usermod -a -G video $USER
sudo reboot
```

## ▶️ Running the System

### แบบ Manual

```bash
# Activate virtual environment
source venv/bin/activate

# Run the controller
python3 main.py
```

### แบบ Service (Auto-start)

```bash
# สร้าง service file
sudo nano /etc/systemd/system/fish-feeder.service
```

เพิ่มเนื้อหา:
```ini
[Unit]
Description=Fish Feeder Pi Controller v3.0
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/fish-feeder
ExecStart=/home/pi/fish-feeder/venv/bin/python main.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

```bash
# Enable และ start service
sudo systemctl daemon-reload
sudo systemctl enable fish-feeder.service
sudo systemctl start fish-feeder.service

# เช็คสถานะ
sudo systemctl status fish-feeder.service

# ดู logs
sudo journalctl -u fish-feeder.service -f
```

## 🌐 API Endpoints (Web App Compatible)

### System Health
```http
GET /api/health
```
Response:
```json
{
  "status": "ok",
  "serial_connected": true,
  "firebase_connected": true,
  "timestamp": "2024-01-01T12:00:00Z",
  "server_info": {
    "version": "3.0.0",
    "uptime_seconds": 3600
  },
  "sensors_available": ["DHT22_FEEDER", "HX711_FEEDER", "DS18B20_WATER_TEMP"]
}
```

### Sensor Data (All Sensors)
```http
GET /api/sensors
```
Response:
```json
{
  "status": "success",
  "timestamp": "2024-01-01T12:00:00Z",
  "data": {
    "DHT22_FEEDER": {
      "timestamp": "2024-01-01T12:00:00Z",
      "values": [
        {
          "type": "humidity",
          "value": 65.2,
          "unit": "%",
          "timestamp": "2024-01-01T12:00:00Z"
        }
      ]
    },
    "HX711_FEEDER": {
      "timestamp": "2024-01-01T12:00:00Z",
      "values": [
        {
          "type": "weight",
          "value": 1.25,
          "unit": "kg",
          "timestamp": "2024-01-01T12:00:00Z"
        }
      ]
    }
  },
  "arduino_connected": true
}
```

### Specific Sensor Data
```http
GET /api/sensors/HX711_FEEDER
```
Response:
```json
{
  "sensor_name": "HX711_FEEDER",
  "values": [
    {
      "type": "weight",
      "value": 1250.5,
      "unit": "grams",
      "timestamp": "2024-01-01T12:00:00Z"
    }
  ]
}
```

### Enhanced Feed Control
```http
POST /api/feed
```
**Request Body (Preset):**
```json
{
  "action": "medium"  // "small", "medium", "large", "xl"
}
```

**Request Body (Custom with Timing):**
```json
{
  "action": "custom",
  "amount": 100,
  "actuator_up": 3,
  "actuator_down": 2,
  "auger_duration": 20,
  "blower_duration": 15
}
```

**Response:**
```json
{
  "success": true,
  "message": "Feed command executed successfully",
  "feed_id": "feed_20240101_120000",
  "estimated_duration": 40,
  "timestamp": "2024-01-01T12:00:00Z",
  "photo_url": "/photos/photo_20240101_120000.jpg"
}
```

### Feed History
```http
GET /api/feed/history
```
Response:
```json
{
  "data": [
    {
      "feed_id": "feed_20240101_120000",
      "timestamp": "2024-01-01T12:00:00Z",
      "amount": 100,
      "type": "manual",
      "status": "completed",
      "video_url": "",
      "duration_seconds": 40,
      "device_timings": {
        "actuator_up": 3,
        "actuator_down": 2,
        "auger_duration": 20,
        "blower_duration": 15
      }
    }
  ]
}
```

### Feed Statistics
```http
GET /api/feed/statistics
```
Response:
```json
{
  "total_amount_today": 450,
  "total_feeds_today": 4,
  "average_per_feed": 112.5,
  "last_feed_time": "2024-01-01T12:00:00Z",
  "daily_target": 500,
  "target_achieved_percentage": 90.0
}
```

### Camera Controls
```http
GET /api/camera/stream
# Returns: multipart/x-mixed-replace MJPEG stream

GET /api/camera/status
POST /api/camera/photo
```

### Direct Arduino Commands
```http
POST /api/control/direct
Content-Type: application/json
{
  "command": "R:1"  # Any Arduino command (R:1, G:1, B:1, A:1, etc.)
}
```

## 📁 Project Structure

```
pi-mqtt-server/
├── main.py                 # 🎯 Main controller (ALL-IN-ONE)
├── requirements.txt        # 📦 Python dependencies
├── serviceAccountKey.json  # 🔑 Firebase credentials (optional)
├── README.md              # 📖 This documentation
├── .gitignore             # 🚫 Git ignore rules
└── logs/                  # 📊 System logs
    ├── system.log         # 📝 Main system log
    ├── feed_history.json  # 📈 Feed history database
    ├── YYYY-MM-DD/        # 📅 Daily sensor logs
    │   └── sensor_log.txt # 📊 Daily sensor data
    └── photos/            # 📸 Captured photos
        └── photo_*.jpg    # 🖼️ Feed session photos
```

## 🧩 System Components

### 1. ArduinoManager
- **Serial Communication**: USB connection กับ Arduino (Auto-detect port)
- **Feed Sequence Control**: ควบคุมลำดับการให้อาหารแบบสมบูรณ์
- **Auto-reconnect**: เชื่อมต่อใหม่เมื่อขาดการเชื่อมต่อ
- **Command Sending**: ส่งคำสั่งไปยัง Arduino แบบ real-time
- **Data Parsing**: แปลงข้อมูล JSON จาก Arduino

### 2. CameraManager
- **Live Streaming**: สตรีมวิดีโอแบบ Real-time (MJPEG)
- **Photo Capture**: ถ่ายรูปแบบ on-demand และ auto-capture
- **Threaded Processing**: ประมวลผล frame ใน background
- **Auto-resolution**: ปรับความละเอียดตาม config

### 3. FeedHistoryManager
- **Feed Recording**: บันทึกประวัติการให้อาหารทุกครั้ง
- **Statistics**: คำนวณสถิติรายวันและข้อมูลสรุป
- **JSON Database**: เก็บข้อมูลในไฟล์ JSON แบบ persistent
- **Device Timing**: บันทึกเวลาการทำงานของแต่ละอุปกรณ์

### 4. FirebaseManager (Optional)
- **Cloud Sync**: ซิงค์ข้อมูลกับ Firebase Realtime Database
- **Offline Mode**: ทำงานได้แม้ไม่มี Firebase connection
- **Remote Commands**: รับคำสั่งจาก Web App ผ่าน Firebase
- **Auto-retry**: พยายามเชื่อมต่อใหม่อัตโนมัติ

### 5. WebAPI (Flask)
- **REST Endpoints**: API ที่เข้ากันได้กับ Web App
- **CORS Support**: รองรับการเรียกจาก Web browser
- **Error Handling**: จัดการ error อย่างละเอียด
- **JSON Responses**: รูปแบบข้อมูลมาตรฐาน

## ⚙️ Configuration

### Feed Presets (ปรับได้ใน main.py)
```python
FEED_PRESETS = {
    "small": {
        "amount": 50,        # grams
        "actuator_up": 2,    # seconds
        "actuator_down": 2,  # seconds
        "auger_duration": 10,  # seconds
        "blower_duration": 8   # seconds
    },
    "medium": {
        "amount": 100,
        "actuator_up": 3,
        "actuator_down": 2,
        "auger_duration": 20,
        "blower_duration": 15
    },
    # ... large, xl
}
```

### System Config
```python
class Config:
    # Arduino
    ARDUINO_BAUDRATE = 115200
    ARDUINO_SCAN_PORTS = ["/dev/ttyUSB0", "/dev/ttyACM0"]  # Linux
    
    # Web Server
    WEB_HOST = "0.0.0.0"
    WEB_PORT = 5000
    
    # Camera
    CAMERA_INDEX = 0
    CAMERA_WIDTH = 640
    CAMERA_HEIGHT = 480
    CAMERA_FPS = 30
    
    # Timing
    SENSOR_READ_INTERVAL = 3      # seconds
    FIREBASE_SYNC_INTERVAL = 5    # seconds
```

## 🔍 Monitoring & Troubleshooting

### Log Files
```bash
# System logs
tail -f logs/system.log

# Daily sensor logs
tail -f logs/$(date +%Y-%m-%d)/sensor_log.txt

# Service logs
sudo journalctl -u fish-feeder.service -f

# Check system status
curl http://localhost:5000/api/health
```

### Common Issues

#### Arduino Not Connected
```bash
# Check USB devices
lsusb

# Check serial ports
ls -la /dev/tty*

# Check permissions
sudo usermod -a -G dialout $USER
sudo reboot
```

#### Camera Not Working
```bash
# List video devices
ls /dev/video*

# Test camera
sudo apt install cheese
cheese

# Check permissions
sudo usermod -a -G video $USER
```

#### Web App Connection Issues
```bash
# Test API endpoints
curl http://localhost:5000/api/health
curl http://localhost:5000/api/sensors

# Check if port is open
netstat -tlnp | grep :5000

# Check firewall
sudo ufw status
```

## 🌐 Web App Integration Guide

### 1. Web App Setup
Web App จะ fallback มาเรียก Pi Server API เมื่อ Firebase ไม่เชื่อมต่อ:

```javascript
// Web App config (fish-feeder-web)
const API_CONFIG = {
  BASE_URL: 'http://192.168.1.100:5000',  // Pi IP
  FALLBACK_ENABLED: true
}
```

### 2. Feed Control Integration
Web App ส่ง feed command พร้อม timing parameters:

```javascript
// Web App feed request
const feedData = {
  action: "custom",
  amount: 150,
  actuator_up: 3,
  actuator_down: 2,
  auger_duration: 25,
  blower_duration: 20
}

fetch('/api/feed', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(feedData)
})
```

### 3. Real-time Monitoring
```javascript
// Sensor data polling (Web App)
setInterval(() => {
  fetch('/api/sensors')
    .then(response => response.json())
    .then(data => updateSensorDisplay(data))
}, 3000)  // Every 3 seconds
```

## 📱 Mobile Access

- **Local Network**: `http://pi-ip:5000` (direct access)
- **Remote Access**: ใช้ VPN หรือ port forwarding
- **Web App**: https://fish-feeder-test-1.web.app (cloud-hosted)

## 🔒 Security

- ใช้ strong passwords สำหรับ Pi account
- ตั้งค่า firewall อย่างเหมาะสม
- อัพเดทระบบเป็นประจำ
- ใช้ VPN สำหรับ remote access

## 📞 Support

- **Web App GitHub**: https://github.com/iamotakugot/fish-feeder-web
- **Arduino Documentation**: `../fish-feeder-arduino/README.md`
- **API Documentation**: ดูจาก source code หรือ `/api/health`

## 📄 License

MIT License - ใช้งานได้อย่างอิสระ

---

**🐟 Happy Fish Feeding with Complete Integration! 🐟**
