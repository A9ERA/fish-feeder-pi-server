#!/usr/bin/env python3
"""
🚀 COMPLETE SYSTEM STARTER
รัน Flask API + Firebase Sync พร้อมกัน
"""

import subprocess
import threading
import time
import sys
import signal
import os

class CompleteFishFeederSystem:
    def __init__(self):
        self.processes = []
        self.running = True
        
    def start_firebase_sync(self):
        """Start Firebase sync process"""
        print("[START] Starting Firebase Sync...")
        try:
            proc = subprocess.Popen([
                sys.executable, 'firebase_production_sync_fixed.py'
            ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            
            self.processes.append(proc)
            
            # Monitor output
            for line in iter(proc.stdout.readline, ''):
                if not self.running:
                    break
                if line.strip():
                    print(f"[FIREBASE] {line.strip()}")
                    
        except Exception as e:
            print(f"[ERROR] Firebase sync failed: {e}")
    
    def start_flask_api(self):
        """Start Flask API server"""
        print("[START] Starting Flask API Server...")
        try:
            proc = subprocess.Popen([
                sys.executable, 'api/flask_api_server.py'
            ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            
            self.processes.append(proc)
            
            # Monitor output
            for line in iter(proc.stdout.readline, ''):
                if not self.running:
                    break
                if line.strip():
                    print(f"[API] {line.strip()}")
                    
        except Exception as e:
            print(f"[ERROR] Flask API failed: {e}")
    
    def signal_handler(self, sig, frame):
        """Handle shutdown signals"""
        print("\n[STOP] Shutting down system...")
        self.running = False
        
        for proc in self.processes:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except:
                proc.kill()
        
        print("[OK] System shutdown complete")
        sys.exit(0)
    
    def run(self):
        """Run complete system"""
        print("COMPLETE FISH FEEDER SYSTEM")
        print("=" * 60)
        print("Firebase Sync: Real-time data")
        print("Flask API: Port 5000")
        print("Web App: https://fish-feeder-test-1.web.app")
        print("Press Ctrl+C to stop")
        print("=" * 60)
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Start services in separate threads
        firebase_thread = threading.Thread(target=self.start_firebase_sync, daemon=True)
        flask_thread = threading.Thread(target=self.start_flask_api, daemon=True)
        
        firebase_thread.start()
        time.sleep(2)  # Give Firebase a head start
        flask_thread.start()
        
        # Keep main thread alive
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.signal_handler(signal.SIGINT, None)

if __name__ == "__main__":
    # Get script directory and change to it
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    print(f"[DIR] Working directory: {script_dir}")
    
    # Check requirements
    if not os.path.exists('config/firebase-key.json'):
        print("[ERROR] config/firebase-key.json not found!")
        print(f"[TIP] Expected path: {os.path.abspath('config/firebase-key.json')}")
        sys.exit(1)
    
    if not os.path.exists('config/.env'):
        print("[WARNING] Creating default config/.env file...")
        with open('config/.env', 'w') as f:
            f.write("SERIAL_PORT=COM3\nBAUD_RATE=9600\n")
    
    print("[OK] All configuration files found!")
    
    # Start complete system
    system = CompleteFishFeederSystem()
    system.run() 