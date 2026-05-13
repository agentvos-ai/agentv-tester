from typing import List
from core.base_agent import BaseAgent
from core.registry import register_agent


@register_agent("loan_underwriting_agent")
class LoanUnderwritingAgent(BaseAgent):
    """Credit bureau calls, policy compliance, multi-step approval workflow, notifies applicant."""

    @property
    def system_prompt(self) -> str:
        return """You are an AI Loan Underwriter. You evaluate loan applications for creditworthiness.
You use databases, credit APIs, and compliance engines. 
You must follow the multi-step approval workflow and notify applicants via email."""

    @property
    def allowed_shims(self) -> List[str]:
        return ["database", "rest_api", "compliance", "workflow", "hitl", "email"]
