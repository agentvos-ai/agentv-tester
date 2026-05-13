from typing import List
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

    @property
    def allowed_shims(self) -> List[str]:
        return ["compliance", "database", "workflow", "hitl"]
