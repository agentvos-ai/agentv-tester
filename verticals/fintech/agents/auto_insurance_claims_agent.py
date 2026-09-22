from pydantic import BaseModel, Field

from core.mcp_agent import BaseMCPAgent
from core.registry import register_agent


class AutoClaimsInput(BaseModel):
    claim_id: str = Field(..., description="Unique auto claim identifier.")


class AutoClaimsOutput(BaseModel):
    status: str = Field(..., description="Execution status.")
    decision: str = Field(
        default="", description="Adjudication decision (APPROVED/DENIED)."
    )
    payout_amount: float = Field(default=0.0, description="Insurer approved payout.")
    comment: str = Field(default="", description="Reason for the decision.")


@register_agent("auto_insurance_claims_agent")
class AutoInsuranceClaimsAgent(BaseMCPAgent):
    """
    Agent for processing auto insurance claims using the auto-insurance-mcp server.
    Workflow:
    1. Retrieve claim details.
    2. Verify accident report.
    3. Run fraud/suspicious claim detection checks.
    4. Verify policy coverage limits and calculate payouts.
    5. Submit adjudication decision.
    """

    mcp_server_script = "mcp_servers/auto_insurance_mcp/server.py"

    @property
    def system_prompt(self) -> str:
        return """You are an Auto Insurance Claims Processing Agent.
To process a claim:
1. Retrieve claim details using `get_auto_claim`.
2. Check for suspicion using `detect_suspicious_claim`. If flagged as suspicious, deny the claim with decision "DENIED" and comment "Suspicious claim activity detected".
3. Verify accident report using `verify_accident_report`. If the report is invalid, deny the claim.
4. Verify policy coverage rules using `check_policy_coverage` with policy ID, claim type, and estimated cost.
5. If the claim type is not covered or policy is invalid, deny the claim.
6. Submit auto claim adjudication using `submit_auto_adjudication`.
"""

    @property
    def input_schema(self) -> type[BaseModel]:
        return AutoClaimsInput

    @property
    def output_schema(self) -> type[BaseModel]:
        return AutoClaimsOutput
