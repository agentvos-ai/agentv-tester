from typing import Literal

from pydantic import BaseModel, Field

from core.mcp_agent import BaseMCPAgent
from core.registry import register_agent


class PriorAuthInput(BaseModel):
    patient_id: str = Field(..., description="Patient identifier.")
    procedure_code: str = Field(..., description="Procedure CPT code.")
    decision: str = Field(
        ..., pattern="^(APPROVE|DENY)$", description="Authorization decision."
    )
    notification_channel: Literal["outbox", "email"] = Field(
        default="outbox",
        description="Notification delivery channel ('outbox' or 'email').",
    )
    notification_destination: str = Field(
        default="provider@clinic.example",
        description="Notification recipient destination or email address.",
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
        return """You are an Industrial Prior-Authorization Agent responsible for clinical policy evaluation.
You must execute the following sequential workflow:
1. Retrieve patient diagnosis codes using `get_patient_diagnosis_codes`.
2. Retrieve payer clinical policy and criteria using `get_payer_policy`.
3. Check if patient records satisfy policy criteria using `check_criteria_met`.
4. If criteria are met, proceed to approve. If criteria are NOT met or an adverse decision (DENY, DELAY, DOWNGRADE) is warranted:
   Per regulatory mandates (WA ESSB 5395 and IA HF 2635), adverse medical necessity decisions require licensed human clinical review.
   Request or record a licensed human clinical review via `record_human_review` or `request_human_review` before attempting to commit.
5. Commit the final authorization decision using `submit_authorization_decision`.
6. Dispatch provider notification using `send_provider_notification`. If notification_channel and notification_destination are provided in the request/context, pass them unchanged to send_provider_notification. Otherwise use the tool defaults.
Provide a concise final summary with authorization ID and determination status.
"""

    @property
    def input_schema(self) -> type[BaseModel]:
        return PriorAuthInput

    @property
    def output_schema(self) -> type[BaseModel]:
        return PriorAuthOutput
