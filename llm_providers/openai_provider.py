import os
from collections.abc import Generator
from typing import Any

from openai import OpenAI

from core.base_llm import BaseLLMProvider
from core.errors import LLMProviderError
from core.registry import register_llm


@register_llm("openai")
class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI LLM Provider implementation.
    Acts as the reference implementation for OpenAI-compatible APIs.
    """

    def __init__(self, config: Any):
        super().__init__(config)
        api_key = os.environ.get(config.api_key_env)
        if not api_key:
            raise LLMProviderError(
                f"API key environment variable '{config.api_key_env}' not set."
            )

        self.client = OpenAI(
            api_key=api_key,
            base_url=config.base_url,
            organization=os.environ.get(config.extra.get("organization_env", ""))
            if config.extra
            else None,
        )

    def chat(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Synchronous chat completion returning OpenAI-compatible dictionary.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,  # type: ignore
                tools=tools,  # type: ignore
                temperature=kwargs.get("temperature", 0.1),
                **self.config.extra.get("completion_params", {}),
            )
            # Convert to dict and ensure it's JSON serializable
            return response.model_dump()
        except Exception as e:
            raise LLMProviderError(f"OpenAI chat failed: {e!s}") from e

    def stream(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> Generator[dict[str, Any], None, None]:
        """Streaming chat completion."""
        try:
            stream = self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,  # type: ignore
                tools=tools,  # type: ignore
                stream=True,
                **kwargs,
            )
            for chunk in stream:
                yield chunk.model_dump()
        except Exception as e:
            raise LLMProviderError(f"OpenAI stream failed: {e!s}") from e

    @property
    def supports_tool_calling(self) -> bool:
        return True
