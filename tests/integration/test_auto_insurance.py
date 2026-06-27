import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))
import unittest
import os
import json
from server.app import create_app

# Import MCP tools directly to verify unit-level correctness & hit 100% coverage
from mcp_servers.auto_insurance_mcp.server import (
    get_auto_claim,
    verify_accident_report,
    check_policy_coverage,
    detect_suspicious_claim,
    submit_auto_adjudication,
)


class TestAutoInsuranceIntegration(unittest.TestCase):
    """
    End-to-end integration and coverage tests for the Auto Insurance Claims MCP workflow.
    """

    def setUp(self):
        # Force Mock LLM and fintech vertical
        os.environ["ACTIVE_LLM"] = "mock"
        os.environ["ACTIVE_VERTICAL"] = "fintech"

        # Reset the synthetic auto claims database before each test
        self.fixture_path = (
            Path(__file__).resolve().parent.parent.parent
            / "fixtures"
            / "synthetic_auto_claims.json"
        )
        self.initial_data = {
            "claims": {
                "AUTO-CLAIM-001": {
                    "claim_id": "AUTO-CLAIM-001",
                    "policy_id": "POL-101",
                    "claim_type": "Collision",
                    "estimated_cost": 1200.00,
                    "date_of_accident": "2026-06-25",
                    "status": "SUBMITTED",
                    "police_report_filed": True,
                    "details": "Rear-end collision at traffic light.",
                },
                "AUTO-CLAIM-002": {
                    "claim_id": "AUTO-CLAIM-002",
                    "policy_id": "POL-102",
                    "claim_type": "Theft",
                    "estimated_cost": 8000.00,
                    "date_of_accident": "2026-06-26",
                    "status": "SUBMITTED",
                    "police_report_filed": False,
                    "details": "Vehicle reported stolen shortly after policy start.",
                },
            },
            "policies": {
                "POL-101": {
                    "deductible": 500.00,
                    "deductible_met": 500.00,
                    "payout_limit": 5000.00,
                    "covered_claims": ["Collision", "Comprehensive"],
                },
                "POL-102": {
                    "deductible": 1000.00,
                    "deductible_met": 200.00,
                    "payout_limit": 5000.00,
                    "covered_claims": [],
                },
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

    # ==========================================
    # 1. MCP Tools Direct Unit Coverage Tests
    # ==========================================

    def test_mcp_get_claim(self):
        # Claim exists in claims
        claim = get_auto_claim("AUTO-CLAIM-001")
        self.assertEqual(claim["claim_id"], "AUTO-CLAIM-001")

        # Claim does not exist
        not_found = get_auto_claim("INVALID-CLAIM")
        self.assertIn("error", not_found)

        # Claim in adjudicated_claims
        submit_auto_adjudication("AUTO-CLAIM-001", "APPROVED", 1200.00)
        adj_claim = get_auto_claim("AUTO-CLAIM-001")
        self.assertEqual(adj_claim["status"], "ADJUDICATED")

    def test_mcp_verify_accident_report(self):
        # Police report filed
        res_filed = verify_accident_report("AUTO-CLAIM-001")
        self.assertTrue(res_filed["valid"])

        # Police report not filed
        res_missing = verify_accident_report("AUTO-CLAIM-002")
        self.assertFalse(res_missing["valid"])

        # Claim not found
        res_not_found = verify_accident_report("INVALID-CLAIM")
        self.assertFalse(res_not_found["valid"])

    def test_mcp_check_policy_coverage(self):
        # Valid coverage and limits
        cov1 = check_policy_coverage("POL-101", "Collision", 1200.00)
        self.assertTrue(cov1["eligible"])
        self.assertEqual(cov1["payout_amount"], 1200.00)

        # Policy not found
        cov_not_found = check_policy_coverage("INVALID-POL", "Collision", 1200.00)
        self.assertFalse(cov_not_found["eligible"])

        # Claim type not covered
        cov_not_covered = check_policy_coverage("POL-102", "Collision", 1200.00)
        self.assertFalse(cov_not_covered["eligible"])

        # Deductible remaining and exceeds limit checks
        cov_deductible = check_policy_coverage("POL-102", "Theft", 8000.00)
        # Deductible = 1000, Met = 200, Remaining = 800.
        # Covered claim = [] in POL-102 so let's temporarily add Theft to covered for testing limits
        data = json.loads(self.fixture_path.read_text("utf-8"))
        data["policies"]["POL-102"]["covered_claims"] = ["Theft"]
        with open(self.fixture_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        cov_deductible = check_policy_coverage("POL-102", "Theft", 8000.00)
        self.assertTrue(cov_deductible["eligible"])
        # cost 8000 - deductible remaining 800 = 7200. Max payout limit is 5000.
        self.assertEqual(cov_deductible["payout_amount"], 5000.00)

    def test_mcp_detect_suspicious_claim(self):
        # Suspicious theft claim on POL-102
        susp = detect_suspicious_claim("POL-102", "Theft")
        self.assertTrue(susp["suspicious"])

        # Clean collision claim on POL-101
        clean = detect_suspicious_claim("POL-101", "Collision")
        self.assertFalse(clean["suspicious"])

    def test_mcp_submit_auto_adjudication_not_found(self):
        res = submit_auto_adjudication("INVALID-CLAIM", "DENIED", 0.0)
        self.assertEqual(res["status"], "failed")

    # ==========================================
    # 2. Agent E2E Happy & Fault Workflows
    # ==========================================

    def test_auto_claims_happy_flow(self):
        payload = {
            "task_id": "FT-AI-HAPPY",
            "agent": "auto_insurance_claims_agent",
            "input": "Process auto claim AUTO-CLAIM-001. Validate accident report, check risk flags, and apply policy rules.",
            "context": {"claim_id": "AUTO-CLAIM-001"},
        }

        response = self.client.post("/execute_task", json=payload)
        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("approved", data.get("output", "").lower())

    def test_auto_claims_fault_flow(self):
        payload = {
            "task_id": "FT-AI-FAULT",
            "agent": "auto_insurance_claims_agent",
            "input": "Process auto claim AUTO-CLAIM-002. Validate accident report, check risk flags, and apply policy rules.",
            "context": {"claim_id": "AUTO-CLAIM-002"},
        }

        response = self.client.post("/execute_task", json=payload)
        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("denied", data.get("output", "").lower())


if __name__ == "__main__":
    unittest.main()
