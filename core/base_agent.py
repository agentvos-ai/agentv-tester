from abc import ABC, abstractmethod
from typing import List, Dict, Any
from core.base_framework import BaseFrameworkAdapter, RunnableAgent
from core.errors import AgentExecutionError


class BaseAgent(ABC):
    """
    Base abstraction for all 12 vertical agents.
    Handles framework-agnostic execution logic.
    """

    def __init__(
        self, config: Any, framework: BaseFrameworkAdapter, shims: Dict[str, Any]
    ):
        self.config = config
        self.framework = framework
        self._shims = shims
        self._runnable: RunnableAgent | None = None

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """The core instruction set for the agent."""
        pass

    @abstractmethod
    def get_tool_specs(self) -> List[Any]:
        """Returns the subset of shims this agent uses as tools."""
        pass

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Primary entry point for the agentic external caller.

        Args:
            task: {"task_id": str, "input": str, "context": dict}

        Returns:
            {"status": "success", "output": str, "tool_calls": list}
        """
        if not self._runnable:
            # Build the agent within the chosen framework on first run
            self._runnable = self.framework.build_agent(self.system_prompt)

        task_input = task.get("input", "")
        context = task.get("context", {})

        try:
            result = self._runnable.run(task_input, context=context)
            return {
                "status": "success",
                "task_id": task.get("task_id"),
                "output": result["output"],
                "tool_calls": result.get("tool_calls", []),
            }
        except Exception as e:
            raise AgentExecutionError(f"Agent execution failed: {str(e)}") from e
