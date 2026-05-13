from typing import List
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

    @property
    def allowed_shims(self) -> List[str]:
        return ["analytics", "payment", "email", "database"]
