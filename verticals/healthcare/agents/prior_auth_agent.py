from typing import List, Type
from pydantic import BaseModel, Field
from core.base_agent import BaseAgent
from core.registry import register_agent


class PriorAuthInput(BaseModel):
    patient_id: str = Field(..., description="Unique ID of the patient.")
    procedure_code: str = Field(..., description="CPT or ICD code for the procedure.")
    diagnosis_code: str = Field(..., description="Diagnosis code (e.g., ICD-10).")
    provider_id: str = Field(..., description="Requesting provider ID.")


class PriorAuthOutput(BaseModel):
    auth_number: str = Field(None, description="Authorization ID if approved.")
    status: str = Field(..., description="APPROVED, DENIED, or PENDING_REVIEW.")
    denial_reason: str = Field(None, description="Rationale if denied.")


@register_agent("prior_auth_agent")
class PriorAuthAgent(BaseAgent):
    """Processes insurance prior-authorization requests."""

    @property
    def system_prompt(self) -> str:
        return """You are a Prior Authorization Agent.
Process requests by checking insurance 'compliance' rules and patient 'database' records.
Initiate 'workflow' for approval. Escalate to 'hitl' for complex denials."""

    @property
    def allowed_shims(self) -> List[str]:
        return ["compliance", "database", "workflow", "hitl"]

    @property
    def input_schema(self) -> Type[BaseModel]:
        return PriorAuthInput

    @property
    def output_schema(self) -> Type[BaseModel]:
        return PriorAuthOutput
