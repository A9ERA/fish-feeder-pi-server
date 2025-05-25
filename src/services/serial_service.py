"""
Serial Service for handling USB serial communication with Arduino
"""
import serial
import json
import threading
from typing import Optional
from src.services.sensor_data_service import SensorDataService
from src.config.settings import SERIAL_PORT, BAUD_RATE

class SerialService:
    def __init__(self, port: str = SERIAL_PORT, baud_rate: int = BAUD_RATE):
        """
        Initialize Serial Service
        
        Args:
            port: Serial port (default from settings)
            baud_rate: Baud rate for serial communication (default from settings)
        """
        self.port = port
        self.baud_rate = baud_rate
        self.serial = None
        self.is_running = False
        self._stop_event = threading.Event()
        self.sensor_data_service = SensorDataService()
        self.read_thread = None

    def connect(self) -> bool:
        """
        Connect to the serial port
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baud_rate,
                timeout=1
            )
            print(f"Connected to {self.port} at {self.baud_rate} baud")
            return True
        except Exception as e:
            print(f"Serial connection error: {e}")
            return False

    def disconnect(self):
        """Disconnect from the serial port"""
        if self.serial and self.serial.is_open:
            self.serial.close()
            print("Disconnected from serial port")

    def read_serial_data(self):
        """Read data from serial port in a loop"""
        while not self._stop_event.is_set():
            if self.serial and self.serial.is_open:
                try:
                    if self.serial.in_waiting:
                        line = self.serial.readline().decode('utf-8').strip()
                        if line:
                            self._process_data(line)
                except Exception as e:
                    print(f"Error reading serial data: {e}")
                    continue

    def _process_data(self, data: str):
        """
        Process received data and update sensor data service
        
        Expected format from Arduino:
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
            data_dict = json.loads(data)
            sensor_name = data_dict['name']
            self.sensor_data_service.update_sensor_data(sensor_name, data_dict['value'])
        except json.JSONDecodeError:
            print(f"Invalid JSON data received: {data}")
        except Exception as e:
            print(f"Error processing serial data: {e}")

    def start(self):
        """Start the serial service"""
        if not self.connect():
            return False

        self._stop_event.clear()
        self.read_thread = threading.Thread(target=self.read_serial_data, daemon=True)
        self.read_thread.start()
        print("Serial service started")
        return True

    def stop(self):
        """Stop the serial service"""
        self._stop_event.set()
        if self.read_thread:
            self.read_thread.join()
        self.disconnect()
        print("Serial service stopped") 