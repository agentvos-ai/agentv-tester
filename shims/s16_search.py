import logging
logger = logging.getLogger(__name__)

from typing import List, Dict, Any, Tuple
from core.registry import register_shim
from shims import BaseShim

@register_shim("search")

class SearchShim(BaseShim):
    """
    Ranked search simulator for web, enterprise, and news data.
    """

    @property
    def name(self) -> str:
        return "search"

    @property
    def description(self) -> str:
        return "High-fidelity search engine for multi-source information retrieval."

    def reset(self) -> None:
        """Deterministic reset of the search corpus."""
        self._state["web"] = [
            {"title": "Global Market Trends", "snippet": "Recent analysis shows...", "url": "https://market-news.com/trends"}
        ]
        self._state["enterprise"] = [
            {"title": "Internal IT Policy", "snippet": "All employees must use...", "url": "local://it-policy"}
        ]
        self._state["news"] = [
            {"title": "Breaking: Tech Giant Acquires AI Startup", "snippet": "The acquisition aims to...", "url": "https://news.com/breaking"}
        ]

    def _search_collection(self, collection: str, query: str) -> List[Dict[str, str]]:
        docs = self._state.get(collection, [])
        return [d for d in docs if query.lower() in d["title"].lower() or query.lower() in d["snippet"].lower()]

    def web_search(self, query: str) -> List[Dict[str, str]]:
        """Perform a public web search."""
        return self._search_collection("web", query)

    def enterprise_search(self, query: str) -> List[Dict[str, str]]:
        """Perform a search across internal enterprise documents."""
        return self._search_collection("enterprise", query)

    def news_search(self, query: str) -> List[Dict[str, str]]:
        """Perform a search for current news articles."""
        return self._search_collection("news", query)

    def get_tool_specs(self) -> List[Tuple[str, Any, str]]:
        return [
            ("search_web", self.web_search, "Perform a search on the public web."),
            ("search_enterprise", self.enterprise_search, "Search internal company documents and intranets."),
            ("search_news", self.news_search, "Search for recent news articles.")
        ]