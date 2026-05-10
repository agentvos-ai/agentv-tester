# Multi-Vertical Agentic Test Suite

A production-grade, highly configurable Agentic Test Suite designed to verify enterprise agent capabilities across multiple domains, frameworks, and LLM providers.

## 🚀 One-Line Swaps

Switch any dimension of the suite using environment variables or `suite.yaml`:

```bash
# Run Fintech agents with LangGraph on Gemini
ACTIVE_VERTICAL=fintech ACTIVE_FRAMEWORK=langgraph ACTIVE_LLM=gemini python server/app.py

# Run Healthcare agents with CrewAI on Claude
ACTIVE_VERTICAL=healthcare ACTIVE_FRAMEWORK=crewai ACTIVE_LLM=claude python server/app.py

# Run Telecom agents with AG2 (AutoGen) on OpenAI
ACTIVE_VERTICAL=telecom ACTIVE_FRAMEWORK=ag2 ACTIVE_LLM=openai python server/app.py
```

## 🏗️ Architecture

- **3 Verticals**: Fintech, Healthcare, Telecom.
- **4 Frameworks**: LangChain, LangGraph, AG2, CrewAI.
- **5 LLM Providers**: Gemini, OpenAI, Claude, Grok, Ollama.
- **20 Shims**: High-fidelity simulators for Git, SQL, REST, VectorDB, etc.

## 🛡️ Quality Gates

| Gate | Status | Standard |
|------|--------|----------|
| Type safety | ✅ | `mypy --strict` passes |

## 📖 Documentation

For detailed instructions on setup, configuration, and adding new components, see the [Operations & Verification Guide](design/OPERATIONS_GUIDE.md).
| Linting | ✅ | `ruff check .` zero errors |
| Determinism | ✅ | Seeded `reset()` in all shims |
| Blindness | ✅ | Zero `eval_harness` leaks in agents |

## 🛠️ Quickstart

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Secrets**:
   Create a `.env` file with your API keys (e.g., `GEMINI_API_KEY`, `OPENAI_API_KEY`).

3. **Run the Suite**:
   ```bash
   python server/app.py
   ```

4. **Verify with Smoke Tests**:
   ```bash
   python tests/smoke/test_all_combos.py
   ```
