
from pydantic import BaseModel, Field

from core.mcp_agent import BaseMCPAgent
from core.registry import register_agent


class ClaimsProcessingInput(BaseModel):
    claim_id: str = Field(..., description="Unique identifier of the claim to process.")


class ClaimsProcessingOutput(BaseModel):
    status: str = Field(..., description="Execution status.")
    decision: str = Field(
        default="", description="Adjudication decision (APPROVED/DENIED)."
    )
    approved_amount: float = Field(
        default=0.0, description="Insurer approved payout amount."
    )
    rejection_reason: str = Field(default="", description="Reason if claim is denied.")


@register_agent("claims_processing_agent")
class ClaimsProcessingAgent(BaseMCPAgent):
    """
    Agent for processing health insurance claims using the claims-mcp server.
    Follows a multi-step workflow:
    1. Retrieve and validate the claim format.
    2. Check for duplicate claims/fraud.
    3. Evaluate eligibility and policy rules (deductibles, co-insurance, coverage limits).
    4. Submit adjudication decision.
    """

    mcp_server_script = "mcp_servers/claims_mcp/server.py"

    @property
    def system_prompt(self) -> str:
        return """You are a Health Insurance Claims Processing Agent.
To process a claim:
1. Retrieve details using `get_claim_status`.
2. Validate format using `validate_claim_format`. If invalid, deny the claim.
3. Check for duplicates using `check_duplicate_claims`. If duplicate claims exist for the same patient, procedure, and date (more than 1 match), deny the claim with reason "Duplicate claim detected".
4. If valid and not a duplicate, verify policy rules using `verify_policy_rules` with the patient's ID, procedure code, and billed amount.
5. If the procedure is not covered or the patient has no policy, deny the claim.
6. Calculate approval payout and submit adjudication using `submit_claim_adjudication`.
"""

    @property
    def input_schema(self) -> type[BaseModel]:
        return ClaimsProcessingInput

    @property
    def output_schema(self) -> type[BaseModel]:
        return ClaimsProcessingOutput
