from typing import List
from core.base_agent import BaseAgent
from core.registry import register_agent


@register_agent("fraud_detection_agent")
class FraudDetectionAgent(BaseAgent):
    """
    Monitors transactions, applies risk scoring, and files SARs.
    """

    @property
    def system_prompt(self) -> str:
        return """You are a Fraud Detection Specialist. 
Your goal is to analyze transactions for potential fraud.
1. Check transaction history in the 'database'.
2. Calculate risk scores using 'analytics'.
3. If fraud is found (>70 score), file a report using 'compliance'.
4. Notify the security team via 'notification'."""

    @property
    def allowed_shims(self) -> List[str]:
        return ["database", "analytics", "compliance", "notification"]
