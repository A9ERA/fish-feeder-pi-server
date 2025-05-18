"""
Video streaming service for handling camera feed
"""
import cv2
from flask import Response

class VideoStreamService:
    def __init__(self, camera_index=0):
        """Initialize video stream service with camera"""
        self.camera = cv2.VideoCapture(camera_index)

    def generate_frames(self):
        """Generate camera frames for streaming"""
        while True:
            success, frame = self.camera.read()
            if not success:
                break
            else:
                # Convert frame to JPEG
                ret, buffer = cv2.imencode('.jpg', frame)
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    def get_video_feed(self):
        """Get video feed response"""
        return Response(self.generate_frames(),
                       mimetype='multipart/x-mixed-replace; boundary=frame')

    def release(self):
        """Release camera resources"""
        if hasattr(self, 'camera'):
            self.camera.release() 