#!/usr/bin/env python3
"""
Main entry point for Pi Server
"""
import sys
import os
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / 'src'))

from src.services.api_service import APIService
from src.services.firebase_service import FirebaseService
from src.services.serial_service import SerialService

def main():
    """Main function to start the server"""
    print("🚀 Starting Pi Server...")
    
    try:
        # Initialize services
        print("🔧 Initializing services...")
        
        # Initialize Serial service first
        print("📡 Starting Serial Service...")
        serial_service = SerialService()
        if not serial_service.start():
            print("⚠️  Failed to start Serial service. Please check your USB connection.")
            print("💡 Server will continue without serial communication.")
            serial_service = None
        
        # Test Firebase connection
        print("🔥 Testing Firebase connection...")
        firebase_service = FirebaseService()
        health = firebase_service.health_check()
        if health['status'] == 'healthy':
            print("✅ Firebase connection successful")
        else:
            print(f"⚠️  Firebase connection issue: {health.get('error', 'Unknown error')}")
        
        # Initialize API service with serial service
        api_service = APIService(host='0.0.0.0', port=5000, serial_service=serial_service)
        # api_service = APIService(host='0.0.0.0', port=5000)

        
        print("🌐 Server starting on http://0.0.0.0:5000")
        print("📋 Available endpoints:")
        print("  - GET  /health                    - Health check")
        print("  - GET  /api/sensors               - Get all sensors")
        print("  - GET  /api/sensors/<name>        - Get specific sensor")
        print("  - POST /api/sensors/sync          - Sync sensors data to Firebase")
        print("  - POST /api/control/blower        - Control blower")
        print("  - POST /api/control/actuator      - Control actuator")
        print("  - POST /api/control/auger         - Control auger")
        print("  - POST /api/control/relay         - Control relay")
        print("  - POST /api/feeder/start          - Start feeding process")
        print("\n🔥 Firebase sync endpoint: POST /api/sensors/sync")
        print("💡 Test with: curl -X POST http://localhost:5000/api/sensors/sync")
        print("\n" + "="*60)
        
        # Start the server
        api_service.start()
        
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
        if 'serial_service' in locals() and serial_service:
            serial_service.stop()
    except Exception as e:
        print(f"❌ Error starting server: {str(e)}")
        import traceback
        traceback.print_exc()
        if 'serial_service' in locals() and serial_service:
            serial_service.stop()
        sys.exit(1)

if __name__ == "__main__":
    main() 