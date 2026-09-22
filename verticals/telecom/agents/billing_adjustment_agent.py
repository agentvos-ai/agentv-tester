from pydantic import BaseModel, Field

from core.mcp_agent import BaseMCPAgent
from core.registry import register_agent


class BillingAdjustmentInput(BaseModel):
    account_id: str = Field(..., description="Customer account ID.")
    amount: float = Field(..., description="Credit amount requested.")
    reason: str = Field(..., description="Reason for billing adjustment.")
    charge_id: str = Field(..., description="Underlying disputed charge ID.")
    agent_role: str = Field(
        "tier1_support", description="Support representative role level."
    )


class BillingAdjustmentOutput(BaseModel):
    status: str = Field(..., description="Result of billing credit issue.")
    credit_id: str = Field(default="", description="Billing credit ID if successful.")
    error: str = Field(default="", description="Error description if rejected.")


@register_agent("billing_adjustment_agent")
class BillingAdjustmentAgent(BaseMCPAgent):
    """
    LangChain customer billing adjustments agent.
    Uses telecom-mcp server to review dispute logs, verify validity, and issue billing credits.
    """

    mcp_server_script = "mcp_servers/telecom_mcp/server.py"

    @property
    def system_prompt(self) -> str:
        return """You are a Telecom Billing Adjustment Agent.
To issue a credit:
1. Retrieve customer account plan, balance, and dispute history.
2. Retrieve billing history for the customer.
3. Check dispute validity for the specified charge.
4. Verify if credit amount is within the agent's authority limit.
5. If valid and authorized, call `issue_billing_credit` to commit the credit.
"""

    @property
    def input_schema(self) -> type[BaseModel]:
        return BillingAdjustmentInput

    @property
    def output_schema(self) -> type[BaseModel]:
        return BillingAdjustmentOutput
