import os
import tempfile
import unittest
from pathlib import Path

from mcp_servers.finance_mcp.server import initiate_wire_transfer
from server.app import create_app
from server.finance_state_service import FinanceStateService


class TestFinanceStateService(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = Path(self.temp_dir.name) / "finance.sqlite"
        self.service = FinanceStateService(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_wire_commit_is_visible_in_independent_state(self):
        before = self.service.snapshot()
        result = self.service.initiate_wire_transfer(
            "ACC-001", "ACC-999", 100.0, "USD", "fixture test", "TRF-001"
        )
        after = self.service.snapshot()

        self.assertEqual(result["status"], "completed")
        self.assertEqual(after["state"]["accounts"]["ACC-001"]["balance"], 149900.0)
        self.assertEqual(after["state"]["transfers"][0]["transfer_id"], "TRF-001")
        self.assertNotEqual(before["state_hash"], after["state_hash"])

    def test_reset_restores_fixture_deterministically(self):
        baseline = self.service.snapshot()
        self.service.initiate_wire_transfer(
            "ACC-001", "ACC-999", 100.0, "USD", "fixture test", "TRF-002"
        )
        reset = self.service.reset_state()

        self.assertEqual(reset["state"], baseline["state"])
        self.assertEqual(reset["state_hash"], baseline["state_hash"])


class TestFinanceStateEndpoints(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = Path(self.temp_dir.name) / "finance_endpoints.sqlite"
        os.environ["FINANCE_STATE_DB"] = str(self.db_path)
        self.app = create_app()
        self.client = self.app.test_client()

    def tearDown(self):
        os.environ.pop("FINANCE_STATE_DB", None)
        self.temp_dir.cleanup()

    def test_endpoints_observe_mcp_wire_commit(self):
        initial = self.client.get("/finance/state").get_json()
        self.assertIn("accounts", initial["state"])
        self.assertEqual(initial["state"]["transfers"], [])
        self.assertTrue(initial["state_hash"].startswith("sha256:"))
        self.assertTrue(initial["receipt_hash"].startswith("sha256:"))

        result = initiate_wire_transfer("ACC-001", "ACC-999", 100.0, "USD", "test")
        self.assertEqual(result["status"], "completed")
        state = self.client.get("/finance/state").get_json()["state"]
        self.assertEqual(state["transfers"][0]["transfer_id"], result["transfer_id"])

        reset = self.client.post("/finance/reset").get_json()
        self.assertEqual(reset["status"], "reset")
        self.assertEqual(reset["snapshot"]["state"], initial["state"])
