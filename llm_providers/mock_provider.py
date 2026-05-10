from typing import List, Dict, Any
from core.base_llm import BaseLLMProvider
from core.registry import register_llm

@register_llm("mock")
class MockLLMProvider(BaseLLMProvider):
    """
    Deterministic Mock LLM for integration testing.
    Returns pre-programmed responses based on message content.
    """

    def chat(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]] | None = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        last_msg = messages[-1]["content"].lower()
        
        # Simple rule-based mock
        if "fraud" in last_msg:
            content = "I have checked the transaction and it looks suspicious. I will file a SAR."
        else:
            content = "Mock response from the AI assistant."

        return {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": content,
                    "tool_calls": []
                }
            }],
            "usage": {"total_tokens": 10}
        }

    def stream(self, messages, tools=None, **kwargs):
        yield {"content": "Mock stream"}

    @property
    def supports_tool_calling(self) -> bool:
        return True
