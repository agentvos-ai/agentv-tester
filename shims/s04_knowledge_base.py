import logging
logger = logging.getLogger(__name__)

from typing import List, Any, Tuple
from core.registry import register_shim
from core.errors import ShimError
from shims import BaseShim

@register_shim("knowledge_base")

class KnowledgeBaseShim(BaseShim):
    """
    Document store with keyword retrieval.
    Supports searching, fetching, and topic listing.
    """

    @property
    def name(self) -> str:
        return "knowledge_base"

    @property
    def description(self) -> str:
        return "Internal knowledge base for document retrieval and search."

    def reset(self) -> None:
        """Deterministic reset of the KB state."""
        self._state["docs"] = {
            "fraud_policy_v1": {
                "topic": "Compliance",
                "content": "All transactions above $10,000 must be flagged for manual review."
            },
            "aml_guidelines_2025": {
                "topic": "Regulatory",
                "content": "Anti-Money Laundering rules require filing SAR for suspicious activities."
            }
        }

    def search(self, query: str) -> List[str]:
        """Search the KB for relevant documents."""
        results = []
        for doc_id, data in self._state["docs"].items():
            if query.lower() in doc_id.lower() or query.lower() in data["content"].lower():
                results.append(doc_id)
        return results

    def fetch_doc(self, doc_id: str) -> str:
        """Fetches the full content of a document."""
        if doc_id not in self._state["docs"]:
            raise ShimError(f"Document '{doc_id}' not found in the knowledge base.")
        return self._state["docs"][doc_id]["content"]

    def list_topics(self) -> List[str]:
        """Lists all topics available in the KB."""
        topics = set()
        for data in self._state["docs"].values():
            topics.add(data["topic"])
        return list(topics)

    def get_tool_specs(self) -> List[Tuple[str, Any, str]]:
        return [
            ("kb_search", self.search, "Search the internal knowledge base for document IDs."),
            ("kb_fetch", self.fetch_doc, "Fetch the full content of a specific document."),
            ("kb_topics", self.list_topics, "List all available knowledge base topics.")
        ]