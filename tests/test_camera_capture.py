"""
Tests for Emergency Photo Capture Subsystem
"""
import unittest
import numpy as np
from pathlib import Path
import os
import camera_capture


class TestCameraCaptureSubsystem(unittest.TestCase):
    def test_capture_emergency_photo_valid_frame(self):
        """Verify snapshot is written to disk with emergency_ timestamp format."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        photo_path = camera_capture.capture_emergency_photo(frame)

        self.assertIsNotNone(photo_path)
        self.assertTrue(isinstance(photo_path, Path))
        self.assertTrue(photo_path.exists())
        self.assertTrue(photo_path.name.startswith("emergency_"))
        self.assertTrue(photo_path.name.endswith(".jpg"))

        # Clean up test artifact
        try:
            os.remove(photo_path)
        except OSError:
            pass

    def test_capture_emergency_photo_empty_frame(self):
        """Verify graceful failure and None return when frame is None or empty."""
        res_none = camera_capture.capture_emergency_photo(None)
        self.assertIsNone(res_none)

        empty_frame = np.array([])
        res_empty = camera_capture.capture_emergency_photo(empty_frame)
        self.assertIsNone(res_empty)


if __name__ == "__main__":
    unittest.main()
