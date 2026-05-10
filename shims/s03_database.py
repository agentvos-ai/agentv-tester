import logging
logger = logging.getLogger(__name__)

from typing import List, Dict, Any, Tuple
from sqlalchemy import create_engine, text
from core.registry import register_shim
from core.errors import ShimError
from shims import BaseShim

@register_shim("database")

class DatabaseShim(BaseShim):
    """
    SQL-like in-memory store (SQLite) with schema per vertical.
    Supports standard CRUD and schema inspection.
    """

    def __init__(self, seed: int = 42):
        self.engine = create_engine("sqlite:///:memory:", echo=False)
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

    def _initialize_schema(self) -> None:
        with self.engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS accounts"))
            conn.execute(text("CREATE TABLE accounts (id INTEGER PRIMARY KEY, name TEXT, balance REAL)"))
            conn.execute(text("INSERT INTO accounts (id, name, balance) VALUES (1, 'Main Operating', 1000000.0)"))
            conn.execute(text("INSERT INTO accounts (id, name, balance) VALUES (2, 'Fraud Reserve', 50000.0)"))
            conn.commit()

    def query(self, sql: str) -> List[Dict[str, Any]]:
        """Executes a SELECT query."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(sql))
                return [dict(row._mapping) for row in result]
        except Exception as e:
            raise ShimError(f"Database query failed: {str(e)}")

    def insert(self, table: str, data: Dict[str, Any]) -> str:
        """Inserts a new record into a table."""
        columns = ", ".join(data.keys())
        values = ", ".join([f":{k}" for k in data.keys()])
        sql = f"INSERT INTO {table} ({columns}) VALUES ({values})"
        try:
            with self.engine.connect() as conn:
                conn.execute(text(sql), data)
                conn.commit()
            return f"Record inserted into '{table}'."
        except Exception as e:
            raise ShimError(f"Database insert failed: {str(e)}")

    def update(self, table: str, data: Dict[str, Any], condition: str) -> str:
        """Updates records in a table."""
        set_clause = ", ".join([f"{k} = :{k}" for k in data.keys()])
        sql = f"UPDATE {table} SET {set_clause} WHERE {condition}"
        try:
            with self.engine.connect() as conn:
                conn.execute(text(sql), data)
                conn.commit()
            return f"Table '{table}' updated."
        except Exception as e:
            raise ShimError(f"Database update failed: {str(e)}")

    def delete(self, table: str, condition: str) -> str:
        """Deletes records from a table."""
        sql = f"DELETE FROM {table} WHERE {condition}"
        try:
            with self.engine.connect() as conn:
                conn.execute(text(sql))
                conn.commit()
            return f"Records deleted from '{table}'."
        except Exception as e:
            raise ShimError(f"Database delete failed: {str(e)}")

    def schema_describe(self) -> Dict[str, Any]:
        """Describes the database schema."""
        return {
            "accounts": ["id (INT)", "name (TEXT)", "balance (REAL)"]
        }

    def get_tool_specs(self) -> List[Tuple[str, Any, str]]:
        return [
            ("db_query", self.query, "Execute a SELECT query on the enterprise database."),
            ("db_insert", self.insert, "Insert a new record into a database table."),
            ("db_update", self.update, "Update existing records in a database table."),
            ("db_delete", self.delete, "Delete records from a database table."),
            ("db_describe", self.schema_describe, "Describe the schema of the enterprise database.")
        ]