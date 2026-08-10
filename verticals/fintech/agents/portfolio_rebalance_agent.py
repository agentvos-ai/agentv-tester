
from pydantic import BaseModel, Field

from core.mcp_agent import BaseMCPAgent
from core.registry import register_agent


class PortfolioRebalanceInput(BaseModel):
    account_id: str = Field(..., description="Unique client account ID.")
    ticker: str = Field(..., description="Stock ticker symbol to rebalance.")
    side: str = Field(
        ..., pattern="^(BUY|SELL)$", description="Order side: BUY or SELL."
    )
    quantity: int = Field(..., ge=1, description="Quantity of shares.")


class PortfolioRebalanceOutput(BaseModel):
    status: str = Field(..., description="Status of the trade order execution.")
    trade_id: str = Field(default="", description="Trade ID if successful.")
    error: str = Field(default="", description="Error details if execution failed.")


@register_agent("portfolio_rebalance_agent")
class PortfolioRebalanceAgent(BaseMCPAgent):
    """
    LangGraph stateful graph agent that manages portfolio rebalancing.
    Connects to the finance-mcp server to perform holdings lookups, risk assessment, and execute trades.
    """

    mcp_server_script = "mcp_servers/finance_mcp/server.py"
    mcp_transport = "sse"

    @property
    def system_prompt(self) -> str:
        return """You are an AI Portfolio Rebalancing Agent.
To execute a rebalancing order:
1. Retrieve portfolio holdings for the account.
2. Check market price of the ticker.
3. Check for wash sale risks.
4. Check risk limits for the proposed trade.
5. If all validations are successful, call `execute_trade`.
"""

    @property
    def input_schema(self) -> type[BaseModel]:
        return PortfolioRebalanceInput

    @property
    def output_schema(self) -> type[BaseModel]:
        return PortfolioRebalanceOutput
