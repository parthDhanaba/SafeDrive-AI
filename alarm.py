"""
SafeDrive-AI Audible Alarm Subsystem
Handles non-blocking emergency and warning audio playback via Pygame Mixer.
Safely falls back if audio devices or sound files are unavailable.
"""
from typing import Optional
from pathlib import Path
from config import ALARM_SOUND_PATH
from logger import logger


class AlarmManager:
    def __init__(self, sound_path: Optional[Path] = None):
        self.sound_path = sound_path or ALARM_SOUND_PATH
        self.sound = None
        self.playing = False
        self.initialized = False

        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init()

            if Path(self.sound_path).exists():
                self.sound = pygame.mixer.Sound(str(self.sound_path))
                self.initialized = True
                logger.info(f"Alarm sound loaded successfully from {self.sound_path}")
            else:
                logger.warning(f"Alarm sound file not found at {self.sound_path}. Audible alerts will be visual only.")
        except Exception as e:
            logger.warning(f"Audio subsystem initialization failed: {e}. Audible alerts disabled.")
            self.initialized = False

    def play(self):
        """Plays the alarm sound in a continuous loop if not already playing."""
        if self.initialized and self.sound and not self.playing:
            try:
                self.sound.play(-1)
                self.playing = True
            except Exception as e:
                logger.error(f"Error playing alarm sound: {e}")
                self.playing = False
        elif not self.initialized:
            self.playing = True

    def stop(self):
        """Stops the alarm immediately."""
        if self.initialized and self.sound and self.playing:
            try:
                self.sound.stop()
            except Exception as e:
                logger.error(f"Error stopping alarm sound: {e}")
        self.playing = False

    def is_playing(self) -> bool:
        """Returns True if alarm is currently active."""
        return self.playing