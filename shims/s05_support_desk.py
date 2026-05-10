from typing import List, Dict, Any, Tuple
from core.registry import register_shim
from core.errors import ShimError
from shims import BaseShim

@register_shim("support_desk")
class SupportDeskShim(BaseShim):
    """
    Customer support ticketing system.
    Supports full ticket lifecycle.
    """

    @property
    def name(self) -> str:
        return "support_desk"

    @property
    def description(self) -> str:
        return "Enterprise ticketing system for managing customer support requests."

    def reset(self) -> None:
        """Deterministic reset of the support desk state."""
        self._state["tickets"]: Dict[str, Dict[str, Any]] = {}

    def create_ticket(self, title: str, description: str) -> str:
        """Creates a new support ticket."""
        tid = f"T-{len(self._state['tickets']) + 101}"
        self._state["tickets"][tid] = {
            "id": tid,
            "title": title,
            "description": description,
            "status": "OPEN",
            "history": []
        }
        return tid

    def update_ticket(self, ticket_id: str, update: str) -> str:
        """Adds a comment or update to an existing ticket."""
        if ticket_id not in self._state["tickets"]:
            raise ShimError(f"Ticket '{ticket_id}' not found.")
        self._state["tickets"][ticket_id]["history"].append(update)
        return f"Ticket '{ticket_id}' updated."

    def resolve_ticket(self, ticket_id: str, resolution: str) -> str:
        """Resolves a support ticket."""
        if ticket_id not in self._state["tickets"]:
            raise ShimError(f"Ticket '{ticket_id}' not found.")
        self._state["tickets"][ticket_id]["status"] = "RESOLVED"
        self._state["tickets"][ticket_id]["history"].append(f"RESOLVED: {resolution}")
        return f"Ticket '{ticket_id}' resolved."

    def list_open_tickets(self) -> List[Dict[str, Any]]:
        """Lists all tickets with OPEN status."""
        return [t for t in self._state["tickets"].values() if t["status"] == "OPEN"]

    def get_tool_specs(self) -> List[Tuple[str, Any, str]]:
        return [
            ("ticket_create", self.create_ticket, "Create a new support ticket."),
            ("ticket_update", self.update_ticket, "Update an existing support ticket with a comment."),
            ("ticket_resolve", self.resolve_ticket, "Resolve a support ticket with a final note."),
            ("ticket_list_open", self.list_open_tickets, "List all current open support tickets.")
        ]
