"""
Feed Session Service for managing feed session logs and history
"""
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
import uuid
import shutil
from typing import Dict, List, Any, Optional

class FeedSessionService:
    def __init__(self):
        # Use relative paths in project directory
        project_root = Path(__file__).parent.parent.parent  # Go up to pi-mqtt-server root
        self.logs_dir = project_root / "logs" / "feed_sessions"
        self.videos_dir = project_root / "logs" / "videos"
        self.current_session = None
        self.ensure_directories()
    
    def ensure_directories(self):
        """Create necessary directories if they don't exist"""
        print(f"📁 Creating logs directory: {self.logs_dir.absolute()}")
        print(f"📁 Creating videos directory: {self.videos_dir.absolute()}")
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.videos_dir.mkdir(parents=True, exist_ok=True)
        print("✅ Feed session directories created successfully")
    
    def create_session_id(self) -> str:
        """Create unique session ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        short_uuid = str(uuid.uuid4())[:8]
        return f"feed_{timestamp}_{short_uuid}"
    
    def start_feed_session(self, arduino_data: Dict[str, Any]) -> str:
        """Start a new feed session"""
        session_id = self.create_session_id()
        timestamp = datetime.now().isoformat()
        
        # Create session data structure
        session_data = {
            "id": session_id,
            "start_timestamp": timestamp,
            "end_timestamp": None,
            "template": arduino_data.get("template", "unknown"),
            "target_weight": arduino_data.get("target_weight", 0),
            "weight_fed": 0,
            "status": "in_progress",
            "reason": None,
            "start_sensors": arduino_data.get("sensors", {}),
            "end_sensors": {},
            "alerts": [],
            "video_local": None,
            "video_cloud": None,
            "duration_seconds": 0
        }
        
        # Save to file
        today = datetime.now().strftime("%Y-%m-%d")
        session_dir = self.logs_dir / today
        session_dir.mkdir(exist_ok=True)
        
        session_file = session_dir / f"{session_id}.json"
        with open(session_file, 'w') as f:
            json.dump(session_data, f, indent=2)
        
        self.current_session = session_data
        return session_id
    
    def end_feed_session(self, arduino_data: Dict[str, Any]) -> bool:
        """End the current feed session"""
        if not self.current_session:
            return False
        
        session_id = self.current_session["id"]
        end_timestamp = datetime.now().isoformat()
        
        # Calculate duration
        start_time = datetime.fromisoformat(self.current_session["start_timestamp"])
        end_time = datetime.fromisoformat(end_timestamp)
        duration = int((end_time - start_time).total_seconds())
        
        # Update session data
        self.current_session.update({
            "end_timestamp": end_timestamp,
            "weight_fed": arduino_data.get("weight_fed", 0),
            "status": "completed",
            "reason": arduino_data.get("reason", "unknown"),
            "end_sensors": arduino_data.get("sensors", {}),
            "duration_seconds": duration
        })
        
        # Save updated session
        today = datetime.now().strftime("%Y-%m-%d")
        session_file = self.logs_dir / today / f"{session_id}.json"
        with open(session_file, 'w') as f:
            json.dump(self.current_session, f, indent=2)
        
        self.current_session = None
        return True
    
    def add_alert_to_session(self, arduino_data: Dict[str, Any]) -> bool:
        """Add alert to current session"""
        if not self.current_session:
            # Create standalone alert if no session active
            return self.create_standalone_alert(arduino_data)
        
        alert_data = {
            "timestamp": datetime.now().isoformat(),
            "alert_type": arduino_data.get("alert_type", "unknown"),
            "message": arduino_data.get("message", ""),
            "sensors": arduino_data.get("sensors", {})
        }
        
        self.current_session["alerts"].append(alert_data)
        
        # Save updated session
        session_id = self.current_session["id"]
        today = datetime.now().strftime("%Y-%m-%d")
        session_file = self.logs_dir / today / f"{session_id}.json"
        with open(session_file, 'w') as f:
            json.dump(self.current_session, f, indent=2)
        
        return True
    
    def create_standalone_alert(self, arduino_data: Dict[str, Any]) -> bool:
        """Create standalone alert when no session is active"""
        alert_id = f"alert_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        timestamp = datetime.now().isoformat()
        
        alert_data = {
            "id": alert_id,
            "type": "standalone_alert",
            "timestamp": timestamp,
            "alert_type": arduino_data.get("alert_type", "unknown"),
            "message": arduino_data.get("message", ""),
            "sensors": arduino_data.get("sensors", {}),
            "video_local": None,
            "video_cloud": None
        }
        
        # Save to alerts subdirectory
        today = datetime.now().strftime("%Y-%m-%d")
        alerts_dir = self.logs_dir / today / "alerts"
        alerts_dir.mkdir(exist_ok=True)
        
        alert_file = alerts_dir / f"{alert_id}.json"
        with open(alert_file, 'w') as f:
            json.dump(alert_data, f, indent=2)
        
        return True
    
    def attach_video_to_session(self, session_id: str, video_path: str) -> bool:
        """Attach video file to a session"""
        try:
            # Find session file
            session_file = self.find_session_file(session_id)
            if not session_file:
                return False
            
            # Load session data
            with open(session_file, 'r') as f:
                session_data = json.load(f)
            
            # Update video path
            session_data["video_local"] = video_path
            
            # Save updated session
            with open(session_file, 'w') as f:
                json.dump(session_data, f, indent=2)
            
            return True
        except Exception:
            return False
    
    def find_session_file(self, session_id: str) -> Optional[Path]:
        """Find session file by ID"""
        for date_dir in self.logs_dir.iterdir():
            if date_dir.is_dir() and date_dir.name.count('-') == 2:  # YYYY-MM-DD format
                session_file = date_dir / f"{session_id}.json"
                if session_file.exists():
                    return session_file
        return None
    
    def get_sessions_by_date_range(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Get sessions within date range"""
        sessions = []
        
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        current_date = start_dt
        while current_date <= end_dt:
            date_str = current_date.strftime("%Y-%m-%d")
            date_dir = self.logs_dir / date_str
            
            if date_dir.exists():
                # Get feed sessions
                for session_file in date_dir.glob("feed_*.json"):
                    try:
                        with open(session_file, 'r') as f:
                            session_data = json.load(f)
                            sessions.append(session_data)
                    except Exception:
                        continue
                
                # Get standalone alerts
                alerts_dir = date_dir / "alerts"
                if alerts_dir.exists():
                    for alert_file in alerts_dir.glob("alert_*.json"):
                        try:
                            with open(alert_file, 'r') as f:
                                alert_data = json.load(f)
                                sessions.append(alert_data)
                        except Exception:
                            continue
            
            current_date += timedelta(days=1)
        
        # Sort by timestamp
        sessions.sort(key=lambda x: x.get("timestamp", x.get("start_timestamp", "")), reverse=True)
        return sessions
    
    def get_sessions_by_template(self, template: str) -> List[Dict[str, Any]]:
        """Get sessions filtered by template"""
        all_sessions = self.get_all_sessions()
        return [s for s in all_sessions if s.get("template") == template]
    
    def get_sessions_by_alert_type(self, alert_type: str) -> List[Dict[str, Any]]:
        """Get sessions filtered by alert type"""
        all_sessions = self.get_all_sessions()
        filtered_sessions = []
        
        for session in all_sessions:
            # Check if session has alerts of this type
            if session.get("type") == "standalone_alert" and session.get("alert_type") == alert_type:
                filtered_sessions.append(session)
            elif session.get("alerts"):
                for alert in session["alerts"]:
                    if alert.get("alert_type") == alert_type:
                        filtered_sessions.append(session)
                        break
        
        return filtered_sessions
    
    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """Get all sessions"""
        sessions = []
        
        for date_dir in self.logs_dir.iterdir():
            if date_dir.is_dir() and date_dir.name.count('-') == 2:  # YYYY-MM-DD format
                # Get feed sessions
                for session_file in date_dir.glob("feed_*.json"):
                    try:
                        with open(session_file, 'r') as f:
                            session_data = json.load(f)
                            sessions.append(session_data)
                    except Exception:
                        continue
                
                # Get standalone alerts
                alerts_dir = date_dir / "alerts"
                if alerts_dir.exists():
                    for alert_file in alerts_dir.glob("alert_*.json"):
                        try:
                            with open(alert_file, 'r') as f:
                                alert_data = json.load(f)
                                sessions.append(alert_data)
                        except Exception:
                            continue
        
        # Sort by timestamp
        sessions.sort(key=lambda x: x.get("timestamp", x.get("start_timestamp", "")), reverse=True)
        return sessions
    
    def get_session_statistics(self) -> Dict[str, Any]:
        """Get statistics about feed sessions"""
        all_sessions = self.get_all_sessions()
        
        feed_sessions = [s for s in all_sessions if s.get("type") != "standalone_alert"]
        standalone_alerts = [s for s in all_sessions if s.get("type") == "standalone_alert"]
        
        stats = {
            "total_feed_sessions": len(feed_sessions),
            "total_standalone_alerts": len(standalone_alerts),
            "templates": {},
            "alert_types": {},
            "total_weight_fed": 0,
            "average_duration": 0
        }
        
        # Calculate template distribution
        for session in feed_sessions:
            template = session.get("template", "unknown")
            stats["templates"][template] = stats["templates"].get(template, 0) + 1
            stats["total_weight_fed"] += session.get("weight_fed", 0)
        
        # Calculate alert type distribution
        for session in all_sessions:
            if session.get("type") == "standalone_alert":
                alert_type = session.get("alert_type", "unknown")
                stats["alert_types"][alert_type] = stats["alert_types"].get(alert_type, 0) + 1
            elif session.get("alerts"):
                for alert in session["alerts"]:
                    alert_type = alert.get("alert_type", "unknown")
                    stats["alert_types"][alert_type] = stats["alert_types"].get(alert_type, 0) + 1
        
        # Calculate average duration
        if feed_sessions:
            total_duration = sum(s.get("duration_seconds", 0) for s in feed_sessions)
            stats["average_duration"] = total_duration / len(feed_sessions)
        
        return stats 