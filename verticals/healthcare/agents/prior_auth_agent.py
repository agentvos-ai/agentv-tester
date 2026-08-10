
from pydantic import BaseModel, Field

from core.mcp_agent import BaseMCPAgent
from core.registry import register_agent


class PriorAuthInput(BaseModel):
    patient_id: str = Field(..., description="Patient identifier.")
    procedure_code: str = Field(..., description="Procedure CPT code.")
    decision: str = Field(
        ..., pattern="^(APPROVE|DENY)$", description="Authorization decision."
    )


class PriorAuthOutput(BaseModel):
    status: str = Field(..., description="Result status.")
    auth_id: str = Field(default="", description="Unique authorization transaction ID.")
    error: str = Field(default="", description="Rejection reason details.")


@register_agent("prior_auth_agent")
class PriorAuthAgent(BaseMCPAgent):
    """
    AutoGen negotiation agent for clinical policy checks.
    Uses healthcare-mcp server to check policy criteria and submit decisions.
    """

    mcp_server_script = "mcp_servers/healthcare_mcp/server.py"

    @property
    def system_prompt(self) -> str:
        return """You are a Prior-Authorization Agent.
To submit an authorization decision:
1. Retrieve patient diagnosis codes.
2. Retrieve the payer policy for the procedure code.
3. Check if policy criteria are met.
4. If criteria are met, submit procedure authorization as APPROVED. If missing requirements, reject/deny or request clarifications.
5. Invoke `submit_authorization_decision` tool to commit the decision.
"""

    @property
    def input_schema(self) -> type[BaseModel]:
        return PriorAuthInput

    @property
    def output_schema(self) -> type[BaseModel]:
        return PriorAuthOutput
