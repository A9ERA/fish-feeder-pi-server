# 🚀 QUICK SETUP GUIDE

## ⚡ ติดตั้งเร็ว / Quick Install

```bash
# 1. Navigate to pi-mqtt-server directory
cd /path/to/pi-mqtt-server

# 2. Install enhanced dependencies
pip3 install -r requirements_enhanced.txt

# 3. Run complete setup
python3 setup_hybrid_storage.py
```

---

## 🌐 PageKite Setup (b65iee02.pagekite.me)

### ✅ คุณมี subdomain แล้ว! / You already have the subdomain!

```bash
# Setup PageKite with your subdomain
python3 pagekite_setup.py
```

**🔗 Your URL: `https://b65iee02.pagekite.me`**

### 🎮 การใช้งาน / Usage:

```bash
# Start tunnel
./start_pagekite.sh

# Check status  
./status_pagekite.sh

# Stop tunnel
./stop_pagekite.sh
```

### 📊 PageKite ไม่ต้องใส่ login code!
- ใช้งานผ่าน command line ได้เลย
- Free 2GB/month 
- ไม่ต้องสมัครหรือยืนยันเพิ่ม

---

## 🗂️ Google Drive Setup (200GB)

### 📋 ขั้นตอน / Steps:

```bash
# Run Google Drive setup wizard
python3 google_drive_setup.py
```

### 🔑 สิ่งที่ต้องทำ / What you need:

1. **Google Cloud Console**: https://console.cloud.google.com/
2. **Create Project**: "Fish-Feeder-Storage"
3. **Enable API**: Google Drive API  
4. **Create Credentials**: OAuth 2.0 (Desktop app)
5. **Download JSON**: เป็น `google_drive_credentials.json`

### ✅ ไม่ต้องใส่อะไรเพิ่ม!
- ไม่ต้อง API key เพิ่ม
- ไม่ต้อง Service Account
- ใช้ OAuth flow ธรรมดา

---

## 🎯 Complete Setup Commands

```bash
# 1. Install dependencies
pip3 install -r requirements_enhanced.txt

# 2. Setup storage system  
python3 setup_hybrid_storage.py

# 3. Setup PageKite (b65iee02.pagekite.me)
python3 pagekite_setup.py

# 4. Setup Google Drive (200GB)
python3 google_drive_setup.py

# 5. Integrate with main.py
python3 integrate_hybrid_storage.py

# 6. Start the system
./start_fish_feeder.sh
```

---

## 📊 System Overview

### 💾 Storage Strategy:
```
📹 Pi Local (128GB) → 🔥 Firebase (5GB) → 🗂️ Google Drive (200GB)
    ↑ Live Recording    ↑ Immediate Upload   ↑ Long-term Archive
    🗑️ 7 days cleanup    🔄 24h migration    📦 Permanent storage
```

### 🌐 Access URLs:
- **Local**: `http://localhost:5000`
- **Web App**: `https://fish-feeder-test-1.web.app`
- **PageKite**: `https://b65iee02.pagekite.me`

### 🎮 New API Endpoints:
```bash
# Video Recording
POST /api/camera/record/start
POST /api/camera/record/stop

# PageKite Control  
POST /api/pagekite/start
POST /api/pagekite/stop
GET  /api/pagekite/status

# Storage Management
GET  /api/storage/status
POST /api/storage/migrate
```

---

## 🔧 Configuration Files

### 📁 Files you'll have:
- `storage_config.json` - Main configuration
- `google_drive_credentials.json` - Google Drive OAuth
- `google_drive_token.json` - Auto-generated token
- `serviceAccountKey.json` - Firebase credentials (existing)

### 🎯 Default Settings:
```json
{
  "local_storage": {
    "base_path": "/home/pi/fish_feeder_data",
    "max_size_gb": 100,
    "video_retention_days": 7
  },
  "firebase": {
    "enabled": true,
    "bucket_name": "fish-feeder-test-1.firebasestorage.app"
  },
  "google_drive": {
    "enabled": true,
    "folder_name": "Fish Feeder Videos"
  },
  "pagekite": {
    "enabled": true,
    "subdomain": "b65iee02",
    "backend_port": 5000
  }
}
```

---

## ✅ Verification Steps

### 1. Check PageKite:
```bash
./status_pagekite.sh
# Should show: ✅ PageKite is running
```

### 2. Check Google Drive:
```bash
python3 -c "from smart_hybrid_storage import SmartHybridStorage; s=SmartHybridStorage(); print('✅ Google Drive OK' if s.config['google_drive']['enabled'] else '❌ Not configured')"
```

### 3. Check Storage System:
```bash
curl http://localhost:5000/api/storage/status
```

### 4. Test Video Recording:
```bash
# Start recording
curl -X POST http://localhost:5000/api/camera/record/start

# Stop and upload  
curl -X POST http://localhost:5000/api/camera/record/stop
```

---

## 🎉 Ready to Go!

### 🐟 Fish Feeding with Video:
1. Feed fish via Web App: `https://fish-feeder-test-1.web.app`
2. Video automatically recorded & uploaded
3. View videos in Firebase (immediate)
4. Long-term storage in Google Drive

### 🌐 External Access:
1. Start PageKite: `./start_pagekite.sh`
2. Access from anywhere: `https://b65iee02.pagekite.me`
3. Control fish feeder remotely!

### 💾 Storage Monitoring:
- **Local**: `df -h /home/pi/fish_feeder_data`
- **Firebase**: Check Firebase Console
- **Google Drive**: https://drive.google.com/drive/folders/

---

**🎯 Total Storage: 128GB + 5GB + 200GB = 333GB effective capacity!** 