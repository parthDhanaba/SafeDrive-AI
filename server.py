"""
SafeDrive-AI Flask REST & MJPEG Streaming Server
Exposes real-time computer-vision telemetry, MJPEG webcam video stream,
deep learning model inference status, emergency orchestration, and session controls.
"""
import os
import sys
import time
import math
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

import cv2
import numpy as np
from flask import Flask, Response, jsonify, request, send_from_directory
from flask_cors import CORS

from config import (
    CAMERA_INDEX,
    CAMERA_WIDTH,
    CAMERA_HEIGHT,
    APP_NAME,
    APP_VERSION,
    EAR_THRESHOLD,
    MAR_THRESHOLD,
    EYE_MODEL_THRESHOLD,
    YAWN_MODEL_THRESHOLD,
    AI_DETECTION_MODE,
    RESPONSE_TIMEOUT_SECONDS,
    YAWN_LIMIT,
    CAPTURE_DIR
)
from logger import logger
from detector import FaceDetector
from eye import EyeDetector
from alarm import AlarmManager
from emergency import EmergencyCoordinator
from location import location_provider
from model_loader import eye_model, yawn_model
from database import (
    initialize_database,
    get_default_profile,
    get_driver,
    get_vehicle,
    add_driver,
    add_vehicle,
    get_recent_events,
    get_event_statistics,
    save_safety_event
)


# Initialize Flask App
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Ensure database is initialized
initialize_database()
default_driver_id, default_vehicle_id = get_default_profile()
if not default_driver_id or not default_vehicle_id:
    logger.info("Seeding default driver profile for web server...")
    default_driver_id = add_driver(
        name="Default Driver",
        phone="+15550001234",
        emergency_contact_name="Emergency Support",
        emergency_contact_phone="+15559998888"
    )
    default_vehicle_id = add_vehicle(
        vehicle_number="MH-08-SAFE-01",
        vehicle_type="SUV",
        owner_name="Default Fleet"
    )

driver_profile = get_driver(default_driver_id)
vehicle_profile = get_vehicle(default_vehicle_id)

# Core AI & Safety Singletons
detector = FaceDetector()
eye_detector = EyeDetector()
alarm_manager = AlarmManager()
coordinator = EmergencyCoordinator(alarm_manager)

# Location prefetch
location_provider.prefetch_location()


class VisionPipeline:
    """
    High-performance background vision and camera pipeline.
    Maintains a dedicated 30 FPS capture thread, runs face mesh & DL models,
    encodes latest frames to JPEG, and provides thread-safe access for web clients.
    """

    def __init__(self, camera_index: int = CAMERA_INDEX):
        self.camera_index = camera_index
        self.camera: Optional[cv2.VideoCapture] = None
        self.camera_connected: bool = False
        self.camera_error: Optional[str] = None
        self.running: bool = False
        self.monitoring_active: bool = True

        self.lock = threading.Lock()
        self.latest_jpeg: Optional[bytes] = None
        self.latest_raw_frame: Optional[np.ndarray] = None
        self.latest_telemetry: Dict[str, Any] = {
            "ear": 0.0,
            "mar": 0.0,
            "state": "INITIALIZING",
            "closed_frames": 0,
            "drowsy": False,
            "yawns": 0,
            "eye_open_prob": 1.0,
            "yawn_prob": 0.0,
            "fps": 0.0
        }

        self.session_start_time = time.time()
        self.worker_thread: Optional[threading.Thread] = None

        # Diagnostic logging state tracking
        self._last_diag_state = None
        self._last_diag_drowsy = None
        self._last_diag_alarm = None
        self._last_diag_log_time = 0.0

        self._init_camera()

    def _init_camera(self):
        """Attempts to open physical webcam with DirectShow then default backend."""
        logger.info(f"Opening camera index {self.camera_index}...")
        try:
            self.camera = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
            if not self.camera or not self.camera.isOpened():
                logger.warning("DirectShow camera access failed, trying default...")
                self.camera = cv2.VideoCapture(self.camera_index)

            if self.camera and self.camera.isOpened():
                self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                self.camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
                self.camera.set(cv2.CAP_PROP_FPS, 30)
                self.camera_connected = True
                self.camera_error = None
                logger.info("Physical webcam opened successfully.")
            else:
                self.camera_connected = False
                self.camera_error = f"Cannot open webcam index {self.camera_index}. Video will use synthetic driver simulation."
                logger.warning(self.camera_error)
        except Exception as e:
            self.camera_connected = False
            self.camera_error = str(e)
            logger.error(f"Error accessing webcam: {e}")

    def _generate_synthetic_frame(self, t: float) -> np.ndarray:
        """
        Generates a high-tech synthetic driver test pattern with cabin telemetry
        if physical webcam is absent or busy.
        """
        frame = np.zeros((CAMERA_HEIGHT, CAMERA_WIDTH, 3), dtype=np.uint8)
        # Deep cockpit gradient
        for y in range(CAMERA_HEIGHT):
            shade = int(14 + (y / CAMERA_HEIGHT) * 18)
            frame[y, :] = (shade + 8, shade + 4, shade)

        # Subtle HUD grid lines
        grid_color = (35, 45, 60)
        for x in range(0, CAMERA_WIDTH, 40):
            cv2.line(frame, (x, 0), (x, CAMERA_HEIGHT), grid_color, 1)
        for y in range(0, CAMERA_HEIGHT, 40):
            cv2.line(frame, (0, y), (CAMERA_WIDTH, y), grid_color, 1)

        # Scanning reticle animation
        center_x, center_y = CAMERA_WIDTH // 2, CAMERA_HEIGHT // 2
        sweep_y = int(center_y + math.sin(t * 2.0) * 120)
        cv2.line(frame, (center_x - 140, sweep_y), (center_x + 140, sweep_y), (0, 230, 200), 1, cv2.LINE_AA)

        # Driver bounding bracket simulation
        bx1, by1 = center_x - 110, center_y - 120
        bx2, by2 = center_x + 110, center_y + 110
        hud_col = (0, 210, 160)
        br_len = 24
        # Corners
        cv2.line(frame, (bx1, by1), (bx1 + br_len, by1), hud_col, 2)
        cv2.line(frame, (bx1, by1), (bx1, by1 + br_len), hud_col, 2)
        cv2.line(frame, (bx2, by1), (bx2 - br_len, by1), hud_col, 2)
        cv2.line(frame, (bx2, by1), (bx2, by1 + br_len), hud_col, 2)
        cv2.line(frame, (bx1, by2), (bx1 + br_len, by2), hud_col, 2)
        cv2.line(frame, (bx1, by2), (bx1, by2 - br_len), hud_col, 2)
        cv2.line(frame, (bx2, by2), (bx2 - br_len, by2), hud_col, 2)
        cv2.line(frame, (bx2, by2), (bx2, by2 - br_len), hud_col, 2)

        # Simulated face features
        eye_y = center_y - 30
        left_eye_x = center_x - 45
        right_eye_x = center_x + 45
        cv2.circle(frame, (left_eye_x, eye_y), 6, (0, 255, 0), -1)
        cv2.circle(frame, (right_eye_x, eye_y), 6, (0, 255, 0), -1)
        cv2.ellipse(frame, (center_x, center_y + 45), (30, 12), 0, 0, 360, (255, 0, 255), 2)

        # Overlay text
        cv2.putText(frame, "SAFEDRIVE AI - SYNTHETIC DRIVER TEST FEED", (16, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 230, 200), 1, cv2.LINE_AA)
        cv2.putText(frame, f"STATUS: {self.latest_telemetry.get('state', 'NORMAL')}", (16, 52),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(frame, "PHYSICAL WEBCAM STANDBY / OFFLINE", (16, CAMERA_HEIGHT - 16),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (100, 160, 255), 1, cv2.LINE_AA)

        return frame

    def start(self):
        """Starts background capture and vision worker."""
        if self.running:
            return
        self.running = True
        self.worker_thread = threading.Thread(target=self._run_loop, daemon=True)
        self.worker_thread.start()
        logger.info("Vision pipeline thread started.")

    def stop(self):
        """Stops background capture thread and releases camera."""
        self.running = False
        if self.camera and self.camera.isOpened():
            try:
                self.camera.release()
            except Exception:
                pass
        if alarm_manager:
            alarm_manager.stop()
        logger.info("Vision pipeline stopped.")

    def _run_loop(self):
        """Main camera acquisition and computer-vision loop."""
        prev_time = time.time()

        while self.running:
            t = time.time()

            if not self.monitoring_active:
                time.sleep(0.05)
                continue

            frame = None
            if self.camera and self.camera.isOpened():
                success, captured = self.camera.read()
                if success and captured is not None and getattr(captured, "size", 0) > 0:
                    frame = cv2.flip(captured, 1)
                else:
                    logger.warning("Failed to read frame from webcam, retrying...")
                    time.sleep(0.02)

            if frame is None:
                # Use synthetic driver simulation frame
                frame = self._generate_synthetic_frame(t)
                face_landmarks = None
                processed_frame, eye_data = frame, {
                    "ear": self.latest_telemetry.get("ear", 0.28),
                    "mar": self.latest_telemetry.get("mar", 0.15),
                    "state": self.latest_telemetry.get("state", "SIMULATED"),
                    "closed_frames": self.latest_telemetry.get("closed_frames", 0),
                    "drowsy": self.latest_telemetry.get("drowsy", False),
                    "yawns": self.latest_telemetry.get("yawns", 0),
                    "eye_open_prob": self.latest_telemetry.get("eye_open_prob", 0.95),
                    "yawn_prob": self.latest_telemetry.get("yawn_prob", 0.05),
                    "eye_model_active": eye_model.loaded,
                    "yawn_model_active": yawn_model.loaded
                }
            else:
                # Real camera frame -> Run MediaPipe + Trained Models
                try:
                    raw_frame = frame.copy()
                    frame, face_landmarks = detector.detect(frame)
                    processed_frame, eye_data = eye_detector.process(frame, face_landmarks, raw_frame=raw_frame)
                except Exception as e:
                    logger.error(f"Error processing frame through vision pipeline: {e}")
                    processed_frame = frame
                    eye_data = self.latest_telemetry

            # Calculate FPS
            curr_time = time.time()
            fps = 1.0 / max(curr_time - prev_time, 0.001)
            prev_time = curr_time
            eye_data["fps"] = round(fps, 1)

            # Update Safety Coordinator
            try:
                coordinator.update(
                    eye_data=eye_data,
                    frame=processed_frame,
                    driver_id=default_driver_id,
                    vehicle_id=default_vehicle_id,
                    driver=driver_profile,
                    vehicle=vehicle_profile
                )
            except Exception as e:
                logger.error(f"Emergency coordinator error: {e}")

            # Rate-limited & state-change diagnostic logging (Requirement 8)
            now = time.time()
            current_state = eye_data.get("state")
            current_drowsy = eye_data.get("drowsy")
            current_alarm = alarm_manager.is_playing()
            state_changed = (
                current_state != getattr(self, "_last_diag_state", None) or
                current_drowsy != getattr(self, "_last_diag_drowsy", None) or
                current_alarm != getattr(self, "_last_diag_alarm", None)
            )
            time_elapsed = now - getattr(self, "_last_diag_log_time", 0.0)
            if state_changed or (time_elapsed >= 2.0 and face_landmarks is not None):
                self._last_diag_state = current_state
                self._last_diag_drowsy = current_drowsy
                self._last_diag_alarm = current_alarm
                self._last_diag_log_time = now
                logger.info(
                    f"[DIAGNOSTIC] EAR={eye_data.get('ear', 0.0):.3f} (thresh={eye_detector.EAR_THRESHOLD:.2f}) | "
                    f"EyeOpenProb={eye_data.get('eye_open_prob', 1.0):.3f} (thresh={eye_detector.EYE_MODEL_THRESHOLD:.2f}) | "
                    f"ClosedFrames={eye_data.get('closed_frames', 0)}/{eye_detector.CLOSED_FRAMES_THRESHOLD} | "
                    f"State={current_state} | Drowsy={current_drowsy} | "
                    f"AlarmPlaying={current_alarm} | Countdown={coordinator.countdown_active}"
                )

            # Draw HUD status badge on frame top-right
            h, w = processed_frame.shape[:2]
            hud_status = eye_data.get("state", "NORMAL")
            status_color = (0, 230, 100)
            if hud_status == "CLOSED" or eye_data.get("drowsy"):
                status_color = (0, 0, 255)
            elif coordinator.countdown_active:
                status_color = (0, 140, 255)

            # Draw top telemetry bar
            cv2.rectangle(processed_frame, (0, 0), (w, 36), (15, 20, 30), -1)
            cv2.putText(
                processed_frame,
                f"SAFEDRIVE AI  |  FPS: {fps:.0f}  |  STATUS: {hud_status}",
                (14, 24),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.46,
                status_color,
                1,
                cv2.LINE_AA
            )

            # Model health indicators
            m_text = f"EYE AI: {'ACTIVE' if eye_model.loaded else 'FALLBACK'} | YAWN AI: {'ACTIVE' if yawn_model.loaded else 'FALLBACK'}"
            cv2.putText(
                processed_frame,
                m_text,
                (w - 280, 24),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.36,
                (200, 220, 240),
                1,
                cv2.LINE_AA
            )

            # Encode frame to JPEG
            success, jpeg = cv2.imencode(
                ".jpg",
                processed_frame,
                [int(cv2.IMWRITE_JPEG_QUALITY), 80]
            )

            if success:
                with self.lock:
                    self.latest_jpeg = jpeg.tobytes()
                    self.latest_raw_frame = processed_frame
                    self.latest_telemetry = eye_data

            time.sleep(0.008)

    def reset(self):
        """Resets coordinator, eye detector counters, and alarm."""
        logger.info("Resetting session detection state.")
        coordinator.reset(eye_detector)
        if alarm_manager:
            alarm_manager.stop()

    def get_latest_jpeg(self) -> Optional[bytes]:
        with self.lock:
            return self.latest_jpeg

    def get_telemetry(self) -> Dict[str, Any]:
        with self.lock:
            return dict(self.latest_telemetry)


# Start singleton VisionPipeline
pipeline = VisionPipeline()
pipeline.start()


# -------------------------------------------------------------
# REST API Endpoints
# -------------------------------------------------------------

@app.route("/api/status", methods=["GET"])
def get_status():
    """
    Returns full system health, connection status, active models,
    real-time driver telemetry, alarm state, and session statistics.
    """
    telemetry = pipeline.get_telemetry()
    uptime = int(time.time() - pipeline.session_start_time)
    loc = coordinator.last_location

    return jsonify({
        "status": "ok",
        "app_name": APP_NAME,
        "app_version": APP_VERSION,
        "monitoring_active": pipeline.monitoring_active,
        "camera_connected": pipeline.camera_connected,
        "camera_error": pipeline.camera_error,
        "models": {
            "eye_model": {
                "name": "eye_drowsiness_model.keras",
                "loaded": eye_model.loaded,
                "input_shape": [64, 64, 3],
                "threshold": EYE_MODEL_THRESHOLD,
                "class_mapping": {"0": "Closed Eyes", "1": "Open Eyes"},
                "internal_rescaling": True
            },
            "yawn_model": {
                "name": "yawn_model.keras",
                "loaded": yawn_model.loaded,
                "input_shape": [128, 128, 3],
                "threshold": YAWN_MODEL_THRESHOLD,
                "class_mapping": {"0": "No Yawn", "1": "Yawn"},
                "backbone": "MobileNetV2"
            }
        },
        "telemetry": {
            "ear": round(telemetry.get("ear", 0.0), 3),
            "mar": round(telemetry.get("mar", 0.0), 3),
            "state": telemetry.get("state", "NORMAL"),
            "closed_frames": telemetry.get("closed_frames", 0),
            "drowsy": telemetry.get("drowsy", False),
            "yawns": telemetry.get("yawns", 0),
            "eye_open_prob": round(telemetry["eye_open_prob"], 3) if telemetry.get("eye_open_prob") is not None else None,
            "yawn_prob": round(telemetry["yawn_prob"], 3) if telemetry.get("yawn_prob") is not None else None,
            "fps": telemetry.get("fps", 0.0)
        },
        "alarm": {
            "is_playing": alarm_manager.is_playing(),
            "countdown_active": coordinator.countdown_active,
            "remaining_time": coordinator.remaining_time,
            "is_emergency": coordinator.is_emergency,
            "danger_detected": coordinator.danger_detected,
            "danger_reason": coordinator.danger_reason,
            "hazard_lights": coordinator.hazard_lights
        },
        "location": {
            "available": loc.is_available if loc else False,
            "latitude": loc.latitude if loc else None,
            "longitude": loc.longitude if loc else None,
            "accuracy": loc.accuracy if loc else None,
            "maps_url": loc.maps_url if loc else None,
            "status_text": loc.status_text if loc else "Standby"
        },
        "session": {
            "uptime_seconds": uptime,
            "total_yawns": telemetry.get("yawns", 0),
            "drowsy_logged": coordinator.drowsy_logged,
            "last_photo_path": coordinator.last_photo_path,
            "last_whatsapp_status": coordinator.last_whatsapp_status,
            "last_notification_status": coordinator.last_notification_status
        }
    })


def generate_frames():
    """Generator streaming JPEG frames with multipart boundary."""
    while True:
        frame_bytes = pipeline.get_latest_jpeg()
        if frame_bytes is None:
            # Short yield if first frame is not yet ready
            time.sleep(0.03)
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n"
            b"Content-Length: " + str(len(frame_bytes)).encode() + b"\r\n\r\n"
            + frame_bytes + b"\r\n"
        )
        time.sleep(0.033)  # ~30 FPS stream cap


@app.route("/api/video_feed", methods=["GET"])
def video_feed():
    """MJPEG stream endpoint consumed by standard <img> tags."""
    return Response(
        generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


@app.route("/api/session/start", methods=["POST"])
def start_session():
    """Starts / resumes driver monitoring."""
    pipeline.monitoring_active = True
    logger.info("Driver monitoring started via API.")
    return jsonify({"success": True, "message": "Monitoring active"})


@app.route("/api/session/stop", methods=["POST"])
def stop_session():
    """Pauses driver monitoring."""
    pipeline.monitoring_active = False
    pipeline.reset()
    logger.info("Driver monitoring paused via API.")
    return jsonify({"success": True, "message": "Monitoring paused"})


@app.route("/api/session/reset", methods=["POST"])
def reset_session():
    """Resets driver fatigue counters and silences alarms."""
    pipeline.reset()
    logger.info("Driver monitoring reset via API.")
    return jsonify({"success": True, "message": "Session reset successful"})


@app.route("/api/events", methods=["GET"])
def get_events():
    """Retrieves recent safety events from SQLite database."""
    limit = request.args.get("limit", default=20, type=int)
    events = get_recent_events(limit=limit)
    return jsonify({"success": True, "count": len(events), "events": events})


@app.route("/api/statistics", methods=["GET"])
def get_statistics():
    """Retrieves aggregated safety statistics."""
    stats = get_event_statistics()
    return jsonify({"success": True, "statistics": stats})


@app.route("/api/config", methods=["GET", "POST"])
def manage_config():
    """Gets or updates live detection thresholds."""
    global EAR_THRESHOLD, MAR_THRESHOLD, EYE_MODEL_THRESHOLD, YAWN_MODEL_THRESHOLD

    if request.method == "POST":
        data = request.get_json() or {}
        if "ear_threshold" in data:
            eye_detector.EAR_THRESHOLD = float(data["ear_threshold"])
        if "mar_threshold" in data:
            eye_detector.MAR_THRESHOLD = float(data["mar_threshold"])
        if "eye_model_threshold" in data:
            eye_detector.EYE_MODEL_THRESHOLD = float(data["eye_model_threshold"])
        if "yawn_model_threshold" in data:
            eye_detector.YAWN_MODEL_THRESHOLD = float(data["yawn_model_threshold"])
        if "closed_frames_threshold" in data:
            eye_detector.CLOSED_FRAMES_THRESHOLD = int(data["closed_frames_threshold"])

        logger.info(f"Updated live config: EAR={eye_detector.EAR_THRESHOLD}, MAR={eye_detector.MAR_THRESHOLD}, CLOSED_FRAMES={eye_detector.CLOSED_FRAMES_THRESHOLD}")
        return jsonify({"success": True, "message": "Configuration updated"})

    return jsonify({
        "ear_threshold": eye_detector.EAR_THRESHOLD,
        "mar_threshold": eye_detector.MAR_THRESHOLD,
        "eye_model_threshold": eye_detector.EYE_MODEL_THRESHOLD,
        "yawn_model_threshold": eye_detector.YAWN_MODEL_THRESHOLD,
        "closed_frames_threshold": eye_detector.CLOSED_FRAMES_THRESHOLD,
        "yawn_limit": YAWN_LIMIT,
        "response_timeout": RESPONSE_TIMEOUT_SECONDS,
        "ai_detection_mode": AI_DETECTION_MODE
    })


@app.route("/api/test/trigger", methods=["POST"])
def trigger_test_event():
    """
    Simulation endpoint for project demonstrations:
    Allows triggering Drowsiness, Yawn, SOS Emergency, or Reset
    instantly for presentation review.
    """
    data = request.get_json() or {}
    action = data.get("action", "").lower()

    if action == "drowsy":
        eye_detector.closed_frames = 50
        with pipeline.lock:
            pipeline.latest_telemetry["closed_frames"] = 50
            pipeline.latest_telemetry["drowsy"] = True
            pipeline.latest_telemetry["state"] = "CLOSED"
            pipeline.latest_telemetry["eye_open_prob"] = 0.05
        return jsonify({"success": True, "message": "Triggered simulated drowsiness event"})

    elif action == "yawn":
        eye_detector.yawn_count += 1
        with pipeline.lock:
            pipeline.latest_telemetry["yawns"] = eye_detector.yawn_count
            pipeline.latest_telemetry["state"] = "YAWNING"
            pipeline.latest_telemetry["yawn_prob"] = 0.92
        return jsonify({"success": True, "message": f"Triggered simulated yawn event (Count: {eye_detector.yawn_count})"})

    elif action == "emergency":
        coordinator.is_emergency = True
        coordinator.hazard_lights = True
        coordinator.danger_detected = True
        coordinator.danger_reason = "Manual Test Simulation"
        alarm_manager.play()
        return jsonify({"success": True, "message": "Triggered simulated emergency SOS"})

    elif action == "reset":
        pipeline.reset()
        return jsonify({"success": True, "message": "Reset simulation"})

    return jsonify({"success": False, "error": f"Unknown test action: {action}"}), 400


@app.route("/emergency_captures/<path:filename>", methods=["GET"])
def serve_capture(filename):
    """Serves captured emergency snapshot images."""
    return send_from_directory(str(CAPTURE_DIR), filename)


if __name__ == "__main__":
    logger.info(f"Starting SafeDrive AI Flask Server on http://127.0.0.1:5000 ...")
    try:
        app.run(host="0.0.0.0", port=5000, threaded=True, debug=False)
    finally:
        pipeline.stop()
