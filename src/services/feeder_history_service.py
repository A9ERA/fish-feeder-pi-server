"""
Service for managing feeder operation history storage to CSV files
"""
import csv
import datetime
import os
from typing import Dict, Any, List
from pathlib import Path

class FeederHistoryService:
    def __init__(self, history_base_path: str = 'src/data/history/feeder'):
        self.history_base_path = Path(history_base_path)
        
    def _ensure_history_directory_exists(self):
        """Ensure the history directory exists for feeder logs"""
        self.history_base_path.mkdir(parents=True, exist_ok=True)
        return self.history_base_path
    
    def _get_csv_filename(self, date: datetime.datetime) -> str:
        """Generate CSV filename based on date"""
        date_str = date.strftime("%d-%m-%Y")
        return f"feeder_{date_str}.csv"
    
    def _write_csv_data(self, csv_path: Path, feed_data: Dict[str, Any], is_new_file: bool):
        """Write feed data to CSV file"""
        try:
            # Prepare row data
            row_data = {
                'timestamp': feed_data['timestamp'],
                'amount_g': feed_data['amount'],
                'actuator_up_s': feed_data['actuator_up'],
                'actuator_down_s': feed_data['actuator_down'],
                'auger_duration_s': feed_data['auger_duration'],
                'blower_duration_s': feed_data['blower_duration'],
                'status': feed_data['status'],
                'message': feed_data.get('message', '')
            }
            
            # Write to CSV
            with open(csv_path, 'a', newline='', encoding='utf-8') as csvfile:
                fieldnames = list(row_data.keys())
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                # Write header if it's a new file
                if is_new_file:
                    writer.writeheader()
                
                writer.writerow(row_data)
                
        except Exception as e:
            print(f"[❌][Feeder History] Error writing CSV data: {e}")
    
    def log_feed_operation(self, feed_size: int, actuator_up: float, actuator_down: float, 
                          auger_duration: float, blower_duration: float, status: str, message: str = ""):
        """Log a feed operation to CSV file"""
        try:
            current_time = datetime.datetime.now()
            
            # Ensure directory exists
            self._ensure_history_directory_exists()
            
            # Generate filename
            csv_filename = self._get_csv_filename(current_time)
            csv_path = self.history_base_path / csv_filename
            
            # Check if file exists to determine if we need to write headers
            is_new_file = not csv_path.exists()
            
            # Prepare feed data
            feed_data = {
                'timestamp': current_time.strftime("%Y-%m-%d %H:%M:%S"),
                'amount': feed_size,
                'actuator_up': actuator_up,
                'actuator_down': actuator_down,
                'auger_duration': auger_duration,
                'blower_duration': blower_duration,
                'status': status,
                'message': message
            }
            
            # Write data to CSV
            self._write_csv_data(csv_path, feed_data, is_new_file)
            
            print(f"[✅][Feeder History] Logged feed operation: {feed_size}g at {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
                
        except Exception as e:
            print(f"[❌][Feeder History] Error logging feed operation: {e}")
    
    def get_feed_history_files(self) -> List[str]:
        """Get list of feed history files"""
        try:
            if self.history_base_path.exists():
                files = [f.name for f in self.history_base_path.glob("*.csv")]
                return sorted(files, reverse=True)  # Most recent first
            return []
            
        except Exception as e:
            print(f"[❌][Feeder History] Error getting history files: {e}")
            return []
    
    def read_feed_history(self, date: datetime.datetime = None) -> List[Dict[str, Any]]:
        """Read feed history from CSV file for a specific date or today"""
        try:
            if date is None:
                date = datetime.datetime.now()
            
            csv_filename = self._get_csv_filename(date)
            csv_path = self.history_base_path / csv_filename
            
            if not csv_path.exists():
                return []
            
            feed_logs = []
            with open(csv_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    try:
                        # Convert numeric values
                        feed_log = {
                            'timestamp': row['timestamp'],
                            'amount': int(float(row['amount_g'])),
                            'actuator_up': float(row['actuator_up_s']),
                            'actuator_down': float(row['actuator_down_s']),
                            'auger_duration': float(row['auger_duration_s']),
                            'blower_duration': float(row['blower_duration_s']),
                            'status': row['status'],
                            'message': row.get('message', '')
                        }
                        feed_logs.append(feed_log)
                    except (ValueError, KeyError) as e:
                        print(f"[⚠️][Feeder History] Error parsing row: {e}")
                        continue
            
            # Sort by timestamp (most recent first)
            feed_logs.sort(key=lambda x: x['timestamp'], reverse=True)
            return feed_logs
            
        except Exception as e:
            print(f"[❌][Feeder History] Error reading feed history: {e}")
            return []
    
    def get_available_dates(self) -> List[str]:
        """Get list of available dates with feed history"""
        try:
            files = self.get_feed_history_files()
            dates = []
            
            for filename in files:
                # Extract date from filename (feeder_DD-MM-YYYY.csv)
                if filename.startswith('feeder_') and filename.endswith('.csv'):
                    date_part = filename[7:-4]  # Remove 'feeder_' and '.csv'
                    dates.append(date_part)
            
            return dates
            
        except Exception as e:
            print(f"[❌][Feeder History] Error getting available dates: {e}")
            return [] 