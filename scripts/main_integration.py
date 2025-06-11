"""
🔧 INTEGRATION SAMPLE FOR MAIN.PY
================================
Sample code showing how to integrate SmartHybridStorage 
with the existing FishFeederController in main.py
"""

# Add these imports to main.py
from smart_hybrid_storage import SmartHybridStorage

class FishFeederController:
    """Enhanced Fish Feeder Controller with Smart Hybrid Storage"""
    
    def __init__(self):
        # ... existing initialization code ...
        
        # Add storage manager initialization
        self.storage_manager = None
        
    def initialize(self):
        """Initialize all components"""
        try:
            # ... existing initialization code ...
            
            # Initialize Smart Hybrid Storage
            self.logger.info("🚀 Initializing Smart Hybrid Storage...")
            self.storage_manager = SmartHybridStorage()
            
            # ... rest of existing initialization ...
            
        except Exception as e:
            self.logger.error(f"Initialization failed: {e}")
            return False

# ==============================================================================
# ENHANCED WEB API WITH STORAGE INTEGRATION
# ==============================================================================

class WebAPI:
    """Enhanced Web API with Smart Hybrid Storage"""
    
    def __init__(self, arduino_mgr, firebase_mgr, camera_mgr, feed_history_mgr, config_mgr, storage_mgr, logger):
        # ... existing initialization ...
        self.storage_mgr = storage_mgr  # Add storage manager
        
    def _setup_routes(self):
        """Setup enhanced API routes with storage support"""
        
        # ... existing routes ...
        
        # ==== ENHANCED CAMERA ROUTES WITH CLOUD STORAGE ====
        
        @self.app.route('/api/camera/photo', methods=['POST'])
        def take_photo():
            """Take photo with cloud upload"""
            try:
                if self.storage_mgr:
                    result = self.storage_mgr.take_photo()
                else:
                    # Fallback to original camera manager
                    result = self.camera_mgr.take_photo()
                
                return jsonify(result)
                
            except Exception as e:
                self.logger.error(f"Photo capture failed: {e}")
                return jsonify({
                    'status': 'error',
                    'message': str(e)
                }), 500
        
        @self.app.route('/api/camera/record/start', methods=['POST'])
        def start_recording():
            """Start video recording"""
            try:
                data = request.get_json() or {}
                session_id = data.get('session_id', f"session_{int(time.time())}")
                
                if self.storage_mgr:
                    result = self.storage_mgr.start_recording(session_id, self.camera_mgr)
                else:
                    result = {'status': 'error', 'message': 'Storage manager not available'}
                
                return jsonify(result)
                
            except Exception as e:
                self.logger.error(f"Start recording failed: {e}")
                return jsonify({
                    'status': 'error',
                    'message': str(e)
                }), 500
        
        @self.app.route('/api/camera/record/stop', methods=['POST'])
        def stop_recording():
            """Stop video recording and upload"""
            try:
                if self.storage_mgr:
                    result = self.storage_mgr.stop_recording()
                else:
                    result = {'status': 'error', 'message': 'Storage manager not available'}
                
                return jsonify(result)
                
            except Exception as e:
                self.logger.error(f"Stop recording failed: {e}")
                return jsonify({
                    'status': 'error',
                    'message': str(e)
                }), 500
        
        # ==== PAGEKITE CONTROL ROUTES ====
        
        @self.app.route('/api/pagekite/start', methods=['POST'])
        def start_pagekite():
            """Start PageKite tunnel"""
            try:
                if self.storage_mgr:
                    url = self.storage_mgr.start_pagekite()
                    if url:
                        return jsonify({
                            'status': 'success',
                            'message': 'PageKite started',
                            'tunnel_url': url
                        })
                    else:
                        return jsonify({
                            'status': 'error',
                            'message': 'Failed to start PageKite'
                        }), 500
                else:
                    return jsonify({
                        'status': 'error',
                        'message': 'Storage manager not available'
                    }), 500
                    
            except Exception as e:
                self.logger.error(f"PageKite start failed: {e}")
                return jsonify({
                    'status': 'error',
                    'message': str(e)
                }), 500
        
        @self.app.route('/api/pagekite/stop', methods=['POST'])
        def stop_pagekite():
            """Stop PageKite tunnel"""
            try:
                if self.storage_mgr:
                    self.storage_mgr.stop_pagekite()
                    return jsonify({
                        'status': 'success',
                        'message': 'PageKite stopped'
                    })
                else:
                    return jsonify({
                        'status': 'error',
                        'message': 'Storage manager not available'
                    }), 500
                    
            except Exception as e:
                self.logger.error(f"PageKite stop failed: {e}")
                return jsonify({
                    'status': 'error',
                    'message': str(e)
                }), 500
        
        @self.app.route('/api/pagekite/status', methods=['GET'])
        def pagekite_status():
            """Get PageKite status"""
            try:
                if self.storage_mgr:
                    status = self.storage_mgr.get_status()
                    return jsonify({
                        'status': 'success',
                        'pagekite': status['pagekite']
                    })
                else:
                    return jsonify({
                        'status': 'error',
                        'message': 'Storage manager not available'
                    }), 500
                    
            except Exception as e:
                self.logger.error(f"PageKite status failed: {e}")
                return jsonify({
                    'status': 'error',
                    'message': str(e)
                }), 500
        
        # ==== STORAGE MANAGEMENT ROUTES ====
        
        @self.app.route('/api/storage/status', methods=['GET'])
        def storage_status():
            """Get storage system status"""
            try:
                if self.storage_mgr:
                    status = self.storage_mgr.get_status()
                    return jsonify({
                        'status': 'success',
                        'storage': status
                    })
                else:
                    return jsonify({
                        'status': 'error',
                        'message': 'Storage manager not available'
                    }), 500
                    
            except Exception as e:
                self.logger.error(f"Storage status failed: {e}")
                return jsonify({
                    'status': 'error',
                    'message': str(e)
                }), 500
        
        @self.app.route('/api/storage/migrate', methods=['POST'])
        def manual_migration():
            """Manually trigger migration to Google Drive"""
            try:
                if self.storage_mgr:
                    # Run migration in background
                    migration_thread = threading.Thread(
                        target=self.storage_mgr.run_migration_batch,
                        daemon=True
                    )
                    migration_thread.start()
                    
                    return jsonify({
                        'status': 'success',
                        'message': 'Migration started'
                    })
                else:
                    return jsonify({
                        'status': 'error',
                        'message': 'Storage manager not available'
                    }), 500
                    
            except Exception as e:
                self.logger.error(f"Manual migration failed: {e}")
                return jsonify({
                    'status': 'error',
                    'message': str(e)
                }), 500
        
        # ==== ENHANCED FEED CONTROL WITH VIDEO RECORDING ====
        
        @self.app.route('/api/feed', methods=['POST'])
        def enhanced_feed_control():
            """Enhanced feed control with automatic video recording"""
            try:
                data = request.get_json()
                if not data:
                    return jsonify({'error': 'No data provided'}), 400
                
                # Start recording if enabled
                session_id = f"feed_{int(time.time())}"
                recording_started = False
                
                if self.storage_mgr and data.get('record_video', True):
                    record_result = self.storage_mgr.start_recording(session_id, self.camera_mgr)
                    recording_started = record_result.get('status') == 'success'
                
                # Execute feed command (existing logic)
                result = self._execute_feed_command(data)
                
                # Stop recording after feeding
                video_url = None
                if recording_started:
                    # Wait a bit for feeding to complete
                    time.sleep(2)
                    stop_result = self.storage_mgr.stop_recording()
                    if stop_result.get('status') == 'success':
                        video_url = stop_result.get('video_url')
                
                # Add video URL to result
                if video_url:
                    result['video_url'] = video_url
                
                # Save to feed history with video URL
                if result.get('success'):
                    device_timings = {
                        'actuator_up': data.get('actuator_up', 3),
                        'actuator_down': data.get('actuator_down', 2),
                        'auger_duration': data.get('auger_duration', 20),
                        'blower_duration': data.get('blower_duration', 15)
                    }
                    
                    self.feed_history_mgr.add_feed_record(
                        amount=data.get('amount', 100),
                        feed_type=data.get('action', 'manual'),
                        device_timings=device_timings,
                        video_url=video_url
                    )
                
                return jsonify(result)
                
            except Exception as e:
                self.logger.error(f"Enhanced feed control failed: {e}")
                return jsonify({
                    'error': 'Feed control failed',
                    'message': str(e)
                }), 500

# ==============================================================================
# INTEGRATION EXAMPLE USAGE
# ==============================================================================

def integrate_with_main():
    """Example of how to modify main() function"""
    
    # In the main() function, update the controller initialization:
    controller = FishFeederController()
    
    if not controller.initialize():
        logger.error("❌ Initialization failed")
        return
    
    # Update WebAPI initialization to include storage manager:
    web_api = WebAPI(
        arduino_mgr=controller.arduino_mgr,
        firebase_mgr=controller.firebase_mgr,
        camera_mgr=controller.camera_mgr,
        feed_history_mgr=controller.feed_history_mgr,
        config_mgr=controller.config_mgr,
        storage_mgr=controller.storage_manager,  # Add this line
        logger=controller.logger
    )
    
    # Rest of the main() function remains the same... 