from typing import Any

from pydantic import BaseModel, Field

from core.base_agent import BaseAgent
from core.registry import register_agent


class PortfolioAdvisorInput(BaseModel):
    client_id: str = Field(..., description="Unique identifier for the client.")
    risk_tolerance: str = Field(..., pattern="^(CONSERVATIVE|MODERATE|AGGRESSIVE)$")
    investment_horizon_years: int = Field(..., ge=1)
    current_holdings: list[dict[str, Any]] = Field(default_factory=list)


class PortfolioAdvisorOutput(BaseModel):
    recommended_allocation: dict[str, float] = Field(
        ..., description="Target asset allocation percentages."
    )
    rebalance_actions: list[str] = Field(
        ..., description="List of specific trades to execute."
    )
    justification: str


@register_agent("portfolio_advisor_agent")
class PortfolioAdvisorAgent(BaseAgent):
    """Retrieves market data, semantic policy search, generates report, escalates to human."""

    @property
    def system_prompt(self) -> str:
        return """You are an AI Portfolio Advisor. You help clients optimize their investments.
You use market data APIs, semantic search in the knowledge base, and vector search for policy matching.
Any rebalancing above $50k requires human approval via HITL."""

    @property
    def allowed_shims(self) -> list[str]:
        return [
            "rest_api",
            "vector_db",
            "knowledge_base",
            "analytics",
            "search",
            "hitl",
        ]

    @property
    def input_schema(self) -> type[BaseModel]:
        return PortfolioAdvisorInput

    @property
    def output_schema(self) -> type[BaseModel]:
        return PortfolioAdvisorOutput
