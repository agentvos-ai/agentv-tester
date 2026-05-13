import pytest
import sys
from unittest.mock import MagicMock, patch


# Use a fixture to mock modules, ensuring they are restored after the test
@pytest.fixture(autouse=True)
def mock_framework_modules():
    # Define real classes so isinstance() works
    class MockHumanMessage:
        def __init__(self, content):
            self.content = content

    class MockAIMessage:
        def __init__(self, content, tool_calls=None):
            self.content = content
            self.tool_calls = tool_calls or []

    class MockSystemMessage:
        def __init__(self, content):
            self.content = content

    class MockToolMessage:
        def __init__(self, content, tool_call_id):
            self.content = content
            self.tool_call_id = tool_call_id

    class MockBaseChatModel:
        def __init__(self, **kwargs):
            pass

        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            pass

    class MockChatGeneration:
        def __init__(self, message):
            self.message = message

    class MockChatResult:
        def __init__(self, generations):
            self.generations = generations

    mock_modules = [
        "autogen",
        "crewai",
        "crewai.agent",
        "crewai.task",
        "crewai.crew",
        "langchain_classic",
        "langchain_classic.agents",
        "langchain_core",
        "langchain_core.prompts",
        "langchain_core.tools",
        "langchain_core.messages",
        "langchain_core.language_models",
        "langchain_core.language_models.chat_models",
        "langchain_core.outputs",
        "langgraph",
        "langgraph.graph",
        "langgraph.prebuilt",
    ]
    with patch.dict(sys.modules, {name: MagicMock() for name in mock_modules}):
        # Inject our real classes into the mock modules
        m = sys.modules["langchain_core.messages"]
        m.HumanMessage = MockHumanMessage
        m.AIMessage = MockAIMessage
        m.SystemMessage = MockSystemMessage
        m.ToolMessage = MockToolMessage

        cm = sys.modules["langchain_core.language_models.chat_models"]
        cm.BaseChatModel = MockBaseChatModel

        om = sys.modules["langchain_core.outputs"]
        om.ChatResult = MockChatResult
        om.ChatGeneration = MockChatGeneration

        yield


@pytest.fixture
def framework_config():
    cfg = MagicMock()
    cfg.active_llm = "mock"
    cfg.llms = {"mock": MagicMock(model="gpt-4")}
    cfg.extra = {}
    return cfg


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.chat.return_value = {
        "choices": [
            {"message": {"role": "assistant", "content": "Response", "tool_calls": []}}
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
    }
    return llm


@pytest.fixture
def shim_tools():
    return [("tool1", lambda x: x, "desc1")]


def test_ag2_adapter_full(mock_llm, shim_tools, framework_config):
    # Reload adapter to pick up the mocks from sys.modules
    if "frameworks.ag2_adapter" in sys.modules:
        del sys.modules["frameworks.ag2_adapter"]
    from frameworks.ag2_adapter import AG2Adapter, SuiteModelClient, AG2Runnable
    import autogen

    with (
        patch.object(autogen, "AssistantAgent"),
        patch.object(autogen, "UserProxyAgent"),
        patch.object(autogen, "register_function"),
    ):
        adapter = AG2Adapter(mock_llm, shim_tools, framework_config)
        runnable = adapter.build_agent("System prompt")
        assert isinstance(runnable, AG2Runnable)

        # Test SuiteModelClient
        client = SuiteModelClient(MagicMock(model="m1"), mock_llm)
        params = {"messages": [{"role": "user", "content": "hi"}], "tools": []}
        res = client.create(params)
        assert res.choices[0].message.content == "Response"
        assert client.message_retrieval(res) is not None
        assert client.cost(res) == 0.0
        assert client.get_common_config_list([{}]) == [{}]

        # Test AG2Runnable
        mock_assistant = MagicMock()
        mock_assistant.last_message.return_value = {"content": "Final result"}
        mock_user = MagicMock()
        runnable = AG2Runnable(mock_assistant, mock_user)

        # Standard run
        out = runnable.run("task")
        assert out["output"] == "Final result"

        # Run with context
        out = runnable.run("task", context={"key": "val"})
        assert out["output"] == "Final result"

        # Error path
        mock_user.initiate_chat.side_effect = Exception("Fail")
        with pytest.raises(Exception):
            runnable.run("task")


def test_crewai_adapter(mock_llm, shim_tools, framework_config):
    if "frameworks.crewai_adapter" in sys.modules:
        del sys.modules["frameworks.crewai_adapter"]
    from frameworks.crewai_adapter import CrewAIAdapter
    import frameworks.crewai_adapter as ca

    with patch.object(ca, "Agent"), patch.object(ca, "Task"), patch.object(ca, "Crew"):
        adapter = CrewAIAdapter(mock_llm, shim_tools, framework_config)
        runnable = adapter.build_agent("System prompt")
        assert runnable is not None


def test_langchain_adapter_full(mock_llm, shim_tools, framework_config):
    if "frameworks.langchain_adapter" in sys.modules:
        del sys.modules["frameworks.langchain_adapter"]
    from frameworks.langchain_adapter import LangChainAdapter, LangChainRunnable
    from langchain_core.messages import (
        HumanMessage,
        AIMessage,
        SystemMessage,
        ToolMessage,
    )

    import frameworks.langchain_adapter as la

    with (
        patch.object(la, "AgentExecutor") as mock_exec_cls,
        patch.object(la, "create_structured_chat_agent"),
    ):
        adapter = LangChainAdapter(mock_llm, shim_tools, framework_config)
        runnable = adapter.build_agent("System prompt")
        assert isinstance(runnable, LangChainRunnable)

        # Test SuiteChatModel logic
        lc_llm = adapter._get_lc_llm()

        # 1. Message conversion
        msgs = [
            HumanMessage(content="user"),
            AIMessage(content="ai"),
            SystemMessage(content="sys"),
            ToolMessage(content="tool_res", tool_call_id="tc_1"),
        ]

        # Mock LLM response with tool call
        mock_llm.chat.return_value = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "thought",
                        "tool_calls": [
                            {
                                "type": "function",
                                "id": "tc_1",
                                "function": {"name": "tool1", "arguments": "{}"},
                            }
                        ],
                    }
                }
            ]
        }

        # Exercise _generate with various messages
        # We need to ensure SuiteChatModel._generate is actually called and not mocked by langchain_core
        res = lc_llm._generate(msgs)
        assert res.generations[0].message.content == "thought"
        assert len(res.generations[0].message.tool_calls) == 1

        # Test tool calls with string arguments
        mock_llm.chat.return_value = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "c",
                        "tool_calls": [
                            {"function": {"name": "t", "arguments": '{"a": 1}'}}
                        ],
                    }
                }
            ]
        }
        lc_llm._generate([HumanMessage(content="h")])

        # 2. Runnable execution paths
        mock_executor = mock_exec_cls.return_value
        # Success with intermediate steps
        mock_executor.invoke.return_value = {
            "output": "Final answer",
            "intermediate_steps": [(MagicMock(tool="tool1", tool_input="{}"), "res")],
        }
        out = runnable.run("task", context={"c": "v"})
        assert out["output"] == "Final answer"
        assert len(out["tool_calls"]) == 1

        # Error path
        mock_executor.invoke.side_effect = Exception("LC Fail")
        with pytest.raises(Exception, match="LangChain execution failed"):
            runnable.run("task")


def test_langgraph_adapter_full(mock_llm, shim_tools, framework_config):
    if "frameworks.langgraph_adapter" in sys.modules:
        del sys.modules["frameworks.langgraph_adapter"]

    from frameworks.langgraph_adapter import LangGraphAdapter, LangGraphRunnable
    import frameworks.langgraph_adapter as lga
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

    with patch.object(lga, "StateGraph") as mock_graph_cls:
        mock_graph = mock_graph_cls.return_value
        mock_graph.compile.return_value = MagicMock()
        adapter = LangGraphAdapter(mock_llm, shim_tools, framework_config)
        runnable = adapter.build_agent("System prompt")
        assert isinstance(runnable, LangGraphRunnable)

        # Test conversion logic
        # We patch the classes in the adapter's namespace to our mock classes
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

        with (
            patch("frameworks.langgraph_adapter.HumanMessage", HumanMessage),
            patch("frameworks.langgraph_adapter.AIMessage", AIMessage),
            patch("frameworks.langgraph_adapter.SystemMessage", SystemMessage),
        ):
            assert adapter._lc_to_suite_msg(HumanMessage(content="h"))["role"] == "user"
            assert (
                adapter._lc_to_suite_msg(AIMessage(content="a"))["role"] == "assistant"
            )
            assert (
                adapter._lc_to_suite_msg(SystemMessage(content="s"))["role"] == "system"
            )
            assert adapter._lc_to_suite_msg(MagicMock())["role"] == "user"

        # Test Runnable run
        mock_compiled = mock_graph.compile.return_value
        mock_compiled.invoke.return_value = {
            "messages": [AIMessage(content="Graph result")]
        }
        out = runnable.run("task")
        assert out["output"] == "Graph result"

        # Error path
        mock_compiled.invoke.side_effect = Exception("Graph Fail")
        with pytest.raises(Exception, match="LangGraph execution failed"):
            runnable.run("task")

        # Test different provider tool normalization in build_agent
        # (This exercises the ToolNormalizer integration)
        framework_config.active_llm = "gemini"
        adapter.build_agent("p")
        framework_config.active_llm = "claude"
        adapter.build_agent("p")
        framework_config.active_llm = "openai"
        adapter.build_agent("p")
