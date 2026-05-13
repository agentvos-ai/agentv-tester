import operator
from typing import Annotated, Sequence, TypedDict, List, Any, Dict
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    AIMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import StructuredTool
from core.base_framework import BaseFrameworkAdapter, RunnableAgent
from core.registry import register_framework
from core.errors import AgentExecutionError
from core.tool_utils import ToolNormalizer


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]


@register_framework("langgraph")
class LangGraphAdapter(BaseFrameworkAdapter):
    """
    Adapter for LangGraph ReAct agents.
    Converts between LangChain message types and suite internal formats.
    """

    def build_agent(self, system_prompt: str) -> RunnableAgent:
        # 1. Prepare Tools
        tools = self._get_lc_tools()
        tool_node = ToolNode(tools)

        # 2. Define the Graph
        workflow = StateGraph(AgentState)

        def call_model(state: AgentState) -> Dict[str, Any]:
            # Convert LC messages back to suite format for our LLM provider
            suite_messages = [self._lc_to_suite_msg(m) for m in state["messages"]]
            if system_prompt:
                suite_messages.insert(0, {"role": "system", "content": system_prompt})

            # Select tool format based on provider
            provider_name = self.config.active_llm
            if provider_name == "gemini":
                suite_tools = ToolNormalizer.to_gemini(self.shim_tools)
            elif provider_name == "claude":
                suite_tools = ToolNormalizer.to_claude(self.shim_tools)
            else:
                suite_tools = ToolNormalizer.to_openai(self.shim_tools)

            response = self.llm.chat(suite_messages, tools=suite_tools)

            # Convert response back to LC AIMessage
            msg = response["choices"][0]["message"]
            raw_tool_calls = msg.get("tool_calls", [])
            lc_tool_calls = []
            for tc in raw_tool_calls:
                if tc.get("type") == "function":
                    f = tc["function"]
                    lc_tool_calls.append(
                        {"name": f["name"], "args": f["arguments"], "id": tc["id"]}
                    )

            return {
                "messages": [
                    AIMessage(content=msg["content"], tool_calls=lc_tool_calls)
                ]
            }

        def should_continue(state: AgentState) -> str:
            last_message = state["messages"][-1]
            if isinstance(last_message, AIMessage) and last_message.tool_calls:
                return "tools"
            return END

        workflow.add_node("agent", call_model)
        workflow.add_node("tools", tool_node)
        workflow.set_entry_point("agent")
        workflow.add_conditional_edges("agent", should_continue)
        workflow.add_edge("tools", "agent")

        graph = workflow.compile()
        return LangGraphRunnable(graph)

    def _get_lc_tools(self) -> List[StructuredTool]:
        lc_tools = []
        for name, fn, desc in self.shim_tools:
            lc_tools.append(
                StructuredTool.from_function(func=fn, name=name, description=desc)
            )
        return lc_tools

    def _lc_to_suite_msg(self, msg: BaseMessage) -> Dict[str, Any]:
        if isinstance(msg, HumanMessage):
            return {"role": "user", "content": str(msg.content)}
        if isinstance(msg, AIMessage):
            # Preserve tool calls for stateful LLMs (like our Mock simulator)
            lc_tool_calls = getattr(msg, "tool_calls", [])
            suite_tool_calls = []
            for tc in lc_tool_calls:
                suite_tool_calls.append(
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {"name": tc["name"], "arguments": tc["args"]},
                    }
                )
            return {
                "role": "assistant",
                "content": str(msg.content),
                "tool_calls": suite_tool_calls,
            }
        if isinstance(msg, SystemMessage):
            return {"role": "system", "content": str(msg.content)}

        # Handle ToolMessage (result of a tool execution)
        if isinstance(msg, ToolMessage):
            return {
                "role": "tool",
                "tool_call_id": msg.tool_call_id,
                "content": str(msg.content),
            }

        return {"role": "user", "content": str(msg.content)}


class LangGraphRunnable(RunnableAgent):
    def __init__(self, graph: Any):
        self.graph = graph

    def run(self, task: str, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        try:
            full_task = task
            if context:
                ctx_str = "\n".join([f"{k}: {v}" for k, v in context.items()])
                full_task = f"CONTEXT:\n{ctx_str}\n\nTASK:\n{task}"

            initial_state = {"messages": [HumanMessage(content=full_task)]}
            final_state = self.graph.invoke(initial_state)
            last_msg = final_state["messages"][-1]
            return {
                "output": last_msg.content,
                "tool_calls": getattr(last_msg, "tool_calls", []),
            }
        except Exception as e:
            raise AgentExecutionError(f"LangGraph execution failed: {str(e)}") from e
