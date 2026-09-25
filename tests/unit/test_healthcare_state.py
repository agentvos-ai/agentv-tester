import os
import tempfile
import unittest
from pathlib import Path

from server.app import create_app
from server.authorization_state_service import (
    AuthorizationStateService,
    HealthcareStateService,
)


class TestHealthcareStateService(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = Path(self.temp_dir.name) / "test_hc_state.sqlite"
        self.service = AuthorizationStateService(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_durable_persistence_across_instances(self):
        # 1. Commit an authorization in instance 1
        record = self.service.commit_authorization(
            patient_id="PAT-001",
            procedure_code="CPT-99213",
            decision="APPROVE",
            criteria_met=True,
            authorization_id="AUTH-TEST-001",
        )
        self.assertEqual(record["authorization_id"], "AUTH-TEST-001")
        self.assertEqual(record["decision"], "APPROVE")
        self.assertEqual(record["decision_source"], "AI_ASSISTED")
        self.assertFalse(record["human_review_required"])
        self.assertIsNone(record["human_review_id"])

        # 2. Re-instantiate service pointing to same SQLite file using HealthcareStateService alias
        service2 = HealthcareStateService(self.db_path)
        persisted = service2.get_authorization("AUTH-TEST-001")
        self.assertIsNotNone(persisted)
        self.assertEqual(persisted["patient_id"], "PAT-001")
        self.assertEqual(persisted["procedure_code"], "CPT-99213")
        self.assertEqual(persisted["decision"], "APPROVE")

    def test_canonical_hash_changes_with_state(self):
        snap1 = self.service.snapshot()
        hash1 = snap1["state_hash"]
        self.assertTrue(hash1.startswith("sha256:"))

        self.service.commit_authorization(
            patient_id="PAT-001",
            procedure_code="CPT-99213",
            decision="APPROVE",
            criteria_met=True,
        )
        snap2 = self.service.snapshot()
        hash2 = snap2["state_hash"]

        self.assertNotEqual(hash1, hash2)
        self.assertTrue(hash2.startswith("sha256:"))

    def test_reset_restores_clean_fixture(self):
        self.service.commit_authorization(
            patient_id="PAT-001",
            procedure_code="CPT-99213",
            decision="APPROVE",
            criteria_met=True,
        )
        self.assertEqual(len(self.service.list_authorizations()), 1)

        self.service.reset_state()
        self.assertEqual(len(self.service.list_authorizations()), 0)
        self.assertEqual(len(self.service.list_outbox()), 0)
        self.assertEqual(len(self.service.list_human_reviews()), 0)

    def test_adverse_decision_requires_human_review(self):
        # WA ESSB 5395 & IA HF 2635 enforcement:
        # Attempting DENY without human review artifact raises ValueError
        with self.assertRaises(ValueError) as ctx:
            self.service.commit_authorization(
                patient_id="PAT-002",
                procedure_code="CPT-33510",
                decision="DENY",
                criteria_met=False,
            )
        self.assertIn(
            "licensed human review artifact required", str(ctx.exception).lower()
        )

        # Now record valid human review
        review = self.service.record_human_review(
            patient_id="PAT-002",
            procedure_code="CPT-33510",
            reviewer_id="MD-LIC-4491",
            reviewer_type="LICENSED_PHYSICIAN",
            disposition="DENY",
            clinical_notes="Stress test and cardiology referral missing from record.",
        )
        self.assertTrue(review["review_id"].startswith("REV-"))

        # Now commit DENY succeeds with reviewer evidence attached
        committed = self.service.commit_authorization(
            patient_id="PAT-002",
            procedure_code="CPT-33510",
            decision="DENY",
            criteria_met=False,
        )
        self.assertEqual(committed["decision"], "DENY")
        self.assertEqual(committed["decision_source"], "HUMAN_REVIEWED")
        self.assertTrue(committed["human_review_required"])
        self.assertEqual(committed["human_review_id"], review["review_id"])

    def test_provider_notification_outbox(self):
        auth = self.service.commit_authorization(
            patient_id="PAT-001",
            procedure_code="CPT-99213",
            decision="APPROVE",
            criteria_met=True,
        )
        auth_id = auth["authorization_id"]

        notif = self.service.send_provider_notification(
            authorization_id=auth_id,
            channel="outbox",
            destination="clinic@provider.example",
            message="Prior authorization CPT-99213 approved.",
        )
        self.assertEqual(notif["status"], "SENT")
        self.assertEqual(notif["authorization_id"], auth_id)

        # Verify authorization status updated
        updated_auth = self.service.get_authorization(auth_id)
        self.assertEqual(updated_auth["notification_status"], "SENT")

        # Verify outbox listing
        outbox = self.service.list_outbox()
        self.assertEqual(len(outbox), 1)
        self.assertEqual(outbox[0]["notification_id"], notif["notification_id"])


class TestHealthcareEndpoints(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = Path(self.temp_dir.name) / "endpoints_hc.sqlite"
        os.environ["AUTHORIZATION_STATE_DB"] = str(self.db_path)
        os.environ["HEALTHCARE_STATE_DB"] = str(self.db_path)
        self.app = create_app()
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()
        for k in ["AUTHORIZATION_STATE_DB", "HEALTHCARE_STATE_DB"]:
            if k in os.environ:
                del os.environ[k]

    def test_state_and_reset_endpoints(self):
        # Healthcare alias
        res = self.client.get("/healthcare/state")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["state_hash"].startswith("sha256:"))
        self.assertTrue(data["receipt_hash"].startswith("sha256:"))
        self.assertIn("state", data)

        res_reset = self.client.post("/healthcare/reset")
        self.assertEqual(res_reset.status_code, 200)
        self.assertEqual(res_reset.get_json()["status"], "reset")

        # Generic authorizations endpoint
        res_auth_state = self.client.get("/authorizations/state")
        self.assertEqual(res_auth_state.status_code, 200)
        self.assertTrue(res_auth_state.get_json()["state_hash"].startswith("sha256:"))

        res_reset = self.client.post("/healthcare/reset")
        self.assertEqual(res_reset.status_code, 200)
        self.assertEqual(res_reset.get_json()["status"], "reset")

    def test_review_and_authorization_endpoints(self):
        # 1. Post a human review
        rev_payload = {
            "patient_id": "PAT-002",
            "procedure_code": "CPT-33510",
            "reviewer_id": "MD-LIC-4491",
            "reviewer_type": "LICENSED_PHYSICIAN",
            "disposition": "DENY",
            "clinical_notes": "Criteria not met.",
        }
        rev_res = self.client.post("/healthcare/reviews", json=rev_payload)
        self.assertEqual(rev_res.status_code, 201)
        rev_data = rev_res.get_json()
        self.assertEqual(rev_data["status"], "recorded")

        # 2. Check 404 for non-existent authorization
        res_404 = self.client.get("/healthcare/authorizations/AUTH-NONEXISTENT")
        self.assertEqual(res_404.status_code, 404)

        # 3. Check outbox endpoint
        outbox_res = self.client.get("/healthcare/outbox")
        self.assertEqual(outbox_res.status_code, 200)
        self.assertIsInstance(outbox_res.get_json()["outbox"], list)

    def test_openapi_endpoint(self):
        res = self.client.get("/openapi.json")
        self.assertEqual(res.status_code, 200)
        spec = res.get_json()
        self.assertEqual(spec.get("openapi"), "3.1.0")
        paths = spec.get("paths", {})
        self.assertIn("/health", paths)
        self.assertIn("/execute_task", paths)
        self.assertIn("/healthcare/state", paths)
        self.assertIn("/healthcare/reset", paths)
        self.assertIn("/healthcare/authorizations/{authorization_id}", paths)
        self.assertIn("/healthcare/outbox", paths)

        # Verify no AgentV terms appear in the spec
        raw_spec = res.get_data(as_text=True)
        self.assertNotIn("AgentV", raw_spec)
        self.assertNotIn("agentv", raw_spec)


if __name__ == "__main__":
    unittest.main()
