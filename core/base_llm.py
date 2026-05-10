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
        **kwargs
    ) -> Dict[str, Any]:
        """Synchronous chat completion."""
        pass

    @abstractmethod
    def stream(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]] | None = None,
        **kwargs
    ) -> Generator[Dict[str, Any], None, None]:
        """Streaming chat completion."""
        pass

    @property
    @abstractmethod
    def supports_tool_calling(self) -> bool:
        """Returns True if the provider supports native tool calling."""
        pass
