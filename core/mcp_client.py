import asyncio
import logging
import socket
import subprocess
import time
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


class MCPClient:
    """
    Client wrapper for stdio and SSE-based MCP servers.
    Handles startup, initialization, tool discovery, and tool execution.
    """

    def __init__(
        self,
        command: str,
        args: list[str],
        transport: str = "stdio",
        env: dict[str, str] | None = None,
    ):
        self.command = command
        self.args = args
        self.transport = transport
        self.env = env
        self.server_process = None
        self.sse_port = None
        self._loop = None

        if self.transport == "sse":
            self.sse_port = find_free_port()
            # Append sse and port arguments to the server process command line
            self.server_args = self.args + ["sse", f"--port={self.sse_port}"]
            self._start_sse_server()
        else:
            self.server_params = StdioServerParameters(
                command=command, args=args, env=env
            )

    def _start_sse_server(self):
        """Starts the MCP server in SSE mode as a background process and waits for it to be ready."""
        cmd = [self.command] + self.server_args
        logger.info(f"Starting MCP server in SSE mode: {' '.join(cmd)}")
        self.server_process = subprocess.Popen(cmd)
        # Poll the server port until it's open, with a timeout of 10 seconds
        start_time = time.time()
        while time.time() - start_time < 10:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                try:
                    s.connect(("127.0.0.1", self.sse_port))
                    logger.info(f"SSE server is up on port {self.sse_port}")
                    time.sleep(0.5)
                    return
                except (TimeoutError, ConnectionRefusedError):
                    time.sleep(0.2)
        logger.warning(
            f"SSE server on port {self.sse_port} did not start responding in time."
        )

    def close(self):
        """Terminates the background server process if running in SSE mode."""
        if self.server_process:
            logger.info("Terminating SSE MCP server background process.")
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
            self.server_process = None

    async def _async_list_tools(self) -> list[dict[str, Any]]:
        if self.transport == "sse":
            url = f"http://localhost:{self.sse_port}/sse"
            async with sse_client(url) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    response = await session.list_tools()
                    return [
                        {
                            "name": tool.name,
                            "description": tool.description,
                            "input_schema": tool.inputSchema,
                        }
                        for tool in response.tools
                    ]
        else:
            async with stdio_client(self.server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    response = await session.list_tools()
                    return [
                        {
                            "name": tool.name,
                            "description": tool.description,
                            "input_schema": tool.inputSchema,
                        }
                        for tool in response.tools
                    ]

    async def _async_call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        if self.transport == "sse":
            url = f"http://localhost:{self.sse_port}/sse"
            async with sse_client(url) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    response = await session.call_tool(name, arguments)
                    return response.content
        else:
            async with stdio_client(self.server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    response = await session.call_tool(name, arguments)
                    return response.content

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        try:
            return asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop

    def list_tools(self) -> list[dict[str, Any]]:
        """Synchronous wrapper to list tools from the MCP server."""
        try:
            loop = self._get_loop()
            if loop.is_running():
                future = asyncio.run_coroutine_threadsafe(
                    self._async_list_tools(), loop
                )
                return future.result()
            return loop.run_until_complete(self._async_list_tools())
        except Exception as e:
            logger.error(f"Failed to list tools from MCP server: {e}", exc_info=True)
            raise

    def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Synchronous wrapper to execute a tool on the MCP server."""
        try:
            loop = self._get_loop()
            if loop.is_running():
                future = asyncio.run_coroutine_threadsafe(
                    self._async_call_tool(name, arguments), loop
                )
                return future.result()
            return loop.run_until_complete(self._async_call_tool(name, arguments))
        except Exception as e:
            logger.error(
                f"Failed to call tool {name} on MCP server: {e}", exc_info=True
            )
            raise
