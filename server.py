import paho.mqtt.client as mqtt
import requests
import json

FIREBASE_URL = "https://addsensorvalue-bp4gxqhmza-uc.a.run.app"

# ฟังก์ชันเมื่อเชื่อมต่อกับ Broker สำเร็จ
def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    client.subscribe("sensor/data")  # ติดตามหัวข้อ

# ฟังก์ชันเมื่อได้รับข้อความจาก ESP32
def on_message(client, userdata, msg):
    print(f"Topic: {msg.topic}, Message: {msg.payload.decode()}")

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        print(f"MQTT Received: {payload}")
        data_dict = json.loads(payload)  # แปลง JSON string เป็น dict

        for key, value in data_dict.items():
            post_data = {
                "sensorName": key,
                "value": value
            }

            headers = {'Content-Type': 'application/json'}
            response = requests.post(FIREBASE_URL, headers=headers, data=json.dumps(post_data))
            print(f"Sent {key}: {value} → {response.status_code}, {response.text}")

    except Exception as e:
        print("Error:", e)


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

# เชื่อมต่อกับ Broker ที่อยู่ในเครื่องตัวเอง
client.connect("localhost", 1883, 60)

client.loop_forever()
