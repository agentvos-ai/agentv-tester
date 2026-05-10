from typing import List, Any
from core.base_agent import BaseAgent
from core.registry import register_agent


@register_agent("churn_prevention_agent")
class ChurnPreventionAgent(BaseAgent):
    """Identifies customers at risk of leaving and offers incentives."""

    @property
    def system_prompt(self) -> str:
        return """You are a Retention Specialist AI.
Analyze user engagement in 'analytics' and recent 'support_desk' tickets.
Search for competitive 'search' data. Send retention 'email' or 'social_media' DMs."""

    def get_tool_specs(self) -> List[Any]:
        tools = []
        for s in ["analytics", "support_desk", "search", "email", "social_media"]:
            if s in self._shims:
                tools.extend(self._shims[s].get_tool_specs())
        return tools
