"""
SafeDrive-AI - AI-Powered Driver Attentiveness & Safety Monitoring System
Main Application Entry Point.
"""
import sys
import time
import argparse
import socket
import threading
from typing import Optional, Dict, Any

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


# Global single-instance guard socket
_INSTANCE_LOCK_SOCKET = None


def acquire_single_instance_lock(port: int = 49152) -> bool:
    """Ensures only one instance of SafeDrive AI can run concurrently on this computer."""
    global _INSTANCE_LOCK_SOCKET
    try:
        _INSTANCE_LOCK_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _INSTANCE_LOCK_SOCKET.bind(("127.0.0.1", port))
        return True
    except OSError:
        logger.error(
            "Another instance of SafeDrive AI is already running! "
            "Please close the existing window before launching a new one."
        )
        return False


def open_camera(camera_index: int = CAMERA_INDEX) -> Optional[cv2.VideoCapture]:
    """
    Safely opens webcam with DirectShow on Windows, configuring low latency buffer
    and MJPG compression for fluid 30 FPS capture.
    """
    logger.info(f"Attempting to initialize webcam index {camera_index}...")
    try:
        camera = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        if not camera.isOpened():
            logger.warning("DirectShow camera access failed. Retrying with default backend...")
            camera = cv2.VideoCapture(camera_index)

        if camera.isOpened():
            # Configure webcam for fluid 30 FPS performance
            camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
            camera.set(cv2.CAP_PROP_FPS, 30)
            logger.info(f"Webcam successfully initialized at {CAMERA_WIDTH}x{CAMERA_HEIGHT}.")
            return camera
        else:
            logger.error(f"Could not open webcam index {camera_index}.")
            return None
    except Exception as e:
        logger.error(f"Error accessing webcam: {e}")
        return None


class CameraWorker(threading.Thread):
    """
    Dedicated background worker thread for high-FPS camera capture and AI vision analysis.
    Decouples computer-vision processing from the Tkinter GUI thread to prevent lag.
    """

    def __init__(
        self,
        camera: Optional[cv2.VideoCapture],
        detector: FaceDetector,
        eye_detector: EyeDetector,
        coordinator: EmergencyCoordinator,
        driver_id: Optional[int],
        vehicle_id: Optional[int],
        driver_profile: Optional[Dict[str, Any]],
        vehicle_profile: Optional[Dict[str, Any]]
    ):
        super().__init__(daemon=True)
        self.camera = camera
        self.detector = detector
        self.eye_detector = eye_detector
        self.coordinator = coordinator
        self.driver_id = driver_id
        self.vehicle_id = vehicle_id
        self.driver_profile = driver_profile
        self.vehicle_profile = vehicle_profile

        self.running = True
        self.lock = threading.Lock()
        self.latest_frame = None
        self.latest_eye_data = {
            "ear": 0.0,
            "mar": 0.0,
            "state": "NO FACE",
            "closed_frames": 0,
            "drowsy": False,
            "yawns": 0
        }
        self.latest_fps = 0.0

    def run(self):
        prev_time = time.time()

        while self.running:
            if not self.camera or not self.camera.isOpened():
                time.sleep(0.05)
                continue

            success, frame = self.camera.read()
            if not success or frame is None:
                time.sleep(0.01)
                continue

            frame = cv2.flip(frame, 1)

            # Computer Vision Pipeline (Eye + Mouth Landmarks)
            frame, face_landmarks = self.detector.detect(frame)
            frame, eye_data = self.eye_detector.process(frame, face_landmarks)

            # FPS calculation
            curr_time = time.time()
            fps = 1.0 / max(curr_time - prev_time, 0.001)
            prev_time = curr_time

            # Safety Coordinator update
            self.coordinator.update(
                eye_data=eye_data,
                frame=frame,
                driver_id=self.driver_id,
                vehicle_id=self.vehicle_id,
                driver=self.driver_profile,
                vehicle=self.vehicle_profile
            )

            # Store latest telemetry under lock
            with self.lock:
                self.latest_frame = frame
                self.latest_eye_data = eye_data
                self.latest_fps = fps

            # Small sleep to yield CPU
            time.sleep(0.005)

    def stop(self):
        self.running = False


class SafeDriveApplication:
    """Master Application Manager integrating Computer Vision, Orchestration, and UI."""

    def __init__(self, camera_index: int = CAMERA_INDEX):
        self.camera_index = camera_index
        self.running = False

        # Database initialization & profiles
        initialize_database()
        self.driver_id, self.vehicle_id = get_default_profile()

        # Seed default profile if database was empty
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

        # Background Worker Thread for capture & CV
        self.worker = CameraWorker(
            camera=self.camera,
            detector=self.detector,
            eye_detector=self.eye_detector,
            coordinator=self.coordinator,
            driver_id=self.driver_id,
            vehicle_id=self.vehicle_id,
            driver_profile=self.driver_profile,
            vehicle_profile=self.vehicle_profile
        )

        # Dashboard UI
        self.dashboard = SafeDriveDashboard(
            on_reset_callback=self.on_reset,
            on_quit_callback=self.on_quit,
            driver_id=self.driver_id,
            vehicle_id=self.vehicle_id
        )

    def on_reset(self):
        """User triggered reset via UI button or R key."""
        self.coordinator.reset(self.eye_detector)

    def on_quit(self):
        """Clean shutdown of monitoring threads, camera, and audio."""
        logger.info("Shutdown initiated by user.")
        self.running = False
        if self.worker:
            self.worker.stop()
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
            if hasattr(self.dashboard, "video_label"):
                self.dashboard.video_label.configure(
                    text="⚠️ WEBCAM DISCONNECTED OR IN USE\nPlease connect a camera and restart the application."
                )
        else:
            # Start background vision worker
            self.worker.start()

        # Launch UI scheduler
        self._schedule_frame_update()
        self.dashboard.mainloop()

    def _schedule_frame_update(self):
        """Periodic UI tick pulling latest processed frame and telemetry without blocking."""
        if not self.running:
            return

        frame = None
        eye_data = None
        fps = 0.0

        if self.worker and self.worker.is_alive():
            with self.worker.lock:
                if self.worker.latest_frame is not None:
                    frame = self.worker.latest_frame.copy()
                    eye_data = self.worker.latest_eye_data
                    fps = self.worker.latest_fps

        if frame is not None and eye_data is not None:
            emerg_status = self.coordinator.get_status_summary()
            loc = location_provider.get_cached_location()

            self.dashboard.update_frame(frame)
            self.dashboard.update_telemetry(fps, eye_data, emerg_status, loc)

        # Schedule next UI tick (~30-50 FPS refresh)
        self.dashboard.after(20, self._schedule_frame_update)


def main():
    parser = argparse.ArgumentParser(description=f"{APP_NAME} - AI Driver Safety Monitoring")
    parser.add_argument("--camera", type=int, default=CAMERA_INDEX, help="Camera device index (default: 0)")
    args = parser.parse_args()

    # Guard against accidental multiple instances
    if not acquire_single_instance_lock():
        sys.exit(1)

    app = SafeDriveApplication(camera_index=args.camera)
    app.run()


if __name__ == "__main__":
    main()