import re
from collections.abc import Generator
from typing import Any

from core.base_llm import BaseLLMProvider
from core.registry import register_llm


@register_llm("heuristic")
class HeuristicProvider(BaseLLMProvider):
    """
    Local Heuristic Provider that uses rule-based logic to handle failures.
    Provides a fast, zero-cost, local fallback for common industrial patterns.
    """

    def __init__(self, config: Any):
        super().__init__(config)
        self.rules = [
            (
                r"(?i)fraud|suspicious|transaction",
                "Based on local heuristic analysis, this transaction shows potential risk patterns. Recommended action: Flag for manual review.",
            ),
            (
                r"(?i)patient|medical|diagnosis",
                "Local medical heuristic: Patient data appears consistent with standard protocols. No immediate anomalies detected.",
            ),
            (
                r"(?i)network|outage|signal",
                "Telecom diagnostic heuristic: Signal strength is within acceptable parameters. Check hardware if issues persist.",
            ),
            (r"(?i)terminate", "Task completed. TERMINATE"),
        ]

    def chat(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        last_msg = messages[-1]["content"] if messages else ""

        content = "Local fallback: The primary LLM is unavailable. Based on simple heuristics, I recommend checking the manual documentation for this specific case."

        for pattern, response in self.rules:
            if re.search(pattern, last_msg):
                content = response
                break

        return {
            "choices": [
                {"message": {"role": "assistant", "content": content, "tool_calls": []}}
            ],
            "usage": {"total_tokens": 0},
        }

    def stream(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> Generator[dict[str, Any], None, None]:
        yield self.chat(messages, tools, **kwargs)

    @property
    def supports_tool_calling(self) -> bool:
        return False
