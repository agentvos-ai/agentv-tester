import json
import logging
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
            if m.get("role") == "assistant":
                if m.get("tool_calls"):
                    for tc in m["tool_calls"]:
                        called_tools.append(tc["function"]["name"])
                # Fallback: parse action from JSON block inside markdown content
                content = m.get("content", "")
                if content and "```json" in content:
                    try:
                        json_str = content.split("```json")[1].split("```")[0].strip()
                        parsed = json.loads(json_str)
                        if "action" in parsed and parsed["action"] not in (
                            "Final Answer",
                            "final answer",
                        ):
                            called_tools.append(parsed["action"])
                    except Exception:
                        pass

        tool_calls = []
        action = "Final Answer"
        action_input = "Mock response: Analysis complete."

        # Scenario 1: Fraud Detection
        if any(k in full_user_text for k in ["transaction", "fraud"]):
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
