"""
Main entry point for the Pi MQTT Server application
"""
from src.services.mqtt_service import MQTTService
from src.services.command_service import CommandService
from src.services.api_service import APIService
from src.config.settings import APP_NAME, DEBUG
import threading

def main():
    print(f"Starting {APP_NAME}...")
    if DEBUG:
        print("Running in DEBUG mode")

    # Initialize MQTT service
    mqtt_service = MQTTService()
    mqtt_service.connect()

    # Initialize and start command service
    # command_service = CommandService(mqtt_service)
    # command_service.start()

    # Initialize and start API service in a separate thread
    api_service = APIService()
    api_thread = threading.Thread(target=api_service.start, daemon=True)
    api_thread.start()
    print("API server started on http://0.0.0.0:5000")

    try:
        # Start MQTT loop (this will block)
        mqtt_service.start_loop()
    except KeyboardInterrupt:
        print("\nShutting down...")
        command_service.stop()
        print("Shutdown complete")

if __name__ == "__main__":
    main() 