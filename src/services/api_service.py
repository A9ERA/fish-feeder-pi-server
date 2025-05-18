"""
Flask API service for handling sensor data requests
"""
import json5  # Add json5 for JSONC support
from flask import Flask, jsonify, Response, render_template
from pathlib import Path
import time
from .video_stream_service import VideoStreamService

class APIService:
    def __init__(self, host='0.0.0.0', port=5000):
        self.app = Flask(__name__, 
                        template_folder=Path(__file__).parent.parent / 'templates')
        self.host = host
        self.port = port
        self.sensors_file = Path(__file__).parent.parent / 'data' / 'sensors_data.jsonc'
        self.start_time = time.time()
        self.video_service = VideoStreamService()  # Initialize video service
        
        # Register routes
        self.app.route('/api/sensors/<sensor_name>')(self.get_sensor_data)
        self.app.route('/api/sensors')(self.get_all_sensors)
        self.app.route('/health')(self.health_check)
        self.app.route('/video_feed')(self.video_feed)
        self.app.route('/')(self.index)  # Add route for the main page

    def index(self):
        """Render the main video streaming page"""
        return render_template('index.html')

    def video_feed(self):
        """Video streaming endpoint"""
        return self.video_service.get_video_feed()

    def health_check(self):
        """Health check endpoint that returns API status and uptime"""
        try:
            # Try to read the sensors file as a basic health check
            with open(self.sensors_file, 'r') as f:
                json5.loads(f.read())  # Use json5 instead of json for JSONC support
                
            uptime_seconds = int(time.time() - self.start_time)
            hours, remainder = divmod(uptime_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            return jsonify({
                'status': 'healthy',
                'uptime': f'{hours}h {minutes}m {seconds}s',
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'version': '1.0.0'
            })
            
        except Exception as e:
            return jsonify({
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }), 503

    def get_sensor_data(self, sensor_name):
        """Get data for a specific sensor by name"""
        try:
            with open(self.sensors_file, 'r') as f:
                data = json5.loads(f.read())  # Use json5 instead of json for JSONC support
                
            if sensor_name not in data['sensors']:
                return jsonify({
                    'error': f'Sensor {sensor_name} not found'
                }), 404
                
            return jsonify(data['sensors'][sensor_name])
            
        except Exception as e:
            return jsonify({
                'error': f'Error retrieving sensor data: {str(e)}'
            }), 500

    def get_all_sensors(self):
        """Get list of all available sensors"""
        try:
            with open(self.sensors_file, 'r') as f:
                data = json5.loads(f.read())  # Use json5 instead of json for JSONC support
                
            # Return just the sensor names and descriptions
            sensors = {
                name: {'description': info['description']}
                for name, info in data['sensors'].items()
            }
            
            return jsonify(sensors)
            
        except Exception as e:
            return jsonify({
                'error': f'Error retrieving sensors list: {str(e)}'
            }), 500

    def start(self):
        """Start the Flask server"""
        try:
            # Start Flask server
            self.app.run(host=self.host, port=self.port)
        finally:
            # Release video service resources
            if hasattr(self, 'video_service'):
                self.video_service.release() 