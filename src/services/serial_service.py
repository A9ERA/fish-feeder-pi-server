"""
Serial Service for handling USB serial communication with Arduino
"""
import serial
import serial.tools.list_ports
import json
import threading
import queue
import time
from typing import Optional, Dict, List, Any
from src.services.sensor_data_service import SensorDataService
from src.config.settings import BAUD_RATE

class SerialService:
    def __init__(self, port: str = None, baud_rate: int = BAUD_RATE):
        """
        Initialize Serial Service
        
        Args:
            port: Serial port (if None, will auto-detect Arduino)
            baud_rate: Baud rate for serial communication (default from settings)
        """
        self.port = port or self.find_arduino_port()
        self.baud_rate = baud_rate
        self.serial = None
        self.is_running = False
        self._stop_event = threading.Event()
        self.sensor_data_service = SensorDataService()
        self.read_thread = None
        
        # Command response handling
        self._pending_commands = {}  # Dict to track pending commands
        self._command_responses = queue.Queue()  # Queue for command responses
        self._command_lock = threading.Lock()

    def find_arduino_port(self) -> Optional[str]:
        """
        Automatically find Arduino port by checking connected devices
        
        Returns:
            str: Arduino port device path if found, None otherwise
        """
        ports = serial.tools.list_ports.comports()
        if not ports:
            print("❌ No serial ports found!")
            print("💡 Troubleshooting:")
            print("   • Make sure Arduino is connected via USB")
            print("   • Try a different USB cable or port")
            print("   • Install Arduino drivers if needed")
            print("   • Check Device Manager (Windows) for unrecognized devices")
            return None

        print(f"🔍 Found {len(ports)} serial port(s):")
        arduino_port = None
        
        for port in ports:
            print(f"   📱 {port.device} - {port.description}")
            
            # Check for common Arduino identifiers
            if (any(keyword in port.description.upper() for keyword in 
                   ["ARDUINO", "CH340", "CH341", "FT232", "CP210", "USB SERIAL"]) or
                any(keyword in port.device.upper() for keyword in 
                   ["TTYUSB", "TTYACM", "COM"])):
                print(f"      ⭐ Likely Arduino device!")
                if not arduino_port:  # Use the first Arduino-like device found
                    arduino_port = port.device
        
        if arduino_port:
            print(f"✅ Selected Arduino port: {arduino_port}")
            return arduino_port
        else:
            print("❌ No Arduino-like device found")
            print("💡 If your Arduino is connected but not detected:")
            print("   • Check if drivers are installed for your specific Arduino model")
            print("   • Try connecting to a different USB port")
            print("   • Verify the Arduino is powered on")
            return None

    def list_available_ports(self):
        """
        List all available serial ports for debugging
        """
        ports = serial.tools.list_ports.comports()
        print("\n📋 Available serial ports:")
        if not ports:
            print("  ❌ No serial ports found")
            print("  💡 This usually means:")
            print("     • Arduino is not connected")
            print("     • USB drivers are not installed")
            print("     • Arduino is not powered on")
        else:
            for port in ports:
                print(f"  • {port.device} - {port.description}")
                if port.vid and port.pid:
                    print(f"    VID: {port.vid:04X}, PID: {port.pid:04X}")
        print()

    def connect(self) -> bool:
        """
        Connect to the serial port
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        if not self.port:
            print("❌ No Arduino port available to connect to")
            self.list_available_ports()
            return False
            
        # Try to connect to the current port
        if not self._try_connect(self.port):
            print(f"❌ Failed to connect to {self.port}")
            
            # Try to find Arduino port again
            print("🔍 Searching for Arduino again...")
            new_arduino_port = self.find_arduino_port()
            
            if new_arduino_port and new_arduino_port != self.port:
                print(f"🔄 Trying new port: {new_arduino_port}")
                self.port = new_arduino_port
                return self._try_connect(self.port)
            else:
                print("❌ Unable to establish Arduino connection")
                self._print_connection_troubleshooting()
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
        except serial.SerialException as e:
            print(f"❌ Serial connection error on {port}: {e}")
            if "Access is denied" in str(e) or "Permission denied" in str(e):
                print("💡 This usually means another application is using the port")
                print("   Try closing Arduino IDE, PuTTY, or other serial applications")
            elif "could not open port" in str(e).lower():
                print("💡 Port may not exist or Arduino disconnected")
            return False
        except Exception as e:
            print(f"❌ Unexpected connection error on {port}: {e}")
            return False

    def _print_connection_troubleshooting(self):
        """Print comprehensive troubleshooting information"""
        print("\n🔧 Arduino Connection Troubleshooting:")
        print("=" * 50)
        print("1. 🔌 Hardware Check:")
        print("   • Verify Arduino is connected via USB cable")
        print("   • Try a different USB cable (data cable, not charge-only)")
        print("   • Try a different USB port")
        print("   • Check if Arduino power LED is on")
        
        print("\n2. 💾 Software Check:")
        print("   • Make sure Arduino is programmed with fish-feeder code")
        print("   • Verify Arduino IDE can connect to the device")
        print("   • Check Device Manager (Windows) for driver issues")
        
        print("\n3. 🐞 System Check:")
        print("   • Close Arduino IDE if it's open")
        print("   • Close any other applications using serial ports")
        print("   • Try unplugging and reconnecting Arduino")
        
        print("\n4. 🛠️ Driver Check:")
        print("   • Arduino Uno/Nano: Usually auto-detected")
        print("   • ESP32/ESP8266: May need CP210x or CH34x drivers")
        print("   • Chinese clones: Often need CH340G drivers")
        print("=" * 50)

    def disconnect(self):
        """Disconnect from the serial port"""
        if self.serial and self.serial.is_open:
            self.serial.close()
            print("🔌 Disconnected from serial port")

    def send_command(self, command: str) -> bool:
        """
        Send a command to Arduino with auto-reconnection on failure
        
        Args:
            command: Command to send (without [control]: prefix)
            
        Returns:
            bool: True if command sent successfully
        """
        if not self.serial or not self.serial.is_open:
            print("❌ Serial connection not available")
            # Try to reconnect before giving up
            if self._attempt_reconnection():
                print("✅ Reconnected successfully, retrying command...")
            else:
                return False
            
        try:
            full_command = f"[control]:{command}\n"
            self.serial.write(full_command.encode('utf-8'))
            print(f"[Serial Service] Sent command: {full_command.strip()}")
            return True
        except (serial.SerialException, OSError, IOError) as e:
            print(f"❌ Serial connection error sending command: {e}")
            print("🔄 Attempting to reconnect and retry...")
            
            # Close and reset connection
            try:
                if self.serial and self.serial.is_open:
                    self.serial.close()
            except:
                pass
            self.serial = None
            
            # Try to reconnect and retry once
            if self._attempt_reconnection():
                try:
                    full_command = f"[control]:{command}\n"
                    self.serial.write(full_command.encode('utf-8'))
                    print(f"[Serial Service] Sent command after reconnection: {full_command.strip()}")
                    return True
                except Exception as retry_e:
                    print(f"❌ Failed to send command after reconnection: {retry_e}")
                    return False
            else:
                print("❌ Failed to reconnect")
                return False
        except Exception as e:
            print(f"❌ Unexpected error sending command: {e}")
            print(f"   Error type: {type(e).__name__}")
            return False

    def send_command_with_response(self, command: str, timeout: float = 3.0) -> Dict:
        """
        Send a command and wait for response with auto-reconnection on failure
        
        Args:
            command: Command to send (without [control]: prefix)
            timeout: Timeout in seconds
            
        Returns:
            Dict with success status and response data
        """
        if not self.serial or not self.serial.is_open:
            print("❌ Serial connection not available")
            # Try to reconnect before giving up
            if self._attempt_reconnection():
                print("✅ Reconnected successfully, retrying command...")
            else:
                return {
                    'success': False,
                    'error': 'Serial connection not available and reconnection failed'
                }
            
        try:
            with self._command_lock:
                # Generate unique command ID
                command_id = f"{command}_{time.time()}"
                
                # Register command expectation
                self._pending_commands[command_id] = {
                    'command': command,
                    'responses': [],
                    'completed': False
                }
                
                # Send command
                full_command = f"[control]:{command}\n"
                self.serial.write(full_command.encode('utf-8'))
                print(f"[Serial Service] Sent command: {full_command.strip()}")
                
            # Wait for response
            start_time = time.time()
            while time.time() - start_time < timeout:
                # Check if we have collected responses for this command
                with self._command_lock:
                    if command_id in self._pending_commands:
                        cmd_data = self._pending_commands[command_id]
                        if cmd_data['completed'] or len(cmd_data['responses']) > 0:
                            responses = cmd_data['responses']
                            del self._pending_commands[command_id]
                            
                            if responses:
                                return {
                                    'success': True,
                                    'responses': responses
                                }
                
                time.sleep(0.1)
            
            # Timeout occurred
            with self._command_lock:
                if command_id in self._pending_commands:
                    del self._pending_commands[command_id]
                    
            return {
                'success': False,
                'error': 'Command timeout - no response received'
            }
            
        except (serial.SerialException, OSError, IOError) as e:
            print(f"❌ Serial connection error sending command with response: {e}")
            print("🔄 Attempting to reconnect...")
            
            # Close and reset connection
            try:
                if self.serial and self.serial.is_open:
                    self.serial.close()
            except:
                pass
            self.serial = None
            
            # Clean up pending command
            with self._command_lock:
                if command_id in self._pending_commands:
                    del self._pending_commands[command_id]
            
            # Try to reconnect and retry once
            if self._attempt_reconnection():
                print("✅ Reconnected successfully, retrying command...")
                return self.send_command_with_response(command, timeout)
            else:
                return {
                    'success': False,
                    'error': f'Serial connection error: {str(e)} and reconnection failed'
                }
        except Exception as e:
            print(f"❌ Error sending command with response: {e}")
            # Clean up pending command
            with self._command_lock:
                if command_id in self._pending_commands:
                    del self._pending_commands[command_id]
            return {
                'success': False,
                'error': str(e)
            }

    def check_connection_health(self) -> bool:
        """
        Check if the serial connection is healthy
        
        Returns:
            bool: True if connection is healthy, False otherwise
        """
        try:
            if not self.serial or not self.serial.is_open:
                return False
            
            # Try to check if the port is still available
            return True
            
        except Exception as e:
            print(f"❌ Connection health check failed: {e}")
            return False

    def get_connection_status(self) -> Dict[str, Any]:
        """
        Get detailed connection status information
        
        Returns:
            Dictionary with connection status details
        """
        status = {
            'connected': False,
            'port': self.port,
            'baud_rate': self.baud_rate,
            'is_open': False,
            'healthy': False
        }
        
        try:
            if self.serial:
                status['connected'] = True
                status['is_open'] = self.serial.is_open
                status['healthy'] = self.check_connection_health()
            
            return status
            
        except Exception as e:
            status['error'] = str(e)
            return status

    def read_serial_data(self):
        """Read data from serial port in a loop with auto-reconnection"""
        reconnection_attempts = 0
        max_reconnection_attempts = 5
        reconnection_delay = 2  # seconds
        
        while not self._stop_event.is_set():
            if self.serial and self.serial.is_open:
                try:
                    if self.serial.in_waiting:
                        line = self.serial.readline().decode('utf-8', errors='ignore').strip()
                        if line:
                            self._process_data(line)
                    # Reset reconnection attempts on successful read
                    reconnection_attempts = 0
                except (serial.SerialException, OSError, IOError) as e:
                    print(f"❌ Serial connection error: {e}")
                    print("💡 Arduino may have been disconnected or connection lost")
                    
                    # Handle Input/output error and other connection errors
                    print(f"🔄 Attempting to reconnect... (attempt {reconnection_attempts + 1}/{max_reconnection_attempts})")
                    
                    # Close current connection
                    try:
                        if self.serial and self.serial.is_open:
                            self.serial.close()
                    except:
                        pass  # Ignore errors during disconnection
                    
                    self.serial = None
                    
                    # Wait before attempting reconnection
                    time.sleep(reconnection_delay)
                    
                    # Try to reconnect
                    if self._attempt_reconnection():
                        print("✅ Successfully reconnected to Arduino!")
                        reconnection_attempts = 0
                        continue
                    else:
                        reconnection_attempts += 1
                        if reconnection_attempts >= max_reconnection_attempts:
                            print(f"❌ Failed to reconnect after {max_reconnection_attempts} attempts")
                            print("🛑 Serial service will stop. Please check Arduino connection.")
                            break
                        else:
                            print(f"⚠️ Reconnection failed. Will retry in {reconnection_delay} seconds...")
                            time.sleep(reconnection_delay)
                            
                except Exception as e:
                    print(f"❌ Unexpected error reading serial data: {e}")
                    print(f"   Error type: {type(e).__name__}")
                    # For truly unexpected exceptions, add a small delay to prevent spam
                    time.sleep(0.5)
                    continue
            else:
                # No connection available, try to establish one
                if reconnection_attempts < max_reconnection_attempts:
                    print("🔄 No serial connection available, attempting to connect...")
                    if self._attempt_reconnection():
                        print("✅ Successfully connected to Arduino!")
                        reconnection_attempts = 0
                    else:
                        reconnection_attempts += 1
                        print(f"⚠️ Connection attempt {reconnection_attempts}/{max_reconnection_attempts} failed")
                        time.sleep(reconnection_delay)
                else:
                    print("❌ Maximum reconnection attempts reached. Waiting...")
                    time.sleep(10)  # Wait longer before trying again
                    reconnection_attempts = 0  # Reset attempts after long wait
                    
    def _attempt_reconnection(self) -> bool:
        """
        Attempt to reconnect to Arduino
        
        Returns:
            bool: True if reconnection successful, False otherwise
        """
        try:
            # First try the current port
            if self.port:
                print(f"🔄 Trying to reconnect to {self.port}...")
                if self._try_connect(self.port):
                    return True
            
            # If current port fails, try to find Arduino again
            print("🔍 Searching for Arduino device...")
            new_port = self.find_arduino_port()
            
            if new_port:
                if new_port != self.port:
                    print(f"🔄 Found Arduino on different port: {new_port}")
                    self.port = new_port
                
                if self._try_connect(self.port):
                    return True
            
            return False
            
        except Exception as e:
            print(f"❌ Error during reconnection attempt: {e}")
            return False

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
                # print(f"[⌗][Serial Service] - Processing data from sensor: {sensor_name}")
                self.sensor_data_service.update_sensor_data(sensor_name, data_dict['value'])
            elif data.startswith("[INFO]"):
                # Handle Arduino info messages (could be command responses)
                print(f"[Arduino] {data}")
                
                # Check if this is a response to a pending command
                with self._command_lock:
                    for command_id, cmd_data in self._pending_commands.items():
                        # For sensor status commands, collect INFO responses
                        if 'sensors:status' in cmd_data['command']:
                            cmd_data['responses'].append(data)
                            # Mark as completed after getting both status lines
                            if len(cmd_data['responses']) >= 2:
                                cmd_data['completed'] = True
            else:
                # Handle other Arduino messages
                if any(prefix in data for prefix in ["[ACTUATOR]", "[AUGER]", "[RELAY]", "[BLOWER]"]):
                    print(f"[Arduino] {data}")
                    
        except json.JSONDecodeError:
            # Don't spam with JSON errors for non-JSON Arduino messages
            if not any(prefix in data for prefix in ["[ACTUATOR]", "[AUGER]", "[RELAY]", "[BLOWER]", "[INFO]"]):
                print(f"⚠️ Invalid JSON data received: {data}")
        except Exception as e:
            print(f"❌ Error processing serial data: {e}")

    def restart(self) -> bool:
        """
        Restart the serial service completely
        
        Returns:
            bool: True if restart successful, False otherwise
        """
        print("🔄 Restarting Serial Service...")
        
        # Stop current service
        self.stop()
        
        # Wait a bit for cleanup
        time.sleep(1)
        
        # Start again
        return self.start()

    def start(self):
        """Start the serial service"""
        print("🚀 Starting Serial Service...")
        
        if not self.connect():
            print("❌ Failed to establish serial connection")
            print("🛑 Serial service startup failed")
            return False

        self._stop_event.clear()
        self.read_thread = threading.Thread(target=self.read_serial_data, daemon=True)
        self.read_thread.start()
        print("✅ Serial service started successfully")
        return True

    def stop(self):
        """Stop the serial service"""
        print("🛑 Stopping serial service...")
        self._stop_event.set()
        if self.read_thread and self.read_thread.is_alive():
            self.read_thread.join(timeout=5)  # Add timeout to prevent hanging
            if self.read_thread.is_alive():
                print("⚠️ Read thread did not stop gracefully")
        self.disconnect()
        print("✅ Serial service stopped")

    def is_connected(self) -> bool:
        """Check if serial connection is active"""
        return self.serial is not None and self.serial.is_open 