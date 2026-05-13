from typing import List
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

    @property
    def allowed_shims(self) -> List[str]:
        return ["analytics", "support_desk", "search", "email", "social_media"]
