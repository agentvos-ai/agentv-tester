import os
from collections.abc import Generator
from typing import Any

from google import genai
from google.genai import types

from core.base_llm import BaseLLMProvider
from core.errors import LLMProviderError
from core.registry import register_llm


@register_llm("gemini")
class GeminiProvider(BaseLLMProvider):
    """
    Google Gemini Provider using google-genai 2.0.1.
    Normalizes response to OpenAI-compatible structure.
    """

    def __init__(self, config: Any):
        super().__init__(config)
        api_key = os.environ.get(config.api_key_env)
        if not api_key:
            raise LLMProviderError(
                f"API key environment variable '{config.api_key_env}' not set."
            )

        self.client = genai.Client(
            api_key=api_key, http_options={"api_version": "v1beta"}
        )

    def chat(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Synchronous chat with Gemini."""
        import sys
        import time

        max_retries = 5
        retry_delay = 15
        for attempt in range(max_retries):
            try:
                contents, system_instruction = self._prepare_contents(messages)

                response = self.client.models.generate_content(
                    model=self.config.model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        tools=tools,
                        temperature=kwargs.get("temperature", 0.1),
                    ),
                )

                # Add a small delay after a successful call to avoid hitting the rate limit
                time.sleep(2.0)

                return self._normalize_response(response)
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    if attempt < max_retries - 1:
                        sys.stderr.write(
                            f"\n[Gemini] 429 Rate Limit hit. Retrying in {retry_delay}s... (Attempt {attempt + 1}/{max_retries})\n"
                        )
                        sys.stderr.flush()
                        time.sleep(retry_delay)
                        retry_delay += 10
                        continue
                raise LLMProviderError(f"Gemini chat failed: {e!s}") from e

    def stream(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> Generator[dict[str, Any], None, None]:
        """Full industrial streaming implementation for Gemini."""
        try:
            contents, system_instruction = self._prepare_contents(messages)

            response = self.client.models.generate_content_stream(
                model=self.config.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    tools=tools,
                    temperature=kwargs.get("temperature", 0.1),
                ),
            )

            for chunk in response:
                yield self._normalize_response(chunk)
        except Exception as e:
            raise LLMProviderError(f"Gemini stream failed: {e!s}") from e

    def _prepare_contents(
        self, messages: list[dict[str, str]]
    ) -> tuple[list[Any], str | None]:
        contents = []
        system_instruction = None
        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            else:
                contents.append(
                    types.Content(
                        role="user" if msg["role"] == "user" else "model",
                        parts=[types.Part.from_text(text=msg["content"])],
                    )
                )
        return contents, system_instruction

    @property
    def supports_tool_calling(self) -> bool:
        return True

    def _normalize_response(self, response: Any) -> dict[str, Any]:
        """Normalizes Gemini response to OpenAI-compatible format."""
        text = response.text if hasattr(response, "text") and response.text else ""
        tool_calls = []
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.function_call:
                    # Convert types.Parameters (dict-like) to a plain dict
                    args = {}
                    if part.function_call.args:
                        args = {k: v for k, v in part.function_call.args.items()}

                    tool_calls.append(
                        {
                            "id": f"call_{part.function_call.name}",
                            "type": "function",
                            "function": {
                                "name": part.function_call.name,
                                "arguments": args,
                            },
                        }
                    )

        return {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": text,
                        "tool_calls": tool_calls,
                    }
                }
            ]
        }
