import json
import logging
import re
from typing import Any

from core.base_llm import BaseLLMProvider
from core.registry import register_llm

logger = logging.getLogger(__name__)


@register_llm("mock")
class MockLLMProvider(BaseLLMProvider):
    """
    Stateful Simulator LLM for high-fidelity integration testing.
    Can simulate multi-turn tool calling sequences based on task keywords.
    Provides LangChain JSON-style response formatting.
    """

    def __init__(self, config: Any):
        super().__init__(config)

    def chat(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        # Collect all user messages to determine active scenario
        user_contents = []
        for m in messages:
            if m.get("role") == "user":
                user_contents.append(m.get("content", "").lower())
        full_user_text = " ".join(user_contents)

        # Build history of called tools
        called_tools = []
        for m in messages:
            content = str(m.get("content", ""))
            if m.get("tool_calls"):
                for tc in m["tool_calls"]:
                    called_tools.append(tc["function"]["name"])
            if m.get("role") == "tool" and m.get("name"):
                called_tools.append(m.get("name"))
            if "```json" in content:
                for block in content.split("```json")[1:]:
                    try:
                        json_str = block.split("```")[0].strip()
                        parsed = json.loads(json_str)
                        act = parsed.get("action")
                        if act and act not in ("Final Answer", "final answer"):
                            called_tools.append(act)
                    except Exception:
                        pass
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith("Action:") and not stripped.startswith("Action: Final Answer"):
                    act_val = stripped.split("Action:", 1)[1].strip().strip("`")
                    if act_val and not act_val.startswith("{") and act_val not in ("Final Answer", "final answer"):
                        called_tools.append(act_val)

        tool_calls = []
        action = "Final Answer"
        action_input = "Mock response: Analysis complete."

        # Extract available tool names if tools spec was provided
        avail_tools = set()
        if tools:
            for t in tools:
                if isinstance(t, dict):
                    if "function" in t:
                        avail_tools.add(t["function"].get("name", ""))
                    elif "name" in t:
                        avail_tools.add(t.get("name", ""))

        # Scenario 0: Healthcare Prior-Authorization (Happy and Adverse Flows)
        is_prior_auth = (
            any(
                k in full_user_text
                for k in [
                    "prior-auth",
                    "prior_auth",
                    "prior auth",
                    "cpt-99213",
                    "cpt-33510",
                    "hc-pa",
                    "authorization",
                ]
            )
            or "submit_authorization_decision" in avail_tools
            or "get_patient_diagnosis_codes" in avail_tools
        )

        if is_prior_auth:
            is_adverse = any(
                k in full_user_text
                for k in ["pat-002", "cpt-33510", "hc-pa-fault", "deny", "denial", "adverse"]
            )
            patient_id = "PAT-002" if is_adverse else "PAT-001"
            procedure_code = "CPT-33510" if is_adverse else "CPT-99213"

            # Parse auth_id if present from previous tool responses in message history
            auth_id = "AUTH-MOCK-001"
            for m in messages:
                c = str(m.get("content", ""))
                match = re.search(r"AUTH-[A-Za-z0-9]+", c)
                if match:
                    auth_id = match.group(0)
                    break

            if "get_patient_diagnosis_codes" not in called_tools:
                action = "get_patient_diagnosis_codes"
                action_input = {"patient_id": patient_id}
                tool_calls.append(
                    {
                        "id": "call_pa_diag_1",
                        "type": "function",
                        "function": {"name": action, "arguments": action_input},
                    }
                )
            elif "get_payer_policy" not in called_tools:
                action = "get_payer_policy"
                action_input = {"procedure_code": procedure_code}
                tool_calls.append(
                    {
                        "id": "call_pa_policy_1",
                        "type": "function",
                        "function": {"name": action, "arguments": action_input},
                    }
                )
            elif "check_criteria_met" not in called_tools:
                action = "check_criteria_met"
                action_input = {
                    "patient_id": patient_id,
                    "procedure_code": procedure_code,
                }
                tool_calls.append(
                    {
                        "id": "call_pa_criteria_1",
                        "type": "function",
                        "function": {"name": action, "arguments": action_input},
                    }
                )
            elif is_adverse and "request_human_review" not in called_tools:
                action = "request_human_review"
                action_input = {
                    "patient_id": patient_id,
                    "procedure_code": procedure_code,
                    "reason": "Criteria not met: missing stress test report and cardiology referral.",
                }
                tool_calls.append(
                    {
                        "id": "call_pa_hrev_req_1",
                        "type": "function",
                        "function": {"name": action, "arguments": action_input},
                    }
                )
            elif is_adverse and "record_human_review" not in called_tools:
                action = "record_human_review"
                action_input = {
                    "patient_id": patient_id,
                    "procedure_code": procedure_code,
                    "reviewer_id": "MD-LIC-4491",
                    "reviewer_type": "LICENSED_PHYSICIAN",
                    "disposition": "DENY",
                    "clinical_notes": "Licensed physician review confirmed absence of required stress test and cardiology consult.",
                }
                tool_calls.append(
                    {
                        "id": "call_pa_hrev_rec_1",
                        "type": "function",
                        "function": {"name": action, "arguments": action_input},
                    }
                )
            elif "submit_authorization_decision" not in called_tools:
                action = "submit_authorization_decision"
                action_input = {
                    "patient_id": patient_id,
                    "procedure_code": procedure_code,
                    "decision": "DENY" if is_adverse else "APPROVE",
                }
                tool_calls.append(
                    {
                        "id": "call_pa_submit_1",
                        "type": "function",
                        "function": {"name": action, "arguments": action_input},
                    }
                )
            elif "send_provider_notification" not in called_tools:
                action = "send_provider_notification"
                action_input = {
                    "authorization_id": auth_id,
                    "channel": "outbox",
                    "destination": "provider@clinic.example",
                    "message": (
                        f"Prior authorization {procedure_code} DENIED following physician review."
                        if is_adverse
                        else f"Prior authorization {procedure_code} APPROVED for {patient_id}."
                    ),
                }
                tool_calls.append(
                    {
                        "id": "call_pa_notify_1",
                        "type": "function",
                        "function": {"name": action, "arguments": action_input},
                    }
                )
            else:
                action = "Final Answer"
                action_input = (
                    f"Prior authorization for {patient_id} / {procedure_code} processed: "
                    f"{'DENIED following licensed physician review' if is_adverse else 'APPROVED'}; "
                    f"provider notified."
                )

        # Scenario 1: Fraud Detection
        elif any(k in full_user_text for k in ["transaction", "fraud"]):
            if "db_query" not in called_tools:
                action = "db_query"
                action_input = {"query": "SELECT * FROM transactions"}
                tool_calls.append(
                    {
                        "id": "call_db_1",
                        "type": "function",
                        "function": {
                            "name": action,
                            "arguments": action_input,
                        },  # Use dict for LangChain compatibility
                    }
                )
            elif "comp_check" not in called_tools:
                action = "comp_check"
                action_input = {
                    "resource_id": "T-123",
                    "check_type": "AML",
                    "data": {"amount": 5000},
                }
                tool_calls.append(
                    {
                        "id": "call_comp_1",
                        "type": "function",
                        "function": {"name": action, "arguments": action_input},
                    }
                )
            else:
                action = "Final Answer"
                action_input = "Industrial analysis complete: SAR filed and verified."

        # Scenario 2: Network Fault
        elif any(k in full_user_text for k in ["node", "fault"]):
            if "iot_read" not in called_tools:
                action = "iot_read"
                action_input = {"device_id": "sensor-01"}
                tool_calls.append(
                    {
                        "id": "call_iot_1",
                        "type": "function",
                        "function": {"name": action, "arguments": action_input},
                    }
                )
            else:
                action = "Final Answer"
                action_input = "Network diagnostic complete: Node is stable."

        # Scenario 4: Auto Insurance Claims Processing
        elif any(
            k in full_user_text for k in ["auto claim", "auto claims", "auto insurance"]
        ):
            if "get_auto_claim" not in called_tools:
                action = "get_auto_claim"
                action_input = {
                    "claim_id": "AUTO-CLAIM-002"
                    if "auto-claim-002" in full_user_text
                    else "AUTO-CLAIM-001"
                }
                tool_calls.append(
                    {
                        "id": "call_auto_claim_get",
                        "type": "function",
                        "function": {"name": action, "arguments": action_input},
                    }
                )
            elif "detect_suspicious_claim" not in called_tools:
                action = "detect_suspicious_claim"
                action_input = {
                    "policy_id": "POL-102"
                    if "auto-claim-002" in full_user_text
                    else "POL-101",
                    "claim_type": "Theft"
                    if "auto-claim-002" in full_user_text
                    else "Collision",
                }
                tool_calls.append(
                    {
                        "id": "call_auto_claim_susp",
                        "type": "function",
                        "function": {"name": action, "arguments": action_input},
                    }
                )
            elif (
                "verify_accident_report" not in called_tools
                and "auto-claim-002" not in full_user_text
            ):
                action = "verify_accident_report"
                action_input = {"claim_id": "AUTO-CLAIM-001"}
                tool_calls.append(
                    {
                        "id": "call_auto_claim_rep",
                        "type": "function",
                        "function": {"name": action, "arguments": action_input},
                    }
                )
            elif (
                "check_policy_coverage" not in called_tools
                and "auto-claim-002" not in full_user_text
            ):
                action = "check_policy_coverage"
                action_input = {
                    "policy_id": "POL-101",
                    "claim_type": "Collision",
                    "estimated_cost": 1200.00,
                }
                tool_calls.append(
                    {
                        "id": "call_auto_claim_cov",
                        "type": "function",
                        "function": {"name": action, "arguments": action_input},
                    }
                )
            elif "submit_auto_adjudication" not in called_tools:
                action = "submit_auto_adjudication"
                if "auto-claim-002" in full_user_text:
                    action_input = {
                        "claim_id": "AUTO-CLAIM-002",
                        "decision": "DENIED",
                        "payout_amount": 0.0,
                        "comment": "Suspicious claim activity detected",
                    }
                else:
                    action_input = {
                        "claim_id": "AUTO-CLAIM-001",
                        "decision": "APPROVED",
                        "payout_amount": 1200.00,
                        "comment": "Adjudicated successfully",
                    }
                tool_calls.append(
                    {
                        "id": "call_auto_claim_adj",
                        "type": "function",
                        "function": {"name": action, "arguments": action_input},
                    }
                )
            else:
                action = "Final Answer"
                if "auto-claim-002" in full_user_text:
                    action_input = "Auto claim AUTO-CLAIM-002 processed: DENIED due to suspicion of fraud."
                else:
                    action_input = (
                        "Auto claim AUTO-CLAIM-001 processed: APPROVED for $1200.00."
                    )

        # Scenario 3: Claims Processing
        elif any(k in full_user_text for k in ["claim", "claims"]):
            if "get_claim_status" not in called_tools:
                action = "get_claim_status"
                action_input = {
                    "claim_id": "CLAIM-002"
                    if "claim-002" in full_user_text
                    else "CLAIM-001"
                }
                tool_calls.append(
                    {
                        "id": "call_claim_status",
                        "type": "function",
                        "function": {"name": action, "arguments": action_input},
                    }
                )
            elif "validate_claim_format" not in called_tools:
                action = "validate_claim_format"
                action_input = {
                    "claim_id": "CLAIM-002"
                    if "claim-002" in full_user_text
                    else "CLAIM-001"
                }
                tool_calls.append(
                    {
                        "id": "call_claim_val",
                        "type": "function",
                        "function": {"name": action, "arguments": action_input},
                    }
                )
            elif "check_duplicate_claims" not in called_tools:
                action = "check_duplicate_claims"
                action_input = {
                    "patient_id": "PAT-001",
                    "procedure_code": "CPT-99213",
                    "date_of_service": "2026-06-25",
                }
                tool_calls.append(
                    {
                        "id": "call_claim_dup",
                        "type": "function",
                        "function": {"name": action, "arguments": action_input},
                    }
                )
            elif (
                "verify_policy_rules" not in called_tools
                and "claim-002" not in full_user_text
            ):
                action = "verify_policy_rules"
                action_input = {
                    "patient_id": "PAT-001",
                    "procedure_code": "CPT-99213",
                    "billed_amount": 150.00,
                }
                tool_calls.append(
                    {
                        "id": "call_claim_pol",
                        "type": "function",
                        "function": {"name": action, "arguments": action_input},
                    }
                )
            elif "submit_claim_adjudication" not in called_tools:
                action = "submit_claim_adjudication"
                if "claim-002" in full_user_text:
                    action_input = {
                        "claim_id": "CLAIM-002",
                        "decision": "DENY",
                        "approved_amount": 0.0,
                        "rejection_reason": "Duplicate claim detected",
                    }
                else:
                    action_input = {
                        "claim_id": "CLAIM-001",
                        "decision": "APPROVE",
                        "approved_amount": 120.00,
                    }
                tool_calls.append(
                    {
                        "id": "call_claim_adj",
                        "type": "function",
                        "function": {"name": action, "arguments": action_input},
                    }
                )
            else:
                action = "Final Answer"
                if "claim-002" in full_user_text:
                    action_input = (
                        "Claim CLAIM-002 processed: DENIED due to duplicate submission."
                    )
                else:
                    action_input = "Claim CLAIM-001 processed: APPROVED for $120.00."

        # Format as Markdown JSON block for LangChain parser
        content = f'```json\n{{\n  "action": "{action}",\n  "action_input": {json.dumps(action_input)}\n}}\n```'

        return {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": content,
                        "tool_calls": tool_calls,
                    }
                }
            ],
            "usage": {"total_tokens": 50},
        }

    def stream(self, messages, tools=None, **kwargs):
        yield self.chat(messages, tools, **kwargs)

    @property
    def supports_tool_calling(self) -> bool:
        return True
