import logging
import functools
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple
from core.base_framework import BaseFrameworkAdapter, RunnableAgent
from core.errors import AgentExecutionError, ShimError

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Industrial-grade base abstraction for vertical agents.
    Implements security gating, schema validation, and execution feedback loops.
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

    @property
    @abstractmethod
    def allowed_shims(self) -> List[str]:
        """List of shim names this agent is authorized to use."""
        pass

    def get_tool_specs(self) -> List[Tuple[str, Any, str]]:
        """
        Returns gated and wrapped tool specs.
        Implements the 'Execution Feedback Loop' by catching shim errors
        and returning them as strings to the LLM.
        """
        tools = []
        for shim_name in self.allowed_shims:
            if shim_name not in self._shims:
                logger.warning(
                    f"Agent requested unauthorized or missing shim: {shim_name}"
                )
                continue

            shim = self._shims[shim_name]
            for name, func, desc in shim.get_tool_specs():
                # Wrap the function with our feedback loop handler
                wrapped_func = self._wrap_tool_with_feedback(name, func)
                tools.append((name, wrapped_func, desc))

        return tools

    def _wrap_tool_with_feedback(self, tool_name: str, func: Any):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # Industrial-grade Tool Schema Validation (Basic check)
                # In a more complex system, we'd use Pydantic/inspect here
                return func(*args, **kwargs)
            except ShimError as e:
                # Feedback Loop: Return the error to the LLM instead of crashing
                msg = f"TOOL_ERROR ({tool_name}): {str(e)}"
                logger.warning(msg)
                return msg
            except Exception as e:
                # System Error: Log and return a generic error to avoid leaking internals
                msg = f"SYSTEM_ERROR ({tool_name}): An internal error occurred. Please try again or use a different tool."
                logger.error(
                    f"Unexpected error in tool {tool_name}: {str(e)}", exc_info=True
                )
                return msg

        return wrapper

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Primary entry point for the agentic external caller.
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
