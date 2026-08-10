import json
import logging
import os
from typing import Any

from core.registry import register_shim
from shims import BaseShim

logger = logging.getLogger(__name__)


@register_shim("search")
class SearchShim(BaseShim):
    """
    Industrial-grade Search interface.
    Indexes local Knowledge Base and provides authoritative canned web results.
    """

    def __init__(self, seed: int = 42):
        self.kb_root = os.path.abspath(".agent_workspace/kb")
        self.canned_results_path = os.path.abspath(
            ".agent_workspace/search/web_results.json"
        )
        super().__init__(seed)

    @property
    def name(self) -> str:
        return "search"

    @property
    def description(self) -> str:
        return (
            "Enterprise search engine for internal and external information retrieval."
        )

    def setup(self) -> None:
        """Ensure search directory and canned results exist."""
        os.makedirs(os.path.dirname(self.canned_results_path), exist_ok=True)
        if not os.path.exists(self.canned_results_path):
            with open(self.canned_results_path, "w") as f:
                json.dump(
                    [
                        {
                            "title": "Latest AML Regulations 2025",
                            "url": "https://fincen.gov/aml-2025",
                            "snippet": "New guidelines for high-value transactions...",
                        },
                        {
                            "title": "Cloud Infrastructure Security",
                            "url": "https://aws.amazon.com/security",
                            "snippet": "Best practices for securing enterprise cloud workloads...",
                        },
                    ],
                    f,
                )

    def reset(self) -> None:
        """Deterministic reset of the search state."""
        self.setup()

    def web_search(self, query: str) -> list[dict[str, str]]:
        """Simulates an external web search using canned forensic results."""
        results = []
        if os.path.exists(self.canned_results_path):
            with open(self.canned_results_path, "r") as f:
                canned = json.load(f)
                for res in canned:
                    if (
                        query.lower() in res["title"].lower()
                        or query.lower() in res["snippet"].lower()
                    ):
                        results.append(res)
        return results

    def internal_search(self, query: str) -> list[dict[str, str]]:
        """Searches the local knowledge base (crawls disk)."""
        results = []
        if not os.path.exists(self.kb_root):
            return []

        for name in os.listdir(self.kb_root):
            if not name.endswith(".md"):
                continue

            full_path = os.path.join(self.kb_root, name)
            try:
                with open(full_path, "r") as f:
                    content = f.read()
                    if (
                        query.lower() in name.lower()
                        or query.lower() in content.lower()
                    ):
                        # Extract first line as title
                        title = content.split("\n")[0].replace("#", "").strip()
                        results.append(
                            {
                                "title": title,
                                "id": name.replace(".md", ""),
                                "source": "Internal KB",
                            }
                        )
            except Exception:
                continue
        return results

    def enterprise_search(self, query: str) -> list[dict[str, str]]:
        """Alias for internal_search to maintain compatibility."""
        return self.internal_search(query)

    def news_search(self, query: str) -> list[dict[str, str]]:
        """Alias for web_search to maintain compatibility."""
        return self.web_search(query)

    def get_tool_specs(self) -> list[tuple[str, Any, str]]:
        return [
            ("search_web", self.web_search, "Search the web for external information."),
            (
                "search_internal",
                self.internal_search,
                "Search the internal enterprise knowledge base.",
            ),
            (
                "search_enterprise",
                self.enterprise_search,
                "Search internal company documents.",
            ),
            ("search_news", self.news_search, "Search for recent news articles."),
        ]
