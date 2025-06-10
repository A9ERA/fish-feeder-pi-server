# 🚀 Fish Feeder IoT - Production System

## 📁 โครงสร้างโฟลเดอร์

```
production/
├── 🚀 start_production_fixed.py     # Main startup script
├── 🔄 start_complete_system.py      # Complete system runner
├── 🔥 firebase_production_sync_fixed.py  # Firebase sync service
├── 📁 api/
│   └── flask_api_server.py          # Flask API server (สำรอง)
├── 📁 config/
│   ├── firebase-key.json            # Firebase credentials
│   ├── .env                         # Environment variables
│   ├── env.example                  # Environment template
│   └── requirements_firebase.txt    # Python dependencies
└── 📁 scripts/                      # Utility scripts
```

## 🏃‍♂️ วิธีรันระบบ

### เริ่มระบบครบเซ็ต
```bash
python start_production_fixed.py
```

### รันเฉพาะ Firebase Sync
```bash
python firebase_production_sync_fixed.py
```

### รันเฉพาะ API Server
```bash
python api/flask_api_server.py
```

## ⚙️ การตั้งค่า

### 1. Environment Variables
```bash
# config/.env
SERIAL_PORT=COM3
BAUD_RATE=9600
```

### 2. Firebase Configuration
- วางไฟล์ `firebase-key.json` ในโฟลเดอร์ `config/`
- ดาวน์โหลดจาก Firebase Console > Project Settings > Service accounts

### 3. Python Dependencies
```bash
pip install -r config/requirements_firebase.txt
```

## 🌐 Web Application

เว็บแอปพลิเคชันเชื่อมต่อ Firebase โดยตรง:
- 🌍 URL: https://fish-feeder-test-1.web.app
- 📊 ข้อมูล Sensors แบบ Real-time
- 🎛️ ควบคุม Relays ผ่าน Firebase Commands
- ⚡ Response time < 100ms

## 📡 API Endpoints (สำรอง)

```
GET  /health              - Health check
GET  /api/sensors         - All sensor data
GET  /api/relay/status    - Relay status
POST /api/relay/led       - Control LED
POST /api/relay/fan       - Control Fan
POST /api/control/direct  - Direct Arduino commands
```

## 🔧 Troubleshooting

### Arduino ไม่เชื่อมต่อ
1. ตรวจสอบ COM port ใน `config/.env`
2. ตรวจสอบสาย USB
3. รีสตาร์ท Arduino

### Firebase ไม่เชื่อมต่อ
1. ตรวจสอบ `config/firebase-key.json`
2. ตรวจสอบ internet connection
3. ตรวจสอบ Firebase project settings

### เว็บไม่แสดงข้อมูล
1. ตรวจสอบ Firebase database rules
2. ตรวจสอบ web app permissions
3. ลอง refresh หน้าเว็บ

## 📝 Log Files

ระบบจะแสดง log แบบ real-time:
- `[FIREBASE]` - Firebase sync logs
- `[API]` - API server logs
- Sensor data updates ทุก 5 วินาทีี
- Command execution logs

## 🛑 การหยุดระบบ

กด `Ctrl+C` เพื่อหยุดระบบอย่างปลอดภัย 