#!/usr/bin/env python3
"""
🚀 PRODUCTION STARTER - FIXED VERSION
JSON format support for Arduino
"""

import os
import sys
import subprocess

def check_requirements():
    """Check if all requirements are met"""
    print("[CHECK] Checking Production Requirements...")
    
    # Check firebase-key.json
    if not os.path.exists('config/firebase-key.json'):
        print("[ERROR] config/firebase-key.json not found!")
        print("[TIP] Download from Firebase Console > Project Settings > Service accounts")
        return False
    
    # Check .env file
    if not os.path.exists('config/.env'):
        print("[WARNING] config/.env file not found, creating default...")
        with open('config/.env', 'w') as f:
            f.write("SERIAL_PORT=COM3\nBAUD_RATE=9600\n")
        print("[OK] config/.env created with default COM3 settings")
    
    print("[OK] All requirements met!")
    return True

def main():
    # Get script directory and change to it
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    print(f"[DIR] Working directory: {script_dir}")
    
    print("COMPLETE FISH FEEDER SYSTEM")
    print("=" * 60)
    print("Firebase Sync + API Server")
    print("Web Compatible Endpoints")
    print("=" * 60)
    
    if not check_requirements():
        print("[ERROR] Requirements not met. Please fix and try again.")
        return
    
    print("[START] Starting COMPLETE system...")
    print("Web: https://fish-feeder-test-1.web.app")
    print("Sensors: Every 5 seconds")
    print("API: Port 5000")
    print("Commands: Real-time")
    print("=" * 60)
    
    # Start COMPLETE system (Firebase + API)
    try:
        subprocess.run([sys.executable, 'start_complete_system.py'], check=True)
    except KeyboardInterrupt:
        print("\n[STOP] System stopped by user")
    except Exception as e:
        print(f"[ERROR] System error: {e}")

if __name__ == "__main__":
    main() 