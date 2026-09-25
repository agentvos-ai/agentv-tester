"""Independent acceptance-state authority for integration test fixtures.

This service owns an isolated SQLite ledger distinct from test runner run artifacts.
Test fixtures query it before and after a run and receive a SHA-256-bound observation
receipt. It deliberately has no dependency on external harness trace/manifest code.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from flask import Blueprint, jsonify, request


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def create_acceptance_state_oracle(database: str | Path) -> Blueprint:
    db_path = Path(database).resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    oracle = Blueprint(
        "acceptance_state_oracle", __name__, url_prefix="/acceptance-oracle"
    )

    @contextlib.contextmanager
    def connect():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute(
            "CREATE TABLE IF NOT EXISTS balances (account TEXT PRIMARY KEY, balance INTEGER NOT NULL)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS transfers (id TEXT PRIMARY KEY, source TEXT, target TEXT, amount INTEGER, committed_at TEXT)"
        )
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    @oracle.post("/reset")
    def reset():
        payload = request.get_json(force=True) or {}
        balances = payload.get("balances", {})
        if not isinstance(balances, dict):
            return jsonify({"error": "balances must be an object"}), 400
        with connect() as conn:
            conn.execute("DELETE FROM transfers")
            conn.execute("DELETE FROM balances")
            conn.executemany(
                "INSERT INTO balances(account, balance) VALUES (?, ?)", balances.items()
            )
        return jsonify({"status": "reset", "snapshot": snapshot()})

    def snapshot() -> dict[str, object]:
        with connect() as conn:
            balances = {
                row["account"]: row["balance"]
                for row in conn.execute(
                    "SELECT account, balance FROM balances ORDER BY account"
                )
            }
            transfers = [
                dict(row) for row in conn.execute("SELECT * FROM transfers ORDER BY id")
            ]
        state = {"balances": balances, "transfers": transfers}
        return {
            "state": state,
            "state_hash": "sha256:" + hashlib.sha256(_canonical(state)).hexdigest(),
        }

    @oracle.get("/state")
    def state():
        observation = {"observed_at": datetime.now(UTC).isoformat(), **snapshot()}
        observation["receipt_hash"] = (
            "sha256:" + hashlib.sha256(_canonical(observation)).hexdigest()
        )
        return jsonify(observation)

    @oracle.post("/transfers")
    def transfer():
        payload = request.get_json(force=True) or {}
        try:
            transfer_id, source, target, amount = (
                payload["id"],
                payload["source"],
                payload["target"],
                int(payload["amount"]),
            )
        except (KeyError, TypeError, ValueError):
            return jsonify({"error": "id, source, target, amount required"}), 400
        with connect() as conn:
            if conn.execute(
                "SELECT 1 FROM transfers WHERE id = ?", (transfer_id,)
            ).fetchone():
                return jsonify({"error": "duplicate transfer"}), 409
            row = conn.execute(
                "SELECT balance FROM balances WHERE account = ?", (source,)
            ).fetchone()
            if row is None or row["balance"] < amount:
                return jsonify({"error": "insufficient funds"}), 409
            conn.execute(
                "UPDATE balances SET balance = balance - ? WHERE account = ?",
                (amount, source),
            )
            conn.execute(
                "UPDATE balances SET balance = balance + ? WHERE account = ?",
                (amount, target),
            )
            conn.execute(
                "INSERT INTO transfers VALUES (?, ?, ?, ?, ?)",
                (transfer_id, source, target, amount, datetime.now(UTC).isoformat()),
            )
        return jsonify({"status": "committed", **snapshot()}), 201

    return oracle
