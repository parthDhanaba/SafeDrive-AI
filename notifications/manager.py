"""
SafeDrive-AI Notification Manager
Coordinates alert dispatch across SMS and WhatsApp channels,
manages family contact resolution, and records delivery audits into SQLite.
"""
from typing import Optional, Dict, Any
from pathlib import Path

from config import (
    USE_MOCK_SMS,
    WHATSAPP_ENABLED,
    WHATSAPP_PROVIDER,
    DEFAULT_EMERGENCY_PHONE,
    WHATSAPP_RECIPIENT_PHONE
)
from logger import logger
from database import save_emergency_alert
from notifications.base import (
    NotificationResult,
    NotificationProvider,
    format_emergency_message,
    format_whatsapp_emergency_message,
    format_whatsapp_location_update_message
)
from notifications.mock_provider import MockSMSProvider, MockWhatsAppProvider
from notifications.sms_provider import TwilioSMSProvider
from notifications.whatsapp_provider import MetaCloudWhatsAppProvider


def get_active_provider() -> NotificationProvider:
    """
    Selects the active SMS notification provider.
    Uses MockSMSProvider by default unless USE_MOCK_SMS is explicitly false
    and Twilio credentials are configured.
    """
    if not USE_MOCK_SMS:
        twilio = TwilioSMSProvider()
        if twilio.is_configured():
            return twilio
    return MockSMSProvider()


def get_active_whatsapp_provider() -> NotificationProvider:
    """
    Selects the active WhatsApp alert provider.
    Defaults to MockWhatsAppProvider (zero cost) unless 'meta_cloud'
    is specified with valid access token and phone number ID.
    """
    if WHATSAPP_PROVIDER == "meta_cloud":
        meta_provider = MetaCloudWhatsAppProvider()
        if meta_provider.is_configured():
            return meta_provider
        logger.warning("Meta Cloud WhatsApp provider requested but credentials unconfigured. Falling back to MockWhatsAppProvider.")

    return MockWhatsAppProvider()


def send_whatsapp_family_alert(
    driver: Optional[Dict[str, Any]],
    vehicle: Optional[Dict[str, Any]],
    location_obj,
    photo_path: Optional[Path] = None,
    event_id: Optional[int] = None,
    is_update: bool = False
) -> NotificationResult:
    """
    Dispatches a LIVE LOCATION emergency alert via WhatsApp to the driver's family contact.
    Retrieves family emergency phone and name from SQLite driver record.
    """
    if not WHATSAPP_ENABLED:
        logger.info("WhatsApp emergency family alert skipped (WHATSAPP_ENABLED is false in configuration).")
        return NotificationResult(
            success=True,
            status="SKIPPED",
            provider_name="Disabled",
            message_text="WhatsApp disabled by configuration.",
            recipient="N/A"
        )

    driver_name = driver.get("name", "Primary Driver") if driver else "Primary Driver"
    family_contact_name = (
        (driver.get("emergency_contact_name") if driver else None)
        or "Family Emergency Contact"
    )
    family_contact_phone = (
        (driver.get("emergency_contact_phone") if driver else None)
        or WHATSAPP_RECIPIENT_PHONE
        or DEFAULT_EMERGENCY_PHONE
        or "Simulated Family Contact"
    )
    vehicle_num = vehicle.get("vehicle_number", "Vehicle") if vehicle else "Vehicle"

    maps_url = getattr(location_obj, "maps_url", "Unavailable")
    accuracy = getattr(location_obj, "accuracy", None)
    lat = getattr(location_obj, "latitude", None)
    lon = getattr(location_obj, "longitude", None)
    loc_available = getattr(location_obj, "is_available", False)

    # Format message
    if is_update:
        message = format_whatsapp_location_update_message(
            driver_name=driver_name,
            vehicle_number=vehicle_num,
            maps_url=maps_url,
            accuracy=accuracy
        )
    else:
        message = format_whatsapp_emergency_message(
            driver_name=driver_name,
            vehicle_number=vehicle_num,
            maps_url=maps_url,
            photo_path=photo_path,
            accuracy=accuracy
        )

    meta = {
        "maps_url": maps_url,
        "photo_path": str(photo_path) if photo_path else "None",
        "accuracy": accuracy,
        "is_update": is_update
    }

    provider = get_active_whatsapp_provider()
    result = provider.send(recipient=family_contact_phone, message=message, meta=meta)

    # Persist alert record into SQLite
    try:
        save_emergency_alert(
            event_id=event_id,
            recipient_type="FAMILY",
            recipient_name=family_contact_name,
            recipient_phone=family_contact_phone,
            message=message,
            latitude=lat,
            longitude=lon,
            location_accuracy=accuracy,
            photo_path=str(photo_path) if photo_path else None,
            delivery_status=result.status,
            whatsapp_attempted=1,
            whatsapp_succeeded=1 if result.success and result.status in ("SENT", "SIMULATED") else 0,
            location_available=1 if loc_available else 0,
            photo_captured=1 if photo_path else 0,
            channel="WHATSAPP"
        )
    except Exception as e:
        logger.error(f"Failed to record WhatsApp emergency alert in database: {e}")

    return result


def send_emergency_notification(
    driver: Optional[Dict[str, Any]],
    vehicle: Optional[Dict[str, Any]],
    reason: str,
    location_obj,
    photo_path: Optional[Path] = None,
    event_id: Optional[int] = None
) -> NotificationResult:
    """
    Standard emergency notification dispatcher for SMS channels.
    Maintained for full backward compatibility.
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
    loc_available = getattr(location_obj, "is_available", False)

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
            delivery_status=result.status,
            whatsapp_attempted=0,
            whatsapp_succeeded=0,
            location_available=1 if loc_available else 0,
            photo_captured=1 if photo_path else 0,
            channel="SMS"
        )
    except Exception as e:
        logger.error(f"Failed to record emergency SMS alert in database: {e}")

    return result
