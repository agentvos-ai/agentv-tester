import logging

logger = logging.getLogger(__name__)

import numpy as np
from typing import List, Dict, Any, Tuple
from core.registry import register_shim
from core.errors import ShimError
from shims import BaseShim


@register_shim("vector_db")
class VectorDbShim(BaseShim):
    """
    In-memory cosine-similarity vector store (numpy).
    Supports multi-collection vector operations.
    """

    @property
    def name(self) -> str:
        return "vector_db"

    @property
    def description(self) -> str:
        return "High-performance vector database for semantic and similarity search."

    def reset(self) -> None:
        """Deterministic reset of the vector database state."""
        self._state["collections"]: Dict[str, List[Dict[str, Any]]] = {"policies": []}

    def upsert(
        self, collection: str, vector: List[float], metadata: Dict[str, Any]
    ) -> str:
        """Insert or update a vector and its metadata in a collection."""
        if collection not in self._state["collections"]:
            self._state["collections"][collection] = []

        # In a real system, we'd check if ID exists in metadata to update
        self._state["collections"][collection].append(
            {"vector": np.array(vector), "metadata": metadata}
        )
        return f"Vector upserted into collection '{collection}'."

    def query_similar(
        self, collection: str, vector: List[float], limit: int = 3
    ) -> List[Dict[str, Any]]:
        """Perform a cosine similarity search."""
        if collection not in self._state["collections"]:
            raise ShimError(f"Collection '{collection}' not found.")

        if not self._state["collections"][collection]:
            return []

        query_vec = np.array(vector)
        results = []
        for item in self._state["collections"][collection]:
            # Simple cosine similarity
            norm_a = np.linalg.norm(query_vec)
            norm_b = np.linalg.norm(item["vector"])
            if norm_a == 0 or norm_b == 0:
                score = 0.0
            else:
                score = np.dot(query_vec, item["vector"]) / (norm_a * norm_b)

            results.append({"score": float(score), "metadata": item["metadata"]})

        # Sort by score descending
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    def delete_vector(self, collection: str, filter_metadata: Dict[str, Any]) -> str:
        """Delete vectors from a collection based on metadata matching."""
        if collection not in self._state["collections"]:
            raise ShimError(f"Collection '{collection}' not found.")

        # Simplified filter: match any metadata key-value
        original_count = len(self._state["collections"][collection])
        self._state["collections"][collection] = [
            item
            for item in self._state["collections"][collection]
            if not all(item["metadata"].get(k) == v for k, v in filter_metadata.items())
        ]
        deleted_count = original_count - len(self._state["collections"][collection])
        return f"Deleted {deleted_count} vectors from '{collection}'."

    def list_collections(self) -> List[str]:
        """List all active vector collections."""
        return list(self._state["collections"].keys())

    def get_tool_specs(self) -> List[Tuple[str, Any, str]]:
        return [
            (
                "vector_upsert",
                self.upsert,
                "Upsert a vector and metadata into a collection.",
            ),
            (
                "vector_query",
                self.query_similar,
                "Query similar vectors in a collection using cosine similarity.",
            ),
            (
                "vector_delete",
                self.delete_vector,
                "Delete vectors from a collection based on metadata filters.",
            ),
            (
                "vector_list_collections",
                self.list_collections,
                "List all available vector collections.",
            ),
        ]
