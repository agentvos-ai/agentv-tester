
from pydantic import BaseModel, Field

from core.base_agent import BaseAgent
from core.registry import register_agent


class ClinicalTriageInput(BaseModel):
    patient_id: str = Field(..., description="Unique identifier for the patient.")
    symptoms: list[str] = Field(..., description="List of symptoms reported.")
    vital_signs: dict = Field(
        default_factory=dict, description="Current vital signs (HR, BP, etc.)"
    )


class ClinicalTriageOutput(BaseModel):
    severity: str = Field(..., description="Triage level (e.g., URGENT, ROUTINE).")
    department: str
    recommended_action: str


@register_agent("clinical_triage_agent")
class ClinicalTriageAgent(BaseAgent):
    """
    Performs initial clinical assessment and department routing.
    """

    @property
    def system_prompt(self) -> str:
        return """You are a Clinical Triage Specialist.
Analyze patient symptoms and vital signs to determine the appropriate department and urgency.
1. Consult the 'knowledge_base' for clinical protocols.
2. Review patient history in the 'database'.
3. Escalate to 'hitl' if symptoms are life-threatening or ambiguous."""

    @property
    def allowed_shims(self) -> list[str]:
        return ["knowledge_base", "database", "hitl"]

    @property
    def input_schema(self) -> type[BaseModel]:
        return ClinicalTriageInput

    @property
    def output_schema(self) -> type[BaseModel]:
        return ClinicalTriageOutput
