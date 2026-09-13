"""
SafeDrive-AI Notification Subsystem
Provider-independent alert architecture supporting Mock SMS (local development/testing)
and optional real SMS providers (Twilio) without mandatory paid dependencies.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from config import (
    USE_MOCK_SMS,
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_FROM_NUMBER,
    DEFAULT_EMERGENCY_PHONE
)
from logger import logger
from database import save_emergency_alert


@dataclass
class NotificationResult:
    success: bool
    status: str             # "SIMULATED", "SENT", "FAILED", "SKIPPED"
    provider_name: str
    message_text: str
    recipient: str
    message_id: Optional[str] = None
    error: Optional[str] = None


def format_emergency_message(
    driver_name: str,
    vehicle_number: str,
    reason: str,
    maps_url: str,
    accuracy: Optional[float] = None,
    photo_path: Optional[Path] = None,
    timestamp: Optional[str] = None
) -> str:
    """Constructs standard SafeDrive-AI emergency alert message text."""
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


class NotificationProvider(ABC):
    """Abstract interface for all emergency notification providers."""

    @abstractmethod
    def is_configured(self) -> bool:
        """Returns True if provider has required credentials/endpoints."""
        pass

    @abstractmethod
    def send(self, recipient: str, message: str, meta: Optional[Dict[str, Any]] = None) -> NotificationResult:
        """Dispatches or simulates notification delivery."""
        pass


class MockSMSProvider(NotificationProvider):
    """
    Default testing and development SMS provider.
    Generates full emergency message, logs to console/file,
    and returns explicit 'SIMULATED' status.
    Never falsely reports 'DELIVERED'.
    """

    def is_configured(self) -> bool:
        return True

    def send(self, recipient: str, message: str, meta: Optional[Dict[str, Any]] = None) -> NotificationResult:
        sim_id = f"SIM-{int(datetime.now().timestamp())}"
        target = recipient or DEFAULT_EMERGENCY_PHONE or "Default Contact"

        logger.info(
            f"\n"
            f"================== [MOCK SMS ALERT DISPATCHED] ==================\n"
            f"Recipient : {target}\n"
            f"Provider  : MockSMSProvider (Simulated Mode)\n"
            f"Status    : SIMULATED (No paid SMS required)\n"
            f"----------------------------------------------------------------\n"
            f"{message}\n"
            f"================================================================="
        )

        return NotificationResult(
            success=True,
            status="SIMULATED",
            provider_name="Mock SMS Provider",
            message_text=message,
            recipient=target,
            message_id=sim_id
        )


class TwilioSMSProvider(NotificationProvider):
    """
    Optional Twilio SMS provider.
    Only active if all credentials are set in environment.
    Never prints auth tokens and gracefully handles trial restrictions.
    """

    def __init__(self):
        self._sid = TWILIO_ACCOUNT_SID
        self._token = TWILIO_AUTH_TOKEN
        self._from_number = TWILIO_FROM_NUMBER

    def is_configured(self) -> bool:
        return bool(self._sid and self._token and self._from_number)

    def send(self, recipient: str, message: str, meta: Optional[Dict[str, Any]] = None) -> NotificationResult:
        target = recipient or DEFAULT_EMERGENCY_PHONE
        if not target:
            return NotificationResult(
                success=False,
                status="FAILED",
                provider_name="Twilio SMS",
                message_text=message,
                recipient="Unknown",
                error="No recipient phone number configured."
            )

        try:
            from twilio.rest import Client
            client = Client(self._sid, self._token)
            sent = client.messages.create(
                body=message,
                from_=self._from_number,
                to=target
            )
            logger.info(f"Twilio SMS dispatched with SID: {sent.sid}")
            return NotificationResult(
                success=True,
                status="SENT",
                provider_name="Twilio SMS",
                message_text=message,
                recipient=target,
                message_id=sent.sid
            )
        except Exception as e:
            err_msg = str(e)
            logger.warning(f"Twilio SMS delivery failed: {err_msg}")
            return NotificationResult(
                success=False,
                status="FAILED",
                provider_name="Twilio SMS",
                message_text=message,
                recipient=target,
                error=err_msg
            )


def get_active_provider() -> NotificationProvider:
    """
    Selects the active notification provider.
    Uses MockSMSProvider by default unless USE_MOCK_SMS is explicitly disabled
    and Twilio credentials are fully supplied.
    """
    if not USE_MOCK_SMS:
        twilio = TwilioSMSProvider()
        if twilio.is_configured():
            return twilio
    return MockSMSProvider()


def send_emergency_notification(
    driver: Optional[Dict[str, Any]],
    vehicle: Optional[Dict[str, Any]],
    reason: str,
    location_obj,
    photo_path: Optional[Path] = None,
    event_id: Optional[int] = None
) -> NotificationResult:
    """
    High-level emergency notification dispatcher.
    Coordinates message formatting, provider dispatch, and database logging.
    """
    driver_name = driver.get("name", "Unknown Driver") if driver else "Unknown Driver"
    driver_contact_name = driver.get("emergency_contact_name", "Emergency Contact") if driver else "Emergency Contact"
    recipient_phone = (
        driver.get("emergency_contact_phone")
        or DEFAULT_EMERGENCY_PHONE
        or "Simulated Contact"
    ) if driver else (DEFAULT_EMERGENCY_PHONE or "Simulated Contact")

    vehicle_num = vehicle.get("vehicle_number", "Unknown Vehicle") if vehicle else "Unknown Vehicle"

    maps_url = getattr(location_obj, "maps_url", "Unavailable")
    accuracy = getattr(location_obj, "accuracy", None)
    lat = getattr(location_obj, "latitude", None)
    lon = getattr(location_obj, "longitude", None)

    # Build standard message
    message = format_emergency_message(
        driver_name=driver_name,
        vehicle_number=vehicle_num,
        reason=reason,
        maps_url=maps_url,
        accuracy=accuracy,
        photo_path=photo_path
    )

    provider = get_active_provider()
    result = provider.send(recipient=recipient_phone, message=message)

    # Persist alert record to SQLite
    try:
        save_emergency_alert(
            event_id=event_id,
            recipient_type="EMERGENCY_CONTACT",
            recipient_name=driver_contact_name,
            recipient_phone=recipient_phone,
            message=message,
            latitude=lat,
            longitude=lon,
            location_accuracy=accuracy,
            photo_path=str(photo_path) if photo_path else None,
            delivery_status=result.status
        )
    except Exception as e:
        logger.error(f"Failed to record emergency alert in database: {e}")

    return result
