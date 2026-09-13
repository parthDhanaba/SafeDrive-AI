"""
SafeDrive-AI SMS Notification Providers
"""
from typing import Optional, Dict, Any
from notifications.base import NotificationProvider, NotificationResult
from logger import logger
from config import (
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_FROM_NUMBER,
    DEFAULT_EMERGENCY_PHONE
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
