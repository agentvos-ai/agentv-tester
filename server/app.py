# ruff: noqa: F401
import os
import sys
import warnings

# Automatic Path Injection: Ensure project root is in sys.path for direct execution
from pathlib import Path

root_dir = Path(__file__).parent.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

from typing import Any

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from core.base_llm import FallbackLLMProvider
from core.config_loader import ConfigLoader
from core.registry import (
    get_agent_class,
    get_framework_adapter,
    get_llm_provider,
    list_frameworks,
    list_llms,
)
from server.middleware import setup_middleware
from shims.registry import ShimRegistry

# Capture explicit CLI environment variables set before loading .env
cli_envs = {k: os.environ[k] for k in os.environ if k.startswith("ACTIVE_")}

# Load environment variables from .env if present
load_dotenv()

# Environment Audit & Purge: Ensure YAML priority by clearing persistent overrides
if cli_envs:
    # Persist the environment overrides into suite.yaml on startup
    config_path = Path(__file__).parent.parent / "config" / "suite.yaml"
    import yaml

    try:
        with open(config_path, "r") as f:
            suite = yaml.safe_load(f) or {}
    except Exception:
        suite = {}

    if "active" not in suite:
        suite["active"] = {}

    for k, v in cli_envs.items():
        sys.stderr.write(f"APPLYING ENV OVERRIDE TO CONFIG: {k}={v}\n")
        # Map ACTIVE_VERTICAL -> vertical, ACTIVE_FRAMEWORK -> framework, ACTIVE_LLM -> llm
        config_key = k.replace("ACTIVE_", "").lower()
        suite["active"][config_key] = v

    try:
        with open(config_path, "w") as f:
            yaml.dump(suite, f, default_flow_style=False)
    except Exception as e:
        sys.stderr.write(f"Failed to persist env overrides to suite.yaml: {e}\n")

# Now purge any ACTIVE_ variables from os.environ so they do not override /update_config on reload
for k in list(os.environ.keys()):
    if k.startswith("ACTIVE_"):
        sys.stderr.write(f"PURGING ENV OVERRIDE: {k}={os.environ[k]}\n")
        del os.environ[k]

# Suppress noisy upstream deprecations for a clean evaluation environment
warnings.filterwarnings("ignore", category=DeprecationWarning, module="google.genai")
warnings.filterwarnings("ignore", category=UserWarning, module="langchain")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="jsonschema")

# Ensure all plugins are registered by importing their packages
import frameworks as _frameworks
import llm_providers as _llm_providers
import shims as _shims
import verticals.construction.agents as _construction_agents

# Vertical Agents: Trigger registration for all industrial domains
import verticals.fintech.agents as _fintech_agents
import verticals.healthcare.agents as _healthcare_agents
import verticals.telecom.agents as _telecom_agents


def get_config() -> Any:
    """Helper to load the latest config, supporting live reloads."""
    config_path = os.environ.get("SUITE_CONFIG", "suite.yaml")
    return ConfigLoader.load(config_path)


def create_app() -> Flask:
    app = Flask(__name__)
    setup_middleware(app)

    @app.route("/execute_task", methods=["POST"])
    def execute_task():
        """
        The primary endpoint for the external caller.
        Expects: {"task_id": str, "agent": str, "input": str, "context": dict}
        """
        config = get_config()
        data = request.json
        if not data:
            return jsonify(
                {"status": "error", "message": "No JSON payload provided"}
            ), 400

        # Dimension 1: LLM (Loaded per request for config flexibility)
        active_llm_cfg = config.llms[config.active_llm]

        def instantiate_provider(name, cfg):
            cls = get_llm_provider(name)
            return cls(cfg)

        try:
            llm = instantiate_provider(config.active_llm, active_llm_cfg)
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(
                f"Failed to instantiate primary LLM {config.active_llm}: {e!s}"
            )
            if not active_llm_cfg.fallbacks:
                raise
            llm = None

        # Apply fallback logic if configured
        if active_llm_cfg.fallbacks:
            fallbacks = []
            for f_name in active_llm_cfg.fallbacks:
                try:
                    f_cfg = config.llms[f_name]
                    fallbacks.append(instantiate_provider(f_name, f_cfg))
                except Exception as e:
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.warning(
                        f"Failed to instantiate fallback LLM {f_name}: {e!s}"
                    )

            if llm is None:
                if not fallbacks:
                    raise Exception(
                        "Primary and all fallback LLMs failed to instantiate."
                    )
                llm = FallbackLLMProvider(primary=fallbacks[0], fallbacks=fallbacks[1:])
            else:
                llm = FallbackLLMProvider(primary=llm, fallbacks=fallbacks)

        # Dimension 2: Vertical/Shims (Isolated per request)
        active_vertical = config.verticals[config.active_vertical]
        shim_registry = ShimRegistry(enabled_shims=active_vertical.shims)
        shim_registry.reset_all()

        try:
            # Dynamically load the agent class
            agent_name = data.get("agent", active_vertical.agents[0])
            agent_cls = get_agent_class(agent_name)

            # Step 1: Create agent with a dummy framework to discover tools
            # (In a real industrial app, we'd use a classmethod for tools)
            temp_agent = agent_cls(config, None, shim_registry.shims)
            required_tools = temp_agent.get_tool_specs()

            # Dimension 3: Framework (Wired to ONLY the tools the agent requested)
            framework_cls = get_framework_adapter(config.active_framework)
            framework = framework_cls(llm, required_tools, config)

            # Step 2: Inject the real framework back into the agent
            temp_agent.framework = framework

            # Execute
            result = temp_agent.execute(data)
            return jsonify(result)
        finally:
            if "temp_agent" in locals() and hasattr(temp_agent, "close"):
                try:
                    temp_agent.close()
                except Exception as e:
                    import logging

                    logging.getLogger(__name__).warning(f"Error closing agent: {e}")
            shim_registry.shutdown_all()

    @app.route("/health", methods=["GET"])
    def health():
        config = get_config()
        active_vert = config.verticals[config.active_vertical]
        return jsonify(
            {
                "status": "healthy",
                "active_llm": config.active_llm,
                "active_framework": config.active_framework,
                "active_vertical": {
                    "name": config.active_vertical,
                    "agents": active_vert.agents,
                    "scenarios": active_vert.scenarios,
                },
            }
        )

    @app.route("/", methods=["GET"])
    def index():
        """Render the premium interactive UI with active state and options."""
        config = get_config()
        active_vert = config.verticals[config.active_vertical]

        # Get all options for dropdowns
        all_llms = list_llms()
        all_frameworks = list_frameworks()

        # List verticals by scanning config directory
        verticals_dir = Path(__file__).parent.parent / "config" / "verticals"
        all_verticals = [f.stem for f in verticals_dir.glob("*.yaml")]

        # Load scenario details from YAML files
        scenarios = []
        scenarios_dir = (
            Path(__file__).parent.parent
            / "verticals"
            / config.active_vertical
            / "scenarios"
        )
        import yaml

        for scenario_name in active_vert.scenarios:
            scenario_path = scenarios_dir / f"{scenario_name}.yaml"
            if scenario_path.exists():
                try:
                    with open(scenario_path, "r", encoding="utf-8") as f:
                        s_data = yaml.safe_load(f)
                        scenarios.append(
                            {
                                "id": s_data.get("task_id", scenario_name),
                                "input": s_data.get("input", ""),
                                "context": s_data.get("context", {}),
                            }
                        )
                except Exception as e:
                    import logging

                    logging.getLogger(__name__).warning(
                        f"Failed to load scenario {scenario_name}: {e}"
                    )

        return render_template(
            "index.html",
            agents=active_vert.agents,
            active_llm=config.active_llm,
            active_framework=config.active_framework,
            active_vertical=config.active_vertical,
            all_llms=all_llms,
            all_frameworks=all_frameworks,
            all_verticals=all_verticals,
            scenarios=scenarios,
        )

    @app.route("/update_config", methods=["POST"])
    def update_config():
        """Update the active configuration dimensions."""
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400

        # Validate keys
        valid_keys = ["vertical", "framework", "llm"]
        updates = {k: v for k, v in data.items() if k in valid_keys}

        if not updates:
            return jsonify(
                {"status": "error", "message": "No valid configuration keys provided"}
            ), 400

        # Update suite.yaml to persist changes (follows Master Configuration pattern)
        config_path = Path(__file__).parent.parent / "config" / "suite.yaml"
        import yaml

        with open(config_path, "r") as f:
            suite = yaml.safe_load(f)

        if "active" not in suite:
            suite["active"] = {}

        for k, v in updates.items():
            suite["active"][k] = v

        with open(config_path, "w") as f:
            yaml.dump(suite, f, default_flow_style=False)

        return jsonify(
            {"status": "success", "message": "Configuration updated and reloaded"}
        )

    @app.route("/favicon.ico")
    def favicon():
        """Handle noisy favicon requests gracefully."""
        return "", 204

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
