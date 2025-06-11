# 🚀 คู่มือ Deploy Fish Feeder ไปยัง Raspberry Pi

## 📋 สิ่งที่ต้องเตรียมก่อน Deploy

### 1. Raspberry Pi Setup
- ✅ Raspberry Pi พร้อม Raspberry Pi OS
- ✅ เชื่อมต่อ Internet 
- ✅ SSH เปิดใช้งาน (`sudo systemctl enable ssh`)
- ✅ Camera module เชื่อมต่อแล้ว
- ✅ หน่วยความจำ 128GB+ สำหรับเก็บวิดีโอ

### 2. Network Setup
- ✅ Pi และคอมพิวเตอร์อยู่ network เดียวกัน
- ✅ รู้ IP address หรือใช้ `raspberrypi.local`
- ✅ สามารถ SSH ได้โดยไม่ต้องใส่รหัสผ่าน (แนะนำ)

---

## 🎯 วิธี Deploy แบบ One-Click (แนะนำ)

### วิธีที่ 1: Auto Deploy Script
```bash
# รันคำสั่งเดียวจบ!
python3 one_click_deploy.py
```

**ระบบจะทำอะไร:**
1. 🔍 ตรวจสอบไฟล์ที่จำเป็น
2. 📡 ทดสอบการเชื่อมต่อ Pi
3. 📦 Copy ไฟล์ทั้งหมดไป Pi
4. 🤖 Install dependencies อัตโนมัติ
5. ⚙️ Setup systemd service
6. ✅ พร้อมใช้งาน!

---

## 🛠️ วิธี Deploy แบบ Manual

### Step 1: Copy Files ไป Pi
```bash
# ใช้ deploy script
chmod +x deploy_to_pi.sh
./deploy_to_pi.sh
```

### Step 2: SSH เข้า Pi
```bash
ssh pi@raspberrypi.local
cd /home/pi/pi-mqtt-server
```

### Step 3: Run Auto Setup
```bash
chmod +x auto_setup_pi.sh
./auto_setup_pi.sh
```

### Step 4: Setup Google Drive OAuth
```bash
python3 google_drive_setup.py
```

### Step 5: Test System
```bash
python3 main.py
```

---

## 🔧 การตั้งค่า Auto-Start

### Enable Auto-Start เมื่อ Boot
```bash
sudo systemctl enable fish-feeder
sudo systemctl start fish-feeder
```

### ตรวจสอบสถานะ
```bash
sudo systemctl status fish-feeder
```

### ดู Logs
```bash
sudo journalctl -u fish-feeder -f
```

---

## 🌐 การใช้งาน PageKite (External Access)

### เริ่ม PageKite Tunnel
```bash
./start_pagekite.sh
```

### ตรวจสอบสถานะ
```bash
./status_pagekite.sh
```

### หยุด Tunnel
```bash
./stop_pagekite.sh
```

---

## 📱 URLs สำหรับเข้าถึงระบบ

| Service | URL | หมายเหตุ |
|---------|-----|----------|
| **Web App** | https://fish-feeder-test-1.web.app | หลัก Control Panel |
| **Local Pi** | http://localhost:5000 | เข้าจาก Pi โดยตรง |
| **PageKite** | https://b65iee02.pagekite.me | External access |

---

## 💾 ระบบ Storage

### การทำงานของ Storage System
```
📹 Video Recording → Pi Local (128GB)
                ↓
📤 Auto Upload → Firebase Storage (5GB) 
                ↓ (หลัง 24 ชม.)
☁️ Long-term → Google Drive (200GB)
                ↓ (หลัง 7 วัน)
🗑️ Cleanup → ลบจาก Pi Local
```

### สถิติ Storage
- **Pi Local**: 128GB (เก็บวิดีโอล่าสุด)
- **Firebase**: 5GB (upload ทันที)  
- **Google Drive**: 200GB (archive ระยะยาว)
- **รวม**: 333GB ความจุเก็บข้อมูล

---

## 🎮 คำสั่งควบคุม

### ควบคุมระบบหลัก
```bash
# เริ่มระบบ
python3 main.py

# เริ่มแบบ background
sudo systemctl start fish-feeder

# หยุดระบบ
sudo systemctl stop fish-feeder

# รีสตาร์ท
sudo systemctl restart fish-feeder
```

### ควบคุม PageKite
```bash
# เริ่ม tunnel
./start_pagekite.sh

# ดูสถานะ
./status_pagekite.sh

# หยุด tunnel  
./stop_pagekite.sh
```

### ควบคุม Video Recording
```bash
# ผ่าน API calls หรือ Web Interface
curl -X POST http://localhost:5000/api/camera/record/start
curl -X POST http://localhost:5000/api/camera/record/stop
```

---

## 🚨 การแก้ไขปัญหา

### ถ้า Deploy ไม่สำเร็จ
```bash
# ตรวจสอบการเชื่อมต่อ
ping raspberrypi.local

# ตรวจสอบ SSH
ssh pi@raspberrypi.local

# ลอง deploy ใหม่
python3 one_click_deploy.py
```

### ถ้า Google Drive ไม่ทำงาน
```bash
# Setup OAuth ใหม่
python3 google_drive_setup.py

# ทดสอบ credentials
python3 test_google_drive.py
```

### ถ้า PageKite ไม่ทำงาน
```bash
# ตรวจสอบ installation
pip3 install pagekite

# ทดสอบ connection
./status_pagekite.sh
```

### ถ้า Video Recording มีปัญหา
```bash
# ตรวจสอบ camera
raspistill -o test.jpg

# ตรวจสอบ permissions
ls -la /home/pi/fish_feeder_data/

# แก้ไข permissions
sudo chown -R pi:pi /home/pi/fish_feeder_data/
```

---

## 📞 สถานการณ์ฉุกเฉิน

### รีสตาร์ทระบบทั้งหมด
```bash
sudo systemctl stop fish-feeder
./stop_pagekite.sh
sudo reboot
```

### การ Reset ระบบ
```bash
# หยุดทุกอย่าง
sudo systemctl stop fish-feeder
sudo systemctl disable fish-feeder

# ลบ service
sudo rm /etc/systemd/system/fish-feeder.service
sudo systemctl daemon-reload

# Deploy ใหม่
python3 one_click_deploy.py
```

---

## 🎯 เสร็จแล้ว! คุณจะได้:

✅ **ระบบให้อาหารปลาอัตโนมัติ** พร้อม video recording  
✅ **Smart Storage System** 333GB ความจุรวม  
✅ **External Access** ผ่าน PageKite tunnel  
✅ **Auto-start** เมื่อ Pi เปิดเครื่อง  
✅ **Web Control Panel** บนมือถือและคอมพิวเตอร์  
✅ **Cloud Backup** Firebase + Google Drive  

🎉 **สนุกกับการให้อาหารปลาแบบสมาร์ท!** 🐟📹 