import os
from collections.abc import Generator
from typing import Any

import anthropic

from core.base_llm import BaseLLMProvider
from core.errors import LLMProviderError
from core.registry import register_llm


@register_llm("claude")
class ClaudeProvider(BaseLLMProvider):
    """
    Anthropic Claude Provider implementation.
    Normalizes Anthropic SDK format to OpenAI-compatible structures.
    """

    def __init__(self, config: Any):
        super().__init__(config)
        api_key = os.environ.get(config.api_key_env)
        if not api_key:
            raise LLMProviderError(
                f"API key environment variable '{config.api_key_env}' not set."
            )

        self.client = anthropic.Anthropic(api_key=api_key)

    def chat(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Synchronous chat completion with format normalization."""
        try:
            # Extract system message
            system_msg = next(
                (m["content"] for m in messages if m["role"] == "system"), ""
            )
            user_msgs = [m for m in messages if m["role"] != "system"]

            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=kwargs.get("max_tokens", 4096),
                system=system_msg,
                messages=user_msgs,  # type: ignore
                tools=tools or [],  # type: ignore
                temperature=kwargs.get("temperature", 0.1),
            )

            # Normalize to OpenAI-compatible dict
            return {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": response.content[0].text
                            if hasattr(response.content[0], "text")
                            else "",
                            "tool_calls": self._parse_tool_calls(response),
                        }
                    }
                ],
                "usage": {
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens
                    + response.usage.output_tokens,
                },
            }
        except Exception as e:
            raise LLMProviderError(f"Claude chat failed: {e!s}") from e

    def stream(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> Generator[dict[str, Any], None, None]:
        """Full industrial streaming implementation for Claude."""
        try:
            system_msg = next(
                (m["content"] for m in messages if m["role"] == "system"), ""
            )
            user_msgs = [m for m in messages if m["role"] != "system"]

            with self.client.messages.stream(
                model=self.config.model,
                max_tokens=kwargs.get("max_tokens", 4096),
                system=system_msg,
                messages=user_msgs,  # type: ignore
                tools=tools or [],  # type: ignore
                temperature=kwargs.get("temperature", 0.1),
            ) as stream:
                for event in stream:
                    # Normalize stream events to OpenAI-compatible chunks
                    if event.type == "text":
                        yield {
                            "choices": [{"delta": {"content": event.text}, "index": 0}]
                        }
                    elif event.type == "tool_use":
                        yield {
                            "choices": [
                                {
                                    "delta": {
                                        "tool_calls": [
                                            {
                                                "id": event.id,
                                                "function": {"name": event.name},
                                            }
                                        ]
                                    },
                                    "index": 0,
                                }
                            ]
                        }
        except Exception as e:
            raise LLMProviderError(f"Claude stream failed: {e!s}") from e

    @property
    def supports_tool_calling(self) -> bool:
        return True

    def _parse_tool_calls(self, response: Any) -> list[dict[str, Any]]:
        tool_calls = []
        for block in response.content:
            if block.type == "tool_use":
                tool_calls.append(
                    {
                        "id": block.id,
                        "type": "function",
                        "function": {"name": block.name, "arguments": str(block.input)},
                    }
                )
        return tool_calls
