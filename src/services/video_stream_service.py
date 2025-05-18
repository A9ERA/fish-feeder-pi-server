"""
Video streaming service for handling camera feed using Picamera2
"""
import cv2
from flask import Response
from picamera2 import Picamera2

class VideoStreamService:
    def __init__(self):
        """Initialize video stream service with Picamera2"""
        self.picam2 = Picamera2()
        # Configure camera
        self.picam2.preview_configuration.main.size = (640, 480)
        self.picam2.preview_configuration.main.format = "RGB888"
        self.picam2.set_controls({
            "ExposureTime": 100000,
            "AnalogueGain": 4.0
        })
        self.picam2.configure("preview")
        self.picam2.start()

    def generate_frames(self):
        """Generate camera frames for streaming"""
        while True:
            try:
                frame = self.picam2.capture_array()
                # Convert frame to JPEG
                ret, buffer = cv2.imencode('.jpg', frame)
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            except Exception as e:
                print(f"Error capturing frame: {e}")
                break

    def get_video_feed(self):
        """Get video feed response"""
        return Response(self.generate_frames(),
                       mimetype='multipart/x-mixed-replace; boundary=frame')

    def release(self):
        """Release camera resources"""
        if hasattr(self, 'picam2'):
            self.picam2.stop() 