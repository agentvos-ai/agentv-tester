from typing import List, Dict, Any
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

    def get_tool_specs(self) -> List[Dict[str, Any]]:
        tools = []
        for shim_name in ["database", "rest_api", "compliance", "workflow", "hitl", "email"]:
            if shim_name in self._shims:
                tools.extend(self._shims[shim_name].get_tool_specs())
        return tools
