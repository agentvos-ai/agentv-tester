import logging
import os
import sqlite3
import random
from typing import List, Dict, Any, Tuple
from core.registry import register_shim
from core.errors import ShimError
from shims import BaseShim

logger = logging.getLogger(__name__)


@register_shim("iot")
class IotShim(BaseShim):
    """
    Industrial-grade IoT interface.
    Uses a local SQLite database for device registry and time-series sensor logs.
    """

    def __init__(self, seed: int = 42):
        self.db_path = os.path.abspath(".agent_workspace/db/iot.db")
        super().__init__(seed)

    @property
    def name(self) -> str:
        return "iot"

    @property
    def description(self) -> str:
        return "Interface for managing and monitoring industrial IoT devices."

    def setup(self) -> None:
        """Ensure database and tables exist."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS devices (
                    id TEXT PRIMARY KEY,
                    type TEXT,
                    status TEXT,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sensor_logs (
                    device_id TEXT,
                    reading REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(device_id) REFERENCES devices(id)
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
        """Deterministic reset of the IoT state."""
        self.shutdown()
        self.setup()

        # Seed default devices
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "INSERT INTO devices (id, type, status) VALUES ('sensor-01', 'TEMPERATURE', 'ONLINE')"
            )
            conn.execute(
                "INSERT INTO devices (id, type, status) VALUES ('actuator-01', 'SWITCH', 'OFF')"
            )
            conn.commit()
        finally:
            conn.close()

    def read_sensor(self, device_id: str) -> Dict[str, Any]:
        """Reads a sensor value with realistic time-series simulation."""
        conn = sqlite3.connect(self.db_path)
        try:
            res = conn.execute(
                "SELECT type, status FROM devices WHERE id = ?", (device_id,)
            ).fetchone()
            if not res:
                raise ShimError(f"Device '{device_id}' not found.")

            if res[1] != "ONLINE" and res[0] == "TEMPERATURE":
                raise ShimError(f"Device '{device_id}' is offline.")

            # Simulate reading: base temp + noise
            base = 22.0
            noise = random.uniform(-0.5, 0.5)
            reading = base + noise

            conn.execute(
                "INSERT INTO sensor_logs (device_id, reading) VALUES (?, ?)",
                (device_id, reading),
            )
            conn.commit()

            return {
                "id": device_id,
                "type": res[0],
                "reading": reading,
                "unit": "Celsius",
            }
        except Exception as e:
            if isinstance(e, ShimError):
                raise
            raise ShimError(f"Failed to read sensor: {str(e)}")
        finally:
            conn.close()

    def send_command(self, device_id: str, command: str) -> str:
        """Sends a control command to an actuator."""
        conn = sqlite3.connect(self.db_path)
        try:
            res = conn.execute(
                "SELECT type FROM devices WHERE id = ?", (device_id,)
            ).fetchone()
            if not res:
                raise ShimError(f"Device '{device_id}' not found.")

            # Simple status update simulation
            status = "ON" if "ON" in command.upper() else "OFF"
            conn.execute(
                "UPDATE devices SET status = ? WHERE id = ?", (status, device_id)
            )
            conn.commit()

            return f"Command '{command}' executed on device '{device_id}'. New status: {status}."
        except Exception as e:
            if isinstance(e, ShimError):
                raise
            raise ShimError(f"Failed to send command: {str(e)}")
        finally:
            conn.close()

    def list_devices(self) -> List[Dict[str, Any]]:
        """Lists all registered IoT devices."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute("SELECT id, type, status FROM devices")
            return [
                {"id": row[0], "type": row[1], "status": row[2]}
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()

    def get_tool_specs(self) -> List[Tuple[str, Any, str]]:
        return [
            (
                "iot_read",
                self.read_sensor,
                "Read the current value from an IoT sensor.",
            ),
            (
                "iot_command",
                self.send_command,
                "Send a control command to an IoT actuator.",
            ),
            ("iot_list", self.list_devices, "List all registered industrial devices."),
        ]
