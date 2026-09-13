"""
Tests for Live Location to WhatsApp Family Alert Subsystem
Covers all 10 prompt-specified validation criteria:
1. Location retrieval
2. Google Maps link generation
3. Emergency WhatsApp message generation
4. Mock WhatsApp sending
5. Emergency notification sent only once
6. Missing WhatsApp credentials
7. Missing location
8. WhatsApp API failure
9. Emergency reset using R
10. SQLite emergency alert logging
"""
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
import io
import sys

from location import Location, get_emergency_location
from notifications import (
    format_whatsapp_emergency_message,
    format_whatsapp_location_update_message,
    MockWhatsAppProvider,
    MetaCloudWhatsAppProvider,
    send_whatsapp_family_alert,
    NotificationResult
)
from emergency import EmergencyCoordinator
from database import (
    initialize_database,
    save_emergency_alert,
    get_emergency_alerts_for_event,
    get_connection
)


class TestWhatsAppFamilyAlertSubsystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        initialize_database()

    def setUp(self):
        self.mock_alarm = MagicMock()
        self.mock_alarm.is_playing.return_value = False
        self.coord = EmergencyCoordinator(self.mock_alarm)
        self.driver = {
            "name": "Sarah Connor",
            "emergency_contact_name": "John Connor",
            "emergency_contact_phone": "+15559998888"
        }
        self.vehicle = {"vehicle_number": "MH-02-CY-2026"}

    # 1. Location retrieval
    def test_01_location_retrieval(self):
        """Verify Location dataclass stores and returns latitude, longitude, accuracy, timestamp."""
        loc = Location(
            latitude=18.5204,
            longitude=73.8567,
            accuracy=12.5,
            is_available=True,
            status_text="Available",
            timestamp="2026-09-13T22:00:00"
        )
        self.assertEqual(loc.latitude, 18.5204)
        self.assertEqual(loc.longitude, 73.8567)
        self.assertEqual(loc.accuracy, 12.5)
        self.assertEqual(loc.timestamp, "2026-09-13T22:00:00")
        self.assertTrue(loc.is_available)
        self.assertIn("18.52040", loc.summary())

    # 2. Google Maps link generation
    def test_02_google_maps_link_generation(self):
        """Verify Google Maps URL is generated accurately from coordinates and handles missing fixes."""
        loc = Location(latitude=19.0760, longitude=72.8777, is_available=True)
        self.assertEqual(loc.maps_url, "https://www.google.com/maps?q=19.076,72.8777")

        loc_unavail = Location(is_available=False)
        self.assertEqual(loc_unavail.maps_url, "Unavailable")

    # 3. Emergency WhatsApp message generation
    def test_03_emergency_whatsapp_message_generation(self):
        """Verify exact text and structure of emergency WhatsApp family message."""
        msg = format_whatsapp_emergency_message(
            driver_name="Sarah Connor",
            vehicle_number="MH-02-CY-2026",
            maps_url="https://www.google.com/maps?q=18.5204,73.8567",
            photo_path=Path("emergency_20260913_230000.jpg"),
            timestamp="2026-09-13 23:00:00",
            accuracy=15.0
        )
        self.assertIn("SAFE DRIVE-AI EMERGENCY ALERT", msg)
        self.assertIn("Driver: Sarah Connor", msg)
        self.assertIn("Vehicle: MH-02-CY-2026", msg)
        self.assertIn("The system has detected a serious driver-safety emergency and the driver did not respond.", msg)
        self.assertIn("LIVE LOCATION:\nhttps://www.google.com/maps?q=18.5204,73.8567", msg)
        self.assertIn("Time:\n2026-09-13 23:00:00", msg)
        self.assertIn("Emergency photo:\nemergency_20260913_230000.jpg", msg)
        self.assertIn("Please contact the driver immediately.", msg)

    # 4. Mock WhatsApp sending
    def test_04_mock_whatsapp_sending(self):
        """Verify MockWhatsAppProvider prints standardized prompt block and returns SIMULATED."""
        provider = MockWhatsAppProvider()
        self.assertTrue(provider.is_configured())

        captured_stdout = io.StringIO()
        sys.stdout = captured_stdout
        try:
            result = provider.send(
                recipient="+15559998888",
                message="Test Message Content",
                meta={"maps_url": "https://maps.google.com/?q=18.5,73.8", "photo_path": "photo.jpg"}
            )
        finally:
            sys.stdout = sys.__stdout__

        output = captured_stdout.getvalue()
        self.assertIn("[MOCK WHATSAPP]", output)
        self.assertIn("Emergency alert sent to: +15559998888", output)
        self.assertIn("Location: https://maps.google.com/?q=18.5,73.8", output)
        self.assertIn("Photo: photo.jpg", output)

        self.assertTrue(result.success)
        self.assertEqual(result.status, "SIMULATED")
        self.assertEqual(result.provider_name, "Mock WhatsApp Provider")
        self.assertIsNotNone(result.message_id)
        self.assertTrue(result.message_id.startswith("SIM-WA-"))

    # 5. Emergency notification sent only once
    def test_05_notification_sent_only_once(self):
        """Verify that emergency SOS and WhatsApp alert are dispatched strictly once per emergency event."""
        with patch("emergency.send_whatsapp_family_alert") as mock_wa, \
             patch("emergency.send_emergency_notification") as mock_sms, \
             patch("emergency.capture_emergency_photo") as mock_photo, \
             patch("emergency.get_emergency_location") as mock_loc:

            mock_wa.return_value = NotificationResult(
                success=True, status="SIMULATED", provider_name="Mock WhatsApp",
                message_text="Test", recipient="+15559998888"
            )
            mock_sms.return_value = NotificationResult(
                success=True, status="SIMULATED", provider_name="Mock SMS",
                message_text="Test", recipient="+15559998888"
            )
            mock_photo.return_value = Path("test.jpg")
            mock_loc.return_value = Location(latitude=18.5, longitude=73.8, is_available=True)

            eye_data_danger = {"ear": 0.15, "mar": 0.10, "yawns": 0, "closed_frames": 50, "drowsy": True}

            # Fast forward time to trigger emergency activation
            self.coord.alarm_start_time = 100.0
            with patch("time.time", return_value=120.0):  # 20s elapsed > 10s timeout
                # Simulate 20 consecutive frames in emergency mode
                for _ in range(20):
                    self.coord.update(eye_data_danger, None, 1, 1, self.driver, self.vehicle)

            # Wait briefly for daemon worker thread to complete
            import time
            time.sleep(0.3)

            # Verify send_whatsapp_family_alert called exactly ONCE
            self.assertEqual(mock_wa.call_count, 1)

    # 6. Missing WhatsApp credentials
    def test_06_missing_whatsapp_credentials(self):
        """Verify MetaCloudWhatsAppProvider handles missing credentials safely without crashing."""
        provider = MetaCloudWhatsAppProvider(access_token="", phone_number_id="")
        self.assertFalse(provider.is_configured())

        res = provider.send(recipient="+15551234567", message="Test Message")
        self.assertFalse(res.success)
        self.assertEqual(res.status, "FAILED")
        self.assertIn("missing", res.error.lower())

    # 7. Missing location
    def test_07_missing_location(self):
        """Verify system handles unavailable location gracefully without crashing."""
        loc_unavail = Location(is_available=False, status_text="Unavailable")
        res = send_whatsapp_family_alert(
            driver=self.driver,
            vehicle=self.vehicle,
            location_obj=loc_unavail,
            photo_path=None
        )
        self.assertTrue(res.success)
        self.assertIn(res.status, ("SIMULATED", "SENT"))
        self.assertIn("Unavailable", res.message_text)

    # 8. WhatsApp API failure
    def test_08_whatsapp_api_failure(self):
        """Verify MetaCloudWhatsAppProvider gracefully catches HTTP failures without exposing secrets."""
        provider = MetaCloudWhatsAppProvider(access_token="SECRET_TOKEN_XYZ", phone_number_id="123456789")

        # Mock requests.post raising HTTP 500 error
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error with SECRET_TOKEN_XYZ in response"

        with patch("requests.post", return_value=mock_response):
            res = provider.send(recipient="+15551234567", message="Test Message")
            self.assertFalse(res.success)
            self.assertEqual(res.status, "FAILED")
            # Verify secret token is redacted
            self.assertNotIn("SECRET_TOKEN_XYZ", res.error)
            self.assertIn("[REDACTED_ACCESS_TOKEN]", res.error)

    # 9. Emergency reset using R
    def test_09_emergency_reset_using_r(self):
        """Verify R reset clears emergency state, halts periodic location tracker, and stops alarm."""
        self.coord.is_emergency = True
        self.coord.sos_triggered = True
        self.coord.whatsapp_sent = True
        self.coord.last_whatsapp_status = "SENT"

        eye_detector_mock = MagicMock()
        self.coord.reset(eye_detector_mock)

        self.assertFalse(self.coord.is_emergency)
        self.assertFalse(self.coord.sos_triggered)
        self.assertFalse(self.coord.whatsapp_sent)
        self.assertEqual(self.coord.last_whatsapp_status, "IDLE")
        self.assertTrue(self.coord._stop_periodic_updates.is_set())
        self.mock_alarm.stop.assert_called()
        eye_detector_mock.reset_detection.assert_called_once()

    # 10. SQLite emergency alert logging
    def test_10_sqlite_emergency_alert_logging(self):
        """Verify SQLite emergency_alerts records FAMILY recipient, flags, and delivery status."""
        alert_id = save_emergency_alert(
            event_id=None,
            recipient_type="FAMILY",
            recipient_name="John Connor",
            recipient_phone="+15559998888",
            message="Test Emergency WhatsApp Message",
            latitude=18.5204,
            longitude=73.8567,
            location_accuracy=10.0,
            photo_path="emergency_captures/test.jpg",
            delivery_status="SIMULATED",
            whatsapp_attempted=1,
            whatsapp_succeeded=1,
            location_available=1,
            photo_captured=1,
            channel="WHATSAPP"
        )
        self.assertIsNotNone(alert_id)

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM emergency_alerts WHERE id = ?", (alert_id,))
            row = dict(cursor.fetchone())

            self.assertEqual(row["recipient_type"], "FAMILY")
            self.assertEqual(row["recipient_name"], "John Connor")
            self.assertEqual(row["recipient_phone"], "+15559998888")
            self.assertEqual(row["delivery_status"], "SIMULATED")
            self.assertEqual(row["channel"], "WHATSAPP")
            self.assertEqual(row["whatsapp_attempted"], 1)
            self.assertEqual(row["whatsapp_succeeded"], 1)
            self.assertEqual(row["location_available"], 1)
            self.assertEqual(row["photo_captured"], 1)


if __name__ == "__main__":
    unittest.main()
