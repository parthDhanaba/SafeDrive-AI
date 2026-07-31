import cv2
import time

from detector import FaceDetector
from eye import EyeDetector
from alarm import AlarmManager


WINDOW_NAME = "SafeDrive AI"


def initialize_camera(camera_index: int = 0):

    camera = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)

    if not camera.isOpened():
        raise RuntimeError("Unable to access webcam.")

    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    return camera


def create_window():

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, 1280, 720)


def main():

    detector = FaceDetector()
    eye_detector = EyeDetector()
    alarm = AlarmManager()

    camera = initialize_camera()

    create_window()

    previous_time = time.time()

    while True:

        success, frame = camera.read()

        if not success:
            break

        frame = cv2.flip(frame, 1)

        # Face Detection
        frame, face_landmarks = detector.detect(frame)

        # Eye Detection
        frame, eye_data = eye_detector.process(frame, face_landmarks)

        # FPS
        current_time = time.time()
        fps = 1 / (current_time - previous_time)
        previous_time = current_time

        cv2.putText(
            frame,
            f"FPS : {int(fps)}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2
        )

        cv2.putText(
            frame,
            f"EAR : {eye_data['ear']:.2f}",
            (20, 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 255),
            2
        )

        cv2.putText(
            frame,
            f"Eyes : {eye_data['state']}",
            (20, 120),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 255),
            2
        )

        cv2.putText(
            frame,
            f"Closed Frames : {eye_data['closed_frames']}",
            (20, 160),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 0),
            2
        )

        # Drowsiness Detection
        if eye_data["drowsy"]:

            alarm.play()

            cv2.putText(
                frame,
                "DROWSINESS DETECTED",
                (250, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 0, 255),
                3
            )

        else:

            alarm.stop()

        cv2.imshow(WINDOW_NAME, frame)

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break

    alarm.stop()
    camera.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()