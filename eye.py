"""
SafeDrive-AI Eye & Yawn Detection Subsystem
Integrates Deep Learning Models with Geometric EAR & MAR Computer Vision Algorithms.
Provides hybrid sensor fusion, anti-false-alarm temporal logic, and real-time HUD overlays.
"""
import math
from typing import Dict, Any, Tuple, Optional, List

import cv2
import numpy as np

from config import (
    EAR_THRESHOLD,
    CLOSED_FRAMES_THRESHOLD,
    MAR_THRESHOLD,
    YAWN_MIN_FRAMES,
    YAWN_COOLDOWN_FRAMES,
    EYE_MODEL_THRESHOLD,
    YAWN_MODEL_THRESHOLD,
    AI_DETECTION_MODE
)
from model_loader import eye_model, yawn_model
from logger import logger


class EyeDetector:
    """
    Driver attentiveness processor combining facial landmark geometry (EAR, MAR)
    with trained deep learning neural networks for high-precision drowsiness
    and yawn classification.
    """

    LEFT_EYE = [33, 160, 158, 133, 153, 144]
    RIGHT_EYE = [362, 385, 387, 263, 373, 380]

    # Full eye boundary points for robust bounding box cropping
    LEFT_EYE_FULL = [33, 160, 158, 133, 153, 144, 163, 7, 246, 161]
    RIGHT_EYE_FULL = [362, 385, 387, 263, 373, 380, 390, 249, 466, 388]

    # Mouth landmark indices
    MOUTH_TOP = 13
    MOUTH_BOTTOM = 14
    MOUTH_LEFT = 61
    MOUTH_RIGHT = 291

    MOUTH_FULL = [
        61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291,
        185, 40, 39, 37, 0, 267, 269, 270, 409,
        78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308,
        191, 80, 81, 82, 13, 312, 311, 310, 415
    ]

    EAR_THRESHOLD = EAR_THRESHOLD
    CLOSED_FRAMES_THRESHOLD = CLOSED_FRAMES_THRESHOLD

    MAR_THRESHOLD = MAR_THRESHOLD
    YAWN_MIN_FRAMES = YAWN_MIN_FRAMES
    YAWN_COOLDOWN_FRAMES = YAWN_COOLDOWN_FRAMES

    EYE_MODEL_THRESHOLD = EYE_MODEL_THRESHOLD
    YAWN_MODEL_THRESHOLD = YAWN_MODEL_THRESHOLD

    def __init__(self):
        self.closed_frames = 0
        self.consecutive_open_frames = 0
        self.yawn_count = 0
        self.mouth_open_frames = 0
        self.yawn_active = False
        self.yawn_cooldown = 0

        # Telemetry cache
        self.last_eye_open_prob: float = 1.0
        self.last_yawn_prob: float = 0.0

    @staticmethod
    def distance(p1: Tuple[int, int], p2: Tuple[int, int]) -> float:
        """Euclidean distance between two 2D points."""
        return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)

    def get_points(self, face_landmarks, indices: List[int], width: int, height: int) -> List[Tuple[int, int]]:
        """Converts normalized landmark coordinates to integer pixel coordinates."""
        points = []
        for idx in indices:
            landmark = face_landmarks.landmark[idx]
            x = int(landmark.x * width)
            y = int(landmark.y * height)
            points.append((x, y))
        return points

    def calculate_ear(self, eye: List[Tuple[int, int]]) -> float:
        """
        Calculates Eye Aspect Ratio (EAR) based on 6 landmark coordinates:
        EAR = (|p2 - p6| + |p3 - p5|) / (2 * |p1 - p4|)
        """
        if len(eye) < 6:
            return 0.0

        A = self.distance(eye[1], eye[5])
        B = self.distance(eye[2], eye[4])
        C = self.distance(eye[0], eye[3])

        if C == 0:
            return 0.0

        return (A + B) / (2.0 * C)

    def calculate_mar(self, face_landmarks, width: int, height: int) -> float:
        """
        Calculates Mouth Aspect Ratio (MAR):
        MAR = |top - bottom| / |left - right|
        """
        try:
            top = face_landmarks.landmark[self.MOUTH_TOP]
            bottom = face_landmarks.landmark[self.MOUTH_BOTTOM]
            left = face_landmarks.landmark[self.MOUTH_LEFT]
            right = face_landmarks.landmark[self.MOUTH_RIGHT]

            top_point = (int(top.x * width), int(top.y * height))
            bottom_point = (int(bottom.x * width), int(bottom.y * height))
            left_point = (int(left.x * width), int(left.y * height))
            right_point = (int(right.x * width), int(right.y * height))

            vertical = self.distance(top_point, bottom_point)
            horizontal = self.distance(left_point, right_point)

            if horizontal == 0:
                return 0.0

            return vertical / horizontal
        except Exception:
            return 0.0

    @staticmethod
    def _extract_crop(frame: np.ndarray, points: List[Tuple[int, int]], pad_ratio: float = 0.35) -> Tuple[Optional[np.ndarray], Tuple[int, int, int, int]]:
        """
        Extracts a padded, roughly square region from the video frame enclosing given points.
        Returns (crop_image, (x1, y1, x2, y2)).
        """
        if not points or frame is None or getattr(frame, "size", 0) == 0:
            return None, (0, 0, 0, 0)

        h, w = frame.shape[:2]
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]

        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        box_w = max_x - min_x
        box_h = max_y - min_y

        half_side = int(max(box_w, box_h) * (0.5 + pad_ratio))
        cx = (min_x + max_x) // 2
        cy = (min_y + max_y) // 2

        x1 = max(0, cx - half_side)
        x2 = min(w, cx + half_side)
        y1 = max(0, cy - half_side)
        y2 = min(h, cy + half_side)

        if (x2 - x1) < 4 or (y2 - y1) < 4:
            return None, (0, 0, 0, 0)

        crop = frame[y1:y2, x1:x2].copy()
        return crop, (x1, y1, x2, y2)

    def process(self, frame: np.ndarray, face_landmarks, raw_frame: Optional[np.ndarray] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Processes a video frame with MediaPipe facial landmarks, runs deep learning
        inference on clean eye and mouth crops, and applies fusion logic.
        """
        if face_landmarks is None or frame is None:
            return frame, {
                "ear": 0.0,
                "state": "NO FACE",
                "closed_frames": self.closed_frames,
                "drowsy": False,
                "mar": 0.0,
                "yawns": self.yawn_count,
                "eye_open_prob": 1.0,
                "yawn_prob": 0.0,
                "eye_model_active": eye_model.loaded,
                "yawn_model_active": yawn_model.loaded
            }

        h, w, _ = frame.shape
        # Use clean, un-annotated source pixels for neural network crops
        clean_source = raw_frame if raw_frame is not None else frame.copy()

        # -------------------------------------------------------------
        # 1. Landmark Extraction
        # -------------------------------------------------------------
        left_eye_pts = self.get_points(face_landmarks, self.LEFT_EYE, w, h)
        right_eye_pts = self.get_points(face_landmarks, self.RIGHT_EYE, w, h)
        left_eye_full_pts = self.get_points(face_landmarks, self.LEFT_EYE_FULL, w, h)
        right_eye_full_pts = self.get_points(face_landmarks, self.RIGHT_EYE_FULL, w, h)
        mouth_pts = self.get_points(face_landmarks, self.MOUTH_FULL, w, h)

        # -------------------------------------------------------------
        # 2. Geometric EAR & MAR Computations
        # -------------------------------------------------------------
        left_ear = self.calculate_ear(left_eye_pts)
        right_ear = self.calculate_ear(right_eye_pts)
        ear = (left_ear + right_ear) / 2.0 if (left_ear > 0 and right_ear > 0) else max(left_ear, right_ear)
        mar = self.calculate_mar(face_landmarks, w, h)

        # -------------------------------------------------------------
        # 3. Deep Learning: Eye Drowsiness Model (from clean crops)
        # -------------------------------------------------------------
        eye_open_prob = None
        left_eye_prob = None
        right_eye_prob = None

        if eye_model.loaded:
            left_crop, l_box = self._extract_crop(clean_source, left_eye_full_pts, pad_ratio=0.30)
            right_crop, r_box = self._extract_crop(clean_source, right_eye_full_pts, pad_ratio=0.30)

            if left_crop is not None:
                left_eye_prob = eye_model.predict(left_crop)
            if right_crop is not None:
                right_eye_prob = eye_model.predict(right_crop)

            probs = [p for p in (left_eye_prob, right_eye_prob) if p is not None]
            if probs:
                eye_open_prob = float(np.mean(probs))
                self.last_eye_open_prob = eye_open_prob

                # Draw subtle HUD bounding indicators around eyes
                for (bx1, by1, bx2, by2), b_prob in [(l_box, left_eye_prob), (r_box, right_eye_prob)]:
                    if bx2 > bx1 and by2 > by1 and b_prob is not None:
                        is_cl = b_prob < self.EYE_MODEL_THRESHOLD
                        col = (0, 0, 255) if is_cl else (0, 230, 100)
                        cv2.rectangle(frame, (bx1, by1), (bx2, by2), col, 1, cv2.LINE_AA)

        # -------------------------------------------------------------
        # 4. Deep Learning: Yawn Detection Model (from clean crop)
        # -------------------------------------------------------------
        yawn_prob = None
        if yawn_model.loaded:
            mouth_crop, m_box = self._extract_crop(clean_source, mouth_pts, pad_ratio=0.35)
            if mouth_crop is not None:
                yawn_prob = yawn_model.predict(mouth_crop)
                if yawn_prob is not None:
                    self.last_yawn_prob = yawn_prob

                    # Draw subtle HUD bracket around mouth
                    mx1, my1, mx2, my2 = m_box
                    if mx2 > mx1 and my2 > my1:
                        is_yw = yawn_prob >= self.YAWN_MODEL_THRESHOLD
                        m_col = (0, 140, 255) if is_yw else (200, 100, 220)
                        cv2.rectangle(frame, (mx1, my1), (mx2, my2), m_col, 1, cv2.LINE_AA)
                        tag = f"YAWN AI {yawn_prob:.0%}" if is_yw else f"MOUTH {yawn_prob:.0%}"
                        cv2.putText(frame, tag, (mx1, max(my1 - 4, 12)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, m_col, 1, cv2.LINE_AA)

        # -------------------------------------------------------------
        # 5. Hybrid Sensor Fusion Logic (Eyes & Drowsiness)
        # -------------------------------------------------------------
        # Evaluate eye closure using consensus between EAR and Neural Network
        if eye_open_prob is not None and AI_DETECTION_MODE == "model":
            is_closed = eye_open_prob < self.EYE_MODEL_THRESHOLD
        elif eye_open_prob is not None and AI_DETECTION_MODE == "hybrid":
            # Hybrid consensus:
            # - Neural model detects closed eyes without severe contradictory EAR (ear < 0.35)
            # - OR geometric EAR detects closed eyes without severe contradictory model (eye_open_prob < 0.80)
            # - OR both agree (model < threshold and EAR < threshold)
            # - OR weighted consensus indicates closure
            ai_closed_score = 1.0 - eye_open_prob
            ear_closed_score = max(0.0, min(1.0, (self.EAR_THRESHOLD - ear) / max(0.01, self.EAR_THRESHOLD * 0.5) + 0.5))
            weighted_closure = 0.60 * ai_closed_score + 0.40 * ear_closed_score

            is_closed = (
                (eye_open_prob < self.EYE_MODEL_THRESHOLD and ear < 0.35)
                or (ear < self.EAR_THRESHOLD and eye_open_prob < 0.80)
                or (eye_open_prob < self.EYE_MODEL_THRESHOLD and ear < self.EAR_THRESHOLD)
                or (weighted_closure >= 0.50)
            )
        else:
            # Geometric EAR fallback
            is_closed = ear < self.EAR_THRESHOLD

        # Temporal logic with single-frame jitter tolerance
        if is_closed:
            state = "CLOSED"
            self.closed_frames += 1
            self.consecutive_open_frames = 0
        else:
            state = "OPEN"
            self.consecutive_open_frames += 1
            if self.consecutive_open_frames >= 2:
                self.closed_frames = 0
            else:
                self.closed_frames = max(0, self.closed_frames - 1)

        drowsy = self.closed_frames >= self.CLOSED_FRAMES_THRESHOLD

        # -------------------------------------------------------------
        # 6. Hybrid Sensor Fusion Logic (Yawn Progression)
        # -------------------------------------------------------------
        if self.yawn_cooldown > 0:
            self.yawn_cooldown -= 1

        # Determine frame-level yawn candidate
        if yawn_prob is not None and AI_DETECTION_MODE == "model":
            yawn_candidate = yawn_prob >= self.YAWN_MODEL_THRESHOLD
        elif yawn_prob is not None and AI_DETECTION_MODE == "hybrid":
            yawn_candidate = (
                (yawn_prob >= self.YAWN_MODEL_THRESHOLD and mar >= 0.30)
                or (mar >= self.MAR_THRESHOLD and yawn_prob >= 0.20)
            )
        else:
            # Geometric MAR fallback
            yawn_candidate = mar >= self.MAR_THRESHOLD

        # Temporal filter: require sustained consecutive frames before registering yawn
        if yawn_candidate:
            self.mouth_open_frames += 1
            if (
                self.mouth_open_frames >= self.YAWN_MIN_FRAMES
                and not self.yawn_active
                and self.yawn_cooldown == 0
            ):
                self.yawn_active = True
        else:
            # Mouth closed after an active sustained yawn -> register single yawn event
            if self.yawn_active:
                self.yawn_count += 1
                self.yawn_active = False
                self.yawn_cooldown = self.YAWN_COOLDOWN_FRAMES
            self.mouth_open_frames = 0

        # Draw landmark points on video for HUD display (after clean crops are processed)
        for p in left_eye_pts:
            cv2.circle(frame, p, 2, (0, 255, 0), -1, cv2.LINE_AA)
        for p in right_eye_pts:
            cv2.circle(frame, p, 2, (255, 120, 0), -1, cv2.LINE_AA)

        # Draw HUD eye status on frame
        eye_tag = f"EYES: {state}"
        if eye_open_prob is not None:
            eye_tag += f" (AI: {eye_open_prob:.0%})"
        tag_col = (0, 0, 255) if is_closed else (0, 255, 0)
        cv2.putText(frame, eye_tag, (16, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.50, tag_col, 1, cv2.LINE_AA)

        return frame, {
            "ear": ear,
            "mar": mar,
            "state": state,
            "closed_frames": self.closed_frames,
            "drowsy": drowsy,
            "yawns": self.yawn_count,
            "eye_open_prob": eye_open_prob if eye_open_prob is not None else self.last_eye_open_prob,
            "yawn_prob": yawn_prob if yawn_prob is not None else self.last_yawn_prob,
            "eye_model_active": eye_model.loaded,
            "yawn_model_active": yawn_model.loaded,
            "yawn_active": self.yawn_active
        }

    def reset_detection(self):
        """Resets all consecutive frame counters and yawn tallies."""
        self.closed_frames = 0
        self.consecutive_open_frames = 0
        self.yawn_count = 0
        self.mouth_open_frames = 0
        self.yawn_active = False
        self.yawn_cooldown = 0