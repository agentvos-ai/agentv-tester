import logging
import os
import sqlite3
from typing import List, Dict, Any, Tuple
from core.registry import register_shim
from shims import BaseShim

logger = logging.getLogger(__name__)


@register_shim("notification")
class NotificationShim(BaseShim):
    """
    Industrial-grade Notification interface.
    Uses a local SQLite database for notification history and delivery tracking.
    """

    def __init__(self, seed: int = 42):
        self.db_path = os.path.abspath(".agent_workspace/db/notifications.db")
        super().__init__(seed)

    @property
    def name(self) -> str:
        return "notification"

    @property
    def description(self) -> str:
        return "Enterprise notification service for SMS, Push, and Webhook delivery."

    def setup(self) -> None:
        """Ensure database and tables exist."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sent_notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT,
                    recipient TEXT,
                    message TEXT,
                    status TEXT DEFAULT 'DELIVERED',
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def shutdown(self) -> None:
        """Cleanup the database file."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def reset(self) -> None:
        """Deterministic reset of the notification state."""
        self.shutdown()
        self.setup()

    def send_push(self, user_id: str, message: str) -> str:
        """Sends a push notification."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "INSERT INTO sent_notifications (type, recipient, message) VALUES (?, ?, ?)",
                ("PUSH", user_id, message),
            )
            conn.commit()
            return f"Push notification sent to '{user_id}'."
        finally:
            conn.close()

    def send_sms(self, phone: str, message: str) -> str:
        """Sends an SMS message."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "INSERT INTO sent_notifications (type, recipient, message) VALUES (?, ?, ?)",
                ("SMS", phone, message),
            )
            conn.commit()
            return f"SMS sent to '{phone}'."
        finally:
            conn.close()

    def send_webhook(self, url: str, payload: Dict[str, Any]) -> str:
        """Sends a webhook notification."""
        import json

        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "INSERT INTO sent_notifications (type, recipient, message) VALUES (?, ?, ?)",
                ("WEBHOOK", url, json.dumps(payload)),
            )
            conn.commit()
            return f"Webhook sent to '{url}'."
        finally:
            conn.close()

    def list_sent(self) -> List[Dict[str, Any]]:
        """Retrieves history of sent notifications."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT type, recipient, message, status, timestamp FROM sent_notifications ORDER BY timestamp DESC"
            )
            return [
                {
                    "type": row[0],
                    "recipient": row[1],
                    "message": row[2],
                    "status": row[3],
                    "timestamp": row[4],
                }
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()

    def get_tool_specs(self) -> List[Tuple[str, Any, str]]:
        return [
            ("notify_push", self.send_push, "Send a push notification."),
            ("notify_sms", self.send_sms, "Send an SMS message."),
            ("notify_webhook", self.send_webhook, "Trigger an external webhook."),
            ("notify_list", self.list_sent, "List notification history."),
        ]
