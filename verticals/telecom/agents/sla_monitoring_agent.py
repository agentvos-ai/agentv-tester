from typing import List, Any
from core.base_agent import BaseAgent
from core.registry import register_agent

@register_agent("sla_monitoring_agent")
class SlaMonitoringAgent(BaseAgent):
    """Ensures service level agreements are met and calculates penalties."""

    @property
    def system_prompt(self) -> str:
        return """You are an SLA Compliance AI.
Monitor 'analytics' for uptime and latency. 
If SLAs are breached, calculate 'payment' credits and notify customers via 'email'."""

    def get_tool_specs(self) -> List[Any]:
        tools = []
        for s in ["analytics", "payment", "email", "database"]:
            if s in self._shims:
                tools.extend(self._shims[s].get_tool_specs())
        return tools
