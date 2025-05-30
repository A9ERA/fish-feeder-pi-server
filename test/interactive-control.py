#!/usr/bin/env python3
"""
Interactive Arduino Control Test Script
Allows manual sending of control commands to Arduino
"""

import serial
import time
import sys

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
    print("ACTUATOR MOTOR CONTROLS:")
    print("  6. Move actuator up")
    print("  7. Move actuator down")
    print("  8. Stop actuator motor")
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
        "[control]:actuatormotor:up\n",
        "[control]:actuatormotor:stop\n",
        "[control]:actuatormotor:down\n",
        "[control]:actuatormotor:stop\n"
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
    SERIAL_PORT = '/dev/ttyUSB0'  # Change this to match your Arduino port
    BAUD_RATE = 9600
    
    print("Arduino Interactive Control Test")
    print(f"Connecting to {SERIAL_PORT} at {BAUD_RATE} baud...")
    
    try:
        # Connect to Arduino
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)
        time.sleep(2)  # Wait for Arduino to reset
        print("Connected successfully!")
        
        while True:
            display_menu()
            
            try:
                choice = input("\nEnter your choice (0-10): ").strip()
                
                if choice == "0":
                    print("Exiting...")
                    break
                    
                elif choice == "1":
                    send_command(ser, "[control]:blower:start\n")
                    
                elif choice == "2":
                    send_command(ser, "[control]:blower:stop\n")
                    
                elif choice == "3":
                    speed = get_custom_speed()
                    send_command(ser, f"[control]:blower:speed:{speed}\n")
                    
                elif choice == "4":
                    send_command(ser, "[control]:blower:direction:reverse\n")
                    
                elif choice == "5":
                    send_command(ser, "[control]:blower:direction:normal\n")
                    
                elif choice == "6":
                    send_command(ser, "[control]:actuatormotor:up\n")
                    
                elif choice == "7":
                    send_command(ser, "[control]:actuatormotor:down\n")
                    
                elif choice == "8":
                    send_command(ser, "[control]:actuatormotor:stop\n")
                    
                elif choice == "9":
                    run_automatic_test(ser)
                    
                elif choice == "10":
                    custom_cmd = input("Enter custom command: ")
                    if not custom_cmd.endswith('\n'):
                        custom_cmd += '\n'
                    send_command(ser, custom_cmd)
                    
                else:
                    print("Invalid choice. Please try again.")
                    
            except KeyboardInterrupt:
                print("\nOperation cancelled")
                continue
                
    except serial.SerialException as e:
        print(f"Error connecting to Arduino: {e}")
        print("\nTroubleshooting:")
        print("1. Check if Arduino is connected")
        print("2. Verify the correct port (ls /dev/tty* on Linux/Mac)")
        print("3. Make sure no other application is using the port")
        print("4. Try different baud rates if needed")
        sys.exit(1)
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("Serial connection closed")

if __name__ == "__main__":
    main() 