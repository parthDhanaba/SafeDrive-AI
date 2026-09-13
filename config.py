"""
SafeDrive-AI Central Configuration
Contains all thresholds, timing parameters, file paths, and environment settings.
"""
from pathlib import Path
import os
from dotenv import load_dotenv

# Base directories
BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
ALARM_SOUND_PATH = ASSETS_DIR / "alarm.mp3"
CAPTURE_DIR = BASE_DIR / "emergency_captures"
DATABASE_PATH = BASE_DIR / "safedrive.db"
LOGS_DIR = BASE_DIR / "logs"

# Ensure runtime directories exist
CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Load environment variables
load_dotenv(BASE_DIR / ".env")

# Detection Thresholds (Preserve verified values)
EAR_THRESHOLD = 0.22              # Eye Aspect Ratio threshold for eye closure
CLOSED_FRAMES_THRESHOLD = 45      # Sustained frames below threshold to trigger drowsiness
MAR_THRESHOLD = 0.50              # Mouth Aspect Ratio threshold for yawn detection
YAWN_MIN_FRAMES = 8               # Minimum consecutive frames mouth must be open to register yawn
YAWN_LIMIT = 3                    # Number of yawns to trigger danger warning
YAWN_COOLDOWN_FRAMES = 15         # Cooldown frames after a registered yawn

# Emergency & Response Parameters
RESPONSE_TIMEOUT_SECONDS = 10     # Driver acknowledgement timeout before SOS activation

# Camera and Window Configuration
CAMERA_INDEX = 0
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720
WINDOW_NAME = "SafeDrive AI - Driver Safety System"

# Application Metadata
APP_NAME = "SafeDrive AI"
APP_VERSION = "1.0.0"

# Optional External Credentials (Defaults to None if not provided)
USE_MOCK_SMS = os.getenv("USE_MOCK_SMS", "true").strip().lower() in ("1", "true", "yes")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "").strip()
DEFAULT_EMERGENCY_PHONE = os.getenv("EMERGENCY_PHONE_NUMBER", "").strip()

