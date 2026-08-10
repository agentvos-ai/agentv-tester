import logging
import os
import sqlite3
from typing import Any

from core.errors import ShimError
from core.registry import register_shim
from shims import BaseShim

logger = logging.getLogger(__name__)


@register_shim("payment")
class PaymentShim(BaseShim):
    """
    Industrial-grade Payment interface.
    Uses a local SQLite database for double-entry ledger persistence.
    """

    def __init__(self, seed: int = 42):
        self.db_path = os.path.abspath(".agent_workspace/db/payments.db")
        super().__init__(seed)

    @property
    def name(self) -> str:
        return "payment"

    @property
    def description(self) -> str:
        return "Enterprise payment gateway for managing transactions and ledgers."

    def setup(self) -> None:
        """Ensure database and tables exist."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id TEXT PRIMARY KEY,
                    balance REAL DEFAULT 0.0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ledger (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_account TEXT,
                    to_account TEXT,
                    amount REAL,
                    description TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(from_account) REFERENCES accounts(id),
                    FOREIGN KEY(to_account) REFERENCES accounts(id)
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
        """Deterministic reset of the payment state."""
        self.shutdown()
        self.setup()

        # Seed default accounts
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "INSERT INTO accounts (id, balance) VALUES ('SYSTEM', 1000000.0)"
            )
            conn.execute(
                "INSERT INTO accounts (id, balance) VALUES ('CUSTOMER-001', 500.0)"
            )
            conn.commit()
        finally:
            conn.close()

    def process_payment(
        self, from_account: str, to_account: str, amount: float, description: str = ""
    ) -> str:
        """Processes a payment between two accounts using double-entry logic."""
        if amount <= 0:
            raise ShimError("Payment amount must be positive.")

        conn = sqlite3.connect(self.db_path)
        try:
            # Verify accounts and balance
            res = conn.execute(
                "SELECT balance FROM accounts WHERE id = ?", (from_account,)
            ).fetchone()
            if not res:
                raise ShimError(f"Source account '{from_account}' not found.")
            if res[0] < amount:
                raise ShimError(f"Insufficient funds in account '{from_account}'.")

            if not conn.execute(
                "SELECT id FROM accounts WHERE id = ?", (to_account,)
            ).fetchone():
                raise ShimError(f"Destination account '{to_account}' not found.")

            # Perform transaction
            conn.execute(
                "UPDATE accounts SET balance = balance - ? WHERE id = ?",
                (amount, from_account),
            )
            conn.execute(
                "UPDATE accounts SET balance = balance + ? WHERE id = ?",
                (amount, to_account),
            )
            conn.execute(
                "INSERT INTO ledger (from_account, to_account, amount, description) VALUES (?, ?, ?, ?)",
                (from_account, to_account, amount, description),
            )
            conn.commit()
            return f"Payment of ${amount:.2f} from '{from_account}' to '{to_account}' successful."
        except Exception as e:
            if isinstance(e, ShimError):
                raise
            raise ShimError(f"Failed to process payment: {e!s}")
        finally:
            conn.close()

    def charge(self, amount: float, currency: str, description: str) -> str:
        """Alias for process_payment (Charging customer)."""
        return self.process_payment(
            "CUSTOMER-001", "SYSTEM", amount, f"[{currency}] {description}"
        )

    def get_balance(self, account_id: str) -> float:
        """Returns the current balance of an account."""
        conn = sqlite3.connect(self.db_path)
        try:
            res = conn.execute(
                "SELECT balance FROM accounts WHERE id = ?", (account_id,)
            ).fetchone()
            if not res:
                raise ShimError(f"Account '{account_id}' not found.")
            return res[0]
        finally:
            conn.close()

    def list_transactions(self, account_id: str) -> list[dict[str, Any]]:
        """Lists all transactions involving a specific account."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT id, from_account, to_account, amount, description, timestamp FROM ledger WHERE from_account = ? OR to_account = ? ORDER BY timestamp DESC",
                (account_id, account_id),
            )
            return [
                {
                    "id": str(row[0]),
                    "from": row[1],
                    "to": row[2],
                    "amount": row[3],
                    "description": row[4],
                    "timestamp": row[5],
                }
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()

    def get_tool_specs(self) -> list[tuple[str, Any, str]]:
        return [
            (
                "pay_process",
                self.process_payment,
                "Process a payment between two accounts.",
            ),
            ("pay_charge", self.charge, "Charge a customer account."),
            ("pay_balance", self.get_balance, "Get the current balance of an account."),
            (
                "pay_history",
                self.list_transactions,
                "List transaction history for an account.",
            ),
        ]
