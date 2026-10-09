"""Lazy loading for pluggable suite components.

Registrations are still performed by the existing decorators.  This module only
keeps the inexpensive name-to-module catalogue so optional SDKs are imported
when their component is selected, rather than when the web process starts.
"""

from __future__ import annotations

from importlib import import_module

LLM_MODULES = {
    "claude": "llm_providers.claude_provider",
    "gemini": "llm_providers.gemini_provider",
    "grok": "llm_providers.grok_provider",
    "heuristic": "llm_providers.heuristic_provider",
    "mock": "llm_providers.mock_provider",
    "ollama": "llm_providers.ollama_provider",
    "openai": "llm_providers.openai_provider",
}

FRAMEWORK_MODULES = {
    "ag2": "frameworks.ag2_adapter",
    "crewai": "frameworks.crewai_adapter",
    "langchain": "frameworks.langchain_adapter",
    "langgraph": "frameworks.langgraph_adapter",
}

SHIM_MODULES = {
    "git": "shims.s01_git",
    "rest_api": "shims.s02_rest_api",
    "database": "shims.s03_database",
    "knowledge_base": "shims.s04_knowledge_base",
    "support_desk": "shims.s05_support_desk",
    "social_media": "shims.s06_social_media",
    "vector_db": "shims.s07_vector_db",
    "cicd": "shims.s08_cicd",
    "iot": "shims.s09_iot",
    "security": "shims.s10_security",
    "filesystem": "shims.s11_filesystem",
    "email": "shims.s12_email",
    "calendar": "shims.s13_calendar",
    "payment": "shims.s14_payment",
    "notification": "shims.s15_notification",
    "search": "shims.s16_search",
    "analytics": "shims.s17_analytics",
    "workflow": "shims.s18_workflow",
    "compliance": "shims.s19_compliance",
    "hitl": "shims.s20_hitl",
    "insurance": "shims.s21_insurance",
    "bonding": "shims.s22_bonding",
    "sanctions": "shims.s23_sanctions",
    "notice_to_proceed": "shims.s24_notice_to_proceed",
}

VERTICAL_MODULES = {
    "construction": "verticals.construction.agents",
    "fintech": "verticals.fintech.agents",
    "healthcare": "verticals.healthcare.agents",
    "telecom": "verticals.telecom.agents",
}

AGENT_MODULES = {
    "auto_insurance_claims_agent": "verticals.fintech.agents.auto_insurance_claims_agent",
    "billing_adjustment_agent": "verticals.telecom.agents.billing_adjustment_agent",
    "churn_prevention_agent": "verticals.telecom.agents.churn_prevention_agent",
    "claims_processing_agent": "verticals.healthcare.agents.claims_processing_agent",
    "clinical_triage_agent": "verticals.healthcare.agents.clinical_triage_agent",
    "epc_subcontractor_vetting_agent": "verticals.construction.agents.epc_subcontractor_vetting_agent",
    "fraud_detection_agent": "verticals.fintech.agents.fraud_detection_agent",
    "loan_underwriting_agent": "verticals.fintech.agents.loan_underwriting_agent",
    "medication_reconciliation_agent": "verticals.healthcare.agents.medication_reconciliation_agent",
    "network_fault_agent": "verticals.telecom.agents.network_fault_agent",
    "patient_discharge_agent": "verticals.healthcare.agents.patient_discharge_agent",
    "portfolio_advisor_agent": "verticals.fintech.agents.portfolio_advisor_agent",
    "portfolio_rebalance_agent": "verticals.fintech.agents.portfolio_rebalance_agent",
    "prescription_refill_agent": "verticals.healthcare.agents.prescription_refill_agent",
    "prior_auth_agent": "verticals.healthcare.agents.prior_auth_agent",
    "provisioning_agent": "verticals.telecom.agents.provisioning_agent",
    "regulatory_reporting_agent": "verticals.fintech.agents.regulatory_reporting_agent",
    "sim_swap_agent": "verticals.telecom.agents.sim_swap_agent",
    "sla_monitoring_agent": "verticals.telecom.agents.sla_monitoring_agent",
    "wire_transfer_agent": "verticals.fintech.agents.wire_transfer_agent",
}


def _load(catalogue: dict[str, str], name: str, kind: str) -> None:
    try:
        module = catalogue[name]
    except KeyError as exc:
        raise ValueError(f"Unknown {kind}: {name}") from exc
    import_module(module)


def ensure_llm_provider(name: str) -> None:
    _load(LLM_MODULES, name, "LLM provider")


def ensure_framework(name: str) -> None:
    _load(FRAMEWORK_MODULES, name, "framework")


def ensure_shim(name: str) -> None:
    _load(SHIM_MODULES, name, "shim")


def ensure_vertical_agents(name: str) -> None:
    _load(VERTICAL_MODULES, name, "vertical")


def ensure_agent(name: str) -> None:
    _load(AGENT_MODULES, name, "agent")
