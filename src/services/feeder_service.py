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

    def start(self, feed_size: int, actuator_up: int, actuator_down: int, 
              auger_duration: int, blower_duration: int) -> dict:
        """
        Start the feeding process sequence
        
        Args:
            feed_size: Feed size in grams (for reference/logging)
            actuator_up: Duration in seconds for actuator up movement
            actuator_down: Duration in seconds for actuator down movement
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
            print(f"Feed size: {feed_size}g, Actuator up: {actuator_up}s, Actuator down: {actuator_down}s")
            print(f"Auger duration: {auger_duration}s, Blower duration: {blower_duration}s")

            # Start video recording
            try:
                video_file = self.video_service.start_feeder_recording()
                print(f"[Feeder Service] Video recording started: {video_file}")
            except Exception as video_error:
                print(f"[Feeder Service] Warning: Failed to start video recording: {video_error}")

            # Step 1: Actuator motor up
            print(f"[Feeder Service] Step 1: Moving actuator up for {actuator_up} seconds")
            if not self.control_service.control_actuator_motor('up'):
                raise Exception("Failed to start actuator up")
            
            time.sleep(actuator_up)
            
            if not self.control_service.control_actuator_motor('stop'):
                raise Exception("Failed to stop actuator after up movement")
            print(f"[Feeder Service] Step 1 completed: Actuator up movement finished")

            time.sleep(1)
            
            # Step 2: Actuator motor down
            print(f"[Feeder Service] Step 2: Moving actuator down for {actuator_down} seconds")
            if not self.control_service.control_actuator_motor('down'):
                raise Exception("Failed to start actuator down")
            
            time.sleep(actuator_down)
            
            if not self.control_service.control_actuator_motor('stop'):
                raise Exception("Failed to stop actuator after down movement")
            print(f"[Feeder Service] Step 2 completed: Actuator down movement finished")

            # Step 3 & 4: Start auger and blower simultaneously
            print(f"[Feeder Service] Step 3 & 4: Starting auger (forward) and blower simultaneously")
            print(f"Auger duration: {auger_duration}s, Blower duration: {blower_duration}s")
            
            # Start both devices
            if not self.control_service.control_auger('forward'):
                raise Exception("Failed to start auger forward")
            
            if not self.control_service.control_blower('start'):
                raise Exception("Failed to start blower")
            
            # Create functions to stop each device after their respective durations
            auger_stopped = threading.Event()
            blower_stopped = threading.Event()
            
            def stop_auger():
                time.sleep(auger_duration)
                if not self.control_service.control_auger('stop'):
                    print(f"[Feeder Service] Warning: Failed to stop auger")
                else:
                    print(f"[Feeder Service] Auger operation finished after {auger_duration}s")
                auger_stopped.set()
            
            def stop_blower():
                time.sleep(blower_duration)
                if not self.control_service.control_blower('stop'):
                    print(f"[Feeder Service] Warning: Failed to stop blower")
                else:
                    print(f"[Feeder Service] Blower operation finished after {blower_duration}s")
                blower_stopped.set()
            
            # Start timer threads for stopping each device
            auger_thread = threading.Thread(target=stop_auger)
            blower_thread = threading.Thread(target=stop_blower)
            
            auger_thread.start()
            blower_thread.start()
            
            # Wait for both operations to complete
            auger_stopped.wait()
            blower_stopped.wait()
            
            # Wait for threads to finish
            auger_thread.join()
            blower_thread.join()
            
            print(f"[Feeder Service] Step 3 & 4 completed: Both auger and blower operations finished")

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
                message='Feeding process completed successfully',
                video_file=video_filename
            )
            
            return {
                'status': 'success',
                'message': 'Feeding process completed successfully',
                'feed_size': feed_size,
                'video_file': video_file,
                'total_duration': actuator_up + actuator_down + auger_duration + blower_duration,
                'steps_completed': [
                    f"Actuator up: {actuator_up}s",
                    f"Actuator down: {actuator_down}s", 
                    f"Auger forward & Blower (simultaneous): {auger_duration}s & {blower_duration}s"
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
            
            # Log failed feed operation
            # Extract only filename from full path for CSV storage
            video_filename = Path(video_file).name if video_file else ""
            self.history_service.log_feed_operation(
                feed_size=feed_size,
                actuator_up=actuator_up,
                actuator_down=actuator_down,
                auger_duration=auger_duration,
                blower_duration=blower_duration,
                status='error',
                message=error_msg,
                video_file=video_filename
            )
            
            # Try to stop all devices in case of error
            try:
                self.control_service.control_actuator_motor('stop')
                self.control_service.control_auger('stop')
                self.control_service.control_blower('stop')
                print(f"[Feeder Service] Emergency stop commands sent to all devices")
            except:
                print(f"[Feeder Service] Failed to send emergency stop commands")

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
            
            # Stop all devices
            self.control_service.control_actuator_motor('stop')
            self.control_service.control_auger('stop') 
            self.control_service.control_blower('stop')
            
            self.is_running = False
            
            return {
                'status': 'success',
                'message': 'All feeder devices stopped successfully'
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to stop devices: {str(e)}'
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