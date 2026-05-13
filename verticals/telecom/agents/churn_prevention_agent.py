from typing import List, Type, Dict, Any
from pydantic import BaseModel, Field
from core.base_agent import BaseAgent
from core.registry import register_agent


class ChurnPreventionInput(BaseModel):
    customer_id: str = Field(..., description="Unique ID of the customer.")
    tenure_months: int = Field(..., ge=0)
    usage_data: Dict[str, Any] = Field(default_factory=dict)


class ChurnPreventionOutput(BaseModel):
    churn_probability: float = Field(..., ge=0.0, le=1.0)
    retention_offer: str = Field(..., description="Details of the incentive offered.")
    channel_used: str = Field(..., pattern="^(email|sms|social_media)$")


@register_agent("churn_prevention_agent")
class ChurnPreventionAgent(BaseAgent):
    """Identifies customers at risk of leaving and offers incentives."""

    @property
    def system_prompt(self) -> str:
        return """You are a Retention Specialist AI.
Analyze user engagement in 'analytics' and recent 'support_desk' tickets.
Search for competitive 'search' data. Send retention 'email' or 'social_media' DMs."""

    @property
    def allowed_shims(self) -> List[str]:
        return ["analytics", "support_desk", "search", "email", "social_media"]

    @property
    def input_schema(self) -> Type[BaseModel]:
        return ChurnPreventionInput

    @property
    def output_schema(self) -> Type[BaseModel]:
        return ChurnPreventionOutput
