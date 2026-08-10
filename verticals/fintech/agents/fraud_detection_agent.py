
from pydantic import BaseModel, Field

from core.base_agent import BaseAgent
from core.registry import register_agent


class FraudDetectionInput(BaseModel):
    transaction_id: str = Field(
        ..., description="Unique identifier for the transaction."
    )
    account_id: str = Field(..., description="The ID of the account involved.")
    amount: float = Field(
        ..., gt=0, description="The monetary value of the transaction."
    )


class FraudDetectionOutput(BaseModel):
    risk_score: float = Field(..., ge=0, le=100)
    recommendation: str
    action_taken: str


@register_agent("fraud_detection_agent")
class FraudDetectionAgent(BaseAgent):
    """
    Monitors transactions, applies risk scoring, and files SARs.
    """

    @property
    def system_prompt(self) -> str:
        return """You are a Fraud Detection Specialist. 
Your goal is to analyze transactions for potential fraud.
1. Check transaction history in the 'database'.
2. Calculate risk scores using 'analytics'.
3. If fraud is found (>70 score), file a report using 'compliance'.
4. Notify the security team via 'notification'."""

    @property
    def allowed_shims(self) -> list[str]:
        return ["database", "analytics", "compliance", "notification"]

    @property
    def input_schema(self) -> type[BaseModel]:
        return FraudDetectionInput

    @property
    def output_schema(self) -> type[BaseModel]:
        return FraudDetectionOutput
