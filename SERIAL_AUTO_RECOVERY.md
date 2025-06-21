# Serial Auto-Recovery System

## ปัญหาที่แก้ไข

ระบบเดิมพบปัญหา **"Error reading serial data: [Errno 5] Input/output error"** เมื่อรันทิ้งไว้ระยะเวลานาน โดยเมื่อเจอ error นี้แล้วระบบจะหยุดทำงานและต้องรีสตาร์ทใหม่

## การแก้ไขที่ทำ

### 1. ปรับปรุง Serial Service (`src/services/serial_service.py`)

#### เพิ่ม Auto-Reconnection ใน `read_serial_data()` method:
- ✅ ตรวจจับ `serial.SerialException` (รวมถึง Input/output error)
- ✅ ปิดการเชื่อมต่อเดิมอัตโนมัติ
- ✅ พยายามเชื่อมต่อใหม่ (สูงสุด 5 ครั้ง)
- ✅ ค้นหา Arduino port ใหม่หากจำเป็น
- ✅ หยุดพัก 2 วินาทีระหว่างการพยายามเชื่อมต่อ

#### เพิ่ม Auto-Reconnection ใน `send_command()` methods:
- ✅ ตรวจสอบการเชื่อมต่อก่อนส่งคำสั่ง
- ✅ พยายามเชื่อมต่อใหม่หากไม่สามารถส่งคำสั่งได้
- ✅ ลองส่งคำสั่งซ้ำหลังจากเชื่อมต่อใหม่

#### เพิ่ม Methods ใหม่:
```python
def _attempt_reconnection(self) -> bool
def check_connection_health(self) -> bool  
def get_connection_status(self) -> Dict[str, Any]
def restart(self) -> bool
```

### 2. ปรับปรุง Main Server (`main.py`)

#### เพิ่ม Connection Monitoring:
- ✅ ตรวจสอบสุขภาพการเชื่อมต่อทุก 30 วินาที
- ✅ รีสตาร์ท Serial Service อัตโนมัติเมื่อพบปัญหา
- ✅ ระบบ Threading สำหรับ API และ Monitoring แยกกัน
- ✅ Retry mechanism เมื่อเริ่มต้น Serial Service

### 3. เพิ่มเครื่องมือทดสอบ (`test_serial_recovery.py`)

#### ฟีเจอร์การทดสอบ:
- 🧪 ทดสอบการเชื่อมต่อปกติ
- 🧪 ทดสอบ Auto-Reconnection
- 🧪 ตรวจสอบสุขภาพการเชื่อมต่อ
- 🧪 Monitor การเชื่อมต่อแบบ Real-time

## วิธีการใช้งาน

### 1. รันเซิร์ฟเวอร์ปกติ
```bash
cd fish-feeder-pi-server
python main.py
```

เซิร์ฟเวอร์จะ:
- เริ่มต้น Serial Service พร้อม retry mechanism
- ตรวจสอบสุขภาพการเชื่อมต่อทุก 30 วินาที
- รีสตาร์ท Serial Service อัตโนมัติเมื่อพบปัญหา

### 2. ทดสอบระบบ Auto-Recovery
```bash
cd fish-feeder-pi-server
python test_serial_recovery.py
```

ระหว่างการทดสอบ:
1. ดูสถานะการเชื่อมต่อปกติ
2. ถอดสาย USB Arduino
3. เสียบสาย USB Arduino กลับ
4. สังเกตการ Auto-Reconnection

## Log Messages ที่สำคัญ

### การเชื่อมต่อปกติ:
```
✅ Serial service started successfully
✅ Connected to /dev/ttyUSB0 at 9600 baud
```

### เมื่อเจอปัญหา:
```
❌ Serial read error: [Errno 5] Input/output error
💡 Arduino may have been disconnected
🔄 Attempting to reconnect... (attempt 1/5)
```

### การเชื่อมต่อใหม่สำเร็จ:
```
✅ Successfully reconnected to Arduino!
```

### การตรวจสอบสุขภาพ:
```
⚠️ Serial connection appears unhealthy, attempting recovery...
✅ Serial service recovered successfully
```

## การกำหนดค่า

### Serial Recovery Settings (ใน `serial_service.py`):
```python
max_reconnection_attempts = 5      # จำนวนครั้งที่พยายามเชื่อมต่อ
reconnection_delay = 2            # หยุดพัก (วินาที) ระหว่างการพยายาม
```

### Monitoring Settings (ใน `main.py`):
```python
serial_check_interval = 30       # ตรวจสอบทุก 30 วินาที
```

## ปัญหาที่แก้ไขได้

✅ **Input/output error**: ระบบจะ reconnect อัตโนมัติ
✅ **Arduino ถูกถอดสาย**: จะค้นหาและเชื่อมต่อใหม่
✅ **Port เปลี่ยน**: จะค้นหา Arduino port ใหม่
✅ **Connection timeout**: จะรีสตาร์ทการเชื่อมต่อ
✅ **Long-running stability**: มี monitoring ตลอดเวลา

## การ Monitor และ Debug

### ดู Serial Connection Status:
```python
status = serial_service.get_connection_status()
print(status)
# Output: {'connected': True, 'port': '/dev/ttyUSB0', 'is_open': True, 'healthy': True}
```

### ทดสอบ Health Check:
```python
health = serial_service.check_connection_health()
print(f"Connection healthy: {health}")
```

### Manual Restart:
```python
success = serial_service.restart()
print(f"Restart successful: {success}")
```

## การแจ้งเตือนและ Logging

ระบบจะแจ้งสถานะผ่าน console logs:
- 🔍 การค้นหา Arduino
- 🔌 การเชื่อมต่อ/ตัดการเชื่อมต่อ  
- ❌ ข้อผิดพลาด
- 🔄 การพยายามเชื่อมต่อใหม่
- ✅ ความสำเร็จ
- ⚠️ คำเตือน

ระบบนี้จะช่วยให้ Fish Feeder System สามารถทำงานได้อย่างต่อเนื่องแม้จะเจอปัญหา serial connection โดยไม่ต้องรีสตาร์ทเซิร์ฟเวอร์ใหม่ 