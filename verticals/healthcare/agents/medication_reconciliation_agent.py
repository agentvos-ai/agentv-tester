from typing import List
from core.base_agent import BaseAgent
from core.registry import register_agent


@register_agent("medication_reconciliation_agent")
class MedicationReconciliationAgent(BaseAgent):
    """Compares current meds with medical history to find discrepancies."""

    @property
    def system_prompt(self) -> str:
        return """You are a Medication Reconciliation AI.
Compare the current medication list from the 'rest_api' with the patient history in the 'database'.
Check for interactions or duplicates using 'knowledge_base'."""

    @property
    def allowed_shims(self) -> List[str]:
        return ["rest_api", "database", "knowledge_base", "analytics"]
