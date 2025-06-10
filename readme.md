# 🐟 Fish Feeder IoT System

## 🎯 **Quick Start**

```bash
# รันระบบ Production
python start.py
```

**เว็บ Global Access**: https://fish-feeder-test-1.web.app

---

## 📂 **โครงสร้างโปรเจค**

```
📁 pi-mqtt-server/
├── 🚀 start.py                    # Main launcher
├── 📋 README.md                   # คู่มือหลัก
├── 📁 production/                 # ไฟล์ Production
│   ├── firebase_production_sync_fixed.py   # ระบบหลัก
│   ├── start_production_fixed.py           # Starter
│   ├── firebase-key.json                   # Firebase credentials
│   ├── requirements_firebase.txt           # Dependencies
│   └── env.example                         # Environment config
├── 📁 docs/                       # เอกสาร
│   ├── PRODUCTION_README.md                # คู่มือ Production
│   ├── FIREBASE_SETUP.md                   # คู่มือ Firebase
│   └── readme.md                           # เอกสารเดิม
└── 📁 tools/                      # เครื่องมือ Debug
    ├── check_firebase_data.py              # ตรวจสอบข้อมูล
    ├── fix_web_data.py                     # แก้ไขเว็บ
    └── test_production_demo.py             # Demo ระบบ
```

---

## 🔧 **การติดตั้ง**

### 1. **Install Dependencies:**
```bash
cd production/
pip install -r requirements_firebase.txt
```

### 2. **Download Firebase Key:**
- Firebase Console → Project Settings → Service accounts
- Generate new private key
- บันทึกเป็น `production/firebase-key.json`

### 3. **Configure Serial Port:**
```bash
# สร้าง production/.env
echo "SERIAL_PORT=COM3" > production/.env
echo "BAUD_RATE=9600" >> production/.env
```

---

## 🚀 **การใช้งาน**

### **Production Mode:**
```bash
python start.py
```

### **Manual Mode:**
```bash
cd production/
python start_production_fixed.py
```

### **Debug Tools:**
```bash
# ตรวจสอบข้อมูล Firebase
python tools/check_firebase_data.py

# แก้ไขเว็บ
python tools/fix_web_data.py

# Demo ระบบ
python tools/test_production_demo.py
```

---

## 📊 **System Architecture**

```
[Arduino Mega 2560] --Serial--> [Raspberry Pi] --Firebase--> [Global Web]
     Sensors             COM3      Python Service    Real-time   Users Worldwide
```

### **Sensors:**
- 🌡️ DHT22: Temperature & Humidity (2 units)
- 🌊 DS18B20: Water Temperature
- ⚖️ HX711: Load Cell (Feeder Weight)
- 🔋 Battery & Solar Monitoring
- 💧 Soil Moisture Sensor

### **Control:**
- ⚡ LED Control (R:1)
- 🌀 Fan Control (R:2)
- 🔴 All Off (R:0)

---

## 🌍 **Web Features**

**URL**: https://fish-feeder-test-1.web.app

- 📊 Real-time sensor dashboard
- 🎛️ Remote relay control
- 📈 Live data monitoring
- 📱 Mobile responsive
- 🔋 Battery status
- 🌡️ Environmental monitoring

---

## 📋 **Performance**

- **Sensor Updates**: Every 5 seconds
- **Command Response**: ~100ms
- **Global Access**: ~300ms via Firebase
- **Uptime**: 24/7 capable
- **Arduino Communication**: Direct serial, 9600 baud
- **JSON Format**: Fully supported

---

## 🛠️ **Troubleshooting**

### **Arduino Connection Issues:**
- Check USB cable
- Verify COM port in `.env`
- Ensure no other programs using serial port

### **Firebase Issues:**
- Verify `firebase-key.json` exists
- Check internet connection
- Confirm Firebase project active

### **Web Shows Offline:**
- Ensure production system running
- Check Firebase Database structure
- Verify Firebase rules allow read/write

---

## 📚 **Documentation**

- 📖 **Production Guide**: `docs/PRODUCTION_README.md`
- 🔥 **Firebase Setup**: `docs/FIREBASE_SETUP.md`
- 🛠️ **Original Docs**: `docs/readme.md`

---

## 💡 **Development**

### **Project Status:**
- ✅ Arduino Integration: 100%
- ✅ Firebase Sync: 100%
- ✅ Web Interface: 100%
- ✅ Global Access: 100%
- ✅ JSON Format: 100%

### **Recent Updates:**
- 🐛 Fixed Arduino JSON parsing
- 🔧 Improved error handling
- 📊 Enhanced web compatibility
- 🗂️ Organized file structure

---

**🚀 Ready for Production! 🌍** 