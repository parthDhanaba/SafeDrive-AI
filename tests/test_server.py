"""
Tests for SafeDrive-AI Flask Server & API Endpoints
Verifies REST API responses, video feed streaming, model status, and session controls.
"""
import unittest
import json
from server import app, pipeline, eye_model, yawn_model


class TestServerAPI(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        pipeline.stop()

    def setUp(self):
        self.client = app.test_client()

    def test_status_endpoint(self):
        """Verify /api/status returns HTTP 200 with complete telemetry and model data."""
        response = self.client.get("/api/status")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()

        self.assertEqual(data["status"], "ok")
        self.assertIn("models", data)
        self.assertIn("eye_model", data["models"])
        self.assertIn("yawn_model", data["models"])
        self.assertTrue(data["models"]["eye_model"]["loaded"])
        self.assertTrue(data["models"]["yawn_model"]["loaded"])

        self.assertIn("telemetry", data)
        self.assertIn("ear", data["telemetry"])
        self.assertIn("mar", data["telemetry"])
        self.assertIn("alarm", data)
        self.assertIn("location", data)
        self.assertIn("session", data)

    def test_video_feed_headers_and_content(self):
        """Verify /api/video_feed returns multipart MJPEG content type."""
        response = self.client.get("/api/video_feed")
        self.assertEqual(response.status_code, 200)
        self.assertIn("multipart/x-mixed-replace; boundary=frame", response.headers.get("Content-Type", ""))

    def test_session_controls(self):
        """Verify start, stop, and reset session endpoints."""
        res_stop = self.client.post("/api/session/stop")
        self.assertEqual(res_stop.status_code, 200)
        self.assertFalse(pipeline.monitoring_active)

        res_start = self.client.post("/api/session/start")
        self.assertEqual(res_start.status_code, 200)
        self.assertTrue(pipeline.monitoring_active)

        res_reset = self.client.post("/api/session/reset")
        self.assertEqual(res_reset.status_code, 200)

    def test_events_endpoint(self):
        """Verify /api/events returns event list from database."""
        response = self.client.get("/api/events?limit=5")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertIsInstance(data["events"], list)

    def test_statistics_endpoint(self):
        """Verify /api/statistics returns aggregated counts."""
        response = self.client.get("/api/statistics")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertIn("total_yawns", data["statistics"])

    def test_config_endpoint_get_and_post(self):
        """Verify reading and updating configuration thresholds."""
        res_get = self.client.get("/api/config")
        self.assertEqual(res_get.status_code, 200)
        cfg = res_get.get_json()
        self.assertIn("ear_threshold", cfg)
        self.assertIn("mar_threshold", cfg)

        # Update test threshold
        res_post = self.client.post("/api/config", json={"ear_threshold": 0.23})
        self.assertEqual(res_post.status_code, 200)

    def test_test_trigger_simulation(self):
        """Verify simulation trigger endpoint for presentations."""
        res_drowsy = self.client.post("/api/test/trigger", json={"action": "drowsy"})
        self.assertEqual(res_drowsy.status_code, 200)

        res_yawn = self.client.post("/api/test/trigger", json={"action": "yawn"})
        self.assertEqual(res_yawn.status_code, 200)

        res_reset = self.client.post("/api/test/trigger", json={"action": "reset"})
        self.assertEqual(res_reset.status_code, 200)


if __name__ == "__main__":
    unittest.main()
