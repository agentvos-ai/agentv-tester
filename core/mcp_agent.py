import logging
import sys
from typing import Any

from core.base_agent import BaseAgent
from core.mcp_client import MCPClient

logger = logging.getLogger(__name__)


class BaseMCPAgent(BaseAgent):
    """
    Subclass of BaseAgent that natively connects to an stdio or SSE-based MCP server
    and exposes its tools dynamically to the framework adapter.
    """

    mcp_server_script: str = (
        ""  # Path relative to workspace root, e.g. "mcp_servers/finance_mcp/server.py"
    )
    mcp_transport: str = "stdio"  # "stdio" or "sse"

    def __init__(self, config: Any, framework: Any, shims: dict[str, Any]):
        super().__init__(config, framework, shims)
        self._mcp_client = None

    @property
    def allowed_shims(self) -> list[str]:
        # MCP agents bypass legacy shims since all tools are served via MCP
        return []

    def get_tool_specs(self) -> list[tuple[str, Any, str]]:
        """
        Connects to the MCP server, discovers tools, and wraps them as functions
        compatible with the framework adapters.
        """
        if not self.mcp_server_script:
            logger.error("No mcp_server_script defined for this agent.")
            return []

        # Start MCP client using chosen transport
        self._mcp_client = MCPClient(
            command=sys.executable,
            args=[self.mcp_server_script],
            transport=self.mcp_transport,
        )

        try:
            mcp_tools = self._mcp_client.list_tools()
        except Exception as e:
            logger.error(
                f"Failed to load tools from MCP server {self.mcp_server_script}: {e}"
            )
            return []

        specs = []
        for tool in mcp_tools:
            name = tool["name"]
            desc = tool["description"]

            # Create a wrapped callable that invokes call_tool on the MCPClient
            wrapped_func = self._create_mcp_wrapper(name)
            specs.append((name, wrapped_func, desc))

        return specs

    def _create_mcp_wrapper(self, tool_name: str):
        def mcp_tool_wrapper(**kwargs):
            try:
                result = self._mcp_client.call_tool(tool_name, kwargs)
                if isinstance(result, list):
                    text_parts = [part.text for part in result if hasattr(part, "text")]
                    return "\n".join(text_parts) if text_parts else str(result)
                return str(result)
            except Exception as e:
                logger.error(f"Error during MCP tool call '{tool_name}': {e}")
                return f"TOOL_ERROR: {e!s}"

        mcp_tool_wrapper.__name__ = tool_name
        return mcp_tool_wrapper

    def close(self):
        """Cleans up the MCP client connection and background processes."""
        if self._mcp_client:
            self._mcp_client.close()
            self._mcp_client = None

    def __del__(self):
        self.close()
