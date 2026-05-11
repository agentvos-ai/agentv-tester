import operator
from typing import Annotated, Sequence, TypedDict, List, Any, Dict
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import StructuredTool
from core.base_framework import BaseFrameworkAdapter, RunnableAgent
from core.registry import register_framework
from core.errors import AgentExecutionError


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

            response = self.llm.chat(
                suite_messages, tools=[self._lc_to_gemini_tool(t) for t in tools]
            )

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

    def _lc_to_suite_msg(self, msg: BaseMessage) -> Dict[str, str]:
        if isinstance(msg, HumanMessage):
            return {"role": "user", "content": str(msg.content)}
        if isinstance(msg, AIMessage):
            return {"role": "assistant", "content": str(msg.content)}
        if isinstance(msg, SystemMessage):
            return {"role": "system", "content": str(msg.content)}
        return {"role": "user", "content": str(msg.content)}

    def _lc_to_gemini_tool(self, lc_tool: StructuredTool) -> Dict[str, Any]:
        # Improved conversion to include parameters with Gemini-specific cleanup
        params = {"type": "OBJECT", "properties": {}, "required": []}
        if lc_tool.args_schema:
            schema = lc_tool.args_schema.model_json_schema()

            def clean_schema(s: Any) -> Any:
                if not isinstance(s, dict):
                    return s
                # Gemini doesn't support additionalProperties or title in function declarations
                s.pop("additionalProperties", None)
                s.pop("title", None)
                # s.pop("description", None)  <-- Removed: Description is valid as a field name, only invalid as a sibling to type in some specs.
                for k, v in s.items():
                    if isinstance(v, dict):
                        s[k] = clean_schema(v)
                    elif isinstance(v, list):
                        s[k] = [clean_schema(i) for i in v]
                return s

            clean_s = clean_schema(schema)
            props = clean_s.get("properties", {})
            params["properties"] = props

            # Ensure required properties actually exist in the properties dictionary
            raw_required = clean_s.get("required", [])
            params["required"] = [r for r in raw_required if r in props]

        return {
            "function_declarations": [
                {
                    "name": lc_tool.name,
                    "description": lc_tool.description,
                    "parameters": params,
                }
            ]
        }


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
