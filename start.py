#!/usr/bin/env python3
"""
🚀 FISH FEEDER IoT - MAIN LAUNCHER
Quick start for production system
"""

import os
import sys
import subprocess

def main():
    print("🐟 FISH FEEDER IoT SYSTEM")
    print("=" * 60)
    print("🚀 Starting Production System...")
    print("📂 Location: production/")
    print("🌍 Web: https://fish-feeder-test-1.web.app")
    print("=" * 60)
    
    # Change to production directory
    production_dir = os.path.join(os.path.dirname(__file__), 'production')
    
    if not os.path.exists(production_dir):
        print("❌ Production directory not found!")
        return
    
    # Change to production directory and run
    original_dir = os.getcwd()
    os.chdir(production_dir)
    
    try:
        subprocess.run([sys.executable, 'start_production_fixed.py'], check=True)
    except KeyboardInterrupt:
        print("\n🛑 System stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        os.chdir(original_dir)

if __name__ == "__main__":
    main() 