import json
import logging
from pathlib import Path
from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("auto-insurance-mcp")

mcp = FastMCP("auto-insurance-mcp")


def get_fixture_path() -> Path:
    return (
        Path(__file__).resolve().parent.parent.parent
        / "fixtures"
        / "synthetic_auto_claims.json"
    )


def load_data() -> dict:
    with open(get_fixture_path(), "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data: dict):
    with open(get_fixture_path(), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


@mcp.tool()
def get_auto_claim(claim_id: str) -> dict:
    """Retrieve details of a submitted auto claim."""
    data = load_data()
    claim = data["claims"].get(claim_id)
    if not claim:
        claim = data.get("adjudicated_claims", {}).get(claim_id)
    if not claim:
        return {"error": f"Auto claim {claim_id} not found"}
    return claim


@mcp.tool()
def verify_accident_report(claim_id: str) -> dict:
    """Verify if a police report has been filed and is valid for the claim."""
    data = load_data()
    claim = data["claims"].get(claim_id)
    if not claim:
        return {"valid": False, "error": "Claim not found"}

    if not claim.get("police_report_filed", False):
        return {
            "valid": False,
            "reason": "No police report filed for high value claim.",
        }
    return {"valid": True, "reason": "Police report is verified."}


@mcp.tool()
def check_policy_coverage(
    policy_id: str, claim_type: str, estimated_cost: float
) -> dict:
    """Verify policy eligibility, apply deductibles, and calculate payout limits."""
    data = load_data()
    policy = data["policies"].get(policy_id)
    if not policy:
        return {"eligible": False, "reason": f"Policy {policy_id} not found"}

    if claim_type not in policy["covered_claims"]:
        return {
            "eligible": False,
            "reason": f"Claim type {claim_type} is not covered under policy {policy_id}.",
        }

    remaining_deductible = max(0.0, policy["deductible"] - policy["deductible_met"])
    payout = estimated_cost - remaining_deductible
    payout = max(0.0, payout)

    if payout > policy["payout_limit"]:
        payout = policy["payout_limit"]

    return {
        "eligible": True,
        "payout_amount": round(payout, 2),
        "deductible_applied": round(remaining_deductible, 2),
        "reason": "Policy coverage verified.",
    }


@mcp.tool()
def detect_suspicious_claim(policy_id: str, claim_type: str) -> dict:
    """Run risk analysis to detect suspicious indicators or fraud flags."""
    # Mock rule: Theft claims on POL-102 trigger suspicion due to lack of police report or early registration
    if policy_id == "POL-102" and claim_type == "Theft":
        return {
            "suspicious": True,
            "reason": "High risk of fraud: Theft claim registered without police report.",
        }
    return {"suspicious": False, "reason": "No suspicious activity detected."}


@mcp.tool()
def submit_auto_adjudication(
    claim_id: str, decision: str, payout_amount: float, comment: str = ""
) -> dict:
    """Commit the final auto claim adjudication decision (APPROVE/DENY). (Mutating commit tool)"""
    data = load_data()
    claim = data["claims"].get(claim_id)
    if not claim:
        return {"status": "failed", "error": f"Claim {claim_id} not found"}

    claim["status"] = "ADJUDICATED"
    claim["decision"] = decision.upper()
    claim["payout_amount"] = payout_amount
    claim["comment"] = comment

    if "adjudicated_claims" not in data:
        data["adjudicated_claims"] = {}

    data["adjudicated_claims"][claim_id] = claim

    if claim_id in data["claims"]:
        del data["claims"][claim_id]

    save_data(data)
    logger.info(
        f"Auto claim {claim_id} adjudicated: {decision.upper()} with payout {payout_amount}"
    )
    return {"claim_id": claim_id, "status": "completed", "decision": decision.upper()}


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
