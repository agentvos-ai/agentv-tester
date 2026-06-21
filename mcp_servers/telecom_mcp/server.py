import json
import logging
import uuid
from pathlib import Path
from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("telecom-mcp")

mcp = FastMCP("telecom-mcp")

def get_fixture_path() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "fixtures" / "synthetic_customers.json"

def load_data() -> dict:
    with open(get_fixture_path(), "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data: dict):
    with open(get_fixture_path(), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

@mcp.tool()
def get_customer_account(account_id: str) -> dict:
    """Retrieve customer plan, balance, and dispute history."""
    data = load_data()
    cust = data["customers"].get(account_id)
    if not cust:
        return {"error": f"Customer {account_id} not found"}
    return {
        "account_id": account_id,
        "name": cust["name"],
        "plan": cust["plan"],
        "balance": cust["balance"],
        "dispute_history": cust["dispute_history"]
    }

@mcp.tool()
def get_billing_history(account_id: str, period: str) -> dict:
    """Retrieve billing charges for a specific period (e.g. '2026-05')."""
    data = load_data()
    cust = data["customers"].get(account_id)
    if not cust:
        return {"error": f"Customer {account_id} not found"}
    
    charges = [
        {"charge_id": cid, **cinfo}
        for cid, cinfo in cust.get("billing_history", {}).items()
        if cinfo["period"] == period
    ]
    return {"charges": charges}

@mcp.tool()
def check_dispute_validity(account_id: str, charge_id: str) -> dict:
    """Check if the dispute for a given charge_id is valid based on factual records."""
    data = load_data()
    cust = data["customers"].get(account_id)
    if not cust:
        return {"valid": False, "reason": "Customer not found"}
    
    charge = cust.get("billing_history", {}).get(charge_id)
    if not charge:
        return {"valid": False, "reason": "Charge not found"}
    
    # If the charge description contains 'overlimit' or 'late fee', we might mock it as valid to dispute,
    # otherwise if it's standard monthly service charge, it's valid to bill (meaning invalid to dispute)
    if "monthly" in charge["description"].lower():
        return {"valid": False, "reason": "Standard recurring monthly fee matches plan subscription."}
    
    return {"valid": True, "reason": "Factual dispute verified for one-time charge."}

@mcp.tool()
def check_credit_authority_limit(agent_role: str, amount: float) -> dict:
    """Verify if the agent's role has the authority to issue a credit of this amount."""
    # Mock limits
    limits = {
        "tier1_support": 50.0,
        "tier2_support": 250.0,
        "manager": 1000.0
    }
    allowed_limit = limits.get(agent_role.lower(), 0.0)
    return {
        "within_authority": amount <= allowed_limit,
        "allowed_limit": allowed_limit
    }

@mcp.tool()
def issue_billing_credit(account_id: str, amount: float, reason: str) -> dict:
    """Issue a billing credit/refund to a customer's account. (Mutating commit tool)"""
    data = load_data()
    cust = data["customers"].get(account_id)
    if not cust:
        return {"status": "failed", "error": f"Customer {account_id} not found"}
    
    # Update balance and add credit to dispute history
    cust["balance"] -= amount
    credit_id = "CRED-" + str(uuid.uuid4())[:8].upper()
    cust["dispute_history"].append({
        "dispute_id": credit_id,
        "amount": amount,
        "status": "credited",
        "reason": reason
    })
    
    save_data(data)
    logger.info(f"Billing credit {credit_id} of {amount} issued to {account_id}")
    return {"credit_id": credit_id, "status": "completed"}

@mcp.tool()
def verify_customer_identity(account_id: str, provided_info: dict) -> dict:
    """Verify customer identity based on security questions and account credentials."""
    data = load_data()
    cust = data["customers"].get(account_id)
    if not cust:
        return {"verified": False, "confidence": 0.0}
    
    # Simple rule-based identity verification
    verified = cust.get("security_question_verified", False)
    confidence = 1.0 if verified else 0.4
    return {"verified": verified, "confidence": confidence}

@mcp.tool()
def check_recent_account_changes(account_id: str) -> dict:
    """Check for recent password resets, address updates, or email changes in the last 24h."""
    data = load_data()
    cust = data["customers"].get(account_id)
    if not cust:
        return {"error": "Customer not found"}
    return {"recent_changes": cust.get("recent_changes", [])}

@mcp.tool()
def check_device_risk_signals(account_id: str, device_info: dict) -> dict:
    """Get the risk score associated with the customer's current requesting device."""
    data = load_data()
    cust = data["customers"].get(account_id)
    if not cust:
        return {"error": "Customer not found"}
    return {"risk_score": cust.get("device_risk_score", 0.0)}

@mcp.tool()
def initiate_sim_swap(account_id: str, new_device_id: str) -> dict:
    """Initiate a SIM swap / number port request to a new device. (Mutating commit tool)"""
    data = load_data()
    cust = data["customers"].get(account_id)
    if not cust:
        return {"status": "failed", "error": f"Customer {account_id} not found"}
    
    # Rule checks (SIM swap has high risk constraints)
    # Check recent account changes (e.g. password resets in last hour)
    recent_changes = cust.get("recent_changes", [])
    if recent_changes:
        return {"status": "failed", "error": "SIM swap blocked: Suspicious recent account changes detected within 24h"}
        
    # Check device risk score
    if cust.get("device_risk_score", 0.0) > 0.7:
        return {"status": "failed", "error": "SIM swap blocked: Requesting device has a high risk score"}
        
    # Check verification status
    if not cust.get("security_question_verified", False):
        return {"status": "failed", "error": "SIM swap blocked: Customer security verification failed"}

    swap_id = "SWAP-" + str(uuid.uuid4())[:8].upper()
    cust["recent_changes"].append({
        "change_type": "sim_swap",
        "timestamp": "2026-06-22T03:00:00Z"
    })
    
    save_data(data)
    logger.info(f"SIM Swap {swap_id} completed successfully for account {account_id} to device {new_device_id}")
    return {"swap_id": swap_id, "status": "completed"}

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


