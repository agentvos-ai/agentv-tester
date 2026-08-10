import logging
import os
import sqlite3
from typing import Any

from core.errors import ShimError
from core.registry import register_shim
from shims import BaseShim

logger = logging.getLogger(__name__)


@register_shim("social_media")
class SocialMediaShim(BaseShim):
    """
    Industrial-grade Social Media interface.
    Uses a local SQLite database for feed and interaction persistence.
    """

    def __init__(self, seed: int = 42):
        self.db_path = os.path.abspath(".agent_workspace/db/social.db")
        super().__init__(seed)

    @property
    def name(self) -> str:
        return "social_media"

    @property
    def description(self) -> str:
        return "Enterprise interface for managing social media posts and engagement."

    def setup(self) -> None:
        """Ensure database and tables exist."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT,
                    status TEXT DEFAULT 'POSTED',
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS mentions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    author TEXT,
                    content TEXT,
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
        """Deterministic reset of the social media state."""
        self.shutdown()
        self.setup()

        # Seed default mentions
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "INSERT INTO mentions (author, content) VALUES ('@user1', 'Great service!')"
            )
            conn.commit()
        finally:
            conn.close()

    def post(self, content: str) -> str:
        """Creates a new social media post."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("INSERT INTO posts (content) VALUES (?)", (content,))
            conn.commit()
            return "Post published successfully."
        except Exception as e:
            raise ShimError(f"Failed to post: {e!s}")
        finally:
            conn.close()

    def get_mentions(self) -> list[dict[str, Any]]:
        """Retrieves recent mentions."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT author, content, timestamp FROM mentions ORDER BY timestamp DESC"
            )
            return [
                {"author": row[0], "content": row[1], "timestamp": row[2]}
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()

    def get_tool_specs(self) -> list[tuple[str, Any, str]]:
        return [
            ("social_post", self.post, "Create a new social media post."),
            ("social_mentions", self.get_mentions, "Get recent mentions and tags."),
        ]
