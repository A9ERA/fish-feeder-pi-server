#!/usr/bin/env python3
"""
Test script to verify serial service fixes for disconnection handling
"""
import sys
import os
from pathlib import Path
import time
import threading

# Add src to path
sys.path.append(str(Path(__file__).parent / 'src'))

from src.services.serial_service import SerialService

def test_serial_disconnection_handling():
    """Test serial service handling of disconnection scenarios"""
    print("🧪 Testing Serial Service Disconnection Handling")
    print("=" * 60)
    
    # Initialize serial service
    print("🔌 Initializing Serial Service...")
    serial_service = SerialService()
    
    # Test 1: Start service
    print("\n📋 Test 1: Starting Serial Service")
    if serial_service.start():
        print("✅ Serial service started successfully")
    else:
        print("❌ Failed to start serial service")
        print("💡 Make sure Arduino is connected and try again")
        return
    
    # Test 2: Connection status
    print("\n📋 Test 2: Connection Status Check")
    status = serial_service.get_connection_status()
    print(f"   Connection Status: {status}")
    
    # Test 3: Send a test command
    print("\n📋 Test 3: Send Test Command")
    if serial_service.send_command("sensors:status"):
        print("✅ Test command sent successfully")
    else:
        print("❌ Failed to send test command")
    
    # Test 4: Monitor for disconnect scenarios
    print("\n📋 Test 4: Monitoring for Disconnect Events")
    print("💡 Now you can:")
    print("   1. Disconnect Arduino USB cable")
    print("   2. Wait for error messages")
    print("   3. Reconnect Arduino USB cable")
    print("   4. Watch for auto-reconnection")
    print("   5. Press Ctrl+C to stop monitoring")
    
    monitor_thread = threading.Thread(target=monitor_connection, args=(serial_service,), daemon=True)
    monitor_thread.start()
    
    try:
        # Keep the main thread alive to monitor
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping test...")
        serial_service.stop()
        print("✅ Test completed")

def monitor_connection(serial_service):
    """Monitor connection status and log changes"""
    last_status = None
    
    while True:
        try:
            status = serial_service.get_connection_status()
            current_status = f"Connected: {status.get('connected', False)}, Open: {status.get('is_open', False)}, Healthy: {status.get('healthy', False)}"
            
            if current_status != last_status:
                timestamp = time.strftime("%H:%M:%S")
                print(f"[{timestamp}] 📊 Status Change: {current_status}")
                last_status = current_status
            
            time.sleep(2)  # Check every 2 seconds
        except Exception as e:
            print(f"❌ Error monitoring connection: {e}")
            time.sleep(5)

if __name__ == "__main__":
    test_serial_disconnection_handling() 