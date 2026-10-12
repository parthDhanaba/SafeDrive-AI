"""
Tests for Deep Learning Eye Drowsiness and Yawn Models Integration
Verifies model loading, inference shapes, preprocessing, and hybrid fusion.
"""
import unittest
import numpy as np
import torch
from pathlib import Path
from unittest.mock import MagicMock

from config import EYE_MODEL_PATH, YAWN_MODEL_PATH, EYE_MODEL_THRESHOLD, YAWN_MODEL_THRESHOLD
from model_loader import eye_model, yawn_model, EyeDrowsinessModel, YawnDetectionModel
from eye import EyeDetector


class TestAIModelsIntegration(unittest.TestCase):
    def test_model_files_exist(self):
        """Verify both model files exist in the models directory."""
        self.assertTrue(EYE_MODEL_PATH.exists(), f"Eye model missing at {EYE_MODEL_PATH}")
        self.assertTrue(YAWN_MODEL_PATH.exists(), f"Yawn model missing at {YAWN_MODEL_PATH}")

    def test_eye_model_loaded(self):
        """Verify eye drowsiness model loads successfully."""
        self.assertTrue(eye_model.loaded, "Eye drowsiness model failed to load")
        self.assertIsNotNone(eye_model.model, "Eye model instance is None")

    def test_yawn_model_loaded(self):
        """Verify yawn detection model loads successfully."""
        self.assertTrue(yawn_model.loaded, "Yawn detection model failed to load")
        self.assertIsNotNone(yawn_model.model, "Yawn model instance is None")

    def test_eye_model_sample_inference(self):
        """Run sample inference on eye model with expected input shape (1, 64, 64, 3)."""
        # Test with synthetic BGR crop (e.g. 80x90 image)
        dummy_crop = np.random.randint(0, 256, (80, 90, 3), dtype=np.uint8)
        prob = eye_model.predict(dummy_crop)
        self.assertIsNotNone(prob, "Inference returned None")
        self.assertGreaterEqual(prob, 0.0, "Probability should be >= 0.0")
        self.assertLessEqual(prob, 1.0, "Probability should be <= 1.0")

        # Test threshold check
        is_closed, p = eye_model.is_closed(dummy_crop, threshold=0.50)
        self.assertEqual(is_closed, p < 0.50)

    def test_yawn_model_sample_inference(self):
        """Run sample inference on yawn model with expected input shape (1, 128, 128, 3)."""
        dummy_crop = np.random.randint(0, 256, (140, 160, 3), dtype=np.uint8)
        prob = yawn_model.predict(dummy_crop)
        self.assertIsNotNone(prob, "Inference returned None")
        self.assertGreaterEqual(prob, 0.0, "Probability should be >= 0.0")
        self.assertLessEqual(prob, 1.0, "Probability should be <= 1.0")

        # Test threshold check (initial threshold 0.40)
        is_yawn, p = yawn_model.is_yawn(dummy_crop, threshold=0.40)
        self.assertEqual(is_yawn, p >= 0.40)

    def test_invalid_crop_handling(self):
        """Verify models handle None, empty, and tiny crops without raising exceptions."""
        self.assertIsNone(eye_model.predict(None))
        self.assertIsNone(eye_model.predict(np.zeros((0, 0, 3), dtype=np.uint8)))
        self.assertIsNone(eye_model.predict(np.zeros((2, 2, 3), dtype=np.uint8)))

        self.assertIsNone(yawn_model.predict(None))
        self.assertIsNone(yawn_model.predict(np.zeros((0, 0, 3), dtype=np.uint8)))
        self.assertIsNone(yawn_model.predict(np.zeros((4, 4, 3), dtype=np.uint8)))

    def test_missing_model_fallback(self):
        """Verify fallback when model file does not exist."""
        dummy_eye = EyeDrowsinessModel(Path("models/nonexistent_eye.keras"))
        self.assertFalse(dummy_eye.loaded)
        self.assertIsNone(dummy_eye.predict(np.zeros((64, 64, 3), dtype=np.uint8)))

        dummy_yawn = YawnDetectionModel(Path("models/nonexistent_yawn.keras"))
        self.assertFalse(dummy_yawn.loaded)
        self.assertIsNone(dummy_yawn.predict(np.zeros((128, 128, 3), dtype=np.uint8)))

    def test_eye_detector_hybrid_telemetry(self):
        """Verify EyeDetector returns AI telemetry keys in process()."""
        detector = EyeDetector()
        frame = np.zeros((200, 200, 3), dtype=np.uint8)

        # Mock landmarks
        landmarks = MagicMock()
        def get_landmark(idx):
            pt = MagicMock()
            pt.x, pt.y = 0.5, 0.5
            return pt
        landmarks.landmark = {i: get_landmark(i) for i in range(468)}

        _, telemetry = detector.process(frame, landmarks)
        self.assertIn("eye_open_prob", telemetry)
        self.assertIn("yawn_prob", telemetry)
        self.assertIn("eye_model_active", telemetry)
        self.assertIn("yawn_model_active", telemetry)
        self.assertTrue(telemetry["eye_model_active"])
        self.assertTrue(telemetry["yawn_model_active"])


if __name__ == "__main__":
    unittest.main()
