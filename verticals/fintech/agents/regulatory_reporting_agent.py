from typing import List
from core.base_agent import BaseAgent
from core.registry import register_agent


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
