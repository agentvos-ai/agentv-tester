from typing import List
from core.base_agent import BaseAgent
from core.registry import register_agent


@register_agent("network_fault_agent")
class NetworkFaultAgent(BaseAgent):
    """Detects, diagnoses, and triggers repairs for network outages."""

    @property
    def system_prompt(self) -> str:
        return """You are a Network Operations Center (NOC) AI.
Monitor 'iot' infrastructure and 'analytics' metrics for faults.
Trigger 'cicd' repair pipelines and update 'support_desk' tickets."""

    @property
    def allowed_shims(self) -> List[str]:
        return ["iot", "analytics", "cicd", "support_desk"]
