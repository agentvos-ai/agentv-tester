from typing import List, Dict, Any, Tuple
from core.registry import register_shim
from core.errors import ShimError
from shims import BaseShim

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
        """Escalates a task for manual human review."""
        rid = f"REQ-{len(self._state['requests']) + 5001}"
        self._state["requests"][rid] = {
            "desc": task_desc,
            "context": context,
            "status": "PENDING",
            "decision": None
        }
        return rid

    def get_review_status(self, request_id: str) -> Dict[str, Any]:
        """Checks the status and final decision of a review request."""
        if request_id not in self._state["requests"]:
            raise ShimError(f"Request ID '{request_id}' not found.")
        
        req = self._state["requests"][request_id]
        # Simulation: auto-approve after first check for flow testing
        if req["status"] == "PENDING":
            req["status"] = "APPROVED"
            req["decision"] = "Proceed with caution."
            
        return req

    def submit_human_decision(self, request_id: str, decision: str) -> str:
        """Allows (mock) manual submission of a decision (for test automation)."""
        if request_id not in self._state["requests"]:
            raise ShimError(f"Request ID '{request_id}' not found.")
        self._state["requests"][request_id]["status"] = "COMPLETED"
        self._state["requests"][request_id]["decision"] = decision
        return f"Decision submitted for request '{request_id}'."

    def get_tool_specs(self) -> List[Tuple[str, Any, str]]:
        return [
            ("hitl_request", self.request_human_review, "Request manual human review for a complex task."),
            ("hitl_status", self.get_review_status, "Check the current status and decision of a review request."),
            ("hitl_submit", self.submit_human_decision, "Submit a manual decision for a review request.")
        ]
