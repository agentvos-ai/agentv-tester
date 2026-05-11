# ruff: noqa: E402, F401
import os
import sys
import warnings
# Automatic Path Injection: Ensure project root is in sys.path for direct execution
from pathlib import Path
import sys
root_dir = Path(__file__).parent.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

from core.config_loader import ConfigLoader
from typing import Any
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

from core.registry import (
    get_llm_provider,
    get_framework_adapter,
    get_agent_class,
    list_llms,
    list_frameworks,
)
from shims.registry import ShimRegistry
from server.middleware import setup_middleware

# Load environment variables from .env if present
load_dotenv()

# Environment Audit & Purge: Ensure YAML priority by clearing persistent overrides
# NOTE: This only purges on first import of the module.
active_envs = [k for k in os.environ.keys() if k.startswith("ACTIVE_")]
for k in active_envs:
    sys.stderr.write(f"PURGING ENV OVERRIDE: {k}={os.environ[k]}\n")
    del os.environ[k]

# Suppress noisy upstream deprecations for a clean evaluation environment
warnings.filterwarnings("ignore", category=DeprecationWarning, module="google.genai")
warnings.filterwarnings("ignore", category=UserWarning, module="langchain")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="jsonschema")

# Ensure all plugins are registered by importing their packages
import llm_providers as _llm_providers
import frameworks as _frameworks
import shims as _shims

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
        llm_cls = get_llm_provider(config.active_llm)
        llm = llm_cls(config.llms[config.active_llm])

        # Dimension 2: Vertical/Shims (Isolated per request)
        active_vertical = config.verticals[config.active_vertical]
        shim_registry = ShimRegistry(enabled_shims=active_vertical.shims)
        shim_registry.reset_all()

        # Dimension 3: Framework (Wired to request-scoped shims)
        framework_cls = get_framework_adapter(config.active_framework)
        framework = framework_cls(llm, shim_registry.get_all_tools(), config)

        # Dynamically load the agent
        agent_name = data.get("agent", active_vertical.agents[0])
        agent_cls = get_agent_class(agent_name)

        # Inject framework and isolated shims into agent
        agent = agent_cls(config, framework, shim_registry.shims)

        # Execute
        result = agent.execute(data)
        return jsonify(result)

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

        return render_template(
            "index.html",
            agents=active_vert.agents,
            active_llm=config.active_llm,
            active_framework=config.active_framework,
            active_vertical=config.active_vertical,
            all_llms=all_llms,
            all_frameworks=all_frameworks,
            all_verticals=all_verticals,
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


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
