import pytest
import sys
from unittest.mock import MagicMock, patch

# Use a fixture to mock modules, ensuring they are restored after the test
@pytest.fixture(autouse=True)
def mock_framework_modules():
    mock_modules = [
        "autogen", "crewai", "crewai.agent", "crewai.task", "crewai.crew",
        "langchain_classic", "langchain_classic.agents", "langchain_core",
        "langchain_core.prompts", "langchain_core.tools", "langchain_core.messages",
        "langchain_core.language_models", "langchain_core.language_models.chat_models",
        "langchain_core.outputs", "langgraph", "langgraph.graph", "langgraph.prebuilt"
    ]
    with patch.dict(sys.modules, {name: MagicMock() for name in mock_modules}):
        # We need to make sure AIMessage etc. are available in the mock
        import langchain_core.messages
        sys.modules["langchain_core.messages"].AIMessage = MagicMock()
        sys.modules["langchain_core.messages"].HumanMessage = MagicMock()
        sys.modules["langchain_core.messages"].SystemMessage = MagicMock()
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
        "choices": [{"message": {"role": "assistant", "content": "Response", "tool_calls": []}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20}
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
    
    with patch.object(autogen, "AssistantAgent"), patch.object(autogen, "UserProxyAgent"), \
         patch.object(autogen, "register_function"):
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

def test_langchain_adapter(mock_llm, shim_tools, framework_config):
    if "frameworks.langchain_adapter" in sys.modules:
        del sys.modules["frameworks.langchain_adapter"]
    from frameworks.langchain_adapter import LangChainAdapter
    import frameworks.langchain_adapter as la
    with patch.object(la, "AgentExecutor"), patch.object(la, "create_structured_chat_agent"):
        adapter = LangChainAdapter(mock_llm, shim_tools, framework_config)
        runnable = adapter.build_agent("System prompt")
        assert runnable is not None

def test_langgraph_adapter(mock_llm, shim_tools, framework_config):
    if "frameworks.langgraph_adapter" in sys.modules:
        del sys.modules["frameworks.langgraph_adapter"]
    
    from frameworks.langgraph_adapter import LangGraphAdapter
    import frameworks.langgraph_adapter as lga
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
    
    with patch.object(lga, "StateGraph") as mock_graph_cls:
        mock_graph = mock_graph_cls.return_value
        mock_graph.compile.return_value = MagicMock()
        adapter = LangGraphAdapter(mock_llm, shim_tools, framework_config)
        runnable = adapter.build_agent("System prompt")
        assert runnable is not None
        
        # Test conversion logic
        m1 = HumanMessage(content="hi")
        m2 = AIMessage(content="hi")
        m3 = SystemMessage(content="hi")
        
        with patch("frameworks.langgraph_adapter.isinstance", side_effect=lambda x, t: True if (
            (x == m1 and t == HumanMessage) or
            (x == m2 and t == AIMessage) or
            (x == m3 and t == SystemMessage)
        ) else False):
            assert adapter._lc_to_suite_msg(m1)["role"] == "user"
            assert adapter._lc_to_suite_msg(m2)["role"] == "assistant"
            assert adapter._lc_to_suite_msg(m3)["role"] == "system"
            assert adapter._lc_to_suite_msg(MagicMock())["role"] == "user"
