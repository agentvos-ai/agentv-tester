import json
import logging
from pathlib import Path
from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("claims-mcp")

mcp = FastMCP("claims-mcp")


def get_fixture_path() -> Path:
    return (
        Path(__file__).resolve().parent.parent.parent
        / "fixtures"
        / "synthetic_claims.json"
    )


def load_data() -> dict:
    with open(get_fixture_path(), "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data: dict):
    with open(get_fixture_path(), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


@mcp.tool()
def get_claim_status(claim_id: str) -> dict:
    """Retrieve the status and details of a submitted claim."""
    data = load_data()
    claim = data["claims"].get(claim_id)
    if not claim:
        # Check adjudicated claims
        claim = data.get("adjudicated_claims", {}).get(claim_id)
    if not claim:
        return {"error": f"Claim {claim_id} not found"}
    return claim


@mcp.tool()
def validate_claim_format(claim_id: str) -> dict:
    """Validate structure and ensure all required fields are present in the claim."""
    data = load_data()
    claim = data["claims"].get(claim_id)
    if not claim:
        return {"valid": False, "error": f"Claim {claim_id} not found"}

    required = [
        "claim_id",
        "patient_id",
        "procedure_code",
        "billed_amount",
        "date_of_service",
    ]
    missing = [field for field in required if field not in claim]
    if missing:
        return {
            "valid": False,
            "error": f"Missing required fields: {', '.join(missing)}",
        }

    if claim["billed_amount"] <= 0:
        return {"valid": False, "error": "Billed amount must be greater than zero."}

    return {"valid": True, "error": ""}


@mcp.tool()
def verify_policy_rules(
    patient_id: str, procedure_code: str, billed_amount: float
) -> dict:
    """Check if the patient has coverage and evaluate remaining policy limits."""
    data = load_data()
    policy = data["insurance_policies"].get(patient_id)
    if not policy:
        return {
            "eligible": False,
            "reason": f"No insurance policy found for patient {patient_id}",
        }

    # Check if procedure is covered
    if procedure_code not in policy["covered_procedures"]:
        return {
            "eligible": False,
            "reason": f"Procedure {procedure_code} is not covered under patient policy.",
        }

    # Calculate patient responsibility vs. insurer payment
    remaining_deductible = max(0.0, policy["deductible"] - policy["deductible_met"])

    patient_responsibility = 0.0
    insurer_payment = 0.0

    current_amount = billed_amount

    if remaining_deductible > 0:
        applied_deductible = min(current_amount, remaining_deductible)
        patient_responsibility += applied_deductible
        current_amount -= applied_deductible

    # Co-insurance
    if current_amount > 0:
        coinsurance_share = current_amount * policy["coinsurance_pct"]
        patient_responsibility += coinsurance_share
        insurer_payment += current_amount - coinsurance_share

    # Check max coverage limit
    if insurer_payment > policy["max_coverage_limit"]:
        excess = insurer_payment - policy["max_coverage_limit"]
        insurer_payment = policy["max_coverage_limit"]
        patient_responsibility += excess

    return {
        "eligible": True,
        "insurer_payment": round(insurer_payment, 2),
        "patient_responsibility": round(patient_responsibility, 2),
        "reason": "Procedure covered. Policy limits evaluated.",
    }


@mcp.tool()
def check_duplicate_claims(
    patient_id: str, procedure_code: str, date_of_service: str
) -> dict:
    """Scan existing claims to identify potential duplicate submissions for the same service and date."""
    data = load_data()

    duplicates = []
    # Check regular claims
    for cid, claim in data["claims"].items():
        if (
            claim["patient_id"] == patient_id
            and claim["procedure_code"] == procedure_code
            and claim["date_of_service"] == date_of_service
        ):
            duplicates.append(cid)

    # Check adjudicated claims
    for cid, claim in data.get("adjudicated_claims", {}).items():
        if (
            claim["patient_id"] == patient_id
            and claim["procedure_code"] == procedure_code
            and claim["date_of_service"] == date_of_service
        ):
            duplicates.append(cid)

    # If the count is > 1 (e.g. including the current one), it's a potential duplicate
    is_duplicate = len(duplicates) > 1
    return {
        "is_duplicate": is_duplicate,
        "duplicate_claim_ids": duplicates,
        "reason": f"Found {len(duplicates)} matching claims on same service date.",
    }


@mcp.tool()
def submit_claim_adjudication(
    claim_id: str, decision: str, approved_amount: float, rejection_reason: str = ""
) -> dict:
    """Submit the final adjudication decision for a claim (APPROVE/DENY). (Mutating commit tool)"""
    data = load_data()
    claim = data["claims"].get(claim_id)
    if not claim:
        return {"status": "failed", "error": f"Claim {claim_id} not found"}

    # Adjudicate
    claim["status"] = "ADJUDICATED"
    claim["decision"] = decision.upper()
    claim["approved_amount"] = approved_amount
    claim["rejection_reason"] = rejection_reason

    if "adjudicated_claims" not in data:
        data["adjudicated_claims"] = {}

    data["adjudicated_claims"][claim_id] = claim

    # Remove from active claims list to reflect completion
    if claim_id in data["claims"]:
        del data["claims"][claim_id]

    save_data(data)
    logger.info(
        f"Claim {claim_id} adjudicated: {decision.upper()} with approved amount {approved_amount}"
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
