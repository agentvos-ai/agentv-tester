class AgenticSuiteError(Exception):
    """Base error for the Agentic Test Suite."""



class ShimError(AgenticSuiteError):
    """Raised when a shim simulator encounters a domain error."""



class LLMProviderError(AgenticSuiteError):
    """Raised when an LLM provider fails to communicate or parse responses."""



class AgentExecutionError(AgenticSuiteError):
    """Raised when an agent execution fails at the framework or logic level."""



class ConfigError(AgenticSuiteError):
    """Raised when configuration is missing or malformed."""

