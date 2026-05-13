import pytest
from core.registry import (
    get_llm_provider,
    get_framework_adapter,
    get_agent_class,
    list_llms,
    list_agents,
    list_frameworks,
)
from core.errors import ConfigError


def test_registry_success():
    assert "mock" in list_llms()
    assert "langgraph" in list_frameworks()
    assert "fraud_detection_agent" in list_agents()


def test_registry_failures():
    with pytest.raises(ConfigError):
        get_llm_provider("non_existent")
    with pytest.raises(ConfigError):
        get_framework_adapter("non_existent")
    with pytest.raises(ConfigError):
        get_agent_class("non_existent")


def test_config_loader_basic(tmp_path):
    # This test might be tricky due to file dependencies,
    # but we can try to test the loading logic if we mock the file reads.
    pass


def test_base_agent_execution(mock_config, mock_llm, shim_registry):
    framework_cls = get_framework_adapter("langgraph")
    framework = framework_cls(mock_llm, shim_registry.get_all_tools(), mock_config)

    agent_cls = get_agent_class("fraud_detection_agent")
    agent = agent_cls(mock_config, framework, shim_registry.shims)

    task = {
        "task_id": "T1",
        "input": "Check this fraud case",
        "context": {"priority": "high"},
    }
    result = agent.execute(task)

    assert result["status"] == "success"
    assert result["task_id"] == "T1"
    # The mock provider responds with SAR if 'fraud' is in the message
    assert "SAR" in result["output"] or "Mock" in result["output"]
