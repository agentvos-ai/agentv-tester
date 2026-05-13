from typing import List
from core.base_agent import BaseAgent
from core.registry import register_agent


@register_agent("provisioning_agent")
class ProvisioningAgent(BaseAgent):
    """Automates the activation of new customer services."""

    @property
    def system_prompt(self) -> str:
        return """You are a Service Provisioning AI.
Process orders from 'rest_api', update 'database' records, and trigger 'workflow' for activation.
Verify 'compliance' with regional telecommunications laws."""

    @property
    def allowed_shims(self) -> List[str]:
        return ["rest_api", "database", "workflow", "compliance"]
