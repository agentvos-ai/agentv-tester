from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple


class BaseShim(ABC):
    """
    Base abstraction for enterprise shims.
    Enforces deterministic state management and tool specification.
    """

    def __init__(self, seed: int = 42):
        self.seed = seed
        self._state: dict[str, Any] = {}
        self.reset()

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for the shim."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Description of the service being simulated."""

    @abstractmethod
    def reset(self) -> None:
        """Resets shim state to a deterministic baseline."""

    def setup(self) -> None:
        """Performs initial setup, such as creating temporary directories or connecting to local backends."""

    def shutdown(self) -> None:
        """Gracefully shuts down the shim, closing any open resources and cleaning up."""

    @abstractmethod
    def get_tool_specs(self) -> list[tuple[str, Any, str]]:
        """
        Returns a list of tools exposed by this shim.
        Format: [(name, function, description), ...]
        """

    def get_state(self) -> dict[str, Any]:
        """Returns the current internal state of the shim."""
        return dict(self._state)
