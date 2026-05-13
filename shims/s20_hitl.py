import logging


from typing import List, Dict, Any, Tuple
from core.registry import register_shim
from core.errors import ShimError
from shims import BaseShim

logger = logging.getLogger(__name__)


@register_shim("hitl")
class HitlShim(BaseShim):
    """
    Human-in-the-Loop (HITL) simulator.
    Supports asynchronous decision escalation to human operators.
    """

    @property
    def name(self) -> str:
        return "hitl"

    @property
    def description(self) -> str:
        return "Interface for escalating decisions to human experts and operators."

    def reset(self) -> None:
        """Deterministic reset of the HITL state."""
        self._state["requests"]: Dict[str, Dict[str, Any]] = {}

    def request_human_review(self, task_desc: str, context: Dict[str, Any]) -> str:
        """Escalates a task for manual human review with priority detection."""
        rid = f"REQ-{len(self._state['requests']) + 5001}"
        priority = "NORMAL"
        if "urgent" in task_desc.lower() or context.get("priority") == "high":
            priority = "HIGH"

        self._state["requests"][rid] = {
            "id": rid,
            "desc": task_desc,
            "context": context,
            "status": "PENDING",
            "decision": None,
            "priority": priority,
            "created_at": "2026-05-11T14:00:00Z",
            "check_count": 0,
        }
        return rid

    def get_review_status(self, request_id: str) -> Dict[str, Any]:
        """Checks status. Industrial implementation: stays PENDING until advanced."""
        if request_id not in self._state["requests"]:
            raise ShimError(f"Request ID '{request_id}' not found.")

        req = self._state["requests"][request_id]
        req["check_count"] += 1

        # Industrial-grade: We don't use probabilistic resolution here.
        # It stays PENDING until an external system/operator calls 'submit_human_decision'.
        return req

    def submit_human_decision(self, request_id: str, decision: str) -> str:
        """Explicitly submits a human decision to advance the state."""
        if request_id not in self._state["requests"]:
            raise ShimError(f"Request ID '{request_id}' not found.")

        req = self._state["requests"][request_id]
        req["decision"] = decision

        # Normalize status based on decision
        if "approve" in decision.lower():
            req["status"] = "APPROVED"
        elif "reject" in decision.lower():
            req["status"] = "REJECTED"
        else:
            req["status"] = "COMPLETED"

        return f"Decision submitted for request '{request_id}': {req['status']}."

    def get_tool_specs(self) -> List[Tuple[str, Any, str]]:
        return [
            (
                "hitl_request",
                self.request_human_review,
                "Request manual human review for a complex task.",
            ),
            (
                "hitl_status",
                self.get_review_status,
                "Check the current status and decision of a review request.",
            ),
            (
                "hitl_submit",
                self.submit_human_decision,
                "Submit a manual decision for a review request.",
            ),
        ]
