# 🐟 Fish Feeder Pi Controller - Complete IoT System

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.3.3-green)](https://flask.palletsprojects.com)
[![Firebase](https://img.shields.io/badge/Firebase-Realtime%20DB-orange)](https://firebase.google.com)
[![Arduino](https://img.shields.io/badge/Arduino-Compatible-red)](https://arduino.cc)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

> **Advanced Raspberry Pi controller for Arduino-based automated fish feeding system with real-time monitoring, IoT integration, and comprehensive sensor analytics.**

## 🚀 **What's New in This Version**

### ✅ **Enhanced Sensor Data Parsing**
- **Complete sensor coverage** - All Arduino sensors now properly parsed
- **Standardized data format** - Consistent value/unit/timestamp structure
- **Temperature & Humidity** - DHT22 sensors fully supported
- **System Health Monitoring** - Real-time status validation

### ✅ **Improved Architecture**
- **High-performance Arduino communication** (115200 baud)
- **Real-time WebSocket updates** (2-second intervals)
- **Firebase Realtime Database** sync (5-second intervals)
- **Comprehensive error handling** with graceful fallbacks

---

## 📋 **System Overview**

```
📱 Arduino Mega 2560 → 🔌 USB/Serial → 🥧 Raspberry Pi → 🔥 Firebase → 🌐 Web App
```

### **Key Components:**
- **Arduino Mega 2560** - Sensor controller with optimized JSON output
- **Raspberry Pi** - Main server with Flask API and real-time processing
- **Firebase Realtime DB** - Cloud storage for sensor data and configuration
- **Web Application** - React/Vue.js dashboard with live monitoring

---

## 🔧 **Quick Setup**

### **1. Installation**
```bash
# Clone repository
git clone https://github.com/your-repo/fish-feeder-pi-controller.git
cd fish-feeder-pi-controller

# Install dependencies
pip install -r requirements.txt

# Setup Firebase credentials
cp serviceAccountKey.json.example serviceAccountKey.json
# Edit with your Firebase credentials
```

### **2. Configuration**
```bash
# Configure system
cp config/storage_config.json.example config/storage_config.json
# Edit configuration as needed

# Test Arduino connection
python -c "from main import ArduinoManager; import logging; am = ArduinoManager(logging.getLogger()); print('Arduino found!' if am.find_arduino() else 'Arduino not found')"
```

### **3. Run Server**
```bash
# Start the main server
python main.py

# Server will be available at:
# Web Interface: http://localhost:5000
# API Endpoints: http://localhost:5000/api/*
# WebSocket: ws://localhost:5000
```

---

## 📊 **Sensor Data & API**

### **Complete Sensor Coverage:**

| Sensor | Arduino Key | API Output | Status |
|--------|-------------|------------|--------|
| Battery Voltage | `bat_v` | `BATTERY_STATUS.voltage` | ✅ |
| Battery Current | `bat_i` | `BATTERY_STATUS.current` | ✅ |
| Solar Voltage | `sol_v` | `SOLAR_VOLTAGE.voltage` | ✅ |
| Solar Current | `sol_i` | `SOLAR_CURRENT.current` | ✅ |
| Feed Temperature | `feed_temp` | `FEED_TEMPERATURE.temperature` | ✅ |
| Control Temperature | `ctrl_temp` | `CONTROL_TEMPERATURE.temperature` | ✅ |
| Feed Humidity | `feed_hum` | `FEED_HUMIDITY.humidity` | ✅ |
| Control Humidity | `ctrl_hum` | `CONTROL_HUMIDITY.humidity` | ✅ |
| Weight Sensor | `weight` | `WEIGHT.weight` | ✅ |
| Soil Moisture | `soil` | `SOIL_MOISTURE.moisture` | ✅ |

### **API Example Response:**
```json
{
  "timestamp": "2025-12-06T14:30:00.000Z",
  "arduino_connected": true,
  "BATTERY_STATUS": {
    "voltage": {"value": 11.89, "unit": "V", "timestamp": "2025-12-06T14:30:00.000Z"},
    "current": {"value": 2.10, "unit": "A", "timestamp": "2025-12-06T14:30:00.000Z"},
    "soc": {"value": 78.0, "unit": "%", "timestamp": "2025-12-06T14:30:00.000Z"}
  },
  "FEED_TEMPERATURE": {
    "temperature": {"value": 25.3, "unit": "°C", "timestamp": "2025-12-06T14:30:00.000Z"}
  }
}
```

---

## 🎮 **Control Commands**

### **Feed Control**
```bash
# API: POST /api/feed
curl -X POST http://localhost:5000/api/feed \
  -H "Content-Type: application/json" \
  -d '{"action": "medium", "amount": 100}'

# Arduino Command: G:20 (auger 20 seconds)
```

### **Device Control**
```bash
# Blower Control
curl -X POST http://localhost:5000/api/control/blower \
  -d '{"action": "start", "speed": 255}'

# Actuator Control  
curl -X POST http://localhost:5000/api/control/actuator \
  -d '{"action": "up", "duration": 3.0}'

# Direct Arduino Command
curl -X POST http://localhost:5000/api/control/direct \
  -d '{"command": "R:1"}'  # LED on
```

---

## 🌐 **Real-time Features**

### **WebSocket Events**
```javascript
// Connect to WebSocket
const socket = io('http://localhost:5000');

// Listen for real-time sensor updates
socket.on('sensor_update', (data) => {
  console.log('Live sensor data:', data);
});

// Request system status
socket.emit('request_system_status');
```

### **Firebase Integration**
- **Real-time sync** every 5 seconds
- **Cloud storage** for sensor history
- **Cross-platform access** for multiple devices
- **Offline resilience** with local backup

---

## 📁 **Project Structure**

```
📁 pi-mqtt-server/
├── 📄 main.py                    # Main Flask server & Arduino manager
├── 📄 sensor_history_manager.py  # Historical data storage & analytics
├── 📄 serviceAccountKey.json     # Firebase credentials
├── 📄 requirements.txt           # Python dependencies
├── 📄 API_REFERENCE.md          # Complete API documentation
├── 📄 WEB_APP_INTEGRATION.md    # Web app integration guide
├── 📄 UPGRADE_SUMMARY.md        # Recent improvements summary
├── 📁 config/                   # Configuration files
│   ├── 📄 storage_config.json   # Storage settings
│   └── 📄 google_drive_credentials.json
├── 📁 data/                     # Local sensor data storage
│   └── 📁 sensor_history/
├── 📁 logs/                     # System & sensor logs
│   ├── 📄 system.log
│   └── 📁 2025-06-12/
└── 📁 docs/                     # Complete documentation
    ├── 📄 FINAL_STATUS_v2.0.0.md
    ├── 📄 DEPLOY_INSTRUCTIONS.md
    └── 📄 SETUP_COMPLETE.md
```

---

## ⚡ **Performance & Reliability**

### **Optimized Communication**
- **115200 baud** Arduino serial connection
- **1ms main loop** on Arduino for real-time response
- **Non-blocking operations** with threading
- **Smart error recovery** and reconnection

### **Data Management**
- **128GB Pi storage** optimization
- **Intelligent data retention** (30 days raw, 1 year hourly, 5 years daily)
- **Background data compression** for long-term storage
- **Firebase cloud backup** for data safety

### **System Monitoring**
- **Real-time health checks** for all components
- **Battery SOC calculation** for Li-ion 12V 12AH
- **Solar panel efficiency** monitoring
- **System temperature** protection

---

## 🔧 **Configuration Options**

### **Timing Settings**
```json
{
  "sensor_read_interval": 3,
  "firebase_sync_interval": 5,
  "websocket_broadcast_interval": 2
}
```

### **Feed Presets**
```json
{
  "small": {"amount": 50, "auger_duration": 10},
  "medium": {"amount": 100, "auger_duration": 20},
  "large": {"amount": 200, "auger_duration": 40},
  "xl": {"amount": 1000, "auger_duration": 120}
}
```

### **Auto-Feed Schedule**
```json
{
  "auto_feed_enabled": true,
  "auto_feed_schedule": [
    {"time": "08:00", "preset": "medium", "enabled": true},
    {"time": "14:00", "preset": "small", "enabled": true},
    {"time": "18:00", "preset": "medium", "enabled": true}
  ]
}
```

---

## 🛠️ **Development**

### **Testing**
```bash
# Test Arduino connection
python -c "import main; main.test_arduino_connection()"

# Test Firebase connection
python -c "import main; main.test_firebase_connection()"

# Run sensor data test
python -c "import main; main.test_sensor_parsing()"
```

### **Debugging**
```bash
# Enable debug mode
export FLASK_DEBUG=1
python main.py

# View real-time logs
tail -f logs/system.log

# Monitor sensor data
tail -f logs/2025-06-12/sensor_log.txt
```

---

## 📖 **Documentation**

- 📄 **[API Reference](API_REFERENCE.md)** - Complete REST API documentation
- 📄 **[Web App Integration](WEB_APP_INTEGRATION.md)** - Frontend integration guide
- 📄 **[Upgrade Summary](UPGRADE_SUMMARY.md)** - Recent improvements details
- 📄 **[Project Structure](PROJECT_STRUCTURE.md)** - File organization guide

---

## 🚀 **Deployment**

### **Production Setup**
```bash
# Install as systemd service
sudo cp scripts/fish-feeder.service /etc/systemd/system/
sudo systemctl enable fish-feeder
sudo systemctl start fish-feeder

# Check status
sudo systemctl status fish-feeder
```

### **Web Server Integration**
```bash
# Nginx configuration
sudo cp config/nginx.conf /etc/nginx/sites-available/fish-feeder
sudo ln -s /etc/nginx/sites-available/fish-feeder /etc/nginx/sites-enabled/
sudo systemctl reload nginx
```

---

## 🌟 **Features**

- ✅ **Real-time sensor monitoring** with WebSocket updates
- ✅ **Automated feeding system** with customizable presets
- ✅ **Battery & solar monitoring** with efficiency calculations
- ✅ **Temperature & humidity control** with automatic fan management
- ✅ **Weight-based feeding** with precision load cell
- ✅ **Camera integration** for feeding verification
- ✅ **Firebase cloud sync** for remote access
- ✅ **Historical data analytics** with trend analysis
- ✅ **RESTful API** for third-party integration
- ✅ **Responsive web interface** for all devices

---

## 📞 **Support & Contributing**

### **Getting Help**
- 📧 Create an issue on GitHub
- 📚 Check the [documentation](docs/)
- 💬 Join our community discussions

### **Contributing**
1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

---

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🎯 **System Requirements**

- **Raspberry Pi 3B+** or newer
- **Arduino Mega 2560** or compatible
- **Python 3.8+**
- **Node.js 16+** (for web app)
- **Firebase project** with Realtime Database
- **8GB+ microSD card** (16GB+ recommended)

---

## 🔗 **Related Projects**

- [Fish Feeder Arduino Code](../fish-feeder-arduino/) - Arduino firmware
- [Fish Feeder Web App](../fish-feeder-web/) - React/Vue.js frontend
- [Mobile App](../fish-feeder-mobile/) - React Native mobile application

---

**⭐ If this project helps you, please give it a star!**
