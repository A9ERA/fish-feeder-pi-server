"""
Feeder Service for controlling feeding process sequence
"""
import time
import threading
from typing import Optional
from .control_service import ControlService

class FeederService:
    def __init__(self, control_service: Optional[ControlService] = None):
        """
        Initialize Feeder Service
        
        Args:
            control_service: ControlService instance for device control
        """
        self.control_service = control_service
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

        try:
            print(f"[Feeder Service] Starting feeding process...")
            print(f"Feed size: {feed_size}g, Actuator up: {actuator_up}s, Actuator down: {actuator_down}s")
            print(f"Auger duration: {auger_duration}s, Blower duration: {blower_duration}s")

            # Step 1: Actuator motor up
            print(f"[Feeder Service] Step 1: Moving actuator up for {actuator_up} seconds")
            if not self.control_service.control_actuator_motor('up'):
                raise Exception("Failed to start actuator up")
            
            time.sleep(actuator_up)
            
            if not self.control_service.control_actuator_motor('stop'):
                raise Exception("Failed to stop actuator after up movement")
            print(f"[Feeder Service] Step 1 completed: Actuator up movement finished")

            # Step 2: Actuator motor down
            print(f"[Feeder Service] Step 2: Moving actuator down for {actuator_down} seconds")
            if not self.control_service.control_actuator_motor('down'):
                raise Exception("Failed to start actuator down")
            
            time.sleep(actuator_down)
            
            if not self.control_service.control_actuator_motor('stop'):
                raise Exception("Failed to stop actuator after down movement")
            print(f"[Feeder Service] Step 2 completed: Actuator down movement finished")

            # Step 3: Auger forward
            print(f"[Feeder Service] Step 3: Running auger forward for {auger_duration} seconds")
            if not self.control_service.control_auger('forward'):
                raise Exception("Failed to start auger forward")
            
            time.sleep(auger_duration)
            
            if not self.control_service.control_auger('stop'):
                raise Exception("Failed to stop auger")
            print(f"[Feeder Service] Step 3 completed: Auger operation finished")

            # Step 4: Blower start
            print(f"[Feeder Service] Step 4: Running blower for {blower_duration} seconds")
            if not self.control_service.control_blower('start'):
                raise Exception("Failed to start blower")
            
            time.sleep(blower_duration)
            
            if not self.control_service.control_blower('stop'):
                raise Exception("Failed to stop blower")
            print(f"[Feeder Service] Step 4 completed: Blower operation finished")

            print(f"[Feeder Service] Feeding process completed successfully!")
            
            return {
                'status': 'success',
                'message': 'Feeding process completed successfully',
                'feed_size': feed_size,
                'total_duration': actuator_up + actuator_down + auger_duration + blower_duration,
                'steps_completed': [
                    f"Actuator up: {actuator_up}s",
                    f"Actuator down: {actuator_down}s", 
                    f"Auger forward: {auger_duration}s",
                    f"Blower: {blower_duration}s"
                ]
            }

        except Exception as e:
            error_msg = f"Feeding process failed: {str(e)}"
            print(f"[Feeder Service] Error: {error_msg}")
            
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
                'message': error_msg
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