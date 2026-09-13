"""
SafeDrive-AI SMS Dispatcher
Backward-compatible wrapper integrating with the provider-independent notifications system.
Operates with MockSMSProvider by default and safely falls back without paid requirements.
"""
from typing import Optional, Dict, Any
from notifications import get_active_provider, NotificationResult
from config import DEFAULT_EMERGENCY_PHONE
from logger import logger


def send_sms(message: str, recipient: Optional[str] = None) -> Dict[str, Any]:
    """
    Sends an SMS message using the active provider (Mock or Twilio).
    Returns dict containing status and message/simulated ID.
    Never throws unhandled exceptions if credentials or services are unavailable.
    """
    target = recipient or DEFAULT_EMERGENCY_PHONE or "Default Contact"
    provider = get_active_provider()

    result: NotificationResult = provider.send(recipient=target, message=message)

    return {
        "sid": result.message_id or "NONE",
        "status": result.status,
        "provider": result.provider_name,
        "success": result.success,
        "error": result.error
    }