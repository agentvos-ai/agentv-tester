from typing import List, Any
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

    def get_tool_specs(self) -> List[Any]:
        tools = []
        for s in ["rest_api", "database", "workflow", "compliance"]:
            if s in self._shims:
                tools.extend(self._shims[s].get_tool_specs())
        return tools
