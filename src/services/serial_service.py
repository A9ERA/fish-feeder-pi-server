"""
Serial Service for handling USB serial communication with Arduino
"""
import serial
import serial.tools.list_ports
import json
import threading
from typing import Optional
from src.services.sensor_data_service import SensorDataService
from src.config.settings import SERIAL_PORT, BAUD_RATE

class SerialService:
    def __init__(self, port: str = None, baud_rate: int = BAUD_RATE):
        """
        Initialize Serial Service
        
        Args:
            port: Serial port (if None, will auto-detect Arduino)
            baud_rate: Baud rate for serial communication (default from settings)
        """
        self.port = port or self.find_arduino_port() or SERIAL_PORT
        self.baud_rate = baud_rate
        self.serial = None
        self.is_running = False
        self._stop_event = threading.Event()
        self.sensor_data_service = SensorDataService()
        self.read_thread = None

    def find_arduino_port(self) -> Optional[str]:
        """
        Automatically find Arduino port by checking connected devices
        
        Returns:
            str: Arduino port device path if found, None otherwise
        """
        ports = serial.tools.list_ports.comports()
        for port in ports:
            # เช็กจาก description หรือ VID/PID ที่มักใช้กับ Arduino
            if ("Arduino" in port.description or 
                "CH340" in port.description or 
                "ttyUSB" in port.device or
                "ttyACM" in port.device or
                "FT232" in port.description or
                "CP210" in port.description):
                print(f"✅ Arduino found at {port.device} ({port.description})")
                return port.device  # เช่น '/dev/ttyUSB0' หรือ '/dev/ttyUSB1'
        
        print("❌ No Arduino device found")
        return None

    def list_available_ports(self):
        """
        List all available serial ports for debugging
        """
        ports = serial.tools.list_ports.comports()
        print("\n📋 Available serial ports:")
        if not ports:
            print("  No serial ports found")
        else:
            for port in ports:
                print(f"  • {port.device} - {port.description}")
        print()

    def connect(self) -> bool:
        """
        Connect to the serial port
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        # Try to find Arduino port if current port doesn't work
        if not self._try_connect(self.port):
            print(f"Failed to connect to {self.port}, searching for Arduino...")
            arduino_port = self.find_arduino_port()
            if arduino_port and arduino_port != self.port:
                self.port = arduino_port
                return self._try_connect(self.port)
            return False
        return True

    def _try_connect(self, port: str) -> bool:
        """
        Try to connect to a specific port
        
        Args:
            port: Serial port to connect to
            
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.serial = serial.Serial(
                port=port,
                baudrate=self.baud_rate,
                timeout=1
            )
            print(f"✅ Connected to {port} at {self.baud_rate} baud")
            return True
        except Exception as e:
            print(f"❌ Serial connection error on {port}: {e}")
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
        [SEND] - {
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
            if data.startswith("[SEND] - "):
                # Remove the "[SEND] - " prefix
                json_data = data[8:]
                data_dict = json.loads(json_data)
                sensor_name = data_dict['name']
                print(f"[⌗][Serial Service] - Processing data from sensor: {sensor_name}")
                self.sensor_data_service.update_sensor_data(sensor_name, data_dict['value'])
        except json.JSONDecodeError:
            print(f"Invalid JSON data received: {data}")
        except Exception as e:
            print(f"Error processing serial data: {e}")

    def start(self):
        """Start the serial service"""
        print("🔍 Starting Serial Service...")
        print(f"🎯 Target port: {self.port}")
        
        # List available ports for debugging
        if not self.connect():
            print("❌ Failed to establish serial connection")
            self.list_available_ports()
            print("💡 Please check:")
            print("   • Arduino is connected via USB")
            print("   • Arduino drivers are installed")
            print("   • No other application is using the port")
            return False

        self._stop_event.clear()
        self.read_thread = threading.Thread(target=self.read_serial_data, daemon=True)
        self.read_thread.start()
        print("✅ Serial service started successfully")
        return True

    def stop(self):
        """Stop the serial service"""
        self._stop_event.set()
        if self.read_thread:
            self.read_thread.join()
        self.disconnect()
        print("Serial service stopped") 