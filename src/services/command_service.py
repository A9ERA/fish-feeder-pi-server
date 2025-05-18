"""
Command Service for handling command operations
"""
import time
import threading
from src.config.settings import COMMANDS, COMMAND_INTERVAL, TOPIC_PUB

class CommandService:
    def __init__(self, mqtt_service):
        """
        Initialize Command Service
        
        Args:
            mqtt_service: MQTTService instance for publishing commands
        """
        self.mqtt_service = mqtt_service
        self.command_thread = None
        self._stop_event = threading.Event()

    def send_command_loop(self):
        """Send commands in a loop"""
        i = 0
        while not self._stop_event.is_set():
            command = COMMANDS[i % len(COMMANDS)]
            self.mqtt_service.publish(TOPIC_PUB, command)
            print(f"Published command: {command}")
            i += 1
            time.sleep(COMMAND_INTERVAL)

    def start(self):
        """Start the command service in a separate thread"""
        self._stop_event.clear()
        self.command_thread = threading.Thread(target=self.send_command_loop, daemon=True)
        self.command_thread.start()

    def stop(self):
        """Stop the command service"""
        self._stop_event.set()
        if self.command_thread:
            self.command_thread.join() 