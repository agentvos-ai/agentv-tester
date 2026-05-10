import logging


from typing import List, Dict, Any, Tuple
from core.registry import register_shim
from shims import BaseShim

logger = logging.getLogger(__name__)


@register_shim("compliance")
class ComplianceShim(BaseShim):
    """
    Regulatory compliance and policy enforcement engine.
    Tracks all decisions for audit purposes.
    """

    @property
    def name(self) -> str:
        return "compliance"

    @property
    def description(self) -> str:
        return "Compliance engine for validating actions against enterprise and legal policies."

    def reset(self) -> None:
        """Deterministic reset of the compliance state."""
        self._state["audit_trail"]: List[Dict[str, Any]] = []
        self._state["violations"]: List[Dict[str, Any]] = []

    def check_policy(self, action: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validates an action against active policies."""
        # Realistic rule: transactions over 50k need hitl
        if action == "transaction" and data.get("amount", 0) > 50000:
            result = {
                "allowed": False,
                "reason": "Amount exceeds automated threshold ($50k).",
            }
        else:
            result = {"allowed": True, "reason": "Within automated policy limits."}

        self._state["audit_trail"].append(
            {"action": action, "data": data, "result": result}
        )
        return result

    def file_report(self, report_type: str, content: Dict[str, Any]) -> str:
        """Files a mandatory regulatory report."""
        report_id = f"REG-{report_type.upper()}-{len(self._state['audit_trail']) + 1}"
        self._state["audit_trail"].append(
            {"action": "REPORT", "id": report_id, "type": report_type}
        )
        return f"Regulatory report '{report_id}' filed successfully."

    def get_audit_trail(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieves the history of compliance checks and actions."""
        return self._state["audit_trail"][-limit:]

    def flag_violation(self, entity_id: str, reason: str) -> str:
        """Flags an entity (user, transaction) for a compliance violation."""
        violation = {"entity": entity_id, "reason": reason, "status": "OPEN"}
        self._state["violations"].append(violation)
        self._state["audit_trail"].append(
            {"action": "VIOLATION_FLAG", "entity": entity_id}
        )
        return f"Violation flagged for '{entity_id}'."

    def get_tool_specs(self) -> List[Tuple[str, Any, str]]:
        return [
            (
                "comp_check",
                self.check_policy,
                "Check if an action complies with enterprise policy.",
            ),
            ("comp_report", self.file_report, "File a regulatory report."),
            (
                "comp_audit",
                self.get_audit_trail,
                "Retrieve the compliance audit trail.",
            ),
            (
                "comp_flag",
                self.flag_violation,
                "Flag a potential policy violation for review.",
            ),
        ]
