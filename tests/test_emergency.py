"""
Tests for SOS Emergency Coordinator and Workflow
"""
import unittest
import time
import numpy as np
from unittest.mock import MagicMock, patch

from emergency import EmergencyCoordinator
from eye import EyeDetector


class TestEmergencyWorkflow(unittest.TestCase):
    def setUp(self):
        self.mock_alarm = MagicMock()
        self.mock_alarm.is_playing.return_value = False
        self.coord = EmergencyCoordinator(self.mock_alarm)
        self.eye_detector = EyeDetector()
        self.dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        self.driver = {"name": "Test Driver", "emergency_contact_phone": "+15551112222"}
        self.vehicle = {"vehicle_number": "MH-04-TEST"}

    def test_normal_state(self):
        """Under normal driving conditions, alarm and countdown remain inactive."""
        eye_data = {"ear": 0.28, "mar": 0.20, "yawns": 0, "closed_frames": 0, "drowsy": False}
        self.coord.update(eye_data, self.dummy_frame, 1, 1, self.driver, self.vehicle)

        self.assertFalse(self.coord.is_emergency)
        self.assertFalse(self.coord.countdown_active)
        self.assertFalse(self.coord.danger_detected)
        self.mock_alarm.play.assert_not_called()

    def test_yawn_danger_triggers_countdown(self):
        """3 yawns trigger danger warning and countdown."""
        eye_data = {"ear": 0.28, "mar": 0.20, "yawns": 3, "closed_frames": 0, "drowsy": False}
        self.coord.update(eye_data, self.dummy_frame, 1, 1, self.driver, self.vehicle)

        self.assertTrue(self.coord.danger_detected)
        self.assertTrue(self.coord.countdown_active)
        self.assertIn("Yawning", self.coord.danger_reason)
        self.mock_alarm.play.assert_called()

    def test_opening_eyes_does_not_clear_yawn_danger(self):
        """Regression test: Driver opening eyes does NOT prematurely reset 3-yawn danger state."""
        eye_data_danger = {"ear": 0.28, "mar": 0.20, "yawns": 3, "closed_frames": 0, "drowsy": False}
        self.coord.update(eye_data_danger, self.dummy_frame, 1, 1, self.driver, self.vehicle)
        self.assertTrue(self.coord.countdown_active)

        # Eyes fully open frame:
        eye_data_open = {"ear": 0.35, "mar": 0.15, "yawns": 3, "closed_frames": 0, "drowsy": False}
        self.coord.update(eye_data_open, self.dummy_frame, 1, 1, self.driver, self.vehicle)

        # Countdown MUST remain active until driver presses R
        self.assertTrue(self.coord.countdown_active)
        self.assertTrue(self.coord.danger_detected)

    def test_r_key_resets_danger_without_alarm_restart(self):
        """Regression test: Pressing R cleanly resets all state and stops alarm."""
        eye_data = {"ear": 0.28, "mar": 0.20, "yawns": 3, "closed_frames": 0, "drowsy": False}
        self.coord.update(eye_data, self.dummy_frame, 1, 1, self.driver, self.vehicle)
        self.assertTrue(self.coord.countdown_active)

        # Driver presses R
        self.coord.reset(self.eye_detector)
        self.assertFalse(self.coord.countdown_active)
        self.assertFalse(self.coord.is_emergency)
        self.assertFalse(self.coord.danger_detected)
        self.mock_alarm.stop.assert_called()

        # Subsequent normal frame must NOT restart alarm
        eye_data_normal = {"ear": 0.28, "mar": 0.20, "yawns": 0, "closed_frames": 0, "drowsy": False}
        self.mock_alarm.play.reset_mock()
        self.coord.update(eye_data_normal, self.dummy_frame, 1, 1, self.driver, self.vehicle)
        self.mock_alarm.play.assert_not_called()

    @patch("emergency.EmergencyCoordinator._sos_orchestration_worker")
    def test_countdown_timeout_activates_emergency(self, mock_worker):
        """Verify 10s timeout transitions to emergency mode and triggers SOS worker."""
        eye_data = {"ear": 0.12, "mar": 0.20, "yawns": 0, "closed_frames": 50, "drowsy": True}
        self.coord.update(eye_data, self.dummy_frame, 1, 1, self.driver, self.vehicle)

        # Force alarm start time back 11 seconds to simulate timeout
        self.coord.alarm_start_time = time.time() - 11.0

        # Next update should trigger emergency
        self.coord.update(eye_data, self.dummy_frame, 1, 1, self.driver, self.vehicle)

        self.assertTrue(self.coord.is_emergency)
        self.assertTrue(self.coord.hazard_lights)
        self.assertTrue(self.coord.sos_triggered)
        mock_worker.assert_called_once()


if __name__ == "__main__":
    unittest.main()
