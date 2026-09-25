# 1. Environment Setup

### Prerequisites
- Python 3.14 (Industrial Evaluation Baseline)
- Virtual Environment (recommended)
- Access to LLM APIs (Gemini, OpenAI, Anthropic) or Stateful Mock Provider

### Installation
```bash
# Clone and enter the workspace
cd agentv-tester

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 📂 Forensic Workspace
The suite maintains all persistent state within the `.agent_workspace/` directory. This is critical for forensic auditability and state persistence across test runs.

- `.agent_workspace/db/`: Contains SQLite databases for all services (`authorization_state.sqlite`, Git, DB, CRM, IoT, etc.).
- `.agent_workspace/git/`: Contains real Git repository checkouts for `GitShim`.
- `.agent_workspace/vfs/`: Virtual File System root for `FilesystemShim`.

## 2. Server Operations

### Development Mode
Use the built-in Flask development server for local debugging and scenario testing.
```bash
# Start with default configuration (Fintech/LangGraph/Gemini)
# Start with custom dimensions (Note: Environment overrides take priority at startup)
ACTIVE_VERTICAL=healthcare ACTIVE_FRAMEWORK=langchain python server/app.py
```

> [!TIP]
> **Live Configuration Reloading**: The server supports zero-downtime configuration updates. Any changes made to `config/suite.yaml` or posted to `/update_config` are picked up **instantly** by subsequent requests without requiring a server restart.

### Production Mode (Industrial)
Use the `waitress` WSGI server for high-concurrency evaluation runs.
```bash
# Start with 4 worker threads on port 8080
waitress-serve --port=8080 --threads=4 server.app:create_app
```

### Health Verification
Verify the server state and active dimensions. 

> [!IMPORTANT]
> **PowerShell Users**: Use `curl.exe` or `Invoke-WebRequest -UseBasicParsing` to avoid interactive security prompts.

```bash
curl.exe http://localhost:8080/health
```

Expected response:
```json
{
  "status": "healthy",
  "active_llm": "gemini",
  "active_framework": "langgraph",
  "active_vertical": {
    "name": "fintech",
    "agents": ["fraud_detection_agent", "portfolio_advisor_agent", "..."],
    "scenarios": []
  }
}
```

The suite uses a three-tier configuration model defined in `config/`. All files must be encoded in **UTF-8 (No BOM)** to prevent parsing errors.

### Tier 1: Suite Defaults (`suite.yaml`)
Defines the active dimensions and global defaults using a nested `active` block.
```yaml
active:
  vertical: "fintech"
  framework: "langgraph"
  llm: "gemini"
```

### Tier 2: Dimension Specifics
- `verticals/*.yaml`: Defines which shims, agents, and scenarios are enabled for a domain.
- `llms/*.yaml`: Maps model names to environment variables (e.g., `GEMINI_API_KEY`).
- **Frameworks**: Registered dynamically via code adapters; validated at runtime against the `FrameworkRegistry`.

### Tier 3: Environment Isolation
To ensure the `suite.yaml` remains the "Single Source of Truth", the server **purges persistent environment variables** starting with `ACTIVE_` during every configuration load. 

To override settings via the environment, variables must be set **per-execution** (e.g., `ACTIVE_VERTICAL=telecom python server/app.py`). System-wide or shell-persistent variables are ignored to prevent "ghost" configurations from polluting the evaluation matrix.

## 3. Verification & Quality Gates

### Type Safety Audit
```bash
mypy --strict core/ shims/
```

### Linting & Style
```bash
ruff check .
```

### Evaluation Neutrality Gate
Ensures agents and tests maintain zero knowledge of proprietary evaluation products.
```bash
# Verifies clean isolation across verticals
pytest tests/unit/
```

### Determinism Check
Verify that shims reset to identical states using the smoke test. Run from the root directory:
```bash
# Using pytest (recommended)
pytest tests/smoke/test_all_combos.py

# Using unittest
python -m unittest tests/smoke/test_all_combos.py
```

## 4. Extensibility Guide

### Adding a New Shim
1. Create `shims/s21_new_service.py`.
2. Inherit from `BaseShim`.
3. Use `@register_shim("new_service")`.
4. Import in `shims/__init__.py`.

### Adding a New Framework
1. Create `frameworks/new_framework_adapter.py`.
2. Inherit from `BaseFrameworkAdapter`.
3. Implement `build_agent` and a corresponding `RunnableAgent` class.
4. Use `@register_framework("new_framework")`.

### Using the Stateful Simulator
For integration testing without live LLM APIs, use the `mock` provider. It implements a **Deterministic State Machine** that mimics authentic agent-tool sequences across domains, including multi-step clinical prior-authorization with adverse human-review gating.

```yaml
# suite.yaml
active:
  llm: "mock"
```

### Adding a New LLM Provider
1. Create `llm_providers/new_llm_provider.py`.
2. Inherit from `BaseLLMProvider`.
3. Implement `chat` (returning OpenAI-compatible dict).
4. Use `@register_llm("new_llm")`.

## 5. API Surface & Integration Contracts

The server exposes standard OpenAPI 3.1 REST endpoints for automated test execution, configuration management, and durable authorization ledger auditing:

### 5.1 Standard OpenAPI Specification
- **Endpoint**: `GET /openapi.json`
- **Description**: Returns the full OpenAPI 3.1.0 document describing all endpoints, schemas, and SHA-256 digest formats.

### 5.2 Task Execution Contract
- **Endpoint**: `POST /execute_task`
- **Payload**:
  ```json
  {
    "task_id": "REQ-001",
    "agent": "prior_auth_agent",
    "input": "Check prior-authorization for patient PAT-001 / CPT-99213.",
    "context": {
      "patient_id": "PAT-001",
      "procedure_code": "CPT-99213",
      "decision": "APPROVE"
    }
  }
  ```
- **Response**:
  ```json
  {
    "status": "success",
    "task_id": "REQ-001",
    "output": "Prior authorization APPROVED; provider notified.",
    "tool_calls": [
      { "name": "get_patient_diagnosis_codes", "arguments": { "patient_id": "PAT-001" } },
      { "name": "get_payer_policy", "arguments": { "procedure_code": "CPT-99213" } },
      { "name": "check_criteria_met", "arguments": { "patient_id": "PAT-001", "procedure_code": "CPT-99213" } },
      { "name": "submit_authorization_decision", "arguments": { "patient_id": "PAT-001", "procedure_code": "CPT-99213", "decision": "APPROVE" } },
      { "name": "send_provider_notification", "arguments": { "authorization_id": "AUTH-001", "channel": "outbox", "destination": "provider@clinic.example" } }
    ],
    "execution_receipt": {
      "execution_id": "exec-9c18d34e",
      "status": "success",
      "started_at": "2026-09-25T04:58:30.000000+00:00",
      "completed_at": "2026-09-25T04:58:40.000000+00:00",
      "steps": [
        { "sequence": 1, "tool": "get_patient_diagnosis_codes", "status": "completed", "duration_ms": 12.4 },
        { "sequence": 2, "tool": "get_payer_policy", "status": "completed", "duration_ms": 8.1 },
        { "sequence": 3, "tool": "check_criteria_met", "status": "completed", "duration_ms": 7.9 },
        { "sequence": 4, "tool": "submit_authorization_decision", "status": "completed", "duration_ms": 15.2 },
        { "sequence": 5, "tool": "send_provider_notification", "status": "completed", "duration_ms": 9.0 }
      ]
    }
  }
  ```

### 5.3 Durable Authorization State Service
The authorization state authority operates independently via SQLite ledger with SHA-256 state hashing:
- **`GET /authorizations/state`** (alias: `GET /healthcare/state`): Retrieves ledger state (`authorizations`, `human_reviews`, `outbox`) and canonical `state_hash` (SHA-256).
- **`POST /authorizations/reset`** (alias: `POST /healthcare/reset`): Purges authorizations and outbox to restore clean baseline fixtures.
- **`GET /authorizations/<id>`** (alias: `GET /healthcare/authorizations/<id>`): Retrieves record and human-review linkage for a specific authorization.
- **`GET /authorizations/outbox`** (alias: `GET /healthcare/outbox`): Retrieves queued and sent provider notification records.
- **`POST /authorizations/reviews`** (alias: `POST /healthcare/reviews`): Records a licensed clinical human review artifact satisfying regulatory gating.

### 5.4 Dynamic Configuration
- **`POST /update_config`**: Dynamically adjusts runtime dimensions without restarting:
  ```json
  {
    "framework": "langgraph",
    "llm": "gemini",
    "vertical": "healthcare"
  }
  ```

### 5.5 Regulatory Medical Necessity Adjudication
Under **Washington ESSB 5395** and **Iowa HF 2635**, artificial intelligence agents may not unilaterally commit adverse determinations (e.g. `DENY`, `DELAY`, `DOWNGRADE`) or determinations where clinical criteria are unmet. The healthcare MCP server enforces that an adverse determination cannot commit to the durable state authority without a licensed physician review artifact recorded via `record_human_review`. Notifications must be dispatched to the durable outbox following adjudication.

## 6. Interactive Evaluation UI

The suite includes a premium, real-time dashboard for manual evaluation and rapid prototyping.

- **Access**: `GET http://localhost:8080/`
- **Features**:
    - **Dynamic Agent Selection**: Dropdown automatically populates from the registry.
    - **Live Execution**: Submit tasks and view formatted JSON results instantly.
    - **Context Editor**: Built-in JSON editor for injecting metadata into agent runs.
    - **Dark Mode Aesthetic**: Designed for high-focus industrial engineering environments.

## 7. Agent Invocation Examples

Below are representative examples for invoking various agents across different verticals via the REST API.

### Fintech Examples

**PowerShell (Recommended)**
```powershell
# Loan Underwriting
Invoke-RestMethod -Method Post -Uri http://localhost:8080/execute_task `
  -ContentType "application/json" `
  -Body '{
    "task_id": "L-202",
    "agent": "loan_underwriting_agent",
    "input": "Evaluate creditworthiness for applicant ID 9928.",
    "context": {
      "user_tier": "gold",
      "region": "EMEA",
      "session_id": "sess-4455"
    }
  }'
```

**Windows CMD / curl.exe**
```bash
# Fraud Detection (Note the escaped double quotes for Windows CMD)
curl.exe -X POST http://localhost:8080/execute_task ^
  -H "Content-Type: application/json" ^
  -d "{\"task_id\": \"F-101\", \"agent\": \"fraud_detection_agent\", \"input\": \"Analyze recent transactions for user 5501 for anomalies.\"}"
```

### Healthcare Examples

**PowerShell**
```powershell
# Clinical Triage
Invoke-RestMethod -Method Post -Uri http://localhost:8080/execute_task `
  -ContentType "application/json" `
  -Body '{
    "task_id": "H-303",
    "agent": "clinical_triage_agent",
    "input": "Assess patient vitals: BP 140/90, HR 88, Temp 99.1F.",
    "context": {
      "department": "emergency",
      "patient_priority": "high"
    }
  }'
```

**Windows CMD**
```bash
# Prior Authorization
curl.exe -X POST http://localhost:8080/execute_task ^
  -H "Content-Type: application/json" ^
  -d "{\"task_id\": \"H-404\", \"agent\": \"prior_auth_agent\", \"input\": \"Validate coverage for MRI procedure under policy XYZ-99.\"}"
```

### Telecom Examples

**PowerShell**
```powershell
# Churn Prevention
Invoke-RestMethod -Method Post -Uri http://localhost:8080/execute_task `
  -ContentType "application/json" `
  -Body '{
    "task_id": "T-505",
    "agent": "churn_prevention_agent",
    "input": "Identify high-risk churn customers in the Northeast region.",
    "context": {
      "data_source": "snowflake_v2",
      "threshold": 0.85
    }
  }'
```

**Windows CMD**
```bash
# Network Fault Analysis
curl.exe -X POST http://localhost:8080/execute_task ^
  -H "Content-Type: application/json" ^
  -d "{\"task_id\": \"T-606\", \"agent\": \"network_fault_agent\", \"input\": \"Diagnose packet loss spike in Node 7-B.\"}"
```
