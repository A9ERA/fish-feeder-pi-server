#!/usr/bin/env python3
"""
Interactive Arduino Control Test Script
Allows manual sending of control commands to Arduino
"""

import serial
import serial.tools.list_ports
import time
import sys
import os

# Add the src directory to the path so we can import our utils
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from utils.arduino_detector import find_arduino_port, list_all_ports

def display_menu():
    """Display the command menu"""
    print("\n" + "=" * 50)
    print("Arduino Device Control - Interactive Mode")
    print("=" * 50)
    print("BLOWER CONTROLS:")
    print("  1. Start blower")
    print("  2. Stop blower")
    print("  3. Set blower speed (custom)")
    print("  4. Set blower direction to reverse")
    print("  5. Set blower direction to normal")
    print()
    print("FEEDER MOTOR CONTROLS:")
    print("  6. Open feeder motor")
    print("  7. Close feeder motor")
    print()
    print("TESTING:")
    print("  9. Run full automatic test")
    print(" 10. Send custom command")
    print()
    print("  0. Exit")
    print("=" * 50)

def send_command(ser, command):
    """Send a command to Arduino and show response"""
    print(f"\nSending: {command.strip()}")
    try:
        ser.write(command.encode('utf-8'))
        time.sleep(0.3)
        
        # Check for response
        if ser.in_waiting > 0:
            response = ser.readline().decode('utf-8').strip()
            print(f"Arduino response: {response}")
        else:
            print("No response from Arduino")
            
        print("Command sent successfully!")
        
    except Exception as e:
        print(f"Error sending command: {e}")

def run_automatic_test(ser):
    """Run the full automatic test suite"""
    print("\n=== Running Automatic Test ===")
    
    commands = [
        "[control]:blower:start\n",
        "[control]:blower:speed:150\n",
        "[control]:blower:direction:reverse\n",
        "[control]:blower:direction:normal\n",
        "[control]:blower:stop\n",
        "[control]:feedermotor:open\n",
        "[control]:feedermotor:close\n",
    ]
    
    for i, cmd in enumerate(commands, 1):
        print(f"\nStep {i}/{len(commands)}: {cmd.strip()}")
        send_command(ser, cmd)
        time.sleep(1)
    
    print("\n=== Automatic test completed ===")

def get_custom_speed():
    """Get custom speed value from user"""
    while True:
        try:
            speed = int(input("Enter speed value (0-255): "))
            if 0 <= speed <= 255:
                return speed
            else:
                print("Speed must be between 0 and 255")
        except ValueError:
            print("Please enter a valid number")

def main():
    # Configuration
    BAUD_RATE = 9600
    
    print("🤖 Arduino Interactive Control Test")
    print("=" * 50)
    
    # Auto-detect Arduino port
    print("🔍 Searching for Arduino...")
    arduino_port = find_arduino_port()
    
    if not arduino_port:
        print("❌ No Arduino found!")
        print("\n📋 Available ports:")
        list_all_ports()
        print("💡 Please connect your Arduino and try again.")
        return
    
    print(f"✅ Using Arduino at: {arduino_port}")
    print(f"📊 Baud Rate: {BAUD_RATE}")
    print("🔌 Connecting to Arduino...")
    
    try:
        # Connect to Arduino
        ser = serial.Serial(arduino_port, BAUD_RATE, timeout=2)
        time.sleep(2)  # Wait for Arduino to reset
        print("✅ Connected successfully!")
        
        while True:
            display_menu()
            
            try:
                choice = input("\nEnter your choice (0-10): ").strip()
                
                if choice == "0":
                    print("👋 Exiting...")
                    break
                    
                elif choice == "1":
                    send_command(ser, "[control]:blower:start\n")
                    
                elif choice == "2":
                    send_command(ser, "[control]:blower:stop\n")
                    
                elif choice == "3":
                    speed = get_custom_speed()
                    if speed is not None:
                        send_command(ser, f"[control]:blower:speed:{speed}\n")
                    
                elif choice == "4":
                    send_command(ser, "[control]:blower:direction:reverse\n")
                    
                elif choice == "5":
                    send_command(ser, "[control]:blower:direction:normal\n")
                    
                elif choice == "6":
                    send_command(ser, "[control]:feedermotor:open\n")
                    
                elif choice == "7":
                    send_command(ser, "[control]:feedermotor:close\n")
                    
                elif choice == "9":
                    run_automatic_test(ser)
                    
                elif choice == "10":
                    custom_command = input("Enter custom command: ")
                    if not custom_command.endswith('\n'):
                        custom_command += '\n'
                    send_command(ser, custom_command)
                    
                else:
                    print("❌ Invalid choice. Please try again.")
                    
            except KeyboardInterrupt:
                print("\n⚠️  Returning to menu...")
                continue
                
    except serial.SerialException as e:
        print(f"❌ Error connecting to Arduino: {e}")
        print("💡 Make sure:")
        print("   • Arduino is connected")
        print("   • Arduino drivers are installed")
        print("   • Arduino is not being used by another application")
    except KeyboardInterrupt:
        print("\n⚠️  Program interrupted by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("🔌 Serial connection closed")

if __name__ == "__main__":
    main() 