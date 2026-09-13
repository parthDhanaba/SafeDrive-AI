import cv2
import math


class EyeDetector:

    LEFT_EYE = [33, 160, 158, 133, 153, 144]
    RIGHT_EYE = [362, 385, 387, 263, 373, 380]

    MOUTH_TOP = 13
    MOUTH_BOTTOM = 14
    MOUTH_LEFT = 61
    MOUTH_RIGHT = 291

    EAR_THRESHOLD = 0.22
    CLOSED_FRAMES_THRESHOLD = 45

    MAR_THRESHOLD = 0.50
    YAWN_MIN_FRAMES = 8

    def __init__(self):
        self.closed_frames = 0
        self.yawn_count = 0
        self.mouth_open_frames = 0
        self.yawn_active = False
        self.yawn_cooldown = 0

    def distance(self, p1, p2):
        return math.sqrt(
            (p1[0] - p2[0]) ** 2 +
            (p1[1] - p2[1]) ** 2
        )

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

    def calculate_mar(self, face_landmarks, width, height):
        top = face_landmarks.landmark[self.MOUTH_TOP]
        bottom = face_landmarks.landmark[self.MOUTH_BOTTOM]
        left = face_landmarks.landmark[self.MOUTH_LEFT]
        right = face_landmarks.landmark[self.MOUTH_RIGHT]

        top_point = (
            int(top.x * width),
            int(top.y * height)
        )

        bottom_point = (
            int(bottom.x * width),
            int(bottom.y * height)
        )

        left_point = (
            int(left.x * width),
            int(left.y * height)
        )

        right_point = (
            int(right.x * width),
            int(right.y * height)
        )

        vertical = self.distance(top_point, bottom_point)
        horizontal = self.distance(left_point, right_point)

        if horizontal == 0:
            return 0.0

        return vertical / horizontal

    def process(self, frame, face_landmarks):
        if face_landmarks is None:
            return frame, {
                "ear": 0,
                "state": "NO FACE",
                "closed_frames": self.closed_frames,
                "drowsy": False,
                "mar": 0,
                "yawns": self.yawn_count
            }

        h, w, _ = frame.shape

        left_eye = self.get_points(
            face_landmarks,
            self.LEFT_EYE,
            w,
            h
        )

        right_eye = self.get_points(
            face_landmarks,
            self.RIGHT_EYE,
            w,
            h
        )

        for p in left_eye:
            cv2.circle(frame, p, 4, (0, 0, 255), -1)

        for p in right_eye:
            cv2.circle(frame, p, 4, (255, 0, 0), -1)

        left_ear = self.calculate_ear(left_eye)
        right_ear = self.calculate_ear(right_eye)

        ear = (left_ear + right_ear) / 2

        if ear < self.EAR_THRESHOLD:
            state = "CLOSED"
            self.closed_frames += 1
        else:
            state = "OPEN"
            self.closed_frames = 0

        drowsy = self.closed_frames >= self.CLOSED_FRAMES_THRESHOLD

        mar = self.calculate_mar(
            face_landmarks,
            w,
            h
        )

        if self.yawn_cooldown > 0:
            self.yawn_cooldown -= 1

        if mar >= self.MAR_THRESHOLD:
            self.mouth_open_frames += 1

            if (
                self.mouth_open_frames >= self.YAWN_MIN_FRAMES
                and not self.yawn_active
                and self.yawn_cooldown == 0
            ):
                self.yawn_active = True

        else:
            if self.yawn_active:
                self.yawn_count += 1
                self.yawn_active = False
                self.yawn_cooldown = 15

            self.mouth_open_frames = 0

        return frame, {
            "ear": ear,
            "state": state,
            "closed_frames": self.closed_frames,
            "drowsy": drowsy,
            "mar": mar,
            "yawns": self.yawn_count
        }

    def reset_detection(self):
        self.closed_frames = 0
        self.yawn_count = 0
        self.mouth_open_frames = 0
        self.yawn_active = False
        self.yawn_cooldown = 0