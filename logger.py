"""
SafeDrive-AI Logging Subsystem
Provides consistent, formatted logging to console and persistent log files.
"""
import logging
import sys
from pathlib import Path
from config import LOGS_DIR

_LOGGER_INITIALIZED = False


def setup_logger(name: str = "SafeDriveAI", level: int = logging.INFO) -> logging.Logger:
    """Configures and returns a logger instance with console and file handlers."""
    global _LOGGER_INITIALIZED
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not _LOGGER_INITIALIZED:
        formatter = logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # Console Handler with UTF-8 safety
        try:
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # Rotating File Handler
        try:
            log_file = LOGS_DIR / "safedrive.log"
            file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"Warning: Unable to create file logger: {e}", file=sys.stderr)

        _LOGGER_INITIALIZED = True

    return logger


logger = setup_logger()
