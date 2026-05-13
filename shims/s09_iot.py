import logging
import os
import json
import random
import time
from typing import List, Dict, Any, Tuple
from core.registry import register_shim
from core.errors import ShimError
from shims import BaseShim

logger = logging.getLogger(__name__)


@register_shim("iot")
class IotShim(BaseShim):
    """
    Industrial-grade IoT interface.
    Uses a persistent device registry and simulates time-series sensor trends.
    """

    def __init__(self, seed: int = 42):
        self.db_path = os.path.abspath(".agent_workspace/db/iot_registry.json")
        super().__init__(seed)

    @property
    def name(self) -> str:
        return "iot"

    @property
    def description(self) -> str:
        return "Enterprise IoT platform for industrial sensor monitoring and actuator control."

    def setup(self) -> None:
        """Ensure device registry exists."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        if not os.path.exists(self.db_path):
            self.reset()

    def reset(self) -> None:
        """Deterministic reset of the IoT state."""
        default_devices = {
            "sensor-01": {
                "type": "TEMPERATURE",
                "unit": "C",
                "base_val": 45.0,
                "status": "ONLINE",
                "trend": "STABLE",
            },
            "sensor-02": {
                "type": "PRESSURE",
                "unit": "PSI",
                "base_val": 120.0,
                "status": "ONLINE",
                "trend": "RISING",
            },
            "actuator-01": {"type": "VALVE", "status": "CLOSED"},
        }
        with open(self.db_path, "w") as f:
            json.dump(default_devices, f, indent=2)

    def _load_registry(self) -> Dict[str, Any]:
        with open(self.db_path, "r") as f:
            return json.load(f)

    def _save_registry(self, registry: Dict[str, Any]) -> None:
        with open(self.db_path, "w") as f:
            json.dump(registry, f, indent=2)

    def read_sensor(self, device_id: str) -> Dict[str, Any]:
        """Reads real-time sensor data with time-series trend simulation."""
        registry = self._load_registry()
        if device_id not in registry:
            raise ShimError(f"Device '{device_id}' not found in registry.")

        device = registry[device_id]
        if device.get("type") == "VALVE":
            raise ShimError(f"Device '{device_id}' is an actuator, not a sensor.")

        # Simulate Trend Logic
        # RISING trend: +1% per 10 seconds since 'start of shift'
        # For simplicity, we'll use a pseudo-time based on the current timestamp
        base = device["base_val"]
        trend = device["trend"]

        noise = random.uniform(-0.5, 0.5)
        if trend == "RISING":
            # Simple simulation: increases slightly with each call
            base += 1.2
            device["base_val"] = base
            self._save_registry(registry)

        reading = base + noise
        return {
            "device_id": device_id,
            "type": device["type"],
            "reading": round(reading, 2),
            "unit": device["unit"],
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

    def send_command(self, device_id: str, command: str) -> str:
        """Sends a control command to an industrial actuator."""
        registry = self._load_registry()
        if device_id not in registry:
            raise ShimError(f"Device '{device_id}' not found.")

        device = registry[device_id]
        device["status"] = (
            "OPEN" if "OPEN" in command.upper() or "ON" in command.upper() else "CLOSED"
        )
        self._save_registry(registry)

        logger.info(f"IoT: Command '{command}' executed on {device_id}.")
        return f"Command '{command}' successfully acknowledged by {device_id}."

    def list_devices(self) -> List[Dict[str, Any]]:
        """Lists all registered industrial devices."""
        registry = self._load_registry()
        return [{"id": k, **v} for k, v in registry.items()]

    def get_tool_specs(self) -> List[Tuple[str, Any, str]]:
        return [
            (
                "iot_read",
                self.read_sensor,
                "Read real-time data from an industrial sensor.",
            ),
            (
                "iot_command",
                self.send_command,
                "Send a control command to an actuator.",
            ),
            ("iot_list", self.list_devices, "List all connected industrial devices."),
        ]
