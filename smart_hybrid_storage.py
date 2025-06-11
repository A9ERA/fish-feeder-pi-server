"""
🚀 SMART HYBRID STORAGE + PAGEKITE INTEGRATION
==============================================
- Firebase Storage (immediate upload, 5GB)
- Google Drive (long-term storage, 200GB)
- PageKite (tunneling for external access)
- Local Storage Management (128GB Pi storage)
- Auto-migration from Firebase → Google Drive
- Video recording with cloud upload
"""

import os
import time
import json
import subprocess
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from pathlib import Path
import shutil
import cv2

# Cloud storage imports
import firebase_admin
from firebase_admin import credentials, storage as firebase_storage
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

logger = logging.getLogger(__name__)

class SmartHybridStorage:
    """Manages local, Firebase, and Google Drive storage with auto-migration"""
    
    def __init__(self, config_file="storage_config.json"):
        self.config_file = config_file
        self.config = self.load_config()
        self.recording = False
        self.current_video_file = None
        self.pagekite_process = None
        
        # Initialize storage systems
        self.init_local_storage()
        self.init_firebase_storage()
        self.init_google_drive()
        self.init_pagekite()
        
        # Start background migration task
        self.start_migration_scheduler()
    
    def load_config(self):
        """Load storage configuration"""
        default_config = {
            'local_storage': {
                'base_path': '/home/pi/fish_feeder_data',
                'max_size_gb': 100,  # เหลือ 28GB สำหรับ OS และ apps
                'video_retention_days': 7,  # เก็บ local 7 วัน
                'cleanup_threshold_percent': 85
            },
            'firebase': {
                'enabled': True,
                'bucket_name': 'fish-feeder-test-1.firebasestorage.app',
                'max_file_size_mb': 100,
                'retention_days': 30  # เก็บใน Firebase 30 วัน
            },
            'google_drive': {
                'enabled': True,
                'folder_name': 'Fish Feeder Videos',
                'folder_id': None,  # Will be created automatically
                'credentials_file': 'google_drive_credentials.json',
                'token_file': 'google_drive_token.json'
            },
            'pagekite': {
                'enabled': False,
                'subdomain': 'fishfeeder',
                'backend_port': 5000,
                'auto_start': False
            },
            'video_settings': {
                'resolution': [640, 480],
                'fps': 12,
                'quality': 40,
                'max_duration_seconds': 300,  # 5 minutes max
                'auto_stop_after_feeding': True
            },
            'migration': {
                'enabled': True,
                'schedule_hour': 2,  # 2 AM daily migration
                'min_age_hours': 24,  # Migrate files older than 24 hours
                'batch_size': 10  # Process 10 files per batch
            }
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    user_config = json.load(f)
                # Merge with defaults
                self.merge_config(default_config, user_config)
                return default_config
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
        
        # Save default config
        self.save_config(default_config)
        return default_config
    
    def merge_config(self, default, user):
        """Recursively merge user config with defaults"""
        for key, value in user.items():
            if key in default:
                if isinstance(value, dict) and isinstance(default[key], dict):
                    self.merge_config(default[key], value)
                else:
                    default[key] = value
    
    def save_config(self, config=None):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config or self.config, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
    
    def init_local_storage(self):
        """Initialize local storage directories"""
        try:
            base_path = Path(self.config['local_storage']['base_path'])
            self.local_paths = {
                'videos': base_path / 'videos',
                'photos': base_path / 'photos', 
                'temp': base_path / 'temp',
                'processing': base_path / 'processing'
            }
            
            # Create directories
            for path in self.local_paths.values():
                path.mkdir(parents=True, exist_ok=True)
            
            logger.info("✅ Local storage initialized")
            self.log_storage_usage()
            
        except Exception as e:
            logger.error(f"❌ Local storage init failed: {e}")
    
    def init_firebase_storage(self):
        """Initialize Firebase Storage"""
        try:
            if not self.config['firebase']['enabled']:
                return
            
            # Firebase should already be initialized in main.py
            self.firebase_bucket = firebase_storage.bucket()
            logger.info("✅ Firebase Storage initialized")
            
        except Exception as e:
            logger.error(f"❌ Firebase storage init failed: {e}")
            self.config['firebase']['enabled'] = False
    
    def init_google_drive(self):
        """Initialize Google Drive API"""
        try:
            if not self.config['google_drive']['enabled']:
                return
            
            SCOPES = ['https://www.googleapis.com/auth/drive.file']
            creds = None
            
            token_file = self.config['google_drive']['token_file']
            cred_file = self.config['google_drive']['credentials_file']
            
            # Load existing token
            if os.path.exists(token_file):
                creds = Credentials.from_authorized_user_file(token_file, SCOPES)
            
            # Refresh or get new credentials
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                elif os.path.exists(cred_file):
                    flow = InstalledAppFlow.from_client_secrets_file(cred_file, SCOPES)
                    creds = flow.run_local_server(port=0)
                else:
                    logger.warning("Google Drive credentials file not found")
                    self.config['google_drive']['enabled'] = False
                    return
                
                # Save token
                with open(token_file, 'w') as token:
                    token.write(creds.to_json())
            
            self.drive_service = build('drive', 'v3', credentials=creds)
            self.ensure_drive_folder()
            logger.info("✅ Google Drive initialized")
            
        except Exception as e:
            logger.error(f"❌ Google Drive init failed: {e}")
            self.config['google_drive']['enabled'] = False
    
    def ensure_drive_folder(self):
        """Create or find Fish Feeder folder in Google Drive"""
        try:
            folder_name = self.config['google_drive']['folder_name']
            
            # Search for existing folder
            results = self.drive_service.files().list(
                q=f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'",
                fields="files(id, name)"
            ).execute()
            
            if results['files']:
                self.config['google_drive']['folder_id'] = results['files'][0]['id']
                logger.info(f"Found existing Drive folder: {folder_name}")
            else:
                # Create new folder
                folder_metadata = {
                    'name': folder_name,
                    'mimeType': 'application/vnd.google-apps.folder'
                }
                folder = self.drive_service.files().create(
                    body=folder_metadata,
                    fields='id'
                ).execute()
                
                self.config['google_drive']['folder_id'] = folder['id']
                logger.info(f"Created new Drive folder: {folder_name}")
                self.save_config()
                
        except Exception as e:
            logger.error(f"Failed to setup Drive folder: {e}")
    
    def init_pagekite(self):
        """Initialize PageKite configuration"""
        try:
            if not self.config['pagekite']['enabled']:
                return
            
            # Check if PageKite is installed
            try:
                subprocess.run(['pagekite.py', '--help'], 
                             capture_output=True, timeout=5)
                logger.info("✅ PageKite available")
            except (subprocess.TimeoutExpired, FileNotFoundError):
                logger.warning("❌ PageKite not installed. Install with: pip install pagekite")
                self.config['pagekite']['enabled'] = False
                return
            
            if self.config['pagekite']['auto_start']:
                self.start_pagekite()
                
        except Exception as e:
            logger.error(f"PageKite init failed: {e}")
    
    def start_pagekite(self):
        """Start PageKite tunnel"""
        try:
            if self.pagekite_process and self.pagekite_process.poll() is None:
                logger.info("PageKite already running")
                return
            
            subdomain = self.config['pagekite']['subdomain']
            port = self.config['pagekite']['backend_port']
            
            cmd = [
                'pagekite.py',
                str(port),
                f'{subdomain}.pagekite.me'
            ]
            
            self.pagekite_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            logger.info(f"🌐 PageKite started: https://{subdomain}.pagekite.me")
            return f"https://{subdomain}.pagekite.me"
            
        except Exception as e:
            logger.error(f"Failed to start PageKite: {e}")
            return None
    
    def stop_pagekite(self):
        """Stop PageKite tunnel"""
        try:
            if self.pagekite_process:
                self.pagekite_process.terminate()
                self.pagekite_process = None
                logger.info("PageKite stopped")
        except Exception as e:
            logger.error(f"Failed to stop PageKite: {e}")
    
    def start_recording(self, session_id: str, camera_manager) -> Dict:
        """Start video recording for feed session"""
        if self.recording:
            return {'status': 'error', 'message': 'Already recording'}
        
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"feed_{session_id}_{timestamp}.mp4"
            self.current_video_file = self.local_paths['temp'] / filename
            
            # Start recording
            self.recording = True
            self.recording_thread = threading.Thread(
                target=self._record_video,
                args=(camera_manager, str(self.current_video_file))
            )
            self.recording_thread.start()
            
            logger.info(f"🎬 Started recording: {filename}")
            return {
                'status': 'success',
                'message': 'Recording started',
                'filename': filename,
                'session_id': session_id
            }
            
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def stop_recording(self) -> Dict:
        """Stop recording and upload to cloud"""
        if not self.recording:
            return {'status': 'error', 'message': 'Not recording'}
        
        try:
            # Stop recording
            self.recording = False
            self.recording_thread.join(timeout=10)
            
            if not self.current_video_file.exists():
                return {'status': 'error', 'message': 'Video file not found'}
            
            # Move to processing folder
            processing_file = self.local_paths['processing'] / self.current_video_file.name
            shutil.move(str(self.current_video_file), str(processing_file))
            
            # Get file info
            file_size_mb = processing_file.stat().st_size / (1024 * 1024)
            logger.info(f"📹 Recording completed: {file_size_mb:.2f}MB")
            
            # Upload to cloud (async)
            upload_thread = threading.Thread(
                target=self._upload_and_move,
                args=(processing_file, file_size_mb)
            )
            upload_thread.start()
            
            return {
                'status': 'success',
                'message': 'Recording completed, uploading...',
                'file_size_mb': file_size_mb,
                'filename': processing_file.name,
                'video_url': None  # Will be updated after upload
            }
            
        except Exception as e:
            logger.error(f"Failed to stop recording: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _record_video(self, camera_manager, output_file: str):
        """Record video using camera manager"""
        try:
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                logger.error("Camera not available")
                return
            
            # Video settings
            width, height = self.config['video_settings']['resolution']
            fps = self.config['video_settings']['fps']
            max_duration = self.config['video_settings']['max_duration_seconds']
            
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            cap.set(cv2.CAP_PROP_FPS, fps)
            
            # Video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_file, fourcc, fps, (width, height))
            
            start_time = time.time()
            frame_count = 0
            
            while self.recording:
                ret, frame = cap.read()
                if not ret:
                    break
                
                out.write(frame)
                frame_count += 1
                
                # Check duration limit
                if time.time() - start_time > max_duration:
                    logger.info(f"Max duration {max_duration}s reached")
                    break
                
                time.sleep(1/fps)
            
            cap.release()
            out.release()
            
            duration = time.time() - start_time
            logger.info(f"📊 Recorded {frame_count} frames in {duration:.1f}s")
            
        except Exception as e:
            logger.error(f"Recording error: {e}")
            self.recording = False
    
    def _upload_and_move(self, video_file: Path, file_size_mb: float):
        """Upload video to cloud and move to final location"""
        try:
            # Primary upload to Firebase (fast)
            firebase_url = None
            if (self.config['firebase']['enabled'] and 
                file_size_mb <= self.config['firebase']['max_file_size_mb']):
                firebase_url = self.upload_to_firebase(video_file)
            
            # Move to local videos folder
            final_file = self.local_paths['videos'] / video_file.name
            shutil.move(str(video_file), str(final_file))
            
            # Update file record
            self.save_file_record(final_file, firebase_url, file_size_mb)
            
            logger.info(f"✅ Video processed: {video_file.name}")
            
        except Exception as e:
            logger.error(f"Upload and move failed: {e}")
    
    def upload_to_firebase(self, video_file: Path) -> Optional[str]:
        """Upload video to Firebase Storage"""
        try:
            blob = self.firebase_bucket.blob(f"videos/{video_file.name}")
            blob.upload_from_filename(str(video_file))
            blob.make_public()
            
            logger.info(f"✅ Firebase upload: {video_file.name}")
            return blob.public_url
            
        except Exception as e:
            logger.error(f"Firebase upload failed: {e}")
            return None
    
    def upload_to_google_drive(self, video_file: Path) -> Optional[str]:
        """Upload video to Google Drive"""
        try:
            if not self.config['google_drive']['enabled']:
                return None
            
            file_metadata = {
                'name': video_file.name,
                'parents': [self.config['google_drive']['folder_id']]
            }
            
            media = MediaFileUpload(
                str(video_file),
                mimetype='video/mp4',
                resumable=True
            )
            
            file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,webViewLink,webContentLink'
            ).execute()
            
            logger.info(f"✅ Google Drive upload: {video_file.name}")
            return file.get('webViewLink')
            
        except Exception as e:
            logger.error(f"Google Drive upload failed: {e}")
            return None
    
    def save_file_record(self, file_path: Path, firebase_url: str, file_size_mb: float):
        """Save file record to database"""
        try:
            record = {
                'filename': file_path.name,
                'local_path': str(file_path),
                'firebase_url': firebase_url,
                'google_drive_url': None,
                'file_size_mb': file_size_mb,
                'created_at': datetime.now().isoformat(),
                'migrated_to_drive': False,
                'migrated_at': None
            }
            
            # Save to JSON database
            db_file = Path(self.config['local_storage']['base_path']) / 'file_records.json'
            records = []
            
            if db_file.exists():
                with open(db_file, 'r') as f:
                    records = json.load(f)
            
            records.append(record)
            
            with open(db_file, 'w') as f:
                json.dump(records, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save file record: {e}")
    
    def start_migration_scheduler(self):
        """Start background migration scheduler"""
        if not self.config['migration']['enabled']:
            return
        
        def migration_loop():
            while True:
                try:
                    # Run daily at scheduled hour
                    now = datetime.now()
                    target_hour = self.config['migration']['schedule_hour']
                    
                    if now.hour == target_hour and now.minute < 5:
                        self.run_migration_batch()
                        time.sleep(300)  # Wait 5 minutes to avoid re-running
                    
                    time.sleep(60)  # Check every minute
                    
                except Exception as e:
                    logger.error(f"Migration scheduler error: {e}")
                    time.sleep(300)
        
        migration_thread = threading.Thread(target=migration_loop, daemon=True)
        migration_thread.start()
        logger.info("📋 Migration scheduler started")
    
    def run_migration_batch(self):
        """Run migration batch from Firebase to Google Drive"""
        try:
            if not self.config['google_drive']['enabled']:
                return
            
            # Load file records
            db_file = Path(self.config['local_storage']['base_path']) / 'file_records.json'
            if not db_file.exists():
                return
            
            with open(db_file, 'r') as f:
                records = json.load(f)
            
            # Find files to migrate
            min_age = timedelta(hours=self.config['migration']['min_age_hours'])
            batch_size = self.config['migration']['batch_size']
            
            files_to_migrate = []
            for record in records:
                if (not record['migrated_to_drive'] and 
                    record['firebase_url'] and
                    datetime.fromisoformat(record['created_at']) < datetime.now() - min_age):
                    files_to_migrate.append(record)
                    
                    if len(files_to_migrate) >= batch_size:
                        break
            
            # Migrate files
            for record in files_to_migrate:
                self.migrate_file_to_drive(record)
                time.sleep(2)  # Rate limiting
            
            if files_to_migrate:
                logger.info(f"📤 Migrated {len(files_to_migrate)} files to Google Drive")
                
        except Exception as e:
            logger.error(f"Migration batch failed: {e}")
    
    def migrate_file_to_drive(self, record: Dict):
        """Migrate single file from Firebase to Google Drive"""
        try:
            local_path = Path(record['local_path'])
            if not local_path.exists():
                logger.warning(f"Local file not found: {local_path}")
                return
            
            # Upload to Google Drive
            drive_url = self.upload_to_google_drive(local_path)
            if not drive_url:
                return
            
            # Update record
            record['google_drive_url'] = drive_url
            record['migrated_to_drive'] = True
            record['migrated_at'] = datetime.now().isoformat()
            
            # Save updated records
            db_file = Path(self.config['local_storage']['base_path']) / 'file_records.json'
            with open(db_file, 'r') as f:
                all_records = json.load(f)
            
            # Update the specific record
            for i, r in enumerate(all_records):
                if r['filename'] == record['filename']:
                    all_records[i] = record
                    break
            
            with open(db_file, 'w') as f:
                json.dump(all_records, f, indent=2)
            
            logger.info(f"✅ Migrated to Drive: {record['filename']}")
            
        except Exception as e:
            logger.error(f"File migration failed: {e}")
    
    def get_status(self) -> Dict:
        """Get storage system status"""
        return {
            'local_storage': {
                'usage_percent': self.get_storage_usage_percent(),
                'base_path': self.config['local_storage']['base_path']
            },
            'firebase': {
                'enabled': self.config['firebase']['enabled']
            },
            'google_drive': {
                'enabled': self.config['google_drive']['enabled']
            },
            'pagekite': {
                'enabled': self.config['pagekite']['enabled'],
                'running': self.pagekite_process is not None and self.pagekite_process.poll() is None
            },
            'recording': self.recording
        }
    
    def get_storage_usage_percent(self) -> float:
        """Get current storage usage percentage"""
        try:
            total, used, free = shutil.disk_usage(self.config['local_storage']['base_path'])
            return (used / total) * 100
        except:
            return 0
    
    def log_storage_usage(self):
        """Log current storage usage"""
        try:
            total, used, free = shutil.disk_usage(self.config['local_storage']['base_path'])
            usage_pct = (used / total) * 100
            
            logger.info(f"💾 Storage: {used//1e9:.1f}GB used / {total//1e9:.1f}GB total ({usage_pct:.1f}%)")
            
        except Exception as e:
            logger.error(f"Failed to check storage: {e}")
    
    def take_photo(self) -> Dict:
        """Take a photo and upload to Firebase"""
        try:
            # Capture photo
            cap = cv2.VideoCapture(0)
            ret, frame = cap.read()
            cap.release()
            
            if not ret:
                return {'status': 'error', 'message': 'Camera capture failed'}
            
            # Save photo
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            photo_file = self.local_paths['photos'] / f"photo_{timestamp}.jpg"
            cv2.imwrite(str(photo_file), frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            
            # Upload to Firebase
            firebase_url = None
            if self.config['firebase']['enabled']:
                try:
                    blob = self.firebase_bucket.blob(f"photos/{photo_file.name}")
                    blob.upload_from_filename(str(photo_file))
                    blob.make_public()
                    firebase_url = blob.public_url
                except Exception as e:
                    logger.error(f"Photo upload failed: {e}")
            
            return {
                'status': 'success',
                'photo_url': firebase_url or str(photo_file),
                'local_path': str(photo_file),
                'timestamp': timestamp
            }
            
        except Exception as e:
            logger.error(f"Photo capture failed: {e}")
            return {'status': 'error', 'message': str(e)}

# Integration with main.py
def create_storage_manager():
    """Factory function to create storage manager"""
    return SmartHybridStorage() 