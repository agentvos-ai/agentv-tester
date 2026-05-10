import logging

logger = logging.getLogger(__name__)

from typing import List, Dict, Any, Tuple, Optional
from core.registry import register_shim
from shims import BaseShim


@register_shim("rest_api")
class RestApiShim(BaseShim):
    """
    Generic HTTP API simulator with configurable response fixtures.
    Supports standard REST methods.
    """

    @property
    def name(self) -> str:
        return "rest_api"

    @property
    def description(self) -> str:
        return "Interface for interacting with internal and external RESTful services."

    def reset(self) -> None:
        """Deterministic reset of the API state."""
        self._state["endpoints"] = {
            "/v1/credit_score": {
                "GET": {"status": 200, "body": {"score": 750, "rating": "Excellent"}}
            },
            "/v1/transactions": {
                "GET": {"status": 200, "body": []},
                "POST": {"status": 201, "body": {"id": "tx_123", "status": "success"}},
            },
        }

    def _request(
        self, method: str, url: str, payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generic request handler."""
        logger.info("REST: Calling %s %s", method, url)
        endpoint = self._state["endpoints"].get(url)
        if not endpoint or method not in endpoint:
            return {
                "status": 404,
                "error": f"Endpoint '{url}' with method '{method}' not found.",
            }

        # Simulate logic for POST/PUT/PATCH
        if method in ["POST", "PUT", "PATCH"] and url == "/v1/transactions" and payload:
            self._state["endpoints"]["/v1/transactions"]["GET"]["body"].append(payload)

        return endpoint[method]

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
