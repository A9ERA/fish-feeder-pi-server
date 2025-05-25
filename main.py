"""
Main entry point for the Pi MQTT Server application
"""
from src.services.serial_service import SerialService
from src.services.api_service import APIService
from src.config.settings import APP_NAME, DEBUG
import threading

def main():
    print(f"Starting {APP_NAME}...")
    if DEBUG:
        print("Running in DEBUG mode")

    # Initialize Serial service
    serial_service = SerialService()
    if not serial_service.start():
        print("Failed to start Serial service. Please check your USB connection.")
        return

    # Initialize and start API service in a separate thread
    # api_service = APIService()
    # api_thread = threading.Thread(target=api_service.start, daemon=True)
    # api_thread.start()
    # print("API server started on http://0.0.0.0:5000")

    try:
        # Keep the main thread alive
        while True:
            threading.Event().wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
        serial_service.stop()
        print("Shutdown complete")

if __name__ == "__main__":
    main() 