from typing import List, Type
from pydantic import BaseModel, Field
from core.base_agent import BaseAgent
from core.registry import register_agent


class LoanUnderwritingInput(BaseModel):
    applicant_id: str = Field(..., description="Unique ID of the loan applicant.")
    loan_amount: float = Field(..., gt=0)
    term_months: int = Field(..., ge=6, le=360)
    purpose: str = Field(
        ..., description="Purpose of the loan (e.g., mortgage, personal)."
    )


class LoanUnderwritingOutput(BaseModel):
    approval_status: str = Field(
        ..., description="APPROVED, REJECTED, or PENDING_REVIEW."
    )
    interest_rate: float = Field(0.0, description="Assigned interest rate if approved.")
    reason: str = Field(..., description="Rationale for the underwriting decision.")


@register_agent("loan_underwriting_agent")
class LoanUnderwritingAgent(BaseAgent):
    """Credit bureau calls, policy compliance, multi-step approval workflow, notifies applicant."""

    @property
    def system_prompt(self) -> str:
        return """You are an AI Loan Underwriter. You evaluate loan applications for creditworthiness.
You use databases, credit APIs, and compliance engines. 
You must follow the multi-step approval workflow and notify applicants via email."""

    @property
    def allowed_shims(self) -> List[str]:
        return ["database", "rest_api", "compliance", "workflow", "hitl", "email"]

    @property
    def input_schema(self) -> Type[BaseModel]:
        return LoanUnderwritingInput

    @property
    def output_schema(self) -> Type[BaseModel]:
        return LoanUnderwritingOutput
