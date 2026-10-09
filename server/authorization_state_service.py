"""Durable authorization and provider notification state service.

Maintains an isolated, durable SQLite ledger for domain authorization decisions,
licensed human review artifacts aligned to enacted and upcoming control requirements,
and provider notification outbox records.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import secrets
import smtplib
import sqlite3
import uuid
from datetime import UTC, datetime
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

from flask import Blueprint, jsonify, render_template_string, request

DEFAULT_DB_REL = Path(".agent_workspace") / "db" / "authorization_state.sqlite"


def canonical_json_bytes(value: object) -> bytes:
    """Deterministic JSON serialization for SHA-256 hashing."""
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


class AuthorizationStateService:
    """Durable state authority for authorizations, human reviews, and notification outbox."""

    def __init__(self, db_path: str | Path | None = None):
        if db_path is None:
            env_path = os.environ.get("AUTHORIZATION_STATE_DB") or os.environ.get(
                "HEALTHCARE_STATE_DB"
            )
            if env_path:
                self.db_path = Path(env_path).resolve()
            else:
                repo_root = Path(__file__).resolve().parent.parent
                self.db_path = (repo_root / DEFAULT_DB_REL).resolve()
        else:
            self.db_path = Path(db_path).resolve()

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    @contextlib.contextmanager
    def get_connection(self):
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init_db(self) -> None:
        with self.get_connection() as conn:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA busy_timeout = 30000")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS authorizations (
                    authorization_id TEXT PRIMARY KEY,
                    patient_id TEXT NOT NULL,
                    procedure_code TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    decision_source TEXT NOT NULL,
                    criteria_met INTEGER NOT NULL,
                    human_review_required INTEGER NOT NULL,
                    human_review_id TEXT,
                    committed_at TEXT NOT NULL,
                    notification_status TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS human_reviews (
                    review_id TEXT PRIMARY KEY,
                    patient_id TEXT NOT NULL,
                    procedure_code TEXT NOT NULL,
                    reviewer_id TEXT NOT NULL,
                    reviewer_type TEXT NOT NULL,
                    disposition TEXT NOT NULL,
                    clinical_notes TEXT,
                    reviewed_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS human_review_requests (
                    request_id TEXT PRIMARY KEY,
                    patient_id TEXT NOT NULL,
                    procedure_code TEXT NOT NULL,
                    reason TEXT,
                    status TEXT NOT NULL,
                    requested_at TEXT NOT NULL,
                    completed_at TEXT,
                    review_id TEXT UNIQUE,
                    approval_token_hash TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS notification_outbox (
                    notification_id TEXT PRIMARY KEY,
                    authorization_id TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    message TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    sent_at TEXT,
                    delivery_attempted INTEGER NOT NULL DEFAULT 0,
                    transport TEXT NOT NULL DEFAULT 'outbox',
                    delivery_receipt TEXT
                )
                """
            )
            conn.execute(
                """CREATE TABLE IF NOT EXISTS physician_review_workflows (
                    workflow_id TEXT PRIMARY KEY,
                    request_id TEXT UNIQUE NOT NULL,
                    task_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    resumed_at TEXT,
                    authorization_id TEXT,
                    notification_id TEXT
                    ,trajectory_json TEXT NOT NULL DEFAULT '[]'
                )"""
            )
            conn.execute(
                """CREATE TABLE IF NOT EXISTS review_notification_outbox (
                    notification_id TEXT PRIMARY KEY, request_id TEXT NOT NULL,
                    review_id TEXT, destination TEXT NOT NULL, message TEXT NOT NULL,
                    status TEXT NOT NULL, created_at TEXT NOT NULL)"""
            )
            # Existing demo ledgers predate delivery-evidence columns.  Keep the
            # schema upgrade local and idempotent so prior records remain readable.
            existing_columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(notification_outbox)")
            }
            migrations = {
                "delivery_attempted": "ALTER TABLE notification_outbox ADD COLUMN delivery_attempted INTEGER NOT NULL DEFAULT 0",
                "transport": "ALTER TABLE notification_outbox ADD COLUMN transport TEXT NOT NULL DEFAULT 'outbox'",
                "delivery_receipt": "ALTER TABLE notification_outbox ADD COLUMN delivery_receipt TEXT",
            }
            for column, statement in migrations.items():
                if column not in existing_columns:
                    conn.execute(statement)
            request_columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(human_review_requests)")
            }
            if "approval_token_hash" not in request_columns:
                conn.execute(
                    "ALTER TABLE human_review_requests ADD COLUMN approval_token_hash TEXT"
                )
            workflow_columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(physician_review_workflows)")
            }
            if "trajectory_json" not in workflow_columns:
                conn.execute(
                    "ALTER TABLE physician_review_workflows ADD COLUMN trajectory_json TEXT NOT NULL DEFAULT '[]'"
                )

    def reset_state(self) -> dict[str, Any]:
        with self.get_connection() as conn:
            conn.execute("DELETE FROM notification_outbox")
            conn.execute("DELETE FROM human_review_requests")
            conn.execute("DELETE FROM physician_review_workflows")
            conn.execute("DELETE FROM review_notification_outbox")
            conn.execute("DELETE FROM human_reviews")
            conn.execute("DELETE FROM authorizations")
        return self.snapshot()

    def create_physician_review_workflow(
        self, request_id: str, task: dict[str, Any], trajectory: list[Any] | None = None
    ) -> dict[str, Any]:
        """Persist the work blocked by an external review; duplicate pauses reuse it."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM physician_review_workflows WHERE request_id = ?",
                (request_id,),
            ).fetchone()
            if row:
                return dict(row)
            workflow_id = f"HREV-WF-{uuid.uuid4().hex[:8].upper()}"
            created_at = datetime.now(UTC).isoformat()
            conn.execute(
                """INSERT INTO physician_review_workflows
                   (workflow_id, request_id, task_json, status, created_at, trajectory_json)
                   VALUES (?, ?, ?, 'WAITING_FOR_REVIEW', ?, ?)""",
                (
                    workflow_id,
                    request_id,
                    json.dumps(task),
                    created_at,
                    json.dumps(trajectory or []),
                ),
            )
        return self.get_physician_review_workflow_by_request(request_id)  # type: ignore

    def append_workflow_step(
        self, request_id: str, tool: str, status: str = "completed"
    ) -> None:
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT trajectory_json FROM physician_review_workflows WHERE request_id = ?",
                (request_id,),
            ).fetchone()
            if not row:
                return
            steps = json.loads(row["trajectory_json"])
            steps.append(
                {
                    "tool": tool,
                    "status": status,
                    "recorded_at": datetime.now(UTC).isoformat(),
                }
            )
            conn.execute(
                "UPDATE physician_review_workflows SET trajectory_json = ? WHERE request_id = ?",
                (json.dumps(steps), request_id),
            )

    def get_physician_review_workflow_by_request(
        self, request_id: str
    ) -> dict[str, Any] | None:
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM physician_review_workflows WHERE request_id = ?",
                (request_id,),
            ).fetchone()
            return dict(row) if row else None

    def complete_physician_review_workflow(
        self, request_id: str, authorization_id: str | None, notification_id: str | None
    ) -> dict[str, Any]:
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM physician_review_workflows WHERE request_id = ?",
                (request_id,),
            ).fetchone()
            if not row:
                raise ValueError(
                    f"No pending workflow found for review request '{request_id}'."
                )
            workflow = dict(row)
            if workflow["status"] == "COMPLETED":
                return workflow
            conn.execute(
                """UPDATE physician_review_workflows SET status = 'COMPLETED', resumed_at = ?, authorization_id = ?, notification_id = ?
                   WHERE request_id = ? AND status = 'WAITING_FOR_REVIEW'""",
                (
                    datetime.now(UTC).isoformat(),
                    authorization_id,
                    notification_id,
                    request_id,
                ),
            )
        return self.get_physician_review_workflow_by_request(request_id)  # type: ignore

    def set_physician_review_workflow_status(
        self, request_id: str, status: str
    ) -> dict[str, Any]:
        """Record a terminal non-commit outcome, such as an approval blocked by policy."""
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE physician_review_workflows SET status = ?, resumed_at = ? WHERE request_id = ? AND status = 'WAITING_FOR_REVIEW'",
                (status, datetime.now(UTC).isoformat(), request_id),
            )
        return self.get_physician_review_workflow_by_request(request_id)  # type: ignore

    def record_review_notification(
        self,
        request_id: str,
        review_id: str | None,
        destination: str,
        message: str,
        status: str,
    ) -> dict[str, Any]:
        record = {
            "notification_id": f"REV-NOTIF-{uuid.uuid4().hex[:8].upper()}",
            "request_id": request_id,
            "review_id": review_id,
            "destination": destination,
            "message": message,
            "status": status,
            "created_at": datetime.now(UTC).isoformat(),
        }
        with self.get_connection() as conn:
            conn.execute(
                """INSERT INTO review_notification_outbox (notification_id, request_id, review_id, destination, message, status, created_at) VALUES (:notification_id, :request_id, :review_id, :destination, :message, :status, :created_at)""",
                record,
            )
        return record

    def create_human_review_request(
        self, patient_id: str, procedure_code: str, reason: str = ""
    ) -> dict[str, Any]:
        """Create one durable pending request per patient/procedure.

        Repeating a request is deliberately idempotent while it is pending; a new
        request may be created after a prior request has completed or been rejected.
        """
        procedure_code = procedure_code.upper()
        with self.get_connection() as conn:
            row = conn.execute(
                """SELECT * FROM human_review_requests
                   WHERE patient_id = ? AND procedure_code = ? AND status = 'PENDING'
                   ORDER BY requested_at DESC LIMIT 1""",
                (patient_id, procedure_code),
            ).fetchone()
            if row:
                return dict(row)
            request_id = f"HREV-REQ-{uuid.uuid4().hex[:8].upper()}"
            approval_token = secrets.token_urlsafe(32)
            requested_at = datetime.now(UTC).isoformat()
            conn.execute(
                """INSERT INTO human_review_requests
                   (request_id, patient_id, procedure_code, reason, status, requested_at, approval_token_hash)
                   VALUES (?, ?, ?, ?, 'PENDING', ?, ?)""",
                (
                    request_id,
                    patient_id,
                    procedure_code,
                    reason,
                    requested_at,
                    hashlib.sha256(approval_token.encode("utf-8")).hexdigest(),
                ),
            )
        created = self.get_human_review_request(request_id)  # type: ignore
        created["_approval_token"] = approval_token
        return created

    def get_human_review_request(self, request_id: str) -> dict[str, Any] | None:
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM human_review_requests WHERE request_id = ?",
                (request_id,),
            ).fetchone()
            return dict(row) if row else None

    def get_human_review_request_by_approval_token(
        self, approval_token: str
    ) -> dict[str, Any] | None:
        token_hash = hashlib.sha256(approval_token.encode("utf-8")).hexdigest()
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM human_review_requests WHERE approval_token_hash = ?",
                (token_hash,),
            ).fetchone()
            return dict(row) if row else None

    def get_pending_human_review(
        self, patient_id: str, procedure_code: str
    ) -> dict[str, Any] | None:
        with self.get_connection() as conn:
            row = conn.execute(
                """SELECT * FROM human_review_requests WHERE patient_id = ?
                   AND procedure_code = ? AND status = 'PENDING'
                   ORDER BY requested_at DESC LIMIT 1""",
                (patient_id, procedure_code.upper()),
            ).fetchone()
            return dict(row) if row else None

    def get_completed_human_review(
        self, patient_id: str, procedure_code: str
    ) -> dict[str, Any] | None:
        with self.get_connection() as conn:
            row = conn.execute(
                """SELECT * FROM human_review_requests WHERE patient_id = ?
                   AND procedure_code = ? AND status = 'COMPLETED'
                   ORDER BY completed_at DESC LIMIT 1""",
                (patient_id, procedure_code.upper()),
            ).fetchone()
            return dict(row) if row else None

    def complete_human_review_request(
        self, request_id: str, **review_data: Any
    ) -> dict[str, Any]:
        """Atomically bind a pending request to exactly one durable review."""
        with self.get_connection() as conn:
            request_row = conn.execute(
                "SELECT * FROM human_review_requests WHERE request_id = ?",
                (request_id,),
            ).fetchone()
            if not request_row:
                raise ValueError(f"Human review request '{request_id}' not found.")
            request_data = dict(request_row)
            if request_data["status"] == "COMPLETED":
                review = conn.execute(
                    "SELECT * FROM human_reviews WHERE review_id = ?",
                    (request_data["review_id"],),
                ).fetchone()
                return {
                    "request": request_data,
                    "review": dict(review) if review else None,
                    "idempotent": True,
                }
            if request_data["status"] != "PENDING":
                raise ValueError(
                    f"Human review request '{request_id}' is {request_data['status']}."
                )
            if (
                review_data["patient_id"] != request_data["patient_id"]
                or review_data["procedure_code"].upper()
                != request_data["procedure_code"]
            ):
                raise ValueError(
                    "Review patient and procedure must match the pending request."
                )
            if review_data["disposition"].upper().strip() in {
                "REJECT",
                "REJECTED",
                "SKIP_REVIEW",
            }:
                completed_at = datetime.now(UTC).isoformat()
                conn.execute(
                    "UPDATE human_review_requests SET status = 'REJECTED', completed_at = ? WHERE request_id = ?",
                    (completed_at, request_id),
                )
                request_data.update(status="REJECTED", completed_at=completed_at)
                return {"request": request_data, "review": None, "idempotent": False}
            review_id = (
                review_data.get("review_id") or f"REV-{uuid.uuid4().hex[:8].upper()}"
            )
            reviewed_at = datetime.now(UTC).isoformat()
            conn.execute(
                """INSERT INTO human_reviews
                   (review_id, patient_id, procedure_code, reviewer_id, reviewer_type, disposition, clinical_notes, reviewed_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    review_id,
                    request_data["patient_id"],
                    request_data["procedure_code"],
                    review_data["reviewer_id"],
                    review_data["reviewer_type"],
                    review_data["disposition"].upper().strip(),
                    review_data.get("clinical_notes", ""),
                    reviewed_at,
                ),
            )
            conn.execute(
                """UPDATE human_review_requests SET status = 'COMPLETED', completed_at = ?, review_id = ?
                   WHERE request_id = ? AND status = 'PENDING'""",
                (reviewed_at, review_id, request_id),
            )
        return {
            "request": self.get_human_review_request(request_id),
            "review": self.get_human_review_by_id(review_id),
            "idempotent": False,
        }

    def get_human_review_by_id(self, review_id: str) -> dict[str, Any] | None:
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM human_reviews WHERE review_id = ?", (review_id,)
            ).fetchone()
            return dict(row) if row else None

    def record_human_review(
        self,
        patient_id: str,
        procedure_code: str,
        reviewer_id: str,
        reviewer_type: str,
        disposition: str,
        clinical_notes: str = "",
        review_id: str | None = None,
    ) -> dict[str, Any]:
        """Record licensed clinical human review artifact."""
        if not review_id:
            review_id = f"REV-{uuid.uuid4().hex[:8].upper()}"
        reviewed_at = datetime.now(UTC).isoformat()
        disposition_clean = disposition.upper().strip()

        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO human_reviews
                (review_id, patient_id, procedure_code, reviewer_id, reviewer_type, disposition, clinical_notes, reviewed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    review_id,
                    patient_id,
                    procedure_code.upper(),
                    reviewer_id,
                    reviewer_type,
                    disposition_clean,
                    clinical_notes,
                    reviewed_at,
                ),
            )

        return {
            "review_id": review_id,
            "patient_id": patient_id,
            "procedure_code": procedure_code.upper(),
            "reviewer_id": reviewer_id,
            "reviewer_type": reviewer_type,
            "disposition": disposition_clean,
            "clinical_notes": clinical_notes,
            "reviewed_at": reviewed_at,
        }

    def get_latest_human_review(
        self, patient_id: str, procedure_code: str
    ) -> dict[str, Any] | None:
        with self.get_connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM human_reviews
                WHERE patient_id = ? AND procedure_code = ?
                ORDER BY reviewed_at DESC LIMIT 1
                """,
                (patient_id, procedure_code.upper()),
            ).fetchone()
            if row:
                return dict(row)
        return None

    def commit_authorization(
        self,
        patient_id: str,
        procedure_code: str,
        decision: str,
        criteria_met: bool,
        authorization_id: str | None = None,
        human_review_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Durable prior-authorization commit.
        Implements a control pattern aligned to enacted and upcoming requirements,
        including Washington ESSB 5395 and Iowa HF 2635:
        Adverse decisions (DENY, DELAY, DOWNGRADE) or cases where policy criteria
        are not met require licensed human review before committing.
        """
        clean_decision = decision.upper().strip()
        is_adverse = (
            clean_decision in ("DENY", "DELAY", "DOWNGRADE") or not criteria_met
        )

        if is_adverse:
            review = None
            if human_review_id:
                with self.get_connection() as conn:
                    row = conn.execute(
                        "SELECT * FROM human_reviews WHERE review_id = ?",
                        (human_review_id,),
                    ).fetchone()
                    if row:
                        review = dict(row)
            if not review:
                review = self.get_latest_human_review(patient_id, procedure_code)

            if not review:
                raise ValueError(
                    f"Adverse authorization decision '{clean_decision}' blocked: "
                    "licensed human review artifact required by the configured adverse-decision control."
                )
            if review["disposition"] != clean_decision:
                raise ValueError(
                    f"Adverse authorization decision '{clean_decision}' blocked: "
                    "review disposition does not authorize this decision."
                )

            human_review_required = True
            human_review_id = review["review_id"]
            decision_source = "HUMAN_REVIEWED"
        else:
            human_review_required = False
            human_review_id = None
            decision_source = "AI_ASSISTED"

        if not authorization_id:
            authorization_id = f"AUTH-{uuid.uuid4().hex[:8].upper()}"

        committed_at = datetime.now(UTC).isoformat()
        notification_status = "PENDING"

        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO authorizations
                (authorization_id, patient_id, procedure_code, decision, decision_source,
                 criteria_met, human_review_required, human_review_id, committed_at, notification_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    authorization_id,
                    patient_id,
                    procedure_code.upper(),
                    clean_decision,
                    decision_source,
                    1 if criteria_met else 0,
                    1 if human_review_required else 0,
                    human_review_id,
                    committed_at,
                    notification_status,
                ),
            )

        return self.get_authorization(authorization_id)  # type: ignore

    def get_authorization(self, authorization_id: str) -> dict[str, Any] | None:
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM authorizations WHERE authorization_id = ?",
                (authorization_id,),
            ).fetchone()
            if row:
                data = dict(row)
                data["criteria_met"] = bool(data["criteria_met"])
                data["human_review_required"] = bool(data["human_review_required"])
                return data
        return None

    def list_authorizations(self) -> list[dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM authorizations ORDER BY committed_at ASC"
            ).fetchall()
            results = []
            for r in rows:
                item = dict(r)
                item["criteria_met"] = bool(item["criteria_met"])
                item["human_review_required"] = bool(item["human_review_required"])
                results.append(item)
            return results

    def send_provider_notification(
        self,
        authorization_id: str,
        channel: str = "outbox",
        destination: str = "provider@clinic.example",
        message: str = "",
    ) -> dict[str, Any]:
        """Record a notification and dispatch email only when SMTP is configured."""
        auth = self.get_authorization(authorization_id)
        if not auth:
            raise ValueError(
                f"Authorization {authorization_id} not found in durable ledger."
            )

        notification_id = f"NOTIF-{uuid.uuid4().hex[:8].upper()}"
        created_at = datetime.now(UTC).isoformat()
        normalized_channel = channel.lower()
        status = "SENT"
        sent_at: str | None = created_at
        delivery_attempted = True
        transport = "outbox"
        delivery_receipt: str | None = "recorded_in_durable_outbox"

        # Email is an explicit delivery request: it must never be represented as
        # successful merely because a durable outbox row was written.
        smtp_host = os.environ.get("SMTP_HOST")
        if normalized_channel == "email":
            transport = "smtp"
            sent_at = None
            delivery_receipt = None
            if not smtp_host:
                status = "NOT_CONFIGURED"
                delivery_attempted = False
            else:
                delivery_attempted = True
                try:
                    smtp_port = int(os.environ.get("SMTP_PORT", "25"))
                    smtp_user = os.environ.get("SMTP_USER")
                    smtp_pass = os.environ.get("SMTP_PASS")
                    msg = MIMEText(message)
                    msg["Subject"] = f"Prior Authorization Update: {authorization_id}"
                    msg["From"] = os.environ.get(
                        "SMTP_FROM", "notifications@um-portal.org"
                    )
                    msg["To"] = destination

                    with smtplib.SMTP(smtp_host, smtp_port, timeout=5) as server:
                        if smtp_user and smtp_pass:
                            server.starttls()
                            server.login(smtp_user, smtp_pass)
                        server.send_message(msg)
                    status = "SENT"
                    sent_at = datetime.now(UTC).isoformat()
                    delivery_receipt = "accepted_by_smtp"
                except Exception:
                    status = "FAILED"

        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO notification_outbox
                (notification_id, authorization_id, channel, destination, message, status, created_at, sent_at,
                 delivery_attempted, transport, delivery_receipt)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    notification_id,
                    authorization_id,
                    channel,
                    destination,
                    message,
                    status,
                    created_at,
                    sent_at,
                    1 if delivery_attempted else 0,
                    transport,
                    delivery_receipt,
                ),
            )
            conn.execute(
                "UPDATE authorizations SET notification_status = ? WHERE authorization_id = ?",
                (status, authorization_id),
            )

        return {
            "notification_id": notification_id,
            "authorization_id": authorization_id,
            "channel": channel,
            "destination": destination,
            "message": message,
            "status": status,
            "created_at": created_at,
            "sent_at": sent_at,
            "delivery_attempted": delivery_attempted,
            "transport": transport,
            "delivery_receipt": delivery_receipt,
        }

    def list_outbox(self) -> list[dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM notification_outbox ORDER BY created_at ASC"
            ).fetchall()
            reviews = conn.execute(
                "SELECT * FROM review_notification_outbox ORDER BY created_at ASC"
            ).fetchall()
            return [dict(r) for r in rows] + [dict(r) for r in reviews]

    def list_human_reviews(self) -> list[dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM human_reviews ORDER BY reviewed_at ASC"
            ).fetchall()
            return [dict(r) for r in rows]

    def list_human_review_requests(self) -> list[dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM human_review_requests ORDER BY requested_at ASC"
            ).fetchall()
            return [dict(r) for r in rows]

    def snapshot(self) -> dict[str, Any]:
        state = {
            "authorizations": self.list_authorizations(),
            "human_reviews": self.list_human_reviews(),
            "human_review_requests": self.list_human_review_requests(),
            "outbox": self.list_outbox(),
        }
        state_hash = "sha256:" + hashlib.sha256(canonical_json_bytes(state)).hexdigest()
        return {
            "state": state,
            "state_hash": state_hash,
        }


# Generic alias
HealthcareStateService = AuthorizationStateService


def create_authorization_state_blueprint(
    service: AuthorizationStateService | None = None,
    url_prefix: str = "/authorizations",
    name: str = "authorization_state",
) -> Blueprint:
    if service is None:
        service = AuthorizationStateService()

    bp = Blueprint(name, __name__, url_prefix=url_prefix)

    @bp.post("/reset")
    def reset():
        snapshot = service.reset_state()
        return jsonify({"status": "reset", "snapshot": snapshot}), 200

    @bp.get("/state")
    def get_state():
        observed_at = datetime.now(UTC).isoformat()
        snap = service.snapshot()
        receipt_data = {"observed_at": observed_at, **snap}
        receipt_hash = (
            "sha256:" + hashlib.sha256(canonical_json_bytes(receipt_data)).hexdigest()
        )
        receipt_data["receipt_hash"] = receipt_hash
        return jsonify(receipt_data), 200

    @bp.get("/authorizations/<authorization_id>")
    @bp.get("/<authorization_id>")
    def get_authorization(authorization_id: str):
        record = service.get_authorization(authorization_id)
        if not record:
            return jsonify(
                {"error": f"Authorization '{authorization_id}' not found"}
            ), 404
        return jsonify(record), 200

    @bp.get("/authorizations")
    @bp.get("")
    def list_authorizations():
        return jsonify({"authorizations": service.list_authorizations()}), 200

    @bp.get("/outbox")
    def list_outbox():
        return jsonify({"outbox": service.list_outbox()}), 200

    @bp.get("/reviews/<request_id>")
    def get_review_status(request_id: str):
        review_request = service.get_human_review_request(request_id)
        if not review_request:
            return jsonify(
                {"error": f"Human review request '{request_id}' not found"}
            ), 404
        result: dict[str, Any] = {
            "request_id": request_id,
            "status": review_request["status"],
            "patient_id": review_request["patient_id"],
            "procedure_code": review_request["procedure_code"],
            "reason": review_request["reason"],
        }
        if review_request["status"] == "COMPLETED" and review_request["review_id"]:
            result["review"] = service.get_human_review_by_id(
                review_request["review_id"]
            )
        return jsonify(result), 200

    @bp.route("/physician-review/<approval_token>", methods=["GET", "POST"])
    def physician_review_form(approval_token: str):
        """Minimal same-origin approval page for the physician's opaque link."""
        review_request = service.get_human_review_request_by_approval_token(
            approval_token
        )
        if not review_request:
            return render_template_string("<h1>Review link is invalid.</h1>"), 404
        if request.method == "POST":
            reviewer_id = request.form.get("reviewer_id", "").strip()
            reviewer_type = request.form.get("reviewer_type", "").strip()
            disposition = request.form.get("disposition", "").strip().upper()
            clinical_notes = request.form.get("clinical_notes", "").strip()
            if not all([reviewer_id, reviewer_type, disposition]):
                return render_template_string(
                    "<h1>Reviewer identity and disposition are required.</h1>"
                ), 400
            try:
                service.complete_human_review_request(
                    review_request["request_id"],
                    patient_id=review_request["patient_id"],
                    procedure_code=review_request["procedure_code"],
                    reviewer_id=reviewer_id,
                    reviewer_type=reviewer_type,
                    disposition=disposition,
                    clinical_notes=clinical_notes,
                )
            except ValueError as exc:
                return render_template_string(
                    "<h1>Review could not be submitted.</h1><p>{{ error }}</p>",
                    error=str(exc),
                ), 409
            return render_template_string(
                "<h1>Review submitted</h1><p>The authorization workflow may now continue.</p>"
            )
        if review_request["status"] != "PENDING":
            return render_template_string(
                "<h1>This review is already {{ status }}.</h1>",
                status=review_request["status"],
            ), 409
        return render_template_string(
            """<!doctype html><title>Physician Review</title>
            <h1>Physician Review</h1><p>Request {{ request_id }}</p>
            <form method="post" action="/healthcare/physician-review/{{ approval_token }}/resume"><label>Reviewer ID <input name="reviewer_id" required></label><br>
            <label>Reviewer type <input name="reviewer_type" value="LICENSED_PHYSICIAN" required></label><br>
            <label>Disposition <select name="disposition"><option value="DENY">Deny</option><option value="APPROVE">Approve</option><option value="SKIP_REVIEW">Skip review</option></select></label><br>
            <label>Clinical rationale<br><textarea name="clinical_notes" required rows="5" cols="60"></textarea></label><br>
            <button type="submit">Submit review</button></form>""",
            request_id=review_request["request_id"],
            approval_token=approval_token,
        )

    @bp.post("/reviews")
    def record_review():
        payload = request.get_json(force=True) or {}
        required = [
            "patient_id",
            "procedure_code",
            "reviewer_id",
            "reviewer_type",
            "disposition",
        ]
        missing = [f for f in required if f not in payload]
        if missing:
            return jsonify(
                {"error": f"Missing required fields: {', '.join(missing)}"}
            ), 400

        if payload.get("request_id"):
            try:
                completed = service.complete_human_review_request(
                    payload["request_id"], **payload
                )
            except ValueError as exc:
                return jsonify({"error": str(exc)}), 409
            return jsonify({"status": "recorded", **completed}), 200 if completed[
                "idempotent"
            ] else 201
        review = service.record_human_review(
            patient_id=payload["patient_id"],
            procedure_code=payload["procedure_code"],
            reviewer_id=payload["reviewer_id"],
            reviewer_type=payload["reviewer_type"],
            disposition=payload["disposition"],
            clinical_notes=payload.get("clinical_notes", ""),
            review_id=payload.get("review_id"),
        )
        return jsonify({"status": "recorded", "review": review}), 201

    return bp


def create_healthcare_state_blueprint(
    service: AuthorizationStateService | None = None,
) -> Blueprint:
    """Convenience factory providing the /healthcare prefix."""
    return create_authorization_state_blueprint(
        service=service, url_prefix="/healthcare", name="healthcare_state"
    )
