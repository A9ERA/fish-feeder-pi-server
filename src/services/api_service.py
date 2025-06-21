"""
Flask API service for handling sensor data requests and camera operations
"""
import json5  # Add json5 for JSONC support
from flask import Flask, jsonify, Response, render_template, request
from flask_cors import CORS
from pathlib import Path
import time
from .video_stream_service import VideoStreamService
from .control_service import ControlService
from .firebase_service import FirebaseService
from .sensor_data_service import SensorDataService
from .feeder_service import FeederService
from .scheduler_service import SchedulerService
from .chart_data_service import ChartDataService
from .feeder_history_service import FeederHistoryService

class APIService:
    def __init__(self, host='0.0.0.0', port=5000, serial_service=None):
        self.app = Flask(__name__, 
                        template_folder=Path(__file__).parent.parent / 'templates',
                        static_folder=Path(__file__).parent.parent.parent / 'static')
        # Enable CORS for all routes
        CORS(self.app)
        self.host = host
        self.port = port
        self.sensors_file = Path(__file__).parent.parent / 'data' / 'sensors_data.jsonc'
        self.start_time = time.time()
        self.video_service = VideoStreamService()  # Initialize video service
        self.control_service = ControlService(serial_service)  # Initialize control service
        self.firebase_service = FirebaseService()  # Initialize Firebase service
        self.sensor_data_service = SensorDataService()  # Initialize sensor data service
        self.feeder_service = FeederService(self.control_service, self.video_service)  # Initialize feeder service with video service
        self.scheduler_service = SchedulerService(self.firebase_service, self)  # Initialize scheduler service
        self.chart_data_service = ChartDataService()  # Initialize chart data service
        self.feeder_history_service = FeederHistoryService()  # Initialize feeder history service
        
        # Health check route
        self.app.route('/')(self.index)
        self.app.route('/health')(self.health_check)

        # Sensor data routes
        self.app.route('/api/sensors/<sensor_name>')(self.get_sensor_data)
        self.app.route('/api/sensors')(self.get_all_sensors)
        self.app.route('/api/sensors/sync', methods=['POST'])(self.sync_sensors_to_firebase)
        
        # Camera routes
        self.app.route('/api/camera/video_feed')(self.video_feed)
        self.app.route('/api/camera/photo', methods=['POST'])(self.take_photo)
        self.app.route('/api/camera/record/start', methods=['POST'])(self.start_recording)
        self.app.route('/api/camera/record/stop', methods=['POST'])(self.stop_recording)
        self.app.route('/api/camera/audio/record', methods=['POST'])(self.record_audio)
        
        # Device control routes
        self.app.route('/api/control/blower', methods=['POST'])(self.control_blower)
        self.app.route('/api/control/actuator', methods=['POST'])(self.control_actuator_motor)
        self.app.route('/api/control/auger', methods=['POST'])(self.control_auger)
        self.app.route('/api/control/relay', methods=['POST'])(self.control_relay)
        self.app.route('/api/control/sensor', methods=['POST'])(self.control_sensor)
        
        # Feeder control routes
        self.app.route('/api/feeder/start', methods=['POST'])(self.start_feeder)
        
        # Schedule sync routes
        self.app.route('/api/schedule/sync', methods=['POST'])(self.sync_schedule_data)
        
        # Feed preset sync routes
        self.app.route('/api/feed-preset/sync', methods=['POST'])(self.sync_feed_preset_data)
        
        # Scheduler control routes
        self.app.route('/api/scheduler/status', methods=['GET'])(self.get_scheduler_status)
        self.app.route('/api/scheduler/start', methods=['POST'])(self.start_scheduler)
        self.app.route('/api/scheduler/stop', methods=['POST'])(self.stop_scheduler)
        self.app.route('/api/scheduler/update', methods=['POST'])(self.update_scheduler_settings)
        
        # Chart data routes
        self.app.route('/api/charts/power-flow/<date>', methods=['GET'])(self.get_power_flow_chart_data)
        self.app.route('/api/charts/battery/<date>', methods=['GET'])(self.get_battery_chart_data)
        self.app.route('/api/charts/available-dates', methods=['GET'])(self.get_available_chart_dates)
        
        # Feed history routes
        self.app.route('/api/feed-history/<date>', methods=['GET'])(self.get_feed_history)
        self.app.route('/api/feed-history/available-dates', methods=['GET'])(self.get_feed_history_dates)

    def index(self):
        """Render the main video streaming page"""
        return render_template('index.html')

    def video_feed(self):
        """Video streaming endpoint"""
        return self.video_service.get_video_feed()

    def take_photo(self):
        """Take a photo and return the file path"""
        try:
            file_path = self.video_service.take_photo()
            return jsonify({
                'status': 'success',
                'message': 'Photo captured successfully',
                'file_path': file_path
            })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Failed to capture photo: {str(e)}'
            }), 500

    def start_recording(self):
        """Start video recording"""
        try:
            file_path = self.video_service.start_recording()
            return jsonify({
                'status': 'success',
                'message': 'Recording started',
                'file_path': file_path
            })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Failed to start recording: {str(e)}'
            }), 500

    def stop_recording(self):
        """Stop video recording"""
        try:
            self.video_service.stop_recording()
            return jsonify({
                'status': 'success',
                'message': 'Recording stopped'
            })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Failed to stop recording: {str(e)}'
            }), 500

    def record_audio(self):
        """Start audio recording"""
        try:
            duration = request.json.get('duration', 30) if request.is_json else 30
            file_path = self.video_service.record_audio(duration)
            return jsonify({
                'status': 'success',
                'message': f'Audio recording started for {duration} seconds',
                'file_path': file_path
            })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Failed to start audio recording: {str(e)}'
            }), 500

    def health_check(self):
        """Health check endpoint that returns API status and uptime"""
        try:
            # Try to read the sensors file as a basic health check
            with open(self.sensors_file, 'r') as f:
                file_content = f.read().strip()
                if not file_content:
                    raise Exception("Sensor data file is empty")
                json5.loads(file_content)  # Use json5 instead of json for JSONC support
                
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
            # Use sensor data service instead of reading file directly
            all_data = self.sensor_data_service.get_sensor_data()
            
            # Check if there's an error from sensor data service
            if 'error' in all_data:
                return jsonify({
                    'error': f'Error retrieving sensor data: {all_data["error"]}'
                }), 500
                
            # Check if sensor exists
            if sensor_name not in all_data.get('sensors', {}):
                return jsonify({
                    'error': f'Sensor {sensor_name} not found'
                }), 404
                
            return jsonify(all_data['sensors'][sensor_name])
            
        except Exception as e:
            return jsonify({
                'error': f'Error retrieving sensor data: {str(e)}'
            }), 500

    def get_all_sensors(self):
        """Get list of all available sensors"""
        try:
            # Use sensor data service instead of reading file directly
            all_data = self.sensor_data_service.get_sensor_data()
            
            # Check if there's an error from sensor data service
            if 'error' in all_data:
                return jsonify({
                    'error': f'Error retrieving sensors list: {all_data["error"]}'
                }), 500
                
            # Return just the sensor names and descriptions
            sensors = {
                name: {'description': info.get('description', 'No description available')}
                for name, info in all_data.get('sensors', {}).items()
            }
            
            return jsonify(sensors)
            
        except Exception as e:
            return jsonify({
                'error': f'Error retrieving sensors list: {str(e)}'
            }), 500

    def control_blower(self):
        """Control blower device via API"""
        try:
            if not request.is_json:
                return jsonify({
                    'status': 'error',
                    'message': 'Request must be JSON'
                }), 400

            data = request.get_json()
            action = data.get('action')
            value = data.get('value')  # For speed setting

            if not action:
                return jsonify({
                    'status': 'error',
                    'message': 'Action is required'
                }), 400

            # Validate actions
            valid_actions = ['start', 'stop', 'speed', 'direction_reverse', 'direction_normal']
            if action not in valid_actions:
                return jsonify({
                    'status': 'error',
                    'message': f'Invalid action {action}. Valid actions are: {", ".join(valid_actions)}'
                }), 400

            # For speed action, validate value
            if action == 'speed':
                if value is None:
                    return jsonify({
                        'status': 'error',
                        'message': 'Value is required for speed action'
                    }), 400
                if not isinstance(value, int) or value < 0:
                    return jsonify({
                        'status': 'error',
                        'message': 'Speed value must be a positive integer'
                    }), 400

            # Send command via control service
            success = self.control_service.control_blower(action, value)

            if success:
                message = f"Blower {action} command sent successfully"
                if action == 'speed':
                    message = f"Blower speed set to {value}"
                return jsonify({
                    'status': 'success',
                    'message': message
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'Failed to send command to device'
                }), 500

        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Error controlling blower: {str(e)}'
            }), 500

    def control_actuator_motor(self):
        """Control actuator motor device via API"""
        try:
            if not request.is_json:
                return jsonify({
                    'status': 'error',
                    'message': 'Request must be JSON'
                }), 400

            data = request.get_json()
            action = data.get('action')

            if not action:
                return jsonify({
                    'status': 'error',
                    'message': 'Action is required'
                }), 400

            # Validate actions
            valid_actions = ['up', 'down', 'stop']
            if action not in valid_actions:
                return jsonify({
                    'status': 'error',
                    'message': f'Invalid action. Valid actions are: {", ".join(valid_actions)}'
                }), 400

            # Send command via control service
            success = self.control_service.control_actuator_motor(action)

            if success:
                return jsonify({
                    'status': 'success',
                    'message': f"Actuator motor {action} command sent successfully"
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'Failed to send command to device'
                }), 500

        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Error controlling actuator motor: {str(e)}'
            }), 500

    def control_auger(self):
        """Control auger device via API"""
        try:
            if not request.is_json:
                return jsonify({
                    'status': 'error',
                    'message': 'Request must be JSON'
                }), 400

            data = request.get_json()
            action = data.get('action')
            value = data.get('value')  # For setspeed action

            if not action:
                return jsonify({
                    'status': 'error',
                    'message': 'Action is required'
                }), 400

            # Validate actions
            valid_actions = ['forward', 'backward', 'stop', 'speedtest', 'setspeed']
            if action not in valid_actions:
                return jsonify({
                    'status': 'error',
                    'message': f'Invalid action. Valid actions are: {", ".join(valid_actions)}'
                }), 400

            # For setspeed action, validate value
            if action == 'setspeed':
                if value is None:
                    return jsonify({
                        'status': 'error',
                        'message': 'Value is required for setspeed action'
                    }), 400
                if not isinstance(value, int) or value < 0:
                    return jsonify({
                        'status': 'error',
                        'message': 'Speed value must be a positive integer'
                    }), 400

            # Send command via control service
            success = self.control_service.control_auger(action, value)

            if success:
                message = f"Auger {action} command sent successfully"
                if action == 'setspeed':
                    message = f"Auger speed set to {value}"
                return jsonify({
                    'status': 'success',
                    'message': message
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'Failed to send command to device'
                }), 500

        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Error controlling auger: {str(e)}'
            }), 500

    def control_relay(self):
        """Control relay device via API"""
        try:
            if not request.is_json:
                return jsonify({
                    'status': 'error',
                    'message': 'Request must be JSON'
                }), 400

            data = request.get_json()
            device = data.get('device')
            action = data.get('action')

            if not device or not action:
                return jsonify({
                    'status': 'error',
                    'message': 'Both device and action are required'
                }), 400

            # Validate device and action combinations
            valid_devices = ['led', 'fan', 'all']
            valid_actions = ['on', 'off']
            
            if device not in valid_devices:
                return jsonify({
                    'status': 'error',
                    'message': f'Invalid device. Valid devices are: {", ".join(valid_devices)}'
                }), 400

            if action not in valid_actions:
                return jsonify({
                    'status': 'error',
                    'message': f'Invalid action. Valid actions are: {", ".join(valid_actions)}'
                }), 400

            # Special validation for 'all' device - only 'off' is supported
            if device == 'all' and action != 'off':
                return jsonify({
                    'status': 'error',
                    'message': 'Only "off" action is supported for "all" device'
                }), 400

            # Send command via control service
            success = self.control_service.control_relay(device, action)

            if success:
                return jsonify({
                    'status': 'success',
                    'message': f"Relay {device} {action} command sent successfully"
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'Failed to send command to device'
                }), 500

        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Error controlling relay: {str(e)}'
            }), 500

    def start_feeder(self):
        """Start feeder process via API"""
        try:
            if not request.is_json:
                return jsonify({
                    'status': 'error',
                    'message': 'Request must be JSON'
                }), 400

            data = request.get_json()
            
            # Extract parameters from request
            feed_size = data.get('feedSize')
            actuator_up = data.get('actuatorUp')
            actuator_down = data.get('actuatorDown')
            auger_duration = data.get('augerDuration')
            blower_duration = data.get('blowerDuration')

            # Validate required parameters
            if not all([
                feed_size is not None,
                actuator_up is not None,
                actuator_down is not None,
                auger_duration is not None,
                blower_duration is not None
            ]):
                return jsonify({
                    'status': 'error',
                    'message': 'All parameters are required: feedSize, actuatorUp, actuatorDown, augerDuration, blowerDuration'
                }), 400

            # Validate parameter types and values
            try:
                feed_size = int(feed_size)
                actuator_up = int(actuator_up)
                actuator_down = int(actuator_down)
                auger_duration = int(auger_duration)
                blower_duration = int(blower_duration)
            except (ValueError, TypeError):
                return jsonify({
                    'status': 'error',
                    'message': 'All parameters must be integers'
                }), 400

            # Validate parameter ranges
            if any([
                feed_size < 0,
                actuator_up < 0,
                actuator_down < 0,
                auger_duration < 0,
                blower_duration < 0
            ]):
                return jsonify({
                    'status': 'error',
                    'message': 'All parameters must be non-negative integers'
                }), 400

            # Validate reasonable maximum values (safety limits)
            max_duration = 300  # 5 minutes max for any single operation
            if any([
                actuator_up > max_duration,
                actuator_down > max_duration,
                auger_duration > max_duration,
                blower_duration > max_duration
            ]):
                return jsonify({
                    'status': 'error',
                    'message': f'Duration parameters cannot exceed {max_duration} seconds for safety'
                }), 400

            # Start the feeder process
            result = self.feeder_service.start(
                feed_size=feed_size,
                actuator_up=actuator_up,
                actuator_down=actuator_down,
                auger_duration=auger_duration,
                blower_duration=blower_duration
            )

            if result['status'] == 'success':
                return jsonify(result)
            else:
                return jsonify(result), 500

        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Error starting feeder process: {str(e)}'
            }), 500

    def sync_schedule_data(self):
        """Sync schedule data from Firebase to local file"""
        try:
            # Call firebase service to sync schedule data
            result = self.firebase_service.sync_schedule_data()
            
            if result['status'] == 'success':
                return jsonify(result)
            elif result['status'] == 'warning':
                return jsonify(result), 200  # Still successful, just no data
            else:
                return jsonify(result), 500
                
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Error syncing schedule data: {str(e)}',
                'data_synced': False
            }), 500

    def sync_feed_preset_data(self):
        """Sync feed preset data from Firebase to local file"""
        try:
            # Call firebase service to sync feed preset data
            result = self.firebase_service.sync_feed_preset_data()
            
            if result['status'] == 'success':
                return jsonify(result)
            elif result['status'] == 'warning':
                return jsonify(result), 200  # Still successful, just no data
            else:
                return jsonify(result), 500
                
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Error syncing feed preset data: {str(e)}',
                'data_synced': False
            }), 500

    def sync_sensors_to_firebase(self):
        """Sync current sensor data to Firebase Realtime Database"""
        try:
            # Get current sensor data from local storage
            sensor_data = self.sensor_data_service.get_sensor_data()
            
            # Check if sensor data exists
            if 'error' in sensor_data:
                return jsonify({
                    'status': 'error',
                    'message': f'Failed to read sensor data: {sensor_data["error"]}'
                }), 500
            
            # Sync to Firebase
            success = self.firebase_service.sync_sensor_data(sensor_data)
            
            if success:
                return jsonify({
                    'status': 'success',
                    'message': 'Sensor data synced to Firebase successfully',
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'synced_sensors': list(sensor_data.get('sensors', {}).keys())
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'Failed to sync sensor data to Firebase'
                }), 500
                
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Error syncing sensor data: {str(e)}'
            }), 500

    def get_scheduler_status(self):
        """Get scheduler status"""
        try:
            status = self.scheduler_service.get_status()
            return jsonify({
                'status': 'success',
                'message': 'Scheduler status retrieved successfully',
                'scheduler_status': status
            })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Error retrieving scheduler status: {str(e)}'
            }), 500

    def start_scheduler(self):
        """Start scheduler"""
        try:
            self.scheduler_service.start()
            return jsonify({
                'status': 'success',
                'message': 'Scheduler started successfully'
            })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Error starting scheduler: {str(e)}'
            }), 500

    def stop_scheduler(self):
        """Stop scheduler"""
        try:
            self.scheduler_service.stop()
            return jsonify({
                'status': 'success',
                'message': 'Scheduler stopped successfully'
            })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Error stopping scheduler: {str(e)}'
            }), 500

    def update_scheduler_settings(self):
        """Update scheduler sync intervals"""
        try:
            if not request.is_json:
                return jsonify({
                    'status': 'error',
                    'message': 'Request must be JSON'
                }), 400

            data = request.get_json()
            
            # Extract sync interval parameters from request
            new_settings = {}
            if 'syncSensors' in data:
                new_settings['syncSensors'] = data['syncSensors']
            if 'syncSchedule' in data:
                new_settings['syncSchedule'] = data['syncSchedule']
            if 'syncFeedPreset' in data:
                new_settings['syncFeedPreset'] = data['syncFeedPreset']

            if not new_settings:
                return jsonify({
                    'status': 'error',
                    'message': 'At least one sync interval parameter is required: syncSensors, syncSchedule, syncFeedPreset'
                }), 400

            # Update scheduler settings
            result = self.scheduler_service.update_settings_manually(new_settings)
            
            if result['status'] == 'success':
                return jsonify(result)
            else:
                return jsonify(result), 500

        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Error updating scheduler settings: {str(e)}'
            }), 500

    def get_power_flow_chart_data(self, date):
        """Get power flow chart data for a specific date"""
        try:
            # Get power flow data from chart data service
            result = self.chart_data_service.get_power_flow_data(date)
            
            if result['error']:
                return jsonify({
                    'status': 'error',
                    'message': result['error'],
                    'data': []
                }), 404
            
            return jsonify({
                'status': 'success',
                'message': f'Power flow data retrieved for {date}',
                'date': result['date'],
                'total_records': result['total_records'],
                'data': result['data']
            })
            
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Error retrieving power flow data: {str(e)}',
                'data': []
            }), 500

    def get_battery_chart_data(self, date):
        """Get battery level chart data for a specific date"""
        try:
            # Get battery data from chart data service
            result = self.chart_data_service.get_battery_data(date)
            
            if result['error']:
                return jsonify({
                    'status': 'error',
                    'message': result['error'],
                    'data': []
                }), 404
            
            return jsonify({
                'status': 'success',
                'message': f'Battery data retrieved for {date}',
                'date': result['date'],
                'total_records': result['total_records'],
                'data': result['data']
            })
            
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Error retrieving battery data: {str(e)}',
                'data': []
            }), 500

    def get_available_chart_dates(self):
        """Get list of available dates for chart data"""
        try:
            # Get available dates from chart data service
            result = self.chart_data_service.get_available_dates()
            
            if result['error']:
                return jsonify({
                    'status': 'error',
                    'message': result['error'],
                    'dates': []
                }), 500
            
            return jsonify({
                'status': 'success',
                'message': f'Found {len(result["dates"])} available dates',
                'dates': result['dates']
            })
            
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Error retrieving available dates: {str(e)}',
                'dates': []
            }), 500

    def get_feed_history(self, date):
        """Get feed history data for a specific date"""
        try:
            from datetime import datetime
            
            # Parse date string (DD-MM-YYYY format)
            try:
                date_obj = datetime.strptime(date, "%d-%m-%Y")
            except ValueError:
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid date format. Use DD-MM-YYYY format (e.g., 21-06-2025)',
                    'data': []
                }), 400
            
            # Get feed history data
            feed_logs = self.feeder_history_service.read_feed_history(date_obj)
            
            return jsonify({
                'status': 'success',
                'message': f'Feed history retrieved for {date}',
                'date': date,
                'total_records': len(feed_logs),
                'data': feed_logs
            })
            
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Error retrieving feed history: {str(e)}',
                'data': []
            }), 500

    def get_feed_history_dates(self):
        """Get list of available dates for feed history"""
        try:
            # Get available dates from feeder history service
            dates = self.feeder_history_service.get_available_dates()
            
            return jsonify({
                'status': 'success',
                'message': f'Found {len(dates)} available dates',
                'dates': dates
            })
            
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Error retrieving available dates: {str(e)}',
                'dates': []
            }), 500

    def control_sensor(self):
        """Control sensor operations"""
        try:
            if not request.is_json:
                return jsonify({
                    'status': 'error',
                    'message': 'Request must be JSON'
                }), 400

            data = request.get_json()
            action = data.get('action')
            
            if not action:
                return jsonify({
                    'status': 'error',
                    'message': 'Action is required'
                }), 400

            # Validate action
            valid_actions = ['start', 'stop', 'interval', 'status']
            if action not in valid_actions:
                return jsonify({
                    'status': 'error',
                    'message': f'Invalid action. Must be one of: {", ".join(valid_actions)}'
                }), 400

            # Handle interval action (requires interval value)
            if action == 'interval':
                interval = data.get('interval')
                if interval is None:
                    return jsonify({
                        'status': 'error',
                        'message': 'Interval value is required for interval action'
                    }), 400
                
                try:
                    interval = int(interval)
                    if interval < 0:
                        raise ValueError("Interval must be positive")
                except (ValueError, TypeError):
                    return jsonify({
                        'status': 'error',
                        'message': 'Interval must be a positive integer'
                    }), 400
                
                success = self.control_service.control_sensors(action, interval)
                action_description = f'Set sensor interval to {interval}ms'
                
                if success:
                    return jsonify({
                        'status': 'success',
                        'message': f'{action_description} command sent successfully',
                        'action': action,
                        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                    })
                else:
                    return jsonify({
                        'status': 'error',
                        'message': f'Failed to send {action_description.lower()} command'
                    }), 500
                    
            elif action == 'status':
                # Handle status action (returns dict with status info)
                result = self.control_service.control_sensors(action)
                
                if result.get('success'):
                    response_data = {
                        'status': 'success',
                        'message': 'Sensor status retrieved successfully',
                        'action': action,
                        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                        'sensor_status': result.get('status', 'UNKNOWN'),
                        'is_running': result.get('is_running', False),
                        'interval': result.get('interval', 0),
                        'raw_responses': result.get('raw_responses', [])
                    }
                    return jsonify(response_data)
                else:
                    return jsonify({
                        'status': 'error',
                        'message': f'Failed to get sensor status: {result.get("error", "Unknown error")}',
                        'action': action,
                        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                    }), 500
                    
            else:
                # Handle start/stop actions (now returns dict with status)
                result = self.control_service.control_sensors(action)
                action_descriptions = {
                    'start': 'Start sensors',
                    'stop': 'Stop sensors'
                }
                action_description = action_descriptions.get(action, f'Sensor {action}')

                if result.get('success') and result.get('command_success'):
                    return jsonify({
                        'status': 'success',
                        'message': f'{action_description} command sent successfully',
                        'action': action,
                        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                        'sensor_status': result.get('status', 'UNKNOWN'),
                        'is_running': result.get('is_running', False),
                        'interval': result.get('interval', 0)
                    })
                else:
                    error_msg = result.get('error', 'Unknown error') if isinstance(result, dict) else 'Command failed'
                    return jsonify({
                        'status': 'error',
                        'message': f'Failed to send {action_description.lower()} command: {error_msg}'
                    }), 500

        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Error controlling sensor: {str(e)}'
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