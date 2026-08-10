import os
from unittest.mock import patch

import pytest
import yaml

from core.config_loader import ConfigLoader


def test_config_loader_full_path(tmp_path):
    # Setup temporary config directory
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "verticals").mkdir()
    (config_dir / "llms").mkdir()

    # Create mock files
    suite_yaml = {
        "active": {"vertical": "fintech", "framework": "langgraph", "llm": "mock"},
        "shims": {"seed": 123},
    }
    with open(config_dir / "suite.yaml", "w") as f:
        yaml.dump(suite_yaml, f)

    vert_yaml = {"shims": ["database"], "agents": ["agent1"]}
    with open(config_dir / "verticals" / "fintech.yaml", "w") as f:
        yaml.dump(vert_yaml, f)

    # Need a health.yaml for the override test
    with open(config_dir / "verticals" / "health.yaml", "w") as f:
        yaml.dump(vert_yaml, f)

    llm_yaml = {"model": "gpt-mock", "fallbacks": ["fallback1"]}
    with open(config_dir / "llms" / "mock.yaml", "w") as f:
        yaml.dump(llm_yaml, f)

    fallback_yaml = {"model": "gpt-fallback"}
    with open(config_dir / "llms" / "fallback1.yaml", "w") as f:
        yaml.dump(fallback_yaml, f)

    # Monkeypatch CONFIG_DIR
    old_dir = ConfigLoader.CONFIG_DIR
    ConfigLoader.CONFIG_DIR = config_dir

    try:
        # 1. Test standard load with clean environment
        with patch.dict(os.environ, {}, clear=True):
            # Mock registry check to be independent of available adapters
            with patch("core.registry.get_framework_adapter"):
                config = ConfigLoader.load("suite.yaml")
                assert config.active_vertical == "fintech"
                assert config.active_framework == "langgraph"
                assert config.active_llm == "mock"
                assert "fallback1" in config.llms
                assert config.seed == 123

        # 2. Test ENV overrides
        with patch.dict(
            os.environ,
            {
                "ACTIVE_VERTICAL": "health",
                "ACTIVE_FRAMEWORK": "langchain",
                "ACTIVE_LLM": "mock",
                "SUITE_SEED": "999",
            },
        ):
            # Mock registry check to allow 'langchain' even if not registered in this env
            with patch("core.registry.get_framework_adapter"):
                config = ConfigLoader.load("suite.yaml")
                assert config.active_vertical == "health"
                assert config.active_framework == "langchain"
                assert config.seed == 999

    finally:
        ConfigLoader.CONFIG_DIR = old_dir


def test_config_loader_missing_file():
    with pytest.raises(FileNotFoundError):
        ConfigLoader.load("non_existent.yaml")
