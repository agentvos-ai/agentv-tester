from typing import List, Any
from core.base_agent import BaseAgent
from core.registry import register_agent


@register_agent("prior_auth_agent")
class PriorAuthAgent(BaseAgent):
    """Processes insurance prior-authorization requests."""

    @property
    def system_prompt(self) -> str:
        return """You are a Prior Authorization Agent.
Process requests by checking insurance 'compliance' rules and patient 'database' records.
Initiate 'workflow' for approval. Escalate to 'hitl' for complex denials."""

    def get_tool_specs(self) -> List[Any]:
        tools = []
        for s in ["compliance", "database", "workflow", "hitl"]:
            if s in self._shims:
                tools.extend(self._shims[s].get_tool_specs())
        return tools
