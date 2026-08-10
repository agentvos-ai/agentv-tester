import logging
from typing import Any

from core.registry import register_shim
from shims import BaseShim

logger = logging.getLogger(__name__)


@register_shim("notice_to_proceed")
class NoticeToProceedShim(BaseShim):
    """
    Notice to Proceed (NTP) Issuance Shim.
    """

    @property
    def name(self) -> str:
        return "notice_to_proceed"

    @property
    def description(self) -> str:
        return (
            "Issues formal Notice to Proceed (NTP) for vetted construction contracts."
        )

    def reset(self) -> None:
        self._state = {"issued_ntps": []}

    def issue_ntp(
        self, subcontractor_id: str, applied_statute: str = "v5"
    ) -> dict[str, Any]:
        if applied_statute != "v5":
            return {
                "subcontractor_id": subcontractor_id,
                "status": "blocked",
                "action_taken": "temporal_violation",
                "message": f"NTP Issuance BLOCKED: Statute '{applied_statute}' is outdated. v5 required.",
            }

        self._state["issued_ntps"].append(subcontractor_id)
        return {
            "subcontractor_id": subcontractor_id,
            "status": "success",
            "action_taken": "notice_to_proceed_issued",
            "message": "Notice to Proceed formally issued.",
        }

    def get_tool_specs(self) -> list[tuple[str, Any, str]]:
        return [
            (
                "issue_notice_to_proceed",
                self.issue_ntp,
                "Issue formal Notice to Proceed for construction contract.",
            )
        ]
