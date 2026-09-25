"""Backward-compatible re-export for authorization state service.

Deprecated: Import directly from `server.authorization_state_service`.
"""

from server.authorization_state_service import (  # noqa: F401
    AuthorizationStateService,
    HealthcareStateService,
    canonical_json_bytes,
    create_authorization_state_blueprint,
    create_healthcare_state_blueprint,
)
