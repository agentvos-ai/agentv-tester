from typing import List, Dict, Any
from langchain_classic.agents import AgentExecutor, create_structured_chat_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import StructuredTool
from core.base_framework import BaseFrameworkAdapter, RunnableAgent
from core.registry import register_framework
from core.errors import AgentExecutionError


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
                ("system", system_prompt + "\nRespond to the user as best you can."),
                ("placeholder", "{chat_history}"),
                ("user", "{input}"),
                ("placeholder", "{agent_scratchpad}"),
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
        # This would be a more complex wrapper in a full production system
        # For now, we'll use a mock wrapper that calls self.llm.chat
        from langchain_core.language_models.chat_models import BaseChatModel
        from langchain_core.outputs import ChatResult, ChatGeneration

        class SuiteChatModel(BaseChatModel):
            llm: Any

            def _generate(self, messages, stop=None, run_manager=None, **kwargs):
                # Simple conversion
                suite_msgs = [
                    {"role": "user", "content": str(m.content)} for m in messages
                ]
                resp = self.llm.chat(suite_msgs)
                content = resp["choices"][0]["message"]["content"]
                return ChatResult(
                    generations=[ChatGeneration(message=AIMessage(content=content))]
                )

            @property
            def _llm_type(self):
                return "suite-llm"

        from langchain_core.messages import AIMessage

        return SuiteChatModel(llm=self.llm)


class LangChainRunnable(RunnableAgent):
    def __init__(self, executor: AgentExecutor):
        self.executor = executor

    def run(self, task: str, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        try:
            result = self.executor.invoke({"input": task})
            return {
                "output": result["output"],
                "tool_calls": [],  # LangChain executor handles tool calls internally
            }
        except Exception as e:
            raise AgentExecutionError(f"LangChain execution failed: {str(e)}") from e
