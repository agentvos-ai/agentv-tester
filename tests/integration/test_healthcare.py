import os
import sys
import unittest
from pathlib import Path

# Ensure project root is in sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from mcp_servers.healthcare_mcp.server import (
    record_human_review,
    send_provider_notification,
    submit_authorization_decision,
)
from server.app import create_app


class TestHealthcareIntegration(unittest.TestCase):
    """
    End-to-end integration tests for Healthcare Prior-Authorization and clinical triage.
    """

    def setUp(self):
        os.environ["ACTIVE_LLM"] = "mock"
        os.environ["ACTIVE_VERTICAL"] = "healthcare"
        os.environ["ACTIVE_FRAMEWORK"] = "langchain"
        self.app = create_app()
        self.client = self.app.test_client()
        self.client.post("/healthcare/reset")

    def tearDown(self):
        self.client.post("/healthcare/reset")

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
        self.assertIn("analysis complete", data.get("output", "").lower())

    def test_prior_auth_happy_flow_langchain(self):
        """
        T-P0-01 to T-P0-05: Happy path prior-authorization via LangChain & Mock LLM.
        PAT-001 / CPT-99213 / APPROVE -> 5-step trajectory -> durable state commit & outbox.
        """
        self.client.post(
            "/update_config",
            json={"framework": "langchain", "llm": "mock", "vertical": "healthcare"},
        )

        payload = {
            "task_id": "HC-PA-HAPPY",
            "agent": "prior_auth_agent",
            "input": "Please check and submit prior-authorization for procedure CPT-99213 for patient PAT-001 with decision APPROVE.",
            "context": {
                "patient_id": "PAT-001",
                "procedure_code": "CPT-99213",
                "decision": "APPROVE",
            },
        }

        response = self.client.post("/execute_task", json=payload)
        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertEqual(data["status"], "success")

        # Verify Execution Receipt completeness and order (T-P0-03)
        receipt = data.get("execution_receipt")
        self.assertIsNotNone(receipt, "execution_receipt must be returned")
        self.assertEqual(receipt["status"], "success")

        step_tools = [s["tool"] for s in receipt["steps"]]
        expected_sequence = [
            "get_patient_diagnosis_codes",
            "get_payer_policy",
            "check_criteria_met",
            "submit_authorization_decision",
            "send_provider_notification",
        ]
        self.assertEqual(step_tools, expected_sequence)

        # Verify durable state authority records (T-P0-01, T-P0-05)
        state_resp = self.client.get("/healthcare/state")
        self.assertEqual(state_resp.status_code, 200)
        state_data = state_resp.get_json()["state"]

        # Check authorization ledger
        auths = state_data["authorizations"]
        self.assertEqual(len(auths), 1)
        auth = auths[0]
        self.assertEqual(auth["patient_id"], "PAT-001")
        self.assertEqual(auth["procedure_code"], "CPT-99213")
        self.assertEqual(auth["decision"], "APPROVE")
        self.assertEqual(auth["decision_source"], "AI_ASSISTED")
        self.assertTrue(auth["criteria_met"])
        self.assertFalse(auth["human_review_required"])
        self.assertEqual(auth["notification_status"], "SENT")

        # Check outbox ledger
        outbox = state_data["outbox"]
        self.assertEqual(len(outbox), 1)
        self.assertEqual(outbox[0]["authorization_id"], auth["authorization_id"])
        self.assertEqual(outbox[0]["status"], "SENT")

    def test_prior_auth_adverse_flow_langchain(self):
        """
        T-P0-01 to T-P0-05: Adverse path prior-authorization via LangChain & Mock LLM.
        PAT-002 / CPT-33510 / DENY -> Criteria fail -> Human review -> Commit DENY -> Outbox.
        """
        self.client.post(
            "/update_config",
            json={"framework": "langchain", "llm": "mock", "vertical": "healthcare"},
        )

        payload = {
            "task_id": "HC-PA-FAULT",
            "agent": "prior_auth_agent",
            "input": "Please check and submit prior-authorization for procedure CPT-33510 for patient PAT-002 with decision APPROVE.",
            "context": {
                "patient_id": "PAT-002",
                "procedure_code": "CPT-33510",
                "decision": "APPROVE",
            },
        }

        response = self.client.post("/execute_task", json=payload)
        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertEqual(data["status"], "success")

        # Verify execution receipt includes human review and commit
        receipt = data.get("execution_receipt")
        self.assertIsNotNone(receipt)
        step_tools = [s["tool"] for s in receipt["steps"]]
        self.assertIn("get_patient_diagnosis_codes", step_tools)
        self.assertIn("get_payer_policy", step_tools)
        self.assertIn("check_criteria_met", step_tools)
        self.assertIn("request_human_review", step_tools)
        self.assertIn("record_human_review", step_tools)
        self.assertIn("submit_authorization_decision", step_tools)
        self.assertIn("send_provider_notification", step_tools)

        # Verify durable state has human review evidence linked
        state_resp = self.client.get("/healthcare/state")
        self.assertEqual(state_resp.status_code, 200)
        state_data = state_resp.get_json()["state"]

        auths = state_data["authorizations"]
        self.assertEqual(len(auths), 1)
        auth = auths[0]
        self.assertEqual(auth["patient_id"], "PAT-002")
        self.assertEqual(auth["procedure_code"], "CPT-33510")
        self.assertEqual(auth["decision"], "DENY")
        self.assertEqual(auth["decision_source"], "HUMAN_REVIEWED")
        self.assertTrue(auth["human_review_required"])
        self.assertIsNotNone(auth["human_review_id"])

        reviews = state_data["human_reviews"]
        self.assertEqual(len(reviews), 1)
        self.assertEqual(reviews[0]["review_id"], auth["human_review_id"])
        self.assertEqual(reviews[0]["reviewer_type"], "LICENSED_PHYSICIAN")

    def test_prior_auth_happy_flow_langgraph(self):
        """
        Verify that LangGraph adapter also generates complete execution receipt.
        """
        self.client.post(
            "/update_config",
            json={"framework": "langgraph", "llm": "mock", "vertical": "healthcare"},
        )

        payload = {
            "task_id": "HC-PA-HAPPY",
            "agent": "prior_auth_agent",
            "input": "Please check and submit prior-authorization for procedure CPT-99213 for patient PAT-001 with decision APPROVE.",
            "context": {
                "patient_id": "PAT-001",
                "procedure_code": "CPT-99213",
                "decision": "APPROVE",
            },
        }

        response = self.client.post("/execute_task", json=payload)
        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertEqual(data["status"], "success")

        receipt = data.get("execution_receipt")
        self.assertIsNotNone(receipt)
        self.assertEqual(receipt["status"], "success")
        step_tools = [s["tool"] for s in receipt["steps"]]
        self.assertEqual(
            step_tools,
            [
                "get_patient_diagnosis_codes",
                "get_payer_policy",
                "check_criteria_met",
                "submit_authorization_decision",
                "send_provider_notification",
            ],
        )

    def test_mcp_tools_human_review_gate(self):
        """
        T-P0-02: Direct test of healthcare MCP server human review gate.
        PAT-002 / CPT-33510 cannot commit DENY without human review.
        After record_human_review, commit DENY succeeds and reviewer evidence persists.
        """
        # 1. Attempt DENY without human review -> must fail
        fail_res = submit_authorization_decision(
            patient_id="PAT-002", procedure_code="CPT-33510", decision="DENY"
        )
        self.assertEqual(fail_res["status"], "failed")
        self.assertIn("human review artifact required", fail_res["error"].lower())
        self.assertTrue(fail_res.get("human_review_required"))

        # 2. Record human review artifact
        rev_res = record_human_review(
            patient_id="PAT-002",
            procedure_code="CPT-33510",
            reviewer_id="MD-LIC-4491",
            reviewer_type="LICENSED_PHYSICIAN",
            disposition="DENY",
            clinical_notes="Coronary artery disease criteria missing recent stress test.",
        )
        self.assertEqual(rev_res["status"], "completed")
        rev_id = rev_res["review_id"]

        # 3. Re-attempt DENY -> must succeed
        success_res = submit_authorization_decision(
            patient_id="PAT-002", procedure_code="CPT-33510", decision="DENY"
        )
        self.assertEqual(success_res["status"], "denied")
        self.assertIn("record", success_res)
        auth_record = success_res["record"]
        self.assertEqual(auth_record["human_review_id"], rev_id)
        self.assertEqual(auth_record["decision_source"], "HUMAN_REVIEWED")

        # 4. Dispatch notification
        notif_res = send_provider_notification(
            authorization_id=auth_record["authorization_id"],
            channel="outbox",
            destination="provider@cardiology.example",
            message="Prior-authorization CPT-33510 denied following physician review.",
        )
        self.assertEqual(notif_res["status"], "completed")
        self.assertEqual(notif_res["delivery_status"], "SENT")


if __name__ == "__main__":
    unittest.main()
