"""
Service for managing sensor data history storage to CSV files
"""
import json5
import csv
import datetime
import os
from typing import Dict, Any
from pathlib import Path

class SensorHistoryService:
    def __init__(self, data_file_path: str = 'src/data/sensors_data.jsonc', 
                 history_base_path: str = 'src/data/history/sensors'):
        self.data_file_path = Path(data_file_path)
        self.history_base_path = Path(history_base_path)
        
    def _ensure_history_directory_exists(self, sensor_name: str):
        """Ensure the history directory exists for a specific sensor"""
        # Convert sensor name for directory name (lowercase, replace _ with -)
        dir_name = sensor_name.lower().replace('_', '-')
        sensor_dir = self.history_base_path / dir_name
        sensor_dir.mkdir(parents=True, exist_ok=True)
        return sensor_dir
    
    def _format_sensor_name_for_file(self, sensor_name: str) -> str:
        """Convert sensor name to lowercase and replace underscores with hyphens"""
        return sensor_name.lower().replace('_', '-')
    
    def _get_csv_filename(self, sensor_name: str, date: datetime.datetime) -> str:
        """Generate CSV filename based on sensor name and date"""
        formatted_name = self._format_sensor_name_for_file(sensor_name)
        date_str = date.strftime("%d-%m-%Y")
        return f"{formatted_name}_{date_str}.csv"
    
    def _read_sensor_data(self) -> Dict[str, Any]:
        """Read current sensor data from the JSONC file"""
        try:
            if not self.data_file_path.exists():
                print(f"[❌][Sensor History] Sensor data file not found: {self.data_file_path}")
                return {}
                
            with open(self.data_file_path, 'r') as f:
                content = f.read().strip()
                if not content:
                    print(f"[❌][Sensor History] Sensor data file is empty")
                    return {}
                    
                return json5.loads(content)
        except Exception as e:
            print(f"[❌][Sensor History] Error reading sensor data: {e}")
            return {}
    
    def _write_csv_data(self, csv_path: Path, sensor_data: Dict[str, Any], is_new_file: bool):
        """Write sensor data to CSV file"""
        try:
            current_time = datetime.datetime.now()
            
            # Prepare row data
            row_data = {
                'timestamp': current_time.strftime("%Y-%m-%d %H:%M:%S"),
                'sensor_last_updated': sensor_data.get('last_updated', ''),
            }
            
            # Add all sensor values to the row
            for value_data in sensor_data.get('values', []):
                column_name = f"{value_data.get('type', 'unknown')}_{value_data.get('unit', 'unit')}"
                row_data[column_name] = value_data.get('value', '')
            
            # Write to CSV
            with open(csv_path, 'a', newline='', encoding='utf-8') as csvfile:
                fieldnames = list(row_data.keys())
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                # Write header if it's a new file
                if is_new_file:
                    writer.writeheader()
                
                writer.writerow(row_data)
                
        except Exception as e:
            print(f"[❌][Sensor History] Error writing CSV data: {e}")
    
    def save_current_sensor_data(self):
        """Save current sensor data to CSV files for each sensor"""
        try:
            # Read current sensor data
            sensors_data = self._read_sensor_data()
            
            if not sensors_data or 'sensors' not in sensors_data:
                print(f"[❌][Sensor History] No valid sensor data found")
                return
            
            current_time = datetime.datetime.now()
            saved_count = 0
            
            # Process each sensor
            for sensor_name, sensor_data in sensors_data['sensors'].items():
                try:
                    # Ensure directory exists
                    sensor_dir = self._ensure_history_directory_exists(sensor_name)
                    
                    # Generate filename
                    csv_filename = self._get_csv_filename(sensor_name, current_time)
                    csv_path = sensor_dir / csv_filename
                    
                    # Check if file exists to determine if we need to write headers
                    is_new_file = not csv_path.exists()
                    
                    # Write data to CSV
                    self._write_csv_data(csv_path, sensor_data, is_new_file)
                    
                    saved_count += 1
                    
                except Exception as e:
                    print(f"[❌][Sensor History] Error saving data for sensor {sensor_name}: {e}")
            
            # if saved_count > 0:
            #     print(f"[✅][Sensor History] Saved data for {saved_count} sensors at {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
            # else:
            #     print(f"[⚠️][Sensor History] No sensor data was saved")
                
        except Exception as e:
            print(f"[❌][Sensor History] Error in save_current_sensor_data: {e}")
    
    def get_sensor_history_files(self, sensor_name: str = None) -> Dict[str, Any]:
        """Get list of history files for a sensor or all sensors"""
        try:
            result = {}
            
            if sensor_name:
                # Get files for specific sensor
                sensor_dir = self.history_base_path / self._format_sensor_name_for_file(sensor_name)
                if sensor_dir.exists():
                    files = [f.name for f in sensor_dir.glob("*.csv")]
                    result[sensor_name] = sorted(files)
            else:
                # Get files for all sensors
                if self.history_base_path.exists():
                    for sensor_dir in self.history_base_path.iterdir():
                        if sensor_dir.is_dir():
                            files = [f.name for f in sensor_dir.glob("*.csv")]
                            result[sensor_dir.name] = sorted(files)
            
            return result
            
        except Exception as e:
            print(f"[❌][Sensor History] Error getting history files: {e}")
            return {} 