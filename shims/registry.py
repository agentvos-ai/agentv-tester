from typing import Any, Dict, List, Tuple
from shims import BaseShim
from core.registry import get_shim_class


class ShimRegistry:
    """Manages active shims with hot-swap support."""

    def __init__(self, enabled_shims: List[str], seed: int = 42):
        self._seed = seed
        self._enabled_names = enabled_shims
        self.shims: Dict[str, BaseShim] = {}
        self.initialize_shims()

    def initialize_shims(self):
        """Initializes and sets up all enabled shims."""
        for name in self._enabled_names:
            shim_cls = get_shim_class(name)
            instance = shim_cls(seed=self._seed)
            instance.setup()
            self.shims[name] = instance

    def hot_swap(self, shim_name: str, new_shim_instance: BaseShim):
        """Allows swapping a shim at runtime for advanced testing scenarios."""
        self.shims[shim_name] = new_shim_instance

    def get_all_tools(self) -> List[Tuple[str, Any, str]]:
        """Aggregates all tool specs from all active shims."""
        all_tools = []
        for shim in self.shims.values():
            all_tools.extend(shim.get_tool_specs())
        return all_tools

    def setup_all(self):
        """Calls setup on all active shims."""
        for shim in self.shims.values():
            shim.setup()

    def reset_all(self):
        """Resets every active shim to its deterministic baseline."""
        for shim in self.shims.values():
            shim.reset()

    def shutdown_all(self):
        """Shuts down all active shims."""
        for shim in self.shims.values():
            shim.shutdown()
        self.shims.clear()
