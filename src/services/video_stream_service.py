"""
Video streaming service for handling camera feed using Picamera2
"""
import cv2
import os
import platform
from flask import Response
import io
import subprocess
from datetime import datetime
from threading import Condition
import time
from pathlib import Path
import uuid

# Mock classes for non-Raspberry Pi environments
class MockPicamera2:
    def __init__(self):
        self.started = False
        
    def create_video_configuration(self, main=None, controls=None):
        return {"mock": True}
        
    def create_still_configuration(self):
        return {"mock": True}
        
    def configure(self, config):
        pass
        
    def start_encoder(self, encoder):
        pass
        
    def start_recording(self, encoder, output):
        pass
        
    def switch_mode_and_capture_file(self, config, filepath, wait=False):
        # Create a mock photo file
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            f.write("Mock photo file")
        return "mock_job"
        
    def wait(self, job):
        return {"mock": True}
        
    def stop(self):
        pass

class MockEncoder:
    def __init__(self, bitrate=None):
        self.output = None

class MockCircularOutput:
    def __init__(self):
        self.fileoutput = None
        
    def start(self):
        pass
        
    def stop(self):
        pass

class MockFileOutput:
    def __init__(self, stream):
        self.stream = stream

# Try to import picamera2, fallback to mock if not available
try:
    enable_camera = os.getenv('ENABLE_CAMERA', 'false').lower()

    print(f"[⌗][Video Stream Service] - enable_camera: {enable_camera}")
    
    if enable_camera == 'true':
        from picamera2 import Picamera2
        from picamera2.encoders import H264Encoder, MJPEGEncoder
        from picamera2.outputs import FileOutput, CircularOutput
        USE_MOCK_CAMERA = False
        print("✅ Using real Picamera2")
    else:
        raise ImportError("Using mock camera by configuration")
        
except ImportError as e:
    print(f"⚠️  Picamera2 not available ({e}), using mock camera for development")
    Picamera2 = MockPicamera2
    H264Encoder = MockEncoder
    MJPEGEncoder = MockEncoder
    FileOutput = MockFileOutput
    CircularOutput = MockCircularOutput
    USE_MOCK_CAMERA = True

class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()
        self.mock_frame = self._create_mock_frame()

    def _create_mock_frame(self):
        """Create a simple mock JPEG frame for testing"""
        # This is a minimal JPEG header for a 1x1 pixel image
        return bytes([
            0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
            0x01, 0x01, 0x00, 0x48, 0x00, 0x48, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
            0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07, 0x07, 0x07, 0x09,
            0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
            0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20,
            0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
            0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27, 0x39, 0x3D, 0x38, 0x32,
            0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF, 0xC0, 0x00, 0x11, 0x08, 0x00, 0x01,
            0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0x02, 0x11, 0x01, 0x03, 0x11, 0x01,
            0xFF, 0xC4, 0x00, 0x14, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x08, 0xFF, 0xC4,
            0x00, 0x14, 0x10, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFF, 0xDA, 0x00, 0x0C,
            0x03, 0x01, 0x00, 0x02, 0x11, 0x03, 0x11, 0x00, 0x3F, 0x00, 0x00, 0xFF, 0xD9
        ])

    def write(self, buf):
        with self.condition:
            if USE_MOCK_CAMERA:
                self.frame = self.mock_frame
            else:
                self.frame = buf
            self.condition.notify_all()

class VideoStreamService:
    def __init__(self):
        """Initialize video stream service with Picamera2 or mock"""
        print(f"🎥 Initializing VideoStreamService (Mock: {USE_MOCK_CAMERA})")
        
        # Create necessary directories
        self.base_dir = Path(__file__).parent.parent.parent / 'static'
        self.pictures_dir = self.base_dir / 'pictures'
        self.video_dir = self.base_dir / 'video'
        self.sound_dir = self.base_dir / 'sound'
        
        # Create data directory for history
        self.data_dir = Path(__file__).parent.parent / 'data' / 'history' / 'feeder-vdo'
        
        for directory in [self.pictures_dir, self.video_dir, self.sound_dir, self.data_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        if USE_MOCK_CAMERA:
            self._init_mock_camera()
        else:
            self._init_real_camera()
    
    def _init_mock_camera(self):
        """Initialize mock camera for development"""
        print("🎭 Using mock camera for development")
        self.picam2 = MockPicamera2()
        self.encoder = MockEncoder(bitrate=10000000)
        self.stream_out = StreamingOutput()
        self.stream_out2 = MockFileOutput(self.stream_out)
        self.video_encoder = MockEncoder()
        self.video_output = MockCircularOutput()
        
        # Mock configurations
        self.still_config = {"mock": True}
        
    def _init_real_camera(self):
        """Initialize real camera"""
        print("📹 Using real Picamera2")
        # Initialize camera
        self.picam2 = Picamera2()
        
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
        print("Encoder started.")
        self.picam2.start_recording(self.video_encoder, self.video_output)
        print("Recording started.")

    def generate_frames(self):
        """Generate camera frames for streaming"""
        try:
            if USE_MOCK_CAMERA:
                # Generate mock frames for development
                mock_frame = self.stream_out.mock_frame
                while True:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + mock_frame + b'\r\n')
                    time.sleep(0.1)  # 10 FPS for mock
            else:
                # Real camera frame generation
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
        
        if USE_MOCK_CAMERA:
            # Create mock photo
            with open(file_output, 'wb') as f:
                f.write(self.stream_out.mock_frame)
            print(f"📸 Mock photo saved: {file_output}")
        else:
            # Switch to still mode and capture
            job = self.picam2.switch_mode_and_capture_file(
                self.still_config, 
                str(file_output), 
                wait=False
            )
            metadata = self.picam2.wait(job)
            print(f"📸 Photo captured: {file_output}")
        
        return str(file_output)

    def start_recording(self):
        """Start video recording"""
        timestamp = datetime.now().strftime("%d-%m-%Y_%H:%M:%S")
        output_file = self.video_dir / f"Bird_{timestamp}.h264"
        
        if USE_MOCK_CAMERA:
            # Create mock video file
            with open(output_file, 'w') as f:
                f.write(f"Mock video recording started at {timestamp}")
            print(f"🎬 Mock recording started: {output_file}")
        else:
            self.video_output.fileoutput = str(output_file)
            self.video_output.start()
            print(f"🎬 Recording started: {output_file}")
        
        return str(output_file)

    def stop_recording(self):
        """Stop video recording"""
        if USE_MOCK_CAMERA:
            print("🛑 Mock recording stopped")
        else:
            self.video_output.stop()
            print("🛑 Recording stopped")

    def record_audio(self, duration=30):
        """Record audio using arecord"""
        timestamp = datetime.now().strftime("%b-%d-%y-%I:%M:%S-%p")
        output_file = self.sound_dir / f"birdcam_{timestamp}.wav"
        
        if USE_MOCK_CAMERA or platform.system() == "Darwin":  # Darwin is macOS
            # Create mock audio file for development
            with open(output_file, 'w') as f:
                f.write(f"Mock audio recording for {duration} seconds at {timestamp}")
            print(f"🎤 Mock audio recording: {output_file}")
        else:
            # Start recording in background
            cmd = f'arecord -D dmic_sv -d {duration} -r 48000 -f S32_LE {output_file} -c 2'
            subprocess.Popen(cmd, shell=True)
            print(f"🎤 Audio recording started: {output_file}")
        
        return str(output_file)

    def start_feeder_recording(self):
        """Start video recording specifically for feeder operation with UUID and timestamp filename"""
        # Generate UUID and timestamp for filename
        video_uuid = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        filename = f"{video_uuid}-{timestamp}.mp4"
        output_file = self.data_dir / filename
        
        # Also create temporary H264 file
        temp_h264_file = self.data_dir / f"{video_uuid}-{timestamp}.h264"
        
        if USE_MOCK_CAMERA:
            # Create mock video file
            with open(output_file, 'w') as f:
                f.write(f"Mock feeder video recording started at {timestamp}")
            print(f"🎬 Mock feeder recording started: {output_file}")
        else:
            # Configure H264 encoder for high quality recording
            from picamera2.encoders import H264Encoder
            from picamera2.outputs import FileOutput
            
            # Create new encoder specifically for feeder recording
            self.feeder_encoder = H264Encoder(bitrate=10000000)  # 10Mbps for good quality
            self.feeder_output = FileOutput(str(temp_h264_file))
            
            # Start recording using existing camera instance
            self.picam2.start_encoder(self.feeder_encoder, self.feeder_output)
            print(f"🎬 Feeder recording started (H264): {temp_h264_file}")
        
        self.current_feeder_recording = str(output_file)
        self.current_temp_h264 = str(temp_h264_file)
        return str(output_file)

    def stop_feeder_recording(self):
        """Stop feeder video recording and convert to MP4"""
        if USE_MOCK_CAMERA:
            print("🛑 Mock feeder recording stopped")
        else:
            if hasattr(self, 'feeder_encoder'):
                self.picam2.stop_encoder(self.feeder_encoder)
                print("🛑 Feeder recording stopped")
                
                # Convert H264 to MP4 using ffmpeg
                temp_h264 = getattr(self, 'current_temp_h264', None)
                output_mp4 = getattr(self, 'current_feeder_recording', None)
                
                if temp_h264 and output_mp4 and os.path.exists(temp_h264):
                    try:
                        # Use ffmpeg to convert H264 to MP4
                        ffmpeg_cmd = [
                            'ffmpeg', '-y',  # -y to overwrite output file
                            '-i', temp_h264,  # input H264 file
                            '-c', 'copy',     # copy codec (no re-encoding)
                            '-movflags', '+faststart',  # optimize for streaming
                            output_mp4        # output MP4 file
                        ]
                        
                        result = subprocess.run(ffmpeg_cmd, 
                                              capture_output=True, 
                                              text=True, 
                                              timeout=30)
                        
                        if result.returncode == 0:
                            print(f"✅ Successfully converted to MP4: {output_mp4}")
                            # Remove temporary H264 file
                            os.remove(temp_h264)
                            print(f"🗑️  Removed temporary file: {temp_h264}")
                        else:
                            print(f"❌ FFmpeg conversion failed: {result.stderr}")
                            # Keep H264 file as backup
                            print(f"📁 H264 file kept as backup: {temp_h264}")
                            
                    except subprocess.TimeoutExpired:
                        print("⏰ FFmpeg conversion timed out")
                    except Exception as e:
                        print(f"❌ Error during conversion: {e}")
        
        recording_file = getattr(self, 'current_feeder_recording', None)
        
        # Clean up attributes
        if hasattr(self, 'current_feeder_recording'):
            delattr(self, 'current_feeder_recording')
        if hasattr(self, 'current_temp_h264'):
            delattr(self, 'current_temp_h264')
        if hasattr(self, 'feeder_encoder'):
            delattr(self, 'feeder_encoder')
        if hasattr(self, 'feeder_output'):
            delattr(self, 'feeder_output')
        
        return recording_file

    def release(self):
        """Release camera resources"""
        if hasattr(self, 'picam2') and not USE_MOCK_CAMERA:
            self.picam2.stop()
            self.video_output.stop()
            print("📹 Camera resources released")
        else:
            print("🎭 Mock camera resources released") 