from typing import List, Type, Dict
from pydantic import BaseModel, Field
from core.base_agent import BaseAgent
from core.registry import register_agent


class PatientDischargeInput(BaseModel):
    patient_id: str = Field(
        ..., description="Unique ID of the patient to be discharged."
    )
    discharge_date: str = Field(..., description="Target discharge date (ISO format).")
    requirements: List[str] = Field(
        default_factory=lambda: ["med_recon", "followup_check"]
    )


class PatientDischargeOutput(BaseModel):
    readiness_score: float = Field(..., ge=0, le=100)
    checklist_status: Dict[str, bool] = Field(
        ..., description="Status of all discharge tasks."
    )
    summary_report: str


@register_agent("patient_discharge_agent")
class PatientDischargeAgent(BaseAgent):
    """Orchestrates the patient discharge process."""

    @property
    def system_prompt(self) -> str:
        return """You are a Discharge Coordination AI.
Coordinate discharge by verifying status in 'database', scheduling follow-ups in 'calendar', 
and sending instructions via 'email'."""

    @property
    def allowed_shims(self) -> List[str]:
        return ["database", "calendar", "email", "support_desk"]

    @property
    def input_schema(self) -> Type[BaseModel]:
        return PatientDischargeInput

    @property
    def output_schema(self) -> Type[BaseModel]:
        return PatientDischargeOutput
