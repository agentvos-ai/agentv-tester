import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))
import os
import unittest

from server.app import create_app


class TestTelecomIntegration(unittest.TestCase):
    """
    End-to-end integration test for the Telecom vertical.
    """

    def setUp(self):
        # Force Mock LLM for the test
        os.environ["ACTIVE_LLM"] = "mock"
        os.environ["ACTIVE_VERTICAL"] = "telecom"
        self.app = create_app()
        self.client = self.app.test_client()

    def test_network_fault_flow(self):
        payload = {
            "task_id": "TC-INT-001",
            "agent": "network_fault_agent",
            "input": "Detect outage in sector SE-5. Trigger repair and open ticket.",
            "context": {
                "sector_id": "SE-5",
                "node_id": "NODE-01",
                "fault_type": "OUTAGE",
            },
        }

        response = self.client.post("/execute_task", json=payload)
        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertEqual(data["status"], "success")
        # Verify NOC logic in output
        output = data.get("output", "").lower()
        self.assertTrue(
            "mock" in output or "stable" in output or "diagnostic" in output
        )


if __name__ == "__main__":
    unittest.main()
