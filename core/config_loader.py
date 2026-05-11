import os
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    model: str
    api_key_env: str
    base_url: str | None = None
    fallbacks: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VerticalConfig:
    name: str
    shims: List[str]
    agents: List[str]
    scenarios: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class SuiteConfig:
    active_vertical: str
    active_framework: str
    active_llm: str
    llms: Dict[str, LLMConfig]
    verticals: Dict[str, VerticalConfig]
    seed: int = 42


class ConfigLoader:
    BASE_DIR = Path(__file__).parent.parent
    CONFIG_DIR = BASE_DIR / "config"

    @classmethod
    def load(cls, config_path: str = "suite.yaml") -> SuiteConfig:
        """
        Loads and merges configuration with environment overrides.
        Follows Section 2: Master Configuration System.
        """
        # Industrial Hardening: Configuration is driven by suite.yaml,
        # but environment variables allow for targeted session overrides.
        loader = cls()
        # Use the provided config_path (relative to CONFIG_DIR or absolute)
        suite = loader._read(config_path)

        # Determine active dimensions (ENV overrides YAML)
        active_block = suite.get("active", {})

        # Now environment variables are purged, so we only get them if they are set EXPLICITLY for this call
        vertical = os.environ.get(
            "ACTIVE_VERTICAL", active_block.get("vertical", "fintech")
        )
        framework = os.environ.get(
            "ACTIVE_FRAMEWORK", active_block.get("framework", "langgraph")
        )
        llm_name = os.environ.get("ACTIVE_LLM", active_block.get("llm", "gemini"))

        from core.errors import ConfigError
        from core.registry import get_framework_adapter

        try:
            get_framework_adapter(framework)
        except Exception as e:
            raise ConfigError(f"Invalid framework configuration: {str(e)}")

        vertical_cfg = loader._read(f"verticals/{vertical}.yaml")
        llm_cfg_raw = loader._read(f"llms/{llm_name}.yaml")

        llm = LLMConfig(
            provider=llm_name,
            model=llm_cfg_raw.get("model", "unknown"),
            api_key_env=llm_cfg_raw.get("api_key_env", f"{llm_name.upper()}_API_KEY"),
            base_url=llm_cfg_raw.get("base_url"),
            fallbacks=llm_cfg_raw.get("fallbacks", []),
            extra=llm_cfg_raw.get("extra", {}),
        )

        # Load configurations for fallbacks as well
        llms = {llm_name: llm}
        for f_name in llm.fallbacks:
            f_cfg_raw = loader._read(f"llms/{f_name}.yaml")
            llms[f_name] = LLMConfig(
                provider=f_name,
                model=f_cfg_raw.get("model", "unknown"),
                api_key_env=f_cfg_raw.get(
                    "api_key_env", f"{f_name.upper()}_API_KEY"
                ),
                base_url=f_cfg_raw.get("base_url"),
                fallbacks=f_cfg_raw.get("fallbacks", []),
                extra=f_cfg_raw.get("extra", {}),
            )

        return SuiteConfig(
            active_vertical=vertical,
            active_framework=framework,
            active_llm=llm_name,
            llms=llms,
            verticals={
                vertical: VerticalConfig(
                    name=vertical,
                    shims=vertical_cfg.get("shims", []),
                    agents=vertical_cfg.get("agents", []),
                    scenarios=vertical_cfg.get("scenarios", []),
                )
            },
            seed=int(
                os.environ.get("SUITE_SEED", suite.get("shims", {}).get("seed", 42))
            ),
        )

    def _read(self, rel_path: str) -> Dict[str, Any]:
        path = self.CONFIG_DIR / rel_path
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
