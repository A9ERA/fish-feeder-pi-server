"""
MQTT Service for handling MQTT communication
"""
import paho.mqtt.client as mqtt
import json
import datetime
from src.config.settings import MQTT_BROKER, MQTT_PORT, TOPIC_SUB
from src.services.firebase_service import FirebaseService
from src.services.sensor_data_service import SensorDataService

class MQTTService:
    def __init__(self):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.firebase_service = FirebaseService()
        self.sensor_data_service = SensorDataService()

    def on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker"""
        print(f"Connected with result code {rc}")
        client.subscribe(TOPIC_SUB)

    def on_message(self, client, userdata, msg):
        """
            Callback when message is received
            Sample Incoming Message:
            {
                "name": "DHT22_FEEDER",
                "value": [
                    {
                        "type": "temperature",
                        "unit": "C",
                        "value": 22.5
                    },
                    {
                        "type": "humidity",
                        "unit": "%",
                        "value": 45.2
                    }
                ]
            }
        """
        try:
            payload = msg.payload.decode()
            data_dict = json.loads(payload)

            # Update sensor data using the sensor data service
            sensor_name = data_dict['name']
            self.sensor_data_service.update_sensor_data(sensor_name, data_dict['value'])

            # Commented out Firebase integration for now
            # for key, value in data_dict.items():
            #     status_code, response_text = self.firebase_service.send_sensor_data(key, value)
            #     print(f"Sent {key}: {value} → {status_code}, {response_text}")

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