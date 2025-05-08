import paho.mqtt.client as mqtt
import requests
import json
import threading
import time

# === CONFIG ===
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
TOPIC_SUB = "sensor/data"
TOPIC_PUB = "server/message"

FIREBASE_URL = "https://addsensorvalue-bp4gxqhmza-uc.a.run.app"

# === MQTT Callback เมื่อเชื่อมต่อ ===
def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    client.subscribe(TOPIC_SUB)

# === Callback เมื่อได้รับข้อมูลจาก ESP32 ===
def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        print(f"MQTT Received: {payload}")
        data_dict = json.loads(payload)

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

def send_command_loop():
    commands = ["on_in1", "on_in2", "off_all"]
    i = 0
    while True:
        command = commands[i % len(commands)]
        client.publish(TOPIC_PUB, command)
        print(f"📤 Published command: {command}")
        i += 1
        time.sleep(5)

# === START ===
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(MQTT_BROKER, MQTT_PORT, 60)

# เริ่ม thread สำหรับส่ง "hello"
threading.Thread(target=send_command_loop, daemon=True).start()

client.loop_forever()
