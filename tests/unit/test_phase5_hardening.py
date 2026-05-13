import pytest
from types import SimpleNamespace
from core.errors import AgentExecutionError


@pytest.fixture
def mock_config():
    return SimpleNamespace(
        active_llm="mock",
        active_framework="langchain",
        active_vertical="fintech",
        llms={"mock": SimpleNamespace(model="test")},
        verticals={
            "fintech": SimpleNamespace(
                shims=["database", "analytics", "compliance", "notification"],
                agents=["fraud_detection_agent"],
            )
        },
    )


def test_base_agent_schema_enforcement(mock_config):
    from verticals.fintech.agents.fraud_detection_agent import FraudDetectionAgent
    from frameworks.langchain_adapter import LangChainAdapter
    from llm_providers.mock_provider import MockLLMProvider

    llm = MockLLMProvider(mock_config.llms["mock"])
    framework = LangChainAdapter(llm, [], mock_config)
    agent = FraudDetectionAgent(mock_config, framework, {})

    # Valid input
    valid_task = {
        "task_id": "T-1",
        "input_data": {
            "transaction_id": "TX-99",
            "account_id": "ACC-1",
            "amount": 150.0,
        },
    }
    # Should not raise
    agent.execute(valid_task)

    # Invalid input (missing fields)
    invalid_task = {"task_id": "T-2", "input_data": {"amount": 100}}
    with pytest.raises(AgentExecutionError) as exc:
        agent.execute(invalid_task)
    assert "Input Validation Failed" in str(exc.value)


def test_mock_llm_stateful_simulation():
    from llm_providers.mock_provider import MockLLMProvider

    provider = MockLLMProvider(SimpleNamespace(model="test"))

    # Initial message
    messages = [{"role": "user", "content": "Check for fraud in transaction TX-123"}]
    res = provider.chat(messages)

    # Should trigger a database tool call first
    assert len(res["choices"][0]["message"]["tool_calls"]) == 1
    assert (
        res["choices"][0]["message"]["tool_calls"][0]["function"]["name"] == "db_query"
    )

    # Add the tool call and response to messages to simulate next turn
    messages.append(res["choices"][0]["message"])
    messages.append(
        {
            "role": "tool",
            "content": "Success: Found transaction TX-123",
            "tool_call_id": "call_db_1",
        }
    )

    res2 = provider.chat(messages)
    # Should now trigger compliance check
    assert (
        res2["choices"][0]["message"]["tool_calls"][0]["function"]["name"]
        == "comp_check"
    )


def test_hitl_sla_escalation():
    from shims.s20_hitl import HitlShim

    shim = HitlShim()
    shim.reset()

    rid = shim.request_human_review("Check this", {})
    status = shim.get_review_status(rid)
    assert status["sla_tier"] == "LEVEL_1"

    # Check 3 more times (total 4)
    for _ in range(3):
        shim.get_review_status(rid)

    status2 = shim.get_review_status(rid)
    assert status2["sla_tier"] == "LEVEL_2"
    assert status2["priority"] == "HIGH"


def test_iot_trend_simulation():
    from shims.s09_iot import IotShim

    shim = IotShim()
    shim.setup()
    shim.reset()

    # Read sensor-02 (RISING trend)
    r1 = shim.read_sensor("sensor-02")["reading"]
    shim.read_sensor("sensor-02")
    r3 = shim.read_sensor("sensor-02")["reading"]

    # Should be increasing (roughly, noise might fluctuate but base is rising)
    assert r3 > r1
