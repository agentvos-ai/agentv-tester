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
    extra: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class VerticalConfig:
    name: str
    shims: List[str]
    agents: List[str]

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
    def load(cls, config_path: str = "config/suite.yaml") -> SuiteConfig:
        """
        Loads and merges configuration with environment overrides.
        Follows Section 2: Master Configuration System.
        """
        loader = cls()
        suite = loader._read("suite.yaml")
        
        # Determine active dimensions (ENV overrides YAML)
        vertical = os.environ.get("ACTIVE_VERTICAL", suite.get("active_vertical", "fintech"))
        framework = os.environ.get("ACTIVE_FRAMEWORK", suite.get("active_framework", "langgraph"))
        llm_name = os.environ.get("ACTIVE_LLM", suite.get("active_llm", "gemini"))

        vertical_cfg = loader._read(f"verticals/{vertical}.yaml")
        llm_cfg_raw = loader._read(f"llms/{llm_name}.yaml")

        llm = LLMConfig(
            provider=llm_name,
            model=llm_cfg_raw.get("model", "unknown"),
            api_key_env=llm_cfg_raw.get("api_key_env", f"{llm_name.upper()}_API_KEY"),
            base_url=llm_cfg_raw.get("base_url"),
            extra=llm_cfg_raw.get("extra", {}),
        )

        return SuiteConfig(
            active_vertical=vertical,
            active_framework=framework,
            active_llm=llm_name,
            llms={llm_name: llm},
            verticals={vertical: VerticalConfig(
                name=vertical,
                shims=vertical_cfg.get("shims", []),
                agents=vertical_cfg.get("agents", [])
            )},
            seed=int(os.environ.get("SUITE_SEED", suite.get("shims", {}).get("seed", 42)))
        )

    def _read(self, rel_path: str) -> Dict[str, Any]:
        path = self.CONFIG_DIR / rel_path
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        with open(path, "r") as f:
            return yaml.safe_load(f)
