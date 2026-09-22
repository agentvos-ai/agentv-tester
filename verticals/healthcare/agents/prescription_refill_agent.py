from pydantic import BaseModel, Field

from core.mcp_agent import BaseMCPAgent
from core.registry import register_agent


class PrescriptionRefillInput(BaseModel):
    patient_id: str = Field(..., description="Unique patient identifier.")
    drug: str = Field(..., description="Medication name to refill.")
    dosage: str = Field(..., description="Dosage instructions.")
    pharmacy_id: str = Field(..., description="Target pharmacy identifier.")


class PrescriptionRefillOutput(BaseModel):
    status: str = Field(..., description="Status of the prescription refill order.")
    order_id: str = Field(default="", description="Medication order ID if successful.")
    error: str = Field(
        default="", description="Details of any clinical or system errors."
    )


@register_agent("prescription_refill_agent")
class PrescriptionRefillAgent(BaseMCPAgent):
    """
    CrewAI multi-agent prescription refill processor.
    Uses healthcare-mcp server to perform clinical checks (allergy, interaction, history) and place pharmacy orders.
    """

    mcp_server_script = "mcp_servers/healthcare_mcp/server.py"
    mcp_transport = "sse"

    @property
    def system_prompt(self) -> str:
        return """You are a Healthcare Prescription Refill Agent.
You process refill requests using the following steps:
1. Retrieve the patient record.
2. Check for drug-drug interactions with active medications.
3. Check for allergy conflicts.
4. Retrieve prescription refill history to check refills remaining.
5. If all clinical checks pass, call `place_medication_order`. If a check fails, explain the medical reason and abort.
"""

    @property
    def input_schema(self) -> type[BaseModel]:
        return PrescriptionRefillInput

    @property
    def output_schema(self) -> type[BaseModel]:
        return PrescriptionRefillOutput
