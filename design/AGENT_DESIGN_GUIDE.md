# Industrial Agent Design Guide

This document defines the architectural principles, interface contracts, and functional specifications for the 12 industrial agents within the AgentV evaluation harness.

---

## 1. Core Architecture

All agents in the system inherit from the `BaseAgent` abstraction, ensuring framework-agnostic behavior and consistent industrial parity across the evaluation matrix.

### Interface Contract: `BaseAgent`

The interface is designed for high-fidelity evaluation and forensic tracking.

```python
class BaseAgent(ABC):
    def __init__(self, config: Any, framework: BaseFrameworkAdapter, shims: Dict[str, Any]):
        """
        Initializes the agent with industrial configuration, a framework adapter, 
        and the full suite of available enterprise shims.
        """

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Instructional core defining the agent's persona and logic."""

    @abstractmethod
    def get_tool_specs(self) -> List[Any]:
        """Subset of enterprise shims exposed as tools to the agent."""

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Primary entry point for external callers."""
```

### Execution Lifecycle
1. **Request Intake**: Receives a `task` payload containing input and industrial context.
2. **Framework Binding**: On first execution, the agent uses the `framework` adapter to build a runtime instance (e.g., AG2, LangGraph).
3. **Tool Mapping**: `get_tool_specs()` filters the global `shims` registry to only provide the necessary industrial endpoints.
4. **Autonomous Execution**: The framework runs the agent loop against the LLM and the mapped tools.
5. **Result Normalization**: Captures output and forensic tool calls for the evaluator.

---

## 2. Agent Directory: Fintech Vertical

| Agent | Purpose | Primary Tools |
| :--- | :--- | :--- |
| **Fraud Detection** | Monitors transactions, applies risk scoring, and files Suspicious Activity Reports (SAR). | `database`, `analytics`, `compliance`, `notification` |
| **Loan Underwriting** | Evaluates creditworthiness, checks bureau APIs, and manages multi-step approval workflows. | `database`, `rest_api`, `compliance`, `workflow`, `hitl`, `email` |
| **Portfolio Advisor** | Analyzes market trends and rebalances asset allocations based on risk profiles. | `database`, `analytics`, `rest_api`, `search`, `email` |
| **Regulatory Reporting** | Automates the generation and filing of KYC/AML and financial compliance reports. | `database`, `compliance`, `document_processor`, `sftp` |

### Case Study: Fraud Detection Agent
- **Logic**: Analyzes transaction history via `database`, calculates risk via `analytics`. If risk > 70, triggers `compliance` filing and `notification`.
- **Industrial Hardening**: Ensures SAR filings are forensic-grade and notification pathways are authenticated.

---

## 3. Agent Directory: Healthcare Vertical

| Agent | Purpose | Primary Tools |
| :--- | :--- | :--- |
| **Prior Auth** | Processes insurance authorization requests against compliance rules and patient records. | `compliance`, `database`, `workflow`, `hitl` |
| **Clinical Triage** | Analyzes patient vitals and symptoms to prioritize care levels. | `database`, `analytics`, `notification` |
| **Medication Recon** | Compares medication lists to identify contradictions or missed dosages. | `database`, `search`, `compliance` |
| **Patient Discharge** | Coordinates post-care instructions, pharmacy orders, and follow-up scheduling. | `database`, `workflow`, `email`, `calendar` |

### Case Study: Prior Auth Agent
- **Logic**: Cross-references patient history in `database` with insurance `compliance` matrices.
- **Human-in-the-Loop**: Escalates complex denials to `hitl` to maintain medical safety standards.

---

## 4. Agent Directory: Telecom Vertical

| Agent | Purpose | Primary Tools |
| :--- | :--- | :--- |
| **Churn Prevention** | Identifies high-risk customers and executes retention strategies via targeted incentives. | `analytics`, `support_desk`, `search`, `email`, `social_media` |
| **Network Fault** | Diagnoses packet loss, signal drops, and hardware failures in Node infrastructure. | `database`, `analytics`, `notification`, `slack` |
| **Provisioning** | Automates the setup of new fiber/cellular lines and hardware activation. | `database`, `rest_api`, `workflow` |
| **SLA Monitoring** | Tracks uptime and latency against contractual obligations; triggers alerts on breaches. | `analytics`, `compliance`, `notification` |

### Case Study: Churn Prevention Agent
- **Logic**: Fuses sentiment data from `support_desk` with behavioral `analytics`. Executes retention via `social_media` or `email` shims.
- **Competitive Intelligence**: Uses `search` to compare current plans with competitor offerings in real-time.

---

## 5. Interface Schema (The Industrial Contract)

### 5.1 Input Schema (`POST /execute_task`)
```json
{
  "task_id": "REQ-12345",
  "agent": "fraud_detection_agent",
  "input": "Analyze transaction TXN_998 for potential money laundering.",
  "context": {
    "audit_level": "forensic"
  }
}
```

### 5.2 The Context Protocol

The `context` object is a flexible dictionary that is injected into the agent's reasoning loop. Framework adapters (AG2, LangGraph, etc.) are responsible for prepending this context to the primary task input.

#### Standard Industrial Context Keys
While the context is dynamic, the following keys are standardized across the AgentV suite to ensure high-fidelity evaluation:

| Key | Description | Example |
| :--- | :--- | :--- |
| `jurisdiction` | Regulatory region for compliance checks. | `GDPR`, `HIPAA`, `FINRA` |
| `priority` | Execution urgency (affects risk scoring). | `high`, `critical`, `standard` |
| `audit_level` | Depth of logging and forensic tracking. | `forensic`, `minimal`, `none` |
| `role` | The simulated persona of the requester. | `security_admin`, `patient_proxy` |
| `timestamp` | Temporal context for validity checks. | `2024-05-11T10:00:00Z` |

### 5.3 Context Sufficiency

To ensure an agent has "sufficient" context to succeed, users should follow the **Industrial Context Checklist**:

1. **Entity Identification**: Does the context or input identify the specific transaction, patient, or node ID? (e.g., `TXN_998`).
2. **Policy Scope**: Is the relevant regulatory framework specified? (e.g., `jurisdiction: HIPAA`).
3. **Operational Constraints**: Are there specific thresholds or limits provided? (e.g., `max_refund: 500`).
4. **Human-in-the-Loop Availability**: Is the `hitl` shim enabled for cases requiring escalation?

**Sufficiency Failure Handling**:
If an agent detects missing critical context, it is instructed to:
1. Attempt to find the missing data using discovery tools (e.g., `search`, `database`).
2. If unreachable, the agent will include a "Missing Context" warning in the `output` field rather than guessing, ensuring evaluation integrity.

### 5.4 Output Schema
```json
{
  "status": "success",
  "task_id": "REQ-12345",
  "output": "Transaction TXN_998 flagged for risk score 85. SAR filed.",
  "tool_calls": [
    {
      "tool": "compliance_file_report",
      "args": { "type": "SAR", "id": "TXN_998" },
      "result": "Report filed: SAR-445"
    }
  ]
}
```

---

## 6. Implementation Notes for Evaluators
- **Statelessness**: Agents are instantiated per request to prevent cross-scenario drift.
- **Traceability**: Every tool call is logged in the `tool_calls` list for trajectory analysis.
- **Parity**: The `BaseAgent` ensures that whether running on AG2 or LangGraph, the agent prompt and tool availability remain identical for fair benchmarking.
