"""
Tests for UI Dashboard and Dialog Components
"""
import unittest
import numpy as np
from ui import SafeDriveDashboard, EventHistoryDialog
from location import Location


class TestUISubsystem(unittest.TestCase):
    def test_dashboard_creation_and_telemetry_update(self):
        """Verify dashboard starts, updates telemetry, updates video frame, and cleanly destroys."""
        app = SafeDriveDashboard()
        app.withdraw()  # Do not show on screen during headless test

        # Dummy frame
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        app.update_frame(frame)

        # Telemetry
        eye_data = {"ear": 0.29, "mar": 0.15, "yawns": 1, "closed_frames": 0, "drowsy": False, "state": "OPEN"}
        emerg_status = {
            "state": "WARNING",
            "is_emergency": False,
            "hazard_lights": False,
            "countdown_active": False,
            "remaining_time": 10,
            "danger_reason": "Notice: Yawn count: 1 / 3",
            "alarm_active": False,
            "notification_status": "IDLE",
            "provider_name": "Mock SMS",
            "photo_status": "Ready",
            "last_event_id": None
        }
        loc = Location(latitude=16.9889, longitude=73.3065, accuracy=50.0, is_available=True)

        app.update_telemetry(fps=30.0, eye_data=eye_data, emerg_status=emerg_status, location_obj=loc)
        app.update()

        # Check widget values
        self.assertEqual(app.val_ear.cget("text"), "0.29")
        self.assertEqual(app.val_mar.cget("text"), "0.15")
        self.assertIn("OPEN", app.val_closed.cget("text"))
        self.assertIn("1 / 3", app.val_yawns.cget("text"))

        # Clean destroy
        app.destroy()


if __name__ == "__main__":
    unittest.main()
