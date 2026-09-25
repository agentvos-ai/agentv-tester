import operator
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Annotated, Any, TypedDict

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import StructuredTool
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from core.base_framework import BaseFrameworkAdapter, RunnableAgent
from core.errors import AgentExecutionError
from core.registry import register_framework
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

        def call_model(state: AgentState) -> dict[str, Any]:
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

    def _get_lc_tools(self) -> list[StructuredTool]:
        lc_tools = []
        for name, fn, desc in self.shim_tools:
            lc_tools.append(
                StructuredTool.from_function(func=fn, name=name, description=desc)
            )
        return lc_tools

    def _lc_to_suite_msg(self, msg: BaseMessage) -> dict[str, Any]:
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

    def run(self, task: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        started_at = datetime.now(UTC).isoformat()
        try:
            full_task = task
            if context:
                ctx_str = "\n".join([f"{k}: {v}" for k, v in context.items()])
                full_task = f"CONTEXT:\n{ctx_str}\n\nTASK:\n{task}"

            initial_state = {"messages": [HumanMessage(content=full_task)]}
            final_state = self.graph.invoke(initial_state)
            messages = final_state.get("messages", [])
            last_msg = messages[-1] if messages else HumanMessage(content="")

            # Map ToolMessage results by tool_call_id
            tool_outputs: dict[str, str] = {}
            for m in messages:
                if isinstance(m, ToolMessage):
                    t_id = getattr(m, "tool_call_id", None)
                    if t_id:
                        tool_outputs[t_id] = str(m.content)

            steps: list[dict[str, Any]] = []
            all_tool_calls: list[dict[str, Any]] = []
            sequence = 1

            for m in messages:
                if isinstance(m, AIMessage):
                    tc_list = getattr(m, "tool_calls", []) or []
                    for tc in tc_list:
                        name = tc.get("name", "")
                        args = tc.get("args", {})
                        call_id = tc.get("id", "")
                        all_tool_calls.append({"name": name, "arguments": args})

                        raw_summary = tool_outputs.get(call_id, "")
                        result_summary = str(raw_summary)
                        if len(result_summary) > 300:
                            result_summary = result_summary[:297] + "..."

                        steps.append(
                            {
                                "sequence": sequence,
                                "kind": "tool_call",
                                "tool": name,
                                "arguments": args,
                                "result_summary": result_summary,
                            }
                        )
                        sequence += 1

            completed_at = datetime.now(UTC).isoformat()
            execution_receipt = {
                "execution_id": f"exec-{uuid.uuid4().hex[:12]}",
                "steps": steps,
                "started_at": started_at,
                "completed_at": completed_at,
                "status": "success",
            }

            return {
                "output": getattr(last_msg, "content", str(last_msg)),
                "tool_calls": all_tool_calls,
                "execution_receipt": execution_receipt,
            }
        except Exception as e:
            raise AgentExecutionError(f"LangGraph execution failed: {e!s}") from e
