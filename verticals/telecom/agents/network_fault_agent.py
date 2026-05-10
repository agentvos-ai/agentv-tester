from typing import List, Any
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

    def get_tool_specs(self) -> List[Any]:
        tools = []
        for s in ["iot", "analytics", "cicd", "support_desk"]:
            if s in self._shims:
                tools.extend(self._shims[s].get_tool_specs())
        return tools
