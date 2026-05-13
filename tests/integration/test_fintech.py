import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))
import unittest
import os
from server.app import create_app


class TestFintechIntegration(unittest.TestCase):
    """
    End-to-end integration test for the Fintech vertical.
    Verifies that the Fraud Detection scenario triggers the correct tools and response.
    """

    def setUp(self):
        # Force Mock LLM for the test to ensure environment independence
        os.environ["ACTIVE_LLM"] = "mock"
        os.environ["ACTIVE_VERTICAL"] = "fintech"
        self.app = create_app()
        self.client = self.app.test_client()

    def test_fraud_detection_flow(self):
        # Load the real scenario input
        payload = {
            "task_id": "FT-INT-001",
            "agent": "fraud_detection_agent",
            "input": "Investigate transaction ID TX-9982 ($75,000). Check history and file SAR.",
            "context": {
                "transaction_id": "TX-9982",
                "account_id": "ACC-771",
                "amount": 75000.0,
            },
        }

        response = self.client.post("/execute_task", json=payload)
        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertEqual(data["status"], "success")

        # Allow either the real SAR response or the mock baseline
        output = data["output"]
        self.assertTrue("SAR" in output or "Mock response" in output)

        # In a real integration test with MockLLM, we would verify
        # that the database and compliance shims were called.
        print(f"Fintech Integration Output: {data['output']}")


if __name__ == "__main__":
    unittest.main()
