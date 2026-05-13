import logging
import re
from typing import List, Dict, Any, Tuple, Optional, Callable
from core.registry import register_shim
from shims import BaseShim

logger = logging.getLogger(__name__)


@register_shim("rest_api")
class RestApiShim(BaseShim):
    """
    Industrial-grade internal REST API simulator.
    Uses regex-based routing to support path parameters and dynamic responses.
    """

    def __init__(self, seed: int = 42):
        super().__init__(seed)
        self._routes: List[Tuple[str, str, Callable]] = []

    @property
    def name(self) -> str:
        return "rest_api"

    @property
    def description(self) -> str:
        return "Interface for interacting with internal and external RESTful services."

    def reset(self) -> None:
        """Deterministic reset of the API state and routes."""
        self._state["data"] = {
            "accounts": [{"id": "acc_1", "balance": 1000.0}],
            "transactions": [],
        }
        self._setup_default_routes()

    def _setup_default_routes(self) -> None:
        """Configures the regex-based routing table."""
        self._routes = [
            (
                "GET",
                r"^/v1/credit_score$",
                lambda p, b: {"status": 200, "body": {"score": 750}},
            ),
            (
                "GET",
                r"^/v1/accounts$",
                lambda p, b: {"status": 200, "body": self._state["data"]["accounts"]},
            ),
            ("POST", r"^/v1/transactions$", self._handle_post_transaction),
            (
                "GET",
                r"^/v1/transactions/(?P<tx_id>[^/]+)$",
                self._handle_get_transaction,
            ),
            (
                "PUT",
                r"^/v1/transactions/(?P<tx_id>[^/]+)$",
                self._handle_put_transaction,
            ),
            (
                "PATCH",
                r"^/v1/transactions/(?P<tx_id>[^/]+)$",
                self._handle_patch_transaction,
            ),
            (
                "DELETE",
                r"^/v1/transactions/(?P<tx_id>[^/]+)$",
                self._handle_delete_transaction,
            ),
            (
                "GET",
                r"^/v1/status$",
                lambda p, b: {
                    "status": 200,
                    "body": {"service": "online", "version": "1.0.0"},
                },
            ),
        ]

    def _handle_post_transaction(
        self, params: Dict[str, str], body: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        if not body:
            return {"status": 400, "body": {"error": "Missing payload"}}
        tx_id = f"tx_{len(self._state['data']['transactions']) + 100}"
        tx = {"id": tx_id, **body}
        self._state["data"]["transactions"].append(tx)
        return {"status": 201, "body": tx}

    def _handle_get_transaction(
        self, params: Dict[str, str], body: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        tx_id = params.get("tx_id")
        for tx in self._state["data"]["transactions"]:
            if tx["id"] == tx_id:
                return {"status": 200, "body": tx}
        return {"status": 404, "body": {"error": f"Transaction {tx_id} not found"}}

    def _handle_put_transaction(
        self, params: Dict[str, str], body: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        if not body:
            return {"status": 400, "body": {"error": "Missing payload"}}
        tx_id = params.get("tx_id")
        for i, tx in enumerate(self._state["data"]["transactions"]):
            if tx["id"] == tx_id:
                updated_tx = {"id": tx_id, **body}
                self._state["data"]["transactions"][i] = updated_tx
                return {"status": 200, "body": updated_tx}
        return {"status": 404, "body": {"error": f"Transaction {tx_id} not found"}}

    def _handle_patch_transaction(
        self, params: Dict[str, str], body: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        if not body:
            return {"status": 400, "body": {"error": "Missing payload"}}
        tx_id = params.get("tx_id")
        for i, tx in enumerate(self._state["data"]["transactions"]):
            if tx["id"] == tx_id:
                self._state["data"]["transactions"][i].update(body)
                return {"status": 200, "body": self._state["data"]["transactions"][i]}
        return {"status": 404, "body": {"error": f"Transaction {tx_id} not found"}}

    def _handle_delete_transaction(
        self, params: Dict[str, str], body: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        tx_id = params.get("tx_id")
        initial_len = len(self._state["data"]["transactions"])
        self._state["data"]["transactions"] = [
            tx for tx in self._state["data"]["transactions"] if tx["id"] != tx_id
        ]
        if len(self._state["data"]["transactions"]) < initial_len:
            return {"status": 204, "body": {}}
        return {"status": 404, "body": {"error": f"Transaction {tx_id} not found"}}

    def _request(
        self, method: str, url: str, payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Industrial internal router using regex matching."""
        logger.info("REST: Calling %s %s", method, url)

        for r_method, r_regex, handler in self._routes:
            if r_method == method:
                match = re.match(r_regex, url)
                if match:
                    return handler(match.groupdict(), payload)

        return {
            "status": 404,
            "error": f"Endpoint '{url}' with method '{method}' not found.",
        }

    def get(self, url: str) -> Dict[str, Any]:
        """Perform a GET request."""
        return self._request("GET", url)

    def post(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Perform a POST request."""
        return self._request("POST", url, payload)

    def put(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Perform a PUT request."""
        return self._request("PUT", url, payload)

    def delete(self, url: str) -> Dict[str, Any]:
        """Perform a DELETE request."""
        return self._request("DELETE", url)

    def patch(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Perform a PATCH request."""
        return self._request("PATCH", url, payload)

    def get_tool_specs(self) -> List[Tuple[str, Any, str]]:
        return [
            ("api_get", self.get, "Perform a GET request to a REST API."),
            ("api_post", self.post, "Perform a POST request with a payload."),
            ("api_put", self.put, "Perform a PUT request to update a resource."),
            ("api_delete", self.delete, "Perform a DELETE request."),
            ("api_patch", self.patch, "Perform a PATCH request for partial updates."),
        ]
