import logging
import os
import sqlite3
import json
from typing import List, Dict, Any, Tuple
from core.registry import register_shim
from core.errors import ShimError
from shims import BaseShim

logger = logging.getLogger(__name__)


@register_shim("analytics")
class AnalyticsShim(BaseShim):
    """
    Industrial-grade Analytics interface.
    Uses a local SQLite database for metrics, reports, and forecasts.
    """

    def __init__(self, seed: int = 42):
        self.db_path = os.path.abspath(".agent_workspace/db/analytics.db")
        super().__init__(seed)

    @property
    def name(self) -> str:
        return "analytics"

    @property
    def description(self) -> str:
        return "Enterprise analytics engine for business intelligence and forecasting."

    def setup(self) -> None:
        """Ensure database and tables exist."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id TEXT PRIMARY KEY,
                    value REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    config_json TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def shutdown(self) -> None:
        """Cleanup the database file."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def reset(self) -> None:
        """Deterministic reset of the analytics state."""
        self.shutdown()
        self.setup()

        # Seed default metrics
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "INSERT INTO metrics (id, value) VALUES (?, ?)", ("avg_nps", 8.5)
            )
            conn.execute(
                "INSERT INTO metrics (id, value) VALUES (?, ?)", ("churn_rate", 0.12)
            )
            conn.execute(
                "INSERT INTO metrics (id, value) VALUES (?, ?)", ("nps_score", 72.0)
            )
            conn.commit()
        finally:
            conn.close()

    def query_metrics(self, metric_id: str) -> float:
        """Retrieves a specific business metric."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT value FROM metrics WHERE id = ?", (metric_id,)
            )
            row = cursor.fetchone()
            if not row:
                raise ShimError(f"Metric '{metric_id}' not found.")
            return row[0]
        finally:
            conn.close()

    def create_report(self, title: str, metrics: List[str]) -> str:
        """Generates a new business report."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "INSERT INTO reports (title, config_json) VALUES (?, ?)",
                (title, json.dumps(metrics)),
            )
            conn.commit()
            return f"Report '{title}' generated successfully."
        except Exception as e:
            raise ShimError(f"Failed to create report: {str(e)}")
        finally:
            conn.close()

    def get_kpi(self, kpi_name: str) -> Dict[str, Any]:
        """Retrieves a Key Performance Indicator."""
        val = self.query_metrics(kpi_name)
        return {
            "name": kpi_name,
            "value": val,
            "status": "OPTIMAL" if val > 5 else "CRITICAL",
        }

    def forecast(self, metric_id: str, periods: int) -> List[float]:
        """Simulates forecasting based on historic metrics."""
        base = self.query_metrics(metric_id)
        # Simple linear projection with a bit of "industrial" noise
        return [base * (1 + 0.02 * i) for i in range(1, periods + 1)]

    def aggregate_metrics(self, metric_ids: List[str], operation: str = "sum") -> float:
        """Aggregates multiple metrics using sum, avg, min, or max."""
        if not metric_ids:
            return 0.0
        conn = sqlite3.connect(self.db_path)
        try:
            placeholders = ", ".join(["?" for _ in metric_ids])
            sql = f"SELECT value FROM metrics WHERE id IN ({placeholders})"
            cursor = conn.execute(sql, metric_ids)
            values = [row[0] for row in cursor.fetchall()]
            if not values:
                return 0.0

            op = operation.lower()
            if op == "sum":
                return sum(values)
            if op == "avg":
                return sum(values) / len(values)
            if op == "min":
                return min(values)
            if op == "max":
                return max(values)
            raise ShimError(f"Unsupported aggregation operation: {operation}")
        finally:
            conn.close()

    def get_tool_specs(self) -> List[Tuple[str, Any, str]]:
        return [
            ("analytics_query", self.query_metrics, "Query a business metric."),
            ("analytics_report", self.create_report, "Create a performance report."),
            ("analytics_kpi", self.get_kpi, "Retrieve a Key Performance Indicator."),
            (
                "analytics_forecast",
                self.forecast,
                "Forecast metrics for future periods.",
            ),
            (
                "analytics_aggregate",
                self.aggregate_metrics,
                "Aggregate multiple metrics (sum, avg, min, max).",
            ),
        ]
