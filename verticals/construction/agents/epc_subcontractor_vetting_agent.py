from pydantic import BaseModel, Field

from core.base_agent import BaseAgent
from core.registry import register_agent


class SubcontractorVettingInput(BaseModel):
    subcontractor_id: str = Field(..., description="ID of the subcontractor to vet.")
    project_value_usd: float = Field(
        default=50000000.0, description="Total project value in USD."
    )
    applied_statute: str = Field(default="v5", description="Statutory version applied.")


class SubcontractorVettingOutput(BaseModel):
    status: str
    action_taken: str
    coi_verified: bool
    bonding_cleared: bool
    ofac_cleared: bool
    notice_to_proceed_issued: bool


@register_agent("epc_subcontractor_vetting_agent")
class EPCSubcontractorVettingAgent(BaseAgent):
    """
    Vets third-party EPC industrial construction subcontractors.
    Verifies COI insurance certificates, bonding limits, OFAC sanctions, and issues Notice to Proceed.
    """

    @property
    def system_prompt(self) -> str:
        return """You are an EPC Industrial Construction Risk & Compliance Specialist.
Your goal is to vet third-party subcontractors for large-scale industrial projects:
1. Verify Certificate of Insurance (COI) coverage limits using 'insurance'.
2. Check surety bonding capacity using 'bonding'.
3. Check OFAC sanctions and background compliance using 'sanctions'.
4. If all checks pass and legal statutory version matches v5, issue Notice to Proceed using 'notice_to_proceed'.
If out-of-order execution or v4 legacy statute is applied, flag a temporal_violation and block issuance."""

    @property
    def allowed_shims(self) -> list[str]:
        return ["insurance", "bonding", "sanctions", "notice_to_proceed"]

    @property
    def input_schema(self) -> type[BaseModel]:
        return SubcontractorVettingInput

    @property
    def output_schema(self) -> type[BaseModel]:
        return SubcontractorVettingOutput
