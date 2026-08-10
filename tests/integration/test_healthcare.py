import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))
import os
import unittest

from server.app import create_app


class TestHealthcareIntegration(unittest.TestCase):
    """
    End-to-end integration test for the Healthcare vertical.
    """

    def setUp(self):
        # Force Mock LLM for the test
        os.environ["ACTIVE_LLM"] = "mock"
        os.environ["ACTIVE_VERTICAL"] = "healthcare"
        self.app = create_app()
        self.client = self.app.test_client()

    def test_clinical_triage_flow(self):
        payload = {
            "task_id": "HC-INT-001",
            "agent": "clinical_triage_agent",
            "input": "Patient P-11 has heart rate 145 and SpO2 88%. Prioritize and alert.",
            "context": {
                "patient_id": "P-11",
                "symptoms": ["High heart rate", "Low SpO2"],
            },
        }

        response = self.client.post("/execute_task", json=payload)
        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertEqual(data["status"], "success")
        # Verify urgency logic in output
        self.assertIn("analysis complete", data.get("output", "").lower())


if __name__ == "__main__":
    unittest.main()
