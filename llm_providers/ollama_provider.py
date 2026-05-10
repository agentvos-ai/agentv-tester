from typing import Any
from .openai_provider import OpenAIProvider
from core.registry import register_llm

@register_llm("ollama")
class OllamaProvider(OpenAIProvider):
    """
    Ollama Local Provider using OpenAI-compatible interface.
    """
    def __init__(self, config: Any):
        # Ensure default local URL for Ollama
        if not config.base_url:
            config.base_url = "http://localhost:11434/v1"
        super().__init__(config)
