# Environment Setup

### Prerequisites
- Python 3.10+
- Virtual Environment (recommended)
- Access to LLM APIs (Gemini, OpenAI, Anthropic)

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

## 2. Server Operations

### Development Mode
Use the built-in Flask development server for local debugging and scenario testing.
```bash
# Start with default configuration (Fintech/LangGraph/Gemini)
# Start with custom dimensions (Note: Environment overrides take priority at startup)
ACTIVE_VERTICAL=healthcare ACTIVE_FRAMEWORK=crewai python server/app.py
```

> [!TIP]
> **Live Configuration Reloading**: The server supports zero-downtime configuration updates. Any changes made to `config/suite.yaml` are picked up **instantly** by the next request to `/health` or `/execute_task` without requiring a server restart.

### Production Mode (Industrial)
Use the `waitress` WSGI server for high-concurrency evaluation runs. This is the recommended mode for integration with the external harness.
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

### Harness Blindness Gate
Ensures agents have zero knowledge of the evaluation infrastructure.
```bash
# Should return zero matches
grep -r "eval_harness" verticals/
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

### Adding a New LLM Provider
1. Create `llm_providers/new_llm_provider.py`.
2. Inherit from `BaseLLMProvider`.
3. Implement `chat` (returning OpenAI-compatible dict).
4. Use `@register_llm("new_llm")`.

## 5. Integration with Eval Harness

The suite exposes a production-grade Flask endpoint:
- **Endpoint**: `POST /execute_task`
- **Payload**:
  ```json
  {
    "task_id": "REQ-001",
    "agent": "fraud_detection_agent",
    "input": "User query...",
    "context": {}
  }
  ```
- **Response**:
  ```json
  {
    "status": "success",
    "output": "Agent response...",
    "tool_calls": []
  }
  ```
