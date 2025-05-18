"""
MQTT Service for handling MQTT communication
"""
import paho.mqtt.client as mqtt
import json
from src.config.settings import MQTT_BROKER, MQTT_PORT, TOPIC_SUB
from src.services.firebase_service import FirebaseService

class MQTTService:
    def __init__(self):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.firebase_service = FirebaseService()

    def on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker"""
        print(f"Connected with result code {rc}")
        client.subscribe(TOPIC_SUB)

    def on_message(self, client, userdata, msg):
        """Callback when message is received"""
        try:
            payload = msg.payload.decode()
            print(f"MQTT Received: {payload}")
            data_dict = json.loads(payload)

            for key, value in data_dict.items():
                status_code, response_text = self.firebase_service.send_sensor_data(key, value)
                print(f"Sent {key}: {value} → {status_code}, {response_text}")

        except Exception as e:
            print(f"MQTT Error: {e}")

    def connect(self):
        """Connect to MQTT broker"""
        self.client.connect(MQTT_BROKER, MQTT_PORT, 60)

    def start_loop(self):
        """Start the MQTT loop"""
        self.client.loop_forever()

    def publish(self, topic, message):
        """Publish message to topic"""
        self.client.publish(topic, message) 