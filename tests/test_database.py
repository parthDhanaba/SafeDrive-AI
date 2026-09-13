"""
Tests for SafeDrive-AI SQLite Database Subsystem
"""
import unittest
import sqlite3
import gc
from pathlib import Path
import tempfile
import os

import database


class TestDatabaseSubsystem(unittest.TestCase):
    def setUp(self):
        # Create temporary database for testing
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.original_db_path = database.DATABASE_PATH
        database.DATABASE_PATH = Path(self.temp_db.name)
        database.initialize_database()

    def tearDown(self):
        database.DATABASE_PATH = self.original_db_path
        gc.collect()
        try:
            if os.path.exists(self.temp_db.name):
                os.remove(self.temp_db.name)
        except OSError:
            pass

    def test_initialize_and_schema(self):
        """Verify all tables and migrated columns exist."""
        with database.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = {row["name"] for row in cursor.fetchall()}
            self.assertIn("drivers", tables)
            self.assertIn("vehicles", tables)
            self.assertIn("safety_events", tables)
            self.assertIn("emergency_alerts", tables)

            # Check migrated columns in safety_events
            cursor.execute("PRAGMA table_info(safety_events);")
            cols = {row["name"] for row in cursor.fetchall()}
            self.assertIn("location_accuracy", cols)
            self.assertIn("photo_path", cols)
            self.assertIn("notification_status", cols)

    def test_driver_and_vehicle_crud(self):
        """Verify driver and vehicle creation and profile retrieval."""
        driver_id = database.add_driver(
            name="Jane Doe",
            phone="+1234567890",
            emergency_contact_name="Bob Doe",
            emergency_contact_phone="+0987654321"
        )
        self.assertGreater(driver_id, 0)

        vehicle_id = database.add_vehicle(
            vehicle_number="DL-01-XYZ",
            vehicle_type="Sedan",
            owner_name="Jane Doe"
        )
        self.assertGreater(vehicle_id, 0)

        # Retrieve default profile
        d_id, v_id = database.get_default_profile()
        self.assertEqual(d_id, driver_id)
        self.assertEqual(v_id, vehicle_id)

        driver = database.get_driver(driver_id)
        self.assertEqual(driver["name"], "Jane Doe")

        vehicle = database.get_vehicle(vehicle_id)
        self.assertEqual(vehicle["vehicle_number"], "DL-01-XYZ")

    def test_safety_events_logging(self):
        """Verify saving safety events and calculating summary stats."""
        d_id = database.add_driver(name="Test Driver")
        v_id = database.add_vehicle(vehicle_number="TEST-01")

        event_id = database.save_safety_event(
            driver_id=d_id,
            vehicle_id=v_id,
            event_type="YAWN",
            severity="WARNING",
            ear_value=0.28,
            mar_value=0.55,
            yawn_count=1,
            closed_frames=0,
            response_status="DETECTED"
        )
        self.assertGreater(event_id, 0)

        # Save emergency event
        emerg_id = database.save_safety_event(
            driver_id=d_id,
            vehicle_id=v_id,
            event_type="EMERGENCY",
            severity="CRITICAL",
            ear_value=0.15,
            mar_value=0.2,
            yawn_count=3,
            closed_frames=50,
            response_status="NO_RESPONSE",
            alarm_triggered=True,
            hazard_activated=True,
            sos_sent=True,
            photo_path="emergency_captures/test.jpg",
            notification_status="SIMULATED"
        )
        self.assertGreater(emerg_id, 0)

        stats = database.get_event_statistics()
        self.assertGreaterEqual(stats["total_yawns"], 1)
        self.assertGreaterEqual(stats["emergency_events"], 1)

        recent = database.get_recent_events(limit=5)
        self.assertEqual(len(recent), 2)
        self.assertEqual(recent[0]["event_type"], "EMERGENCY")


if __name__ == "__main__":
    unittest.main()
