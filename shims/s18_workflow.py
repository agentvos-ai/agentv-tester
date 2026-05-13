import logging
import os
import sqlite3
import json
from typing import List, Dict, Any, Tuple
from core.registry import register_shim
from core.errors import ShimError
from shims import BaseShim

logger = logging.getLogger(__name__)


@register_shim("workflow")
class WorkflowShim(BaseShim):
    """
    Industrial-grade Workflow interface.
    Uses a local SQLite database for workflow state persistence and execution history.
    """

    def __init__(self, seed: int = 42):
        self.db_path = os.path.abspath(".agent_workspace/db/workflow.db")
        super().__init__(seed)

    @property
    def name(self) -> str:
        return "workflow"

    @property
    def description(self) -> str:
        return "Enterprise workflow engine for orchestrating multi-step processes."

    def setup(self) -> None:
        """Ensure database and tables exist."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS workflows (
                    id TEXT PRIMARY KEY,
                    type TEXT,
                    status TEXT,
                    state_json TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    workflow_id TEXT,
                    transition TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(workflow_id) REFERENCES workflows(id)
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
        """Deterministic reset of the workflow state."""
        self.shutdown()
        self.setup()

        # Seed default workflow
        self.start_workflow(
            "LOAN-PROCESSING", {"customer": "C-001", "step": "INITIAL_REVIEW"}
        )

    def start_workflow(self, workflow_type: str, initial_state: Dict[str, Any]) -> str:
        """Starts a new multi-step workflow."""
        conn = sqlite3.connect(self.db_path)
        try:
            count = conn.execute("SELECT COUNT(*) FROM workflows").fetchone()[0]
            wid = f"WF-{1000 + count + 1}"
            conn.execute(
                "INSERT INTO workflows (id, type, status, state_json) VALUES (?, ?, ?, ?)",
                (wid, workflow_type, "RUNNING", json.dumps(initial_state)),
            )
            conn.execute(
                "INSERT INTO history (workflow_id, transition) VALUES (?, ?)",
                (wid, "START"),
            )
            conn.commit()
            return wid
        except Exception as e:
            raise ShimError(f"Failed to start workflow: {str(e)}")
        finally:
            conn.close()

    def update_workflow(
        self, workflow_id: str, new_state: Dict[str, Any], transition_desc: str
    ) -> str:
        """Updates the state of an existing workflow."""
        conn = sqlite3.connect(self.db_path)
        try:
            # Verify workflow exists
            res = conn.execute(
                "SELECT status FROM workflows WHERE id = ?", (workflow_id,)
            ).fetchone()
            if not res:
                raise ShimError(f"Workflow '{workflow_id}' not found.")
            if res[0] != "RUNNING":
                raise ShimError(f"Workflow '{workflow_id}' is already {res[0]}.")

            conn.execute(
                "UPDATE workflows SET state_json = ?, last_updated = CURRENT_TIMESTAMP WHERE id = ?",
                (json.dumps(new_state), workflow_id),
            )
            conn.execute(
                "INSERT INTO history (workflow_id, transition) VALUES (?, ?)",
                (workflow_id, transition_desc),
            )
            conn.commit()
            return f"Workflow '{workflow_id}' updated: {transition_desc}."
        except Exception as e:
            if isinstance(e, ShimError):
                raise
            raise ShimError(f"Failed to update workflow: {str(e)}")
        finally:
            conn.close()

    def complete_task(self, workflow_id: str, task_name: str) -> str:
        """Alias for update_workflow (Completing a task)."""
        # In a real system, we'd fetch current state and update it
        return self.update_workflow(
            workflow_id,
            {"last_task": task_name, "status": "STEP_COMPLETE"},
            f"COMPLETE_{task_name}",
        )

    def escalate(self, workflow_id: str, reason: str) -> str:
        """Alias for update_workflow (Escalating a workflow)."""
        return self.update_workflow(
            workflow_id, {"escalated": True, "reason": reason}, "ESCALATE"
        )

    def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Retrieves the current status and state of a workflow."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT type, status, state_json FROM workflows WHERE id = ?",
                (workflow_id,),
            )
            row = cursor.fetchone()
            if not row:
                raise ShimError(f"Workflow '{workflow_id}' not found.")

            # Fetch history
            h_cursor = conn.execute(
                "SELECT transition, timestamp FROM history WHERE workflow_id = ? ORDER BY timestamp ASC",
                (workflow_id,),
            )
            history = [{"transition": r[0], "time": r[1]} for r in h_cursor.fetchall()]

            return {
                "id": workflow_id,
                "type": row[0],
                "status": row[1],
                "state": json.loads(row[2]),
                "history": history,
            }
        finally:
            conn.close()

    def get_tool_specs(self) -> List[Tuple[str, Any, str]]:
        return [
            ("wf_start", self.start_workflow, "Start a new industrial workflow."),
            (
                "wf_update",
                self.update_workflow,
                "Update the state of a running workflow.",
            ),
            (
                "wf_complete",
                self.complete_task,
                "Mark a specific workflow task as complete.",
            ),
            (
                "wf_escalate",
                self.escalate,
                "Escalate a workflow for higher-level review.",
            ),
            (
                "wf_status",
                self.get_workflow_status,
                "Get the full status of a workflow.",
            ),
        ]
