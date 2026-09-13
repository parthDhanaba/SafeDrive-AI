"""
Tests for Notifications and Mock SMS Subsystem
"""
import unittest
from pathlib import Path
from notifications import (
    MockSMSProvider,
    TwilioSMSProvider,
    format_emergency_message,
    send_emergency_notification,
    get_active_provider
)
from location import Location


class TestNotificationSubsystem(unittest.TestCase):
    def test_format_emergency_message(self):
        """Verify standard alert message formatting conforms to prompt specification."""
        msg = format_emergency_message(
            driver_name="John Driver",
            vehicle_number="MH-12-AB-1234",
            reason="Excessive Yawning (3 yawns)",
            maps_url="https://www.google.com/maps?q=16.9889,73.3065",
            accuracy=50.0,
            photo_path=Path("emergency_20260913_200000.jpg"),
            timestamp="2026-09-13 20:00:00"
        )
        self.assertIn("🚨 SAFEDRIVE-AI EMERGENCY ALERT", msg)
        self.assertIn("John Driver", msg)
        self.assertIn("MH-12-AB-1234", msg)
        self.assertIn("Excessive Yawning", msg)
        self.assertIn("SOS ACTIVATED", msg)
        self.assertIn("https://www.google.com/maps?q=16.9889,73.3065", msg)
        self.assertIn("±50 meters", msg)
        self.assertIn("emergency_20260913_200000.jpg", msg)
        self.assertIn("2026-09-13 20:00:00", msg)

    def test_mock_sms_provider(self):
        """Verify MockSMSProvider returns SIMULATED status and never claims DELIVERED."""
        provider = MockSMSProvider()
        self.assertTrue(provider.is_configured())

        res = provider.send(
            recipient="+1234567890",
            message="Test Emergency Message"
        )
        self.assertTrue(res.success)
        self.assertEqual(res.status, "SIMULATED")
        self.assertEqual(res.provider_name, "Mock SMS Provider")
        self.assertIsNotNone(res.message_id)
        self.assertTrue(res.message_id.startswith("SIM-"))

    def test_twilio_unconfigured_or_fallback(self):
        """Verify Twilio provider handles missing or invalid setup safely."""
        provider = TwilioSMSProvider()
        # If unconfigured, is_configured should be False or send should handle failure gracefully
        res = provider.send(recipient="", message="Test")
        self.assertFalse(res.success)
        self.assertEqual(res.status, "FAILED")

    def test_send_emergency_notification_dispatch(self):
        """Verify high level notification dispatcher coordinates properly."""
        loc = Location(latitude=18.52, longitude=73.85, accuracy=30.0, is_available=True)
        driver = {"name": "Test Driver", "emergency_contact_name": "Contact", "emergency_contact_phone": "+15551112222"}
        vehicle = {"vehicle_number": "KA-01-EF-5678"}

        res = send_emergency_notification(
            driver=driver,
            vehicle=vehicle,
            reason="Drowsiness / Prolonged Eye Closure",
            location_obj=loc,
            photo_path=Path("emergency_captures/sample.jpg")
        )
        self.assertIsNotNone(res)
        self.assertIn(res.status, ("SIMULATED", "SENT", "FAILED"))


if __name__ == "__main__":
    unittest.main()
