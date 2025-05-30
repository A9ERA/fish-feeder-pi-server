#!/usr/bin/env python3
"""
Arduino Port Detection Utility

This script helps detect and test Arduino connections on your system.
Can be run standalone for debugging serial connection issues.
"""
import serial
import serial.tools.list_ports
import sys
from typing import Optional, List

def find_arduino_port() -> Optional[str]:
    """
    Automatically find Arduino port by checking connected devices
    
    Returns:
        str: Arduino port device path if found, None otherwise
    """
    ports = serial.tools.list_ports.comports()
    for port in ports:
        # เช็กจาก description หรือ VID/PID ที่มักใช้กับ Arduino
        if ("Arduino" in port.description or 
            "CH340" in port.description or 
            "ttyUSB" in port.device or
            "ttyACM" in port.device or
            "FT232" in port.description or
            "CP210" in port.description):
            print(f"✅ Arduino found at {port.device} ({port.description})")
            return port.device
    
    print("❌ No Arduino device found")
    return None

def list_all_ports() -> List:
    """
    List all available serial ports
    
    Returns:
        List of port info objects
    """
    ports = serial.tools.list_ports.comports()
    print("\n📋 Available serial ports:")
    if not ports:
        print("  No serial ports found")
    else:
        for i, port in enumerate(ports, 1):
            print(f"  {i}. {port.device}")
            print(f"     Description: {port.description}")
            print(f"     Manufacturer: {port.manufacturer}")
            if hasattr(port, 'vid') and port.vid:
                print(f"     VID:PID: {port.vid:04X}:{port.pid:04X}")
            print()
    
    return ports

def test_connection(port: str, baud_rate: int = 9600) -> bool:
    """
    Test connection to a specific port
    
    Args:
        port: Serial port to test
        baud_rate: Baud rate for testing
        
    Returns:
        bool: True if connection successful
    """
    try:
        print(f"🔌 Testing connection to {port} at {baud_rate} baud...")
        with serial.Serial(port=port, baudrate=baud_rate, timeout=2) as ser:
            print(f"✅ Successfully connected to {port}")
            print(f"   Port is open: {ser.is_open}")
            print(f"   Timeout: {ser.timeout}s")
            return True
    except Exception as e:
        print(f"❌ Failed to connect to {port}: {e}")
        return False

def main():
    """Main function for the Arduino detector utility"""
    print("🤖 Arduino Port Detection Utility")
    print("=" * 40)
    
    # List all ports
    list_all_ports()
    
    # Try to find Arduino
    print("🔍 Searching for Arduino devices...")
    arduino_port = find_arduino_port()
    
    if arduino_port:
        # Test connection
        if test_connection(arduino_port):
            print(f"\n🎉 Arduino is ready at {arduino_port}!")
        else:
            print(f"\n⚠️  Arduino detected at {arduino_port} but connection failed")
    else:
        print("\n🚫 No Arduino devices detected")
        print("\n💡 Troubleshooting tips:")
        print("   • Make sure Arduino is connected via USB")
        print("   • Install Arduino drivers if needed")
        print("   • Try a different USB cable")
        print("   • Check if another application is using the port")

if __name__ == "__main__":
    main() 