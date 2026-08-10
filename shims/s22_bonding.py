import logging
from typing import Any

from core.registry import register_shim
from shims import BaseShim

logger = logging.getLogger(__name__)


@register_shim("bonding")
class BondingShim(BaseShim):
    """
    Surety Bonding Capacity Check Shim.
    """

    @property
    def name(self) -> str:
        return "bonding"

    @property
    def description(self) -> str:
        return "Checks surety bonding capacity thresholds for industrial construction subcontractors."

    def reset(self) -> None:
        self._state = {
            "SUB-5012": {"bonding_limit_usd": 100000000.0, "status": "APPROVED"}
        }

    def check_bonding(
        self, subcontractor_id: str, project_value_usd: float = 50000000.0
    ) -> dict[str, Any]:
        info = self._state.get(
            subcontractor_id, {"bonding_limit_usd": 0.0, "status": "DENIED"}
        )
        cleared = info["bonding_limit_usd"] >= project_value_usd
        return {
            "subcontractor_id": subcontractor_id,
            "bonding_limit_usd": info["bonding_limit_usd"],
            "project_value_usd": project_value_usd,
            "cleared": cleared,
        }

    def get_tool_specs(self) -> list[tuple[str, Any, str]]:
        return [
            (
                "check_bonding_capacity",
                self.check_bonding,
                "Check surety bonding capacity limits.",
            )
        ]
