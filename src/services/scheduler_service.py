"""
Scheduler Service for managing automated sync operations with dynamic intervals
"""
import threading
import time
import logging
from typing import Dict, Any, Optional, Callable
from pathlib import Path
import json
import datetime
import json5  # Add json5 for JSONC support
from firebase_admin import db
from .firebase_service import FirebaseService
from .sensor_history_service import SensorHistoryService
from typing import Tuple

logger = logging.getLogger(__name__)

class SchedulerService:
    def __init__(self, firebase_service: FirebaseService = None, api_service=None):
        """
        Initialize Scheduler Service
        
        Args:
            firebase_service: FirebaseService instance for Firebase operations
            api_service: APIService instance for API operations
        """
        self.firebase_service = firebase_service or FirebaseService()
        self.api_service = api_service
        self.sensor_history_service = SensorHistoryService()
        self._running = False
        self._threads = {}
        self._stop_events = {}
        self._current_settings = {
            'syncSensors': 10,
            'syncSchedule': 10, 
            'syncFeedPreset': 10,
        }
        self._lock = threading.Lock()
        
        # Track executed schedules to prevent duplicate runs on same day
        # Format: {schedule_id: "YYYY-MM-DD"}
        self._executed_schedules = {}
        
        # Settings file path for offline fallback
        self.settings_file = Path(__file__).parent.parent / 'data' / 'app_settings.jsonc'
        
        # Global variables for system status monitoring
        self.current_fan_is_on = False
        self.current_led_is_on = False
        # Track last evaluated alert states to reduce redundant writes
        self._last_alert_state: Dict[str, Any] = {}

    def _get_app_settings(self) -> Dict[str, Any]:
        """
        Get app settings from Firebase with fallback to local file
        
        Returns:
            Dictionary containing app settings
        """
        try:
            # Try to get settings from Firebase
            ref = db.reference('/app_setting')
            firebase_data = ref.get()
            
            if firebase_data and 'duration' in firebase_data:
                logger.info("Successfully retrieved app settings from Firebase")
                # Save to local file as backup
                self._save_settings_to_file(firebase_data)
                return firebase_data['duration']
            
            
            # Fallback to local file
            logger.warning("Failed to get settings from Firebase, using local file")
            return self._load_settings_from_file()
            
        except Exception as e:
            logger.error(f"Error getting app settings: {str(e)}")
            return self._load_settings_from_file()

    def _save_settings_to_file(self, settings: Dict[str, Any]) -> None:
        """Save settings to local file"""
        try:
            local_data = {
                'app_settings': settings,
                'last_updated': time.strftime('%Y-%m-%d %H:%M:%S'),
                'source': 'firebase'
            }
            
            # Ensure directory exists
            self.settings_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(local_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Failed to save settings to file: {str(e)}")

    def _load_settings_from_file(self) -> Dict[str, Any]:
        """Load settings from local file"""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    file_content = f.read().strip()
                    if not file_content:
                        logger.warning("Settings file is empty, using defaults")
                        return self._get_default_settings()
                    data = json.loads(file_content)
                    if 'app_settings' in data and 'duration' in data['app_settings']:
                        return data['app_settings']['duration']
        except Exception as e:
            logger.error(f"Failed to load settings from file: {str(e)}")
        
        # Return default settings if file doesn't exist or is invalid
        return self._get_default_settings()

    def _get_default_settings(self) -> Dict[str, Any]:
        """Get default settings"""
        return {
            'syncSensors': 10,
            'syncSchedule': 10,
            'syncFeedPreset': 10,
        }

    def _sync_sensors_job(self):
        """Job function for syncing sensors to Firebase"""
        try:
            if self.api_service and hasattr(self.api_service, 'sensor_data_service'):
                logger.info("[Scheduler] Running sync sensors to Firebase...")
                # Call the firebase service method directly instead of API endpoint
                sensor_data = self.api_service.sensor_data_service.get_sensor_data()
                result = self.firebase_service.sync_sensor_data(sensor_data)
                if result:
                    logger.info("[Scheduler] Sensors synced to Firebase successfully")
                else:
                    logger.warning("[Scheduler] Failed to sync sensors to Firebase")
            else:
                logger.warning("[Scheduler] API service or sensor_data_service not available for sensor sync")
        except Exception as e:
            logger.error(f"[Scheduler] Error in sync sensors job: {str(e)}")

    def _sync_schedule_job(self):
        """Job function for syncing schedule data from Firebase"""
        try:
            logger.info("[Scheduler] Running sync schedule from Firebase...")
            result = self.firebase_service.sync_schedule_data()
            if result['status'] == 'success':
                logger.info("[Scheduler] Schedule data synced from Firebase successfully")
            else:
                logger.warning(f"[Scheduler] Schedule sync result: {result['message']}")
        except Exception as e:
            logger.error(f"[Scheduler] Error in sync schedule job: {str(e)}")

    def _sync_feed_preset_job(self):
        """Job function for syncing feed preset data from Firebase"""
        try:
            logger.info("[Scheduler] Running sync feed preset from Firebase...")
            result = self.firebase_service.sync_feed_preset_data()
            if result['status'] == 'success':
                logger.info("[Scheduler] Feed preset data synced from Firebase successfully")
            else:
                logger.warning(f"[Scheduler] Feed preset sync result: {result['message']}")
        except Exception as e:
            logger.error(f"[Scheduler] Error in sync feed preset job: {str(e)}")

    def _cleanup_executed_schedules(self):
        """Clean up old executed schedules data to prevent memory buildup"""
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        self._executed_schedules = {k: v for k, v in self._executed_schedules.items() if v == today}

    def _sensor_history_job(self):
        """Job function for saving sensor history data to CSV files"""
        try:
            logger.info("[Scheduler] Running sensor history save job...")
            self.sensor_history_service.save_current_sensor_data()
        except Exception as e:
            logger.error(f"[Scheduler] Error in sensor history job: {str(e)}")

    def _system_status_monitor_job(self):
        """Job function for monitoring system status from Firebase and controlling Arduino"""
        try:
            # Get system status from Firebase
            ref = db.reference('/system_status')
            system_status = ref.get()
            
            if not system_status:
                logger.warning("[Scheduler] No system status data found in Firebase")
                return
            
            # 1. Monitor fan status
            firebase_fan_status = system_status.get('is_fan_on', False)
            if firebase_fan_status != self.current_fan_is_on:
                logger.info(f"[Scheduler] Fan status changed: {self.current_fan_is_on} -> {firebase_fan_status}")
                self.current_fan_is_on = firebase_fan_status
                
                # Send command to Arduino
                if self.api_service and hasattr(self.api_service, 'serial_service'):
                    command = "relay:fan:on" if firebase_fan_status else "relay:fan:off"
                    result = self.api_service.serial_service.send_command_with_response(command)
                    logger.info(f"[Scheduler] Sent fan command: {command}, Result: {result}")
                else:
                    logger.warning("[Scheduler] Serial service not available for fan control")
            
            # 2. Monitor LED status
            firebase_led_status = system_status.get('led_status', False)
            if firebase_led_status != self.current_led_is_on:
                logger.info(f"[Scheduler] LED status changed: {self.current_led_is_on} -> {firebase_led_status}")
                self.current_led_is_on = firebase_led_status
                
                # Send command to Arduino
                if self.api_service and hasattr(self.api_service, 'serial_service'):
                    command = "relay:led:on" if firebase_led_status else "relay:led:off"
                    result = self.api_service.serial_service.send_command_with_response(command)
                    logger.info(f"[Scheduler] Sent LED command: {command}, Result: {result}")
                else:
                    logger.warning("[Scheduler] Serial service not available for LED control")
            
            # 3. Monitor auto temperature control
            is_auto_temp_control = system_status.get('is_auto_temp_control', False)
            if is_auto_temp_control:
                fan_activation_threshold = system_status.get('fan_activation_threshold', 30)
                
                # Read current system temperature from sensors_data.jsonc
                sensors_file = Path(__file__).parent.parent / 'data' / 'sensors_data.jsonc'
                if sensors_file.exists():
                    try:
                        with open(sensors_file, 'r', encoding='utf-8') as f:
                            file_content = f.read().strip()
                            if file_content:
                                sensors_data = json5.loads(file_content)
                                
                                # Get DHT22_SYSTEM temperature
                                dht22_system = sensors_data.get('sensors', {}).get('DHT22_SYSTEM', {})
                                values = dht22_system.get('values', [])
                                
                                current_system_temp = None
                                for value in values:
                                    if value.get('type') == 'temperature':
                                        current_system_temp = float(value.get('value', 0))
                                        break
                                
                                if current_system_temp is not None:
                                    logger.debug(f"[Scheduler] Auto temp control: Current={current_system_temp}°C, Threshold={fan_activation_threshold}°C")
                                    
                                    # Determine if fan should be on based on temperature
                                    should_fan_be_on = current_system_temp >= fan_activation_threshold
                                    
                                    # Update Firebase and global variable if needed
                                    if should_fan_be_on != self.current_fan_is_on:
                                        logger.info(f"[Scheduler] Auto temp control: Fan should be {'ON' if should_fan_be_on else 'OFF'} (temp: {current_system_temp}°C)")
                                        
                                        # Update Firebase
                                        fan_ref = db.reference('/system_status/is_fan_on')
                                        fan_ref.set(should_fan_be_on)
                                        
                                        # Update global variable
                                        self.current_fan_is_on = should_fan_be_on
                                        
                                        # Send command to Arduino
                                        if self.api_service and hasattr(self.api_service, 'serial_service'):
                                            command = "relay:fan:on" if should_fan_be_on else "relay:fan:off"
                                            result = self.api_service.serial_service.send_command_with_response(command)
                                            logger.info(f"[Scheduler] Auto temp control sent command: {command}, Result: {result}")
                                        else:
                                            logger.warning("[Scheduler] Serial service not available for auto temp control")
                                else:
                                    logger.warning("[Scheduler] Could not find temperature value in DHT22_SYSTEM sensor data")
                            else:
                                logger.warning("[Scheduler] Sensors data file is empty")
                    except ValueError as json_error:
                        logger.error(f"[Scheduler] JSON parsing error reading sensors data: {str(json_error)}")
                    except Exception as e:
                        logger.error(f"[Scheduler] Error reading sensors data file: {str(e)}")
                else:
                    logger.warning("[Scheduler] Sensors data file not found")
            
        except Exception as e:
            logger.error(f"[Scheduler] Error in system status monitor job: {str(e)}")

    def _read_current_sensor_values(self) -> Dict[str, Any]:
        """Read current sensor readings from local sensors_data.jsonc file."""
        sensors_file = Path(__file__).parent.parent / 'data' / 'sensors_data.jsonc'
        if not sensors_file.exists():
            return {}
        try:
            with open(sensors_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    return {}
                return json5.loads(content)
        except Exception as e:
            logger.error(f"[Scheduler] Failed reading sensors data for alerts: {e}")
            return {}

    def _get_alert_settings(self) -> Dict[str, Any]:
        """Get alert settings from Firebase under /app_setting/alert with fallback defaults."""
        try:
            ref = db.reference('/app_setting/alert')
            data = ref.get() or {}
            # Defaults if not present
            dht = data.get('dht22_feeder_humidity', {})
            soil = data.get('soil_moisture', {})
            food = data.get('food_weight', {})
            return {
                'dht22_feeder_humidity': {
                    'warning': int(dht.get('warning', 70)),
                    'critical': int(dht.get('critical', 85)),
                },
                'soil_moisture': {
                    'warning': int(soil.get('warning', 60)),
                    'critical': int(soil.get('critical', 80)),
                },
                'food_weight': {
                    # thresholds in kilograms: alert when value is LOW (≤ threshold)
                    'warning': float(food.get('warning', 3.0)),
                    'critical': float(food.get('critical', 2.0)),
                },
            }
        except Exception as e:
            logger.warning(f"[Scheduler] Failed to get alert settings, using defaults: {e}")
            return {
                'dht22_feeder_humidity': {'warning': 70, 'critical': 85},
                'soil_moisture': {'warning': 60, 'critical': 80},
                'food_weight': {'warning': 3.0, 'critical': 2.0},
            }

    def _evaluate_level(self, value: float, warn: float, crit: float) -> str:
        if value >= crit:
            return 'critical'
        if value >= warn:
            return 'warning'
        return 'normal'

    def _write_alert_log(self, log_item: Dict[str, Any]) -> str:
        """Append alert log under /alerts/logs and return generated id."""
        try:
            logs_ref = db.reference('/alerts/logs')
            new_ref = logs_ref.push(log_item)
            return new_ref.key or ''
        except Exception as e:
            logger.error(f"[Scheduler] Failed writing alert log: {e}")
            return ''

    def _alerts_monitor_job(self):
        """Monitor humidity, soil moisture, and food weight (HX711) to manage alerts and ack state."""
        try:
            sensors_data = self._read_current_sensor_values()
            if not sensors_data:
                return

            sensors = sensors_data.get('sensors', {})
            # Extract values
            def get_value(sensor_name: str, type_name: str) -> float:
                sensor = sensors.get(sensor_name, {})
                values = sensor.get('values', [])
                for v in values:
                    if v.get('type') == type_name:
                        try:
                            return float(v.get('value', 0))
                        except Exception:
                            return 0.0
                return 0.0

            feeder_humi = get_value('DHT22_FEEDER', 'humidity')
            soil_moist = get_value('SOIL_MOISTURE', 'soil_moisture')
            # HX711 weight (kg). Use absolute value to avoid negative readings due to calibration offsets
            food_weight_val = abs(get_value('HX711_FEEDER', 'weight'))

            settings = self._get_alert_settings()
            now_iso = datetime.datetime.now().isoformat()

            # Firebase paths
            active_ref = db.reference('/alerts/active')
            ack_ref = db.reference('/alerts/acknowledged')

            # Load existing state
            active_state = active_ref.get() or {}
            ack_state = ack_ref.get() or {}

            # Helper to process a single key
            # mode: 'high' -> alert when value is HIGH (>= threshold); 'low' -> alert when value is LOW (<= threshold)
            def process(sensor_key: str, value: float, mode: str = 'high'):
                thresholds = settings.get(sensor_key, {})
                if mode == 'low':
                    crit = thresholds.get('critical', 0)
                    warn = thresholds.get('warning', 0)
                    if value <= crit:
                        level = 'critical'
                    elif value <= warn:
                        level = 'warning'
                    else:
                        level = 'normal'
                else:
                    level = self._evaluate_level(value, thresholds.get('warning', 0), thresholds.get('critical', 0))

                prev = active_state.get(sensor_key)
                prev_level = prev.get('level') if isinstance(prev, dict) else 'normal'
                alert_id = prev.get('alert_id') if isinstance(prev, dict) else None

                # Transition logic
                if level == 'normal':
                    # Resolve: remove active entry, keep log
                    if prev and prev_level != 'normal':
                        # write resolve log
                        if alert_id:
                            self._write_alert_log({
                                'alert_id': alert_id,
                                'sensorKey': sensor_key,
                                'level': 'normal',
                                'value': value,
                                'thresholds': thresholds,
                                'timestamp': now_iso,
                                'action': 'resolve'
                            })
                    # Clear active
                    if sensor_key in active_state:
                        active_state.pop(sensor_key, None)
                else:
                    # Create or update active
                    new_level = level
                    if prev and alert_id:
                        # existing alert
                        if prev_level != new_level:
                            # Escalate from warning -> critical
                            if prev_level == 'warning' and new_level == 'critical':
                                # write escalate log
                                self._write_alert_log({
                                    'alert_id': alert_id,
                                    'sensorKey': sensor_key,
                                    'level': new_level,
                                    'value': value,
                                    'thresholds': thresholds,
                                    'timestamp': now_iso,
                                    'action': 'escalate'
                                })
                            # Downgrade to warning (rare within else, handled above by normal path), but we keep active with warning
                        # Update active
                        active_state[sensor_key] = {
                            'sensorKey': sensor_key,
                            'level': new_level,
                            'value': value,
                            'thresholds': thresholds,
                            'alert_id': alert_id,
                            'acknowledged': bool(prev.get('acknowledged', False)),
                            'last_updated': now_iso,
                            'timestamp_first_seen': prev.get('timestamp_first_seen') or now_iso
                        }
                        # If escalated to critical, mark any pending warning acknowledgement as irrelevant by setting acknowledged true
                        if new_level == 'critical':
                            ack_state[sensor_key] = {'alert_id': alert_id, 'acknowledged': True, 'level': 'critical', 'timestamp': now_iso}
                    else:
                        # create new alert entry and log
                        # generate alert id by pushing a log first
                        tmp_id = self._write_alert_log({
                            'sensorKey': sensor_key,
                            'level': level,
                            'value': value,
                            'thresholds': thresholds,
                            'timestamp': now_iso,
                            'action': 'trigger'
                        })
                        new_alert_id = tmp_id or f"{sensor_key}-{int(time.time())}"
                        active_state[sensor_key] = {
                            'sensorKey': sensor_key,
                            'level': new_level,
                            'value': value,
                            'thresholds': thresholds,
                            'alert_id': new_alert_id,
                            'acknowledged': False,
                            'timestamp_first_seen': now_iso,
                            'last_updated': now_iso
                        }

            process('dht22_feeder_humidity', feeder_humi)
            process('soil_moisture', soil_moist)
            # For food weight, we alert when weight is low (≤ threshold)
            process('food_weight', food_weight_val, mode='low')

            # Write back active and ack states
            active_ref.set(active_state)
            ack_ref.set(ack_state)

        except Exception as e:
            logger.error(f"[Scheduler] Error in alerts monitor job: {str(e)}")

    def _run_sensor_history_job_with_timing(self):
        """Run sensor history job only on seconds divisible by 5"""
        while not self._stop_events.get('sensorHistory', threading.Event()).is_set():
            try:
                current_time = datetime.datetime.now()
                current_second = current_time.second
                
                # Check if current second is divisible by 5
                if current_second % 5 == 0:
                    self._sensor_history_job()
                    # Sleep until the next 5-second mark to avoid running multiple times in the same second
                    next_run_second = ((current_second // 5) + 1) * 5
                    if next_run_second >= 60:
                        next_run_second = 0
                    
                    # Calculate sleep time
                    if next_run_second == 0:
                        # Next run is at the top of the next minute
                        sleep_time = 60 - current_second
                    else:
                        sleep_time = next_run_second - current_second
                    
                    # Sleep until next 5-second mark
                    time.sleep(sleep_time)
                else:
                    # Sleep until the next 5-second mark
                    next_run_second = ((current_second // 5) + 1) * 5
                    if next_run_second >= 60:
                        next_run_second = 0
                        sleep_time = 60 - current_second
                    else:
                        sleep_time = next_run_second - current_second
                    
                    time.sleep(sleep_time)
                    
            except Exception as e:
                logger.error(f"[Scheduler] Error in sensor history timing job: {str(e)}")
                time.sleep(1)  # Sleep 1 second on error to prevent rapid loop

    def run_feed_schedule_job(self):
        """
        Job function for running scheduled feeding based on schedule_data.jsonc
        This method reads schedule data and executes feeding jobs at scheduled times
        """
        try:
            logger.info("[Scheduler] Running feed schedule job...")
            
            # Clean up old executed schedules (keep only today's records)
            self._cleanup_executed_schedules()
            
            # Read schedule data file
            schedule_file = Path(__file__).parent.parent / 'data' / 'schedule_data.jsonc'
            feed_preset_file = Path(__file__).parent.parent / 'data' / 'feed_preset_data.jsonc'
            
            if not schedule_file.exists():
                logger.warning("[Scheduler] Schedule data file not found, skipping feed schedule job")
                return
            
            if not feed_preset_file.exists():
                logger.warning("[Scheduler] Feed preset data file not found, skipping feed schedule job")
                return
            
            # Read schedule data
            try:
                with open(schedule_file, 'r', encoding='utf-8') as f:
                    file_content = f.read().strip()
                    if not file_content:
                        logger.warning("[Scheduler] Schedule data file is empty, skipping feed schedule job")
                        return
                    schedule_data = json5.loads(file_content)
            except ValueError as json_error:
                logger.error(f"[Scheduler] JSON parsing error reading schedule data: {str(json_error)}")
                return
            
            # Read feed preset data
            try:
                with open(feed_preset_file, 'r', encoding='utf-8') as f:
                    file_content = f.read().strip()
                    if not file_content:
                        logger.warning("[Scheduler] Feed preset data file is empty, skipping feed schedule job")
                        return
                    feed_preset_data = json5.loads(file_content)
            except ValueError as json_error:
                logger.error(f"[Scheduler] JSON parsing error reading feed preset data: {str(json_error)}")
                return
            
            if 'schedule_data' not in schedule_data or not isinstance(schedule_data['schedule_data'], list):
                logger.warning("[Scheduler] Invalid schedule data format, skipping feed schedule job")
                return
                
            if 'feed_preset_data' not in feed_preset_data or not isinstance(feed_preset_data['feed_preset_data'], list):
                logger.warning("[Scheduler] Invalid feed preset data format, skipping feed schedule job")
                return
            
            # Get current time
            current_time = datetime.datetime.now().strftime("%H:%M")
            current_date = datetime.datetime.now().strftime("%Y-%m-%d")
            logger.info(f"[Scheduler] Current time: {current_time} | Date: {current_date}")
            
            # Process each schedule entry
            for schedule_item in schedule_data['schedule_data']:
                try:
                    # Skip if not enabled
                    if not schedule_item.get('enabled', False):
                        logger.debug(f"[Scheduler] Skipping disabled schedule: {schedule_item.get('id', 'unknown')}")
                        continue
                    
                    # Check if it's time to execute this schedule
                    scheduled_time = schedule_item.get('time', '')
                    if scheduled_time != current_time:
                        continue
                    
                    preset_id = schedule_item.get('presetId', '')
                    schedule_id = schedule_item.get('id', 'unknown')
                    
                    # Check if this schedule has already been executed today
                    if schedule_id in self._executed_schedules and self._executed_schedules[schedule_id] == current_date:
                        logger.info(f"[Scheduler] Schedule {schedule_id} already executed today ({current_date}), skipping")
                        continue
                    
                    logger.info(f"[Scheduler] Executing schedule {schedule_id} at {scheduled_time} with preset {preset_id}")
                    
                    # Find matching preset data
                    preset_data = None
                    for preset in feed_preset_data['feed_preset_data']:
                        if preset.get('id') == preset_id:
                            preset_data = preset
                            break
                    
                    if not preset_data:
                        logger.error(f"[Scheduler] Preset {preset_id} not found for schedule {schedule_id}")
                        continue
                    
                    # Extract feeding parameters
                    feed_size = int(preset_data.get('amount', 0))
                    timing = preset_data.get('timing', {})
                    blower_duration = int(timing.get('blowerDuration', 0))
                    
                    logger.info(f"[Scheduler] Feeding parameters for schedule {schedule_id}:")
                    logger.info(f"  Feed size: {feed_size}g")
                    logger.info(f"  Feeder motor open: until {feed_size}g weight reduction (weight-based)")
                    logger.info(f"  Feeder motor close: 12s (fixed)")
                    logger.info(f"  Blower duration: {blower_duration}s")
                    
                    # Execute feeding process
                    if self.api_service and hasattr(self.api_service, 'feeder_service'):
                        print(f"[Scheduler] Feeding schedule {schedule_id}")
                        result = self.api_service.feeder_service.start(
                            feed_size=feed_size,
                            blower_duration=blower_duration
                        )
                        
                        if result['status'] == 'success':
                            # Mark this schedule as executed today
                            self._executed_schedules[schedule_id] = current_date
                            logger.info(f"[Scheduler] Schedule {schedule_id} executed successfully and marked as done for {current_date}")
                        else:
                            logger.error(f"[Scheduler] Schedule {schedule_id} failed: {result.get('message', 'Unknown error')}")
                    else:
                        logger.error("[Scheduler] FeederService not available for schedule execution")
                        
                except Exception as e:
                    logger.error(f"[Scheduler] Error processing schedule item: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"[Scheduler] Error in feed schedule job: {str(e)}")

    def _run_periodic_job(self, job_name: str, job_func: Callable, interval: int):
        """Run a job periodically with specified interval"""
        stop_event = self._stop_events.get(job_name)
        
        while not stop_event.is_set():
            try:
                job_func()
            except Exception as e:
                logger.error(f"[Scheduler] Error in {job_name}: {str(e)}")
            
            # Wait for the interval or until stop event is set
            stop_event.wait(interval)

    def _update_job_intervals(self):
        """Update job intervals based on current Firebase settings"""
        try:
            new_settings = self._get_app_settings()
            
            with self._lock:
                # Check if settings have changed
                settings_changed = False
                for key in ['syncSensors', 'syncSchedule', 'syncFeedPreset']:
                    if new_settings.get(key, 10) != self._current_settings[key]:
                        settings_changed = True
                        break
                
                if settings_changed:
                    logger.info("[Scheduler] Settings changed, restarting jobs...")
                    self._current_settings.update(new_settings)
                    
                    # Restart all jobs with new intervals (exclude current thread to avoid join error)
                    self._stop_all_jobs(exclude_current_thread=True)
                    time.sleep(1)  # Give time for threads to stop
                    self._start_all_jobs()
                    
        except Exception as e:
            logger.error(f"[Scheduler] Error updating job intervals: {str(e)}")

    def _start_all_jobs(self):
        """Start all scheduled jobs"""
        jobs = [
            ('syncSensors', self._sync_sensors_job, self._current_settings['syncSensors']),
            ('syncSchedule', self._sync_schedule_job, self._current_settings['syncSchedule']),
            ('syncFeedPreset', self._sync_feed_preset_job, self._current_settings['syncFeedPreset']),
            ('runFeedSchedule', self.run_feed_schedule_job, 1),
            ('systemStatusMonitor', self._system_status_monitor_job, 1),
            ('alertsMonitor', self._alerts_monitor_job, 1)
        ]
        
        for job_name, job_func, interval in jobs:
            if interval > 0:  # Only start job if interval is positive
                # Skip if thread already exists and is running (for settings_monitor case)
                if job_name in self._threads and self._threads[job_name].is_alive():
                    logger.info(f"[Scheduler] {job_name} job already running, skipping start")
                    continue
                    
                self._stop_events[job_name] = threading.Event()
                thread = threading.Thread(
                    target=self._run_periodic_job,
                    args=(job_name, job_func, interval),
                    name=f"Scheduler-{job_name}",
                    daemon=True
                )
                self._threads[job_name] = thread
                thread.start()
                logger.info(f"[Scheduler] Started {job_name} job with {interval}s interval")
        
        # Start sensor history job with special timing (every 5 seconds)
        if 'sensorHistory' not in self._threads or not self._threads['sensorHistory'].is_alive():
            self._stop_events['sensorHistory'] = threading.Event()
            thread = threading.Thread(
                target=self._run_sensor_history_job_with_timing,
                name="Scheduler-sensorHistory",
                daemon=True
            )
            self._threads['sensorHistory'] = thread
            thread.start()
            logger.info("[Scheduler] Started sensor history job (every 5 seconds when second % 5 == 0)")

    def _stop_all_jobs(self, exclude_current_thread=False):
        """Stop all scheduled jobs"""
        current_thread = threading.current_thread()
        
        # Signal all threads to stop
        for stop_event in self._stop_events.values():
            stop_event.set()
        
        # Wait for all threads to finish, except current thread if requested
        for thread in self._threads.values():
            if thread.is_alive():
                # Skip joining current thread to avoid "cannot join current thread" error
                if exclude_current_thread and thread == current_thread:
                    continue
                thread.join(timeout=5)  # Wait max 5 seconds
        
        # Only clear threads that are not the current thread when excluding
        if exclude_current_thread:
            current_thread_name = current_thread.name
            threads_to_keep = {}
            events_to_keep = {}
            
            for name, thread in self._threads.items():
                if thread == current_thread:
                    threads_to_keep[name] = thread
                    if name in self._stop_events:
                        events_to_keep[name] = self._stop_events[name]
            
            self._threads = threads_to_keep
            self._stop_events = events_to_keep
        else:
            self._threads.clear()
            self._stop_events.clear()

    def start(self):
        """Start the scheduler service"""
        if self._running:
            logger.warning("[Scheduler] Service is already running")
            return
        
        try:
            self._running = True
            logger.info("[Scheduler] Starting scheduler service...")
            
            # Load initial settings
            self._current_settings.update(self._get_app_settings())
            logger.info(f"[Scheduler] Loaded settings: {self._current_settings}")
            
            # Start all jobs
            self._start_all_jobs()
            
            # Start settings monitor thread (checks for setting changes every 30 seconds)
            self._stop_events['settings_monitor'] = threading.Event()
            settings_thread = threading.Thread(
                target=self._settings_monitor,
                name="Scheduler-SettingsMonitor",
                daemon=True
            )
            self._threads['settings_monitor'] = settings_thread
            settings_thread.start()
            
            logger.info("[Scheduler] Scheduler service started successfully")
            
        except Exception as e:
            logger.error(f"[Scheduler] Failed to start scheduler service: {str(e)}")
            self._running = False
            raise

    def _settings_monitor(self):
        """Monitor settings changes every 30 seconds"""
        stop_event = self._stop_events.get('settings_monitor')
        
        while not stop_event.is_set():
            try:
                self._update_job_intervals()
            except Exception as e:
                logger.error(f"[Scheduler] Error in settings monitor: {str(e)}")
            
            # Check for settings changes every 30 seconds
            stop_event.wait(30)

    def stop(self):
        """Stop the scheduler service"""
        if not self._running:
            logger.warning("[Scheduler] Service is not running")
            return
        
        try:
            logger.info("[Scheduler] Stopping scheduler service...")
            self._running = False
            self._stop_all_jobs()
            logger.info("[Scheduler] Scheduler service stopped successfully")
            
        except Exception as e:
            logger.error(f"[Scheduler] Error stopping scheduler service: {str(e)}")

    def get_status(self) -> Dict[str, Any]:
        """Get current status of the scheduler service"""
        return {
            'running': self._running,
            'current_settings': self._current_settings.copy(),
            'active_jobs': list(self._threads.keys()),
            'thread_count': len([t for t in self._threads.values() if t.is_alive()])
        }

    def update_settings_manually(self, new_settings: Dict[str, int]) -> Dict[str, Any]:
        """Manually update settings and sync to Firebase"""
        try:
            with self._lock:
                # Validate settings
                for key in ['syncSensors', 'syncSchedule', 'syncFeedPreset']:
                    if key in new_settings:
                        if not isinstance(new_settings[key], int) or new_settings[key] < 0:
                            return {
                                'status': 'error',
                                'message': f'Invalid value for {key}. Must be non-negative integer.'
                            }
                
                # Update settings
                self._current_settings.update(new_settings)
                
                # Sync updated settings to Firebase
                firebaseSynced = False
                try:
                    ref = db.reference('/app_setting')
                    current_firebase_data = ref.get() or {}
                    
                    # Update only the duration section
                    if 'duration' not in current_firebase_data:
                        current_firebase_data['duration'] = {}
                    
                    current_firebase_data['duration'].update(self._current_settings)
                    
                    # Update Firebase
                    ref.set(current_firebase_data)
                    logger.info(f"[Scheduler] Settings synced to Firebase: {self._current_settings}")
                    firebaseSynced = True

                    # Save to local file as backup
                    self._save_settings_to_file(current_firebase_data)
                    
                except Exception as firebase_error:
                    logger.warning(f"[Scheduler] Failed to sync settings to Firebase: {str(firebase_error)}")
                    # Continue with local update even if Firebase sync fails
                
                if self._running:
                    # Restart jobs with new settings
                    self._stop_all_jobs()
                    time.sleep(1)
                    self._start_all_jobs()
                
                logger.info(f"[Scheduler] Settings updated manually: {new_settings}")
                
                return {
                    'status': 'success',
                    'message': 'Settings updated and synced to Firebase successfully',
                    'new_settings': self._current_settings.copy(),
                    'firebase_synced': firebaseSynced
                }
                
        except Exception as e:
            logger.error(f"[Scheduler] Error updating settings: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            } 