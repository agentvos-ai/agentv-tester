from typing import List, Dict, Any
from langchain_classic.agents import AgentExecutor, create_structured_chat_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import StructuredTool
from core.base_framework import BaseFrameworkAdapter, RunnableAgent
from core.registry import register_framework
from core.errors import AgentExecutionError
from core.tool_utils import ToolNormalizer


@register_framework("langchain")
class LangChainAdapter(BaseFrameworkAdapter):
    """
    Adapter for LangChain Structured Chat agents.
    """

    def build_agent(self, system_prompt: str) -> RunnableAgent:
        # 1. Wrap tools
        tools = self._get_lc_tools()

        # 2. Create Prompt
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt + "\nRespond to the user as best you can.\n\nYou have access to the following tools:\n{tools}\n\nTool Names: {tool_names}"),
                ("placeholder", "{chat_history}"),
                ("user", "{input}"),
                ("user", "{agent_scratchpad}"),
            ]
        )

        # 3. Use our LLM as a LangChain-compatible model
        # For simplicity, we'll implement a minimal wrapper
        lc_llm = self._get_lc_llm()

        agent = create_structured_chat_agent(lc_llm, tools, prompt)
        executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

        return LangChainRunnable(executor)

    def _get_lc_tools(self) -> List[StructuredTool]:
        return [
            StructuredTool.from_function(func=fn, name=name, description=desc)
            for name, fn, desc in self.shim_tools
        ]

    def _get_lc_llm(self):
        from langchain_core.language_models.chat_models import BaseChatModel
        from langchain_core.outputs import ChatResult, ChatGeneration
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
        
        adapter_self = self

        class SuiteChatModel(BaseChatModel):
            def _generate(self, messages, stop=None, run_manager=None, **kwargs):
                suite_msgs = []
                for m in messages:
                    if isinstance(m, HumanMessage):
                        suite_msgs.append({"role": "user", "content": str(m.content)})
                    elif isinstance(m, AIMessage):
                        suite_msgs.append({"role": "assistant", "content": str(m.content)})
                    elif isinstance(m, SystemMessage):
                        suite_msgs.append({"role": "system", "content": str(m.content)})
                    elif isinstance(m, ToolMessage):
                        suite_msgs.append({"role": "tool", "content": str(m.content), "tool_call_id": m.tool_call_id})

                # Normalise tools for the active provider
                provider_name = adapter_self.config.active_llm
                if provider_name == "gemini":
                    suite_tools = ToolNormalizer.to_gemini(adapter_self.shim_tools)
                elif provider_name == "claude":
                    suite_tools = ToolNormalizer.to_claude(adapter_self.shim_tools)
                else:
                    suite_tools = ToolNormalizer.to_openai(adapter_self.shim_tools)

                resp = adapter_self.llm.chat(suite_msgs, tools=suite_tools)
                msg = resp["choices"][0]["message"]
                
                # Convert suite tool_calls back to LangChain format
                lc_tool_calls = []
                for tc in msg.get("tool_calls", []):
                    if tc.get("type") == "function":
                        f = tc["function"]
                        lc_tool_calls.append({
                            "name": f["name"],
                            "args": f["arguments"],
                            "id": tc["id"]
                        })

                ai_msg = AIMessage(content=msg.get("content") or "", tool_calls=lc_tool_calls)
                return ChatResult(generations=[ChatGeneration(message=ai_msg)])

            @property
            def _llm_type(self):
                return "suite-llm"

        return SuiteChatModel()


class LangChainRunnable(RunnableAgent):
    def __init__(self, executor: AgentExecutor):
        self.executor = executor

    def run(self, task: str, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        try:
            full_task = task
            if context:
                ctx_str = "\n".join([f"{k}: {v}" for k, v in context.items()])
                full_task = f"CONTEXT:\n{ctx_str}\n\nTASK:\n{task}"

            result = self.executor.invoke({"input": full_task})
            # Extract tool calls from intermediate steps if available
            tool_calls = []
            if "intermediate_steps" in result:
                for action, _ in result["intermediate_steps"]:
                    tool_calls.append({
                        "name": action.tool,
                        "arguments": action.tool_input,
                    })

            return {
                "output": result["output"],
                "tool_calls": tool_calls,
            }
        except Exception as e:
            raise AgentExecutionError(f"LangChain execution failed: {str(e)}") from e
