import logging


from typing import List, Dict, Any, Tuple
from core.registry import register_shim
from core.errors import ShimError
from shims import BaseShim

logger = logging.getLogger(__name__)


@register_shim("email")
class EmailShim(BaseShim):
    """
    Corporate email service simulator.
    Supports sending, listing, reading, and searching emails.
    """

    @property
    def name(self) -> str:
        return "email"

    @property
    def description(self) -> str:
        return "Corporate email service for internal and external communication."

    def reset(self) -> None:
        """Deterministic reset of the email state."""
        self._state["inbox"] = [
            {
                "id": "msg_1",
                "from": "boss@corp.com",
                "subject": "Quarterly Report",
                "body": "Please review the attached...",
            },
            {
                "id": "msg_2",
                "from": "hr@corp.com",
                "subject": "Benefits Update",
                "body": "New dental plan details...",
            },
        ]
        self._state["sent"] = []

    def send_email(self, recipient: str, subject: str, body: str) -> str:
        """Sends an email message."""
        self._state["sent"].append({"to": recipient, "subject": subject, "body": body})
        return f"Email sent successfully to '{recipient}'."

    def list_inbox(self) -> List[Dict[str, str]]:
        """Lists all emails in the inbox."""
        return [
            {"id": m["id"], "from": m["from"], "subject": m["subject"]}
            for m in self._state["inbox"]
        ]

    def read_email(self, msg_id: str) -> Dict[str, str]:
        """Reads the full content of a specific email."""
        for msg in self._state["inbox"]:
            if msg["id"] == msg_id:
                return msg
        raise ShimError(f"Email ID '{msg_id}' not found.")

    def search_emails(self, query: str) -> List[Dict[str, str]]:
        """Searches the inbox for emails matching a query."""
        results = []
        for m in self._state["inbox"]:
            if (
                query.lower() in m["subject"].lower()
                or query.lower() in m["body"].lower()
            ):
                results.append(
                    {"id": m["id"], "from": m["from"], "subject": m["subject"]}
                )
        return results

    def get_tool_specs(self) -> List[Tuple[str, Any, str]]:
        return [
            ("email_send", self.send_email, "Send an email message."),
            ("email_list", self.list_inbox, "List all messages in the inbox."),
            ("email_read", self.read_email, "Read the full content of an email."),
            (
                "email_search",
                self.search_emails,
                "Search the inbox for specific emails.",
            ),
        ]
