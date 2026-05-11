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
            "desc": task_desc,
            "context": context,
            "status": "PENDING",
            "decision": None,
            "priority": priority,
            "created_at": "2026-05-11T14:00:00Z",
        }
        return rid

    def get_review_status(self, request_id: str) -> Dict[str, Any]:
        """Checks status with probabilistic completion logic."""
        if request_id not in self._state["requests"]:
            raise ShimError(f"Request ID '{request_id}' not found.")

        req = self._state["requests"][request_id]
        
        # Probabilistic simulation: request_id hash determines speed/outcome
        # This makes the simulation deterministic for the same request_id
        import hashlib
        h = int(hashlib.md5(request_id.encode()).hexdigest(), 16)
        
        # High priority requests resolve faster
        threshold = 2 if req["priority"] == "HIGH" else 4
        req["check_count"] = req.get("check_count", 0) + 1
        
        if req["status"] == "PENDING" and req["check_count"] >= threshold:
            # Deterministic outcome based on hash
            if h % 10 < 8: # 80% approval rate
                req["status"] = "APPROVED"
                req["decision"] = "Manual review completed: Action approved."
            else:
                req["status"] = "REJECTED"
                req["decision"] = "Manual review completed: Action rejected due to policy mismatch."

        return req

    def submit_human_decision(self, request_id: str, decision: str) -> str:
        """Allows (mock) manual submission of a decision (for test automation)."""
        if request_id not in self._state["requests"]:
            raise ShimError(f"Request ID '{request_id}' not found.")
        self._state["requests"][request_id]["decision"] = decision
        if decision.upper() in ["APPROVED", "REJECTED"]:
            self._state["requests"][request_id]["status"] = decision.upper()
        else:
            self._state["requests"][request_id]["status"] = "COMPLETED"
        return f"Decision submitted for request '{request_id}'."

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
