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
        # AutoGen expects an object with 'choices' and 'usage'
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
        return 0.0

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
        client_config = {
            "model": self.config.llm.model,
            "model_client_cls": "SuiteModelClient",
        }

        assistant = autogen.AssistantAgent(
            name="assistant",
            system_message=system_prompt,
            llm_config={
                "config_list": [client_config],
                "model_client_cls": SuiteModelClient,  # Pass the class reference
            },
        )

        # 2. Setup Bridge (AutoGen requires registering the client instance)
        assistant.register_model_client(
            model_client_cls=SuiteModelClient, llm=self.llm, config=self.config.llm
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
            self.user_proxy.initiate_chat(self.assistant, message=task)
            last_msg = self.assistant.last_message()
            return {"output": last_msg.get("content", ""), "tool_calls": []}
        except Exception as e:
            raise AgentExecutionError(f"AG2 execution failed: {str(e)}") from e
