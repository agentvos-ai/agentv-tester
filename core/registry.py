from typing import Type, Dict, Any, TypeVar
import logging
from core.errors import ConfigError

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Three-layer registry
_LLM_REGISTRY: Dict[str, Type[Any]] = {}
_FRAMEWORK_REGISTRY: Dict[str, Type[Any]] = {}
_AGENT_REGISTRY: Dict[str, Type[Any]] = {}
_SHIM_REGISTRY: Dict[str, Type[Any]] = {}


def register_llm(name: str) -> Any:
    """Decorator to register an LLM provider."""

    def decorator(cls: Type[T]) -> Type[T]:
        _LLM_REGISTRY[name] = cls
        logger.debug("Registered LLM provider: %s", name)
        return cls

    return decorator


def register_framework(name: str) -> Any:
    """Decorator to register a framework adapter."""

    def decorator(cls: Type[T]) -> Type[T]:
        _FRAMEWORK_REGISTRY[name] = cls
        logger.debug("Registered framework adapter: %s", name)
        return cls

    return decorator


def register_agent(name: str) -> Any:
    """Decorator to register a vertical agent."""

    def decorator(cls: Type[T]) -> Type[T]:
        _AGENT_REGISTRY[name] = cls
        logger.debug("Registered vertical agent: %s", name)
        return cls

    return decorator


def register_shim(name: str) -> Any:
    """Decorator to register an enterprise shim."""

    def decorator(cls: Type[T]) -> Type[T]:
        _SHIM_REGISTRY[name] = cls
        logger.debug("Registered shim: %s", name)
        return cls

    return decorator


def get_llm_provider(name: str) -> Type[Any]:
    """Retrieves an LLM provider class by name."""
    if name not in _LLM_REGISTRY:
        raise ConfigError(
            f"LLM provider '{name}' not found. Available: {list(_LLM_REGISTRY.keys())}"
        )
    return _LLM_REGISTRY[name]


def get_framework_adapter(name: str) -> Type[Any]:
    """Retrieves a framework adapter class by name."""
    if name not in _FRAMEWORK_REGISTRY:
        raise ConfigError(
            f"Framework adapter '{name}' not found. Available: {list(_FRAMEWORK_REGISTRY.keys())}"
        )
    return _FRAMEWORK_REGISTRY[name]


def get_agent_class(name: str) -> Type[Any]:
    """Retrieves a vertical agent class by name."""
    if name not in _AGENT_REGISTRY:
        raise ConfigError(
            f"Agent '{name}' not found. Available: {list(_AGENT_REGISTRY.keys())}"
        )
    return _AGENT_REGISTRY[name]


def get_shim_class(name: str) -> Type[Any]:
    """Retrieves a shim class by name."""
    if name not in _SHIM_REGISTRY:
        raise ConfigError(
            f"Shim '{name}' not found. Available: {list(_SHIM_REGISTRY.keys())}"
        )
    return _SHIM_REGISTRY[name]


def list_agents() -> list[str]:
    """Returns a list of all registered agent names."""
    return sorted(list(_AGENT_REGISTRY.keys()))


def list_llms() -> list[str]:
    """Returns a list of all registered LLM provider names."""
    return sorted(list(_LLM_REGISTRY.keys()))


def list_frameworks() -> list[str]:
    """Returns a list of all registered framework adapter names."""
    return sorted(list(_FRAMEWORK_REGISTRY.keys()))
