"""
Control Service for sending commands to Arduino devices
"""
import threading
from typing import Optional
from src.services.serial_service import SerialService
from src.config.settings import SERIAL_PORT, BAUD_RATE

class ControlService:
    def __init__(self, serial_service: Optional[SerialService] = None):
        """
        Initialize Control Service
        
        Args:
            serial_service: Optional SerialService instance. If None, creates a new one.
        """
        self.serial_service = serial_service
        self._lock = threading.Lock()

    def _send_command(self, command: str) -> bool:
        """
        Send a command to the Arduino via serial
        
        Args:
            command: Command string to send
            
        Returns:
            bool: True if command sent successfully, False otherwise
        """
        if not self.serial_service or not self.serial_service.serial or not self.serial_service.serial.is_open:
            print("Serial connection not available")
            return False

        try:
            with self._lock:
                full_command = f"[control]:{command}\n"
                self.serial_service.serial.write(full_command.encode('utf-8'))
                print(f"[Control Service] Sent command: {full_command.strip()}")
                return True
        except Exception as e:
            print(f"Error sending command: {e}")
            return False

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

    # Actuator motor control methods
    def actuator_motor_up(self) -> bool:
        """Move actuator motor up"""
        return self._send_command("actuatormotor:up")

    def actuator_motor_down(self) -> bool:
        """Move actuator motor down"""
        return self._send_command("actuatormotor:down")

    def actuator_motor_stop(self) -> bool:
        """Stop actuator motor"""
        return self._send_command("actuatormotor:stop")

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

    def control_actuator_motor(self, action: str) -> bool:
        """
        Control actuator motor with a single method
        
        Args:
            action: Action to perform ('up', 'down', 'stop')
        """
        if action == "up":
            return self.actuator_motor_up()
        elif action == "down":
            return self.actuator_motor_down()
        elif action == "stop":
            return self.actuator_motor_stop()
        else:
            print(f"Unknown actuator motor action: {action}")
            return False 