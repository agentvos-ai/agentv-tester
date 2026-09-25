# Industrial Agent Design Guide

This document defines the architectural principles, interface contracts, and functional specifications for the 12 industrial agents within the agent suite.

---

## 1. Core Architecture

All agents in the system inherit from the `BaseAgent` abstraction, ensuring framework-agnostic behavior and consistent industrial parity across the evaluation matrix.

### Interface Contract: `BaseAgent`

The interface is designed for high-fidelity evaluation and forensic tracking.

```python
class BaseAgent(ABC):
    def __init__(
        self, config: Any, framework: BaseFrameworkAdapter, shims: Dict[str, Any]
    ):
        """
        Initializes the agent with industrial configuration, a framework adapter,
        and the full suite of available enterprise shims.
        """

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Instructional core defining the agent's persona and logic."""

    @property
    def input_schema(self) -> Type[BaseModel]:
        """Mandatory Pydantic schema for task input validation."""

    @property
    def output_schema(self) -> Type[BaseModel]:
        """Mandatory Pydantic schema for agent output validation."""

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Primary entry point for external callers with automatic schema validation."""
```

### Execution Lifecycle
1. **Request Intake**: Receives a `task` payload containing input and industrial context.
2. **Framework Binding**: On first execution, the agent uses the `framework` adapter to build a runtime instance (e.g., AG2, LangGraph).
3. **Tool Mapping**: `get_tool_specs()` filters the global `shims` registry to only provide the necessary industrial endpoints.
4. **Autonomous Execution**: The framework runs the agent loop against the LLM and the mapped tools.
5. **Result Normalization**: Captures output, forensic tool calls, and **cost tracking** for the evaluator.

---

## 2. Agent Directory: Fintech & Construction Verticals

| Agent | Vertical | Purpose | Primary Tools |
| :--- | :--- | :--- | :--- |
| **Fraud Detection** | Fintech | Monitors transactions, applies risk scoring, and files Suspicious Activity Reports (SAR). | `database`, `analytics`, `compliance`, `notification` |
| **Loan Underwriting** | Fintech | Evaluates creditworthiness, checks bureau APIs, and manages multi-step approval workflows. | `database`, `rest_api`, `compliance`, `workflow`, `hitl`, `email` |
| **Portfolio Advisor** | Fintech | Analyzes market trends and rebalances asset allocations based on risk profiles. | `database`, `analytics`, `rest_api`, `search`, `email` |
| **Regulatory Reporting** | Fintech | Automates the generation and filing of KYC/AML and financial compliance reports. | `database`, `compliance`, `document_processor`, `sftp` |
| **EPC Subcontractor Vetting** | Construction | Vets third-party EPC subcontractors: COI coverage, surety bonding, OFAC sanctions, and NTP issuance. | `insurance`, `bonding`, `sanctions`, `notice_to_proceed` |

### Case Study: EPC Subcontractor Vetting Agent
- **Logic**: Verifies COI insurance certificates via `insurance`, checks surety bonding limits via `bonding`, and checks OFAC sanctions via `sanctions`. If all pass and statutory version matches v5, issues Notice to Proceed via `notice_to_proceed`.
- **Industrial Hardening**: Out-of-order execution or v4 legacy statute citations trigger temporal drift violations and halt NTP issuance.

---

## 3. Agent Directory: Healthcare Vertical

| Agent | Purpose | Primary Tools |
| :--- | :--- | :--- |
| **Prior Auth** | Autonomous clinical prior-authorization evaluation enforcing statutory human review gates. | `get_patient_diagnosis_codes`, `get_payer_policy`, `check_criteria_met`, `request_human_review`, `record_human_review`, `submit_authorization_decision`, `send_provider_notification` (via `healthcare_mcp`) |
| **Clinical Triage** | Analyzes patient vitals and symptoms to prioritize care levels. | `database`, `analytics`, `notification` |
| **Medication Recon** | Compares medication lists to identify contradictions or missed dosages. | `database`, `search`, `compliance` |
| **Patient Discharge** | Coordinates post-care instructions, pharmacy orders, and follow-up scheduling. | `database`, `workflow`, `email`, `calendar` |

### Case Study: Prior Auth Agent (MCP-Native)
- **Architecture**: Subclasses `BaseMCPAgent` and dynamically connects to `mcp_servers/healthcare_mcp/server.py`.
- **Sequential 6-Step Workflow**:
  1. Retrieve patient diagnosis ICD codes (`get_patient_diagnosis_codes`).
  2. Retrieve payer clinical policy and criteria (`get_payer_policy`).
  3. Evaluate clinical criteria satisfaction (`check_criteria_met`).
  4. If criteria fail or adverse action (`DENY`, `DELAY`, `DOWNGRADE`) is indicated, mandate licensed clinical peer review (`request_human_review` / `record_human_review`) per WA ESSB 5395 and IA HF 2635.
  5. Commit determination to durable SQLite ledger (`submit_authorization_decision`).
  6. Dispatch provider notification to durable outbox (`send_provider_notification`).
- **Forensic Ledger**: Persists transaction and human review linkage into `authorizations` and `human_reviews` tables with SHA-256 state hashing.

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
The suite uses **Pydantic V2** for industrial-grade input validation. Every agent defines an `input_schema`.

```json
{
  "task_id": "REQ-12345",
  "agent": "fraud_detection_agent",
  "input_data": {
    "transaction_id": "TXN_998",
    "account_id": "ACC-001",
    "amount": 1250.0
  },
  "context": {
    "audit_level": "forensic"
  }
}
```

> [!NOTE]
> For backward compatibility, the `input` field is still supported, but `input_data` is preferred for schema-validated execution.

### 5.2 The Context Protocol

The `context` object is a flexible dictionary that is injected into the agent's reasoning loop. Framework adapters (AG2, LangGraph, etc.) are responsible for prepending this context to the primary task input.

#### Standard Industrial Context Keys
While the context is dynamic, the following keys are standardized across the agent suite to ensure high-fidelity evaluation:

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
      "name": "compliance_file_report",
      "arguments": { "type": "SAR", "id": "TXN_998" }
    }
  ],
  "execution_receipt": {
    "execution_id": "exec-9c18d34e",
    "status": "success",
    "started_at": "2026-09-25T04:58:30.000000+00:00",
    "completed_at": "2026-09-25T04:58:40.000000+00:00",
    "steps": [
      {
        "sequence": 1,
        "tool": "compliance_file_report",
        "arguments": { "type": "SAR", "id": "TXN_998" },
        "result_summary": "Report filed: SAR-445",
        "status": "completed",
        "duration_ms": 14.5
      }
    ]
  }
}
```

---

## 6. Implementation Notes for Evaluators
- **Statelessness**: Agents are instantiated per request to prevent cross-scenario drift.
- **Traceability**: Every tool call is logged in the `tool_calls` list and trajectory-ordered `execution_receipt` for forensic inspection.
- **Parity**: The `BaseAgent` ensures that whether running on AG2, LangChain, or LangGraph, the agent prompt and tool availability remain identical for fair benchmarking.
