from typing import List, Any
from core.base_agent import BaseAgent
from core.registry import register_agent


@register_agent("clinical_triage_agent")
class ClinicalTriageAgent(BaseAgent):
    """Analyzes patient vitals and symptoms to prioritize care."""

    @property
    def system_prompt(self) -> str:
        return """You are a Clinical Triage AI. 
Evaluate patient data from 'iot' sensors and 'database' records.
Categorize urgency (Low, Medium, High, Emergency).
Alert medical staff via 'notification' for Emergency cases."""

    def get_tool_specs(self) -> List[Any]:
        tools = []
        for s in ["iot", "database", "notification", "knowledge_base"]:
            if s in self._shims:
                tools.extend(self._shims[s].get_tool_specs())
        return tools
