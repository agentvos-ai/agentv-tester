from typing import List, Dict, Any
import autogen  # type: ignore
from core.base_framework import BaseFrameworkAdapter, RunnableAgent
from core.registry import register_framework
from core.errors import AgentExecutionError


class SuiteModelClient:
    """
    Custom AutoGen client bridge to our BaseLLMProvider.
    Ensures AutoGen agents use our unified LLM interface.
    """

    def __init__(self, config: Any, llm_provider: Any):
        self.llm = llm_provider
        self.model = config.model

    def create(self, params: Dict[str, Any]) -> Any:
        # Convert AutoGen params to our chat format
        messages = params.get("messages", [])
        tools = params.get("tools", None)

        # Call our unified provider
        response = self.llm.chat(messages, tools=tools)

        # Convert back to OpenAI-compatible format AutoGen expects
        from types import SimpleNamespace

        choices = []
        for c in response.get("choices", []):
            m = c.get("message", {})
            choice = SimpleNamespace(
                message=SimpleNamespace(
                    role=m.get("role"),
                    content=m.get("content"),
                    tool_calls=m.get("tool_calls"),
                ),
                finish_reason=c.get("finish_reason", "stop"),
            )
            choices.append(choice)

        return SimpleNamespace(
            choices=choices,
            usage=SimpleNamespace(
                prompt_tokens=response.get("usage", {}).get("prompt_tokens", 0),
                completion_tokens=response.get("usage", {}).get("completion_tokens", 0),
                total_tokens=response.get("usage", {}).get("total_tokens", 0),
            ),
            model=self.model,
        )

    def message_retrieval(self, response: Any) -> List[Any]:
        return [choice.message for choice in response.choices]

    def cost(self, response: Any) -> float:
        # Industrial cost model ($0.03 per 1k prompt tokens, $0.06 per 1k completion)
        u = response.usage
        return (u.prompt_tokens * 0.00003) + (u.completion_tokens * 0.00006)

    @staticmethod
    def get_common_config_list(
        config_list: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        return config_list


@register_framework("ag2")
class AG2Adapter(BaseFrameworkAdapter):
    """
    Adapter for AG2 (AutoGen) agents with a hardened custom client bridge.
    """

    def build_agent(self, system_prompt: str) -> RunnableAgent:
        # 1. Register our custom client
        active_llm_cfg = self.config.llms[self.config.active_llm]
        # In newer AutoGen/AG2 versions, custom models are registered via the class directly
        # and config_list just needs a placeholder to trigger the client lookup.
        client_config = {
            "model": active_llm_cfg.model,
            "api_type": "openai",
        }

        assistant = autogen.AssistantAgent(
            name="assistant",
            system_message=system_prompt,
            llm_config={
                "config_list": [client_config],
            },
        )

        # 2. Setup Bridge
        assistant.register_model_client(
            model_client_cls=SuiteModelClient, llm=self.llm, config=active_llm_cfg
        )

        # 3. User Proxy and Tools
        user_proxy = autogen.UserProxyAgent(
            name="user_proxy",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=10,
            is_termination_msg=lambda x: (
                x.get("content", "").rstrip().endswith("TERMINATE")
            ),
        )

        for name, fn, desc in self.shim_tools:
            autogen.register_function(
                fn, caller=assistant, executor=user_proxy, name=name, description=desc
            )

        return AG2Runnable(assistant, user_proxy)


class AG2Runnable(RunnableAgent):
    def __init__(self, assistant: Any, user_proxy: Any) -> None:
        self.assistant = assistant
        self.user_proxy = user_proxy

    def run(self, task: str, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        try:
            full_task = task
            if context:
                ctx_str = "\n".join([f"{k}: {v}" for k, v in context.items()])
                full_task = f"CONTEXT:\n{ctx_str}\n\nTASK:\n{task}"

            self.user_proxy.initiate_chat(self.assistant, message=full_task)

            # Extract tool calls from assistant history
            # AG2 stores history in assistant.chat_messages[user_proxy]
            chat_history = self.assistant.chat_messages.get(self.user_proxy, [])
            tool_calls = []
            for msg in chat_history:
                if "tool_calls" in msg and msg["tool_calls"]:
                    for tc in msg["tool_calls"]:
                        # Convert back to our suite format
                        tool_calls.append(
                            {
                                "name": tc["function"]["name"],
                                "args": tc["function"]["arguments"],
                            }
                        )

            last_msg = self.assistant.last_message()
            return {"output": last_msg.get("content", ""), "tool_calls": tool_calls}
        except Exception as e:
            raise AgentExecutionError(f"AG2 execution failed: {str(e)}") from e
