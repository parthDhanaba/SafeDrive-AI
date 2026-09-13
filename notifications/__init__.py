"""
SafeDrive-AI Notifications Subsystem
Provider-independent alert architecture supporting Mock SMS/WhatsApp (local development)
and production Meta WhatsApp Cloud API / Twilio SMS without mandatory paid dependencies.
"""
from notifications.base import (
    NotificationResult,
    NotificationProvider,
    format_emergency_message,
    format_whatsapp_emergency_message,
    format_whatsapp_location_update_message
)
from notifications.mock_provider import (
    MockSMSProvider,
    MockWhatsAppProvider
)
from notifications.sms_provider import (
    TwilioSMSProvider
)
from notifications.whatsapp_provider import (
    MetaCloudWhatsAppProvider
)
from notifications.manager import (
    get_active_provider,
    get_active_whatsapp_provider,
    send_emergency_notification,
    send_whatsapp_family_alert
)

__all__ = [
    "NotificationResult",
    "NotificationProvider",
    "format_emergency_message",
    "format_whatsapp_emergency_message",
    "format_whatsapp_location_update_message",
    "MockSMSProvider",
    "MockWhatsAppProvider",
    "TwilioSMSProvider",
    "MetaCloudWhatsAppProvider",
    "get_active_provider",
    "get_active_whatsapp_provider",
    "send_emergency_notification",
    "send_whatsapp_family_alert"
]
