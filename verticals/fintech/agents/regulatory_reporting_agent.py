from typing import List, Type
from pydantic import BaseModel, Field
from core.base_agent import BaseAgent
from core.registry import register_agent


class RegulatoryReportingInput(BaseModel):
    report_type: str = Field(
        ..., description="Type of report (e.g., SAR, 10-Q, BASEL-III)."
    )
    reporting_period: str = Field(
        ..., description="The time period covered by the report."
    )
    data_sources: List[str] = Field(default_factory=lambda: ["database", "analytics"])


class RegulatoryReportingOutput(BaseModel):
    report_path: str = Field(
        ..., description="Path to the generated report in the filesystem."
    )
    git_commit_hash: str = Field(
        ..., description="Version control hash for the filed report."
    )
    filing_status: str = Field(..., description="FILED, DRAFT, or FAILED.")


@register_agent("regulatory_reporting_agent")
class RegulatoryReportingAgent(BaseAgent):
    """Extracts data, assembles report, versions via git, emails regulator, files compliance record."""

    @property
    def system_prompt(self) -> str:
        return """You are a Regulatory Reporting Agent. You automate the filing of mandated financial reports.
You extract data from databases, assemble reports in the filesystem, version them using Git, and file them via compliance engines."""

    @property
    def allowed_shims(self) -> List[str]:
        return ["database", "filesystem", "compliance", "email", "analytics", "git"]

    @property
    def input_schema(self) -> Type[BaseModel]:
        return RegulatoryReportingInput

    @property
    def output_schema(self) -> Type[BaseModel]:
        return RegulatoryReportingOutput
