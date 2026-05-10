import logging

logger = logging.getLogger(__name__)

from typing import List, Dict, Any, Tuple
from core.registry import register_shim
from core.errors import ShimError
from shims import BaseShim


@register_shim("calendar")
class CalendarShim(BaseShim):
    """
    Enterprise calendar and scheduling service simulator.
    Supports event management and free/busy lookup.
    """

    @property
    def name(self) -> str:
        return "calendar"

    @property
    def description(self) -> str:
        return "Enterprise scheduling service for managing appointments and meetings."

    def reset(self) -> None:
        """Deterministic reset of the calendar state."""
        self._state["events"] = [
            {
                "id": "ev_1",
                "title": "Team Sync",
                "start": "2026-05-10T10:00:00",
                "end": "2026-05-10T11:00:00",
            }
        ]

    def create_event(self, title: str, start: str, end: str) -> str:
        """Schedules a new calendar event."""
        eid = f"ev_{len(self._state['events']) + 1}"
        self._state["events"].append(
            {"id": eid, "title": title, "start": start, "end": end}
        )
        return f"Event '{title}' scheduled (ID: {eid})."

    def list_events(self, date: str) -> List[Dict[str, str]]:
        """Lists all events for a specific date (YYYY-MM-DD)."""
        return [e for e in self._state["events"] if e["start"].startswith(date)]

    def find_free_slot(self, date: str, duration_min: int) -> str:
        """Finds the first available time slot for a given duration."""
        # Simple simulation: always returns 2 PM for now
        return f"{date}T14:00:00"

    def cancel_event(self, event_id: str) -> str:
        """Cancels an existing event."""
        original_count = len(self._state["events"])
        self._state["events"] = [
            e for e in self._state["events"] if e["id"] != event_id
        ]
        if len(self._state["events"]) == original_count:
            raise ShimError(f"Event ID '{event_id}' not found.")
        return f"Event '{event_id}' cancelled."

    def get_tool_specs(self) -> List[Tuple[str, Any, str]]:
        return [
            ("calendar_create", self.create_event, "Create a new calendar event."),
            ("calendar_list", self.list_events, "List events for a specific date."),
            (
                "calendar_find_slot",
                self.find_free_slot,
                "Find an available time slot for a meeting.",
            ),
            (
                "calendar_cancel",
                self.cancel_event,
                "Cancel a scheduled calendar event.",
            ),
        ]
