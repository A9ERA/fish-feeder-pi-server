# Pi MQTT Server - Fish Feeder Project

A Raspberry Pi server application for managing sensor data, device control, and Firebase integration with MQTT communication.

## 📋 Features

- **🌡️ Sensor Data Management**: Real-time sensor data collection and storage
- **🔥 Firebase Integration**: Cloud data synchronization
- **⚙️ Device Control**: Remote control of blower and actuator motor
- **📹 Video Streaming**: Live camera feed and recording
- **🌐 RESTful API**: Complete API endpoints for web integration
- **📡 Serial Communication**: Arduino/microcontroller communication
- **🔧 MQTT Support**: IoT device communication protocol

## 🚀 Quick Start

### Prerequisites
- Raspberry Pi (3B+ or later recommended)
- Python 3.7+
- Camera module (optional)
- Arduino/microcontroller with sensors

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/A9ERA/pi-mqtt-server.git
   cd pi-mqtt-server
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp env.example .env
   # Edit .env with your Firebase credentials
   ```

4. **Run the server**
   ```bash
   python main.py
   ```

## ⚙️ Configuration

### Firebase Setup
1. Create a Firebase project at [console.firebase.google.com](https://console.firebase.google.com)
2. Generate Admin SDK credentials (JSON file)
3. Place the JSON file in project root
4. Update `.env` file:
   ```
   FIREBASE_ADMIN_SDK_PATH=your-firebase-admin-sdk-file.json
   FIREBASE_DATABASE_URL=https://your-project-default-rtdb.firebaseio.com/
   FIREBASE_PROJECT_ID=your-project-id
   ```

### MQTT Setup (Mosquitto)
```bash
sudo apt update
sudo apt install -y mosquitto mosquitto-clients
sudo systemctl enable mosquitto
sudo systemctl start mosquitto
```

## 🧪 System Testing & Verification

### 🔍 Health Check
Test basic server functionality:
```bash
curl http://localhost:5000/health
```
Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "services": {
    "api": "running",
    "firebase": "connected",
    "serial": "connected"
  }
}
```

### 📊 Sensor Data Testing

1. **Check available sensors**
   ```bash
   curl http://localhost:5000/api/sensors
   ```

2. **Get specific sensor data**
   ```bash
   curl http://localhost:5000/api/sensors/temperature
   ```

3. **Test Firebase sync**
   ```bash
   curl -X POST http://localhost:5000/api/sensors/sync
   ```

### 🎛️ Device Control Testing

1. **Test blower control**
   ```bash
   # Turn on blower
   curl -X POST http://localhost:5000/api/control/blower \
     -H "Content-Type: application/json" \
     -d '{"action": "on", "duration": 5}'
   
   # Turn off blower
   curl -X POST http://localhost:5000/api/control/blower \
     -H "Content-Type: application/json" \
     -d '{"action": "off"}'
   ```

2. **Test actuator motor**
   ```bash
   # Move actuator
   curl -X POST http://localhost:5000/api/control/actuator \
     -H "Content-Type: application/json" \
     -d '{"action": "move", "position": 90}'
   ```

### 📹 Camera Testing

1. **Take a photo**
   ```bash
   curl -X POST http://localhost:5000/api/camera/photo
   ```

2. **Start video recording**
   ```bash
   curl -X POST http://localhost:5000/api/camera/record/start
   ```

3. **Stop recording**
   ```bash
   curl -X POST http://localhost:5000/api/camera/record/stop
   ```

### 📡 Serial Communication Testing

Monitor serial communication:
```bash
screen /dev/ttyUSB0 9600
```

Or use built-in serial monitor:
```bash
curl http://localhost:5000/api/serial/status
```

## 🔧 Troubleshooting

### Common Issues

**1. Serial port not found**
```bash
# Check available ports
ls /dev/tty*
# Check permissions
sudo usermod -a -G dialout $USER
# Restart required after group change
```

**2. Firebase connection failed**
- Verify JSON credentials file path
- Check internet connectivity
- Validate Firebase project settings

**3. Camera not working**
```bash
# Enable camera interface
sudo raspi-config
# Select: Interface Options > Camera > Enable
```

**4. Permission denied errors**
```bash
# Fix file permissions
chmod +x main.py
# Or run with sudo for hardware access
sudo python main.py
```

### 📊 System Monitoring

**Monitor logs**
```bash
tail -f /var/log/pi-server.log
```

**Check system resources**
```bash
# CPU and memory usage
htop

# Disk space
df -h

# Network connections
netstat -tulpn | grep :5000
```

## 🧪 Automated Testing

Run the test suite:
```bash
# Run all tests
python -m pytest test/

# Run specific test
python -m pytest test/test_api.py

# Run with coverage
python -m pytest --cov=src test/
```

## 📁 Project Structure

```
pi-mqtt-server/
├── src/
│   ├── config/              # Configuration files
│   ├── services/            # Core services
│   │   ├── api_service.py   # Flask API server
│   │   ├── firebase_service.py  # Firebase integration
│   │   ├── serial_service.py    # Arduino communication
│   │   └── camera_service.py    # Camera operations
│   ├── data/               # Local data storage
│   ├── templates/          # HTML templates
│   └── utils/              # Utility functions
├── test/                   # Test files
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
├── .env.example           # Environment template
└── README.md              # This file
```

## 🌐 API Reference

### Sensor Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/sensors` | List all sensors |
| GET | `/api/sensors/<name>` | Get sensor data |
| POST | `/api/sensors/sync` | Sync to Firebase |

### Control Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/control/blower` | Control blower device |
| POST | `/api/control/actuator` | Control actuator motor |

### Camera Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/camera/video_feed` | Live video stream |
| POST | `/api/camera/photo` | Take photo |
| POST | `/api/camera/record/start` | Start recording |
| POST | `/api/camera/record/stop` | Stop recording |

## 🔒 Security Notes

- Change default ports in production
- Use HTTPS for external access
- Implement API authentication
- Regularly update dependencies
- Monitor system logs

## 🌍 Remote Access Setup

### Using ngrok
```bash
# Install ngrok
sudo apt install unzip
wget https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-linux-arm.zip
unzip ngrok-stable-linux-arm.zip
sudo mv ngrok /usr/local/bin

# Setup authentication
ngrok config add-authtoken <your-token>

# Expose local server
ngrok http 5000
```

### Firewall Configuration
```bash
# Open port 5000
sudo ufw allow 5000
sudo ufw enable
```

## 📞 Support

- **Issues**: Report bugs on GitHub Issues
- **Documentation**: Check `/docs` folder for detailed guides
- **Contact**: [Project Repository](https://github.com/A9ERA/pi-mqtt-server)

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Last Updated**: 2024-01-01  
**Version**: 1.0.0