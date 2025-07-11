"""
Firebase Service for updating sensor data to Realtime Database
"""
import firebase_admin
from firebase_admin import credentials, db
import datetime
import json
from typing import Dict, Any, Optional
from pathlib import Path
import logging
from ..config.settings import FIREBASE_ADMIN_SDK_PATH, FIREBASE_DATABASE_URL, FIREBASE_PROJECT_ID

logger = logging.getLogger(__name__)

class FirebaseService:
    def __init__(self):
        self.app = None
        self.database = None
        self._initialize_firebase()

    def _initialize_firebase(self):
        """Initialize Firebase Admin SDK"""
        try:
            # Check if Firebase app is already initialized
            if not firebase_admin._apps:
                # Path to service account key file
                cred_path = Path(FIREBASE_ADMIN_SDK_PATH)
                
                # Check if credential file exists
                if not cred_path.exists():
                    logger.error(f"Firebase credential file not found: {cred_path}")
                    raise FileNotFoundError(f"Firebase credential file not found: {cred_path}")
                
                # Initialize the app with a service account, granting admin privileges
                cred = credentials.Certificate(str(cred_path))
                self.app = firebase_admin.initialize_app(cred, {
                    'databaseURL': FIREBASE_DATABASE_URL,
                    'projectId': FIREBASE_PROJECT_ID
                })
                
                logger.info("Firebase Admin SDK initialized successfully")
            else:
                # Use existing app
                self.app = firebase_admin.get_app()
                logger.info("Using existing Firebase app instance")
                
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {str(e)}")
            raise

    def sync_sensor_data(self, sensor_data: Dict[str, Any]) -> bool:
        """
        Sync sensor data to Firebase Realtime Database
        
        Args:
            sensor_data: Dictionary containing sensor data to sync
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get a database reference
            ref = db.reference('/sensors_data')
            
            # Prepare data for Firebase
            firebase_data = {
                'sensors': sensor_data.get('sensors', {}),
                'last_updated': sensor_data.get('last_updated', datetime.datetime.now().isoformat()),
                'sync_timestamp': datetime.datetime.now().isoformat()
            }
            
            # Update data in Firebase
            ref.update(firebase_data)
            
            logger.info("Successfully synced sensor data to Firebase")
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync sensor data to Firebase: {str(e)}")
            return False

    def update_specific_sensor(self, sensor_name: str, sensor_values: list) -> bool:
        """
        Update specific sensor data in Firebase
        
        Args:
            sensor_name: Name of the sensor
            sensor_values: List of sensor readings
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get a database reference for the specific sensor
            ref = db.reference(f'/sensors/{sensor_name}')
            
            current_time = datetime.datetime.now().isoformat()
            
            sensor_data = {
                'last_updated': current_time,
                'description': f"Data from {sensor_name}",
                'values': sensor_values,
                'sync_timestamp': current_time
            }
            
            # Update sensor data
            ref.set(sensor_data)
            
            # Update global last_updated timestamp
            global_ref = db.reference('/last_updated')
            global_ref.set(current_time)
            
            logger.info(f"Successfully updated sensor '{sensor_name}' in Firebase")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update sensor '{sensor_name}' in Firebase: {str(e)}")
            return False

    def get_sensor_data_from_firebase(self, sensor_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get sensor data from Firebase
        
        Args:
            sensor_name: Optional specific sensor name to retrieve
            
        Returns:
            Dictionary containing sensor data
        """
        try:
            if sensor_name:
                ref = db.reference(f'/sensors/{sensor_name}')
            else:
                ref = db.reference('/')
                
            data = ref.get()
            
            if data:
                logger.info(f"Successfully retrieved sensor data from Firebase")
                return data
            else:
                logger.warning("No data found in Firebase")
                return {}
                
        except Exception as e:
            logger.error(f"Failed to retrieve sensor data from Firebase: {str(e)}")
            return {'error': str(e)}

    def sync_schedule_data(self) -> Dict[str, Any]:
        """
        Sync schedule data from Firebase to local schedule_data.jsonc file
        
        Returns:
            Dictionary containing sync status and result
        """
        try:
            # Get schedule data from Firebase
            ref = db.reference('/schedule_data')
            firebase_data = ref.get()
            
            if firebase_data is None:
                logger.warning("No schedule data found in Firebase")
                return {
                    'status': 'warning',
                    'message': 'No schedule data found in Firebase',
                    'data_synced': False
                }
            
            # Prepare data structure for local file
            local_data = {
                'schedule_data': firebase_data,
                'last_synced': datetime.datetime.now().isoformat(),
                'sync_source': 'firebase'
            }
            
            # Save to local file
            schedule_file = Path(__file__).parent.parent / 'data' / 'schedule_data.jsonc'
            
            with open(schedule_file, 'w', encoding='utf-8') as f:
                # Write as pretty-formatted JSON
                json.dump(local_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Successfully synced schedule data from Firebase to {schedule_file}")
            
            return {
                'status': 'success',
                'message': 'Schedule data synced successfully from Firebase',
                'data_synced': True,
                'records_count': len(firebase_data) if isinstance(firebase_data, list) else 1,
                'sync_timestamp': datetime.datetime.now().isoformat(),
                'file_path': str(schedule_file)
            }
            
        except Exception as e:
            error_msg = f"Failed to sync schedule data from Firebase: {str(e)}"
            logger.error(error_msg)
            return {
                'status': 'error',
                'message': error_msg,
                'data_synced': False
            }

    def sync_feed_preset_data(self) -> Dict[str, Any]:
        """
        Sync feed preset data from Firebase to local feed_preset_data.jsonc file
        
        Returns:
            Dictionary containing sync status and result
        """
        try:
            # Get feed preset data from Firebase
            ref = db.reference('/feed_preset')
            firebase_data = ref.get()
            
            if firebase_data is None:
                logger.warning("No feed preset data found in Firebase")
                return {
                    'status': 'warning',
                    'message': 'No feed preset data found in Firebase',
                    'data_synced': False
                }
            
            # Prepare data structure for local file
            local_data = {
                'feed_preset_data': firebase_data,
                'last_synced': datetime.datetime.now().isoformat(),
                'sync_source': 'firebase'
            }
            
            # Save to local file
            preset_file = Path(__file__).parent.parent / 'data' / 'feed_preset_data.jsonc'
            
            with open(preset_file, 'w', encoding='utf-8') as f:
                # Write as pretty-formatted JSON
                json.dump(local_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Successfully synced feed preset data from Firebase to {preset_file}")
            
            return {
                'status': 'success',
                'message': 'Feed preset data synced successfully from Firebase',
                'data_synced': True,
                'records_count': len(firebase_data) if isinstance(firebase_data, list) else 1,
                'sync_timestamp': datetime.datetime.now().isoformat(),
                'file_path': str(preset_file)
            }
            
        except Exception as e:
            error_msg = f"Failed to sync feed preset data from Firebase: {str(e)}"
            logger.error(error_msg)
            return {
                'status': 'error',
                'message': error_msg,
                'data_synced': False
            }

    def health_check(self) -> Dict[str, Any]:
        """
        Check Firebase connection health
        
        Returns:
            Dictionary containing health status
        """
        try:
            # Try to read from Firebase
            ref = db.reference('/health_check')
            ref.set({
                'timestamp': datetime.datetime.now().isoformat(),
                'status': 'healthy'
            })
            
            return {
                'status': 'healthy',
                'firebase_connected': True,
                'timestamp': datetime.datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'firebase_connected': False,
                'error': str(e),
                'timestamp': datetime.datetime.now().isoformat()
            } 