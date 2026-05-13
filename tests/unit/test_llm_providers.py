import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))
import unittest
from llm_providers.mock_provider import MockLLMProvider
from core.config_loader import LLMConfig


class TestLLMProviders(unittest.TestCase):
    """
    Unit tests for LLM provider abstractions.
    Ensures normalization logic and error handling work as expected.
    """

    def setUp(self):
        self.config = LLMConfig(
            provider="mock", model="test-model", api_key_env="TEST_API_KEY"
        )

    def test_mock_provider_chat(self):
        provider = MockLLMProvider(self.config)
        messages = [{"role": "user", "content": "test message"}]
        response = provider.chat(messages)

        self.assertIn("choices", response)
        self.assertEqual(response["choices"][0]["message"]["role"], "assistant")

    def test_mock_provider_logic(self):
        provider = MockLLMProvider(self.config)
        # Turn 1: Detect fraud keywords and trigger DB query
        messages = [{"role": "user", "content": "There is some fraud here"}]
        response = provider.chat(messages)
        self.assertIn("db_query", response["choices"][0]["message"]["content"])


if __name__ == "__main__":
    unittest.main()
