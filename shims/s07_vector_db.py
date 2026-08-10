import io
import logging
import os
import sqlite3
from typing import Any

import numpy as np

from core.errors import ShimError
from core.registry import register_shim
from shims import BaseShim

logger = logging.getLogger(__name__)


def adapt_array(arr):
    """Adapts a numpy array to a BLOB for SQLite."""
    out = io.BytesIO()
    np.save(out, arr)
    out.seek(0)
    return sqlite3.Binary(out.read())


def convert_array(text):
    """Converts a BLOB from SQLite back to a numpy array."""
    out = io.BytesIO(text)
    out.seek(0)
    return np.load(out)


sqlite3.register_adapter(np.ndarray, adapt_array)
sqlite3.register_converter("ARRAY", convert_array)


@register_shim("vector_db")
class VectorDbShim(BaseShim):
    """
    Industrial-grade Vector Database interface.
    Uses a local SQLite database for vector and metadata persistence.
    """

    def __init__(self, seed: int = 42):
        self.db_path = os.path.abspath(".agent_workspace/db/vectors.db")
        super().__init__(seed)

    @property
    def name(self) -> str:
        return "vector_db"

    @property
    def description(self) -> str:
        return "High-performance vector database for semantic and similarity search."

    def setup(self) -> None:
        """Ensure database and tables exist."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    collection TEXT,
                    vector ARRAY,
                    metadata_json TEXT
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
        """Deterministic reset of the vector database state."""
        self.shutdown()
        self.setup()

    def upsert(
        self, collection: str, vector: list[float], metadata: dict[str, Any]
    ) -> str:
        """Insert a vector and its metadata into a collection."""
        import json

        conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        try:
            conn.execute(
                "INSERT INTO embeddings (collection, vector, metadata_json) VALUES (?, ?, ?)",
                (collection, np.array(vector, dtype=np.float32), json.dumps(metadata)),
            )
            conn.commit()
            return f"Vector upserted into collection '{collection}'."
        except Exception as e:
            raise ShimError(f"Failed to upsert vector: {e!s}")
        finally:
            conn.close()

    def query_similar(
        self, collection: str, vector: list[float], limit: int = 3
    ) -> list[dict[str, Any]]:
        """Perform a cosine similarity search against stored vectors."""
        import json

        conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        try:
            cursor = conn.execute(
                "SELECT vector, metadata_json FROM embeddings WHERE collection = ?",
                (collection,),
            )
            rows = cursor.fetchall()

            if not rows:
                return []

            query_vec = np.array(vector, dtype=np.float32)
            results = []

            for vec, meta_json in rows:
                # Cosine similarity
                norm_a = np.linalg.norm(query_vec)
                norm_b = np.linalg.norm(vec)
                if norm_a == 0 or norm_b == 0:
                    score = 0.0
                else:
                    score = np.dot(query_vec, vec) / (norm_a * norm_b)

                results.append(
                    {"score": float(score), "metadata": json.loads(meta_json)}
                )

            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:limit]
        finally:
            conn.close()

    def delete_vector(self, collection: str, filter_metadata: dict[str, Any]) -> str:
        """Deletes vectors from a collection based on metadata matching."""
        import json

        conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        try:
            # We have to fetch all to check metadata accurately unless we use SQLite JSON extension
            cursor = conn.execute(
                "SELECT id, metadata_json FROM embeddings WHERE collection = ?",
                (collection,),
            )
            to_delete = []
            for row_id, meta_json in cursor.fetchall():
                meta = json.loads(meta_json)
                if all(meta.get(k) == v for k, v in filter_metadata.items()):
                    to_delete.append(row_id)

            if to_delete:
                conn.executemany(
                    "DELETE FROM embeddings WHERE id = ?", [(rid,) for rid in to_delete]
                )
                conn.commit()

            return f"Deleted {len(to_delete)} vectors from '{collection}'."
        finally:
            conn.close()

    def list_collections(self) -> list[str]:
        """Lists all collections in the vector database."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute("SELECT DISTINCT collection FROM embeddings")
            return [row[0] for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_tool_specs(self) -> list[tuple[str, Any, str]]:
        return [
            (
                "vector_upsert",
                self.upsert,
                "Upsert a vector and metadata into a collection.",
            ),
            (
                "vector_query",
                self.query_similar,
                "Query similar vectors in a collection.",
            ),
            (
                "vector_delete",
                self.delete_vector,
                "Delete vectors based on metadata filter.",
            ),
            ("vector_list", self.list_collections, "List all vector collections."),
        ]
