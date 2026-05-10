import logging
logger = logging.getLogger(__name__)

from typing import List, Dict, Any, Tuple
from core.registry import register_shim
from shims import BaseShim

@register_shim("notification")

class NotificationShim(BaseShim):
    """
    Multi-channel notification service simulator.
    Supports SMS, Push notifications, and Webhooks.
    """

    @property
    def name(self) -> str:
        return "notification"

    @property
    def description(self) -> str:
        return "Enterprise notification service for multi-channel alerting."

    def reset(self) -> None:
        """Deterministic reset of the notification history."""
        self._state["sent_log"]: List[Dict[str, str]] = []

    def send_sms(self, phone: str, message: str) -> str:
        """Sends an SMS message."""
        self._state["sent_log"].append({"channel": "SMS", "to": phone, "msg": message})
        return f"SMS sent to {phone}."

    def send_push(self, user_id: str, message: str) -> str:
        """Sends a push notification to a user's device."""
        self._state["sent_log"].append({"channel": "PUSH", "to": user_id, "msg": message})
        return f"Push notification sent to {user_id}."

    def send_webhook(self, url: str, payload: Dict[str, Any]) -> str:
        """Triggers a webhook alert."""
        self._state["sent_log"].append({"channel": "WEBHOOK", "to": url, "msg": str(payload)})
        return f"Webhook triggered for {url}."

    def list_sent(self) -> List[Dict[str, str]]:
        """Retrieves the history of sent notifications."""
        return self._state["sent_log"]

    def get_tool_specs(self) -> List[Tuple[str, Any, str]]:
        return [
            ("notify_sms", self.send_sms, "Send an SMS message to a mobile device."),
            ("notify_push", self.send_push, "Send a push notification to a user."),
            ("notify_webhook", self.send_webhook, "Trigger a webhook with a data payload."),
            ("notify_list", self.list_sent, "View the log of recently sent notifications.")
        ]