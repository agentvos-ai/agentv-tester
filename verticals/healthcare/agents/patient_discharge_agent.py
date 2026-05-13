from typing import List
from core.base_agent import BaseAgent
from core.registry import register_agent


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
