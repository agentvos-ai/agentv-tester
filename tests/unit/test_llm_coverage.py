import pytest
from core.base_llm import BaseLLMProvider, FallbackLLMProvider
from llm_providers.heuristic_provider import HeuristicProvider
from llm_providers.mock_provider import MockLLMProvider


def test_heuristic_provider():
    config = {"model": "test"}
    provider = HeuristicProvider(config)

    # Test fraud heuristic
    messages = [{"role": "user", "content": "Analyze transaction for fraud"}]
    res = provider.chat(messages)
    assert "potential risk patterns" in res["choices"][0]["message"]["content"]

    # Test medical heuristic
    messages = [{"role": "user", "content": "Patient diagnosis"}]
    res = provider.chat(messages)
    assert "medical heuristic" in res["choices"][0]["message"]["content"].lower()

    # Test default
    messages = [{"role": "user", "content": "Hello"}]
    res = provider.chat(messages)
    assert "fallback" in res["choices"][0]["message"]["content"].lower()


def test_fallback_provider(mock_config):
    p1 = MockLLMProvider(mock_config.llms["mock"])
    p2 = HeuristicProvider({"model": "test"})

    fallback = FallbackLLMProvider(primary=p1, fallbacks=[p2])

    # Test primary success
    res = fallback.chat([{"role": "user", "content": "hello"}])
    assert "Mock" in res["choices"][0]["message"]["content"]

    # Test primary failure (manual mock)
    def fail_chat(*args, **kwargs):
        raise Exception("Primary failed")

    p1.chat = fail_chat

    res = fallback.chat([{"role": "user", "content": "hello"}])
    assert "fallback" in res["choices"][0]["message"]["content"].lower()


def test_fallback_provider_stream(mock_config):
    p1 = MockLLMProvider(mock_config.llms["mock"])
    p2 = HeuristicProvider({"model": "test"})
    fallback = FallbackLLMProvider(primary=p1, fallbacks=[p2])

    # Test success
    chunks = list(fallback.stream([{"role": "user", "content": "hello"}]))
    assert "Mock" in chunks[0]["choices"][0]["message"]["content"]

    # Test fallback on stream error
    def fail_stream(*args, **kwargs):
        raise Exception("Stream failed")
        yield {}  # make it a generator

    p1.stream = fail_stream

    chunks = list(fallback.stream([{"role": "user", "content": "hello"}]))
    assert "fallback" in chunks[0]["choices"][0]["message"]["content"].lower()


def test_fallback_provider_failures():
    class FailingProvider(BaseLLMProvider):
        def chat(self, *args, **kwargs):
            raise Exception("Fail")

        def stream(self, *args, **kwargs):
            raise Exception("Fail")

        @property
        def supports_tool_calling(self):
            return False

    p1 = FailingProvider({"model": "m"})
    fallback = FallbackLLMProvider(primary=p1, fallbacks=[])

    with pytest.raises(Exception, match="Fail"):
        fallback.chat([])

    with pytest.raises(Exception, match="Fail"):
        list(fallback.stream([]))

    assert fallback.supports_tool_calling is False


def test_mock_provider_stream(mock_config):
    p = MockLLMProvider(mock_config.llms["mock"])
    chunks = list(p.stream([{"role": "user", "content": "hello"}]))
    assert len(chunks) > 0
    assert "Mock" in chunks[0]["choices"][0]["message"]["content"]
