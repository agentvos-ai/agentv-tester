from abc import ABC, abstractmethod
from collections.abc import Generator
from typing import Any


class BaseLLMProvider(ABC):
    """Abstract interface for LLM providers."""

    def __init__(self, config: Any):
        self.config = config

    @abstractmethod
    def chat(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Synchronous chat completion."""

    @abstractmethod
    def stream(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs,
    ) -> Generator[dict[str, Any], None, None]:
        """Streaming chat completion."""

    @property
    @abstractmethod
    def supports_tool_calling(self) -> bool:
        """Returns True if the provider supports native tool calling."""


class FallbackLLMProvider(BaseLLMProvider):
    """
    Resilient wrapper that cascades through multiple providers on failure.
    Useful for handling rate limits or outages with local fallbacks.
    """

    def __init__(self, primary: BaseLLMProvider, fallbacks: list[BaseLLMProvider]):
        self.primary = primary
        self.fallbacks = fallbacks
        self.current_provider = primary
        super().__init__(primary.config)

    def chat(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        providers = [self.primary] + self.fallbacks
        last_error = None

        for provider in providers:
            try:
                self.current_provider = provider
                return provider.chat(messages, tools=tools, **kwargs)
            except Exception as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(
                    f"LLM Provider {provider.__class__.__name__} failed: {e!s}. "
                    "Trying next fallback..."
                )
                last_error = e
                continue

        raise last_error or Exception("All LLM providers failed.")

    def stream(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs,
    ) -> Generator[dict[str, Any], None, None]:
        providers = [self.primary] + self.fallbacks
        last_error = None

        for provider in providers:
            try:
                self.current_provider = provider
                # We need to exhaust the generator to see if it fails
                yield from provider.stream(messages, tools=tools, **kwargs)
                return
            except Exception as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(
                    f"LLM Provider {provider.__class__.__name__} failed in stream: {e!s}. "
                    "Trying next fallback..."
                )
                last_error = e
                continue

        raise last_error or Exception("All LLM providers failed in stream.")

    @property
    def supports_tool_calling(self) -> bool:
        return self.current_provider.supports_tool_calling
