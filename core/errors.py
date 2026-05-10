class AgenticSuiteError(Exception):
    """Base error for the Agentic Test Suite."""

    pass


class ShimError(AgenticSuiteError):
    """Raised when a shim simulator encounters a domain error."""

    pass


class LLMProviderError(AgenticSuiteError):
    """Raised when an LLM provider fails to communicate or parse responses."""

    pass


class AgentExecutionError(AgenticSuiteError):
    """Raised when an agent execution fails at the framework or logic level."""

    pass


class ConfigError(AgenticSuiteError):
    """Raised when configuration is missing or malformed."""

    pass
