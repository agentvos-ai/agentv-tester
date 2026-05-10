import logging
logger = logging.getLogger(__name__)

from typing import List, Dict, Any, Tuple
from core.registry import register_shim
from core.errors import ShimError
from shims import BaseShim

@register_shim("workflow")

class WorkflowShim(BaseShim):
    """
    Business Process Management (BPM) simulator.
    Tracks stateful multi-step workflows.
    """

    @property
    def name(self) -> str:
        return "workflow"

    @property
    def description(self) -> str:
        return "Orchestration engine for automating multi-step business processes."

    def reset(self) -> None:
        """Deterministic reset of the workflow state."""
        self._state["workflows"]: Dict[str, Dict[str, Any]] = {}

    def start_workflow(self, process_id: str, payload: Dict[str, Any]) -> str:
        """Initiates a new business process workflow."""
        wid = f"WF-{process_id.upper()}-{len(self._state['workflows']) + 1001}"
        self._state["workflows"][wid] = {
            "process": process_id,
            "status": "IN_PROGRESS",
            "current_step": "START",
            "payload": payload,
            "escalated": False
        }
        return wid

    def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Gets the current status and payload of a workflow."""
        if workflow_id not in self._state["workflows"]:
            raise ShimError(f"Workflow ID '{workflow_id}' not found.")
        return self._state["workflows"][workflow_id]

    def complete_task(self, workflow_id: str, task_id: str) -> str:
        """Completes a specific task within a workflow, advancing the process."""
        if workflow_id not in self._state["workflows"]:
            raise ShimError(f"Workflow ID '{workflow_id}' not found.")
        self._state["workflows"][workflow_id]["current_step"] = task_id
        if task_id == "END":
            self._state["workflows"][workflow_id]["status"] = "COMPLETED"
        return f"Task '{task_id}' in workflow '{workflow_id}' completed."

    def escalate(self, workflow_id: str, reason: str) -> str:
        """Escalates a workflow to a manager for manual intervention."""
        if workflow_id not in self._state["workflows"]:
            raise ShimError(f"Workflow ID '{workflow_id}' not found.")
        self._state["workflows"][workflow_id]["escalated"] = True
        self._state["workflows"][workflow_id]["status"] = "ESCALATED"
        return f"Workflow '{workflow_id}' escalated for reason: {reason}."

    def get_tool_specs(self) -> List[Tuple[str, Any, str]]:
        return [
            ("wf_start", self.start_workflow, "Start a new business process workflow."),
            ("wf_status", self.get_workflow_status, "Check the status of an active workflow."),
            ("wf_complete_task", self.complete_task, "Complete a task and advance the workflow."),
            ("wf_escalate", self.escalate, "Escalate a workflow for manual review.")
        ]