from typing import List, Dict, Any
from core.base_agent import BaseAgent
from core.registry import register_agent

@register_agent("portfolio_advisor_agent")
class PortfolioAdvisorAgent(BaseAgent):
    """Retrieves market data, semantic policy search, generates report, escalates to human."""

    @property
    def system_prompt(self) -> str:
        return """You are an AI Portfolio Advisor. You help clients optimize their investments.
You use market data APIs, semantic search in the knowledge base, and vector search for policy matching.
Any rebalancing above $50k requires human approval via HITL."""

    def get_tool_specs(self) -> List[Dict[str, Any]]:
        tools = []
        for shim_name in ["rest_api", "vector_db", "knowledge_base", "analytics", "search", "hitl"]:
            if shim_name in self._shims:
                tools.extend(self._shims[shim_name].get_tool_specs())
        return tools
