from typing import List, Dict, Any
from core.base_agent import BaseAgent
from core.registry import register_agent

@register_agent("regulatory_reporting_agent")
class RegulatoryReportingAgent(BaseAgent):
    """Extracts data, assembles report, versions via git, emails regulator, files compliance record."""

    @property
    def system_prompt(self) -> str:
        return """You are a Regulatory Reporting Agent. You automate the filing of mandated financial reports.
You extract data from databases, assemble reports in the filesystem, version them using Git, and file them via compliance engines."""

    def get_tool_specs(self) -> List[Dict[str, Any]]:
        tools = []
        for shim_name in ["database", "filesystem", "compliance", "email", "analytics", "git"]:
            if shim_name in self._shims:
                tools.extend(self._shims[shim_name].get_tool_specs())
        return tools
