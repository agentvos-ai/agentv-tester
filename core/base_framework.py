from abc import ABC, abstractmethod
from typing import Any, List, Dict


class BaseFrameworkAdapter(ABC):
    """
    Translates a list of shim tools and an LLM provider into a framework-specific agent.
    """

    def __init__(self, llm_provider: Any, shim_tools: List[Any], config: Any):
        self.llm = llm_provider
        self.shim_tools = shim_tools
        self.config = config

    @abstractmethod
    def build_agent(self, system_prompt: str) -> Any:
        """Constructs a framework-specific agent runnable."""
        pass


class RunnableAgent(ABC):
    """Interface for the agent object returned by build_agent."""

    @abstractmethod
    def run(self, task: str, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """Executes a task."""
        pass
