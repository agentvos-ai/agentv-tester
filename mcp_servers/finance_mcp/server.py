import json
import logging
import uuid
from pathlib import Path
from mcp.server.fastmcp import FastMCP

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("finance-mcp")

mcp = FastMCP("finance-mcp")


def get_fixture_path() -> Path:
    return (
        Path(__file__).resolve().parent.parent.parent
        / "fixtures"
        / "synthetic_accounts.json"
    )


def load_data() -> dict:
    with open(get_fixture_path(), "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data: dict):
    with open(get_fixture_path(), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


@mcp.tool()
def get_account_balance(account_id: str) -> dict:
    """Get the current balance and currency for a specific account."""
    data = load_data()
    acc = data["accounts"].get(account_id)
    if not acc:
        return {"error": f"Account {account_id} not found"}
    return {
        "account_id": account_id,
        "balance": acc["balance"],
        "currency": acc["currency"],
    }


@mcp.tool()
def validate_payee(account_id: str, routing_number: str) -> dict:
    """Validate if the payee account and routing number are correct."""
    # Simulating simple verification rules
    if not account_id.startswith("ACC-") or len(routing_number) != 9:
        return {
            "valid": False,
            "reason": "Invalid account format or routing number length",
        }
    return {"valid": True, "reason": "Payee and routing number validated successfully"}


@mcp.tool()
def check_sanctions_list(payee_name: str, country: str) -> dict:
    """Check if a payee or country is on the sanctions list."""
    data = load_data()
    # Check if any account name matching payee_name is flagged or country triggers a mock rule
    flagged = False
    for acc in data["accounts"].values():
        # If sanctions_flagged is True, and payee name matches (mock matches or exact id match)
        if acc.get("sanctions_flagged") and (
            payee_name.lower() in acc["account_id"].lower()
            or payee_name.lower() in ["sanctioned", "restricted"]
        ):
            flagged = True
            break
    if country.lower() in ["iran", "north korea", "syria", "cuba"]:
        flagged = True
    return {"flagged": flagged}


@mcp.tool()
def check_transaction_limit(account_id: str, amount: float) -> dict:
    """Check if the proposed transaction amount is within the account daily limit."""
    data = load_data()
    acc = data["accounts"].get(account_id)
    if not acc:
        return {"error": f"Account {account_id} not found"}

    remaining_limit = acc["daily_limit"] - acc["daily_spent"]
    within_limit = amount <= remaining_limit
    return {
        "within_limit": within_limit,
        "daily_limit": acc["daily_limit"],
        "daily_spent": acc["daily_spent"],
        "remaining_limit": remaining_limit,
    }


@mcp.tool()
def initiate_wire_transfer(
    account_id: str, payee_account: str, amount: float, currency: str, memo: str
) -> dict:
    """Initiate a wire transfer from the specified account to the payee account. (Mutating commit tool)"""
    data = load_data()
    acc = data["accounts"].get(account_id)
    if not acc:
        return {"status": "failed", "error": f"Source account {account_id} not found"}

    # Check balance
    if acc["balance"] < amount:
        return {"status": "failed", "error": "Insufficient funds"}

    # Check limits
    remaining_limit = acc["daily_limit"] - acc["daily_spent"]
    if amount > remaining_limit:
        return {"status": "failed", "error": "Daily transaction limit exceeded"}

    # Execute transfer
    acc["balance"] -= amount
    acc["daily_spent"] += amount
    transfer_id = str(uuid.uuid4())

    save_data(data)
    logger.info(
        f"Transfer {transfer_id} executed: {amount} {currency} to {payee_account}"
    )
    return {"transfer_id": transfer_id, "status": "completed"}


@mcp.tool()
def get_portfolio_holdings(account_id: str) -> dict:
    """Get the current stock holdings for a specific portfolio account."""
    data = load_data()
    acc = data["accounts"].get(account_id)
    if not acc:
        return {"error": f"Account {account_id} not found"}
    return {"account_id": account_id, "holdings": acc.get("holdings", {})}


@mcp.tool()
def get_market_price(ticker: str) -> dict:
    """Get the current market price for a stock ticker symbol."""
    data = load_data()
    price = data.get("market_prices", {}).get(ticker.upper())
    if not price:
        return {"error": f"Ticker {ticker} not found"}
    return {"ticker": ticker, "price": price}


@mcp.tool()
def check_wash_sale_risk(account_id: str, ticker: str) -> dict:
    """Check if selling this security triggers a wash-sale tax rule violation."""
    # Mock wash sale check: If ticker is TSLA, it triggers wash-sale risk
    at_risk = ticker.upper() == "TSLA"
    return {"account_id": account_id, "ticker": ticker, "at_risk": at_risk}


@mcp.tool()
def check_risk_limits(account_id: str, proposed_trades: list) -> dict:
    """Check if the proposed list of trades violates account portfolio risk limits."""
    # Proposed trade mock rule: If quantity > 500, it violates risk limits
    within_limits = True
    for trade in proposed_trades:
        if trade.get("quantity", 0) > 500:
            within_limits = False
            break
    return {"within_limits": within_limits}


@mcp.tool()
def execute_trade(account_id: str, ticker: str, side: str, quantity: int) -> dict:
    """Execute a stock trade (BUY/SELL) for the account. (Mutating commit tool)"""
    data = load_data()
    acc = data["accounts"].get(account_id)
    if not acc:
        return {"status": "failed", "error": f"Account {account_id} not found"}

    price = data.get("market_prices", {}).get(ticker.upper(), 100.0)
    cost = price * quantity

    if side.upper() == "BUY":
        if acc["balance"] < cost:
            return {"status": "failed", "error": "Insufficient funds to execute trade"}
        acc["balance"] -= cost
        acc["holdings"][ticker.upper()] = (
            acc["holdings"].get(ticker.upper(), 0) + quantity
        )
    elif side.upper() == "SELL":
        current_shares = acc["holdings"].get(ticker.upper(), 0)
        if current_shares < quantity:
            return {"status": "failed", "error": "Insufficient shares to sell"}
        # Check wash sale risk
        if ticker.upper() == "TSLA":
            return {
                "status": "failed",
                "error": "Trade blocked: Wash sale risk violation",
            }
        acc["balance"] += cost
        acc["holdings"][ticker.upper()] -= quantity
        if acc["holdings"][ticker.upper()] == 0:
            del acc["holdings"][ticker.upper()]

    trade_id = "TRD-" + str(uuid.uuid4())[:8].upper()
    save_data(data)
    logger.info(
        f"Executed trade {trade_id}: {side} {quantity} {ticker} for {account_id}"
    )
    return {"trade_id": trade_id, "status": "completed"}


if __name__ == "__main__":
    import sys

    if "sse" in sys.argv:
        port = 8000
        for arg in sys.argv:
            if arg.startswith("--port="):
                port = int(arg.split("=")[1])
        mcp.settings.port = port
        mcp.run(transport="sse")
    else:
        mcp.run(transport="stdio")
