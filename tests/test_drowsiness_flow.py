"""
SafeDrive-AI End-to-End Drowsiness & Recovery Flow Test
Verifies:
1. Clean frame processing with real driver images.
2. Eye model closure inference and EAR consensus.
3. Accumulation of closed frames to trigger drowsiness.
4. Alarm manager activation & warning countdown initiation.
5. Reopening eyes cleanly stops alarm and resets system to nominal status.
"""
import unittest
import cv2
import numpy as np

from detector import FaceDetector
from eye import EyeDetector
from alarm import AlarmManager
from emergency import EmergencyCoordinator


class TestDrowsinessAlarmFlow(unittest.TestCase):
    def setUp(self):
        self.detector = FaceDetector()
        self.eye_detector = EyeDetector()
        self.alarm = AlarmManager()
        self.coord = EmergencyCoordinator(self.alarm)

        self.driver = {"name": "Test Driver", "emergency_contact_phone": "+15551112222"}
        self.vehicle = {"vehicle_number": "TEST-01"}

        # Real driver captures
        self.img_closed = cv2.imread("emergency_captures/emergency_20261017_212551.jpg")
        self.img_open = cv2.imread("emergency_captures/emergency_20261026_184952.jpg")

    def tearDown(self):
        self.alarm.stop()

    def test_end_to_end_closed_eyes_triggers_alarm_and_reopening_resets(self):
        """Simulate driver closing eyes for threshold duration then reopening."""
        self.assertIsNotNone(self.img_closed, "Closed eyes test image must exist")
        self.assertIsNotNone(self.img_open, "Open eyes test image must exist")

        # 1. Verify single closed frame is recognized as CLOSED
        raw_closed = self.img_closed.copy()
        f_closed, lm_closed = self.detector.detect(self.img_closed.copy())
        self.assertIsNotNone(lm_closed, "Face landmarks must be detected in closed eye frame")

        f_proc, data_single = self.eye_detector.process(f_closed, lm_closed, raw_frame=raw_closed)
        self.assertEqual(data_single["state"], "CLOSED", f"Expected CLOSED, got {data_single}")
        self.assertLess(data_single["eye_open_prob"], self.eye_detector.EYE_MODEL_THRESHOLD)

        # 2. Reset and simulate sustained eye closure for CLOSED_FRAMES_THRESHOLD
        self.eye_detector.reset_detection()
        self.coord.reset(self.eye_detector)
        threshold = self.eye_detector.CLOSED_FRAMES_THRESHOLD

        alarm_triggered = False
        countdown_started = False

        for frame_idx in range(1, threshold + 5):
            raw_c = self.img_closed.copy()
            f_c, lm_c = self.detector.detect(self.img_closed.copy())
            proc_f, eye_data = self.eye_detector.process(f_c, lm_c, raw_frame=raw_c)

            self.coord.update(
                eye_data=eye_data,
                frame=proc_f,
                driver_id=1,
                vehicle_id=1,
                driver=self.driver,
                vehicle=self.vehicle
            )

            if frame_idx < threshold:
                self.assertFalse(eye_data["drowsy"], f"Frame {frame_idx} should not trigger drowsy yet")
            else:
                self.assertTrue(eye_data["drowsy"], f"Frame {frame_idx} should be marked drowsy")
                if self.coord.countdown_active and self.alarm.is_playing():
                    alarm_triggered = True
                    countdown_started = True

        self.assertTrue(alarm_triggered, "Alarm must be playing after sustained eye closure")
        self.assertTrue(countdown_started, "10-second response countdown must be active")
        self.assertTrue(self.coord.danger_detected, "Danger flag must be set")
        self.assertIn("Drowsiness", self.coord.danger_reason)

        # 3. Simulate driver waking up and reopening eyes
        raw_open = self.img_open.copy()
        f_open, lm_open = self.detector.detect(self.img_open.copy())
        self.assertIsNotNone(lm_open, "Face landmarks must be detected in open eye frame")

        # Process 3 open frames to ensure debounce resets closed frames
        for _ in range(3):
            proc_open, open_data = self.eye_detector.process(f_open, lm_open, raw_frame=raw_open)
            self.coord.update(
                eye_data=open_data,
                frame=proc_open,
                driver_id=1,
                vehicle_id=1,
                driver=self.driver,
                vehicle=self.vehicle
            )

        # 4. Verify system restored to nominal state
        self.assertEqual(open_data["state"], "OPEN")
        self.assertFalse(open_data["drowsy"])
        self.assertEqual(self.eye_detector.closed_frames, 0)
        self.assertFalse(self.coord.countdown_active, "Countdown should stop when eyes reopen")
        self.assertFalse(self.coord.danger_detected, "Danger state should clear when eyes reopen")
        self.assertFalse(self.alarm.is_playing(), "Alarm should stop when eyes reopen")


if __name__ == "__main__":
    unittest.main()
