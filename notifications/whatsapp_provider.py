"""
SafeDrive-AI Official Meta WhatsApp Cloud API Provider
Communicates directly with the official Meta WhatsApp Business Cloud API.
Adheres strictly to official API practices with token redaction and network timeouts.
Does NOT use unofficial web scraping, Selenium, or browser automation.
"""
import re
from typing import Optional, Dict, Any
from notifications.base import NotificationProvider, NotificationResult
from logger import logger
from config import (
    WHATSAPP_ACCESS_TOKEN,
    WHATSAPP_PHONE_NUMBER_ID,
    WHATSAPP_API_VERSION,
    WHATSAPP_RECIPIENT_PHONE
)


class MetaCloudWhatsAppProvider(NotificationProvider):
    """
    Official WhatsApp Cloud API Provider (Meta Business Platform).
    Docs: https://developers.facebook.com/docs/whatsapp/cloud-api
    """

    def __init__(
        self,
        access_token: Optional[str] = None,
        phone_number_id: Optional[str] = None,
        api_version: Optional[str] = None
    ):
        self._token = access_token or WHATSAPP_ACCESS_TOKEN
        self._phone_id = phone_number_id or WHATSAPP_PHONE_NUMBER_ID
        self._api_version = api_version or WHATSAPP_API_VERSION or "v20.0"

    def is_configured(self) -> bool:
        """Verifies required Meta Cloud API credentials exist."""
        return bool(self._token and self._phone_id)

    def _sanitize_recipient(self, raw_phone: str) -> str:
        """Removes spaces, hyphens, and parenthesis, leaving digits."""
        if not raw_phone:
            return ""
        digits = re.sub(r"[^\d]", "", raw_phone)
        return digits

    def _redact_token(self, text: str) -> str:
        """Sanitizes text to prevent accidental exposure of access token in logs."""
        if self._token and self._token in text:
            return text.replace(self._token, "[REDACTED_ACCESS_TOKEN]")
        return text

    def send(self, recipient: str, message: str, meta: Optional[Dict[str, Any]] = None) -> NotificationResult:
        target = recipient or WHATSAPP_RECIPIENT_PHONE
        cleaned_target = self._sanitize_recipient(target)

        if not self.is_configured():
            err_msg = "Meta WhatsApp Cloud API credentials missing (WHATSAPP_ACCESS_TOKEN or WHATSAPP_PHONE_NUMBER_ID)."
            logger.warning(err_msg)
            return NotificationResult(
                success=False,
                status="FAILED",
                provider_name="Meta WhatsApp Cloud API",
                message_text=message,
                recipient=target or "Unconfigured",
                error=err_msg
            )

        if not cleaned_target:
            err_msg = "No valid recipient phone number provided for WhatsApp alert."
            logger.warning(err_msg)
            return NotificationResult(
                success=False,
                status="FAILED",
                provider_name="Meta WhatsApp Cloud API",
                message_text=message,
                recipient="Invalid",
                error=err_msg
            )

        url = f"https://graph.facebook.com/{self._api_version}/{self._phone_id}/messages"
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": cleaned_target,
            "type": "text",
            "text": {
                "preview_url": True,
                "body": message
            }
        }

        try:
            import requests
            response = requests.post(url, json=payload, headers=headers, timeout=8.0)
            status_code = response.status_code

            if status_code in (200, 201):
                res_data = response.json()
                msg_id = None
                messages = res_data.get("messages", [])
                if messages and isinstance(messages, list):
                    msg_id = messages[0].get("id")

                logger.info(f"WhatsApp Cloud API message dispatched successfully to {cleaned_target} (ID: {msg_id})")
                return NotificationResult(
                    success=True,
                    status="SENT",
                    provider_name="Meta WhatsApp Cloud API",
                    message_text=message,
                    recipient=cleaned_target,
                    message_id=msg_id,
                    meta=meta
                )
            else:
                raw_err = response.text
                sanitized_err = self._redact_token(raw_err)
                logger.warning(f"WhatsApp Cloud API dispatch failed (HTTP {status_code}): {sanitized_err}")
                return NotificationResult(
                    success=False,
                    status="FAILED",
                    provider_name="Meta WhatsApp Cloud API",
                    message_text=message,
                    recipient=cleaned_target,
                    error=f"HTTP {status_code}: {sanitized_err}",
                    meta=meta
                )

        except Exception as e:
            sanitized_err = self._redact_token(str(e))
            logger.error(f"WhatsApp Cloud API network exception: {sanitized_err}")
            return NotificationResult(
                success=False,
                status="FAILED",
                provider_name="Meta WhatsApp Cloud API",
                message_text=message,
                recipient=cleaned_target,
                error=sanitized_err,
                meta=meta
            )
