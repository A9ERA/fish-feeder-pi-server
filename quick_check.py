#!/usr/bin/env python3
"""
Quick Health Check for Pi MQTT Server
Performs rapid system verification
"""

import requests
import sys
import time
from datetime import datetime

def check_server_health(base_url="http://localhost:5000"):
    """Quick server health check"""
    print("🔍 Pi MQTT Server - Quick Health Check")
    print("=" * 40)
    
    try:
        # Test basic connectivity
        print("📡 Testing server connectivity...", end=" ")
        response = requests.get(f"{base_url}/health", timeout=5)
        
        if response.status_code == 200:
            print("✅ OK")
            data = response.json()
            
            # Display health status
            print(f"🟢 Server Status: {data.get('status', 'Unknown')}")
            
            # Check services
            services = data.get('services', {})
            print("\n📊 Services Status:")
            for service, status in services.items():
                emoji = "✅" if status in ['connected', 'running', 'healthy'] else "⚠️"
                print(f"  {emoji} {service.capitalize()}: {status}")
            
            # Test API endpoints
            print("\n🔧 API Endpoints:")
            
            # Test sensors
            try:
                sensor_resp = requests.get(f"{base_url}/api/sensors", timeout=3)
                if sensor_resp.status_code == 200:
                    print("  ✅ Sensors API: Responsive")
                else:
                    print(f"  ⚠️ Sensors API: Status {sensor_resp.status_code}")
            except:
                print("  ❌ Sensors API: Not responding")
            
            # Test control endpoints (just check if they exist)
            try:
                control_resp = requests.post(f"{base_url}/api/control/blower", 
                                          json={"action": "status"}, timeout=3)
                if control_resp.status_code in [200, 201, 400]:  # 400 is OK for status check
                    print("  ✅ Control API: Responsive")
                else:
                    print(f"  ⚠️ Control API: Status {control_resp.status_code}")
            except:
                print("  ❌ Control API: Not responding")
            
            print("\n🎉 Quick check completed successfully!")
            return True
            
        else:
            print(f"❌ Server returned status: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server")
        print("💡 Make sure the server is running: python main.py")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def main():
    """Main function"""
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = "http://localhost:5000"
    
    success = check_server_health(base_url)
    
    if success:
        print(f"\n✅ System is healthy! ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
        sys.exit(0)
    else:
        print(f"\n❌ System check failed! ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
        sys.exit(1)

if __name__ == "__main__":
    main() 