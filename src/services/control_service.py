"""
Control Service for sending commands to Arduino devices
"""
import threading
from typing import Optional
from .serial_service import SerialService

class ControlService:
    def __init__(self, serial_service: Optional[SerialService] = None):
        """
        Initialize Control Service with optional serial service
        
        Args:
            serial_service: SerialService instance for Arduino communication
        """
        self.serial_service = serial_service
        self._lock = threading.Lock()

    def _send_command(self, command: str) -> bool:
        """
        Send a control command to Arduino
        
        Args:
            command: Command to send (without [control]: prefix)
        """
        if not self.serial_service:
            print("No serial service available")
            return False
        
        return self.serial_service.send_command(command)

    # Blower control methods
    def start_blower(self) -> bool:
        """Start the blower"""
        return self._send_command("blower:start")

    def stop_blower(self) -> bool:
        """Stop the blower"""
        return self._send_command("blower:stop")

    def set_blower_speed(self, speed: int) -> bool:
        """
        Set blower speed
        
        Args:
            speed: Speed value (0-100 or device specific range)
        """
        if not isinstance(speed, int) or speed < 0:
            print("Invalid speed value. Must be a positive integer.")
            return False
        return self._send_command(f"blower:speed:{speed}")

    def set_blower_direction_reverse(self) -> bool:
        """Set blower direction to reverse"""
        return self._send_command("blower:direction:reverse")

    def set_blower_direction_normal(self) -> bool:
        """Set blower direction to normal"""
        return self._send_command("blower:direction:normal")

    # Actuator control methods (updated to match Arduino commands)
    def actuator_up(self) -> bool:
        """Move actuator up"""
        return self._send_command("actuator:up")

    def actuator_down(self) -> bool:
        """Move actuator down"""
        return self._send_command("actuator:down")

    def actuator_stop(self) -> bool:
        """Stop actuator"""
        return self._send_command("actuator:stop")

    # Auger control methods
    def auger_forward(self) -> bool:
        """Move auger forward"""
        return self._send_command("auger:forward")

    def auger_backward(self) -> bool:
        """Move auger backward"""
        return self._send_command("auger:backward")

    def auger_stop(self) -> bool:
        """Stop auger"""
        return self._send_command("auger:stop")

    def auger_speedtest(self) -> bool:
        """Run auger speed test"""
        return self._send_command("auger:speedtest")

    def auger_setspeed(self, speed: int) -> bool:
        """
        Set auger speed
        
        Args:
            speed: Speed value (0-100 or device specific range)
        """
        if not isinstance(speed, int) or speed < 0:
            print("Invalid speed value. Must be a positive integer.")
            return False
        return self._send_command(f"auger:setspeed:{speed}")

    # Relay control methods
    def relay_led_on(self) -> bool:
        """Turn LED relay on"""
        return self._send_command("relay:led:on")

    def relay_led_off(self) -> bool:
        """Turn LED relay off"""
        return self._send_command("relay:led:off")

    def relay_fan_on(self) -> bool:
        """Turn fan relay on"""
        return self._send_command("relay:fan:on")

    def relay_fan_off(self) -> bool:
        """Turn fan relay off"""
        return self._send_command("relay:fan:off")

    def relay_all_off(self) -> bool:
        """Turn all relays off"""
        return self._send_command("relay:all:off")

    # Convenience methods for common operations
    def control_blower(self, action: str, value: Optional[int] = None) -> bool:
        """
        Control blower with a single method
        
        Args:
            action: Action to perform ('start', 'stop', 'speed', 'direction_reverse', 'direction_normal')
            value: Value for speed setting (required for 'speed' action)
        """
        if action == "start":
            return self.start_blower()
        elif action == "stop":
            return self.stop_blower()
        elif action == "speed":
            if value is None:
                print("Speed value is required for speed action")
                return False
            return self.set_blower_speed(value)
        elif action == "direction_reverse":
            return self.set_blower_direction_reverse()
        elif action == "direction_normal":
            return self.set_blower_direction_normal()
        else:
            print(f"Unknown blower action: {action}")
            return False

    def control_actuator(self, action: str) -> bool:
        """
        Control actuator with a single method
        
        Args:
            action: Action to perform ('up', 'down', 'stop')
        """
        if action == "up":
            return self.actuator_up()
        elif action == "down":
            return self.actuator_down()
        elif action == "stop":
            return self.actuator_stop()
        else:
            print(f"Unknown actuator action: {action}")
            return False

    def control_auger(self, action: str, value: Optional[int] = None) -> bool:
        """
        Control auger with a single method
        
        Args:
            action: Action to perform ('forward', 'backward', 'stop', 'speedtest', 'setspeed')
            value: Value for speed setting (required for 'setspeed' action)
        """
        if action == "forward":
            return self.auger_forward()
        elif action == "backward":
            return self.auger_backward()
        elif action == "stop":
            return self.auger_stop()
        elif action == "speedtest":
            return self.auger_speedtest()
        elif action == "setspeed":
            if value is None:
                print("Speed value is required for setspeed action")
                return False
            return self.auger_setspeed(value)
        else:
            print(f"Unknown auger action: {action}")
            return False

    def control_relay(self, device: str, action: str) -> bool:
        """
        Control relay with a single method
        
        Args:
            device: Device to control ('led', 'fan', 'all')
            action: Action to perform ('on', 'off')
        """
        if device == "led":
            if action == "on":
                return self.relay_led_on()
            elif action == "off":
                return self.relay_led_off()
        elif device == "fan":
            if action == "on":
                return self.relay_fan_on()
            elif action == "off":
                return self.relay_fan_off()
        elif device == "all" and action == "off":
            return self.relay_all_off()
        
        print(f"Unknown relay device/action: {device}/{action}")
        return False

    # Sensor control methods
    def sensors_start(self) -> bool:
        """Start sensors"""
        return self._send_command("sensors:start")

    def sensors_stop(self) -> bool:
        """Stop sensors"""
        return self._send_command("sensors:stop")

    def sensors_set_interval(self, interval: int) -> bool:
        """
        Set sensors interval
        
        Args:
            interval: Interval value in milliseconds
        """
        if not isinstance(interval, int) or interval < 0:
            print("Invalid interval value. Must be a positive integer.")
            return False
        return self._send_command(f"sensors:interval:{interval}")

    def sensors_status(self) -> dict:
        """Get sensors status using proper command response system"""
        if not self.serial_service or not self.serial_service.is_connected():
            return {
                'success': False,
                'error': 'Serial connection not available'
            }

        try:
            # Use the new command-with-response system
            result = self.serial_service.send_command_with_response("sensors:status", timeout=3.0)
            
            if result['success']:
                response_lines = result['responses']
                print(f"[Control Service] Received {len(response_lines)} response lines from Arduino")
                
                # Parse the status information
                status_info = {}
                arduino_status = None
                arduino_interval = None
                
                for line in response_lines:
                    print(f"[Control Service] Arduino response: {line}")
                    
                    if 'Sensor service status:' in line:
                        if line.endswith('INACTIVE'):
                            arduino_status = 'INACTIVE'
                        elif line.endswith('ACTIVE'):
                            arduino_status = 'ACTIVE'
                    elif 'Print interval:' in line:
                        # Extract interval value (e.g., "Print interval: 1000ms")
                        import re
                        match = re.search(r'(\d+)ms', line)
                        if match:
                            arduino_interval = int(match.group(1))
                
                # Set consistent status values
                if arduino_status:
                    status_info['status'] = arduino_status
                    status_info['is_running'] = (arduino_status == 'ACTIVE')
                    print(f"[Control Service] DEBUG - Parsed status: {arduino_status}, is_running: {arduino_status == 'ACTIVE'}")
                else:
                    status_info['status'] = 'UNKNOWN'
                    status_info['is_running'] = False
                    print(f"[Control Service] DEBUG - No status found, setting to UNKNOWN")
                    
                if arduino_interval:
                    status_info['interval'] = arduino_interval
                    print(f"[Control Service] DEBUG - Parsed interval: {arduino_interval}")
                
                print(f"[Control Service] DEBUG - Final status_info: {status_info}")
                
                return {
                    'success': True,
                    'raw_responses': response_lines,
                    **status_info
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Unknown error')
                }
                
        except Exception as e:
            print(f"Error getting sensor status: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def control_sensors(self, action: str, value: Optional[int] = None):
        """
        Control sensors with a single method
        
        Args:
            action: Action to perform ('start', 'stop', 'interval', 'status')
            value: Value for interval setting (required for 'interval' action)
            
        Returns:
            bool for start/stop/interval actions, dict for status action
        """
        if action == "start":
            return self.sensors_start()
        elif action == "stop":
            return self.sensors_stop()
        elif action == "interval":
            if value is None:
                print("Interval value is required for interval action")
                return False
            return self.sensors_set_interval(value)
        elif action == "status":
            return self.sensors_status()
        else:
            print(f"Unknown sensors action: {action}")
            return False

    # Legacy method name compatibility
    def control_actuator_motor(self, action: str) -> bool:
        """
        Legacy method name for actuator control
        Redirects to control_actuator for backward compatibility
        """
        return self.control_actuator(action) 