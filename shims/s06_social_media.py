import logging


from typing import List, Dict, Any, Tuple
from core.registry import register_shim
from shims import BaseShim

logger = logging.getLogger(__name__)


@register_shim("social_media")
class SocialMediaShim(BaseShim):
    """
    Social media platform simulator.
    Supports posting, feed fetching, and direct messaging.
    """

    @property
    def name(self) -> str:
        return "social_media"

    @property
    def description(self) -> str:
        return "Interface for interacting with enterprise and public social media platforms."

    def reset(self) -> None:
        """Deterministic reset of the social media state."""
        self._state["feed"] = [
            {
                "author": "user_1",
                "content": "Just switched to this bank, love the UI!",
                "mentions": ["@bank"],
            },
            {
                "author": "news_bot",
                "content": "Market update: Tech stocks rising.",
                "mentions": [],
            },
        ]
        self._state["dms"] = []

    def post(self, content: str) -> str:
        """Create a new public post."""
        self._state["feed"].insert(
            0, {"author": "enterprise-agent", "content": content, "mentions": []}
        )
        return "Successfully posted message."

    def fetch_feed(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch the latest posts from the social feed."""
        return self._state["feed"][:limit]

    def send_dm(self, recipient: str, message: str) -> str:
        """Send a direct message to a user."""
        self._state["dms"].append(
            {"to": recipient, "from": "enterprise-agent", "content": message}
        )
        return f"Direct message sent to '{recipient}'."

    def get_mentions(self) -> List[Dict[str, Any]]:
        """Fetch all posts that mention @bank or the agent."""
        return [p for p in self._state["feed"] if "@bank" in p["mentions"]]

    def get_tool_specs(self) -> List[Tuple[str, Any, str]]:
        return [
            (
                "social_post",
                self.post,
                "Post a new message to the public social media feed.",
            ),
            (
                "social_fetch_feed",
                self.fetch_feed,
                "Fetch the most recent posts from the social feed.",
            ),
            (
                "social_send_dm",
                self.send_dm,
                "Send a private direct message to a specific user.",
            ),
            (
                "social_get_mentions",
                self.get_mentions,
                "Fetch all social media posts that mention the organization.",
            ),
        ]
