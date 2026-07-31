import cv2
import math


class EyeDetector:

    LEFT_EYE = [33, 160, 158, 133, 153, 144]
    RIGHT_EYE = [362, 385, 387, 263, 373, 380]

    EAR_THRESHOLD = 0.22
    CLOSED_FRAMES_THRESHOLD = 45

    def __init__(self):
        self.closed_frames = 0

    def distance(self, p1, p2):
        return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)

    def get_points(self, face_landmarks, indices, width, height):

        points = []

        for idx in indices:

            landmark = face_landmarks.landmark[idx]

            x = int(landmark.x * width)
            y = int(landmark.y * height)

            points.append((x, y))

        return points

    def calculate_ear(self, eye):

        A = self.distance(eye[1], eye[5])
        B = self.distance(eye[2], eye[4])
        C = self.distance(eye[0], eye[3])

        if C == 0:
            return 0.0

        return (A + B) / (2 * C)

    def process(self, frame, face_landmarks):

        if face_landmarks is None:

            return frame, {
                "ear": 0,
                "state": "NO FACE",
                "closed_frames": self.closed_frames,
                "drowsy": False
            }

        h, w, _ = frame.shape

        left_eye = self.get_points(face_landmarks, self.LEFT_EYE, w, h)
        right_eye = self.get_points(face_landmarks, self.RIGHT_EYE, w, h)

        for p in left_eye:
            cv2.circle(frame, p, 4, (0, 0, 255), -1)

        for p in right_eye:
            cv2.circle(frame, p, 4, (255, 0, 0), -1)

        left_ear = self.calculate_ear(left_eye)
        right_ear = self.calculate_ear(right_eye)

        ear = (left_ear + right_ear) / 2

        state = "OPEN"

        if ear < self.EAR_THRESHOLD:

            state = "CLOSED"
            self.closed_frames += 1

        else:

            state = "OPEN"
            self.closed_frames = 0

        drowsy = self.closed_frames >= self.CLOSED_FRAMES_THRESHOLD

        return frame, {
            "ear": ear,
            "state": state,
            "closed_frames": self.closed_frames,
            "drowsy": drowsy
        }