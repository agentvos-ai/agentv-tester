from abc import ABC, abstractmethod
from typing import Any, Dict, List, Generator


class BaseLLMProvider(ABC):
    """Abstract interface for LLM providers."""

    def __init__(self, config: Any):
        self.config = config

    @abstractmethod
    def chat(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]] | None = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Synchronous chat completion."""
        pass

    @abstractmethod
    def stream(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]] | None = None,
        **kwargs,
    ) -> Generator[Dict[str, Any], None, None]:
        """Streaming chat completion."""
        pass

    @property
    @abstractmethod
    def supports_tool_calling(self) -> bool:
        """Returns True if the provider supports native tool calling."""
        pass


class FallbackLLMProvider(BaseLLMProvider):
    """
    Resilient wrapper that cascades through multiple providers on failure.
    Useful for handling rate limits or outages with local fallbacks.
    """

    def __init__(self, primary: BaseLLMProvider, fallbacks: List[BaseLLMProvider]):
        self.primary = primary
        self.fallbacks = fallbacks
        self.current_provider = primary
        super().__init__(primary.config)

    def chat(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]] | None = None,
        **kwargs,
    ) -> Dict[str, Any]:
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
                    f"LLM Provider {provider.__class__.__name__} failed: {str(e)}. "
                    "Trying next fallback..."
                )
                last_error = e
                continue

        raise last_error or Exception("All LLM providers failed.")

    def stream(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]] | None = None,
        **kwargs,
    ) -> Generator[Dict[str, Any], None, None]:
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
                    f"LLM Provider {provider.__class__.__name__} failed in stream: {str(e)}. "
                    "Trying next fallback..."
                )
                last_error = e
                continue

        raise last_error or Exception("All LLM providers failed in stream.")

    @property
    def supports_tool_calling(self) -> bool:
        return self.current_provider.supports_tool_calling
