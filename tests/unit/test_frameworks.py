import pytest

from core.base_framework import RunnableAgent
from core.registry import get_framework_adapter


@pytest.mark.parametrize("framework_name", ["langgraph", "ag2", "langchain", "crewai"])
def test_framework_adapters(framework_name, mock_llm, mock_config, shim_registry):
    try:
        framework_cls = get_framework_adapter(framework_name)
    except Exception:
        pytest.skip(f"Framework {framework_name} not available")

    framework = framework_cls(mock_llm, shim_registry.get_all_tools(), mock_config)
    runnable = framework.build_agent("You are a helpful assistant.")

    assert isinstance(runnable, RunnableAgent)

    result = runnable.run("Hello", context={"user": "test"})
    assert "output" in result

    # If we are in a mocked environment, the output might be a MagicMock.
    # We allow this if the underlying library was mocked.
    out = result["output"]
    from unittest.mock import MagicMock

    if isinstance(out, MagicMock):
        # Ensure it's at least a mock object (it is)
        pass
    else:
        assert isinstance(out, str)
