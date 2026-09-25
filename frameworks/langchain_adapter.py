import uuid
from datetime import UTC, datetime
from typing import Any

from langchain_classic.agents import AgentExecutor, create_structured_chat_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import StructuredTool

from core.base_framework import BaseFrameworkAdapter, RunnableAgent
from core.errors import AgentExecutionError
from core.registry import register_framework
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
                (
                    "system",
                    system_prompt
                    + "\nRespond to the user as best you can.\n\nYou have access to the following tools:\n{tools}\n\nTool Names: {tool_names}",
                ),
                ("placeholder", "{chat_history}"),
                ("user", "{input}"),
                ("user", "{agent_scratchpad}"),
            ]
        )

        # 3. Use our LLM as a LangChain-compatible model
        # For simplicity, we'll implement a minimal wrapper
        lc_llm = self._get_lc_llm()

        agent = create_structured_chat_agent(lc_llm, tools, prompt)
        executor = AgentExecutor(
            agent=agent, tools=tools, verbose=True, return_intermediate_steps=True
        )

        return LangChainRunnable(executor)

    def _get_lc_tools(self) -> list[StructuredTool]:
        lc_tools = []
        for name, fn, desc in self.shim_tools:
            args_schema = getattr(fn, "args_schema", None)
            if args_schema:
                lc_tools.append(
                    StructuredTool.from_function(
                        func=fn, name=name, description=desc, args_schema=args_schema
                    )
                )
            else:
                lc_tools.append(
                    StructuredTool.from_function(func=fn, name=name, description=desc)
                )
        return lc_tools

    def _get_lc_llm(self):
        from langchain_core.language_models.chat_models import BaseChatModel
        from langchain_core.messages import (
            AIMessage,
            HumanMessage,
            SystemMessage,
            ToolMessage,
        )
        from langchain_core.outputs import ChatGeneration, ChatResult

        adapter_self = self

        class SuiteChatModel(BaseChatModel):
            def _generate(self, messages, stop=None, run_manager=None, **kwargs):
                suite_msgs = []
                for m in messages:
                    if isinstance(m, HumanMessage):
                        suite_msgs.append({"role": "user", "content": str(m.content)})
                    elif isinstance(m, AIMessage):
                        suite_msgs.append(
                            {"role": "assistant", "content": str(m.content)}
                        )
                    elif isinstance(m, SystemMessage):
                        suite_msgs.append({"role": "system", "content": str(m.content)})
                    elif isinstance(m, ToolMessage):
                        suite_msgs.append(
                            {
                                "role": "tool",
                                "content": str(m.content),
                                "tool_call_id": m.tool_call_id,
                            }
                        )

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
                        lc_tool_calls.append(
                            {"name": f["name"], "args": f["arguments"], "id": tc["id"]}
                        )

                ai_msg = AIMessage(
                    content=msg.get("content") or "", tool_calls=lc_tool_calls
                )
                return ChatResult(generations=[ChatGeneration(message=ai_msg)])

            @property
            def _llm_type(self):
                return "suite-llm"

        return SuiteChatModel()


class LangChainRunnable(RunnableAgent):
    def __init__(self, executor: AgentExecutor):
        self.executor = executor

    def run(self, task: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        started_at = datetime.now(UTC).isoformat()
        try:
            full_task = task
            if context:
                ctx_str = "\n".join([f"{k}: {v}" for k, v in context.items()])
                full_task = f"CONTEXT:\n{ctx_str}\n\nTASK:\n{task}"

            result = self.executor.invoke({"input": full_task})
            # Extract tool calls and build execution receipt steps
            tool_calls = []
            steps = []
            seq = 1
            if "intermediate_steps" in result:
                for action, observation in result["intermediate_steps"]:
                    t_name = getattr(action, "tool", "")
                    t_input = getattr(action, "tool_input", {})
                    tool_calls.append(
                        {
                            "name": t_name,
                            "arguments": t_input,
                        }
                    )
                    obs_str = str(observation)
                    if len(obs_str) > 300:
                        obs_str = obs_str[:297] + "..."
                    steps.append(
                        {
                            "sequence": seq,
                            "kind": "tool_call",
                            "tool": t_name,
                            "arguments": t_input,
                            "result_summary": obs_str,
                        }
                    )
                    seq += 1

            completed_at = datetime.now(UTC).isoformat()
            execution_receipt = {
                "execution_id": f"exec-{uuid.uuid4().hex[:12]}",
                "steps": steps,
                "started_at": started_at,
                "completed_at": completed_at,
                "status": "success",
            }

            return {
                "output": result["output"],
                "tool_calls": tool_calls,
                "execution_receipt": execution_receipt,
            }
        except Exception as e:
            raise AgentExecutionError(f"LangChain execution failed: {e!s}") from e
