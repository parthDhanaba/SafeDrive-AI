"""
SafeDrive-AI Common Utilities
"""
import math
from datetime import datetime
from typing import Tuple, Optional


def euclidean_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """Calculates 2D Euclidean distance between two points."""
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


def get_iso_timestamp(dt: Optional[datetime] = None) -> str:
    """Returns ISO 8601 formatted timestamp string."""
    if dt is None:
        dt = datetime.now()
    return dt.isoformat()


def get_display_timestamp(dt: Optional[datetime] = None) -> str:
    """Returns human-friendly date and time string."""
    if dt is None:
        dt = datetime.now()
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def mask_phone_number(phone: Optional[str]) -> str:
    """Masks a phone number for privacy display (e.g., '+1 ••• ••• 4567')."""
    if not phone:
        return "N/A"
    clean = str(phone).strip()
    if len(clean) <= 4:
        return "****"
    return clean[:3] + " ••• " + clean[-4:]
