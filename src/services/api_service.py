"""
Flask API service for handling sensor data requests
"""
import json
from flask import Flask, jsonify
from pathlib import Path
import time

class APIService:
    def __init__(self, host='0.0.0.0', port=5000):
        self.app = Flask(__name__)
        self.host = host
        self.port = port
        self.sensors_file = Path(__file__).parent.parent / 'data' / 'sensors_data.jsonc'
        self.start_time = time.time()
        
        # Register routes
        self.app.route('/api/sensors/<sensor_name>')(self.get_sensor_data)
        self.app.route('/api/sensors')(self.get_all_sensors)
        self.app.route('/health')(self.health_check)

    def health_check(self):
        """Health check endpoint that returns API status and uptime"""
        try:
            # Try to read the sensors file as a basic health check
            with open(self.sensors_file, 'r') as f:
                json.load(f)  # Verify we can parse the JSON
                
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
                data = json.load(f)
                
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
                data = json.load(f)
                
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
        self.app.run(host=self.host, port=self.port) 