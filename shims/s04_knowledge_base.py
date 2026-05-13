import logging
import os
import shutil
from typing import List, Any, Tuple
from core.registry import register_shim
from core.errors import ShimError
from shims import BaseShim

logger = logging.getLogger(__name__)


@register_shim("knowledge_base")
class KnowledgeBaseShim(BaseShim):
    """
    Industrial-grade Knowledge Base interface.
    Uses Markdown files in a local workspace for persistence and transparency.
    """

    def __init__(self, seed: int = 42):
        self.workspace_root = os.path.abspath(".agent_workspace/kb")
        super().__init__(seed)

    @property
    def name(self) -> str:
        return "knowledge_base"

    @property
    def description(self) -> str:
        return "Internal knowledge base for document retrieval and search."

    def setup(self) -> None:
        """Ensure workspace directory exists."""
        if not os.path.exists(self.workspace_root):
            os.makedirs(self.workspace_root)

    def shutdown(self) -> None:
        """Cleanup the workspace."""
        if os.path.exists(self.workspace_root):
            shutil.rmtree(self.workspace_root)

    def reset(self) -> None:
        """Deterministic reset of the KB state."""
        self.shutdown()
        self.setup()

        # Seed default documents
        docs = {
            "fraud_policy_v1.md": """# Compliance Policy: Fraud
All transactions above $10,000 must be flagged for manual review.
Category: Compliance""",
            "aml_guidelines_2025.md": """# Regulatory: AML Guidelines
Anti-Money Laundering rules require filing SAR for suspicious activities.
Category: Regulatory""",
        }

        for name, content in docs.items():
            with open(os.path.join(self.workspace_root, name), "w") as f:
                f.write(content)

    def search(self, query: str) -> List[str]:
        """Search the KB for relevant documents using keyword matching."""
        results = []
        if not os.path.exists(self.workspace_root):
            return []

        for name in os.listdir(self.workspace_root):
            if not name.endswith(".md"):
                continue

            full_path = os.path.join(self.workspace_root, name)
            try:
                with open(full_path, "r") as f:
                    content = f.read()
                    if (
                        query.lower() in name.lower()
                        or query.lower() in content.lower()
                    ):
                        results.append(name.replace(".md", ""))
            except Exception as e:
                logger.error(f"Failed to read KB doc {name}: {str(e)}")

        return results

    def fetch_doc(self, doc_id: str) -> str:
        """Fetches the full content of a document."""
        # Handle both ID and filename-style requests
        if not doc_id.endswith(".md"):
            doc_id += ".md"

        full_path = os.path.join(self.workspace_root, doc_id)
        if not os.path.exists(full_path):
            raise ShimError(f"Document '{doc_id}' not found in the knowledge base.")

        try:
            with open(full_path, "r") as f:
                return f.read()
        except Exception as e:
            raise ShimError(f"Failed to fetch document '{doc_id}': {str(e)}")

    def list_topics(self) -> List[str]:
        """Lists all topics available in the KB by parsing 'Category:' markers."""
        topics = set()
        if not os.path.exists(self.workspace_root):
            return []

        for name in os.listdir(self.workspace_root):
            full_path = os.path.join(self.workspace_root, name)
            try:
                with open(full_path, "r") as f:
                    for line in f:
                        if line.startswith("Category:"):
                            topics.add(line.replace("Category:", "").strip())
            except Exception:
                continue
        return list(topics)

    def get_tool_specs(self) -> List[Tuple[str, Any, str]]:
        return [
            (
                "kb_search",
                self.search,
                "Search the internal knowledge base for document IDs.",
            ),
            (
                "kb_fetch",
                self.fetch_doc,
                "Fetch the full content of a specific document.",
            ),
            (
                "kb_topics",
                self.list_topics,
                "List all available knowledge base topics.",
            ),
        ]
