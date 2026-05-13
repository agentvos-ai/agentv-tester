import logging
import os
import sqlite3
from typing import List, Dict, Any, Tuple
from core.registry import register_shim
from core.errors import ShimError
from shims import BaseShim

logger = logging.getLogger(__name__)


@register_shim("email")
class EmailShim(BaseShim):
    """
    Industrial-grade Email interface.
    Uses a local SQLite database for message persistence and auditability.
    """

    def __init__(self, seed: int = 42):
        self.db_path = os.path.abspath(".agent_workspace/db/email.db")
        super().__init__(seed)

    @property
    def name(self) -> str:
        return "email"

    @property
    def description(self) -> str:
        return "Enterprise email service for managing inboxes and sending messages."

    def setup(self) -> None:
        """Ensure database and tables exist."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender TEXT,
                    recipient TEXT,
                    subject TEXT,
                    body TEXT,
                    folder TEXT,
                    is_read INTEGER DEFAULT 0,
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
        """Deterministic reset of the email state."""
        self.shutdown()
        self.setup()

        # Seed default messages
        self.send_email(
            "hr@enterprise.com",
            "agent@enterprise.com",
            "Welcome",
            "Welcome to the team.",
        )

    def send_email(self, *args, **kwargs) -> str:
        """
        Sends an email. Supports multiple signatures:
        1. (recipient, subject, body)
        2. (sender, recipient, subject, body)
        """
        if len(args) == 4:
            sender, recipient, subject, body = args
        elif len(args) == 3:
            recipient, subject, body = args
            sender = kwargs.get("sender", "agent@enterprise.com")
        else:
            # Fallback to keyword args if any
            sender = kwargs.get("sender", "agent@enterprise.com")
            recipient = kwargs.get("recipient")
            subject = kwargs.get("subject")
            body = kwargs.get("body")

        if not recipient or not subject or not body:
            raise ShimError("Missing required email fields (recipient, subject, body).")

        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "INSERT INTO messages (sender, recipient, subject, body, folder) VALUES (?, ?, ?, ?, ?)",
                (sender, recipient, subject, body, "SENT"),
            )
            # Also simulate receiving if recipient is local
            if recipient.endswith("@enterprise.com") or recipient.endswith("@corp.com"):
                conn.execute(
                    "INSERT INTO messages (sender, recipient, subject, body, folder) VALUES (?, ?, ?, ?, ?)",
                    (sender, recipient, subject, body, "INBOX"),
                )
            conn.commit()
            return f"Email sent to {recipient}."
        except Exception as e:
            raise ShimError(f"Failed to send email: {str(e)}")
        finally:
            conn.close()

    def search_emails(self, query: str) -> List[Dict[str, Any]]:
        """Searches the mailbox for messages matching a query."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT id, sender, recipient, subject, body, timestamp FROM messages "
                "WHERE subject LIKE ? OR body LIKE ? ORDER BY timestamp DESC",
                (f"%{query}%", f"%{query}%"),
            )
            return [
                {
                    "id": str(row[0]),
                    "from": row[1],
                    "to": row[2],
                    "subject": row[3],
                    "body": row[4],
                    "timestamp": row[5],
                }
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()

    def list_inbox(
        self, recipient: str = "agent@enterprise.com"
    ) -> List[Dict[str, Any]]:
        """Lists all messages in the inbox for a specific recipient."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT id, sender, subject, body, timestamp, is_read FROM messages WHERE recipient = ? AND folder = 'INBOX' ORDER BY timestamp DESC",
                (recipient,),
            )
            return [
                {
                    "id": str(row[0]),
                    "from": row[1],
                    "subject": row[2],
                    "body": row[3],
                    "timestamp": row[4],
                    "status": "READ" if row[5] else "UNREAD",
                }
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()

    def read_email(self, msg_id: str) -> Dict[str, Any]:
        """Reads a specific email and marks it as read."""
        # Support 'msg_1' format from legacy tests
        db_id = msg_id.replace("msg_", "")

        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT id, sender, recipient, subject, body, timestamp FROM messages WHERE id = ?",
                (db_id,),
            )
            row = cursor.fetchone()
            if not row:
                raise ShimError(f"Email ID '{msg_id}' not found.")

            conn.execute("UPDATE messages SET is_read = 1 WHERE id = ?", (msg_id,))
            conn.commit()

            return {
                "id": str(row[0]),
                "from": row[1],
                "to": row[2],
                "subject": row[3],
                "body": row[4],
                "timestamp": row[5],
            }
        finally:
            conn.close()

    def get_tool_specs(self) -> List[Tuple[str, Any, str]]:
        return [
            ("email_send", self.send_email, "Send an enterprise email."),
            ("email_list", self.list_inbox, "List messages in an inbox."),
            ("email_read", self.read_email, "Read a specific email message."),
            ("email_search", self.search_emails, "Search for specific emails."),
        ]
