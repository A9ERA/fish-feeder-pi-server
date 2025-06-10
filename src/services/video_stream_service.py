"""
Video streaming service for handling camera feed using Picamera2
"""
import cv2
from flask import Response
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder, MJPEGEncoder
from picamera2.outputs import FileOutput, CircularOutput
import io
import subprocess
from datetime import datetime
from threading import Condition
import time
import os
from pathlib import Path

class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()

class VideoStreamService:
    def __init__(self):
        """Initialize video stream service with Picamera2"""
        self.camera_available = False
        self.picam2 = None
        
        # Create necessary directories
        self.base_dir = Path(__file__).parent.parent.parent / 'static'
        self.pictures_dir = self.base_dir / 'pictures'
        self.video_dir = self.base_dir / 'video'
        self.sound_dir = self.base_dir / 'sound'
        
        for directory in [self.pictures_dir, self.video_dir, self.sound_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Try to initialize camera
        print("📷 Checking for camera...")
        try:
            # Initialize camera
            self.picam2 = Picamera2()
            print("📷 Camera detected - initializing...")
            
            # Configure video streaming
            video_config = self.picam2.create_video_configuration(
                main={"size": (500, 500)},
                controls={"FrameRate": 30.0}
            )
            self.picam2.configure(video_config)
            self.still_config = self.picam2.create_still_configuration()
            
            # Setup streaming
            self.encoder = MJPEGEncoder(bitrate=10000000)
            self.stream_out = StreamingOutput()
            self.stream_out2 = FileOutput(self.stream_out)
            self.encoder.output = [self.stream_out2]
            
            # Setup video recording
            self.video_encoder = H264Encoder()
            self.video_output = CircularOutput()
            
            # Start camera
            self.picam2.start_encoder(self.encoder)
            self.picam2.start_recording(self.video_encoder, self.video_output)
            
            print("✅ Camera initialized successfully!")
            print("📷 Camera encoder and recording started")
            self.camera_available = True
            
        except Exception as e:
            print(f"❌ Camera not found or initialization failed: {str(e)}")
            print("📷 No camera available - video streaming disabled")
            print("🔄 Server will run without camera support")
            self.camera_available = False

    def generate_frames(self):
        """Generate camera frames for streaming"""
        if not self.camera_available:
            # Generate a simple "No Camera" message frame
            while True:
                # Simple placeholder message
                message = "Camera not available"
                yield (b'--frame\r\n'
                       b'Content-Type: text/plain\r\n\r\n' + message.encode() + b'\r\n')
                time.sleep(1)  # Slow refresh rate for placeholder
            return
        
        try:
            while True:
                try:
                    with self.stream_out.condition:
                        # Reduced timeout to make stream more responsive
                        self.stream_out.condition.wait(timeout=1)
                        frame = self.stream_out.frame
                    
                    if frame is not None:
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                    else:
                        # If no frame, send an empty frame to keep connection alive
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n\r\n')
                        time.sleep(0.1)  # Small delay to prevent CPU overload
                        
                except Exception as e:
                    print(f"Frame capture error: {e}")
                    # Don't break on single frame error, try to continue
                    time.sleep(0.5)
                    continue
                    
        except GeneratorExit:
            # Clean handling of client disconnection
            print("Client disconnected from stream")
        except Exception as e:
            print(f"Fatal streaming error: {e}")
        finally:
            # Ensure resources are properly managed
            print("Stream ended")

    def get_video_feed(self):
        """Get video feed response"""
        return Response(
            self.generate_frames(),
            mimetype='multipart/x-mixed-replace; boundary=frame',
            headers={
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            }
        )

    def take_photo(self):
        """Take a photo and save it"""
        if not self.camera_available:
            raise Exception("Camera not available")
            
        timestamp = datetime.now().isoformat("_", "seconds")
        file_output = self.pictures_dir / f"snap_{timestamp}.jpg"
        
        # Switch to still mode and capture
        job = self.picam2.switch_mode_and_capture_file(
            self.still_config, 
            str(file_output), 
            wait=False
        )
        metadata = self.picam2.wait(job)
        return str(file_output)

    def start_recording(self):
        """Start video recording"""
        if not self.camera_available:
            raise Exception("Camera not available")
            
        timestamp = datetime.now().strftime("%d-%m-%Y_%H:%M:%S")
        output_file = self.video_dir / f"Bird_{timestamp}.h264"
        self.video_output.fileoutput = str(output_file)
        self.video_output.start()
        return str(output_file)

    def stop_recording(self):
        """Stop video recording"""
        if not self.camera_available:
            return  # Nothing to stop
            
        self.video_output.stop()

    def record_audio(self, duration=30):
        """Record audio using arecord"""
        timestamp = datetime.now().strftime("%b-%d-%y-%I:%M:%S-%p")
        output_file = self.sound_dir / f"birdcam_{timestamp}.wav"
        
        # Start recording in background
        cmd = f'arecord -D dmic_sv -d {duration} -r 48000 -f S32_LE {output_file} -c 2'
        subprocess.Popen(cmd, shell=True)
        return str(output_file)

    def release(self):
        """Release camera resources"""
        if self.camera_available and hasattr(self, 'picam2') and self.picam2:
            try:
                self.picam2.stop()
                if hasattr(self, 'video_output'):
                    self.video_output.stop()
                print("✅ Camera resources released")
            except Exception as e:
                print(f"⚠️  Error releasing camera: {e}") 