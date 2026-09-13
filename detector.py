import cv2
import mediapipe as mp


class FaceDetector:

    LEFT_EYE = [
        33, 160, 158, 133, 153, 144,
        163, 7, 246, 161
    ]

    RIGHT_EYE = [
        362, 385, 387, 263, 373, 380,
        390, 249, 466, 388
    ]

    def __init__(self):

        self.mp_face_mesh = mp.solutions.face_mesh
        self.mp_drawing = mp.solutions.drawing_utils

        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

    def detect(self, frame):
        if frame is None or getattr(frame, "size", 0) == 0:
            return frame, None

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb)

        height, width, _ = frame.shape

        if not results.multi_face_landmarks:
            # Subtle HUD scanning reticle when searching for driver
            box_w, box_h = int(width * 0.4), int(height * 0.5)
            bx1, by1 = (width - box_w) // 2, (height - box_h) // 2
            bx2, by2 = bx1 + box_w, by1 + box_h
            hud_dim = (80, 100, 120)
            cv2.rectangle(frame, (bx1, by1), (bx2, by2), hud_dim, 1, cv2.LINE_AA)
            cv2.putText(frame, "CABIN SCAN: SEARCHING DRIVER", (bx1 + 10, by1 + 24),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, hud_dim, 1, cv2.LINE_AA)
            return frame, None

        face_landmarks = results.multi_face_landmarks[0]

        # Compute bounding rectangle for realistic HUD face lock brackets
        xs = [int(lm.x * width) for lm in face_landmarks.landmark]
        ys = [int(lm.y * height) for lm in face_landmarks.landmark]
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

        # Subtle HUD tag
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

        # Left eye landmarks
        for idx in self.LEFT_EYE:
            landmark = face_landmarks.landmark[idx]
            x = int(landmark.x * width)
            y = int(landmark.y * height)
            cv2.circle(frame, (x, y), 2, (0, 255, 0), -1, cv2.LINE_AA)

        # Right eye landmarks
        for idx in self.RIGHT_EYE:
            landmark = face_landmarks.landmark[idx]
            x = int(landmark.x * width)
            y = int(landmark.y * height)
            cv2.circle(frame, (x, y), 2, (0, 255, 0), -1, cv2.LINE_AA)

        # Mouth-only mesh connections
        mouth_connections = self.mp_face_mesh.FACEMESH_LIPS
        mouth_points = set()

        for connection in mouth_connections:
            mouth_points.add(connection[0])
            mouth_points.add(connection[1])

            p1 = face_landmarks.landmark[connection[0]]
            p2 = face_landmarks.landmark[connection[1]]

            x1 = int(p1.x * width)
            y1 = int(p1.y * height)
            x2 = int(p2.x * width)
            y2 = int(p2.y * height)

            cv2.line(frame, (x1, y1), (x2, y2), (255, 0, 255), 1, cv2.LINE_AA)

        # Mouth landmark points
        for idx in mouth_points:
            landmark = face_landmarks.landmark[idx]
            x = int(landmark.x * width)
            y = int(landmark.y * height)
            cv2.circle(frame, (x, y), 2, (255, 0, 255), -1, cv2.LINE_AA)

        return frame, face_landmarks