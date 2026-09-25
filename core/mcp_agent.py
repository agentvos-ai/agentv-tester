import inspect
import logging
import sys
from typing import Any

from core.base_agent import BaseAgent
from core.mcp_client import MCPClient

from pydantic import BaseModel, Field, create_model

logger = logging.getLogger(__name__)


def _schema_to_pydantic_model(
    name: str, schema: dict[str, Any] | None
) -> type[BaseModel] | None:
    if not schema or "properties" not in schema:
        return None
    type_map = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict,
    }
    field_defs = {}
    required = set(schema.get("required", []))
    for prop_name, prop_info in schema.get("properties", {}).items():
        if not isinstance(prop_info, dict):
            prop_info = {}
        py_type = type_map.get(prop_info.get("type", "string"), Any)
        desc = prop_info.get("description", "")
        if prop_name in required:
            field_defs[prop_name] = (py_type, Field(..., description=desc))
        else:
            default_val = prop_info.get("default", None)
            field_defs[prop_name] = (
                py_type | None,
                Field(default=default_val, description=desc),
            )
    model_name = "".join(part.capitalize() for part in name.split("_")) + "Input"
    try:
        return create_model(model_name, **field_defs)
    except Exception as e:
        logger.warning(f"Could not create Pydantic model for {name}: {e}")
        return None


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
            schema = tool.get("input_schema") or tool.get("inputSchema")

            # Create a wrapped callable that invokes call_tool on the MCPClient
            wrapped_func = self._create_mcp_wrapper(name, schema)
            specs.append((name, wrapped_func, desc))

        return specs

    def _create_mcp_wrapper(
        self, tool_name: str, input_schema: dict[str, Any] | None = None
    ):
        def mcp_tool_wrapper(*args, **kwargs):
            merged_kwargs = dict(kwargs)
            if args:
                if len(args) == 1 and isinstance(args[0], dict):
                    merged_kwargs.update(args[0])
                elif input_schema and "properties" in input_schema:
                    prop_names = list(input_schema["properties"].keys())
                    for idx, arg in enumerate(args):
                        if idx < len(prop_names):
                            merged_kwargs[prop_names[idx]] = arg
            try:
                result = self._mcp_client.call_tool(tool_name, merged_kwargs)
                if isinstance(result, list):
                    text_parts = [part.text for part in result if hasattr(part, "text")]
                    return "\n".join(text_parts) if text_parts else str(result)
                return str(result)
            except Exception as e:
                logger.error(f"Error during MCP tool call '{tool_name}': {e}")
                return f"TOOL_ERROR: {e!s}"

        mcp_tool_wrapper.__name__ = tool_name
        mcp_tool_wrapper.input_schema = input_schema
        mcp_tool_wrapper.args_schema = _schema_to_pydantic_model(tool_name, input_schema)
        if input_schema and "properties" in input_schema:
            try:
                params = []
                required = set(input_schema.get("required", []))
                for prop_name in input_schema["properties"]:
                    default = (
                        inspect.Parameter.empty if prop_name in required else None
                    )
                    param = inspect.Parameter(
                        prop_name,
                        inspect.Parameter.POSITIONAL_OR_KEYWORD,
                        default=default,
                    )
                    params.append(param)
                mcp_tool_wrapper.__signature__ = inspect.Signature(params)
            except Exception as e:
                logger.warning(f"Could not build signature for {tool_name}: {e}")

        return mcp_tool_wrapper

    def close(self):
        """Cleans up the MCP client connection and background processes."""
        if getattr(self, "_mcp_client", None):
            self._mcp_client.close()
            self._mcp_client = None

    def __del__(self):
        self.close()
