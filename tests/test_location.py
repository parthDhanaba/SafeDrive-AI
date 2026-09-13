"""
Tests for Windows Device Location Subsystem
"""
import unittest
from unittest.mock import patch, MagicMock
import subprocess
from location import Location, LocationProvider, get_emergency_location


class TestLocationSubsystem(unittest.TestCase):
    def test_location_dataclass_available(self):
        """Test Location dataclass properties when location is valid."""
        loc = Location(
            latitude=16.9889,
            longitude=73.3065,
            accuracy=50.0,
            is_available=True,
            status_text="Available"
        )
        self.assertEqual(loc.maps_url, "https://www.google.com/maps?q=16.9889,73.3065")
        self.assertIn("16.98890", loc.summary())
        self.assertIn("±50m", loc.summary())

    def test_location_dataclass_unavailable(self):
        """Test Location dataclass properties when location is unavailable."""
        loc = Location(
            is_available=False,
            status_text="Unavailable"
        )
        self.assertEqual(loc.maps_url, "Unavailable")
        self.assertEqual(loc.summary(), "Unavailable")

    @patch("subprocess.run")
    def test_get_device_location_success(self, mock_run):
        """Test parsing valid Windows GeoCoordinateWatcher output."""
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stdout = '{"Latitude": 18.5204, "Longitude": 73.8567, "HorizontalAccuracy": 100}'
        mock_run.return_value = mock_res

        provider = LocationProvider()
        loc = provider.get_device_location(timeout=1.0)
        self.assertTrue(loc.is_available)
        self.assertAlmostEqual(loc.latitude, 18.5204)
        self.assertAlmostEqual(loc.longitude, 73.8567)
        self.assertEqual(loc.accuracy, 100.0)

    @patch("subprocess.run")
    def test_get_device_location_timeout(self, mock_run):
        """Test fallback when subprocess times out."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="powershell", timeout=1.0)

        provider = LocationProvider()
        loc = provider.get_device_location(timeout=1.0)
        self.assertFalse(loc.is_available)
        self.assertIn(loc.status_text, ("Timeout", "Unavailable"))

    @patch("subprocess.run")
    def test_get_device_location_unavailable_output(self, mock_run):
        """Test fallback when Windows Location reports UNAVAILABLE."""
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stdout = "UNAVAILABLE"
        mock_run.return_value = mock_res

        provider = LocationProvider()
        loc = provider.get_device_location(timeout=1.0)
        self.assertFalse(loc.is_available)
        self.assertEqual(loc.status_text, "Unavailable")


if __name__ == "__main__":
    unittest.main()
