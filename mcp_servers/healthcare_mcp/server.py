import json
import logging
import os
import smtplib
import sys
import uuid
from email.mime.text import MIMEText
from pathlib import Path

try:
    from mcp.server.fastmcp import FastMCP
except (ImportError, ModuleNotFoundError):
    from mcp.server.mcpserver import MCPServer as FastMCP

# Ensure repo root is on sys.path for direct script execution
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from server.authorization_state_service import AuthorizationStateService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("healthcare-mcp")

mcp = FastMCP("healthcare-mcp")

_state_service: AuthorizationStateService | None = None


def get_state_service() -> AuthorizationStateService:
    global _state_service
    if _state_service is None:
        _state_service = AuthorizationStateService()
    return _state_service


def get_fixture_path() -> Path:
    return (
        Path(__file__).resolve().parent.parent.parent
        / "fixtures"
        / "synthetic_patients.json"
    )


def load_data() -> dict:
    with open(get_fixture_path(), "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data: dict):
    with open(get_fixture_path(), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


@mcp.tool()
def get_patient_record(patient_id: str) -> dict:
    """Retrieve medical history, active medications, allergies, and conditions for a patient."""
    data = load_data()
    pat = data["patients"].get(patient_id)
    if not pat:
        return {"error": f"Patient {patient_id} not found"}
    return {
        "patient_id": patient_id,
        "name": pat["name"],
        "medications": pat["medications"],
        "allergies": pat["allergies"],
        "conditions": pat["conditions"],
    }


@mcp.tool()
def check_drug_interactions(patient_id: str, new_drug: str) -> dict:
    """Check if the new drug has any negative interactions with the patient's current medications."""
    data = load_data()
    pat = data["patients"].get(patient_id)
    if not pat:
        return {"error": f"Patient {patient_id} not found"}

    # Simple mock rules for drug-drug interactions
    interactions = []
    current_meds = [m.lower() for m in pat["medications"]]
    new_drug_lower = new_drug.lower()

    # Mock interaction: Lisinopril and Sildenafil (just a mock example)
    if "lisinopril" in current_meds and new_drug_lower in ["sildenafil", "viagra"]:
        interactions.append(
            "Severe risk of hypotension when Sildenafil is co-administered with Lisinopril."
        )
    # Mock interaction: Lipitor and Erythromycin
    if "lipitor" in current_meds and new_drug_lower in [
        "erythromycin",
        "clarithromycin",
    ]:
        interactions.append("Increased risk of myopathy/rhabdomyolysis.")

    return {"interactions": interactions}


@mcp.tool()
def check_allergy_conflict(patient_id: str, new_drug: str) -> dict:
    """Check if the patient is allergic to the new drug."""
    data = load_data()
    pat = data["patients"].get(patient_id)
    if not pat:
        return {"error": f"Patient {patient_id} not found"}

    conflicts = []
    allergies = [a.lower() for a in pat["allergies"]]
    new_drug_lower = new_drug.lower()

    # Check for exact match or class matches
    for allergy in allergies:
        if allergy in new_drug_lower:
            conflicts.append(f"Patient has documented allergy to {allergy}.")
        elif allergy == "penicillin" and new_drug_lower in [
            "amoxicillin",
            "ampicillin",
            "penicillin",
        ]:
            conflicts.append(
                "Patient allergic to Penicillins; potential cross-reactivity."
            )

    return {"conflict": len(conflicts) > 0, "conflicts": conflicts}


@mcp.tool()
def get_prescription_history(patient_id: str, drug: str) -> dict:
    """Check refill history and refills remaining for a drug."""
    data = load_data()
    pat = data["patients"].get(patient_id)
    if not pat:
        return {"error": f"Patient {patient_id} not found"}

    # Search prescriptions
    rx_details = pat.get("prescriptions", {}).get(drug)
    if not rx_details:
        # Check case insensitivity
        for k, v in pat.get("prescriptions", {}).items():
            if k.lower() == drug.lower():
                rx_details = v
                break

    if not rx_details:
        return {
            "refills_remaining": 0,
            "last_filled": "Never",
            "error": "No prescription found",
        }

    return {
        "refills_remaining": rx_details["refills_remaining"],
        "last_filled": rx_details["last_filled"],
    }


@mcp.tool()
def place_medication_order(
    patient_id: str, drug: str, dosage: str, pharmacy_id: str
) -> dict:
    """Place a medication order for a patient. (Mutating commit tool)"""
    data = load_data()
    pat = data["patients"].get(patient_id)
    if not pat:
        return {"status": "failed", "error": f"Patient {patient_id} not found"}

    # Check allergies
    allergies = [a.lower() for a in pat["allergies"]]
    if any(a in drug.lower() for a in allergies) or (
        any("penicillin" in a for a in allergies)
        and any(p in drug.lower() for p in ["amoxicillin", "ampicillin", "penicillin"])
    ):
        return {"status": "failed", "error": f"Allergy conflict detected for {drug}"}

    # Check refills
    rx = pat.get("prescriptions", {}).get(drug)
    if not rx:
        # Check case insensitive
        for k, v in pat.get("prescriptions", {}).items():
            if k.lower() == drug.lower():
                rx = v
                drug = k
                break

    if not rx or rx["refills_remaining"] <= 0:
        return {
            "status": "failed",
            "error": "No refills remaining / prescription not authorized",
        }

    # Update refills
    rx["refills_remaining"] -= 1
    order_id = str(uuid.uuid4())

    save_data(data)
    logger.info(f"Medication order {order_id} placed for {drug}")
    return {"order_id": order_id, "status": "completed"}


@mcp.tool()
def get_patient_diagnosis_codes(patient_id: str) -> dict:
    """Retrieve diagnosis ICD codes for a specific patient."""
    data = load_data()
    pat = data["patients"].get(patient_id)
    if not pat:
        return {"error": f"Patient {patient_id} not found"}
    return {"patient_id": patient_id, "icd_codes": pat.get("icd_codes", [])}


@mcp.tool()
def get_payer_policy(procedure_code: str) -> dict:
    """Retrieve payer policy details and approval criteria for a procedure CPT code."""
    data = load_data()
    policy = data.get("payer_policies", {}).get(procedure_code.upper())
    if not policy:
        return {"error": f"Policy for {procedure_code} not found"}
    return {"procedure_code": procedure_code, "criteria": policy["criteria"]}


@mcp.tool()
def check_criteria_met(patient_id: str, procedure_code: str) -> dict:
    """Evaluate whether the patient meets policy criteria for the procedure."""
    data = load_data()
    pat = data["patients"].get(patient_id)
    if not pat:
        return {"error": f"Patient {patient_id} not found"}

    # Check procedure policy mapping in patient record
    policy = pat.get("procedure_policy", {}).get(procedure_code.upper())
    if not policy:
        return {
            "met": False,
            "missing": ["No clinical records found matching procedure policy"],
        }

    return {"met": policy["criteria_met"], "missing": policy.get("missing", [])}


@mcp.tool()
def request_human_review(
    patient_id: str, procedure_code: str, reason: str = ""
) -> dict:
    """Request human physician review for adverse or complex prior-authorization."""
    request_record = get_state_service().create_human_review_request(
        patient_id, procedure_code, reason
    )
    external_mode = (
        os.environ.get("PHYSICIAN_REVIEW_MODE", "auto").lower() == "external"
    )
    delivery = (
        _send_review_email(request_record)
        if external_mode
        else {"status": "not_sent", "message": "Automatic review mode is active."}
    )
    return {
        "status": "pending_physician_review"
        if external_mode
        else "auto_review_pending",
        "request_id": request_record["request_id"],
        "patient_id": patient_id,
        "procedure_code": procedure_code.upper(),
        "reason": reason
        or "Clinical criteria not satisfied; physician adjudication required.",
        "review_notification": delivery,
    }


def _send_review_email(request_record: dict) -> dict:
    """Deliver the opaque review URL using the existing SMTP configuration."""
    recipient = os.environ.get("PHYSICIAN_REVIEW_EMAIL")
    token = request_record.pop("_approval_token", None)
    if not token:
        return {"status": "already_requested"}
    base_url = os.environ.get("REVIEW_PUBLIC_BASE_URL", "http://localhost:8080").rstrip(
        "/"
    )
    approval_url = f"{base_url}/healthcare/physician-review/{token}"
    smtp_host = os.environ.get("SMTP_HOST")
    if not recipient or not smtp_host:
        return {
            "status": "not_configured",
            "message": "Set PHYSICIAN_REVIEW_EMAIL and SMTP_HOST to deliver the review link.",
        }
    smtp_port = int(os.environ.get("SMTP_PORT", "25"))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")
    message = MIMEText(
        "A physician review is waiting. Open the secure review form:\n\n"
        f"{approval_url}\n\n"
        "Do not forward this link. It contains no patient details."
    )
    message["Subject"] = "Physician review required"
    message["From"] = os.environ.get(
        "SMTP_FROM", smtp_user or "notifications@um-portal.org"
    )
    message["To"] = recipient
    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            if smtp_user and smtp_pass:
                server.starttls()
                server.login(smtp_user, smtp_pass)
            server.send_message(message)
        return {"status": "sent", "transport": "smtp", "destination": recipient}
    except Exception as exc:
        logger.warning("Unable to send physician review email: %s", exc)
        return {"status": "failed", "transport": "smtp", "destination": recipient}


def send_physician_policy_block_email(procedure_code: str, review_id: str) -> dict:
    """Inform the reviewing physician that an approval could not pass policy controls."""
    recipient = os.environ.get("PHYSICIAN_REVIEW_EMAIL")
    smtp_host = os.environ.get("SMTP_HOST")
    if not recipient or not smtp_host:
        return {"status": "not_configured"}
    message = MIMEText(
        f"Your approval for prior authorization {procedure_code} (review {review_id}) could not be enacted.\n\n"
        "The request remains blocked because the required clinical policy criteria were not met. "
        "No authorization decision or provider notification was issued."
    )
    message["Subject"] = "Physician approval blocked by policy"
    message["From"] = os.environ.get(
        "SMTP_FROM", os.environ.get("SMTP_USER", "notifications@um-portal.org")
    )
    message["To"] = recipient
    try:
        with smtplib.SMTP(
            smtp_host, int(os.environ.get("SMTP_PORT", "25")), timeout=10
        ) as server:
            if os.environ.get("SMTP_USER") and os.environ.get("SMTP_PASS"):
                server.starttls()
                server.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"])
            server.send_message(message)
        return {"status": "sent", "transport": "smtp", "destination": recipient}
    except Exception as exc:
        logger.warning("Unable to send physician policy-block email: %s", exc)
        return {"status": "failed", "transport": "smtp", "destination": recipient}


@mcp.tool()
def record_human_review(
    patient_id: str,
    procedure_code: str,
    reviewer_id: str = "MD-LIC-4491",
    reviewer_type: str = "LICENSED_PHYSICIAN",
    disposition: str = "DENY",
    clinical_notes: str = "Medical necessity criteria not satisfied following clinical peer review",
    request_id: str | None = None,
) -> dict:
    """Record a completed licensed clinical human review artifact in durable state."""
    service = get_state_service()
    if request_id:
        completed = service.complete_human_review_request(
            request_id,
            patient_id=patient_id,
            procedure_code=procedure_code,
            reviewer_id=reviewer_id,
            reviewer_type=reviewer_type,
            disposition=disposition,
            clinical_notes=clinical_notes,
        )
        review = completed["review"]
    else:
        review = service.record_human_review(
            patient_id=patient_id,
            procedure_code=procedure_code,
            reviewer_id=reviewer_id,
            reviewer_type=reviewer_type,
            disposition=disposition,
            clinical_notes=clinical_notes,
        )
    return {
        "status": "completed",
        "review_id": review["review_id"],
        "disposition": review["disposition"],
        "reviewer_id": review["reviewer_id"],
        "reviewed_at": review["reviewed_at"],
    }


@mcp.tool()
def get_human_review_status(request_id: str) -> dict:
    """Return the vendor-neutral durable status of an external physician review."""
    service = get_state_service()
    request_record = service.get_human_review_request(request_id)
    if not request_record:
        return {"status": "not_found", "request_id": request_id}
    result = {"request_id": request_id, "status": request_record["status"]}
    if request_record["status"] == "COMPLETED":
        result["review"] = service.get_human_review_by_id(request_record["review_id"])
    return result


@mcp.tool()
def submit_authorization_decision(
    patient_id: str, procedure_code: str, decision: str
) -> dict:
    """
    Submit a final prior-authorization decision (APPROVE/DENY). (Mutating commit tool)
    Enforces Washington ESSB 5395 and Iowa HF 2635:
    Adverse outcomes require licensed human review before committing.
    State is persisted to durable SQLite storage.
    """
    data = load_data()
    pat = data["patients"].get(patient_id)
    if not pat:
        return {"status": "failed", "error": f"Patient {patient_id} not found"}

    policy = pat.get("procedure_policy", {}).get(procedure_code.upper())
    criteria_met = bool(policy and policy.get("criteria_met"))
    clean_decision = decision.upper().strip()

    # Check criteria met if requesting approval
    if clean_decision == "APPROVE":
        if not policy or not policy.get("criteria_met"):
            missing_reqs = (
                policy.get("missing", ["Missing policy criteria evaluation"])
                if policy
                else ["No policy matched"]
            )
            return {
                "status": "failed",
                "error": f"Authorization denied: Criteria not met. Missing: {', '.join(missing_reqs)}",
            }

    # For adverse decisions (DENY, DELAY, DOWNGRADE) or failed criteria, verify human review
    service = get_state_service()
    if clean_decision in ("DENY", "DELAY", "DOWNGRADE") or not criteria_met:
        review = service.get_latest_human_review(patient_id, procedure_code)
        if os.environ.get("PHYSICIAN_REVIEW_MODE", "auto").lower() == "external":
            completed_request = service.get_completed_human_review(
                patient_id, procedure_code
            )
            if not completed_request:
                pending = service.get_pending_human_review(patient_id, procedure_code)
                return {
                    "status": "waiting_for_manual_review",
                    "message": "Licensed physician review is required before the adverse decision can continue.",
                    "review_request_id": pending["request_id"] if pending else None,
                }
            review = service.get_human_review_by_id(completed_request["review_id"])
        if not review:
            return {
                "status": "failed",
                "error": (
                    f"Adverse decision '{decision}' cannot commit: Licensed clinical human review "
                    "artifact required under WA ESSB 5395 and IA HF 2635."
                ),
                "human_review_required": True,
            }

    try:
        record = service.commit_authorization(
            patient_id=patient_id,
            procedure_code=procedure_code,
            decision=clean_decision,
            criteria_met=criteria_met,
        )
        auth_id = record["authorization_id"]
        logger.info(
            f"Prior-auth {auth_id} committed to durable state for {patient_id}: {decision}"
        )
        return {
            "auth_id": auth_id,
            "status": "completed" if clean_decision == "APPROVE" else "denied",
            "record": record,
        }
    except Exception as e:
        logger.error(f"Failed to commit authorization for {patient_id}: {e}")
        return {"status": "failed", "error": str(e)}


@mcp.tool()
def send_provider_notification(
    authorization_id: str,
    channel: str = "outbox",
    destination: str = "provider@clinic.example",
    message: str = "",
) -> dict:
    """Send an authorization notification via durable outbox or configured SMTP."""
    service = get_state_service()
    try:
        notif = service.send_provider_notification(
            authorization_id=authorization_id,
            channel=channel,
            destination=destination,
            message=message,
        )
        return {
            "status": "completed",
            "notification_id": notif["notification_id"],
            "authorization_id": authorization_id,
            "delivery_status": notif["status"],
            "channel": notif["channel"],
            "destination": notif["destination"],
            "delivery_attempted": notif["delivery_attempted"],
            "transport": notif["transport"],
            "delivery_receipt": notif["delivery_receipt"],
        }
    except Exception as e:
        logger.error(
            f"Failed to send provider notification for {authorization_id}: {e}"
        )
        return {"status": "failed", "error": str(e)}


if __name__ == "__main__":
    # This module is also imported by the Flask review-resume route.  Flask
    # owns environment loading, while a standalone MCP process must load its
    # own configuration exactly once.
    from dotenv import load_dotenv

    load_dotenv()
    import sys

    if "sse" in sys.argv:
        port = 8000
        for arg in sys.argv:
            if arg.startswith("--port="):
                port = int(arg.split("=")[1])
        try:
            mcp.run(transport="sse", port=port)
        except TypeError:
            if hasattr(mcp, "settings"):
                mcp.settings.port = port
            mcp.run(transport="sse")
    else:
        mcp.run(transport="stdio")
