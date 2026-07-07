import sys
import unittest
from pathlib import Path

# Ensure root is in sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(root_dir))

from core.mcp_client import MCPClient  # noqa: E402


class TestMCPIntegration(unittest.TestCase):
    """
    Validates stdio/SSE client connections and MCP tool execution.
    """

    def test_finance_mcp_stdio(self):
        client = MCPClient(
            command=sys.executable,
            args=["mcp_servers/finance_mcp/server.py"],
            transport="stdio",
        )
        try:
            tools = client.list_tools()
            tool_names = [t["name"] for t in tools]
            self.assertIn("get_account_balance", tool_names)
            self.assertIn("initiate_wire_transfer", tool_names)

            # Call tool
            res = client.call_tool("get_account_balance", {"account_id": "ACC-001"})
            self.assertIsNotNone(res)
            # Response comes as list of TextContent/ImageContent or raw depending on python-mcp client session returning format
            # In our wrapper we handle it, let's print and assert it contains ACC-001 or balance
            self.assertTrue(len(res) > 0)
        finally:
            client.close()

    def test_finance_mcp_sse(self):
        client = MCPClient(
            command=sys.executable,
            args=["mcp_servers/finance_mcp/server.py"],
            transport="sse",
        )
        try:
            tools = client.list_tools()
            tool_names = [t["name"] for t in tools]
            self.assertIn("get_account_balance", tool_names)
            self.assertIn("initiate_wire_transfer", tool_names)

            # Call tool
            res = client.call_tool("get_account_balance", {"account_id": "ACC-001"})
            self.assertIsNotNone(res)
        finally:
            client.close()

    def test_healthcare_mcp_sse(self):
        client = MCPClient(
            command=sys.executable,
            args=["mcp_servers/healthcare_mcp/server.py"],
            transport="sse",
        )
        try:
            tools = client.list_tools()
            tool_names = [t["name"] for t in tools]
            self.assertIn("get_patient_record", tool_names)
            self.assertIn("place_medication_order", tool_names)
        finally:
            client.close()

    def test_telecom_mcp_sse(self):
        client = MCPClient(
            command=sys.executable,
            args=["mcp_servers/telecom_mcp/server.py"],
            transport="sse",
        )
        try:
            tools = client.list_tools()
            tool_names = [t["name"] for t in tools]
            self.assertIn("get_customer_account", tool_names)
            self.assertIn("initiate_sim_swap", tool_names)
        finally:
            client.close()


if __name__ == "__main__":
    unittest.main()
