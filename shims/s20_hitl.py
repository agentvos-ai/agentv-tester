import logging
import time
from typing import Any

from core.errors import ShimError
from core.registry import register_shim
from shims import BaseShim

logger = logging.getLogger(__name__)


@register_shim("hitl")
class HitlShim(BaseShim):
    """
    Industrial-grade Human-in-the-Loop (HITL) interface.
    Supports asynchronous decision escalation, SLA tracking, and auto-escalation tiers.
    """

    def __init__(self, seed: int = 42):
        self._requests: dict[str, dict[str, Any]] = {}
        super().__init__(seed)

    @property
    def name(self) -> str:
        return "hitl"

    @property
    def description(self) -> str:
        return "Enterprise interface for escalating decisions to human experts with SLA tracking."

    def reset(self) -> None:
        """Deterministic reset of the HITL state."""
        self._requests = {}

    def request_human_review(self, task_desc: str, context: dict[str, Any]) -> str:
        """Escalates a task for manual human review with priority detection and SLA initiation."""
        rid = f"REQ-{len(self._requests) + 5001}"
        priority = "NORMAL"
        if "urgent" in task_desc.lower() or context.get("priority") == "high":
            priority = "HIGH"

        self._requests[rid] = {
            "id": rid,
            "desc": task_desc,
            "context": context,
            "status": "PENDING",
            "decision": None,
            "priority": priority,
            "created_at": time.time(),
            "check_count": 0,
            "sla_tier": "LEVEL_1",
        }
        logger.info(f"HITL: Request {rid} created with priority {priority}.")
        return rid

    def get_review_status(self, request_id: str) -> dict[str, Any]:
        """
        Checks status and implements SLA Auto-Escalation logic.
        If a request is checked more than 3 times without resolution, it moves to LEVEL_2.
        """
        if request_id not in self._requests:
            raise ShimError(f"Request ID '{request_id}' not found.")

        req = self._requests[request_id]
        req["check_count"] += 1

        # SLA Logic: Auto-escalation based on check counts (simulating time-based delays)
        if req["status"] == "PENDING" and req["check_count"] > 3:
            req["sla_tier"] = "LEVEL_2"
            req["priority"] = "HIGH"
            logger.warning(
                f"HITL: Request {request_id} AUTO-ESCALATED to LEVEL_2 due to SLA breach."
            )

        return req

    def submit_human_decision(self, request_id: str, decision: str) -> str:
        """Explicitly submits a human decision to advance the state."""
        if request_id not in self._requests:
            raise ShimError(f"Request ID '{request_id}' not found.")

        req = self._requests[request_id]
        req["decision"] = decision

        # Normalize status based on decision
        if "approve" in decision.lower():
            req["status"] = "APPROVED"
        elif "reject" in decision.lower():
            req["status"] = "REJECTED"
        else:
            req["status"] = "COMPLETED"

        req["resolved_at"] = time.time()
        return f"Decision submitted for request '{request_id}': {req['status']}."

    def get_tool_specs(self) -> list[tuple[str, Any, str]]:
        return [
            (
                "hitl_request",
                self.request_human_review,
                "Request manual human review for a complex task.",
            ),
            (
                "hitl_status",
                self.get_review_status,
                "Check the current status and SLA tier of a review request.",
            ),
            (
                "hitl_submit",
                self.submit_human_decision,
                "Submit a manual decision for a review request.",
            ),
        ]
