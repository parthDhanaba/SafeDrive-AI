"""
SafeDrive-AI - AI-Powered Driver Attentiveness & Safety Monitoring System
Main Application Entry Point.
"""
import sys
import time
import argparse
import threading
from typing import Optional

import cv2

from config import (
    CAMERA_INDEX,
    CAMERA_WIDTH,
    CAMERA_HEIGHT,
    APP_NAME,
    APP_VERSION
)
from logger import logger
from detector import FaceDetector
from eye import EyeDetector
from alarm import AlarmManager
from emergency import EmergencyCoordinator
from location import location_provider
from database import (
    initialize_database,
    get_default_profile,
    get_driver,
    get_vehicle,
    add_driver,
    add_vehicle
)
from ui import SafeDriveDashboard


def open_camera(camera_index: int = CAMERA_INDEX) -> Optional[cv2.VideoCapture]:
    """
    Safely opens webcam with DirectShow on Windows, with fallback to standard index.
    Returns cv2.VideoCapture object or None if no camera is available.
    """
    logger.info(f"Attempting to initialize webcam index {camera_index}...")
    try:
        camera = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        if not camera.isOpened():
            logger.warning("DirectShow camera access failed. Retrying with default backend...")
            camera = cv2.VideoCapture(camera_index)

        if camera.isOpened():
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
            logger.info("Webcam successfully initialized.")
            return camera
        else:
            logger.error(f"Could not open webcam index {camera_index}.")
            return None
    except Exception as e:
        logger.error(f"Error accessing webcam: {e}")
        return None


class SafeDriveApplication:
    """Master Application Manager integrating Computer Vision, Orchestration, and UI."""

    def __init__(self, camera_index: int = CAMERA_INDEX):
        self.camera_index = camera_index
        self.running = False

        # Database initialization & profiles
        initialize_database()
        self.driver_id, self.vehicle_id = get_default_profile()

        # If no profile exists yet, seed initial default profile
        if not self.driver_id or not self.vehicle_id:
            logger.info("No active driver profile found in database. Creating default driver profile...")
            self.driver_id = add_driver(
                name="Default Driver",
                phone="+15550001234",
                emergency_contact_name="Emergency Support",
                emergency_contact_phone="+15559998888"
            )
            self.vehicle_id = add_vehicle(
                vehicle_number="MH-08-SAFE-01",
                vehicle_type="SUV",
                owner_name="Default Fleet"
            )

        self.driver_profile = get_driver(self.driver_id)
        self.vehicle_profile = get_vehicle(self.vehicle_id)

        # Warm up Windows device GPS in background
        location_provider.prefetch_location()

        # Core subsystems
        self.detector = FaceDetector()
        self.eye_detector = EyeDetector()
        self.alarm = AlarmManager()
        self.coordinator = EmergencyCoordinator(self.alarm)

        # Camera
        self.camera = open_camera(self.camera_index)

        # Dashboard UI
        self.dashboard = SafeDriveDashboard(
            on_reset_callback=self.on_reset,
            on_quit_callback=self.on_quit,
            driver_id=self.driver_id,
            vehicle_id=self.vehicle_id
        )

        self.previous_time = time.time()
        self.camera_thread: Optional[threading.Thread] = None

    def on_reset(self):
        """User triggered reset via UI button or R key."""
        self.coordinator.reset(self.eye_detector)

    def on_quit(self):
        """Clean shutdown of monitoring threads, camera, and audio."""
        logger.info("Shutdown initiated by user.")
        self.running = False
        if self.alarm:
            self.alarm.stop()
        if self.camera and self.camera.isOpened():
            self.camera.release()
            logger.info("Camera released.")

    def run(self):
        """Starts monitoring pipeline and enters the UI event loop."""
        self.running = True

        if not self.camera or not self.camera.isOpened():
            logger.warning("Camera not available. Dashboard will display standby state.")
            # Set notification on UI that camera is disconnected
            if hasattr(self.dashboard, "video_label"):
                self.dashboard.video_label.configure(
                    text="⚠️ WEBCAM DISCONNECTED OR IN USE\nPlease connect a camera and restart the application."
                )

        # Launch processing loop via Tkinter scheduler
        self._schedule_frame_update()
        self.dashboard.mainloop()

    def _schedule_frame_update(self):
        """Periodic tick reading camera, calculating telemetry, and updating dashboard."""
        if not self.running:
            return

        if self.camera and self.camera.isOpened():
            success, frame = self.camera.read()

            if success and frame is not None:
                frame = cv2.flip(frame, 1)

                # Computer Vision Pipeline (Preserving existing verified mesh)
                frame, face_landmarks = self.detector.detect(frame)
                frame, eye_data = self.eye_detector.process(frame, face_landmarks)

                # Calculate FPS
                curr_time = time.time()
                fps = 1.0 / max(curr_time - self.previous_time, 0.001)
                self.previous_time = curr_time

                # Safety & Emergency Orchestration
                self.coordinator.update(
                    eye_data=eye_data,
                    frame=frame,
                    driver_id=self.driver_id,
                    vehicle_id=self.vehicle_id,
                    driver=self.driver_profile,
                    vehicle=self.vehicle_profile
                )

                # Fetch Status & Location
                emerg_status = self.coordinator.get_status_summary()
                loc = location_provider.get_cached_location()

                # Push to UI
                self.dashboard.update_frame(frame)
                self.dashboard.update_telemetry(fps, eye_data, emerg_status, loc)

        # Schedule next iteration (approx 30 FPS tick)
        self.dashboard.after(10, self._schedule_frame_update)


def main():
    parser = argparse.ArgumentParser(description=f"{APP_NAME} - AI Driver Safety Monitoring")
    parser.add_argument("--camera", type=int, default=CAMERA_INDEX, help="Camera device index (default: 0)")
    args = parser.parse_args()

    app = SafeDriveApplication(camera_index=args.camera)
    app.run()


if __name__ == "__main__":
    main()