# Feeder Video Recording System

## 📖 ภาพรวม
ระบบจะทำการบันทึกวิดีโอโดยอัตโนมัติเมื่อเริ่มกระบวนการป้อนปลา (Feeder Service)

## 🎬 การทำงาน

### การเริ่มบันทึก
- เมื่อเรียก `feeder_service.start()` ระบบจะเริ่มบันทึกวิดีโออัตโนมัติ
- ใช้กล้อง Raspberry Pi Camera Module
- บันทึกตลอดกระบวนการป้อนปลา (12+ วินาที)

### การหยุดบันทึก
- หยุดบันทึกเมื่อกระบวนการป้อนปลาเสร็จสิ้น
- แปลงไฟล์ H264 เป็น MP4 ด้วย FFmpeg
- ลบไฟล์ temporary H264 

## 📁 การเก็บไฟล์

### ตำแหน่งไฟล์
```
src/data/history/feeder-vdo/
```

### รูปแบบชื่อไฟล์
```
{uuid4}-{yyyy-mm-dd-hh-mm-ss}.mp4
```

### ตัวอย่าง
```
5298ef37-2d85-4270-9790-94849509581c-2025-06-21-20-17-57.mp4
```

## ⚙️ ข้อกำหนดระบบ

### Dependencies
- **picamera2**: สำหรับควบคุมกล้อง
- **ffmpeg**: สำหรับแปลงไฟล์วิดีโอ

### การติดตั้ง FFmpeg บน Raspberry Pi
```bash
sudo apt update
sudo apt install ffmpeg -y
```

## 🎥 ข้อมูลเทคนิค

### การตั้งค่าวิดีโอ
- **Resolution**: 500x500 pixels (streaming)
- **Frame Rate**: 30 FPS
- **Bitrate**: 0.5 Mbps (ประหยัดพื้นที่)
- **Encoder**: H264
- **Container**: MP4

### กระบวนการบันทึก
1. สร้างไฟล์ temporary H264
2. บันทึกด้วย Picamera2 H264Encoder
3. หยุดบันทึกเมื่อเสร็จสิ้น
4. แปลงเป็น MP4 ด้วย FFmpeg
5. ลบไฟล์ temporary

## 📊 การจัดเก็บข้อมูล

### CSV History
ข้อมูลไฟล์วิดีโอจะถูกบันทึกใน CSV history พร้อม **video_file column ใหม่**:

```csv
timestamp,amount_g,actuator_up_s,actuator_down_s,auger_duration_s,blower_duration_s,status,message,video_file
2025-06-21 20:30:15,25,3.0,3.0,8.0,5.0,success,Feeding process completed successfully,a1b2c3d4-e5f6-7890-abcd-ef1234567890-2025-06-21-20-30-15.mp4
2025-06-21 18:45:22,15,2.0,2.0,6.0,4.0,success,Feeding process completed successfully,f9e8d7c6-b5a4-3210-9876-543210abcdef-2025-06-21-18-45-22.mp4
```

**หมายเหตุ**: video_file จะเก็บเฉพาะชื่อไฟล์ (ไม่ใส่ full path) เพื่อให้ CSV อ่านง่าย

### API Response
```json
{
  "status": "success",
  "message": "Feeding process completed successfully",
  "feed_size": 10,
  "video_file": "/path/to/video.mp4",
  "total_duration": 12
}
```

## 🔧 การแก้ไขปัญหา

### วิดีโอเล่นไม่ได้
**สาเหตุ**: ไฟล์ H264 ไม่ได้ถูกแปลงเป็น MP4
**วิธีแก้**:
1. ตรวจสอบ FFmpeg: `ffmpeg -version`
2. ดู log การแปลงไฟล์
3. ตรวจสอบไฟล์ temporary H264

### ไฟล์ขนาด 0 bytes
**สาเหตุ**: การบันทึกหยุดเร็วเกินไป (error หรือ interrupt)
**วิธีแก้**:
1. ตรวจสอบ log error
2. ให้กระบวนการป้อนปลาทำงานจนจบ

### กล้องไม่ทำงาน
**สาเหตุ**: Camera module ไม่ได้เปิดใช้งาน
**วิธีแก้**:
```bash
sudo raspi-config
# Interfacing Options > Camera > Yes
sudo reboot
```

### Multiple Camera Instance Error
**สาเหตุ**: สร้าง VideoStreamService หลายครั้ง
**วิธีแก้**: ใช้ instance เดียวกันทั้งระบบ

## 🧪 การทดสอบ

### Mock Mode (Development)
```python
# ตั้ง environment variable
export ENABLE_CAMERA=false

# หรือใน code
USE_MOCK_CAMERA = True
```

### การทดสอบบน Pi
```bash
cd fish-feeder-pi-server
python test_feeder_video.py
```

## 📝 การใช้งาน API

### เริ่มการป้อนปลา (พร้อมบันทึกวิดีโอ)
```bash
curl -X POST http://localhost:5000/api/feeder/start \
  -H "Content-Type: application/json" \
  -d '{
    "feed_size": 10,
    "actuator_up": 2,
    "actuator_down": 2,
    "auger_duration": 5,
    "blower_duration": 3
  }'
```

### Response
```json
{
  "status": "success",
  "message": "Feeding process completed successfully",
  "feed_size": 10,
  "video_file": "/home/pi/fish-feeder-pi-server/src/data/history/feeder-vdo/uuid-timestamp.mp4",
  "total_duration": 12,
  "steps_completed": [
    "Actuator up: 2s",
    "Actuator down: 2s",
    "Auger forward & Blower (simultaneous): 5s & 3s"
  ]
}
```

## 🎯 Features

### ✅ ทำงานแล้ว
- ✅ บันทึกวิดีโอเมื่อเริ่มป้อนปลา
- ✅ ชื่อไฟล์ด้วย UUID + timestamp
- ✅ แปลงเป็น MP4 ที่เล่นได้
- ✅ เก็บข้อมูลใน CSV history
- ✅ จัดการ error อัตโนมัติ
- ✅ Mock mode สำหรับ development

### 🔄 อาจเพิ่มในอนาคต
- 📊 Video analytics (motion detection)
- 🔄 Video compression options
- 📡 Auto upload to cloud storage
- 📱 Real-time streaming during feeding
- 🎛️ Manual recording controls

---
**หมายเหตุ**: ระบบนี้ต้องการกล้อง Raspberry Pi และ FFmpeg ที่ติดตั้งอย่างถูกต้อง 