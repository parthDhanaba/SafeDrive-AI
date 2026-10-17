"""
SafeDrive-AI Facial Detection and Landmark Tracking Subsystem
Supports both modern MediaPipe Tasks FaceLandmarker and legacy mp.solutions.face_mesh.
Draws sleek automotive HUD brackets and facial landmark overlays.
"""
from pathlib import Path
from typing import Optional, Tuple, Any, List
import cv2
import numpy as np

# Landmark index constants
LEFT_EYE_INDICES = [33, 160, 158, 133, 153, 144, 163, 7, 246, 161]
RIGHT_EYE_INDICES = [362, 385, 387, 263, 373, 380, 390, 249, 466, 388]

# Mouth lip connections (start, end)
DEFAULT_LIPS_CONNECTIONS = [
    (61, 146), (146, 91), (91, 181), (181, 84), (84, 17), (17, 314),
    (314, 405), (405, 321), (321, 375), (375, 291), (61, 185), (185, 40),
    (40, 39), (39, 37), (37, 0), (0, 267), (267, 269), (269, 270),
    (270, 409), (409, 291), (78, 95), (95, 88), (88, 178), (178, 87),
    (87, 14), (14, 317), (317, 402), (402, 318), (318, 324), (324, 308),
    (78, 191), (191, 80), (80, 81), (81, 82), (82, 13), (13, 312),
    (312, 311), (311, 310), (310, 415), (415, 308)
]


class _NormalizedLandmark:
    __slots__ = ("x", "y", "z")

    def __init__(self, x: float, y: float, z: float = 0.0):
        self.x = x
        self.y = y
        self.z = z


class _FaceLandmarksWrapper:
    __slots__ = ("landmark",)

    def __init__(self, landmarks_list: List[_NormalizedLandmark]):
        self.landmark = landmarks_list


class FaceDetector:
    LEFT_EYE = LEFT_EYE_INDICES
    RIGHT_EYE = RIGHT_EYE_INDICES

    def __init__(self):
        self.backend = None
        self.face_mesh = None
        self.landmarker = None
        self.lips_connections = DEFAULT_LIPS_CONNECTIONS

        # 1. Try legacy mediapipe solutions API (Python <= 3.12)
        try:
            import mediapipe as mp
            if hasattr(mp, "solutions") and hasattr(mp.solutions, "face_mesh"):
                self.mp_face_mesh = mp.solutions.face_mesh
                self.face_mesh = self.mp_face_mesh.FaceMesh(
                    static_image_mode=False,
                    max_num_faces=1,
                    refine_landmarks=True,
                    min_detection_confidence=0.5,
                    min_tracking_confidence=0.5
                )
                self.backend = "solutions"
                # Use solutions lip connections
                if hasattr(self.mp_face_mesh, "FACEMESH_LIPS"):
                    self.lips_connections = [(c[0], c[1]) for c in self.mp_face_mesh.FACEMESH_LIPS]
        except Exception:
            pass

        # 2. Try modern MediaPipe Tasks FaceLandmarker (Python 3.13+)
        if not self.backend:
            try:
                import mediapipe as mp
                from mediapipe.tasks.python import vision, BaseOptions

                model_path = Path(__file__).resolve().parent / "models" / "face_landmarker.task"
                if not model_path.exists():
                    import urllib.request
                    model_path.parent.mkdir(parents=True, exist_ok=True)
                    url = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task"
                    urllib.request.urlretrieve(url, str(model_path))

                options = vision.FaceLandmarkerOptions(
                    base_options=BaseOptions(model_asset_path=str(model_path)),
                    running_mode=vision.RunningMode.IMAGE,
                    num_faces=1,
                    min_face_detection_confidence=0.5,
                    min_face_presence_confidence=0.5,
                    min_tracking_confidence=0.5,
                    output_face_blendshapes=False
                )
                self.landmarker = vision.FaceLandmarker.create_from_options(options)
                self.backend = "tasks"

                if hasattr(vision, "FaceLandmarksConnections") and hasattr(vision.FaceLandmarksConnections, "FACE_LANDMARKS_LIPS"):
                    self.lips_connections = [(c.start, c.end) for c in vision.FaceLandmarksConnections.FACE_LANDMARKS_LIPS]
            except Exception as e:
                pass

    def detect(self, frame: np.ndarray) -> Tuple[np.ndarray, Optional[Any]]:
        if frame is None or getattr(frame, "size", 0) == 0:
            return frame, None

        height, width, _ = frame.shape
        raw_landmarks = None

        if self.backend == "solutions" and self.face_mesh:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.face_mesh.process(rgb)
            if results and results.multi_face_landmarks:
                raw_landmarks = results.multi_face_landmarks[0].landmark

        elif self.backend == "tasks" and self.landmarker:
            import mediapipe as mp
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = self.landmarker.detect(mp_image)
            if result and result.face_landmarks and len(result.face_landmarks) > 0:
                raw_landmarks = result.face_landmarks[0]

        if not raw_landmarks:
            # Subtle HUD scanning reticle when searching for driver
            box_w, box_h = int(width * 0.4), int(height * 0.5)
            bx1, by1 = (width - box_w) // 2, (height - box_h) // 2
            bx2, by2 = bx1 + box_w, by1 + box_h
            hud_dim = (80, 100, 120)
            cv2.rectangle(frame, (bx1, by1), (bx2, by2), hud_dim, 1, cv2.LINE_AA)
            cv2.putText(
                frame,
                "CABIN SCAN: SEARCHING DRIVER",
                (bx1 + 10, by1 + 24),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.42,
                hud_dim,
                1,
                cv2.LINE_AA
            )
            return frame, None

        # Build normalized wrapper list
        landmarks_list = [
            _NormalizedLandmark(lm.x, lm.y, getattr(lm, "z", 0.0))
            for lm in raw_landmarks
        ]
        face_landmarks = _FaceLandmarksWrapper(landmarks_list)

        # Compute bounding rectangle for realistic HUD face lock brackets
        xs = [int(lm.x * width) for lm in landmarks_list]
        ys = [int(lm.y * height) for lm in landmarks_list]
        fx1, fx2 = max(0, min(xs) - 12), min(width - 1, max(xs) + 12)
        fy1, fy2 = max(0, min(ys) - 16), min(height - 1, max(ys) + 12)

        # Draw sleek automotive HUD corner brackets around driver's face
        bracket_len = min(22, (fx2 - fx1) // 5)
        hud_color = (0, 230, 200)  # Luminous Cyan / Emerald
        thickness = 2

        # Top-Left
        cv2.line(frame, (fx1, fy1), (fx1 + bracket_len, fy1), hud_color, thickness, cv2.LINE_AA)
        cv2.line(frame, (fx1, fy1), (fx1, fy1 + bracket_len), hud_color, thickness, cv2.LINE_AA)
        # Top-Right
        cv2.line(frame, (fx2, fy1), (fx2 - bracket_len, fy1), hud_color, thickness, cv2.LINE_AA)
        cv2.line(frame, (fx2, fy1), (fx2, fy1 + bracket_len), hud_color, thickness, cv2.LINE_AA)
        # Bottom-Left
        cv2.line(frame, (fx1, fy2), (fx1 + bracket_len, fy2), hud_color, thickness, cv2.LINE_AA)
        cv2.line(frame, (fx1, fy2), (fx1, fy2 - bracket_len), hud_color, thickness, cv2.LINE_AA)
        # Bottom-Right
        cv2.line(frame, (fx2, fy2), (fx2 - bracket_len, fy2), hud_color, thickness, cv2.LINE_AA)
        cv2.line(frame, (fx2, fy2), (fx2, fy2 - bracket_len), hud_color, thickness, cv2.LINE_AA)

        # HUD tag
        cv2.putText(
            frame,
            "TARGET: DRIVER LOCKED",
            (fx1, max(fy1 - 6, 16)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.40,
            hud_color,
            1,
            cv2.LINE_AA
        )

        num_points = len(landmarks_list)

        # Left eye landmarks
        for idx in self.LEFT_EYE:
            if idx < num_points:
                lm = landmarks_list[idx]
                cv2.circle(frame, (int(lm.x * width), int(lm.y * height)), 2, (0, 255, 0), -1, cv2.LINE_AA)

        # Right eye landmarks
        for idx in self.RIGHT_EYE:
            if idx < num_points:
                lm = landmarks_list[idx]
                cv2.circle(frame, (int(lm.x * width), int(lm.y * height)), 2, (0, 255, 0), -1, cv2.LINE_AA)

        # Mouth lip connections
        mouth_pts = set()
        for start_idx, end_idx in self.lips_connections:
            if start_idx < num_points and end_idx < num_points:
                mouth_pts.add(start_idx)
                mouth_pts.add(end_idx)
                p1 = (int(landmarks_list[start_idx].x * width), int(landmarks_list[start_idx].y * height))
                p2 = (int(landmarks_list[end_idx].x * width), int(landmarks_list[end_idx].y * height))
                cv2.line(frame, p1, p2, (255, 0, 255), 1, cv2.LINE_AA)

        for idx in mouth_pts:
            if idx < num_points:
                lm = landmarks_list[idx]
                cv2.circle(frame, (int(lm.x * width), int(lm.y * height)), 2, (255, 0, 255), -1, cv2.LINE_AA)

        return frame, face_landmarks