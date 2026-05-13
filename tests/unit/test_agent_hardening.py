from unittest.mock import MagicMock
from core.base_agent import BaseAgent
from core.errors import ShimError


class MockShim:
    def get_tool_specs(self):
        return [("test_tool", self.test_func, "A test tool")]

    def test_func(self, x):
        if x == "error":
            raise ShimError("Something went wrong")
        if x == "crash":
            raise Exception("Critical failure")
        return f"result: {x}"


class MockAgent(BaseAgent):
    @property
    def system_prompt(self):
        return "You are a mock agent."

    @property
    def allowed_shims(self):
        return ["mock_shim"]


def test_agent_gatekeeper():
    shims = {"mock_shim": MockShim(), "secret_shim": MockShim()}
    framework = MagicMock()
    agent = MockAgent(config={}, framework=framework, shims=shims)

    tools = agent.get_tool_specs()

    # Gatekeeper: Should only have tools from mock_shim
    assert len(tools) == 1
    assert tools[0][0] == "test_tool"


def test_agent_feedback_loop():
    shim = MockShim()
    shims = {"mock_shim": shim}
    framework = MagicMock()
    agent = MockAgent(config={}, framework=framework, shims=shims)

    tools = agent.get_tool_specs()
    tool_func = tools[0][1]

    # 1. Success case
    assert tool_func(x="data") == "result: data"

    # 2. Feedback loop (ShimError)
    res = tool_func(x="error")
    assert "TOOL_ERROR (test_tool): Something went wrong" in res

    # 3. System Error (Exception)
    res = tool_func(x="crash")
    assert "SYSTEM_ERROR (test_tool)" in res
