import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))
import unittest
import os
import json
from server.app import create_app


class TestClaimsProcessingIntegration(unittest.TestCase):
    """
    End-to-end integration test for the Claims Processing MCP workflow.
    """

    def setUp(self):
        # Force Mock LLM and healthcare vertical
        os.environ["ACTIVE_LLM"] = "mock"
        os.environ["ACTIVE_VERTICAL"] = "healthcare"

        # Reset the synthetic claims database before each test
        self.fixture_path = (
            Path(__file__).resolve().parent.parent.parent
            / "fixtures"
            / "synthetic_claims.json"
        )
        self.initial_data = {
            "claims": {
                "CLAIM-001": {
                    "claim_id": "CLAIM-001",
                    "patient_id": "PAT-001",
                    "procedure_code": "CPT-99213",
                    "billed_amount": 150.00,
                    "date_of_service": "2026-06-25",
                    "status": "SUBMITTED",
                    "details": "Standard outpatient office visit.",
                },
                "CLAIM-002": {
                    "claim_id": "CLAIM-002",
                    "patient_id": "PAT-001",
                    "procedure_code": "CPT-99213",
                    "billed_amount": 150.00,
                    "date_of_service": "2026-06-25",
                    "status": "SUBMITTED",
                    "details": "Duplicate submission of office visit.",
                },
            },
            "insurance_policies": {
                "PAT-001": {
                    "deductible": 500.00,
                    "deductible_met": 450.00,
                    "coinsurance_pct": 0.20,
                    "max_coverage_limit": 10000.00,
                    "covered_procedures": ["CPT-99213"],
                }
            },
            "adjudicated_claims": {},
        }
        with open(self.fixture_path, "w", encoding="utf-8") as f:
            json.dump(self.initial_data, f, indent=2)

        self.app = create_app()
        self.client = self.app.test_client()

    def tearDown(self):
        # Cleanup synthetic claims file
        if self.fixture_path.exists():
            try:
                os.remove(self.fixture_path)
            except Exception:
                pass

    def test_claims_processing_happy_flow(self):
        payload = {
            "task_id": "HC-CP-HAPPY",
            "agent": "claims_processing_agent",
            "input": "Process claim CLAIM-001. Validate fields, check for duplicates, and evaluate patient policy rules.",
            "context": {"claim_id": "CLAIM-001"},
        }

        response = self.client.post("/execute_task", json=payload)
        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("approved", data.get("output", "").lower())

    def test_claims_processing_fault_flow(self):
        payload = {
            "task_id": "HC-CP-FAULT",
            "agent": "claims_processing_agent",
            "input": "Process claim CLAIM-002. Validate fields, check for duplicates, and evaluate patient policy rules.",
            "context": {"claim_id": "CLAIM-002"},
        }

        response = self.client.post("/execute_task", json=payload)
        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("denied", data.get("output", "").lower())


if __name__ == "__main__":
    unittest.main()
