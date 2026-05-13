import logging
import os
import sqlite3
from typing import List, Dict, Any, Tuple
from core.registry import register_shim
from shims import BaseShim

logger = logging.getLogger(__name__)


@register_shim("compliance")
class ComplianceShim(BaseShim):
    """
    Industrial-grade Compliance interface.
    Uses a local SQLite database for an immutable audit trail.
    """

    def __init__(self, seed: int = 42):
        self.db_path = os.path.abspath(".agent_workspace/db/compliance.db")
        super().__init__(seed)

    @property
    def name(self) -> str:
        return "compliance"

    @property
    def description(self) -> str:
        return "Enterprise compliance service for policy validation and audit logging."

    def setup(self) -> None:
        """Ensure database and tables exist."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_trail (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    resource_id TEXT,
                    check_type TEXT,
                    status TEXT,
                    details TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS policies (
                    id TEXT PRIMARY KEY,
                    description TEXT,
                    is_active INTEGER DEFAULT 1
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def shutdown(self) -> None:
        """Cleanup the database file."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def reset(self) -> None:
        """Deterministic reset of the compliance state."""
        self.shutdown()
        self.setup()

        # Seed default policies
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "INSERT INTO policies (id, description) VALUES ('AML-V1', 'Anti-Money Laundering base policy.')"
            )
            conn.execute(
                "INSERT INTO policies (id, description) VALUES ('GDPR-CORE', 'Data privacy core rules.')"
            )
            conn.commit()
        finally:
            conn.close()

    def perform_check(
        self, resource_id: str, check_type: str, data: Dict[str, Any]
    ) -> str:
        """Performs a compliance check and logs it to the immutable audit trail."""
        # Simple rule: if 'amount' exists and > 10000, mark as 'WARNING'
        status = "PASSED"
        details = "Rule validation successful."

        if data.get("amount", 0) > 10000:
            status = "WARNING"
            details = "High-value transaction detected. Manual SAR required."

        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "INSERT INTO audit_trail (resource_id, check_type, status, details) VALUES (?, ?, ?, ?)",
                (resource_id, check_type, status, details),
            )
            conn.commit()
            return f"Check '{check_type}' for '{resource_id}' completed with status: {status}."
        finally:
            conn.close()

    def check_policy(self, resource_id: str, data: Dict[str, Any]) -> str:
        """Alias for perform_check (Policy validation)."""
        return self.perform_check(resource_id, "POLICY_VAL", data)

    def file_report(self, report_type: str, details: Dict[str, Any]) -> str:
        """Files a compliance report."""
        import json

        return self.perform_check(
            "SYSTEM",
            report_type,
            {"data": json.dumps(details), "action": "REPORT_FILED"},
        )

    def flag_violation(self, resource_id: str, reason: str) -> str:
        """Flags a compliance violation."""
        return self.perform_check(
            resource_id, "VIOLATION", {"reason": reason, "amount": 99999}
        )

    def get_audit_trail(self, resource_id: str = None) -> List[Dict[str, Any]]:
        """Retrieves the audit trail, optionally filtered by resource."""
        conn = sqlite3.connect(self.db_path)
        try:
            query = "SELECT resource_id, check_type, status, details, timestamp FROM audit_trail"
            params = []
            if resource_id:
                query += " WHERE resource_id = ?"
                params.append(resource_id)

            query += " ORDER BY timestamp DESC"
            cursor = conn.execute(query, params)
            return [
                {
                    "resource": row[0],
                    "type": row[1],
                    "status": row[2],
                    "details": row[3],
                    "timestamp": row[4],
                }
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()

    def get_tool_specs(self) -> List[Tuple[str, Any, str]]:
        return [
            (
                "comp_check",
                self.perform_check,
                "Perform a compliance check on a resource.",
            ),
            (
                "comp_policy",
                self.check_policy,
                "Validate a resource against enterprise policy.",
            ),
            (
                "comp_report",
                self.file_report,
                "File a formal compliance report (e.g. SAR).",
            ),
            (
                "comp_violation",
                self.flag_violation,
                "Flag a resource as a compliance violation.",
            ),
            (
                "comp_audit",
                self.get_audit_trail,
                "Retrieve the compliance audit trail.",
            ),
        ]
