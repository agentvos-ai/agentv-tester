from typing import List, Type, Dict, Any
from pydantic import BaseModel, Field
from core.base_agent import BaseAgent
from core.registry import register_agent


class MedicationReconciliationInput(BaseModel):
    patient_id: str = Field(..., description="Unique ID of the patient.")
    current_medications: List[str] = Field(
        ..., description="List of medications the patient is currently taking."
    )
    admission_id: str = Field(
        None, description="Optional hospital admission reference."
    )


class MedicationReconciliationOutput(BaseModel):
    discrepancies: List[Dict[str, Any]] = Field(
        default_factory=list, description="Found interaction risks or duplicates."
    )
    reconciled_list: List[str] = Field(
        ..., description="The verified and corrected list of medications."
    )
    clinical_note: str


@register_agent("medication_reconciliation_agent")
class MedicationReconciliationAgent(BaseAgent):
    """Compares current meds with medical history to find discrepancies."""

    @property
    def system_prompt(self) -> str:
        return """You are a Medication Reconciliation AI.
Compare the current medication list from the 'rest_api' with the patient history in the 'database'.
Check for interactions or duplicates using 'knowledge_base'."""

    @property
    def allowed_shims(self) -> List[str]:
        return ["rest_api", "database", "knowledge_base", "analytics"]

    @property
    def input_schema(self) -> Type[BaseModel]:
        return MedicationReconciliationInput

    @property
    def output_schema(self) -> Type[BaseModel]:
        return MedicationReconciliationOutput
