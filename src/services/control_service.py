"""
Control Service for sending commands to Arduino devices
"""
import threading
from typing import Optional
from src.services.serial_service import SerialService

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

    def control_auger(self, action: str) -> bool:
        """
        Control auger with a single method
        
        Args:
            action: Action to perform ('forward', 'backward', 'stop', 'speedtest')
        """
        if action == "forward":
            return self.auger_forward()
        elif action == "backward":
            return self.auger_backward()
        elif action == "stop":
            return self.auger_stop()
        elif action == "speedtest":
            return self.auger_speedtest()
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

    # Legacy method name compatibility
    def control_actuator_motor(self, action: str) -> bool:
        """
        Legacy method name for actuator control
        Redirects to control_actuator for backward compatibility
        """
        return self.control_actuator(action) 