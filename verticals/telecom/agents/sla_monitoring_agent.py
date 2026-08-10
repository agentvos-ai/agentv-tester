
from pydantic import BaseModel, Field

from core.base_agent import BaseAgent
from core.registry import register_agent


class SlaMonitoringInput(BaseModel):
    service_id: str = Field(..., description="ID of the service to monitor.")
    threshold_uptime: float = Field(99.9, ge=0, le=100)
    monitoring_period_hours: int = Field(24, ge=1)


class SlaMonitoringOutput(BaseModel):
    actual_uptime: float = Field(..., ge=0, le=100)
    breach_detected: bool
    penalty_credit_amount: float = Field(
        0.0, description="Amount credited to customer if SLA is breached."
    )


@register_agent("sla_monitoring_agent")
class SlaMonitoringAgent(BaseAgent):
    """Ensures service level agreements are met and calculates penalties."""

    @property
    def system_prompt(self) -> str:
        return """You are an SLA Compliance AI.
Monitor 'analytics' for uptime and latency. 
If SLAs are breached, calculate 'payment' credits and notify customers via 'email'."""

    @property
    def allowed_shims(self) -> list[str]:
        return ["analytics", "payment", "email", "database"]

    @property
    def input_schema(self) -> type[BaseModel]:
        return SlaMonitoringInput

    @property
    def output_schema(self) -> type[BaseModel]:
        return SlaMonitoringOutput
