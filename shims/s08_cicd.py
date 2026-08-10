import logging
import os
import sqlite3
from typing import Any

from core.errors import ShimError
from core.registry import register_shim
from shims import BaseShim

logger = logging.getLogger(__name__)


@register_shim("cicd")
class CicdShim(BaseShim):
    """
    Industrial-grade CI/CD interface.
    Uses a local SQLite database for pipeline status and log persistence.
    """

    def __init__(self, seed: int = 42):
        self.db_path = os.path.abspath(".agent_workspace/db/cicd.db")
        super().__init__(seed)

    @property
    def name(self) -> str:
        return "cicd"

    @property
    def description(self) -> str:
        return (
            "Enterprise CI/CD platform for automating builds, tests, and deployments."
        )

    def setup(self) -> None:
        """Ensure database and tables exist."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pipelines (
                    id TEXT PRIMARY KEY,
                    status TEXT,
                    logs TEXT,
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
        """Deterministic reset of the CI/CD state."""
        self.shutdown()
        self.setup()

    def trigger_pipeline(self, pipeline_id: str) -> str:
        """Starts a new pipeline run."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "INSERT OR REPLACE INTO pipelines (id, status, logs) VALUES (?, ?, ?)",
                (
                    pipeline_id,
                    "RUNNING",
                    "Started pipeline run...\nRunning unit tests...\n",
                ),
            )
            conn.commit()
            return f"Pipeline '{pipeline_id}' triggered."
        except Exception as e:
            raise ShimError(f"Failed to trigger pipeline: {e!s}")
        finally:
            conn.close()

    def get_status(self, pipeline_id: str) -> str:
        """Retrieves the status of a pipeline."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT status FROM pipelines WHERE id = ?", (pipeline_id,)
            )
            row = cursor.fetchone()
            if not row:
                raise ShimError(f"Pipeline '{pipeline_id}' not found.")
            return row[0]
        finally:
            conn.close()

    def get_logs(self, pipeline_id: str) -> str:
        """Retrieves the logs for a pipeline."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT logs FROM pipelines WHERE id = ?", (pipeline_id,)
            )
            row = cursor.fetchone()
            if not row:
                raise ShimError(f"Pipeline '{pipeline_id}' not found.")
            return row[0]
        finally:
            conn.close()

    def cancel_pipeline(self, pipeline_id: str) -> str:
        """Cancels a running pipeline."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "UPDATE pipelines SET status = 'CANCELLED' WHERE id = ?", (pipeline_id,)
            )
            conn.commit()
            return f"Pipeline '{pipeline_id}' cancelled."
        except Exception as e:
            raise ShimError(f"Failed to cancel pipeline: {e!s}")
        finally:
            conn.close()

    def get_tool_specs(self) -> list[tuple[str, Any, str]]:
        return [
            ("cicd_trigger", self.trigger_pipeline, "Trigger a CI/CD pipeline run."),
            ("cicd_status", self.get_status, "Check the status of a pipeline run."),
            ("cicd_logs", self.get_logs, "Fetch logs for a pipeline run."),
            ("cicd_cancel", self.cancel_pipeline, "Cancel an active pipeline run."),
        ]
