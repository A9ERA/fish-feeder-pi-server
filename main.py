#!/usr/bin/env python3
"""
Main entry point for Pi Server
"""
import sys
import os
from pathlib import Path
import time
import threading
import webbrowser
import subprocess
import shutil
import socket

# Add src to path
sys.path.append(str(Path(__file__).parent / 'src'))

from src.services.api_service import APIService
from src.services.firebase_service import FirebaseService
from src.services.serial_service import SerialService
from src.config.settings import PORT

def wait_for_port(host, port, timeout=30):
    """Wait until a TCP port is open or timeout occurs."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except Exception:
            time.sleep(0.5)
    return False

def open_web_ui(url):
    """Open URL using a GUI browser on Raspberry Pi.

    Priority:
    1) chromium-browser/chromium/google-chrome
    2) xdg-open
    3) Python webbrowser (fallback, may be text-mode)
    """
    print(f"🌐 Opening Web UI: {url}")

    # 1) Try Chromium-family browsers directly to ensure GUI
    try:
        for browser in ['chromium-browser', 'chromium', 'google-chrome']:
            path = shutil.which(browser)
            if path:
                subprocess.Popen([path, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"✅ Web UI opened via {browser}")
                return True
    except Exception as e:
        print(f"⚠️ Chromium open failed: {e}")

    # 2) Try xdg-open if available
    try:
        if shutil.which('xdg-open'):
            subprocess.Popen(['xdg-open', url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("✅ Web UI opened via xdg-open")
            return True
    except Exception as e:
        print(f"⚠️ xdg-open failed: {e}")

    # 3) Fallback to Python webbrowser
    try:
        if webbrowser.open(url, new=2):
            print("✅ Web UI open command sent via webbrowser")
            return True
    except Exception as e:
        print(f"❌ webbrowser failed: {e}")

    return False

def main():
    """Main function to start the server"""
    print("🐟 Fish Feeder System - Raspberry Pi Server")
    print("=" * 50)
    
    # Initialize services
    serial_service = None
    api_service = None
    api_thread = None
    last_serial_check = time.time()
    serial_check_interval = 30  # Check serial connection every 30 seconds
    
    try:
        # Initialize serial service with retry mechanism
        print("🔌 Initializing Serial Service...")
        serial_service = SerialService()
        
        max_startup_attempts = 3
        startup_attempt = 0
        
        while startup_attempt < max_startup_attempts:
            if serial_service.start():
                print("✅ Serial service started successfully")
                break
            else:
                startup_attempt += 1
                if startup_attempt < max_startup_attempts:
                    print(f"⚠️ Serial service startup failed. Retrying in 5 seconds... (attempt {startup_attempt}/{max_startup_attempts})")
                    time.sleep(5)
                else:
                    print(f"❌ Failed to start serial service after {max_startup_attempts} attempts")
                    print("💡 The server will continue running, but Arduino functionality will be limited")
                    print("💡 You can try reconnecting Arduino and restart the server")
        
        # Initialize API service
        print("🌐 Initializing API Service...")
        api_service = APIService(serial_service=serial_service)
        
        # Start API service in a separate thread
        print("🚀 Starting API server...")
        print(f"📡 Server will be available at: http://localhost:{api_service.port}")
        print("🔧 Press Ctrl+C to stop the server")
        print("=" * 50)
        
        # Start the API server in a daemon thread
        api_thread = threading.Thread(target=api_service.start, daemon=True)
        api_thread.start()
        
        # Give the API server time to start
        time.sleep(2)

        # Attempt to open remote Web UI once API port is ready
        url_to_open = 'https://fish-feeder-test-1.web.app/'
        if wait_for_port('127.0.0.1', api_service.port, timeout=15):
            open_web_ui(url_to_open)
        else:
            print("⚠️ API port not ready within timeout; attempting to open Web UI anyway")
            open_web_ui(url_to_open)
        
        # Main monitoring loop
        print("🔍 Starting connection monitoring...")
        while True:
            try:
                # Check if API thread is still running
                if api_thread and not api_thread.is_alive():
                    print("❌ API server thread has stopped unexpectedly")
                    break
                
                # Periodically check serial connection health
                current_time = time.time()
                if current_time - last_serial_check > serial_check_interval:
                    if serial_service:
                        connection_status = serial_service.get_connection_status()
                        if not connection_status.get('healthy', False) or not connection_status.get('is_open', False):
                            print("⚠️ Serial connection appears unhealthy, attempting recovery...")
                            
                            # Try to restart the serial service
                            if serial_service.restart():
                                print("✅ Serial service recovered successfully")
                            else:
                                print("❌ Serial service recovery failed")
                                print("💡 Please check Arduino connection and restart server if needed")
                    
                    last_serial_check = current_time
                
                # Sleep for a short time to prevent busy waiting
                time.sleep(1)
                    
            except Exception as loop_error:
                print(f"❌ Error in monitoring loop: {loop_error}")
                print("🔄 Continuing to monitor...")
                time.sleep(5)
        
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup services
        try:
            if api_service and hasattr(api_service, 'scheduler_service'):
                print("⏰ Stopping scheduler service...")
                api_service.scheduler_service.stop()
        except Exception as cleanup_error:
            print(f"⚠️ Error stopping scheduler service: {cleanup_error}")
        
        try:
            if serial_service:
                print("🔌 Stopping serial service...")
                serial_service.stop()
        except Exception as cleanup_error:
            print(f"⚠️ Error stopping serial service: {cleanup_error}")
        
        print("👋 Server shutdown complete")
        sys.exit(1)

if __name__ == "__main__":
    main() 