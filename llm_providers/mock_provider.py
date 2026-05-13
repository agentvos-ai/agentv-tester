import logging
import json
from typing import List, Dict, Any
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
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        last_msg = messages[-1].get("content", "").lower()

        # Build history of called tools
        called_tools = []
        for m in messages:
            if m.get("role") == "assistant" and m.get("tool_calls"):
                for tc in m["tool_calls"]:
                    called_tools.append(tc["function"]["name"])

        tool_calls = []
        action = "Final Answer"
        action_input = "Mock response: Analysis complete."

        # Scenario 1: Fraud Detection
        if any(k in last_msg for k in ["transaction", "fraud"]):
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
        elif any(k in last_msg for k in ["node", "fault"]):
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
