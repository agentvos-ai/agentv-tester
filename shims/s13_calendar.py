import logging
import os
import sqlite3
from typing import List, Dict, Any, Tuple
from core.registry import register_shim
from core.errors import ShimError
from shims import BaseShim

logger = logging.getLogger(__name__)


@register_shim("calendar")
class CalendarShim(BaseShim):
    """
    Industrial-grade Calendar interface.
    Uses a local SQLite database for event persistence and auditability.
    """

    def __init__(self, seed: int = 42):
        self.db_path = os.path.abspath(".agent_workspace/db/calendar.db")
        super().__init__(seed)

    @property
    def name(self) -> str:
        return "calendar"

    @property
    def description(self) -> str:
        return "Enterprise calendar service for scheduling meetings and events."

    def setup(self) -> None:
        """Ensure database and tables exist."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    start_time TEXT,
                    end_time TEXT,
                    location TEXT,
                    organizer TEXT,
                    status TEXT DEFAULT 'CONFIRMED'
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
        """Deterministic reset of the calendar state."""
        self.shutdown()
        self.setup()

        # Seed default events
        self.create_event(
            "Board Meeting", "2025-06-10 10:00", "2025-06-10 11:30", "Room A"
        )

    def create_event(self, title: str, start: str, end: str, location: str = "") -> str:
        """Schedules a new calendar event."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "INSERT INTO events (title, start_time, end_time, location) VALUES (?, ?, ?, ?)",
                (title, start, end, location),
            )
            conn.commit()
            return f"Event '{title}' scheduled from {start} to {end}."
        except Exception as e:
            raise ShimError(f"Failed to create event: {str(e)}")
        finally:
            conn.close()

    def list_events(self, date: str) -> List[Dict[str, Any]]:
        """Lists all events for a specific date (YYYY-MM-DD)."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT id, title, start_time, end_time, location FROM events WHERE start_time LIKE ?",
                (f"{date}%",),
            )
            return [
                {
                    "id": str(row[0]),
                    "title": row[1],
                    "start": row[2],
                    "end": row[3],
                    "location": row[4],
                }
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()

    def delete_event(self, event_id: str) -> str:
        """Cancels a scheduled event."""
        # Support 'ev_1' format from legacy tests
        db_id = event_id.replace("ev_", "")

        conn = sqlite3.connect(self.db_path)
        try:
            res = conn.execute(
                "SELECT title FROM events WHERE id = ?", (db_id,)
            ).fetchone()
            if not res:
                raise ShimError(f"Event ID '{event_id}' not found.")

            conn.execute("DELETE FROM events WHERE id = ?", (db_id,))
            conn.commit()
            return f"Event '{res[0]}' (ID: {event_id}) has been cancelled."
        finally:
            conn.close()

    def cancel_event(self, event_id: str) -> str:
        """Alias for delete_event."""
        return self.delete_event(event_id)

    def find_free_slot(self, date: str, duration_min: int) -> str:
        """Simulates finding a free slot."""
        return f"{date}T14:00:00"

    def get_tool_specs(self) -> List[Tuple[str, Any, str]]:
        return [
            ("cal_create", self.create_event, "Schedule a new calendar event."),
            ("cal_list", self.list_events, "List events for a specific date."),
            ("cal_delete", self.delete_event, "Cancel a calendar event."),
            ("cal_cancel", self.cancel_event, "Cancel a calendar event."),
            ("cal_find_slot", self.find_free_slot, "Find available time slots."),
        ]
