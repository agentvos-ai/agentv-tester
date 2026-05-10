from typing import List, Dict, Any, Tuple
from core.registry import register_shim
from core.errors import ShimError
from shims import BaseShim

@register_shim("security")
class SecurityShim(BaseShim):
    """
    Enterprise security and identity management service.
    Supports authentication, authorization, and secret management.
    """

    @property
    def name(self) -> str:
        return "security"

    @property
    def description(self) -> str:
        return "Centralized security service for authentication and access control."

    def reset(self) -> None:
        """Deterministic reset of the security state."""
        self._state["audit_log"]: List[Dict[str, Any]] = []
        self._state["secrets"] = {"db_password": "encrypted_root_pass"}
        self._state["permissions"] = {"agent-001": ["read", "write", "execute"]}

    def authenticate(self, user_id: str, token: str) -> bool:
        """Simulates user/service authentication."""
        success = token == "secure_token"
        self._state["audit_log"].append({"action": "AUTH", "user": user_id, "success": success})
        return success

    def check_permission(self, identity: str, permission: str) -> bool:
        """Checks if an identity has a specific permission."""
        allowed = permission in self._state["permissions"].get(identity, [])
        self._state["audit_log"].append({"action": "ACCESS", "user": identity, "permission": permission, "allowed": allowed})
        return allowed

    def rotate_secret(self, secret_id: str) -> str:
        """Rotates an enterprise secret/credential."""
        if secret_id not in self._state["secrets"]:
            raise ShimError(f"Secret '{secret_id}' not found.")
        self._state["secrets"][secret_id] = f"new_encrypted_{secret_id}"
        self._state["audit_log"].append({"action": "ROTATE", "secret": secret_id})
        return f"Secret '{secret_id}' rotated successfully."

    def get_audit_log(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieves recent security audit logs."""
        return self._state["audit_log"][-limit:]

    def get_tool_specs(self) -> List[Tuple[str, Any, str]]:
        return [
            ("security_auth", self.authenticate, "Authenticate a user or service with a token."),
            ("security_check", self.check_permission, "Check if an identity has a specific permission."),
            ("security_rotate", self.rotate_secret, "Rotate an enterprise secret or credential."),
            ("security_audit", self.get_audit_log, "Fetch recent security audit logs.")
        ]
