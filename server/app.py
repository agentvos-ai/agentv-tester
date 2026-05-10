import os
from flask import Flask, request, jsonify
from core.config_loader import ConfigLoader
from core.registry import get_llm_provider, get_framework_adapter, get_agent_class
from shims.registry import ShimRegistry
from server.middleware import setup_middleware

def create_app() -> Flask:
    app = Flask(__name__)
    setup_middleware(app)

    # Initialize Config
    config_path = os.environ.get("SUITE_CONFIG", "config/suite.yaml")
    config = ConfigLoader.load(config_path)

    # Initialize Components (Harness-Blind)
    # Dimension 1: LLM
    llm_cls = get_llm_provider(config.active_llm)
    llm = llm_cls(config.llms[config.active_llm])

    # Dimension 2: Framework
    framework_cls = get_framework_adapter(config.active_framework)
    
    # Dimension 3: Vertical/Shims
    active_vertical = config.verticals[config.active_vertical]
    shim_registry = ShimRegistry(enabled_shims=active_vertical.shims)
    
    framework = framework_cls(llm, shim_registry.get_all_tools())

    @app.route("/execute_task", methods=["POST"])
    def execute_task():
        """
        The primary endpoint for the external evaluation harness.
        Expects: {"task_id": str, "input": str, "context": dict}
        """
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "No JSON payload provided"}), 400

        # Dynamically load the agent requested in the task (or default from config)
        agent_name = data.get("agent", active_vertical.agents[0])
        agent_cls = get_agent_class(agent_name)
        
        # Inject framework and shims into agent
        agent = agent_cls(config, framework, shim_registry.shims)
        
        # Reset shims to baseline for deterministic execution
        shim_registry.reset_all()
        
        # Execute
        result = agent.execute(data)
        return jsonify(result)

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({
            "status": "healthy",
            "active_llm": config.active_llm,
            "active_framework": config.active_framework,
            "active_vertical": config.active_vertical
        })

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
