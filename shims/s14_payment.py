import logging

logger = logging.getLogger(__name__)

from typing import List, Dict, Any, Tuple
from core.registry import register_shim
from core.errors import ShimError
from shims import BaseShim


@register_shim("payment")
class PaymentShim(BaseShim):
    """
    Secure payment gateway simulator.
    Supports transactions, refunds, and subscriptions.
    """

    @property
    def name(self) -> str:
        return "payment"

    @property
    def description(self) -> str:
        return "Secure gateway for processing financial transactions and subscriptions."

    def reset(self) -> None:
        """Deterministic reset of the payment state."""
        self._state["ledger"]: List[Dict[str, Any]] = []
        self._state["subscriptions"]: List[Dict[str, Any]] = []

    def charge(self, amount: float, currency: str, description: str) -> Dict[str, Any]:
        """Processes a payment charge."""
        tx_id = f"tx_{len(self._state['ledger']) + 1001}"
        record = {
            "id": tx_id,
            "amount": amount,
            "currency": currency,
            "desc": description,
            "status": "APPROVED",
        }
        self._state["ledger"].append(record)
        return record

    def refund(self, tx_id: str) -> str:
        """Processes a refund for a transaction."""
        for tx in self._state["ledger"]:
            if tx["id"] == tx_id:
                tx["status"] = "REFUNDED"
                return f"Transaction '{tx_id}' refunded."
        raise ShimError(f"Transaction '{tx_id}' not found.")

    def create_subscription(self, plan_id: str, customer_id: str) -> str:
        """Creates a recurring subscription."""
        sid = f"sub_{len(self._state['subscriptions']) + 101}"
        self._state["subscriptions"].append(
            {"id": sid, "plan": plan_id, "customer": customer_id, "status": "ACTIVE"}
        )
        return sid

    def get_ledger(self) -> List[Dict[str, Any]]:
        """Retrieves the transaction history."""
        return self._state["ledger"]

    def get_tool_specs(self) -> List[Tuple[str, Any, str]]:
        return [
            ("payment_charge", self.charge, "Process a one-time payment charge."),
            ("payment_refund", self.refund, "Refund a previous transaction."),
            (
                "payment_subscribe",
                self.create_subscription,
                "Set up a recurring subscription.",
            ),
            (
                "payment_ledger",
                self.get_ledger,
                "View the organization's transaction ledger.",
            ),
        ]
