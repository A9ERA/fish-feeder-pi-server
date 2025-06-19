# วิธีการรันโปรเจคบน Mac (Development Mode)

โปรเจคนี้ถูกออกแบบมาสำหรับ Raspberry Pi แต่สามารถรันบน Mac ได้เพื่อทดสอบฟังก์ชั่นต่างๆ โดยจะใช้ Mock Camera แทนการใช้ picamera2 จริง

## การติดตั้ง

### 1. ติดตั้ง Dependencies

```bash
# ใช้ requirements-mac.txt แทน requirements.txt
pip install -r requirements-mac.txt
```

### 2. ตั้งค่า Environment Variables

สร้างไฟล์ `.env` จาก `env.example`:

```bash
cp env.example .env
```

แก้ไขไฟล์ `.env`:

```env
# กำหนดให้ใช้ Mock Camera
ENABLE_CAMERA=false

# หรือเว้นไว้เป็น auto เพื่อให้ระบบตรวจจับเอง
# ENABLE_CAMERA=auto
```

### 3. รันโปรเจค

```bash
python main.py
```

## ฟีเจอร์ที่ใช้งานได้บน Mac

✅ **API Endpoints**: ทั้งหมดยกเว้นการทำงานกับฮาร์ดแวร์
✅ **Firebase Integration**: เชื่อมต่อและซิงค์ข้อมูลได้ปกติ
✅ **Web Interface**: เข้าถึงผ่าน http://localhost:5000
✅ **Mock Camera Features**:
- Video streaming (แสดง mock frame)
- Take photo (สร้างไฟล์รูปภาพ mock)
- Video recording (สร้างไฟล์วิดีโอ mock)
- Audio recording (สร้างไฟล์เสียง mock)

⚠️ **ฟีเจอร์ที่ไม่ทำงาน**: 
- Serial Communication (ต้องการ Arduino/Hardware)
- ฮาร์ดแวร์ควบคุม (Blower, Actuator, Auger, Relay)

## ความแตกต่างระหว่าง Mock และ Real Camera

### Mock Camera (Mac Development)
- แสดง static frame สำหรับ video streaming
- สร้างไฟล์ mock สำหรับการถ่ายรูป/บันทึกวิดีโอ
- ไม่ต้องการฮาร์ดแวร์กล้อง
- ใช้สำหรับพัฒนาและทดสอบ API

### Real Camera (Raspberry Pi)
- ใช้ picamera2 จริง
- สตรีมวิดีโอจากกล้อง Raspberry Pi Camera
- บันทึกไฟล์รูป/วิดีโอจริง

## Environment Variables

| Variable | Values | Description |
|----------|---------|-------------|
| `ENABLE_CAMERA` | `true` | บังคับใช้กล้องจริง |
| `ENABLE_CAMERA` | `false` | บังคับใช้ mock camera |
| `ENABLE_CAMERA` | `auto` | ตรวจจับอัตโนมัติ (default) |

## ทดสอบ API

เมื่อรันเซิร์ฟเวอร์แล้ว สามารถทดสอบ Camera API ได้:

```bash
# ทดสอบ video streaming
curl http://localhost:5000/api/camera/video_feed

# ทดสอบถ่ายรูป
curl -X POST http://localhost:5000/api/camera/photo

# ทดสอบบันทึกวิดีโอ
curl -X POST http://localhost:5000/api/camera/record/start
curl -X POST http://localhost:5000/api/camera/record/stop

# ทดสอบบันทึกเสียง
curl -X POST http://localhost:5000/api/camera/audio/record \
  -H "Content-Type: application/json" \
  -d '{"duration": 10}'
```

## การ Deploy บน Raspberry Pi

เมื่อต้องการ deploy จริงบน Raspberry Pi:

1. ใช้ `requirements-pi.txt`
2. ตั้งค่า `ENABLE_CAMERA=true` หรือ `auto`
3. ตรวจสอบว่ามี Camera Module เชื่อมต่อแล้ว

## Troubleshooting

### ImportError: picamera2
ถ้าเจอ error นี้บน Mac แสดงว่า environment variable ไม่ได้ตั้งค่าถูกต้อง:
- ตั้งค่า `ENABLE_CAMERA=false` ใน `.env`
- หรือใช้ `requirements-mac.txt`

### Serial Port Error
บน Mac จะไม่มี `/dev/ttyUSB0` เป็นเรื่องปกติ เซิร์ฟเวอร์จะยังคงรันได้โดยไม่มี Serial connection 