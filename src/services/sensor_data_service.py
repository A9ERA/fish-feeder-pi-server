"""
Service for managing sensor data storage and retrieval
"""
import json5  # Use json5 for JSONC support
import datetime
from typing import Dict, Any
from pathlib import Path

class SensorDataService:
    def __init__(self, data_file_path: str = 'src/data/sensors_data.jsonc'):
        self.data_file_path = Path(data_file_path)
        self._ensure_data_file_exists()

    def _ensure_data_file_exists(self):
        """Ensure the data file exists with proper structure"""
        if not self.data_file_path.exists():
            # Create parent directories if they don't exist
            self.data_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create initial data structure
            initial_data = {
                "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # last updated timestamp of all sensors
                "sensors": {}
            }
            
            # Save initial data
            with open(self.data_file_path, 'w') as f:
                json5.dump(initial_data, f, indent=4, quote_keys=True)

    def update_sensor_data(self, sensor_name: str, sensor_values: list) -> None:
        """
        Update sensor data in the storage file
        
        Args:
            sensor_name: Name of the sensor
            sensor_values: List of sensor readings with type, unit, and value
        """
        try:
            # Ensure file exists
            self._ensure_data_file_exists()
            
            # Load existing data
            with open(self.data_file_path, 'r') as f:
                file_content = f.read().strip()
                if not file_content:
                    # Handle empty file case
                    print(f"[❌][Sensor Data Service] Warning: Empty sensor data file, recreating...")
                    self._ensure_data_file_exists()
                    with open(self.data_file_path, 'r') as f2:
                        file_content = f2.read().strip()
                sensors_data = json5.loads(file_content)

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
                json5.dump(sensors_data, f, indent=4, quote_keys=True)
                
            # print(f"[⌗][Sensor Data Service] - Updated data for sensor: {sensor_name}")

        except Exception as e:
            print(f"[❌][Sensor Data Service] Error: {e}")

    def get_sensor_data(self) -> Dict[str, Any]:
        """
        Get all sensor data from storage
        
        Returns:
            Dictionary containing all sensor data
        """
        try:
            # Ensure file exists
            self._ensure_data_file_exists()
            
            with open(self.data_file_path, 'r') as f:
                file_content = f.read().strip()
                if not file_content:
                    # Handle empty file case
                    print(f"[❌][Sensor Data Service] Warning: Empty sensor data file, recreating...")
                    self._ensure_data_file_exists()
                    with open(self.data_file_path, 'r') as f2:
                        file_content = f2.read().strip()
                return json5.loads(file_content)
        except Exception as e:
            print(f"[❌][Sensor Data Service] Error: {e}")
            return {"error": str(e)} 