import logging
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from core.errors import ShimError
from core.registry import register_shim
from shims import BaseShim

logger = logging.getLogger(__name__)


@register_shim("database")
class DatabaseShim(BaseShim):
    """
    SQL-like in-memory store (SQLite) with schema per vertical.
    Supports standard CRUD and schema inspection.
    """

    def __init__(self, seed: int = 42):
        self.engine = create_engine(
            "sqlite:///:memory:",
            echo=False,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        super().__init__(seed)

    @property
    def name(self) -> str:
        return "database"

    @property
    def description(self) -> str:
        return "Enterprise SQL database for querying and managing structured data."

    def reset(self) -> None:
        """Deterministic reset of the database state."""
        self._initialize_schema()

    def shutdown(self) -> None:
        """Dispose of the engine to release the in-memory SQLite database."""
        self.engine.dispose()

    def _initialize_schema(self) -> None:
        with self.engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS accounts"))
            conn.execute(
                text(
                    "CREATE TABLE accounts (id INTEGER PRIMARY KEY, name TEXT, balance REAL)"
                )
            )
            conn.execute(
                text(
                    "INSERT INTO accounts (id, name, balance) VALUES (1, 'Main Operating', 1000000.0)"
                )
            )
            conn.execute(
                text(
                    "INSERT INTO accounts (id, name, balance) VALUES (2, 'Fraud Reserve', 50000.0)"
                )
            )
            conn.execute(text("DROP TABLE IF EXISTS transactions"))
            conn.execute(
                text(
                    "CREATE TABLE transactions (id TEXT PRIMARY KEY, account_id TEXT, amount REAL, status TEXT)"
                )
            )
            conn.execute(
                text(
                    "INSERT INTO transactions (id, account_id, amount, status) VALUES ('TX-9982', 'ACC-771', 75000.0, 'FLAGGED')"
                )
            )
            conn.commit()

    def query(self, sql: str = "", query: str = "") -> list[dict[str, Any]]:
        """Executes a SELECT query."""
        sql_stmt = sql or query
        if not sql_stmt:
            raise ShimError("Database query failed: SQL statement cannot be empty.")
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(sql_stmt))
                return [dict(row._mapping) for row in result]
        except Exception as e:
            raise ShimError(f"Database query failed: {e!s}")

    def insert(self, table: str, data: dict[str, Any]) -> str:
        """Inserts a new record into a table."""
        columns = ", ".join(data.keys())
        values = ", ".join([f":{k}" for k in data])
        sql = f"INSERT INTO {table} ({columns}) VALUES ({values})"
        try:
            with self.engine.connect() as conn:
                conn.execute(text(sql), data)
                conn.commit()
            return f"Record inserted into '{table}'."
        except Exception as e:
            raise ShimError(f"Database insert failed: {e!s}")

    def update(self, table: str, data: dict[str, Any], condition: str) -> str:
        """Updates records in a table."""
        set_clause = ", ".join([f"{k} = :{k}" for k in data])
        sql = f"UPDATE {table} SET {set_clause} WHERE {condition}"
        try:
            with self.engine.connect() as conn:
                conn.execute(text(sql), data)
                conn.commit()
            return f"Table '{table}' updated."
        except Exception as e:
            raise ShimError(f"Database update failed: {e!s}")

    def delete(self, table: str, condition: str) -> str:
        """Deletes records from a table."""
        sql = f"DELETE FROM {table} WHERE {condition}"
        try:
            with self.engine.connect() as conn:
                conn.execute(text(sql))
                conn.commit()
            return f"Records deleted from '{table}'."
        except Exception as e:
            raise ShimError(f"Database delete failed: {e!s}")

    def schema_describe(self) -> dict[str, Any]:
        """Describes the database schema dynamically using SQLite introspection."""
        try:
            schema = {}
            with self.engine.connect() as conn:
                # Get all table names
                tables = conn.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table'")
                )
                for table_row in tables:
                    table_name = table_row[0]
                    if table_name == "sqlite_sequence":
                        continue

                    # Get columns for each table
                    columns = conn.execute(text(f"PRAGMA table_info({table_name})"))
                    schema[table_name] = [f"{col[1]} ({col[2]})" for col in columns]
            return schema
        except Exception as e:
            raise ShimError(f"Failed to describe database schema: {e!s}")

    def get_tool_specs(self) -> list[tuple[str, Any, str]]:
        return [
            (
                "db_query",
                self.query,
                "Execute a SELECT query on the enterprise database.",
            ),
            ("db_insert", self.insert, "Insert a new record into a database table."),
            ("db_update", self.update, "Update existing records in a database table."),
            ("db_delete", self.delete, "Delete records from a database table."),
            (
                "db_describe",
                self.schema_describe,
                "Describe the schema of the enterprise database.",
            ),
        ]
