"""
SafeDrive-AI Emergency Photo Capture Subsystem
Captures a single local snapshot upon SOS emergency activation.
Ensures verified disk writing, privacy preservation, and error resilience.
"""
from pathlib import Path
from datetime import datetime
from typing import Optional
import cv2
from config import CAPTURE_DIR
from logger import logger


def capture_emergency_photo(frame) -> Optional[Path]:
    """
    Saves a single snapshot frame to the local emergency_captures directory.
    Returns Path to file if successful, or None on write failure.
    Does NOT upload photos externally.
    """
    if frame is None or getattr(frame, "size", 0) == 0:
        logger.warning("Emergency photo capture failed: Input frame is empty or invalid.")
        return None

    try:
        CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        photo_path = CAPTURE_DIR / f"emergency_{timestamp}.jpg"

        success = cv2.imwrite(str(photo_path), frame)
        if success and photo_path.exists():
            logger.info(f"Emergency snapshot successfully captured and saved: {photo_path.name}")
            return photo_path
        else:
            logger.error(f"cv2.imwrite returned False when saving emergency photo: {photo_path}")
            return None

    except Exception as e:
        logger.error(f"Unexpected error during emergency photo capture: {e}")
        return None