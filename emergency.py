"""
SafeDrive-AI Emergency Orchestration Subsystem
Coordinates danger detection, response countdown, audio alarms,
snapshot captures, location fixes, database events, and SOS notifications.
Ensures independent subsystem failure resilience and non-blocking operation.
"""
import time
import threading
from typing import Optional, Dict, Any
from pathlib import Path

from config import RESPONSE_TIMEOUT_SECONDS, YAWN_LIMIT
from logger import logger
from location import get_emergency_location, Location
from camera_capture import capture_emergency_photo
from notifications import send_emergency_notification, NotificationResult
from database import save_safety_event


class EmergencyCoordinator:
    """
    Coordinates the entire safety, warning, countdown, and emergency workflow.
    Ensures that failures in any subsystem (photo, location, SMS, DB) are isolated.
    """

    def __init__(self, alarm_manager):
        self.alarm = alarm_manager

        # State flags
        self.is_emergency: bool = False
        self.hazard_lights: bool = False
        self.countdown_active: bool = False
        self.danger_detected: bool = False
        self.danger_reason: str = ""

        # Timers and counters
        self.alarm_start_time: Optional[float] = None
        self.remaining_time: int = RESPONSE_TIMEOUT_SECONDS
        self.previous_yawn_count: int = 0
        self.drowsy_logged: bool = False
        self.sos_triggered: bool = False

        # Status summaries for UI
        self.last_event_id: Optional[int] = None
        self.last_photo_path: Optional[str] = None
        self.last_location: Optional[Location] = None
        self.last_notification_status: str = "IDLE"
        self.last_notification_error: Optional[str] = None
        self.last_provider_name: str = "Mock SMS"

        self._sos_lock = threading.Lock()

    def update(
        self,
        eye_data: Dict[str, Any],
        frame,
        driver_id: Optional[int],
        vehicle_id: Optional[int],
        driver: Optional[Dict[str, Any]],
        vehicle: Optional[Dict[str, Any]]
    ):
        """
        Frame-level update for safety evaluation and countdown tracking.
        Must execute with high performance on each video frame.
        """
        current_yawns = eye_data.get("yawns", 0)
        is_drowsy = eye_data.get("drowsy", False)
        ear = eye_data.get("ear", 0.0)
        mar = eye_data.get("mar", 0.0)
        closed_frames = eye_data.get("closed_frames", 0)

        # -------------------------------------------------------------
        # 1. Periodic Telemetry Logging
        # -------------------------------------------------------------
        if current_yawns > self.previous_yawn_count:
            yawn_danger = current_yawns >= YAWN_LIMIT
            try:
                save_safety_event(
                    driver_id=driver_id,
                    vehicle_id=vehicle_id,
                    event_type="YAWN_LIMIT" if yawn_danger else "YAWN",
                    severity="HIGH" if yawn_danger else "WARNING",
                    ear_value=ear,
                    mar_value=mar,
                    yawn_count=current_yawns,
                    closed_frames=closed_frames,
                    response_status="ALARM" if yawn_danger else "DETECTED",
                    alarm_triggered=yawn_danger
                )
            except Exception as e:
                logger.error(f"Database write error for yawn event: {e}")
            self.previous_yawn_count = current_yawns

        if is_drowsy and not self.drowsy_logged:
            try:
                save_safety_event(
                    driver_id=driver_id,
                    vehicle_id=vehicle_id,
                    event_type="DROWSINESS",
                    severity="HIGH",
                    ear_value=ear,
                    mar_value=mar,
                    yawn_count=current_yawns,
                    closed_frames=closed_frames,
                    response_status="ALARM",
                    alarm_triggered=True
                )
            except Exception as e:
                logger.error(f"Database write error for drowsiness event: {e}")
            self.drowsy_logged = True

        if not is_drowsy:
            self.drowsy_logged = False

        # -------------------------------------------------------------
        # 2. Danger Evaluation & Response Countdown
        # -------------------------------------------------------------
        yawn_limit_reached = current_yawns >= YAWN_LIMIT
        active_danger = yawn_limit_reached or is_drowsy

        if not self.is_emergency:
            if active_danger:
                self.danger_detected = True

                # Determine descriptive reason
                if yawn_limit_reached and is_drowsy:
                    self.danger_reason = f"Drowsiness & Excessive Yawning ({current_yawns} yawns)"
                elif yawn_limit_reached:
                    self.danger_reason = f"Excessive Yawning ({current_yawns} / {YAWN_LIMIT} yawns)"
                else:
                    self.danger_reason = f"Drowsiness / Eyes Closed ({closed_frames} frames)"

                # Initiate or track countdown
                if self.alarm_start_time is None:
                    self.alarm_start_time = time.time()
                    logger.warning(f"Driver danger condition detected: {self.danger_reason}. Starting {RESPONSE_TIMEOUT_SECONDS}s response timer.")

                elapsed = time.time() - self.alarm_start_time
                self.remaining_time = max(0, RESPONSE_TIMEOUT_SECONDS - int(elapsed))
                self.countdown_active = True

                # Play alarm
                self.alarm.play()

                # Timeout reached -> Activate SOS Emergency
                if elapsed >= RESPONSE_TIMEOUT_SECONDS:
                    self._activate_emergency(
                        frame=frame,
                        driver=driver,
                        vehicle=vehicle,
                        driver_id=driver_id,
                        vehicle_id=vehicle_id,
                        eye_data=eye_data
                    )

            else:
                # Normal state: eyes open, yawning below threshold
                if not yawn_limit_reached and not is_drowsy:
                    self.alarm_start_time = None
                    self.countdown_active = False
                    self.danger_detected = False
                    self.danger_reason = ""
                    self.remaining_time = RESPONSE_TIMEOUT_SECONDS
                    self.alarm.stop()

        else:
            # Already in Emergency Mode: Keep alarm active and hazards flashing
            self.alarm.play()
            self.hazard_lights = True
            self.countdown_active = False

    def _activate_emergency(
        self,
        frame,
        driver: Optional[Dict[str, Any]],
        vehicle: Optional[Dict[str, Any]],
        driver_id: Optional[int],
        vehicle_id: Optional[int],
        eye_data: Dict[str, Any]
    ):
        """Activates emergency mode and dispatches SOS in a background thread."""
        with self._sos_lock:
            if self.is_emergency or self.sos_triggered:
                return
            self.is_emergency = True
            self.hazard_lights = True
            self.countdown_active = False
            self.sos_triggered = True

        logger.critical(f"EMERGENCY MODE ACTIVATED: Driver unresponsive to warning countdown for reason: {self.danger_reason}")

        # Copy frame for snapshot so we don't race with camera frame mutation
        frame_copy = frame.copy() if frame is not None else None

        # Execute SOS orchestration asynchronously to avoid freezing the camera loop
        worker = threading.Thread(
            target=self._sos_orchestration_worker,
            args=(frame_copy, driver, vehicle, driver_id, vehicle_id, eye_data, self.danger_reason),
            daemon=True
        )
        worker.start()

    def _sos_orchestration_worker(
        self,
        frame,
        driver: Optional[Dict[str, Any]],
        vehicle: Optional[Dict[str, Any]],
        driver_id: Optional[int],
        vehicle_id: Optional[int],
        eye_data: Dict[str, Any],
        reason: str
    ):
        """
        Executes SOS pipeline with strict fault isolation.
        Each failure (photo, location, database, SMS) is handled independently.
        """
        # 1. Photo Capture Subsystem
        photo_path = None
        try:
            photo_path = capture_emergency_photo(frame)
            self.last_photo_path = str(photo_path) if photo_path else "Capture failed"
        except Exception as e:
            logger.error(f"SOS Photo Capture Subsystem Error: {e}")
            self.last_photo_path = "Unavailable"

        # 2. Location Subsystem
        try:
            location_obj = get_emergency_location()
            self.last_location = location_obj
        except Exception as e:
            logger.error(f"SOS Location Subsystem Error: {e}")
            location_obj = Location(is_available=False, status_text="Unavailable")
            self.last_location = location_obj

        # 3. Database Event Subsystem
        event_id = None
        try:
            event_id = save_safety_event(
                driver_id=driver_id,
                vehicle_id=vehicle_id,
                event_type="EMERGENCY",
                severity="CRITICAL",
                ear_value=eye_data.get("ear", 0.0),
                mar_value=eye_data.get("mar", 0.0),
                yawn_count=eye_data.get("yawns", 0),
                closed_frames=eye_data.get("closed_frames", 0),
                response_status="NO_RESPONSE",
                latitude=location_obj.latitude,
                longitude=location_obj.longitude,
                location_accuracy=location_obj.accuracy,
                alarm_triggered=True,
                hazard_activated=True,
                sos_sent=True,
                photo_path=str(photo_path) if photo_path else None,
                notification_status="PENDING"
            )
            self.last_event_id = event_id
        except Exception as e:
            logger.error(f"SOS Database Event Logging Error: {e}")

        # 4. Notification Subsystem (Mock or Optional Real SMS)
        try:
            result: NotificationResult = send_emergency_notification(
                driver=driver,
                vehicle=vehicle,
                reason=reason,
                location_obj=location_obj,
                photo_path=Path(photo_path) if photo_path else None,
                event_id=event_id
            )
            self.last_notification_status = result.status
            self.last_provider_name = result.provider_name
            self.last_notification_error = result.error
            logger.info(f"SOS Notification completed with status: {result.status} via {result.provider_name}")
        except Exception as e:
            logger.error(f"SOS Notification Subsystem Error: {e}")
            self.last_notification_status = "FAILED"
            self.last_notification_error = str(e)

    def reset(self, eye_detector):
        """
        Resets emergency state, alarm timer, detection counters, and audio.
        Guaranteed to not cause immediate alarm restart.
        """
        logger.info("Driver reset triggered (R key). Restoring normal monitoring state.")
        self.is_emergency = False
        self.hazard_lights = False
        self.countdown_active = False
        self.danger_detected = False
        self.danger_reason = ""
        self.alarm_start_time = None
        self.remaining_time = RESPONSE_TIMEOUT_SECONDS
        self.previous_yawn_count = 0
        self.drowsy_logged = False
        self.sos_triggered = False

        # Stop alarm sound immediately
        self.alarm.stop()

        # Reset detector internal counters
        if eye_detector:
            eye_detector.reset_detection()

    def get_status_summary(self) -> Dict[str, Any]:
        """Returns snapshot of current emergency system state for the UI."""
        if self.is_emergency:
            state = "EMERGENCY"
        elif self.countdown_active:
            state = "DANGER"
        elif self.danger_detected:
            state = "WARNING"
        else:
            state = "NORMAL"

        return {
            "state": state,
            "is_emergency": self.is_emergency,
            "hazard_lights": self.hazard_lights,
            "countdown_active": self.countdown_active,
            "remaining_time": self.remaining_time,
            "danger_reason": self.danger_reason,
            "alarm_active": self.alarm.is_playing(),
            "notification_status": self.last_notification_status,
            "provider_name": self.last_provider_name,
            "photo_status": "Captured" if self.last_photo_path and "failed" not in self.last_photo_path else "None",
            "last_event_id": self.last_event_id
        }
