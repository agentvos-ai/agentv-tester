import pytest
import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
root_dir = Path(__file__).parent.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

from core.config_loader import ConfigLoader, SuiteConfig, LLMConfig, VerticalConfig
from core.registry import get_llm_provider, get_framework_adapter, get_agent_class

# Ensure all plugins are registered
import llm_providers
import frameworks
import shims
import verticals.fintech.agents
import verticals.healthcare.agents
import verticals.telecom.agents

from shims.registry import ShimRegistry

@pytest.fixture
def mock_config():
    """Provides a basic suite configuration with mock LLM."""
    llm_cfg = LLMConfig(
        provider="mock",
        model="mock-gpt",
        api_key_env="MOCK_API_KEY"
    )
    
    vert_cfg = VerticalConfig(
        name="fintech",
        shims=["database", "analytics"],
        agents=["fraud_detection_agent"],
        scenarios=["basic_fraud"]
    )
    
    return SuiteConfig(
        active_vertical="fintech",
        active_framework="langgraph",
        active_llm="mock",
        llms={"mock": llm_cfg},
        verticals={"fintech": vert_cfg},
        seed=42
    )

@pytest.fixture
def mock_llm(mock_config):
    llm_cls = get_llm_provider("mock")
    return llm_cls(mock_config.llms["mock"])

@pytest.fixture
def shim_registry():
    registry = ShimRegistry(enabled_shims=["database", "analytics", "compliance", "notification"])
    registry.reset_all()
    yield registry
    registry.shutdown_all()
