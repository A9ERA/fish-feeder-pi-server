import serial
import time

ser = serial.Serial('dev/ttyUSB0', 9600, timeout=1)
time.sleep(2)  # รอ Mega รีเซ็ต

# สั่งเปิดรีเลย์
ser.write(b'RELAY_ON\n')
time.sleep(1)

# สั่งปิดรีเลย์
ser.write(b'RELAY_OFF\n')
time.sleep(1)

# สั่ง PWM = 200
ser.write(b'PWM:200\n')
