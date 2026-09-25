# 🚀 ANTIGRAVITY CODING ASSISTANT PROMPT
## Multi-Vertical Agentic Test Suite
### Target: Enterprise AI Agent Testbed (Industrial Baseline v3.0.0)

---

> **ROLE:** You are an expert AI systems architect and senior Python engineer.
> Your mission is to build a **production-grade, highly configurable Agentic Test Suite**
> that mimics real-world enterprise agents across three industry verticals.
> These agents are **test subjects** — they must behave as authentic domain agents
> with zero awareness of any evaluation harness observing them.

---

## 0 ─ PRIME DIRECTIVES

| # | Directive |
|---|-----------|
| 1 | **Harness Blindness** — Agents must NEVER import, reference, or assume any evaluation harness. They are production-grade enterprise agents that happen to be run under test conditions. |
| 2 | **Vertical Fidelity** — Each agent must exhibit authentic domain behaviour: real terminology, plausible tool chains, domain-appropriate error handling, and realistic state transitions. |
| 3 | **One-Line Swap** — Changing vertical, framework, or LLM must require editing exactly ONE config value (env var or YAML key). |
| 4 | **Open/Closed Principle** — Adding a new framework or LLM provider must require zero changes to existing agent or vertical code. Implement via abstract base + plugin registry. |
| 5 | **Shim Composition** — Each agent uses a curated subset (4–10) of the 20 enterprise shims in realistic combinations. No agent uses all 20; no shim is orphaned. |
| 6 | **Framework Parity** — The same vertical scenario must be runnable under any of the 4 supported frameworks with identical observable behaviour. |

---

## 1 ─ PROJECT LAYOUT

```
agent-test-suite/
├── config/
│   ├── suite.yaml                # Master config: active vertical, framework, llm
│   ├── verticals/
│   │   ├── fintech.yaml
│   │   ├── healthcare.yaml
│   │   └── telecom.yaml
│   ├── frameworks/
│   │   ├── langchain.yaml
│   │   ├── langgraph.yaml
│   │   ├── autogen.yaml
│   │   └── crewai.yaml
│   └── llms/
│       ├── openai.yaml
│       ├── claude.yaml
│       ├── gemini.yaml
│       ├── grok.yaml
│       └── ollama.yaml
│
├── core/
│   ├── __init__.py
│   ├── config_loader.py          # Merges suite.yaml → resolved AgentConfig
│   ├── registry.py               # Plugin registries: Framework, LLM, Vertical
│   ├── base_agent.py             # Abstract BaseAgent interface
│   ├── base_llm.py               # Abstract BaseLLMProvider interface
│   └── base_framework.py         # Abstract BaseFrameworkAdapter interface
│
├── llm_providers/
│   ├── __init__.py
│   ├── openai_provider.py
│   ├── claude_provider.py
│   ├── gemini_provider.py
│   ├── grok_provider.py
│   └── ollama_provider.py
│
├── frameworks/
│   ├── __init__.py
│   ├── langchain_adapter.py
│   ├── langgraph_adapter.py
│   ├── autogen_adapter.py
│   └── crewai_adapter.py
│
├── shims/                        # 20 enterprise environment simulators
│   ├── __init__.py
│   ├── registry.py               # ShimRegistry with hot-swap support
│   ├── s01_git.py
│   ├── s02_rest_api.py
│   ├── s03_database.py
│   ├── s04_knowledge_base.py
│   ├── s05_support_desk.py
│   ├── s06_social_media.py
│   ├── s07_vector_db.py
│   ├── s08_cicd.py
│   ├── s09_iot.py
│   ├── s10_security.py
│   ├── s11_filesystem.py
│   ├── s12_email.py
│   ├── s13_calendar.py
│   ├── s14_payment.py
│   ├── s15_notification.py
│   ├── s16_search.py
│   ├── s17_analytics.py
│   ├── s18_workflow.py
│   ├── s19_compliance.py
│   └── s20_hitl.py
│
├── verticals/
│   ├── __init__.py
│   ├── fintech/
│   │   ├── __init__.py
│   │   ├── agents/
│   │   │   ├── fraud_detection_agent.py
│   │   │   ├── portfolio_advisor_agent.py
│   │   │   ├── loan_underwriting_agent.py
│   │   │   └── regulatory_reporting_agent.py
│   │   └── scenarios/            # Scenario YAML files (harness-compatible)
│   │       ├── fraud_detection.yaml
│   │       ├── portfolio_rebalance.yaml
│   │       ├── loan_decision.yaml
│   │       └── regulatory_report.yaml
│   │
│   ├── healthcare/
│   │   ├── __init__.py
│   │   ├── agents/
│   │   │   ├── clinical_triage_agent.py
│   │   │   ├── medication_reconciliation_agent.py
│   │   │   ├── prior_auth_agent.py
│   │   │   └── patient_discharge_agent.py
│   │   └── scenarios/
│   │       ├── clinical_triage.yaml
│   │       ├── medication_reconciliation.yaml
│   │       ├── prior_auth.yaml
│   │       └── patient_discharge.yaml
│   │
│   └── telecom/
│       ├── __init__.py
│       ├── agents/
│       │   ├── network_fault_agent.py
│       │   ├── churn_prevention_agent.py
│       │   ├── provisioning_agent.py
│       │   └── sla_monitoring_agent.py
│       └── scenarios/
│           ├── network_fault.yaml
│           ├── churn_prevention.yaml
│           ├── provisioning.yaml
│           └── sla_monitoring.yaml
│
├── server/
│   ├── app.py                    # Flask server — harness-compatible /execute_task endpoint
│   └── middleware.py             # Request validation, logging, error shaping
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── smoke/
│       └── test_all_combos.py    # Verifies all vertical×framework×llm combos boot
│
├── pyproject.toml
├── requirements.txt
├── .env.example
├── Makefile
└── README.md
```

---

## 2 ─ MASTER CONFIGURATION SYSTEM

### `config/suite.yaml` (the single source of truth)

```yaml
# ─── CHANGE EXACTLY ONE OF THESE TO SWITCH THE ENTIRE SUITE ───
active:
  vertical: fintech          # fintech | healthcare | telecom
  framework: langgraph       # langchain | langgraph | autogen | crewai
  llm: claude                # openai | claude | gemini | grok | ollama

server:
  host: "0.0.0.0"
  port: 5001
  endpoint: /execute_task

agent:
  max_turns: 10
  temperature: 0.1
  verbose: true

shims:
  stateful: true             # shims maintain state across turns in a scenario
  seed: 42                   # reproducible shim randomisation
```

### `core/config_loader.py`

```python
"""
Merges suite.yaml with the appropriate vertical/framework/llm YAML,
produces a frozen AgentConfig dataclass used by all components.
No agent code ever reads os.environ directly — only via AgentConfig.
"""

from __future__ import annotations
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict
import yaml


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    model: str
    api_key_env: str  # name of the env var, never the key itself
    base_url: str | None = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentConfig:
    vertical: str
    framework: str
    llm: LLMConfig
    shims_enabled: list[str]
    max_turns: int = 10
    temperature: float = 0.1
    verbose: bool = True
    seed: int = 42


class ConfigLoader:
    CONFIG_DIR = Path(__file__).parent.parent / "config"

    def load(self) -> AgentConfig:
        suite = self._read("suite.yaml")
        active = suite["active"]

        vertical_cfg = self._read(f"verticals/{active['vertical']}.yaml")
        framework_cfg = self._read(f"frameworks/{active['framework']}.yaml")
        llm_cfg_raw = self._read(f"llms/{active['llm']}.yaml")

        llm = LLMConfig(
            provider=active["llm"],
            model=llm_cfg_raw["model"],
            api_key_env=llm_cfg_raw["api_key_env"],
            base_url=llm_cfg_raw.get("base_url"),
            extra=llm_cfg_raw.get("extra", {}),
        )

        return AgentConfig(
            vertical=active["vertical"],
            framework=active["framework"],
            llm=llm,
            shims_enabled=vertical_cfg["shims"],
            max_turns=suite["agent"]["max_turns"],
            temperature=suite["agent"]["temperature"],
            verbose=suite["agent"]["verbose"],
            seed=suite["shims"]["seed"],
        )

    def _read(self, rel: str) -> dict:
        path = self.CONFIG_DIR / rel
        with open(path) as f:
            return yaml.safe_load(f)
```

---

## 3 ─ THE 20 ENTERPRISE SHIMS

Each shim is a **stateful in-process simulator** implementing a common `BaseShim` interface.
Agents call shim methods as if they were real external services — the shims are wired as
LangChain/LangGraph tools, AutoGen functions, or CrewAI tools by the framework adapter.

### `shims/__init__.py` — BaseShim interface

```python
from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseShim(ABC):
    """Common contract for all 20 enterprise shims."""

    name: str  # matches s01_git → "git"
    description: str  # shown to LLM as tool description

    def __init__(self, seed: int = 42):
        self._seed = seed
        self._state: Dict[str, Any] = {}
        self.reset()

    @abstractmethod
    def reset(self) -> None:
        """Re-initialise to a deterministic starting state."""

    def get_state(self) -> Dict[str, Any]:
        return dict(self._state)
```

### Shim Catalogue — implement each file below

| # | File | Name | Description | Key Methods |
|---|------|------|-------------|-------------|
| 1 | `s01_git.py` | `git` | In-memory Git repo with branches, commits, diffs, PRs | `clone`, `commit`, `push`, `create_pr`, `get_diff`, `list_branches` |
| 2 | `s02_rest_api.py` | `rest_api` | Generic HTTP API simulator with configurable response fixtures | `get`, `post`, `put`, `delete`, `patch` |
| 3 | `s03_database.py` | `database` | SQL-like in-memory store (SQLite) with schema per vertical | `query`, `insert`, `update`, `delete`, `schema_describe` |
| 4 | `s04_knowledge_base.py` | `knowledge_base` | Document store with keyword retrieval | `search`, `fetch_doc`, `list_topics` |
| 5 | `s05_support_desk.py` | `support_desk` | Ticket lifecycle (open/update/resolve/escalate) | `create_ticket`, `update_ticket`, `resolve_ticket`, `list_open_tickets` |
| 6 | `s06_social_media.py` | `social_media` | Post/feed/DM simulator | `post`, `fetch_feed`, `send_dm`, `get_mentions` |
| 7 | `s07_vector_db.py` | `vector_db` | In-memory cosine-similarity vector store (numpy) | `upsert`, `query_similar`, `delete`, `list_collections` |
| 8 | `s08_cicd.py` | `cicd` | Pipeline trigger/status/log simulator | `trigger_pipeline`, `get_status`, `get_logs`, `cancel` |
| 9 | `s09_iot.py` | `iot` | Sensor reading & device command simulator | `read_sensor`, `send_command`, `list_devices`, `subscribe_alert` |
| 10 | `s10_security.py` | `security` | Auth, role check, audit log, secret vault | `authenticate`, `check_permission`, `rotate_secret`, `get_audit_log` |
| 11 | `s11_filesystem.py` | `filesystem` | Virtual filesystem (read/write/move/delete) | `read_file`, `write_file`, `list_dir`, `move`, `delete` |
| 12 | `s12_email.py` | `email` | SMTP/IMAP simulator with inbox/sent/drafts | `send_email`, `list_inbox`, `read_email`, `search_emails` |
| 13 | `s13_calendar.py` | `calendar` | Calendar/scheduling with conflicts & reminders | `create_event`, `list_events`, `find_free_slot`, `cancel_event` |
| 14 | `s14_payment.py` | `payment` | Payment gateway (charge/refund/subscription/ledger) | `charge`, `refund`, `create_subscription`, `get_ledger` |
| 15 | `s15_notification.py` | `notification` | Multi-channel alerts (SMS/push/webhook) | `send_sms`, `send_push`, `send_webhook`, `list_sent` |
| 16 | `s16_search.py` | `search` | Web/enterprise search with ranked results | `web_search`, `enterprise_search`, `news_search` |
| 17 | `s17_analytics.py` | `analytics` | Time-series metrics, dashboards, aggregations | `query_metrics`, `create_report`, `get_kpi`, `forecast` |
| 18 | `s18_workflow.py` | `workflow` | BPM/orchestration (start/pause/resume/route) | `start_workflow`, `get_workflow_status`, `complete_task`, `escalate` |
| 19 | `s19_compliance.py` | `compliance` | Policy check, regulatory filing, audit trail | `check_policy`, `file_report`, `get_audit_trail`, `flag_violation` |
| 20 | `s20_hitl.py` | `hitl` | Human-in-the-loop pause/approve/reject | `request_human_review`, `get_review_status`, `submit_human_decision` |

---

## 4 ─ SHIM COMPOSITION PER VERTICAL

### 4.1 Fintech — Active Shims

| Agent | Shims Used (from the 20) | Rationale |
|-------|--------------------------|-----------|
| `fraud_detection_agent` | `rest_api`, `database`, `security`, `analytics`, `notification`, `compliance` | Calls transaction APIs, queries fraud DB, enforces security policy, raises alerts, files SAR |
| `portfolio_advisor_agent` | `rest_api`, `vector_db`, `knowledge_base`, `analytics`, `search`, `hitl` | Retrieves market data, semantic policy search, generates report, escalates to human |
| `loan_underwriting_agent` | `database`, `rest_api`, `compliance`, `workflow`, `hitl`, `email` | Credit bureau calls, policy compliance, multi-step approval workflow, notifies applicant |
| `regulatory_reporting_agent` | `database`, `filesystem`, `compliance`, `email`, `analytics`, `git` | Extracts data, assembles report, versions via git, emails regulator, files compliance record |

**`config/verticals/fintech.yaml`:**
```yaml
name: fintech
display_name: "Financial Services"
shims:
  - rest_api
  - database
  - security
  - analytics
  - notification
  - compliance
  - vector_db
  - knowledge_base
  - search
  - hitl
  - email
  - workflow
  - filesystem
  - git
default_agent: fraud_detection_agent
agents:
  - fraud_detection_agent
  - portfolio_advisor_agent
  - loan_underwriting_agent
  - regulatory_reporting_agent
domain_context: |
  You are an enterprise AI agent in a regulated financial services firm.
  You have access to internal systems via secure APIs. All decisions above
  $50,000 require human approval. Strict PII handling and audit logging apply.
```

### 4.2 Healthcare — Active Shims

| Agent | Shims Used | Rationale |
|-------|-----------|-----------|
| `clinical_triage_agent` | `database`, `knowledge_base`, `iot`, `hitl`, `notification`, `compliance` | Reads vitals (IoT), checks clinical KB, escalates critical cases to clinician |
| `medication_reconciliation_agent` | `database`, `knowledge_base`, `vector_db`, `compliance`, `email`, `hitl` | Checks drug interactions, reconciles med lists, flags ADR risks, notifies pharmacist |
| `prior_auth_agent` | `rest_api`, `workflow`, `compliance`, `email`, `hitl`, `notification` | Submits auth to payer API, tracks workflow state, notifies patient/provider |
| `patient_discharge_agent` | `database`, `calendar`, `workflow`, `notification`, `email`, `filesystem` | Coordinates bed management, schedules follow-ups, sends discharge summary |

**`config/verticals/healthcare.yaml`:**
```yaml
name: healthcare
display_name: "Healthcare & Clinical"
shims:
  - database
  - knowledge_base
  - iot
  - hitl
  - notification
  - compliance
  - vector_db
  - email
  - rest_api
  - workflow
  - calendar
  - filesystem
  - search
default_agent: clinical_triage_agent
agents:
  - clinical_triage_agent
  - medication_reconciliation_agent
  - prior_auth_agent
  - patient_discharge_agent
domain_context: |
  You are a clinical AI assistant operating under HIPAA and clinical safety rules.
  All recommendations must be evidence-based. Any action affecting patient safety
  requires human clinician sign-off. PHI must never appear in logs.
```

### 4.3 Telecom — Active Shims

| Agent | Shims Used | Rationale |
|-------|-----------|-----------|
| `network_fault_agent` | `iot`, `analytics`, `rest_api`, `support_desk`, `notification`, `cicd` | Reads network sensors, detects anomalies, opens trouble ticket, triggers remediation pipeline |
| `churn_prevention_agent` | `database`, `analytics`, `vector_db`, `notification`, `email`, `search` | Identifies at-risk customers, generates retention offer, triggers personalised outreach |
| `provisioning_agent` | `rest_api`, `database`, `workflow`, `notification`, `filesystem`, `cicd` | Automates SIM/service provisioning, coordinates backend workflow, delivers config |
| `sla_monitoring_agent` | `analytics`, `database`, `compliance`, `notification`, `hitl`, `support_desk` | Tracks SLA KPIs, generates breach reports, escalates to account managers |

**`config/verticals/telecom.yaml`:**
```yaml
name: telecom
display_name: "Telecommunications"
shims:
  - iot
  - analytics
  - rest_api
  - support_desk
  - notification
  - cicd
  - database
  - vector_db
  - email
  - search
  - workflow
  - filesystem
  - compliance
  - hitl
default_agent: network_fault_agent
agents:
  - network_fault_agent
  - churn_prevention_agent
  - provisioning_agent
  - sla_monitoring_agent
domain_context: |
  You are a network operations AI in a Tier-1 telecom. You manage millions
  of subscribers and thousands of network nodes. SLA breach triggers immediate
  escalation. All infrastructure changes require a change-approval workflow.
```

---

## 5 ─ LLM PROVIDER ABSTRACTION

### `core/base_llm.py`

```python
from abc import ABC, abstractmethod
from typing import Any, Dict, Generator, List


class BaseLLMProvider(ABC):
    """All LLM providers must implement this interface."""

    def __init__(self, config):  # config: LLMConfig
        self.config = config

    @abstractmethod
    def chat(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict] | None = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Synchronous chat completion. Returns OpenAI-compatible dict."""

    @abstractmethod
    def stream(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict] | None = None,
        **kwargs,
    ) -> Generator[str, None, None]:
        """Streaming token-by-token generator."""

    @property
    @abstractmethod
    def supports_tool_calling(self) -> bool:
        """Whether this provider supports native tool/function calling."""
```

### LLM Config Files

**`config/llms/openai.yaml`**
```yaml
model: gpt-4o
api_key_env: OPENAI_API_KEY
extra:
  organization_env: OPENAI_ORG_ID   # optional
```

**`config/llms/claude.yaml`**
```yaml
model: claude-sonnet-4-20250514
api_key_env: ANTHROPIC_API_KEY
```

**`config/llms/gemini.yaml`**
```yaml
model: gemini-2.0-flash
api_key_env: GOOGLE_API_KEY
base_url: https://generativelanguage.googleapis.com/v1beta
```

**`config/llms/grok.yaml`**
```yaml
model: grok-3
api_key_env: XAI_API_KEY
base_url: https://api.x.ai/v1
extra:
  openai_compat: true   # xAI exposes an OpenAI-compatible endpoint
```

**`config/llms/ollama.yaml`**
```yaml
model: llama3.3:70b    # override with OLLAMA_MODEL env var
api_key_env: OLLAMA_API_KEY   # set to "ollama" locally
base_url: http://localhost:11434
extra:
  openai_compat: true   # Ollama exposes OpenAI-compatible /v1 endpoint
```

### Provider Implementations

Each file in `llm_providers/` follows this skeleton:

```python
# llm_providers/claude_provider.py
import os
import anthropic
from core.base_llm import BaseLLMProvider


class ClaudeProvider(BaseLLMProvider):
    """Anthropic Claude via the official SDK."""

    def __init__(self, config):
        super().__init__(config)
        self._client = anthropic.Anthropic(api_key=os.environ[config.api_key_env])

    def chat(self, messages, tools=None, **kwargs):
        # Convert OpenAI-style messages to Anthropic format
        # Strip system message from list and pass as system=
        system_msg = next(
            (m["content"] for m in messages if m["role"] == "system"), None
        )
        user_msgs = [m for m in messages if m["role"] != "system"]
        resp = self._client.messages.create(
            model=self.config.model,
            max_tokens=4096,
            system=system_msg or "",
            messages=user_msgs,
            tools=tools or [],
        )
        # Normalise to OpenAI-compatible dict
        return {
            "choices": [
                {"message": {"role": "assistant", "content": resp.content[0].text}}
            ]
        }

    def stream(self, messages, tools=None, **kwargs):
        # Implement streaming via resp.stream()
        ...

    @property
    def supports_tool_calling(self):
        return True
```

> **Note:** Implement `openai_provider.py` via `openai` SDK, `gemini_provider.py` via
> `google-generativeai` SDK, and `grok_provider.py` + `ollama_provider.py` via the
> `openai` SDK pointed at the respective `base_url` (both expose OpenAI-compatible APIs).

### `core/registry.py` — LLM Provider Registry

```python
from typing import Type, Dict
from core.base_llm import BaseLLMProvider


_LLM_REGISTRY: Dict[str, Type[BaseLLMProvider]] = {}


def register_llm(name: str):
    """Decorator. Usage: @register_llm("ollama")"""

    def decorator(cls: Type[BaseLLMProvider]):
        _LLM_REGISTRY[name] = cls
        return cls

    return decorator


def get_llm_provider(name: str, config) -> BaseLLMProvider:
    if name not in _LLM_REGISTRY:
        raise ValueError(
            f"LLM provider '{name}' not registered. Available: {list(_LLM_REGISTRY)}"
        )
    return _LLM_REGISTRY[name](config)


# ── Adding a NEW LLM in future ─────────────────────────────────────────────
# 1. Create llm_providers/my_new_llm_provider.py
# 2. Decorate class with @register_llm("my_new_llm")
# 3. Add config/llms/my_new_llm.yaml
# 4. Import the module in llm_providers/__init__.py
# That is ALL. Zero changes to agent or framework code.
```

---

## 6 ─ FRAMEWORK ADAPTER LAYER

### `core/base_framework.py`

```python
from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseFrameworkAdapter(ABC):
    """
    Translates a list of shim tool-specs and an LLM provider into a
    runnable agent object. The returned agent exposes a single .run(task) method.
    """

    def __init__(self, llm_provider, shim_tools: List[Any], config):
        self.llm = llm_provider
        self.shim_tools = shim_tools
        self.config = config

    @abstractmethod
    def build_agent(self, system_prompt: str) -> "RunnableAgent":
        """Construct and return a framework-specific agent ready to .run()."""
```

### Framework Adapter Skeletons

#### `frameworks/langchain_adapter.py`
```python
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from core.base_framework import BaseFrameworkAdapter
from core.registry import register_framework


@register_framework("langchain")
class LangChainAdapter(BaseFrameworkAdapter):
    def build_agent(self, system_prompt: str):
        from langchain_core.tools import StructuredTool

        lc_tools = [
            StructuredTool.from_function(
                func=shim_fn,
                name=shim_name,
                description=shim_desc,
            )
            for shim_name, shim_fn, shim_desc in self.shim_tools
        ]
        # Wrap self.llm in a LangChain-compatible ChatModel
        lc_llm = _wrap_llm_for_langchain(self.llm)
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                ("placeholder", "{chat_history}"),
                ("human", "{input}"),
                ("placeholder", "{agent_scratchpad}"),
            ]
        )
        agent = create_tool_calling_agent(lc_llm, lc_tools, prompt)
        return AgentExecutor(agent=agent, tools=lc_tools, verbose=self.config.verbose)
```

#### `frameworks/langgraph_adapter.py`
```python
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from core.base_framework import BaseFrameworkAdapter
from core.registry import register_framework


@register_framework("langgraph")
class LangGraphAdapter(BaseFrameworkAdapter):
    def build_agent(self, system_prompt: str):
        # Build a ReAct-style graph: llm_node ↔ tool_node loop
        from typing import TypedDict, Annotated, Sequence
        import operator

        class AgentState(TypedDict):
            messages: Annotated[Sequence, operator.add]

        lc_llm = _wrap_llm_for_langchain(self.llm).bind_tools(self._lc_tools())
        tool_node = ToolNode(self._lc_tools())

        graph = StateGraph(AgentState)
        graph.add_node(
            "llm", lambda state: {"messages": [lc_llm.invoke(state["messages"])]}
        )
        graph.add_node("tools", tool_node)
        graph.set_entry_point("llm")
        graph.add_conditional_edges(
            "llm", _should_call_tools, {"tools": "tools", "end": END}
        )
        graph.add_edge("tools", "llm")
        return graph.compile()
```

#### `frameworks/autogen_adapter.py`
```python
import autogen
from core.base_framework import BaseFrameworkAdapter
from core.registry import register_framework


@register_framework("autogen")
class AutoGenAdapter(BaseFrameworkAdapter):
    def build_agent(self, system_prompt: str):
        llm_cfg = _build_autogen_llm_config(self.llm.config)
        assistant = autogen.AssistantAgent(
            name="VerticalAgent",
            system_message=system_prompt,
            llm_config=llm_cfg,
            function_map={name: fn for name, fn, _ in self.shim_tools},
        )
        user_proxy = autogen.UserProxyAgent(
            name="Orchestrator",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=self.config.max_turns,
            function_map={name: fn for name, fn, _ in self.shim_tools},
        )
        return _AutoGenRunnable(assistant, user_proxy)
```

#### `frameworks/crewai_adapter.py`
```python
from crewai import Agent, Task, Crew, Process
from crewai.tools import tool as crewai_tool
from core.base_framework import BaseFrameworkAdapter
from core.registry import register_framework


@register_framework("crewai")
class CrewAIAdapter(BaseFrameworkAdapter):
    def build_agent(self, system_prompt: str):
        tools = [
            crewai_tool(name=name, description=desc)(fn)
            for name, fn, desc in self.shim_tools
        ]
        agent = Agent(
            role="Domain Expert",
            goal=system_prompt,
            backstory=system_prompt,
            tools=tools,
            llm=_wrap_llm_for_crewai(self.llm),
            verbose=self.config.verbose,
        )
        return _CrewAIRunnable(agent)
```

> **Adding a NEW Framework:**
> 1. Create `frameworks/my_framework_adapter.py`
> 2. Decorate class with `@register_framework("my_framework")`
> 3. Add `config/frameworks/my_framework.yaml`
> 4. Import in `frameworks/__init__.py`
> 5. Zero other changes required.

---

## 7 ─ VERTICAL AGENT IMPLEMENTATIONS

### 7.1 Abstract Base Agent

```python
# core/base_agent.py
from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseAgent(ABC):
    """
    All vertical agents inherit from this.
    They know nothing about the harness — they are production enterprise agents.
    """

    def __init__(self, framework_agent, shims: Dict[str, Any], config):
        self._agent = framework_agent
        self._shims = shims
        self._config = config

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Domain-specific system prompt. Rich, authentic, no harness references."""

    @abstractmethod
    def get_tools(self) -> list:
        """Return the specific subset of shim tool specs this agent uses."""

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Entry point called by the Flask server.
        task = {"task_id": str, "input": str, "context": dict}
        Returns {"response": str, "tool_calls": list, "status": str}
        """
        ...
```

### 7.2 Example — Fintech: Fraud Detection Agent

```python
# verticals/fintech/agents/fraud_detection_agent.py
"""
Real-world enterprise fraud detection agent.
Monitors transactions, applies ML risk scoring, files SARs, notifies compliance.
Zero awareness of any evaluation harness.
"""

from core.base_agent import BaseAgent
from core.registry import register_agent


@register_agent("fintech", "fraud_detection_agent")
class FraudDetectionAgent(BaseAgent):
    @property
    def system_prompt(self) -> str:
        return """You are an AI-powered Fraud Detection Specialist at a global bank.

Your responsibilities:
- Monitor real-time transaction streams for anomalous patterns
- Cross-reference flagged transactions against known fraud typologies
- Apply regulatory thresholds (BSA/AML, FinCEN rules, Reg E)
- Escalate high-risk cases to human compliance officers
- File Suspicious Activity Reports (SARs) for confirmed fraud
- Maintain a complete audit trail of all decisions

Decision framework:
- Risk score ≥ 0.85 → Auto-block + immediate SAR filing
- Risk score 0.65–0.85 → Flag for human review (HITL)
- Risk score < 0.65 → Log and monitor

Tools at your disposal: transaction database, fraud analytics engine,
compliance policy checker, notification system, regulatory filing system,
and human review escalation channel.

Always explain your reasoning. Always cite which rule or pattern triggered
each decision. Never approve a transaction you cannot justify."""

    def get_tools(self) -> list:
        # Uses 6 of the 20 shims: database, rest_api, analytics,
        # compliance, notification, hitl
        return [
            (
                "query_transactions",
                self._shims["database"].query,
                "Query the transaction database. Args: sql_query (str)",
            ),
            (
                "get_transaction_risk_score",
                self._shims["rest_api"].get,
                "GET risk score from fraud scoring API. Args: endpoint (str)",
            ),
            (
                "run_fraud_analytics",
                self._shims["analytics"].query_metrics,
                "Run pattern analysis. Args: metric_name (str), filters (dict)",
            ),
            (
                "check_compliance_policy",
                self._shims["compliance"].check_policy,
                "Validate action against AML/BSA policy. Args: action (str), context (dict)",
            ),
            (
                "file_sar_report",
                self._shims["compliance"].file_report,
                "File a Suspicious Activity Report. Args: transaction_id (str), details (dict)",
            ),
            (
                "send_alert",
                self._shims["notification"].send_webhook,
                "Send alert to compliance team. Args: channel (str), message (str)",
            ),
            (
                "escalate_to_human",
                self._shims["hitl"].request_human_review,
                "Escalate to human compliance officer. Args: case_id (str), summary (str)",
            ),
        ]
```

### 7.3 Example — Healthcare: Clinical Triage Agent

```python
# verticals/healthcare/agents/clinical_triage_agent.py
"""
Clinical AI triage agent for emergency department.
Reads vitals, assesses acuity, routes patients, escalates critical cases.
Operates under HIPAA and clinical safety protocols.
"""

from core.base_agent import BaseAgent
from core.registry import register_agent


@register_agent("healthcare", "clinical_triage_agent")
class ClinicalTriageAgent(BaseAgent):
    @property
    def system_prompt(self) -> str:
        return """You are a Clinical Decision Support AI assisting ED triage nurses.

Your responsibilities:
- Read and interpret patient vital signs from bedside monitors
- Apply the Emergency Severity Index (ESI) 1–5 triage scale
- Cross-reference symptoms against clinical knowledge base (UpToDate, CDC)
- Flag sepsis, STEMI, stroke, and trauma alerts immediately
- Route patients to appropriate care area
- Escalate ESI-1 and ESI-2 cases to attending physician immediately

Clinical decision rules you follow:
- SIRS criteria for sepsis: Temp >38°C or <36°C, HR >90, RR >20, WBC >12k or <4k
- STEMI: chest pain + ST elevation in ≥2 contiguous leads
- Stroke: FAST protocol (Face, Arms, Speech, Time)

You MUST request human physician review before any ESI-1 determination.
Never guess; always cite the clinical evidence base for your assessment.
PHI must not appear in system logs — use patient_id only."""

    def get_tools(self) -> list:
        # Uses 6 shims: iot, database, knowledge_base, hitl, notification, compliance
        return [
            (
                "read_vitals",
                self._shims["iot"].read_sensor,
                "Read patient vitals from bedside monitor. Args: device_id (str)",
            ),
            (
                "query_patient_record",
                self._shims["database"].query,
                "Query EHR for patient history. Args: sql_query (str)",
            ),
            (
                "search_clinical_evidence",
                self._shims["knowledge_base"].search,
                "Search clinical knowledge base. Args: query (str), top_k (int)",
            ),
            (
                "check_hipaa_compliance",
                self._shims["compliance"].check_policy,
                "Verify action is HIPAA compliant. Args: action (str), context (dict)",
            ),
            (
                "request_physician_review",
                self._shims["hitl"].request_human_review,
                "Escalate to attending physician. Args: patient_id (str), acuity (str), summary (str)",
            ),
            (
                "send_clinical_alert",
                self._shims["notification"].send_push,
                "Send alert to clinical team. Args: team (str), message (str), priority (str)",
            ),
        ]
```

### 7.4 Example — Telecom: Network Fault Agent

```python
# verticals/telecom/agents/network_fault_agent.py
"""
Network Operations Center AI agent.
Detects, diagnoses, and remediates network faults autonomously.
Triggers change-management workflows for infrastructure changes.
"""

from core.base_agent import BaseAgent
from core.registry import register_agent


@register_agent("telecom", "network_fault_agent")
class NetworkFaultAgent(BaseAgent):
    @property
    def system_prompt(self) -> str:
        return """You are an autonomous Network Operations AI for a Tier-1 carrier.

Your responsibilities:
- Continuously monitor network node health via sensor telemetry
- Detect fault patterns: packet loss >0.1%, latency >50ms, BER >1e-6
- Classify faults: hardware failure, config drift, capacity exhaustion, external
- Execute L1/L2 remediation autonomously within change-approval policy
- Open and update NOC trouble tickets
- Trigger automated remediation pipelines for known fault signatures
- Escalate novel or customer-impacting faults to NOC engineers

Escalation triggers:
- Customer-impacting outage (>100 subscribers affected)
- P1 SLA breach imminent (<15 min to breach)
- Unknown fault signature not in runbook
- Failed automated remediation after 2 attempts

You must always open a trouble ticket before taking any remediation action.
All infrastructure changes require change-approval workflow sign-off."""

    def get_tools(self) -> list:
        # Uses 6 shims: iot, analytics, rest_api, support_desk, notification, cicd
        return [
            (
                "read_network_telemetry",
                self._shims["iot"].read_sensor,
                "Read telemetry from network node. Args: node_id (str), metric (str)",
            ),
            (
                "analyse_fault_pattern",
                self._shims["analytics"].query_metrics,
                "Analyse metric for fault pattern. Args: metric_name (str), window (str)",
            ),
            (
                "query_network_inventory",
                self._shims["rest_api"].get,
                "Query network inventory API. Args: endpoint (str), params (dict)",
            ),
            (
                "create_trouble_ticket",
                self._shims["support_desk"].create_ticket,
                "Open NOC trouble ticket. Args: title (str), severity (str), details (dict)",
            ),
            (
                "update_trouble_ticket",
                self._shims["support_desk"].update_ticket,
                "Update existing ticket. Args: ticket_id (str), update (dict)",
            ),
            (
                "trigger_remediation_pipeline",
                self._shims["cicd"].trigger_pipeline,
                "Trigger automated remediation. Args: pipeline_id (str), params (dict)",
            ),
            (
                "send_noc_alert",
                self._shims["notification"].send_webhook,
                "Alert NOC team. Args: severity (str), message (str)",
            ),
        ]
```

---

## 8 ─ FLASK SERVER (HARNESS-COMPATIBLE ENDPOINT)

```python
# server/app.py
"""
Exposes the active agent via HTTP at /execute_task.
Compatible with standard agent evaluation execution contracts.
This server knows about the config layer but the agents themselves do not.
"""

from flask import Flask, request, jsonify
from core.config_loader import ConfigLoader
from core.registry import get_llm_provider, get_framework_adapter, get_agent
from shims.registry import ShimRegistry

app = Flask(__name__)

# ── Boot sequence ────────────────────────────────────────────────────────────
config = ConfigLoader().load()
shim_registry = ShimRegistry(config.shims_enabled, seed=config.seed)
llm_provider = get_llm_provider(config.llm.provider, config.llm)
agent_cls = get_agent(config.vertical, config.active_agent)
agent_instance = agent_cls(
    framework_agent=None,  # built lazily
    shims=shim_registry.get_all(),
    config=config,
)
tool_specs = agent_instance.get_tools()
framework = get_framework_adapter(config.framework, llm_provider, tool_specs, config)
runnable = framework.build_agent(agent_instance.system_prompt)
agent_instance._agent = runnable  # wire the built agent back


@app.route("/execute_task", methods=["POST"])
def execute_task():
    """
    Harness-compatible endpoint.
    Input:  {"task_id": str, "input": str, "context": dict}
    Output: {"response": str, "tool_calls": list, "status": str}
    """
    payload = request.get_json(force=True)
    try:
        result = agent_instance.execute(payload)
        return jsonify(result), 200
    except Exception as exc:
        return jsonify({"response": str(exc), "tool_calls": [], "status": "error"}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify(
        {
            "status": "ok",
            "vertical": config.vertical,
            "framework": config.framework,
            "llm": config.llm.provider,
            "model": config.llm.model,
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
```

---

## 9 ─ DEPENDENCY & BUILD SETUP

### `requirements.txt`

```
# Core
flask>=3.1
pyyaml>=6.0
python-dotenv>=1.0

# LLM SDKs
openai>=1.75              # covers OpenAI, Grok (openai-compat), Ollama (openai-compat)
anthropic>=0.50
google-generativeai>=0.8

# Framework SDKs
langchain>=0.3
langchain-openai>=0.3
langchain-anthropic>=0.3
langchain-google-genai>=2.0
langgraph>=0.3
pyautogen>=0.9
crewai>=0.80

# Shim internals
numpy>=1.26              # s07_vector_db cosine similarity
```

### `pyproject.toml`

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "agent-test-suite"
version = "1.0.0"
description = "Multi-vertical agentic test suite for enterprise AI agents"
requires-python = ">=3.10"

[project.scripts]
agent-suite = "server.app:main"

[tool.setuptools.packages.find]
where = ["."]
```

### `.env.example`

```bash
# LLM API Keys (set only the ones you need)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...
XAI_API_KEY=xai-...
OLLAMA_API_KEY=ollama                  # literal string "ollama" for local

# Optional overrides (all have defaults in suite.yaml)
ACTIVE_VERTICAL=fintech                # fintech | healthcare | telecom
ACTIVE_FRAMEWORK=langgraph             # langchain | langgraph | autogen | crewai
ACTIVE_LLM=claude                      # openai | claude | gemini | grok | ollama
ACTIVE_AGENT=fraud_detection_agent     # agent within the vertical
OLLAMA_MODEL=llama3.3:70b              # override Ollama model
OLLAMA_BASE_URL=http://localhost:11434
```

### `Makefile`

```makefile
.PHONY: run test lint smoke install

install:
	pip install -e .
	pip install -r requirements.txt

run:
	python server/app.py

run-fintech-claude-langgraph:
	ACTIVE_VERTICAL=fintech ACTIVE_FRAMEWORK=langgraph ACTIVE_LLM=claude python server/app.py

run-healthcare-openai-crewai:
	ACTIVE_VERTICAL=healthcare ACTIVE_FRAMEWORK=crewai ACTIVE_LLM=openai python server/app.py

run-telecom-gemini-autogen:
	ACTIVE_VERTICAL=telecom ACTIVE_FRAMEWORK=autogen ACTIVE_LLM=gemini python server/app.py

smoke:
	pytest tests/smoke/ -v

test:
	pytest tests/ -v

lint:
	ruff check . && mypy core/ verticals/ shims/
```

---

## 10 ─ EXTENSIBILITY CONTRACT

### Adding a New Vertical (e.g., `insurance`)

1. `mkdir -p verticals/insurance/agents verticals/insurance/scenarios`
2. Implement agent classes inheriting `BaseAgent`, decorated with `@register_agent("insurance", "...")`
3. Add `config/verticals/insurance.yaml` with `shims:` list and `agents:` list
4. Set `active.vertical: insurance` in `suite.yaml`
5. **Zero changes** to `core/`, `shims/`, `frameworks/`, or `server/`

### Adding a New Framework (e.g., `smolagents`)

1. Create `frameworks/smolagents_adapter.py`
2. Implement `BaseFrameworkAdapter`, decorate with `@register_framework("smolagents")`
3. Add `config/frameworks/smolagents.yaml`
4. Import in `frameworks/__init__.py`
5. Set `active.framework: smolagents` in `suite.yaml`

### Adding a New LLM (e.g., `mistral`)

1. Create `llm_providers/mistral_provider.py`
2. Implement `BaseLLMProvider`, decorate with `@register_llm("mistral")`
3. Add `config/llms/mistral.yaml`
4. Import in `llm_providers/__init__.py`
5. Set `active.llm: mistral` in `suite.yaml`

### Adding a New Shim (e.g., `s21_blockchain.py`)

1. Create `shims/s21_blockchain.py`, implement `BaseShim`
2. Register in `shims/registry.py`
3. Add `blockchain` to any vertical YAML's `shims:` list
4. Reference in agent's `get_tools()` as `self._shims["blockchain"]`

---

## 11 ─ SMOKE TEST — ALL COMBOS

```python
# tests/smoke/test_all_combos.py
"""
Verifies every vertical × framework × LLM combination can:
1. Boot without import errors
2. Expose a healthy /health endpoint
3. Accept and respond to a minimal task payload

Does NOT call real LLMs — uses a MockLLMProvider.
"""

import itertools
import pytest
import requests
from unittest.mock import patch

VERTICALS = ["fintech", "healthcare", "telecom"]
FRAMEWORKS = ["langchain", "langgraph", "autogen", "crewai"]
LLMS = ["openai", "claude", "gemini", "grok", "ollama"]


@pytest.mark.parametrize(
    "vertical,framework,llm", itertools.product(VERTICALS, FRAMEWORKS, LLMS)
)
def test_combo_boots(vertical, framework, llm, mock_llm_provider):
    """Each combination must load config and instantiate an agent without error."""
    from core.config_loader import ConfigLoader
    from core.registry import get_agent, get_framework_adapter

    with patch(
        "core.config_loader.ConfigLoader._read",
        side_effect=_config_override(vertical, framework, llm),
    ):
        config = ConfigLoader().load()
        agent_cls = get_agent(config.vertical, "default")
        assert agent_cls is not None

    # Health-check the running server (requires server to be up)
    # resp = requests.get("http://localhost:5001/health")
    # assert resp.json()["vertical"] == vertical
```

---

## 12 ─ SCENARIO YAML FORMAT (Harness-Compatible)

Each scenario YAML under `verticals/<v>/scenarios/` must be valid per the harness JSON Schema.

```yaml
# verticals/fintech/scenarios/fraud_detection.yaml
id: fin_fraud_001
title: "High-Value Wire Transfer — Possible Account Takeover"
industry: fintech
agent: fraud_detection_agent
difficulty: hard
max_turns: 8

context:
  account_id: ACC-7829134
  customer_tier: premium
  recent_logins:
    - ip: "185.220.101.42"   # known Tor exit node
      timestamp: "2025-11-01T02:14:00Z"
  transaction:
    id: TXN-9984421
    amount: 148500.00
    currency: USD
    destination: "IBAN DE89370400440532013000"
    channel: online_banking

turns:
  - role: user
    content: |
      Analyse transaction TXN-9984421 on account ACC-7829134.
      The customer is requesting an urgent international wire.
      Assess fraud risk and take appropriate action.

expected_tool_calls:
  - query_transactions
  - get_transaction_risk_score
  - check_compliance_policy

success_criteria:
  - "SAR filed OR human escalation triggered for risk score >= 0.85"
  - "Audit trail recorded"
  - "Customer notified of transaction hold"

metrics:
  - accuracy
  - compliance_adherence
  - tool_call_efficiency
  - escalation_correctness
```

---

## 13 ─ IMPLEMENTATION CHECKLIST

Build in this exact order:

- [ ] **Phase 1 — Foundation**
  - [ ] `core/config_loader.py` + all YAML configs
  - [ ] `core/registry.py` (LLM + Framework + Agent registries)
  - [ ] `shims/__init__.py` (BaseShim)
  - [ ] All 20 shim files with deterministic `reset()` + realistic state
  - [ ] `shims/registry.py` (ShimRegistry)

- [ ] **Phase 2 — LLM Providers**
  - [ ] `core/base_llm.py`
  - [ ] All 5 LLM providers + unit tests

- [ ] **Phase 3 — Framework Adapters**
  - [ ] `core/base_framework.py`
  - [ ] All 4 framework adapters + unit tests

- [ ] **Phase 4 — Vertical Agents**
  - [ ] `core/base_agent.py`
  - [ ] All 12 agent implementations (4 per vertical)
  - [ ] Scenario YAML files (16 total, 4 per vertical × vertical)

- [ ] **Phase 5 — Server + Integration**
  - [ ] `server/app.py` + `server/middleware.py`
  - [ ] End-to-end integration test per vertical

- [ ] **Phase 6 — Smoke + Docs**
  - [ ] `tests/smoke/test_all_combos.py`
  - [ ] `README.md` with quickstart and one-line swap instructions

---

## 14 ─ QUALITY GATES

| Gate | Standard |
|------|----------|
| Type safety | `mypy --strict` passes on `core/` and all shims |
| Linting | `ruff check .` zero errors |
| Shim determinism | Same `seed` → identical shim state across runs |
| Agent blindness | `grep -r "eval_harness\|EvaluationContext\|eval-runner" verticals/` → no matches |
| Config isolation | `grep -r "os.environ" verticals/ shims/` → no matches (env only via AgentConfig) |
| Swap test | `ACTIVE_LLM=ollama ACTIVE_FRAMEWORK=autogen ACTIVE_VERTICAL=healthcare make run` boots in <5s |
| Combo coverage | Smoke suite passes for all 3×4×5=60 combinations with MockLLMProvider |

---

## 15 ─ CODING STYLE & CONVENTIONS

- **Python 3.10+** — use `match/case`, `X | Y` union types, `@dataclass(frozen=True)`
- **No global state** — everything flows through `AgentConfig` or constructor injection
- **Shim methods** must be pure functions of `self._state` — side-effect free from caller POV
- **Docstrings** on every public class and method — these become LLM tool descriptions
- **No `print()`** — use `logging` with `config.verbose` gate
- **Secrets** — only accessed via `os.environ[config.llm.api_key_env]` in provider constructors
- **Error taxonomy** — `ShimError`, `LLMProviderError`, `AgentExecutionError` — never bare `Exception`

---

*End of Antigravity Prompt. Begin implementation from Phase 1.*
