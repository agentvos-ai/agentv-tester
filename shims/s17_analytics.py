import logging

logger = logging.getLogger(__name__)

from typing import List, Any, Tuple
from core.registry import register_shim
from core.errors import ShimError
from shims import BaseShim


@register_shim("analytics")
class AnalyticsShim(BaseShim):
    """
    Enterprise analytics and reporting simulator.
    Supports metrics querying, KPI calculation, and forecasting.
    """

    @property
    def name(self) -> str:
        return "analytics"

    @property
    def description(self) -> str:
        return "Analytics engine for monitoring performance and forecasting trends."

    def reset(self) -> None:
        """Deterministic reset of the analytics data."""
        self._state["metrics"] = {
            "churn_rate": [0.05, 0.04, 0.06],
            "nps_score": [72, 75, 74],
        }
        self._state["reports"] = []

    def query_metrics(self, metric_id: str) -> List[float]:
        """Queries historical values for a metric."""
        if metric_id not in self._state["metrics"]:
            raise ShimError(f"Metric '{metric_id}' not found.")
        return self._state["metrics"][metric_id]

    def create_report(self, title: str, metric_ids: List[str]) -> str:
        """Generates a summary report for multiple metrics."""
        report_id = f"REP-{len(self._state['reports']) + 1}"
        summary = {m: self.query_metrics(m) for m in metric_ids}
        self._state["reports"].append(
            {"id": report_id, "title": title, "data": summary}
        )
        return f"Report '{title}' generated with ID: {report_id}."

    def get_kpi(self, kpi_name: str) -> float:
        """Calculates a specific Key Performance Indicator."""
        if kpi_name == "avg_nps":
            nps = self._state["metrics"]["nps_score"]
            return sum(nps) / len(nps)
        return 0.0

    def forecast(self, metric_id: str, steps: int) -> List[float]:
        """Simple linear forecast for a metric."""
        history = self.query_metrics(metric_id)
        last = history[-1]
        return [last + (0.1 * i) for i in range(1, steps + 1)]

    def get_tool_specs(self) -> List[Tuple[str, Any, str]]:
        return [
            (
                "analytics_query",
                self.query_metrics,
                "Query historical data for a specific metric.",
            ),
            (
                "analytics_report",
                self.create_report,
                "Generate a performance report for a set of metrics.",
            ),
            ("analytics_kpi", self.get_kpi, "Calculate an enterprise KPI."),
            (
                "analytics_forecast",
                self.forecast,
                "Generate a forecast for a metric based on historical data.",
            ),
        ]
