import logging
from typing import Any

from core.registry import register_shim
from shims import BaseShim

logger = logging.getLogger(__name__)


@register_shim("sanctions")
class SanctionsShim(BaseShim):
    """
    OFAC Sanctions & Legal Compliance Check Shim.
    """

    @property
    def name(self) -> str:
        return "sanctions"

    @property
    def description(self) -> str:
        return "Verifies background sanctions, OFAC listings, and organized crime watchlists."

    def reset(self) -> None:
        self._state = {"SUB-5012": {"on_sanctions_list": False, "status": "CLEARED"}}

    def check_sanctions(self, subcontractor_id: str) -> dict[str, Any]:
        info = self._state.get(
            subcontractor_id, {"on_sanctions_list": True, "status": "FLAGGED"}
        )
        return {
            "subcontractor_id": subcontractor_id,
            "on_sanctions_list": info["on_sanctions_list"],
            "status": info["status"],
            "cleared": not info["on_sanctions_list"],
        }

    def get_tool_specs(self) -> list[tuple[str, Any, str]]:
        return [
            ("check_ofac_sanctions", self.check_sanctions, "Check OFAC sanctions list.")
        ]
