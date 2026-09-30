"""Neutral, durable finance state authority for synthetic tester operations."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import sqlite3
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from flask import Blueprint, jsonify

DEFAULT_DB_REL = Path(".agent_workspace") / "db" / "finance_state.sqlite"


def canonical_json_bytes(value: object) -> bytes:
    """Deterministic JSON serialization for independently verifiable state."""
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


class FinanceStateService:
    """Owns synthetic accounts and wire-transfer records independently of agents."""

    def __init__(self, db_path: str | Path | None = None):
        repo_root = Path(__file__).resolve().parent.parent
        self.fixture_path = repo_root / "fixtures" / "synthetic_accounts.json"
        self.db_path = Path(
            db_path or os.environ.get("FINANCE_STATE_DB") or repo_root / DEFAULT_DB_REL
        ).resolve()
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

    def fixture_data(self) -> dict[str, Any]:
        with self.fixture_path.open(encoding="utf-8") as fixture:
            return json.load(fixture)

    def init_db(self) -> None:
        with self.get_connection() as conn:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute(
                "CREATE TABLE IF NOT EXISTS finance_state (id INTEGER PRIMARY KEY CHECK (id = 1), data TEXT NOT NULL, transfers TEXT NOT NULL)"
            )
            if not conn.execute("SELECT 1 FROM finance_state WHERE id = 1").fetchone():
                baseline = self.fixture_data()
                conn.execute(
                    "INSERT INTO finance_state (id, data, transfers) VALUES (1, ?, ?)",
                    (json.dumps(baseline, sort_keys=True), "[]"),
                )

    def _read(
        self, conn: sqlite3.Connection
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        row = conn.execute(
            "SELECT data, transfers FROM finance_state WHERE id = 1"
        ).fetchone()
        assert row is not None
        return json.loads(row["data"]), json.loads(row["transfers"])

    def _write(
        self,
        conn: sqlite3.Connection,
        data: dict[str, Any],
        transfers: list[dict[str, Any]],
    ) -> None:
        conn.execute(
            "UPDATE finance_state SET data = ?, transfers = ? WHERE id = 1",
            (json.dumps(data, sort_keys=True), json.dumps(transfers, sort_keys=True)),
        )

    def data(self) -> dict[str, Any]:
        with self.get_connection() as conn:
            data, _ = self._read(conn)
            return data

    def save_data(self, data: dict[str, Any]) -> None:
        with self.get_connection() as conn:
            _, transfers = self._read(conn)
            self._write(conn, data, transfers)

    def initiate_wire_transfer(
        self,
        account_id: str,
        payee_account: str,
        amount: float,
        currency: str,
        memo: str,
        transfer_id: str,
    ) -> dict[str, Any]:
        with self.get_connection() as conn:
            data, transfers = self._read(conn)
            account = data["accounts"].get(account_id)
            if not account:
                return {
                    "status": "failed",
                    "error": f"Source account {account_id} not found",
                }
            if account["balance"] < amount:
                return {"status": "failed", "error": "Insufficient funds"}
            if amount > account["daily_limit"] - account["daily_spent"]:
                return {"status": "failed", "error": "Daily transaction limit exceeded"}

            account["balance"] -= amount
            account["daily_spent"] += amount
            transfer = {
                "transfer_id": transfer_id,
                "source_account": account_id,
                "payee_account": payee_account,
                "amount": amount,
                "currency": currency,
                "memo": memo,
                "committed_at": datetime.now(UTC).isoformat(),
            }
            transfers.append(transfer)
            self._write(conn, data, transfers)
        return {"transfer_id": transfer_id, "status": "completed"}

    def reset_state(self) -> dict[str, Any]:
        with self.get_connection() as conn:
            self._write(conn, self.fixture_data(), [])
        return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        with self.get_connection() as conn:
            data, transfers = self._read(conn)
        state = {"accounts": deepcopy(data["accounts"]), "transfers": transfers}
        return {
            "state": state,
            "state_hash": "sha256:"
            + hashlib.sha256(canonical_json_bytes(state)).hexdigest(),
        }


def create_finance_state_blueprint(
    service: FinanceStateService | None = None,
) -> Blueprint:
    service = service or FinanceStateService()
    bp = Blueprint("finance_state", __name__, url_prefix="/finance")

    @bp.post("/reset")
    def reset():
        return jsonify({"status": "reset", "snapshot": service.reset_state()}), 200

    @bp.get("/state")
    def state():
        observed_at = datetime.now(UTC).isoformat()
        snapshot = service.snapshot()
        receipt = {"observed_at": observed_at, **snapshot}
        receipt["receipt_hash"] = (
            "sha256:" + hashlib.sha256(canonical_json_bytes(receipt)).hexdigest()
        )
        return jsonify(receipt), 200

    return bp
