"""
Feeder Service for controlling feeding process sequence
"""
import time
import threading
from typing import Optional
from pathlib import Path
from .control_service import ControlService
from .feeder_history_service import FeederHistoryService
from .video_stream_service import VideoStreamService

class FeederService:
    def __init__(self, control_service: Optional[ControlService] = None, video_service: Optional[VideoStreamService] = None):
        """
        Initialize Feeder Service
        
        Args:
            control_service: ControlService instance for device control
            video_service: VideoStreamService instance for video recording
        """
        self.control_service = control_service
        self.history_service = FeederHistoryService()
        # Only create VideoStreamService if not provided (avoid multiple camera instances)
        if video_service is not None:
            self.video_service = video_service
        else:
            self.video_service = VideoStreamService()
        self._lock = threading.Lock()
        self.is_running = False

    def start(self, feed_size: int, auger_duration: int, blower_duration: int) -> dict:
        """
        Start the feeding process sequence
        
        Args:
            feed_size: Feed size in grams (for reference/logging)
            auger_duration: Duration in seconds for auger operation
            blower_duration: Duration in seconds for blower operation
            
        Returns:
            dict: Status and result of the feeding process
        """
        if not self.control_service:
            return {
                'status': 'error',
                'message': 'Control service not available'
            }

        with self._lock:
            if self.is_running:
                return {
                    'status': 'error',
                    'message': 'Feeding process is already running'
                }
            
            self.is_running = True

        video_file = None
        try:
            print(f"[Feeder Service] Starting feeding process...")
            print(f"Feed size: {feed_size}g, Auger duration: {auger_duration}s, Blower duration: {blower_duration}s")
            print(f"Note: Actuator timings are fixed at 5s up and 10s down in Arduino")

            # Start video recording
            try:
                video_file = self.video_service.start_feeder_recording()
                print(f"[Feeder Service] Video recording started: {video_file}")
            except Exception as video_error:
                print(f"[Feeder Service] Warning: Failed to start video recording: {video_error}")

            # Send feeder start command to Arduino with parameters (only auger and blower durations)
            feeder_params = f"{auger_duration},{blower_duration}"
            command = f"feeder:start:{feeder_params}"
            
            print(f"[Feeder Service] Sending command to Arduino: [control]:{command}")
            if not self.control_service._send_command(command):
                raise Exception("Failed to send feeder start command to Arduino")
            
            # Calculate total estimated duration (with some buffer)
            # Using fixed actuator timings: actuator_up=5, actuator_down=10
            actuator_up = 5
            actuator_down = 10
            total_duration = actuator_up + actuator_down + max(auger_duration, blower_duration)
            buffer_time = 5  # Extra 5 seconds buffer
            estimated_duration = total_duration + buffer_time
            
            print(f"[Feeder Service] Feeding process initiated on Arduino. Estimated duration: {estimated_duration}s")
            
            # Wait for the estimated duration
            time.sleep(estimated_duration)

            # Stop video recording
            try:
                if video_file:
                    final_video_file = self.video_service.stop_feeder_recording()
                    print(f"[Feeder Service] Video recording stopped: {final_video_file}")
            except Exception as video_error:
                print(f"[Feeder Service] Warning: Failed to stop video recording: {video_error}")

            print(f"[Feeder Service] Feeding process completed successfully!")
            
            # Log successful feed operation
            # Extract only filename from full path for CSV storage
            video_filename = Path(video_file).name if video_file else ""
            self.history_service.log_feed_operation(
                feed_size=feed_size,
                actuator_up=actuator_up,
                actuator_down=actuator_down,
                auger_duration=auger_duration,
                blower_duration=blower_duration,
                status='success',
                message='Feeding process completed successfully (Arduino controlled)',
                video_file=video_filename
            )
            
            return {
                'status': 'success',
                'message': 'Feeding process completed successfully (Arduino controlled)',
                'feed_size': feed_size,
                'video_file': video_file,
                'total_duration': estimated_duration,
                'steps_completed': [
                    f"Arduino controlled sequence:",
                    f"  - Actuator up: {actuator_up}s (fixed)",
                    f"  - Actuator down: {actuator_down}s (fixed)", 
                    f"  - Auger forward & Blower (simultaneous): {auger_duration}s & {blower_duration}s"
                ]
            }

        except Exception as e:
            error_msg = f"Feeding process failed: {str(e)}"
            print(f"[Feeder Service] Error: {error_msg}")
            
            # Stop video recording on error
            try:
                if video_file:
                    self.video_service.stop_feeder_recording()
                    print(f"[Feeder Service] Video recording stopped due to error")
            except Exception as video_error:
                print(f"[Feeder Service] Warning: Failed to stop video recording on error: {video_error}")
            
            # Send emergency stop command to Arduino
            try:
                print(f"[Feeder Service] Sending emergency stop command to Arduino")
                self.control_service._send_command("feeder:stop")
            except:
                print(f"[Feeder Service] Failed to send emergency stop command to Arduino")
            
            # Log failed feed operation (use fixed actuator values for logging)
            # Extract only filename from full path for CSV storage
            video_filename = Path(video_file).name if video_file else ""
            self.history_service.log_feed_operation(
                feed_size=feed_size,
                actuator_up=5,  # Fixed value
                actuator_down=10,  # Fixed value
                auger_duration=auger_duration,
                blower_duration=blower_duration,
                status='error',
                message=error_msg,
                video_file=video_filename
            )

            return {
                'status': 'error',
                'message': error_msg,
                'video_file': video_file
            }
        
        finally:
            self.is_running = False

    def stop_all(self) -> dict:
        """
        Emergency stop all devices
        
        Returns:
            dict: Status of the stop operation
        """
        if not self.control_service:
            return {
                'status': 'error',
                'message': 'Control service not available'
            }

        try:
            print(f"[Feeder Service] Emergency stop initiated")
            
            # Send emergency stop command to Arduino
            self.control_service._send_command("feeder:stop")
            
            self.is_running = False
            
            return {
                'status': 'success',
                'message': 'Emergency stop command sent to Arduino'
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to send stop command: {str(e)}'
            }

    def get_status(self) -> dict:
        """
        Get current feeding process status
        
        Returns:
            dict: Current status information
        """
        return {
            'is_running': self.is_running,
            'control_service_available': self.control_service is not None
        } 