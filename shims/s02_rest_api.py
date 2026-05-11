import logging


from typing import List, Dict, Any, Tuple, Optional
from core.registry import register_shim
from shims import BaseShim

logger = logging.getLogger(__name__)


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
        # 1. Handle stateful creation/mutation BEFORE validation for simulation flexibility
        if method == "POST":
            # Automatically create endpoint if it doesn't exist
            if url not in self._state["endpoints"]:
                self._state["endpoints"][url] = {
                    "GET": {"status": 200, "body": []},
                    "POST": {"status": 201, "body": {"status": "success"}}
                }
            
            # Update body
            current_body = self._state["endpoints"][url].get("GET", {}).get("body")
            if isinstance(current_body, list) and payload:
                current_body.append(payload)
            elif isinstance(current_body, dict) and payload:
                current_body.update(payload)
                
        elif method in ["PUT", "PATCH"] and url in self._state["endpoints"] and payload:
            if "GET" in self._state["endpoints"][url]:
                current_body = self._state["endpoints"][url]["GET"].get("body")
                if isinstance(current_body, dict):
                    current_body.update(payload)
                else:
                    self._state["endpoints"][url]["GET"]["body"] = payload
            # Ensure the method itself is supported in the endpoint map for validation
            if method not in self._state["endpoints"][url]:
                 self._state["endpoints"][url][method] = {"status": 200}
                    
        elif method == "DELETE" and url in self._state["endpoints"]:
             self._state["endpoints"][url]["GET"] = {"status": 404, "body": {"error": "Deleted"}}
             if "DELETE" not in self._state["endpoints"][url]:
                 self._state["endpoints"][url]["DELETE"] = {"status": 200}

        # 2. Validate endpoint
        endpoint = self._state["endpoints"].get(url)
        if not endpoint or method not in endpoint:
            return {
                "status": 404,
                "error": f"Endpoint '{url}' with method '{method}' not found.",
            }

        return endpoint.get(method, {"status": 200, "body": {"status": "success"}})

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
