"""
Firebase Service for handling Firebase operations
"""
import requests
import json
from src.config.settings import FIREBASE_URL

class FirebaseService:
    def __init__(self):
        self.url = FIREBASE_URL
        self.headers = {'Content-Type': 'application/json'}

    def send_sensor_data(self, sensor_name: str, value: float) -> tuple:
        """
        Send sensor data to Firebase
        
        Args:
            sensor_name (str): Name of the sensor
            value (float): Sensor value
            
        Returns:
            tuple: (status_code, response_text)
        """
        try:
            post_data = {
                "sensorName": sensor_name,
                "value": value
            }
            response = requests.post(
                self.url, 
                headers=self.headers, 
                data=json.dumps(post_data)
            )
            return response.status_code, response.text
        except Exception as e:
            print(f"Firebase Error: {e}")
            return None, str(e) 