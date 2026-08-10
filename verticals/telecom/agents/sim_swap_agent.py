from typing import Any

from pydantic import BaseModel, Field

from core.mcp_agent import BaseMCPAgent
from core.registry import register_agent


class SimSwapInput(BaseModel):
    account_id: str = Field(..., description="Customer account ID.")
    new_device_id: str = Field(
        ..., description="New device IMEI/ID for SIM activation."
    )
    provided_info: dict[str, Any] = Field(
        default_factory=dict, description="Security verification details."
    )


class SimSwapOutput(BaseModel):
    status: str = Field(..., description="Status of the SIM swap execution.")
    swap_id: str = Field(
        default="", description="Unique SIM swap operation ID if successful."
    )
    error: str = Field(default="", description="Security rejection reason.")


@register_agent("sim_swap_agent")
class SimSwapAgent(BaseMCPAgent):
    """
    LangGraph SIM Swap Account Security agent.
    Uses telecom-mcp server to perform strict identity and device risk analysis before triggering SIM swaps.
    """

    mcp_server_script = "mcp_servers/telecom_mcp/server.py"
    mcp_transport = "sse"

    @property
    def system_prompt(self) -> str:
        return """You are a Telecom SIM Swap / Account Security Agent.
To process a SIM Swap request, you must execute these security checks:
1. Verify the customer identity using `verify_customer_identity`.
2. Check for recent account changes using `check_recent_account_changes` (ignore or fail if changes within 24h).
3. Get the device risk score using `check_device_risk_signals`.
4. If risk score is low, identity is verified, and there are no recent password changes, invoke `initiate_sim_swap`.
"""

    @property
    def input_schema(self) -> type[BaseModel]:
        return SimSwapInput

    @property
    def output_schema(self) -> type[BaseModel]:
        return SimSwapOutput
