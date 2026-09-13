"""
SafeDrive-AI Notifications Subsystem - Core Interfaces and Message Formatters
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path


@dataclass
class NotificationResult:
    """Standard delivery result across all notification channels and providers."""
    success: bool
    status: str             # "SIMULATED", "SENT", "FAILED", "SKIPPED"
    provider_name: str
    message_text: str
    recipient: str
    message_id: Optional[str] = None
    error: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


class NotificationProvider(ABC):
    """Abstract interface for all notification providers (SMS, WhatsApp, Webhooks)."""

    @abstractmethod
    def is_configured(self) -> bool:
        """Returns True if provider has required credentials and configuration."""
        pass

    @abstractmethod
    def send(self, recipient: str, message: str, meta: Optional[Dict[str, Any]] = None) -> NotificationResult:
        """Dispatches or simulates notification delivery."""
        pass


def format_emergency_message(
    driver_name: str,
    vehicle_number: str,
    reason: str,
    maps_url: str,
    accuracy: Optional[float] = None,
    photo_path: Optional[Path] = None,
    timestamp: Optional[str] = None
) -> str:
    """Constructs standard SafeDrive-AI emergency alert message text for SMS channels."""
    ts = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    acc_text = f"±{accuracy:.0f} meters" if accuracy is not None else "Unavailable"
    photo_ref = photo_path.name if photo_path else "Local capture unavailable"

    return (
        f"🚨 SAFEDRIVE-AI EMERGENCY ALERT\n\n"
        f"Driver:\n{driver_name or 'Unregistered Driver'}\n\n"
        f"Vehicle:\n{vehicle_number or 'Unknown Vehicle'}\n\n"
        f"Reason:\n{reason}\n\n"
        f"Emergency Status:\nSOS ACTIVATED\n\n"
        f"Emergency Location:\n{maps_url}\n\n"
        f"Location Accuracy:\n{acc_text}\n\n"
        f"Emergency Photo:\n{photo_ref}\n\n"
        f"Time:\n{ts}"
    )


def format_whatsapp_emergency_message(
    driver_name: str,
    vehicle_number: str,
    maps_url: str,
    photo_path: Optional[Path] = None,
    timestamp: Optional[str] = None,
    accuracy: Optional[float] = None
) -> str:
    """
    Constructs the official SafeDrive-AI WhatsApp emergency message for family contacts.
    Conforms strictly to project specification.
    """
    ts = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    photo_ref = photo_path.name if photo_path else "Local capture saved"
    acc_info = f" (Accuracy: ±{accuracy:.0f}m)" if accuracy is not None else ""

    return (
        "SAFE DRIVE-AI EMERGENCY ALERT\n\n"
        f"Driver: {driver_name or 'Primary Driver'}\n"
        f"Vehicle: {vehicle_number or 'Vehicle'}\n\n"
        "The system has detected a serious driver-safety emergency and the driver did not respond.\n\n"
        "LIVE LOCATION:\n"
        f"{maps_url}{acc_info}\n\n"
        "Time:\n"
        f"{ts}\n\n"
        "Emergency photo:\n"
        f"{photo_ref}\n\n"
        "Please contact the driver immediately."
    )


def format_whatsapp_location_update_message(
    driver_name: str,
    vehicle_number: str,
    maps_url: str,
    timestamp: Optional[str] = None,
    accuracy: Optional[float] = None
) -> str:
    """Constructs periodic location update message during sustained emergency mode."""
    ts = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    acc_info = f"±{accuracy:.0f} meters" if accuracy is not None else "Unavailable"

    return (
        "SAFE DRIVE-AI EMERGENCY ALERT [LOCATION UPDATE]\n\n"
        f"Driver: {driver_name or 'Primary Driver'}\n"
        f"Vehicle: {vehicle_number or 'Vehicle'}\n\n"
        "UPDATED LIVE LOCATION:\n"
        f"{maps_url}\n\n"
        "Location Accuracy:\n"
        f"{acc_info}\n\n"
        "Time:\n"
        f"{ts}\n\n"
        "Emergency mode remains ACTIVE. Driver has not yet acknowledged."
    )
