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

        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

    def detect(self, frame):

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        results = self.face_mesh.process(rgb)

        if not results.multi_face_landmarks:
            return frame, None

        height, width, _ = frame.shape

        face_landmarks = results.multi_face_landmarks[0]

        for idx in self.LEFT_EYE:

            landmark = face_landmarks.landmark[idx]

            x = int(landmark.x * width)
            y = int(landmark.y * height)

            cv2.circle(frame, (x, y), 2, (0, 255, 0), -1)

        for idx in self.RIGHT_EYE:

            landmark = face_landmarks.landmark[idx]

            x = int(landmark.x * width)
            y = int(landmark.y * height)

            cv2.circle(frame, (x, y), 2, (0, 255, 0), -1)

        return frame, face_landmarks