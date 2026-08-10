
from pydantic import BaseModel, Field

from core.base_agent import BaseAgent
from core.registry import register_agent


class NetworkFaultInput(BaseModel):
    node_id: str = Field(
        ..., description="The ID of the network node experiencing issues."
    )
    fault_type: str = Field(
        ..., description="Reported fault type (e.g., PACKET_LOSS, LATENCY)."
    )
    priority: int = Field(default=1, ge=1, le=5)


class NetworkFaultOutput(BaseModel):
    root_cause: str
    resolution_status: str
    maintenance_ticket: str | None


@register_agent("network_fault_agent")
class NetworkFaultAgent(BaseAgent):
    """
    Diagnoses and resolves network infrastructure faults.
    """

    @property
    def system_prompt(self) -> str:
        return """You are a Network Operations Engineer.
Diagnose network faults by checking real-time IoT data and historical logs.
1. Read sensor data from 'iot' for the specific node.
2. Check previous maintenance logs in the 'database'.
3. Trigger 'cicd' pipelines for automated network re-routing if needed."""

    @property
    def allowed_shims(self) -> list[str]:
        return ["iot", "database", "cicd"]

    @property
    def input_schema(self) -> type[BaseModel]:
        return NetworkFaultInput

    @property
    def output_schema(self) -> type[BaseModel]:
        return NetworkFaultOutput
