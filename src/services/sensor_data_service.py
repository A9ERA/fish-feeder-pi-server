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
        try:
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
                
                # Verify the file was created correctly
                with open(self.data_file_path, 'r') as f:
                    content = f.read().strip()
                    if not content:
                        print(f"[❌][Sensor Data Service] Warning: Created file is empty, writing minimal data")
                        # Write minimal JSON if dump failed
                        with open(self.data_file_path, 'w') as f2:
                            f2.write('{\n    "last_updated": "' + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + '",\n    "sensors": {}\n}')
        except Exception as e:
            print(f"[❌][Sensor Data Service] Error creating data file: {e}")
            # Try to create a minimal valid JSON file as fallback
            try:
                with open(self.data_file_path, 'w') as f:
                    f.write('{\n    "last_updated": "' + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + '",\n    "sensors": {}\n}')
                print(f"[✅][Sensor Data Service] Created minimal fallback data file")
            except Exception as fallback_error:
                print(f"[❌][Sensor Data Service] Failed to create fallback file: {fallback_error}")

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
            
            # Load existing data with comprehensive error handling
            try:
                with open(self.data_file_path, 'r') as f:
                    file_content = f.read().strip()
                    if not file_content:
                        # Handle empty file case
                        print(f"[❌][Sensor Data Service] Warning: Empty sensor data file, recreating...")
                        # Force recreate the file by removing it first
                        if self.data_file_path.exists():
                            self.data_file_path.unlink()
                        self._ensure_data_file_exists()
                        # Read the newly created file
                        with open(self.data_file_path, 'r') as f2:
                            file_content = f2.read().strip()
                        
                        # If still empty after recreation, use default data
                        if not file_content:
                            print(f"[❌][Sensor Data Service] Error: Unable to create valid sensor data file, using default data")
                            sensors_data = {
                                "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "sensors": {}
                            }
                        else:
                            sensors_data = json5.loads(file_content)
                    else:
                        sensors_data = json5.loads(file_content)
            except ValueError as json_error:
                # Handle JSON parsing errors
                print(f"[❌][Sensor Data Service] JSON parsing error: {json_error}, recreating file...")
                # Force recreate the file by removing corrupted one
                if self.data_file_path.exists():
                    self.data_file_path.unlink()
                self._ensure_data_file_exists()
                sensors_data = {
                    "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "sensors": {}
                }

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
            
            # Load data with comprehensive error handling
            try:
                with open(self.data_file_path, 'r') as f:
                    file_content = f.read().strip()
                    if not file_content:
                        # Handle empty file case
                        print(f"[❌][Sensor Data Service] Warning: Empty sensor data file, recreating...")
                        # Force recreate the file by removing it first
                        if self.data_file_path.exists():
                            self.data_file_path.unlink()
                        self._ensure_data_file_exists()
                        # Read the newly created file
                        with open(self.data_file_path, 'r') as f2:
                            file_content = f2.read().strip()
                        
                        # If still empty after recreation, return default data
                        if not file_content:
                            print(f"[❌][Sensor Data Service] Error: Unable to create valid sensor data file, returning default data")
                            return {
                                "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "sensors": {}
                            }
                    
                    return json5.loads(file_content)
            except ValueError as json_error:
                # Handle JSON parsing errors
                print(f"[❌][Sensor Data Service] JSON parsing error in get_sensor_data: {json_error}, recreating file...")
                # Force recreate the file by removing corrupted one
                if self.data_file_path.exists():
                    self.data_file_path.unlink()
                self._ensure_data_file_exists()
                return {
                    "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "sensors": {}
                }
        except Exception as e:
            print(f"[❌][Sensor Data Service] Error: {e}")
            return {"error": str(e)} 