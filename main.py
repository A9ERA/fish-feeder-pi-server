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
from src.config.settings import PORT

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
        api_service = APIService(host='0.0.0.0', port=PORT, serial_service=serial_service)
        # api_service = APIService(host='0.0.0.0', port=5000)

        
        print(f"🌐 Server starting on http://0.0.0.0:{PORT}")
        print("📋 Available endpoints:")
        print("  - GET  /health                    - Health check")
        print("  - GET  /api/sensors               - Get all sensors")
        print("  - GET  /api/sensors/<n>           - Get specific sensor")
        print("  - POST /api/sensors/sync          - Sync to Firebase")
        print("  - POST /api/control/blower        - Control blower")
        print("  - POST /api/control/actuator      - Control actuator")
        print("  - POST /api/control/auger         - Control auger")
        print("  - POST /api/control/relay         - Control relay")
        print("  - POST /api/feeder/start          - Start feeding process")
        print("  - POST /api/schedule/sync         - Sync schedule from Firebase")
        print("  - POST /api/feed-preset/sync      - Sync feed presets from Firebase")
        print("  - GET  /api/scheduler/status      - Get scheduler status")
        print("  - POST /api/scheduler/start       - Start scheduler")
        print("  - POST /api/scheduler/stop        - Stop scheduler")
        print("  - POST /api/scheduler/update      - Update scheduler settings")
        print("\n🔥 Firebase sync endpoint: POST /api/sensors/sync")
        print(f"💡 Test with: curl -X POST http://localhost:{PORT}/api/sensors/sync")
        
        # Start scheduler service
        print("\n⏰ Starting Scheduler Service...")
        try:
            api_service.scheduler_service.start()
            print("✅ Scheduler service started successfully")
        except Exception as e:
            print(f"⚠️  Failed to start scheduler service: {str(e)}")
            print("💡 Server will continue without automated sync.")
        
        print("\n" + "="*60)
        
        # Start the server
        api_service.start()
        
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
        # Stop scheduler service
        if 'api_service' in locals() and hasattr(api_service, 'scheduler_service'):
            print("⏰ Stopping scheduler service...")
            api_service.scheduler_service.stop()
        # Stop serial service
        if 'serial_service' in locals() and serial_service:
            serial_service.stop()
    except Exception as e:
        print(f"❌ Error starting server: {str(e)}")
        import traceback
        traceback.print_exc()
        # Stop services on error
        if 'api_service' in locals() and hasattr(api_service, 'scheduler_service'):
            api_service.scheduler_service.stop()
        if 'serial_service' in locals() and serial_service:
            serial_service.stop()
        sys.exit(1)

if __name__ == "__main__":
    main() 