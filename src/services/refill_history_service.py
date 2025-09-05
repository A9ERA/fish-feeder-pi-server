"""
Service for managing food refill history (weight increases) stored as CSV files.
Each log contains timestamp, weight_before_kg, weight_after_kg, and increase_kg.
"""
import csv
import datetime
import os
from typing import Dict, Any, List
from pathlib import Path


class RefillHistoryService:
    def __init__(self, history_base_path: str = 'src/data/history/refill-weight'):
        self.history_base_path = Path(history_base_path)

    def _ensure_history_directory_exists(self):
        """Ensure the history directory exists for refill logs"""
        self.history_base_path.mkdir(parents=True, exist_ok=True)
        return self.history_base_path

    def _get_csv_filename(self, date: datetime.datetime) -> str:
        """Generate CSV filename based on date"""
        date_str = date.strftime("%d-%m-%Y")
        return f"refill_{date_str}.csv"

    def _write_csv_data(self, csv_path: Path, log_data: Dict[str, Any], is_new_file: bool):
        """Write a refill log record to CSV file"""
        try:
            row_data = {
                'timestamp': log_data['timestamp'],
                'weight_before_kg': f"{float(log_data['weight_before_kg']):.3f}",
                'weight_after_kg': f"{float(log_data['weight_after_kg']):.3f}",
                'increase_kg': f"{float(log_data['increase_kg']):.3f}",
            }

            if not is_new_file and csv_path.exists():
                try:
                    with open(csv_path, 'rb') as check_file:
                        check_file.seek(-1, 2)
                        last_byte = check_file.read(1)
                        if last_byte != b'\n':
                            with open(csv_path, 'a', encoding='utf-8') as fix_file:
                                fix_file.write('\n')
                except Exception:
                    pass

            with open(csv_path, 'a', newline='', encoding='utf-8') as csvfile:
                fieldnames = list(row_data.keys())
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, lineterminator='\n')

                if is_new_file:
                    writer.writeheader()

                writer.writerow(row_data)
                csvfile.flush()
                os.fsync(csvfile.fileno())
        except Exception as e:
            print(f"[❌][Refill History] Error writing CSV data: {e}")

    def log_refill(self, weight_before_kg: float, weight_after_kg: float):
        """Log a refill event to CSV file."""
        try:
            now = datetime.datetime.now()
            self._ensure_history_directory_exists()
            csv_filename = self._get_csv_filename(now)
            csv_path = self.history_base_path / csv_filename
            is_new_file = not csv_path.exists()

            increase = float(weight_after_kg) - float(weight_before_kg)
            log_item = {
                'timestamp': now.strftime("%Y-%m-%d %H:%M:%S"),
                'weight_before_kg': float(weight_before_kg),
                'weight_after_kg': float(weight_after_kg),
                'increase_kg': float(increase)
            }

            self._write_csv_data(csv_path, log_item, is_new_file)
            print(f"[✅][Refill History] Logged refill: +{increase:.3f} kg at {log_item['timestamp']}")
        except Exception as e:
            print(f"[❌][Refill History] Error logging refill: {e}")

    def get_history_files(self) -> List[str]:
        """Get list of refill history files (most recent first)."""
        try:
            if self.history_base_path.exists():
                files = [f.name for f in self.history_base_path.glob("*.csv")]
                return sorted(files, reverse=True)
            return []
        except Exception as e:
            print(f"[❌][Refill History] Error getting history files: {e}")
            return []

    def read_history(self, date: datetime.datetime) -> List[Dict[str, Any]]:
        """Read refill history for the specified date."""
        try:
            csv_filename = self._get_csv_filename(date)
            csv_path = self.history_base_path / csv_filename
            if not csv_path.exists():
                return []

            logs: List[Dict[str, Any]] = []
            with open(csv_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    try:
                        logs.append({
                            'timestamp': row['timestamp'],
                            'weight_before_kg': float(row['weight_before_kg']),
                            'weight_after_kg': float(row['weight_after_kg']),
                            'increase_kg': float(row['increase_kg']),
                        })
                    except Exception:
                        continue

            logs.sort(key=lambda x: x['timestamp'], reverse=True)
            return logs
        except Exception as e:
            print(f"[❌][Refill History] Error reading history: {e}")
            return []

    def get_available_dates(self) -> List[str]:
        """Get list of available dates with refill history."""
        try:
            files = self.get_history_files()
            dates: List[str] = []
            for filename in files:
                if filename.startswith('refill_') and filename.endswith('.csv'):
                    dates.append(filename[7:-4])
            return dates
        except Exception as e:
            print(f"[❌][Refill History] Error getting available dates: {e}")
            return []


