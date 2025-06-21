#!/usr/bin/env python3
"""
Test script for Serial Service Auto-Reconnection
This script demonstrates and tests the auto-reconnection functionality
"""

import sys
import os
import time
import threading
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.services.serial_service import SerialService

def test_serial_recovery():
    """Test serial service auto-reconnection functionality"""
    print("🧪 Serial Service Auto-Reconnection Test")
    print("=" * 50)
    
    # Initialize serial service
    print("🔌 Initializing Serial Service...")
    serial_service = SerialService()
    
    # Start serial service
    print("🚀 Starting Serial Service...")
    if not serial_service.start():
        print("❌ Failed to start serial service")
        print("💡 Make sure Arduino is connected and try again")
        return False
    
    print("✅ Serial service started successfully")
    print(f"📡 Connected to: {serial_service.port}")
    
    # Test normal operation
    print("\n🔍 Testing normal operation...")
    for i in range(3):
        success = serial_service.send_command("sensors:status")
        if success:
            print(f"✅ Command {i+1}/3 sent successfully")
        else:
            print(f"❌ Command {i+1}/3 failed")
        time.sleep(1)
    
    # Monitor connection status
    print("\n📊 Monitoring connection status...")
    print("💡 Disconnect and reconnect Arduino cable to test auto-reconnection")
    print("🔧 Press Ctrl+C to stop monitoring")
    
    try:
        monitor_count = 0
        while True:
            monitor_count += 1
            
            # Check connection status
            status = serial_service.get_connection_status()
            health_status = "✅ HEALTHY" if status.get('healthy') else "❌ UNHEALTHY"
            connection_status = "🔗 CONNECTED" if status.get('is_open') else "🔌 DISCONNECTED"
            
            print(f"\n📋 Status Check #{monitor_count} - {time.strftime('%H:%M:%S')}")
            print(f"   Port: {status.get('port', 'N/A')}")
            print(f"   Health: {health_status}")
            print(f"   Connection: {connection_status}")
            
            # Try to send a test command
            print("   🔍 Testing command transmission...")
            success = serial_service.send_command("sensors:status")
            if success:
                print("   ✅ Command sent successfully")
            else:
                print("   ❌ Command failed")
            
            # Wait before next check
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\n🛑 Monitoring stopped by user")
    
    # Stop serial service
    print("\n🛑 Stopping Serial Service...")
    serial_service.stop()
    print("✅ Serial service stopped")
    
    return True

def test_connection_health():
    """Test connection health checking"""
    print("\n🩺 Connection Health Test")
    print("-" * 30)
    
    serial_service = SerialService()
    
    # Test without connection
    print("🔍 Testing health check without connection...")
    health = serial_service.check_connection_health()
    print(f"Health status (no connection): {'✅ HEALTHY' if health else '❌ UNHEALTHY'}")
    
    # Test with connection
    print("\n🔍 Testing health check with connection...")
    if serial_service.connect():
        health = serial_service.check_connection_health()
        print(f"Health status (with connection): {'✅ HEALTHY' if health else '❌ UNHEALTHY'}")
        
        # Get detailed status
        status = serial_service.get_connection_status()
        print(f"\n📊 Detailed Status:")
        for key, value in status.items():
            print(f"   {key}: {value}")
        
        serial_service.disconnect()
    else:
        print("❌ Failed to connect for health test")

def main():
    """Main test function"""
    print("🐟 Fish Feeder Serial Recovery Test Suite")
    print("=" * 60)
    
    try:
        # Test 1: Connection health
        test_connection_health()
        
        print("\n" + "=" * 60)
        
        # Test 2: Auto-reconnection
        if input("\n🔄 Start auto-reconnection test? (y/n): ").lower() == 'y':
            test_serial_recovery()
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n✅ All tests completed!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 