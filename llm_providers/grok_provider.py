from typing import Any
from .openai_provider import OpenAIProvider
from core.registry import register_llm


@register_llm("grok")
class GrokProvider(OpenAIProvider):
    """
    xAI Grok Provider using OpenAI-compatible interface.
    """

    def __init__(self, config: Any):
        # Ensure base_url is set for Grok if not in config
        if not config.base_url:
            config.base_url = "https://api.x.ai/v1"
        super().__init__(config)
