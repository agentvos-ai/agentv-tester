"""Durable authorization and provider notification state service.

Maintains an isolated, durable SQLite ledger for domain authorization decisions,
licensed human review artifacts (enforcing regulatory mandates such as WA ESSB 5395 and IA HF 2635),
and provider notification outbox records.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import smtplib
import sqlite3
import uuid
from datetime import UTC, datetime
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

from flask import Blueprint, jsonify, request

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
                CREATE TABLE IF NOT EXISTS notification_outbox (
                    notification_id TEXT PRIMARY KEY,
                    authorization_id TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    message TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    sent_at TEXT
                )
                """
            )

    def reset_state(self) -> dict[str, Any]:
        with self.get_connection() as conn:
            conn.execute("DELETE FROM notification_outbox")
            conn.execute("DELETE FROM human_reviews")
            conn.execute("DELETE FROM authorizations")
        return self.snapshot()

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
        Enforces Washington ESSB 5395 and Iowa HF 2635:
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
                    "licensed human review artifact required under WA ESSB 5395 and IA HF 2635."
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
        """Record notification in durable outbox and optionally dispatch via SMTP."""
        auth = self.get_authorization(authorization_id)
        if not auth:
            raise ValueError(
                f"Authorization {authorization_id} not found in durable ledger."
            )

        notification_id = f"NOTIF-{uuid.uuid4().hex[:8].upper()}"
        created_at = datetime.now(UTC).isoformat()
        status = "SENT"
        sent_at = created_at

        # Optional SMTP dispatch if explicitly configured in environment
        smtp_host = os.environ.get("SMTP_HOST")
        if smtp_host and channel.lower() == "email":
            try:
                smtp_port = int(os.environ.get("SMTP_PORT", "25"))
                smtp_user = os.environ.get("SMTP_USER")
                smtp_pass = os.environ.get("SMTP_PASS")
                msg = MIMEText(message)
                msg["Subject"] = f"Prior Authorization Update: {authorization_id}"
                msg["From"] = os.environ.get("SMTP_FROM", "notifications@um-portal.org")
                msg["To"] = destination

                with smtplib.SMTP(smtp_host, smtp_port, timeout=5) as server:
                    if smtp_user and smtp_pass:
                        server.starttls()
                        server.login(smtp_user, smtp_pass)
                    server.send_message(msg)
                status = "SENT"
            except Exception:
                status = "FAILED"

        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO notification_outbox
                (notification_id, authorization_id, channel, destination, message, status, created_at, sent_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
        }

    def list_outbox(self) -> list[dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM notification_outbox ORDER BY created_at ASC"
            ).fetchall()
            return [dict(r) for r in rows]

    def list_human_reviews(self) -> list[dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM human_reviews ORDER BY reviewed_at ASC"
            ).fetchall()
            return [dict(r) for r in rows]

    def snapshot(self) -> dict[str, Any]:
        state = {
            "authorizations": self.list_authorizations(),
            "human_reviews": self.list_human_reviews(),
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
