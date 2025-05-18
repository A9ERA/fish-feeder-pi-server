"""
Service for managing sensor data storage and retrieval
"""
import json
import datetime
from typing import Dict, Any

class SensorDataService:
    def __init__(self, data_file_path: str = 'src/data/sensors_data.jsonc'):
        self.data_file_path = data_file_path

    def update_sensor_data(self, sensor_name: str, sensor_values: list) -> None:
        """
        Update sensor data in the storage file
        
        Args:
            sensor_name: Name of the sensor
            sensor_values: List of sensor readings with type, unit, and value
        """
        try:
            # Load existing data
            with open(self.data_file_path, 'r') as f:
                sensors_data = json.loads(f.read())

            # Update sensor data
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Update last_updated timestamps
            sensors_data['last_updated'] = current_time
            if sensor_name in sensors_data['sensors']:
                sensors_data['sensors'][sensor_name]['last_updated'] = current_time
                sensors_data['sensors'][sensor_name]['values'] = sensor_values
            else:
                sensors_data['sensors'][sensor_name] = {
                    'last_updated': current_time,
                    'description': f"Data from {sensor_name}",
                    'values': sensor_values
                }

            # Save updated data
            with open(self.data_file_path, 'w') as f:
                json.dump(sensors_data, f, indent=4)

        except Exception as e:
            print(f"Sensor Data Service Error: {e}")
            raise

    def get_sensor_data(self) -> Dict[str, Any]:
        """
        Get all sensor data from storage
        
        Returns:
            Dictionary containing all sensor data
        """
        try:
            with open(self.data_file_path, 'r') as f:
                return json.loads(f.read())
        except Exception as e:
            print(f"Sensor Data Service Error: {e}")
            raise 