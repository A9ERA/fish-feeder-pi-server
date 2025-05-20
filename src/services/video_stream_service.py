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
        # Initialize camera
        self.picam2 = Picamera2()
        
        # Configure video streaming
        self.picam2.configure(self.picam2.create_video_configuration(main={"size": (800, 600)}))
        self.still_config = self.picam2.create_still_configuration()
        
        # Setup streaming
        self.encoder = MJPEGEncoder(10000000)
        self.stream_out = StreamingOutput()
        self.stream_out2 = FileOutput(self.stream_out)
        self.encoder.output = [self.stream_out2]
        
        # Setup video recording
        self.video_encoder = H264Encoder()
        self.video_output = CircularOutput()
        
        # Create necessary directories
        self.base_dir = Path(__file__).parent.parent.parent / 'static'
        self.pictures_dir = self.base_dir / 'pictures'
        self.video_dir = self.base_dir / 'video'
        self.sound_dir = self.base_dir / 'sound'
        
        for directory in [self.pictures_dir, self.video_dir, self.sound_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Start camera
        self.picam2.start_encoder(self.encoder)
        print("Encoder started.")
        self.picam2.start_recording(self.video_encoder, self.video_output)
        print("Recording started.")

    def generate_frames(self):
        """Generate camera frames for streaming"""
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
        timestamp = datetime.now().strftime("%d-%m-%Y_%H:%M:%S")
        output_file = self.video_dir / f"Bird_{timestamp}.h264"
        self.video_output.fileoutput = str(output_file)
        self.video_output.start()
        return str(output_file)

    def stop_recording(self):
        """Stop video recording"""
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
        if hasattr(self, 'picam2'):
            self.picam2.stop()
            self.video_output.stop() 