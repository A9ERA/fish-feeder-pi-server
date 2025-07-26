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

    # Solenoid valve control methods (updated to match Arduino commands)
    def solenoid_open(self) -> bool:
        """Open solenoid valve"""
        return self._send_command("solenoid:open")

    def solenoid_close(self) -> bool:
        """Close solenoid valve"""
        return self._send_command("solenoid:close")

    def solenoid_stop(self) -> bool:
        """Stop solenoid valve"""
        return self._send_command("solenoid:stop")

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

    def control_solenoid(self, action: str) -> bool:
        """
        Control solenoid valve with a single method
        
        Args:
            action: Action to perform ('open', 'close', 'stop')
        """
        if action == "open":
            return self.solenoid_open()
        elif action == "close":
            return self.solenoid_close()
        elif action == "stop":
            return self.solenoid_stop()
        else:
            print(f"Unknown solenoid action: {action}")
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
    def sensors_start(self) -> dict:
        """Start sensors and return status"""
        success = self._send_command("sensors:start")
        if success:
            # Wait a moment for Arduino to process the command
            import time
            time.sleep(0.5)
            # Get updated status
            status = self.sensors_status()
            status['command_success'] = True
            return status
        else:
            return {
                'success': False,
                'command_success': False,
                'error': 'Failed to send start command'
            }

    def sensors_stop(self) -> dict:
        """Stop sensors and return status"""
        success = self._send_command("sensors:stop")
        if success:
            # Wait a moment for Arduino to process the command
            import time
            time.sleep(0.5)
            # Get updated status
            status = self.sensors_status()
            status['command_success'] = True
            return status
        else:
            return {
                'success': False,
                'command_success': False,
                'error': 'Failed to send stop command'
            }

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
            dict for start/stop/status actions, bool for interval action
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


    # Weight sensor calibration methods
    def weight_calibrate(self) -> bool:
        """Start weight sensor calibration"""
        return self._send_command("weight:calibrate")

    def control_weight(self, action: str) -> dict:
        """
        Control weight sensor with a single method
        
        Args:
            action: Action to perform ('calibrate')
            
        Returns:
            dict: Result with success status and any response data
        """
        if action == "calibrate":
            success = self.weight_calibrate()
            return {
                'success': success,
                'command_success': success,
                'message': 'Weight calibration started' if success else 'Failed to start weight calibration'
            }
        else:
            return {
                'success': False,
                'error': f'Unknown weight action: {action}. Valid action: calibrate'
            } 