"""
SafeDrive-AI Mock Notification Providers
Enables full development, automated testing, and offline demonstrations
without requiring paid subscriptions, SIM cards, or third-party API tokens.
"""
from datetime import datetime
from typing import Optional, Dict, Any
from notifications.base import NotificationProvider, NotificationResult
from logger import logger
from config import DEFAULT_EMERGENCY_PHONE, WHATSAPP_RECIPIENT_PHONE


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
        sim_id = f"SIM-SMS-{int(datetime.now().timestamp())}"
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


class MockWhatsAppProvider(NotificationProvider):
    """
    Simulated zero-cost WhatsApp provider for local development and testing.
    Outputs the standardized prompt verification log and logs delivery details.
    Never sends real network requests or requires Meta Business verification.
    """

    def is_configured(self) -> bool:
        return True

    def send(self, recipient: str, message: str, meta: Optional[Dict[str, Any]] = None) -> NotificationResult:
        sim_id = f"SIM-WA-{int(datetime.now().timestamp())}"
        target = recipient or WHATSAPP_RECIPIENT_PHONE or DEFAULT_EMERGENCY_PHONE or "Family Contact"

        maps_url = "Unavailable"
        photo_ref = "None"
        if meta:
            maps_url = meta.get("maps_url", maps_url)
            photo_ref = meta.get("photo_path", photo_ref)

        # Standardized prompt verification block
        print(
            f"\n[MOCK WHATSAPP]\n"
            f"Emergency alert sent to: {target}\n"
            f"Location: {maps_url}\n"
            f"Photo: {photo_ref}\n"
        )

        logger.info(
            f"\n"
            f"================== [MOCK WHATSAPP FAMILY ALERT] ==================\n"
            f"Recipient : {target}\n"
            f"Provider  : MockWhatsAppProvider (Simulated Mode)\n"
            f"Status    : SIMULATED (Zero-Cost WhatsApp Mode)\n"
            f"Location  : {maps_url}\n"
            f"Photo     : {photo_ref}\n"
            f"----------------------------------------------------------------\n"
            f"{message}\n"
            f"================================================================="
        )

        return NotificationResult(
            success=True,
            status="SIMULATED",
            provider_name="Mock WhatsApp Provider",
            message_text=message,
            recipient=target,
            message_id=sim_id,
            meta=meta
        )
