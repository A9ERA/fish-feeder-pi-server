"""
Video streaming service using USB webcam (OpenCV)
"""
import cv2
import os
import platform
from flask import Response
import subprocess
from datetime import datetime
from threading import Condition, Thread
import time
from pathlib import Path
import uuid


class VideoStreamService:
    def __init__(self):
        """Initialize video stream service with USB webcam or mock fallback"""
        print("🎥 Initializing USB VideoStreamService")

        # Create necessary directories
        self.base_dir = Path(__file__).parent.parent.parent / 'static'
        self.pictures_dir = self.base_dir / 'pictures'
        self.video_dir = self.base_dir / 'video'
        self.sound_dir = self.base_dir / 'sound'

        # Create data directory for history
        self.data_dir = Path(__file__).parent.parent / 'data' / 'history' / 'feeder-vdo'

        for directory in [self.pictures_dir, self.video_dir, self.sound_dir, self.data_dir]:
            directory.mkdir(parents=True, exist_ok=True)

        # Configurations via environment variables
        self.device_path = os.getenv('CAMERA_DEVICE', '/dev/video0')
        self.device_index = None
        try:
            # Allow numeric index via env (e.g., "0")
            if self.device_path.isdigit():
                self.device_index = int(self.device_path)
        except Exception:
            self.device_index = None

        self.frame_width = int(os.getenv('CAMERA_WIDTH', '640'))
        self.frame_height = int(os.getenv('CAMERA_HEIGHT', '360'))
        self.target_fps = int(os.getenv('CAMERA_FPS', '30'))
        self.jpeg_quality = int(os.getenv('CAMERA_JPEG_QUALITY', '60'))

        # Runtime state
        self.capture = None
        self.running = False
        self.capture_thread: Thread | None = None
        self.frame = None  # Latest BGR frame
        self.condition = Condition()

        # Recording state (general recording)
        self.record_writer = None
        self.record_file_path = None

        # Recording state (feeder recording)
        self.feeder_writer = None
        self.current_feeder_recording = None

        # Initialize camera
        self.mock_mode = False
        self._init_usb_camera()

    def _open_capture(self):
        api_preference = cv2.CAP_V4L2 if hasattr(cv2, 'CAP_V4L2') else 0
        if self.device_index is not None:
            cap = cv2.VideoCapture(self.device_index, api_preference)
        else:
            cap = cv2.VideoCapture(self.device_path, api_preference)
        return cap

    def _init_usb_camera(self):
        try:
            self.capture = self._open_capture()
            if not self.capture or not self.capture.isOpened():
                raise RuntimeError(f"Unable to open camera at {self.device_path}")

            # Configure camera properties
            # Set MJPG for better USB webcam performance when available
            try:
                fourcc_mjpg = cv2.VideoWriter_fourcc(*'MJPG')
                self.capture.set(cv2.CAP_PROP_FOURCC, fourcc_mjpg)
            except Exception:
                pass

            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
            self.capture.set(cv2.CAP_PROP_FPS, self.target_fps)

            # Start capture loop
            self.running = True
            self.capture_thread = Thread(target=self._capture_loop, daemon=True)
            self.capture_thread.start()
            print(f"📷 USB camera opened: {self.device_path} @ {self.frame_width}x{self.frame_height}@{self.target_fps}fps")
        except Exception as e:
            print(f"⚠️  USB camera unavailable ({e}), using mock frames")
            self.mock_mode = True

    def _capture_loop(self):
        failures = 0
        while self.running:
            try:
                if self.capture is None:
                    time.sleep(0.1)
                    continue

                ret, frame = self.capture.read()
                if not ret or frame is None:
                    failures += 1
                    if failures >= 30:
                        print("⚠️  Camera read failures detected. Attempting reopen...")
                        try:
                            if self.capture:
                                self.capture.release()
                            self.capture = self._open_capture()
                            failures = 0
                        except Exception as re_err:
                            print(f"❌ Reopen failed: {re_err}")
                            time.sleep(0.5)
                    else:
                        time.sleep(0.01)
                    continue

                failures = 0
                with self.condition:
                    self.frame = frame
                    self.condition.notify_all()

                # Write to active writers
                if self.record_writer is not None:
                    try:
                        self.record_writer.write(frame)
                    except Exception as w_err:
                        print(f"❌ Record writer error: {w_err}")
                        try:
                            self.record_writer.release()
                        except Exception:
                            pass
                        self.record_writer = None

                if self.feeder_writer is not None:
                    try:
                        self.feeder_writer.write(frame)
                    except Exception as w_err:
                        print(f"❌ Feeder writer error: {w_err}")
                        try:
                            self.feeder_writer.release()
                        except Exception:
                            pass
                        self.feeder_writer = None

                # Simple pacing
                time.sleep(max(0, 1.0 / max(self.target_fps, 1)))
            except Exception as loop_err:
                print(f"❌ Capture loop error: {loop_err}")
                time.sleep(0.05)

    def _encode_jpeg(self, frame):
        try:
            encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality]
            success, buffer = cv2.imencode('.jpg', frame, encode_params)
            if success:
                return buffer.tobytes()
        except Exception as e:
            print(f"❌ JPEG encode error: {e}")
        return None

    def _current_frame(self):
        with self.condition:
            return None if self.frame is None else self.frame.copy()

    def generate_frames(self):
        """Generate camera frames for streaming (MJPEG)."""
        try:
            if self.mock_mode:
                # 1x1 pixel minimal JPEG
                mock_jpeg = bytes([
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
                while True:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + mock_jpeg + b'\r\n')
                    time.sleep(0.1)
            else:
                while True:
                    # Wait for a fresh frame
                    with self.condition:
                        self.condition.wait(timeout=1)
                        frame = None if self.frame is None else self.frame.copy()

                    if frame is not None:
                        jpeg_bytes = self._encode_jpeg(frame)
                        if jpeg_bytes is not None:
                            yield (b'--frame\r\n'
                                   b'Content-Type: image/jpeg\r\n\r\n' + jpeg_bytes + b'\r\n')
                        else:
                            yield (b'--frame\r\n'
                                   b'Content-Type: image/jpeg\r\n\r\n' + b'' + b'\r\n')
                            time.sleep(0.05)
                    else:
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + b'' + b'\r\n')
                        time.sleep(0.05)
        except GeneratorExit:
            print("Client disconnected from stream")
        except Exception as e:
            print(f"Fatal streaming error: {e}")
        finally:
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

        if self.mock_mode:
            # 1x1 pixel minimal JPEG
            mock_jpeg = bytes([
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
            with open(file_output, 'wb') as f:
                f.write(mock_jpeg)
            print(f"📸 Mock photo saved: {file_output}")
        else:
            frame = self._current_frame()
            if frame is None:
                raise RuntimeError("No frame available for photo")
            jpeg_bytes = self._encode_jpeg(frame)
            if jpeg_bytes is None:
                raise RuntimeError("Failed to encode photo")
            with open(file_output, 'wb') as f:
                f.write(jpeg_bytes)
            print(f"📸 Photo captured: {file_output}")

        return str(file_output)

    def _create_video_writer(self, filepath: Path):
        # Determine frame size
        width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH)) if self.capture else self.frame_width
        height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT)) if self.capture else self.frame_height
        fps = self.capture.get(cv2.CAP_PROP_FPS) if self.capture else self.target_fps
        if not fps or fps <= 1:
            fps = float(self.target_fps)

        # Try MP4V -> fallback to XVID/AVI
        fourcc_mp4v = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(str(filepath), fourcc_mp4v, fps, (width, height))
        if writer is not None and writer.isOpened():
            return writer, filepath

        # Fallback to AVI/XVID
        fallback_path = filepath.with_suffix('.avi')
        fourcc_xvid = cv2.VideoWriter_fourcc(*'XVID')
        writer = cv2.VideoWriter(str(fallback_path), fourcc_xvid, fps, (width, height))
        return writer, fallback_path

    def start_recording(self):
        """Start general video recording"""
        timestamp = datetime.now().strftime("%d-%m-%Y_%H:%M:%S")
        output_file = self.video_dir / f"Bird_{timestamp}.mp4"

        if self.mock_mode:
            with open(output_file, 'w') as f:
                f.write(f"Mock video recording started at {timestamp}")
            print(f"🎬 Mock recording started: {output_file}")
            self.record_file_path = str(output_file)
            return str(output_file)

        # Create writer
        writer, actual_path = self._create_video_writer(output_file)
        if writer is None or not writer.isOpened():
            raise RuntimeError("Failed to start video writer")
        self.record_writer = writer
        self.record_file_path = str(actual_path)
        print(f"🎬 Recording started: {actual_path}")
        return self.record_file_path

    def stop_recording(self):
        """Stop general video recording"""
        if self.mock_mode:
            print("🛑 Mock recording stopped")
            return
        if self.record_writer is not None:
            try:
                self.record_writer.release()
            except Exception:
                pass
            self.record_writer = None
            print("🛑 Recording stopped")

    def record_audio(self, duration=30):
        """Record audio using arecord (Linux) or mock on macOS"""
        timestamp = datetime.now().strftime("%b-%d-%y-%I:%M:%S-%p")
        output_file = self.sound_dir / f"birdcam_{timestamp}.wav"

        if self.mock_mode or platform.system() == "Darwin":
            with open(output_file, 'w') as f:
                f.write(f"Mock audio recording for {duration} seconds at {timestamp}")
            print(f"🎤 Mock audio recording: {output_file}")
        else:
            cmd = f'arecord -D dmic_sv -d {duration} -r 48000 -f S32_LE {output_file} -c 2'
            subprocess.Popen(cmd, shell=True)
            print(f"🎤 Audio recording started: {output_file}")

        return str(output_file)

    def start_feeder_recording(self):
        """Start video recording for feeder operation with UUID and timestamp filename"""
        video_uuid = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        filename_mp4 = f"{video_uuid}-{timestamp}.mp4"
        output_file = self.data_dir / filename_mp4

        if self.mock_mode:
            with open(output_file, 'w') as f:
                f.write(f"Mock feeder video recording started at {timestamp}")
            print(f"🎬 Mock feeder recording started: {output_file}")
            self.current_feeder_recording = str(output_file)
            return str(output_file)

        writer, actual_path = self._create_video_writer(output_file)
        if writer is None or not writer.isOpened():
            raise RuntimeError("Failed to start feeder video writer")
        self.feeder_writer = writer
        self.current_feeder_recording = str(actual_path)
        print(f"🎬 Feeder recording started: {actual_path}")
        return self.current_feeder_recording

    def stop_feeder_recording(self):
        """Stop feeder video recording and return file path"""
        if self.mock_mode:
            print("🛑 Mock feeder recording stopped")
            return getattr(self, 'current_feeder_recording', None)

        if self.feeder_writer is not None:
            try:
                self.feeder_writer.release()
            except Exception:
                pass
            self.feeder_writer = None
            print("🛑 Feeder recording stopped")

        recording_file = getattr(self, 'current_feeder_recording', None)
        if hasattr(self, 'current_feeder_recording'):
            delattr(self, 'current_feeder_recording')
        return recording_file

    def release(self):
        """Release camera resources"""
        try:
            self.running = False
            if self.capture_thread is not None:
                self.capture_thread.join(timeout=1.0)
        except Exception:
            pass

        try:
            if self.capture is not None:
                self.capture.release()
        except Exception:
            pass

        try:
            if self.record_writer is not None:
                self.record_writer.release()
                self.record_writer = None
        except Exception:
            pass

        try:
            if self.feeder_writer is not None:
                self.feeder_writer.release()
                self.feeder_writer = None
        except Exception:
            pass

        print("📹 Camera resources released")


