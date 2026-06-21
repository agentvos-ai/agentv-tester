import logging
import os
import sqlite3
from typing import List, Dict, Any, Tuple
from core.registry import register_shim
from core.errors import ShimError
from shims import BaseShim

logger = logging.getLogger(__name__)


@register_shim("support_desk")
class SupportDeskShim(BaseShim):
    """
    Industrial-grade Support Desk interface.
    Uses a local SQLite database for ticket persistence and auditability.
    """

    def __init__(self, seed: int = 42):
        self.db_path = os.path.abspath(".agent_workspace/db/support.db")
        super().__init__(seed)

    @property
    def name(self) -> str:
        return "support_desk"

    @property
    def description(self) -> str:
        return "Interface for managing customer support tickets and cases."

    def setup(self) -> None:
        """Ensure database and tables exist."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tickets (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    description TEXT,
                    status TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS comments (
                    ticket_id TEXT,
                    content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(ticket_id) REFERENCES tickets(id)
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def shutdown(self) -> None:
        """Cleanup the database file."""
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except Exception as e:
                logger.warning(f"Failed to remove db file: {e}")

    def reset(self) -> None:
        """Deterministic reset of the support desk state."""
        if os.path.exists(self.db_path):
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute("DROP TABLE IF EXISTS comments")
                conn.execute("DROP TABLE IF EXISTS tickets")
                conn.commit()
            except Exception:
                pass
            finally:
                conn.close()
        
        self.setup()

        # Seed default tickets
        self.create_ticket(
            "Network Outage", "User reports intermittent signal in Zone B."
        )


    def create_ticket(self, title: str, description: str) -> str:
        """Creates a new support ticket."""
        conn = sqlite3.connect(self.db_path)
        try:
            count = conn.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
            tid = f"TKT-{5000 + count + 1}"
            conn.execute(
                "INSERT INTO tickets (id, title, description, status) VALUES (?, ?, ?, ?)",
                (tid, title, description, "OPEN"),
            )
            conn.commit()
            return tid
        except Exception as e:
            raise ShimError(f"Failed to create ticket: {str(e)}")
        finally:
            conn.close()

    def update_ticket(self, ticket_id: str, comment: str) -> str:
        """Adds a comment to an existing ticket."""
        conn = sqlite3.connect(self.db_path)
        try:
            # Verify ticket exists
            res = conn.execute(
                "SELECT id FROM tickets WHERE id = ?", (ticket_id,)
            ).fetchone()
            if not res:
                raise ShimError(f"Ticket '{ticket_id}' not found.")

            conn.execute(
                "INSERT INTO comments (ticket_id, content) VALUES (?, ?)",
                (ticket_id, comment),
            )
            conn.commit()
            return f"Comment added to ticket '{ticket_id}'."
        except Exception as e:
            raise ShimError(f"Failed to update ticket: {str(e)}")
        finally:
            conn.close()

    def resolve_ticket(self, ticket_id: str, resolution_note: str) -> str:
        """Resolves a ticket with a final note."""
        conn = sqlite3.connect(self.db_path)
        try:
            # Verify ticket exists
            res = conn.execute(
                "SELECT id FROM tickets WHERE id = ?", (ticket_id,)
            ).fetchone()
            if not res:
                raise ShimError(f"Ticket '{ticket_id}' not found.")

            conn.execute(
                "UPDATE tickets SET status = 'RESOLVED' WHERE id = ?", (ticket_id,)
            )
            conn.execute(
                "INSERT INTO comments (ticket_id, content) VALUES (?, ?)",
                (ticket_id, f"RESOLUTION: {resolution_note}"),
            )
            conn.commit()
            return f"Ticket '{ticket_id}' resolved."
        except Exception as e:
            raise ShimError(f"Failed to resolve ticket: {str(e)}")
        finally:
            conn.close()

    def list_open_tickets(self) -> List[Dict[str, Any]]:
        """Lists all tickets currently in 'OPEN' status."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT id, title, description, status FROM tickets WHERE status = 'OPEN'"
            )
            return [
                {"id": row[0], "title": row[1], "description": row[2], "status": row[3]}
                for row in cursor.fetchall()
            ]
        except Exception as e:
            raise ShimError(f"Failed to list tickets: {str(e)}")
        finally:
            conn.close()

    def get_tool_specs(self) -> List[Tuple[str, Any, str]]:
        return [
            ("ticket_create", self.create_ticket, "Create a new support ticket."),
            ("ticket_update", self.update_ticket, "Add a comment to a ticket."),
            ("ticket_resolve", self.resolve_ticket, "Resolve a support ticket."),
            ("ticket_list_open", self.list_open_tickets, "List all open tickets."),
        ]
