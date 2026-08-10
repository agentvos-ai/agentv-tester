import logging
from typing import Any

from core.registry import register_shim
from shims import BaseShim

logger = logging.getLogger(__name__)


@register_shim("insurance")
class InsuranceShim(BaseShim):
    """
    Industrial Insurance & Certificate of Insurance (COI) Verification Shim.
    """

    @property
    def name(self) -> str:
        return "insurance"

    @property
    def description(self) -> str:
        return (
            "Verifies subcontractor insurance certificates (COI) and coverage limits."
        )

    def reset(self) -> None:
        self._state = {
            "SUB-5012": {
                "status": "ACTIVE",
                "coverage_usd": 15000000.0,
                "expiration": "2027-12-31",
            }
        }

    def verify_coi(
        self, subcontractor_id: str, required_coverage_usd: float = 10000000.0
    ) -> dict[str, Any]:
        coi = self._state.get(
            subcontractor_id, {"status": "UNKNOWN", "coverage_usd": 0.0}
        )
        is_valid = (
            coi["status"] == "ACTIVE" and coi["coverage_usd"] >= required_coverage_usd
        )
        return {
            "subcontractor_id": subcontractor_id,
            "status": coi["status"],
            "coverage_usd": coi["coverage_usd"],
            "required_coverage_usd": required_coverage_usd,
            "is_valid": is_valid,
        }

    def get_tool_specs(self) -> list[tuple[str, Any, str]]:
        return [
            (
                "check_insurance_certificate",
                self.verify_coi,
                "Verify subcontractor Certificate of Insurance (COI).",
            )
        ]
