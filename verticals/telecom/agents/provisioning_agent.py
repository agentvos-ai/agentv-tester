
from pydantic import BaseModel, Field

from core.base_agent import BaseAgent
from core.registry import register_agent


class ProvisioningInput(BaseModel):
    order_id: str = Field(..., description="Unique ID of the service order.")
    customer_id: str = Field(
        ..., description="ID of the customer for whom service is being provisioned."
    )
    service_type: str = Field(
        ..., description="Type of service (e.g., 5G-UNLIMITED, FIBER-1G)."
    )


class ProvisioningOutput(BaseModel):
    activation_status: str = Field(..., description="ACTIVE, PENDING, or FAILED.")
    provisioned_resources: list[str] = Field(
        default_factory=list, description="IDs of allocated network resources."
    )
    error_log: str = Field(None)


@register_agent("provisioning_agent")
class ProvisioningAgent(BaseAgent):
    """Automates the activation of new customer services."""

    @property
    def system_prompt(self) -> str:
        return """You are a Service Provisioning AI.
Process orders from 'rest_api', update 'database' records, and trigger 'workflow' for activation.
Verify 'compliance' with regional telecommunications laws."""

    @property
    def allowed_shims(self) -> list[str]:
        return ["rest_api", "database", "workflow", "compliance"]

    @property
    def input_schema(self) -> type[BaseModel]:
        return ProvisioningInput

    @property
    def output_schema(self) -> type[BaseModel]:
        return ProvisioningOutput
