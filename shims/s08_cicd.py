import logging
logger = logging.getLogger(__name__)

from typing import List, Dict, Any, Tuple
from core.registry import register_shim
from core.errors import ShimError
from shims import BaseShim

@register_shim("cicd")

class CicdShim(BaseShim):
    """
    CI/CD pipeline management and monitoring service.
    Supports pipeline triggering, monitoring, and cancellation.
    """

    @property
    def name(self) -> str:
        return "cicd"

    @property
    def description(self) -> str:
        return "Enterprise CI/CD service for managing automated software pipelines."

    def reset(self) -> None:
        """Deterministic reset of the CI/CD state."""
        self._state["pipelines"]: Dict[str, Dict[str, Any]] = {
            "deploy-prod": {"status": "SUCCESS", "logs": ["Starting build...", "Tests passed.", "Deployed."]},
            "data-sync": {"status": "IDLE", "logs": []}
        }

    def trigger_pipeline(self, pipeline_id: str) -> str:
        """Triggers an automated pipeline."""
        if pipeline_id not in self._state["pipelines"]:
            raise ShimError(f"Pipeline '{pipeline_id}' not found.")
        self._state["pipelines"][pipeline_id]["status"] = "RUNNING"
        self._state["pipelines"][pipeline_id]["logs"].append("Pipeline triggered by agent.")
        return f"Pipeline '{pipeline_id}' is now running."

    def get_status(self, pipeline_id: str) -> str:
        """Checks the status of a pipeline."""
        if pipeline_id not in self._state["pipelines"]:
            raise ShimError(f"Pipeline '{pipeline_id}' not found.")
        return self._state["pipelines"][pipeline_id]["status"]

    def get_logs(self, pipeline_id: str) -> List[str]:
        """Fetches the execution logs for a pipeline."""
        if pipeline_id not in self._state["pipelines"]:
            raise ShimError(f"Pipeline '{pipeline_id}' not found.")
        return self._state["pipelines"][pipeline_id]["logs"]

    def cancel_pipeline(self, pipeline_id: str) -> str:
        """Cancels a currently running pipeline."""
        if pipeline_id not in self._state["pipelines"]:
            raise ShimError(f"Pipeline '{pipeline_id}' not found.")
        self._state["pipelines"][pipeline_id]["status"] = "CANCELLED"
        self._state["pipelines"][pipeline_id]["logs"].append("Pipeline cancelled by agent.")
        return f"Pipeline '{pipeline_id}' has been cancelled."

    def get_tool_specs(self) -> List[Tuple[str, Any, str]]:
        return [
            ("cicd_trigger", self.trigger_pipeline, "Trigger an automated CI/CD pipeline."),
            ("cicd_status", self.get_status, "Check the current status of a CI/CD pipeline."),
            ("cicd_logs", self.get_logs, "Fetch the most recent logs for a CI/CD pipeline."),
            ("cicd_cancel", self.cancel_pipeline, "Cancel a running CI/CD pipeline.")
        ]