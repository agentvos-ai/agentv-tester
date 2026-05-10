from typing import List, Any
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

    def get_tool_specs(self) -> List[Any]:
        tools = []
        for s in ["database", "calendar", "email", "support_desk"]:
            if s in self._shims:
                tools.extend(self._shims[s].get_tool_specs())
        return tools
