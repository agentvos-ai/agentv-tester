# Operations & Verification Guide

This guide provides exhaustive instructions for the setup, configuration, and verification of the Multi-Vertical Agentic Test Suite.

## 1. Environment Setup

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

## 2. Configuration System

The suite uses a three-tier configuration model defined in `config/`.

### Tier 1: Suite Defaults (`suite.yaml`)
Defines the active dimensions and global defaults.
```yaml
active_vertical: "fintech"
active_framework: "langgraph"
active_llm: "gemini"
```

### Tier 2: Dimension Specifics
- `verticals/*.yaml`: Defines which shims and agents are enabled for a domain.
- `frameworks/*.yaml`: Defines framework-specific parameters.
- `llms/*.yaml`: Maps model names to environment variables (e.g., `OPENAI_API_KEY`).

### Tier 3: Environment Overrides
All configuration keys can be overridden via environment variables using the `ACTIVE_` prefix:
- `ACTIVE_VERTICAL=healthcare`
- `ACTIVE_FRAMEWORK=crewai`
- `ACTIVE_LLM=claude`

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
Verify that shims reset to identical states using the smoke test:
```bash
python tests/smoke/test_all_combos.py
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
