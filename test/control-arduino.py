#!/usr/bin/env python3
"""
Test script for sending control commands to Arduino
Tests the device control functionality matching the controlSensor() function
"""

import serial
import time
import sys

def send_command(ser, command):
    """Send a command and display the result"""
    print(f"Sending: {command.strip()}")
    ser.write(command.encode('utf-8'))
    time.sleep(0.5)  # Short delay between commands
    
    # Try to read any response from Arduino
    if ser.in_waiting > 0:
        response = ser.readline().decode('utf-8').strip()
        print(f"Response: {response}")
    print("-" * 40)

def test_blower_controls(ser):
    """Test all blower control commands"""
    print("=== Testing Blower Controls ===")
    
    # Test blower start
    send_command(ser, "[control]:blower:start\n")
    
    # Test blower speed
    send_command(ser, "[control]:blower:speed:100\n")
    
    # Test blower speed with different value
    send_command(ser, "[control]:blower:speed:200\n")
    
    # Test blower direction - reverse
    send_command(ser, "[control]:blower:direction:reverse\n")
    
    # Test blower direction - normal
    send_command(ser, "[control]:blower:direction:normal\n")
    
    # Test blower stop
    send_command(ser, "[control]:blower:stop\n")

def test_actuator_controls(ser):
    """Test all actuator motor control commands"""
    print("=== Testing Actuator Motor Controls ===")
    
    # Test actuator up
    send_command(ser, "[control]:actuatormotor:up\n")
    
    # Wait a bit
    time.sleep(1)
    
    # Test actuator stop
    send_command(ser, "[control]:actuatormotor:stop\n")
    
    # Test actuator down
    send_command(ser, "[control]:actuatormotor:down\n")
    
    # Wait a bit
    time.sleep(1)
    
    # Test actuator stop
    send_command(ser, "[control]:actuatormotor:stop\n")

def test_invalid_commands(ser):
    """Test invalid commands to see how Arduino handles them"""
    print("=== Testing Invalid Commands (should be ignored) ===")
    
    # Invalid device
    send_command(ser, "[control]:unknown:start\n")
    
    # Invalid action
    send_command(ser, "[control]:blower:invalid\n")
    
    # Missing control prefix
    send_command(ser, "blower:start\n")

def main():
    # Configuration
    SERIAL_PORT = '/dev/ttyUSB0'  # Change this to match your Arduino port
    BAUD_RATE = 9600
    
    print(f"Arduino Control Test Script")
    print(f"Port: {SERIAL_PORT}, Baud Rate: {BAUD_RATE}")
    print("=" * 50)
    
    try:
        # Connect to Arduino
        print("Connecting to Arduino...")
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)
        time.sleep(2)  # Wait for Arduino to reset
        print("Connected successfully!")
        print("=" * 50)
        
        # Test blower controls
        test_blower_controls(ser)
        time.sleep(1)
        
        # Test actuator controls
        test_actuator_controls(ser)
        time.sleep(1)
        
        # Test invalid commands
        test_invalid_commands(ser)
        
        print("=== Test completed ===")
        
    except serial.SerialException as e:
        print(f"Error connecting to Arduino: {e}")
        print("Make sure:")
        print("1. Arduino is connected")
        print("2. Correct port is specified")
        print("3. Arduino is not being used by another application")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("Serial connection closed")

if __name__ == "__main__":
    main()
