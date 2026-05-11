import pytest
import os
import sys
from unittest.mock import MagicMock, patch
from core.errors import LLMProviderError

# Universal Mocking Helper
def setup_mocks():
    sys.modules["openai"] = MagicMock()
    sys.modules["anthropic"] = MagicMock()
    sys.modules["google"] = MagicMock()
    sys.modules["google.genai"] = MagicMock()
    sys.modules["google.genai.types"] = MagicMock()

setup_mocks()

from llm_providers.openai_provider import OpenAIProvider
from llm_providers.claude_provider import ClaudeProvider
from llm_providers.gemini_provider import GeminiProvider

@pytest.fixture
def llm_config():
    os.environ["OPENAI_API_KEY"] = "mock-key"
    os.environ["ANTHROPIC_API_KEY"] = "mock-key"
    os.environ["GOOGLE_API_KEY"] = "mock-key"
    cfg = MagicMock()
    cfg.model = "gpt-4"
    cfg.api_key_env = "OPENAI_API_KEY"
    cfg.base_url = "https://api.openai.com/v1"
    cfg.extra = {}
    return cfg

def test_openai_provider(llm_config):
    with patch("llm_providers.openai_provider.OpenAI") as mock_oa:
        client = mock_oa.return_value
        provider = OpenAIProvider(llm_config)
        
        # 1. Test supports_tool_calling
        assert provider.supports_tool_calling is True

        # 2. Test chat
        mock_res = MagicMock()
        mock_res.model_dump.return_value = {
            "choices": [{"message": {"role": "assistant", "content": "Hello", "tool_calls": []}}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10}
        }
        client.chat.completions.create.return_value = mock_res
        res = provider.chat([{"role": "user", "content": "hi"}])
        assert res["choices"][0]["message"]["content"] == "Hello"
        
        # 3. Test stream
        mock_chunk = MagicMock()
        mock_chunk.model_dump.return_value = {"choices": [{"delta": {"content": " Chunk"}}]}
        client.chat.completions.create.return_value = [mock_chunk]
        
        chunks = list(provider.stream([{"role": "user", "content": "hi"}]))
        assert len(chunks) == 1
        assert chunks[0]["choices"][0]["delta"]["content"] == " Chunk"

        # 4. Test error paths
        client.chat.completions.create.side_effect = Exception("OpenAI Fail")
        with pytest.raises(LLMProviderError, match="OpenAI chat failed"):
            provider.chat([])
        with pytest.raises(LLMProviderError, match="OpenAI stream failed"):
            list(provider.stream([]))

def test_anthropic_provider_full(llm_config):
    with patch("llm_providers.claude_provider.anthropic.Anthropic") as mock_ant_cls:
        mock_client = MagicMock()
        mock_ant_cls.return_value = mock_client
        provider = ClaudeProvider(llm_config)
        
        msgs = [
            {"role": "system", "content": "System message"},
            {"role": "user", "content": "hi"}
        ]
        
        # 1. Test chat
        mock_res = MagicMock()
        mock_text_part = MagicMock(spec=["text", "type"])
        mock_text_part.text = "Hello"
        mock_text_part.type = "text"
        mock_res.content = [mock_text_part]
        mock_res.usage = MagicMock(input_tokens=5, output_tokens=5)
        mock_client.messages.create.return_value = mock_res
        
        res = provider.chat(msgs)
        assert res["choices"][0]["message"]["content"] == "Hello"
        
        # 2. Test stream
        mock_stream = MagicMock()
        mock_event = MagicMock(type="text", text="Chunk")
        mock_stream.__enter__.return_value = [mock_event]
        mock_client.messages.stream.return_value = mock_stream
        
        chunks = list(provider.stream(msgs))
        assert len(chunks) == 1
        assert chunks[0]["choices"][0]["delta"]["content"] == "Chunk"

def test_gemini_provider_full(llm_config):
    with patch("llm_providers.gemini_provider.genai.Client") as mock_client_cls:
        client = mock_client_cls.return_value
        provider = GeminiProvider(llm_config)
        
        # Test supports_tool_calling
        assert provider.supports_tool_calling is True
        
        # Test _prepare_contents with system message
        msgs = [{"role": "system", "content": "Instruction"}, {"role": "user", "content": "hi"}]
        contents, system = provider._prepare_contents(msgs)
        assert system == "Instruction"
        assert len(contents) == 1
        
        # Test chat
        mock_res = MagicMock()
        mock_res.text = "Hello"
        mock_res.candidates = [] # No tool calls
        client.models.generate_content.return_value = mock_res
        res = provider.chat(msgs)
        assert res["choices"][0]["message"]["content"] == "Hello"
        
        # Test tool calls
        mock_part = MagicMock()
        mock_part.function_call.name = "get_weather"
        mock_part.function_call.args = {"city": "London"}
        mock_res.candidates = [MagicMock(content=MagicMock(parts=[mock_part]))]
        res = provider.chat(msgs)
        assert res["choices"][0]["message"]["tool_calls"][0]["function"]["name"] == "get_weather"

def test_provider_errors(llm_config):
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(LLMProviderError): OpenAIProvider(llm_config)
        with pytest.raises(LLMProviderError): ClaudeProvider(llm_config)
        with pytest.raises(LLMProviderError): GeminiProvider(llm_config)
    
    # Claude errors
    with patch("llm_providers.claude_provider.anthropic.Anthropic") as mock_ant_cls:
        client = mock_ant_cls.return_value
        client.messages.create.side_effect = Exception("Chat fail")
        provider = ClaudeProvider(llm_config)
        with pytest.raises(LLMProviderError, match="Claude chat failed"):
            provider.chat([])
        
        client.messages.stream.side_effect = Exception("Stream fail")
        with pytest.raises(LLMProviderError, match="Claude stream failed"):
            next(provider.stream([]))
            
    # Gemini errors
    with patch("llm_providers.gemini_provider.genai.Client") as mock_client_cls:
        client = mock_client_cls.return_value
        client.models.generate_content.side_effect = Exception("Chat fail")
        provider = GeminiProvider(llm_config)
        with pytest.raises(LLMProviderError, match="Gemini chat failed"):
            provider.chat([])
            
        client.models.generate_content_stream.side_effect = Exception("Stream fail")
        with pytest.raises(LLMProviderError, match="Gemini stream failed"):
            next(provider.stream([]))
