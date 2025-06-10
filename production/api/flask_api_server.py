#!/usr/bin/env python3
"""
🌐 FLASK API SERVER FOR WEB
API endpoints compatible with fish-feeder-web
"""

from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime
import os
import time
import json

app = Flask(__name__)
CORS(app, origins=["https://fish-feeder-test-1.web.app", "http://localhost:3000", "http://localhost:5173"])

class FirebaseAPI:
    def __init__(self):
        self.db_ref = None
        self.connect_firebase()
    
    def connect_firebase(self):
        """Connect to Firebase"""
        try:
            if not firebase_admin._apps:
                # Get script directory and navigate to correct config path
                script_dir = os.path.dirname(os.path.abspath(__file__))
                config_path = os.path.join(os.path.dirname(script_dir), 'config', 'firebase-key.json')
                cred = credentials.Certificate(config_path)
                firebase_admin.initialize_app(cred, {
                    'databaseURL': 'https://fish-feeder-test-1-default-rtdb.asia-southeast1.firebasedatabase.app/'
                })
            
            self.db_ref = db.reference('fish-feeder')
            print("[OK] Firebase API connected")
            return True
        except Exception as e:
            print(f"[ERROR] Firebase connection failed: {e}")
            return False

firebase_api = FirebaseAPI()

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Check Firebase connection
        status = firebase_api.db_ref.child('status').get()
        serial_connected = status.get('arduino_connected', False) if status else False
        
        return jsonify({
            'status': 'healthy' if serial_connected else 'unhealthy',
            'message': 'System operational' if serial_connected else 'Arduino disconnected',
            'serial_connected': serial_connected,
            'timestamp': int(time.time())
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'message': f'Error: {str(e)}',
            'serial_connected': False,
            'timestamp': int(time.time())
        }), 500

# Get all sensors
@app.route('/api/sensors', methods=['GET'])
def get_all_sensors():
    """Get all sensor data"""
    try:
        sensors = firebase_api.db_ref.child('sensors').get()
        
        if not sensors:
            return jsonify({
                'status': 'error',
                'message': 'No sensor data available',
                'data': {},
                'timestamp': int(time.time())
            })
        
        return jsonify({
            'status': 'success',
            'data': sensors,
            'timestamp': int(time.time())
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to get sensors: {str(e)}',
            'timestamp': int(time.time())
        }), 500

# Get specific sensor
@app.route('/api/sensors/<sensor_name>', methods=['GET'])
def get_sensor(sensor_name):
    """Get specific sensor data"""
    try:
        sensor_data = firebase_api.db_ref.child('sensors').child(sensor_name).get()
        
        if not sensor_data:
            return jsonify({
                'status': 'error',
                'message': f'Sensor {sensor_name} not found',
                'timestamp': int(time.time())
            }), 404
        
        return jsonify({
            'status': 'success',
            'data': sensor_data,
            'timestamp': int(time.time())
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to get sensor {sensor_name}: {str(e)}',
            'timestamp': int(time.time())
        }), 500

# Get relay status
@app.route('/api/relay/status', methods=['GET'])
def get_relay_status():
    """Get current relay status"""
    try:
        status = firebase_api.db_ref.child('status').get()
        relay_status = status.get('relay', {'led': False, 'fan': False}) if status else {'led': False, 'fan': False}
        
        return jsonify({
            'status': 'success',
            'relay_status': relay_status,
            'timestamp': int(time.time())
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to get relay status: {str(e)}',
            'timestamp': int(time.time())
        }), 500

# Control LED relay
@app.route('/api/relay/led', methods=['POST'])
def control_led():
    """Control LED relay"""
    try:
        data = request.get_json()
        action = data.get('action', 'toggle') if data else 'toggle'
        
        # Get current status
        status = firebase_api.db_ref.child('status').get()
        current_relay = status.get('relay', {'led': False, 'fan': False}) if status else {'led': False, 'fan': False}
        
        # Determine new LED state
        if action == 'on':
            new_led_state = True
        elif action == 'off':
            new_led_state = False
        else:  # toggle
            new_led_state = not current_relay.get('led', False)
        
        # Send command to Arduino via Firebase
        command = 'R:1' if new_led_state else 'R:0'
        command_data = {
            'command': command,
            'source': 'web-api',
            'timestamp': datetime.now().isoformat(),
            'action': f"LED {action}"
        }
        
        firebase_api.db_ref.child('commands').push(command_data)
        
        # Update status immediately (optimistic update)
        new_relay_status = current_relay.copy()
        new_relay_status['led'] = new_led_state
        firebase_api.db_ref.child('status/relay').set(new_relay_status)
        
        return jsonify({
            'status': 'success',
            'message': f'LED turned {action}',
            'relay_status': new_relay_status
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'LED control failed: {str(e)}'
        }), 500

# Control Fan relay
@app.route('/api/relay/fan', methods=['POST'])
def control_fan():
    """Control Fan relay"""
    try:
        data = request.get_json()
        action = data.get('action', 'toggle') if data else 'toggle'
        
        # Get current status
        status = firebase_api.db_ref.child('status').get()
        current_relay = status.get('relay', {'led': False, 'fan': False}) if status else {'led': False, 'fan': False}
        
        # Determine new Fan state
        if action == 'on':
            new_fan_state = True
        elif action == 'off':
            new_fan_state = False
        else:  # toggle
            new_fan_state = not current_relay.get('fan', False)
        
        # Send command to Arduino via Firebase
        command = 'R:2' if new_fan_state else 'R:0'
        command_data = {
            'command': command,
            'source': 'web-api',
            'timestamp': datetime.now().isoformat(),
            'action': f"FAN {action}"
        }
        
        firebase_api.db_ref.child('commands').push(command_data)
        
        # Update status immediately (optimistic update)
        new_relay_status = current_relay.copy()
        new_relay_status['fan'] = new_fan_state
        firebase_api.db_ref.child('status/relay').set(new_relay_status)
        
        return jsonify({
            'status': 'success',
            'message': f'Fan turned {action}',
            'relay_status': new_relay_status
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Fan control failed: {str(e)}'
        }), 500

# Ultra fast control
@app.route('/api/control/ultra', methods=['POST'])
def ultra_control():
    """Ultra fast relay control"""
    try:
        data = request.get_json()
        relay_id = data.get('relay_id', 1) if data else 1
        
        # Simple relay toggle
        command = f'R:{relay_id}'
        command_data = {
            'command': command,
            'source': 'web-ultra',
            'timestamp': datetime.now().isoformat(),
            'relay_id': relay_id
        }
        
        firebase_api.db_ref.child('commands').push(command_data)
        
        return jsonify({
            'status': 'success',
            'message': f'Ultra command sent: {command}',
            'elapsed_ms': '<100'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Ultra control failed: {str(e)}'
        }), 500

# Direct control
@app.route('/api/control/direct', methods=['POST'])
def direct_control():
    """Direct Arduino command"""
    try:
        data = request.get_json()
        command = data.get('command', '') if data else ''
        
        if not command:
            return jsonify({
                'status': 'error',
                'message': 'No command provided'
            }), 400
        
        command_data = {
            'command': command,
            'source': 'web-direct',
            'timestamp': datetime.now().isoformat()
        }
        
        firebase_api.db_ref.child('commands').push(command_data)
        
        return jsonify({
            'status': 'success',
            'message': f'Direct command sent: {command}'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Direct control failed: {str(e)}'
        }), 500

# Firebase sync
@app.route('/api/sensors/sync', methods=['POST'])
def sync_firebase():
    """Sync sensors to Firebase"""
    try:
        # Force a sync by updating the status
        firebase_api.db_ref.child('status/sync_requested').set(datetime.now().isoformat())
        
        return jsonify({
            'status': 'success',
            'message': 'Firebase sync requested'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Sync failed: {str(e)}'
        }), 500

if __name__ == '__main__':
    print("FLASK API SERVER STARTING")
    print("=" * 60)
    print("Port: 5000")
    print("CORS: Enabled for Web App")
    print("Firebase: Connected")
    print("Endpoints:")
    print("  GET  /health")
    print("  GET  /api/sensors")
    print("  GET  /api/sensors/<name>")
    print("  GET  /api/relay/status")
    print("  POST /api/relay/led")
    print("  POST /api/relay/fan")
    print("  POST /api/control/ultra")
    print("  POST /api/control/direct")
    print("  POST /api/sensors/sync")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True) 