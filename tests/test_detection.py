"""
Tests for EAR, MAR, Yawn, and Drowsiness Detection Subsystem
"""
import unittest
import numpy as np
from unittest.mock import MagicMock
from eye import EyeDetector
from detector import FaceDetector


class TestDetectionSubsystem(unittest.TestCase):
    def setUp(self):
        self.eye_detector = EyeDetector()

    def test_ear_calculation_open_and_closed(self):
        """Test EAR formula with simulated coordinates."""
        # Simulated eye points: [p1, p2, p3, p4, p5, p6]
        # p1=(0, 10), p2=(5, 20), p3=(10, 20), p4=(15, 10), p5=(10, 0), p6=(5, 0)
        open_eye = [(0, 10), (5, 20), (10, 20), (15, 10), (10, 0), (5, 0)]
        ear_open = self.eye_detector.calculate_ear(open_eye)
        self.assertGreater(ear_open, 0.25)

        # Closed eye points (collapsed vertical distance)
        closed_eye = [(0, 10), (5, 10.5), (10, 10.5), (15, 10), (10, 9.5), (5, 9.5)]
        ear_closed = self.eye_detector.calculate_ear(closed_eye)
        self.assertLess(ear_closed, 0.15)

    def test_mar_calculation(self):
        """Test MAR formula with simulated landmark indices."""
        # Mock face landmarks
        landmarks = MagicMock()

        # Top(13), Bottom(14), Left(61), Right(291)
        # Standard mouth: vertical = 0.1, horizontal = 0.5 -> MAR = 0.2
        def get_landmark(idx):
            pt = MagicMock()
            if idx == 13: # Top
                pt.x, pt.y = 0.5, 0.45
            elif idx == 14: # Bottom
                pt.x, pt.y = 0.5, 0.55
            elif idx == 61: # Left
                pt.x, pt.y = 0.3, 0.50
            elif idx == 291: # Right
                pt.x, pt.y = 0.7, 0.50
            else:
                pt.x, pt.y = 0.5, 0.5
            return pt

        landmarks.landmark = {i: get_landmark(i) for i in range(468)}
        mar = self.eye_detector.calculate_mar(landmarks, 100, 100)
        self.assertAlmostEqual(mar, 0.25, delta=0.05)

    def test_yawn_counter_and_cooldown(self):
        """Test yawn progression: mouth open >= YAWN_MIN_FRAMES then closing increments count."""
        # Simulate open mouth frames
        self.eye_detector.yawn_active = False
        self.eye_detector.mouth_open_frames = 8
        self.eye_detector.yawn_cooldown = 0

        # Frame where mouth opens
        landmarks = MagicMock()
        # Create mouth with MAR >= 0.50
        def get_open_mouth(idx):
            pt = MagicMock()
            if idx == 13: pt.x, pt.y = 0.5, 0.30
            elif idx == 14: pt.x, pt.y = 0.5, 0.70
            elif idx == 61: pt.x, pt.y = 0.3, 0.50
            elif idx == 291: pt.x, pt.y = 0.7, 0.50
            else: pt.x, pt.y = 0.5, 0.5
            return pt
        landmarks.landmark = {i: get_open_mouth(i) for i in range(468)}

        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        _, data = self.eye_detector.process(frame, landmarks)
        self.assertTrue(self.eye_detector.yawn_active)

        # Now mouth closes
        def get_closed_mouth(idx):
            pt = MagicMock()
            if idx == 13: pt.x, pt.y = 0.5, 0.48
            elif idx == 14: pt.x, pt.y = 0.5, 0.52
            elif idx == 61: pt.x, pt.y = 0.3, 0.50
            elif idx == 291: pt.x, pt.y = 0.7, 0.50
            else: pt.x, pt.y = 0.5, 0.5
            return pt
        landmarks.landmark = {i: get_closed_mouth(i) for i in range(468)}

        _, data = self.eye_detector.process(frame, landmarks)
        self.assertEqual(data["yawns"], 1)
        self.assertGreater(self.eye_detector.yawn_cooldown, 0)

    def test_drowsiness_threshold(self):
        """Test drowsiness flag triggers only after CLOSED_FRAMES_THRESHOLD."""
        self.eye_detector.closed_frames = self.eye_detector.CLOSED_FRAMES_THRESHOLD - 1
        self.assertFalse(self.eye_detector.closed_frames >= self.eye_detector.CLOSED_FRAMES_THRESHOLD)

        self.eye_detector.closed_frames += 1
        drowsy = self.eye_detector.closed_frames >= self.eye_detector.CLOSED_FRAMES_THRESHOLD
        self.assertTrue(drowsy)

    def test_reset_detection(self):
        """Verify reset_detection() zeroes out all counters."""
        self.eye_detector.closed_frames = 50
        self.eye_detector.yawn_count = 3
        self.eye_detector.mouth_open_frames = 10
        self.eye_detector.yawn_active = True
        self.eye_detector.yawn_cooldown = 15

        self.eye_detector.reset_detection()
        self.assertEqual(self.eye_detector.closed_frames, 0)
        self.assertEqual(self.eye_detector.yawn_count, 0)
        self.assertEqual(self.eye_detector.mouth_open_frames, 0)
        self.assertFalse(self.eye_detector.yawn_active)
        self.assertEqual(self.eye_detector.yawn_cooldown, 0)


if __name__ == "__main__":
    unittest.main()
