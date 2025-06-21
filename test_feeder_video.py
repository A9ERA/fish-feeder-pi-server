#!/usr/bin/env python3
"""
Test script for feeder service with video recording functionality
"""
import sys
import os
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.services.feeder_service import FeederService
from src.services.video_stream_service import VideoStreamService
from src.services.control_service import ControlService

def test_feeder_with_video():
    """Test feeder service with video recording"""
    print("🚀 Testing Feeder Service with Video Recording")
    
    # Initialize services (mock mode for testing)
    print("📹 Initializing Video Service...")
    video_service = VideoStreamService()
    
    print("🎛️  Initializing Control Service...")
    control_service = ControlService()  # This will use mock mode for testing
    
    print("🐟 Initializing Feeder Service...")
    feeder_service = FeederService(control_service=control_service, video_service=video_service)
    
    # Test parameters
    test_params = {
        'feed_size': 10,  # grams
        'actuator_up': 2,   # seconds
        'actuator_down': 2, # seconds
        'auger_duration': 5, # seconds
        'blower_duration': 3 # seconds
    }
    
    print(f"\n🧪 Starting test feeding process with parameters:")
    for key, value in test_params.items():
        print(f"   - {key}: {value}")
    
    # Start feeding process (this should trigger video recording)
    result = feeder_service.start(**test_params)
    
    print(f"\n📊 Test Results:")
    print(f"   Status: {result.get('status')}")
    print(f"   Message: {result.get('message')}")
    print(f"   Video File: {result.get('video_file')}")
    print(f"   Total Duration: {result.get('total_duration')} seconds")
    
    # Check if video file was created
    video_file = result.get('video_file')
    if video_file and os.path.exists(video_file):
        print(f"✅ Video file successfully created: {video_file}")
        
        # Get file info
        file_size = os.path.getsize(video_file)
        file_mtime = datetime.fromtimestamp(os.path.getmtime(video_file))
        print(f"   - File size: {file_size} bytes")
        print(f"   - Created at: {file_mtime}")
    else:
        print(f"❌ Video file not found or not created")
    
    print(f"\n🏁 Test completed at {datetime.now()}")

if __name__ == "__main__":
    test_feeder_with_video() 