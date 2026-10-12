"""
SafeDrive-AI Deep Learning Model Loader & Inference Engine
Integrates trained Keras 3 models for eye drowsiness and yawn detection.
Provides robust pre-processing, thread-safe inference, and graceful fallbacks.
"""
import os
import sys
import io
import math
import zipfile
import threading
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

import cv2
import numpy as np

# Ensure Keras uses PyTorch backend for high performance and compatibility
os.environ.setdefault("KERAS_BACKEND", "torch")

# Set up pure-Python HDF5 shim (pyfive) to ensure 100% reliability
# and prevent Windows Smart App Control from blocking C-extension DLLs.
try:
    import pyfive

    class _DummyLink:
        pass

    pyfive.ExternalLink = _DummyLink
    pyfive.SoftLink = _DummyLink

    if hasattr(pyfive, "high_level") and hasattr(pyfive.high_level, "Dataset"):
        pyfive.high_level.Dataset.external = None
        pyfive.high_level.Dataset.is_virtual = False
        pyfive.high_level.Dataset.__array__ = (
            lambda self, dtype=None: self[()] if dtype is None else self[()].astype(dtype)
        )

    if hasattr(pyfive, "h5d") and hasattr(pyfive.h5d, "DatasetID"):
        pyfive.h5d.DatasetID.get_storage_size = lambda self: 100000000

    _orig_get = pyfive.Group.get

    def _patched_get(self, name, default=None, **kwargs):
        if name not in self:
            return default
        if kwargs.get("getclass"):
            return type(self[name])
        return _orig_get(self, name, default)

    pyfive.Group.get = _patched_get
    pyfive.File.__bool__ = lambda self: True
    pyfive.Group.__bool__ = lambda self: True

    sys.modules["h5py"] = pyfive
except ImportError:
    pass

import torch
import keras

from config import (
    EYE_MODEL_PATH,
    YAWN_MODEL_PATH,
    EYE_MODEL_THRESHOLD,
    YAWN_MODEL_THRESHOLD
)
from logger import logger


class EyeDrowsinessModel:
    """
    Eye State Deep Learning Classifier.
    Model input: (1, 64, 64, 3) RGB image in range [0, 255].
    Internal layer: Rescaling(1./255).
    Model output: Sigmoid probability in range [0, 1].
      - Class 0: Closed Eyes (< threshold)
      - Class 1: Open Eyes (>= threshold)
    """

    def __init__(self, model_path: Optional[Path] = None):
        self.model_path = Path(model_path or EYE_MODEL_PATH)
        self.model = None
        self.loaded = False
        self._lock = threading.Lock()
        self.load()

    def load(self) -> bool:
        """Loads the eye drowsiness model once at startup."""
        if not self.model_path.exists():
            logger.warning(
                f"Eye drowsiness model not found at {self.model_path}. "
                "Eye state detection will fall back to geometric EAR."
            )
            self.loaded = False
            return False

        try:
            logger.info(f"Loading Eye Drowsiness Model from {self.model_path}...")
            # Load model with Keras
            self.model = keras.models.load_model(str(self.model_path))
            self.loaded = True

            # Warm-up run with dummy input to compile execution graph
            with torch.no_grad():
                dummy = torch.zeros(1, 64, 64, 3, dtype=torch.float32)
                _ = self.model(dummy)

            logger.info("Eye Drowsiness Model successfully loaded and warmed up.")
            return True
        except Exception as e:
            logger.error(f"Failed to load Eye Drowsiness Model: {e}")
            self.model = None
            self.loaded = False
            return False

    def predict(self, eye_crop: np.ndarray) -> Optional[float]:
        """
        Runs inference on an eye image crop.
        Converts BGR to RGB, resizes to 64x64, preserves [0, 255] scaling.
        Returns open_eye_probability (0.0 = closed, 1.0 = open).
        """
        if not self.loaded or self.model is None:
            return None

        if eye_crop is None or getattr(eye_crop, "size", 0) == 0:
            return None

        try:
            h, w = eye_crop.shape[:2]
            if h < 4 or w < 4:
                return None

            # Convert BGR to RGB
            rgb_crop = cv2.cvtColor(eye_crop, cv2.COLOR_BGR2RGB)

            # Resize to exactly 64 x 64 pixels
            resized = cv2.resize(rgb_crop, (64, 64), interpolation=cv2.INTER_AREA)

            # Convert to float32 tensor (preserve 0..255 pixel range, model has its own Rescaling layer)
            inp = torch.from_numpy(resized).unsqueeze(0).float()

            with self._lock, torch.no_grad():
                output = self.model(inp)
                if isinstance(output, torch.Tensor):
                    prob = float(output.item())
                else:
                    prob = float(np.array(output).flatten()[0])

            # Bound probability to [0.0, 1.0]
            return max(0.0, min(1.0, prob))

        except Exception as e:
            logger.warning(f"Error during Eye Drowsiness inference: {e}")
            return None

    def is_closed(self, eye_crop: np.ndarray, threshold: float = EYE_MODEL_THRESHOLD) -> Tuple[Optional[bool], Optional[float]]:
        """
        Returns (is_closed, open_prob).
        Closed eyes have open_prob < threshold (Class 0: closed).
        """
        prob = self.predict(eye_crop)
        if prob is None:
            return None, None
        return (prob < threshold), prob


class YawnDetectionModel:
    """
    Yawn Deep Learning Classifier (MobileNetV2 backbone).
    Model input: (1, 128, 128, 3) RGB image in range [0, 255].
    Model output: Sigmoid probability in range [0, 1].
      - Class 0: no_yawn (< threshold)
      - Class 1: yawn (>= threshold)
    Default threshold: 0.40.
    """

    def __init__(self, model_path: Optional[Path] = None):
        self.model_path = Path(model_path or YAWN_MODEL_PATH)
        self.model = None
        self.loaded = False
        self._lock = threading.Lock()
        self.load()

    def load(self) -> bool:
        """Loads the yawn detection model once at startup."""
        if not self.model_path.exists():
            logger.warning(
                f"Yawn detection model not found at {self.model_path}. "
                "Yawn detection will fall back to geometric MAR."
            )
            self.loaded = False
            return False

        try:
            logger.info(f"Loading Yawn Detection Model from {self.model_path}...")
            self.model = keras.models.load_model(str(self.model_path))
            self.loaded = True

            # Warm-up run with dummy input
            with torch.no_grad():
                dummy = torch.zeros(1, 128, 128, 3, dtype=torch.float32)
                _ = self.model(dummy)

            logger.info("Yawn Detection Model successfully loaded and warmed up.")
            return True
        except Exception as e:
            logger.error(f"Failed to load Yawn Detection Model: {e}")
            self.model = None
            self.loaded = False
            return False

    def predict(self, mouth_crop: np.ndarray) -> Optional[float]:
        """
        Runs inference on a mouth/lower-face crop.
        Converts BGR to RGB, resizes to 128x128, preserves [0, 255] float32 scaling
        (no extra MobileNetV2 preprocess_input, preserving expected training pipeline).
        Returns yawn_probability (0.0 = no yawn, 1.0 = yawn).
        """
        if not self.loaded or self.model is None:
            return None

        if mouth_crop is None or getattr(mouth_crop, "size", 0) == 0:
            return None

        try:
            h, w = mouth_crop.shape[:2]
            if h < 8 or w < 8:
                return None

            # Convert BGR to RGB
            rgb_crop = cv2.cvtColor(mouth_crop, cv2.COLOR_BGR2RGB)

            # Resize to exactly 128 x 128 pixels
            resized = cv2.resize(rgb_crop, (128, 128), interpolation=cv2.INTER_AREA)

            # Convert to float32 tensor without external normalization
            inp = torch.from_numpy(resized).unsqueeze(0).float()

            with self._lock, torch.no_grad():
                output = self.model(inp)
                if isinstance(output, torch.Tensor):
                    prob = float(output.item())
                else:
                    prob = float(np.array(output).flatten()[0])

            # Bound probability to [0.0, 1.0]
            return max(0.0, min(1.0, prob))

        except Exception as e:
            logger.warning(f"Error during Yawn Detection inference: {e}")
            return None

    def is_yawn(self, mouth_crop: np.ndarray, threshold: float = YAWN_MODEL_THRESHOLD) -> Tuple[Optional[bool], Optional[float]]:
        """
        Returns (is_yawn, yawn_prob).
        Yawn condition triggers when yawn_prob >= threshold.
        """
        prob = self.predict(mouth_crop)
        if prob is None:
            return None, None
        return (prob >= threshold), prob


# Global singletons loaded once at startup
eye_model = EyeDrowsinessModel()
yawn_model = YawnDetectionModel()
