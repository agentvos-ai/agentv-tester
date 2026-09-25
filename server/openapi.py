"""Standard OpenAPI 3.1.0 specification for the Agent Evaluation Testbed server."""

from typing import Any


def get_openapi_spec() -> dict[str, Any]:
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "Agent Evaluation Testbed API",
            "version": "1.0.0",
            "description": (
                "Standard HTTP and MCP integration API for autonomous agent testing, "
                "observability, and durable domain state ledgers."
            ),
        },
        "paths": {
            "/openapi.json": {
                "get": {
                    "summary": "Retrieve OpenAPI specification",
                    "operationId": "getOpenApiSpec",
                    "responses": {
                        "200": {
                            "description": "Valid OpenAPI 3.1 schema document",
                            "content": {
                                "application/json": {"schema": {"type": "object"}}
                            },
                        }
                    },
                }
            },
            "/health": {
                "get": {
                    "summary": "Health and runtime configuration check",
                    "operationId": "getHealth",
                    "responses": {
                        "200": {
                            "description": "Server health status and active dimensions",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "status": {
                                                "type": "string",
                                                "example": "healthy",
                                            },
                                            "active_llm": {
                                                "type": "string",
                                                "example": "mock",
                                            },
                                            "active_framework": {
                                                "type": "string",
                                                "example": "langchain",
                                            },
                                            "active_vertical": {
                                                "type": "object",
                                                "properties": {
                                                    "name": {
                                                        "type": "string",
                                                        "example": "healthcare",
                                                    },
                                                    "agents": {
                                                        "type": "array",
                                                        "items": {"type": "string"},
                                                    },
                                                    "scenarios": {
                                                        "type": "array",
                                                        "items": {"type": "string"},
                                                    },
                                                },
                                                "required": [
                                                    "name",
                                                    "agents",
                                                    "scenarios",
                                                ],
                                            },
                                        },
                                        "required": [
                                            "status",
                                            "active_llm",
                                            "active_framework",
                                            "active_vertical",
                                        ],
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "/execute_task": {
                "post": {
                    "summary": "Execute an agentic task workflow",
                    "operationId": "executeTask",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "task_id": {
                                            "type": "string",
                                            "example": "HC-PA-HAPPY",
                                        },
                                        "agent": {
                                            "type": "string",
                                            "example": "prior_auth_agent",
                                        },
                                        "input": {
                                            "type": "string",
                                            "example": "Please check and submit prior-authorization for procedure CPT-99213 for patient PAT-001 with decision APPROVE.",
                                        },
                                        "context": {
                                            "type": "object",
                                            "example": {
                                                "patient_id": "PAT-001",
                                                "procedure_code": "CPT-99213",
                                                "decision": "APPROVE",
                                            },
                                        },
                                        "input_data": {"type": "object"},
                                    },
                                    "required": ["input"],
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Execution result including complete trajectory and receipt",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "status": {
                                                "type": "string",
                                                "example": "success",
                                            },
                                            "task_id": {
                                                "type": "string",
                                                "example": "HC-PA-HAPPY",
                                            },
                                            "output": {"type": "string"},
                                            "tool_calls": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "name": {"type": "string"},
                                                        "arguments": {"type": "object"},
                                                    },
                                                    "required": ["name", "arguments"],
                                                },
                                            },
                                            "execution_receipt": {
                                                "type": "object",
                                                "properties": {
                                                    "execution_id": {"type": "string"},
                                                    "steps": {
                                                        "type": "array",
                                                        "items": {
                                                            "type": "object",
                                                            "properties": {
                                                                "sequence": {
                                                                    "type": "integer"
                                                                },
                                                                "kind": {
                                                                    "type": "string"
                                                                },
                                                                "tool": {
                                                                    "type": "string"
                                                                },
                                                                "arguments": {
                                                                    "type": "object"
                                                                },
                                                                "result_summary": {
                                                                    "type": "string"
                                                                },
                                                            },
                                                            "required": [
                                                                "sequence",
                                                                "kind",
                                                                "tool",
                                                                "arguments",
                                                                "result_summary",
                                                            ],
                                                        },
                                                    },
                                                    "started_at": {
                                                        "type": "string",
                                                        "format": "date-time",
                                                    },
                                                    "completed_at": {
                                                        "type": "string",
                                                        "format": "date-time",
                                                    },
                                                    "status": {"type": "string"},
                                                },
                                                "required": [
                                                    "execution_id",
                                                    "steps",
                                                    "started_at",
                                                    "completed_at",
                                                    "status",
                                                ],
                                            },
                                            "schema_validated": {"type": "boolean"},
                                        },
                                        "required": [
                                            "status",
                                            "output",
                                            "tool_calls",
                                            "schema_validated",
                                        ],
                                    }
                                }
                            },
                        },
                        "400": {
                            "description": "Invalid payload or parameters",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "status": {
                                                "type": "string",
                                                "example": "error",
                                            },
                                            "message": {"type": "string"},
                                        },
                                        "required": ["status", "message"],
                                    }
                                }
                            },
                        },
                    },
                }
            },
            "/update_config": {
                "post": {
                    "summary": "Update active testing dimensions (vertical, framework, llm)",
                    "operationId": "updateConfig",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "vertical": {
                                            "type": "string",
                                            "example": "healthcare",
                                        },
                                        "framework": {
                                            "type": "string",
                                            "example": "langchain",
                                        },
                                        "llm": {"type": "string", "example": "mock"},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Configuration successfully updated",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "status": {
                                                "type": "string",
                                                "example": "success",
                                            },
                                            "message": {"type": "string"},
                                        },
                                        "required": ["status", "message"],
                                    }
                                }
                            },
                        },
                        "400": {
                            "description": "Invalid configuration parameters",
                        },
                    },
                }
            },
            "/healthcare/reset": {
                "post": {
                    "summary": "Reset healthcare authorization state and outbox to pristine fixture baseline",
                    "operationId": "resetHealthcareState",
                    "responses": {
                        "200": {
                            "description": "Reset status and pristine snapshot",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "status": {
                                                "type": "string",
                                                "example": "reset",
                                            },
                                            "snapshot": {"type": "object"},
                                        },
                                        "required": ["status", "snapshot"],
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "/healthcare/state": {
                "get": {
                    "summary": "Query current healthcare authorization ledger, review records, and outbox with SHA-256 integrity hash",
                    "operationId": "getHealthcareState",
                    "responses": {
                        "200": {
                            "description": "Current snapshot and deterministic hashes",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "observed_at": {
                                                "type": "string",
                                                "format": "date-time",
                                            },
                                            "state": {
                                                "type": "object",
                                                "properties": {
                                                    "authorizations": {"type": "array"},
                                                    "human_reviews": {"type": "array"},
                                                    "outbox": {"type": "array"},
                                                },
                                                "required": [
                                                    "authorizations",
                                                    "human_reviews",
                                                    "outbox",
                                                ],
                                            },
                                            "state_hash": {
                                                "type": "string",
                                                "example": "sha256:...",
                                            },
                                            "receipt_hash": {
                                                "type": "string",
                                                "example": "sha256:...",
                                            },
                                        },
                                        "required": [
                                            "observed_at",
                                            "state",
                                            "state_hash",
                                            "receipt_hash",
                                        ],
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "/healthcare/authorizations/{authorization_id}": {
                "get": {
                    "summary": "Retrieve authorization record by unique identifier",
                    "operationId": "getHealthcareAuthorizationById",
                    "parameters": [
                        {
                            "name": "authorization_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                            "example": "AUTH-48A2C19F",
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Durable authorization record",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "authorization_id": {"type": "string"},
                                            "patient_id": {"type": "string"},
                                            "procedure_code": {"type": "string"},
                                            "decision": {"type": "string"},
                                            "decision_source": {"type": "string"},
                                            "criteria_met": {"type": "boolean"},
                                            "human_review_required": {
                                                "type": "boolean"
                                            },
                                            "human_review_id": {
                                                "type": ["string", "null"]
                                            },
                                            "committed_at": {
                                                "type": "string",
                                                "format": "date-time",
                                            },
                                            "notification_status": {"type": "string"},
                                        },
                                        "required": [
                                            "authorization_id",
                                            "patient_id",
                                            "procedure_code",
                                            "decision",
                                            "decision_source",
                                            "criteria_met",
                                            "human_review_required",
                                            "committed_at",
                                            "notification_status",
                                        ],
                                    }
                                }
                            },
                        },
                        "404": {"description": "Authorization record not found"},
                    },
                }
            },
            "/healthcare/authorizations": {
                "get": {
                    "summary": "List all committed authorizations",
                    "operationId": "listHealthcareAuthorizations",
                    "responses": {
                        "200": {
                            "description": "List of authorizations",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "authorizations": {"type": "array"}
                                        },
                                        "required": ["authorizations"],
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "/healthcare/outbox": {
                "get": {
                    "summary": "Query durable provider notification outbox records",
                    "operationId": "getHealthcareOutbox",
                    "responses": {
                        "200": {
                            "description": "List of notification outbox entries",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {"outbox": {"type": "array"}},
                                        "required": ["outbox"],
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "/healthcare/reviews": {
                "post": {
                    "summary": "Record a licensed clinical human review artifact",
                    "operationId": "recordHealthcareHumanReview",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "patient_id": {
                                            "type": "string",
                                            "example": "PAT-002",
                                        },
                                        "procedure_code": {
                                            "type": "string",
                                            "example": "CPT-33510",
                                        },
                                        "reviewer_id": {
                                            "type": "string",
                                            "example": "MD-LIC-4491",
                                        },
                                        "reviewer_type": {
                                            "type": "string",
                                            "example": "LICENSED_PHYSICIAN",
                                        },
                                        "disposition": {
                                            "type": "string",
                                            "example": "DENY",
                                        },
                                        "clinical_notes": {"type": "string"},
                                        "review_id": {"type": "string"},
                                    },
                                    "required": [
                                        "patient_id",
                                        "procedure_code",
                                        "reviewer_id",
                                        "reviewer_type",
                                        "disposition",
                                    ],
                                }
                            }
                        },
                    },
                    "responses": {
                        "201": {
                            "description": "Recorded human review artifact",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "status": {
                                                "type": "string",
                                                "example": "recorded",
                                            },
                                            "review": {"type": "object"},
                                        },
                                        "required": ["status", "review"],
                                    }
                                }
                            },
                        },
                        "400": {"description": "Missing required fields"},
                    },
                }
            },
        },
    }
