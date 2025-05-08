import paho.mqtt.client as mqtt

# ฟังก์ชันเมื่อเชื่อมต่อกับ Broker สำเร็จ
def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    client.subscribe("sensor/data")  # ติดตามหัวข้อ

# ฟังก์ชันเมื่อได้รับข้อความจาก ESP32
def on_message(client, userdata, msg):
    print(f"Topic: {msg.topic}, Message: {msg.payload.decode()}")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

# เชื่อมต่อกับ Broker ที่อยู่ในเครื่องตัวเอง
client.connect("localhost", 1883, 60)

client.loop_forever()
