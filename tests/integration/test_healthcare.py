import os
import re
import smtplib
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

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
        self.assertEqual(outbox[0]["channel"], "outbox")
        self.assertEqual(outbox[0]["destination"], "provider@clinic.example")

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

    def test_deterministic_1_default_path_remains_unchanged(self):
        """
        Deterministic Test 1: Verify default path remains unchanged when no notification fields supplied.
        - no notification fields supplied in request context;
        - tool call uses 'outbox' and 'provider@clinic.example';
        - existing healthcare tests continue to pass.
        """
        self.client.post(
            "/update_config",
            json={"framework": "langchain", "llm": "mock", "vertical": "healthcare"},
        )

        payload = {
            "task_id": "TEST-DEFAULT-NOTIF",
            "agent": "prior_auth_agent",
            "input": "Evaluate PAT-001 / CPT-99213 prior-authorization request.",
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
        notif_step = next(
            s for s in receipt["steps"] if s["tool"] == "send_provider_notification"
        )
        self.assertEqual(notif_step["arguments"].get("channel"), "outbox")
        self.assertEqual(
            notif_step["arguments"].get("destination"), "provider@clinic.example"
        )

        state_resp = self.client.get("/healthcare/state")
        self.assertEqual(state_resp.status_code, 200)
        state_data = state_resp.get_json()["state"]
        outbox = state_data["outbox"]
        self.assertEqual(len(outbox), 1)
        self.assertEqual(outbox[0]["channel"], "outbox")
        self.assertEqual(outbox[0]["destination"], "provider@clinic.example")
        self.assertEqual(outbox[0]["status"], "SENT")

    def test_deterministic_2_email_arguments_propagate(self):
        """
        Deterministic Test 2: Verify email arguments propagate from request context to tool.
        - request context contains notification_channel=email;
        - destination contains a synthetic test address;
        - send_provider_notification receives those exact values.
        """
        self.client.post(
            "/update_config",
            json={"framework": "langchain", "llm": "mock", "vertical": "healthcare"},
        )

        synthetic_dest = "demo-recipient@example.com"
        payload = {
            "task_id": "DEMO-UM-EMAIL",
            "agent": "prior_auth_agent",
            "input": "Evaluate PAT-002 / CPT-33510 and complete the required prior-authorization workflow.",
            "context": {
                "patient_id": "PAT-002",
                "procedure_code": "CPT-33510",
                "decision": "APPROVE",
                "notification_channel": "email",
                "notification_destination": synthetic_dest,
            },
        }

        response = self.client.post("/execute_task", json=payload)
        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertEqual(data["status"], "success")

        # Verify execution receipt specifies the business channel and destination
        receipt = data.get("execution_receipt")
        self.assertIsNotNone(receipt)
        notif_step = next(
            s for s in receipt["steps"] if s["tool"] == "send_provider_notification"
        )
        self.assertEqual(notif_step["arguments"].get("channel"), "email")
        self.assertEqual(notif_step["arguments"].get("destination"), synthetic_dest)

        # Verify durable state authority records notification in outbox with requested channel and destination
        state_resp = self.client.get("/healthcare/state")
        self.assertEqual(state_resp.status_code, 200)
        state_data = state_resp.get_json()["state"]
        outbox = state_data["outbox"]
        self.assertEqual(len(outbox), 1)
        self.assertEqual(outbox[0]["channel"], "email")
        self.assertEqual(outbox[0]["destination"], synthetic_dest)

    @patch("smtplib.SMTP")
    def test_deterministic_3_smtp_success(self, mock_smtp_cls):
        """
        Deterministic Test 3: Verify SMTP success path.
        - monkeypatch smtplib.SMTP;
        - verify send_message is called;
        - durable outbox row is channel=email, expected destination, status=SENT.
        """
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        dest = "dr.smith@clinic.example"
        with patch.dict(
            os.environ, {"SMTP_HOST": "smtp.test.example", "SMTP_PORT": "587"}
        ):
            auth_res = submit_authorization_decision(
                patient_id="PAT-001",
                procedure_code="CPT-99213",
                decision="APPROVE",
            )
            self.assertEqual(auth_res["status"], "completed")
            self.assertEqual(auth_res["record"]["decision"], "APPROVE")
            auth_id = auth_res["record"]["authorization_id"]

            notif_res = send_provider_notification(
                authorization_id=auth_id,
                channel="email",
                destination=dest,
                message="Your authorization request CPT-99213 has been approved.",
            )
            self.assertEqual(notif_res["status"], "completed")
            self.assertEqual(notif_res["delivery_status"], "SENT")
            self.assertEqual(notif_res["channel"], "email")
            self.assertEqual(notif_res["destination"], dest)

            # Verify smtplib.SMTP interactions
            mock_smtp_cls.assert_called_with("smtp.test.example", 587, timeout=5)
            self.assertTrue(mock_server.send_message.called)
            sent_msg = mock_server.send_message.call_args[0][0]
            self.assertEqual(sent_msg["To"], dest)
            self.assertEqual(
                sent_msg["Subject"], f"Prior Authorization Update: {auth_id}"
            )

            # Verify durable state ledger outbox and authorization notification_status
            state_resp = self.client.get("/healthcare/state")
            self.assertEqual(state_resp.status_code, 200)
            state_data = state_resp.get_json()["state"]

            outbox = state_data["outbox"]
            self.assertEqual(len(outbox), 1)
            self.assertEqual(outbox[0]["channel"], "email")
            self.assertEqual(outbox[0]["destination"], dest)
            self.assertEqual(outbox[0]["status"], "SENT")

            auth = next(
                a
                for a in state_data["authorizations"]
                if a["authorization_id"] == auth_id
            )
            self.assertEqual(auth["notification_status"], "SENT")

    @patch("smtplib.SMTP")
    def test_deterministic_4_smtp_failure(self, mock_smtp_cls):
        """
        Deterministic Test 4: Verify SMTP failure path.
        - monkeypatch SMTP to raise;
        - durable outbox row records status=FAILED;
        - authorization notification_status=FAILED.
        """
        mock_smtp_cls.side_effect = smtplib.SMTPConnectError(421, b"Connection refused")

        dest = "dr.jones@hospital.example"
        with patch.dict(os.environ, {"SMTP_HOST": "smtp.failing.example"}):
            auth_res = submit_authorization_decision(
                patient_id="PAT-001",
                procedure_code="CPT-99213",
                decision="APPROVE",
            )
            auth_id = auth_res["record"]["authorization_id"]

            notif_res = send_provider_notification(
                authorization_id=auth_id,
                channel="email",
                destination=dest,
                message="Prior-authorization status update.",
            )
            self.assertEqual(notif_res["status"], "completed")
            self.assertEqual(notif_res["delivery_status"], "FAILED")

            # Verify durable state ledger records FAILED status
            state_resp = self.client.get("/healthcare/state")
            self.assertEqual(state_resp.status_code, 200)
            state_data = state_resp.get_json()["state"]

            outbox = state_data["outbox"]
            self.assertEqual(len(outbox), 1)
            self.assertEqual(outbox[0]["channel"], "email")
            self.assertEqual(outbox[0]["destination"], dest)
            self.assertEqual(outbox[0]["status"], "FAILED")

            auth = next(
                a
                for a in state_data["authorizations"]
                if a["authorization_id"] == auth_id
            )
            self.assertEqual(auth["notification_status"], "FAILED")

    def test_deterministic_5_no_evaluator_coupling(self):
        """
        Deterministic Test 5: Verify no evaluator coupling.
        - static test/grep rejects imports or references to agentv_runtime,
          harness certificates, or AgentV cryptography from Tester application code.
        """
        app_dirs = [
            "core",
            "verticals",
            "server",
            "mcp_servers",
            "llm_providers",
            "frameworks",
        ]
        forbidden_patterns = [
            (r"\bagentv_runtime\b", "agentv_runtime import/reference"),
            (r"\bAgentVCertificate\b", "AgentV harness certificate reference"),
            (
                r"\bSignatureVerifier\b",
                "AgentV cryptographic signature verifier reference",
            ),
            (r"\bharness_certificate\b", "harness certificate reference"),
            (r"\bevaluator_flag\b", "evaluator flag reference"),
        ]

        violations = []
        for app_dir in app_dirs:
            dir_path = root_dir / app_dir
            if not dir_path.exists():
                continue
            for py_file in dir_path.rglob("*.py"):
                text = py_file.read_text(encoding="utf-8")
                for pat, label in forbidden_patterns:
                    matches = re.findall(pat, text, re.IGNORECASE)
                    if matches:
                        violations.append(
                            f"{py_file.relative_to(root_dir)}: found {label} ({matches})"
                        )

        self.assertEqual(
            violations,
            [],
            f"Evaluator coupling violations detected in application code: {violations}",
        )


if __name__ == "__main__":
    unittest.main()
