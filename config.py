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

# Models directory and model file paths
MODELS_DIR = BASE_DIR / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)
EYE_MODEL_PATH = MODELS_DIR / "eye_drowsiness_model.keras"
YAWN_MODEL_PATH = MODELS_DIR / "yawn_model.keras"

# Load environment variables
load_dotenv(BASE_DIR / ".env")

# AI Model Detection Thresholds (Configurable)
EYE_MODEL_THRESHOLD = float(os.getenv("EYE_MODEL_THRESHOLD", "0.50"))      # Prob < 0.50 -> Closed eyes (Class 0: closed, 1: open)
YAWN_MODEL_THRESHOLD = float(os.getenv("YAWN_MODEL_THRESHOLD", "0.40"))    # Prob >= 0.40 -> Yawn (Class 0: no_yawn, 1: yawn)
AI_DETECTION_MODE = os.getenv("AI_DETECTION_MODE", "hybrid").strip().lower() # "hybrid", "model", or "geometric"

# Detection Thresholds (Preserve verified values)
EAR_THRESHOLD = float(os.getenv("EAR_THRESHOLD", "0.22"))              # Eye Aspect Ratio threshold for eye closure
CLOSED_FRAMES_THRESHOLD = int(os.getenv("CLOSED_FRAMES_THRESHOLD", "20"))      # Sustained frames below threshold to trigger drowsiness (~1.5s at real-time FPS)
MAR_THRESHOLD = float(os.getenv("MAR_THRESHOLD", "0.50"))              # Mouth Aspect Ratio threshold for yawn detection
YAWN_MIN_FRAMES = 8               # Minimum consecutive frames mouth must be open to register yawn
YAWN_LIMIT = 3                    # Number of yawns to trigger danger warning
YAWN_COOLDOWN_FRAMES = 15         # Cooldown frames after a registered yawn

# Emergency & Response Parameters
RESPONSE_TIMEOUT_SECONDS = 10     # Driver acknowledgement timeout before SOS activation

# Camera and Window Configuration
CAMERA_INDEX = 0
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
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

# WhatsApp Family Alert Configuration (Defaults to mock provider for local development)
WHATSAPP_ENABLED = os.getenv("WHATSAPP_ENABLED", "true").strip().lower() in ("1", "true", "yes")
WHATSAPP_PROVIDER = os.getenv("WHATSAPP_PROVIDER", "mock").strip().lower()
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "").strip()
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "").strip()
WHATSAPP_RECIPIENT_PHONE = os.getenv("WHATSAPP_RECIPIENT_PHONE", "").strip()
WHATSAPP_API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v20.0").strip()
WHATSAPP_LOCATION_UPDATE_INTERVAL = int(os.getenv("WHATSAPP_LOCATION_UPDATE_INTERVAL", "60").strip() or 60)

