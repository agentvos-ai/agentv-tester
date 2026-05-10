import logging
logger = logging.getLogger(__name__)

from typing import List, Dict, Any, Tuple
from core.registry import register_shim
from core.errors import ShimError
from shims import BaseShim

@register_shim("iot")

class IotShim(BaseShim):
    """
    IoT device management and sensor data interface.
    Supports reading sensors, sending commands, and monitoring alerts.
    """

    @property
    def name(self) -> str:
        return "iot"

    @property
    def description(self) -> str:
        return "Enterprise IoT platform for managing industrial and facility devices."

    def reset(self) -> None:
        """Deterministic reset of the IoT state."""
        self._state["devices"] = {
            "sensor-01": {"type": "temp", "value": 22.5, "status": "ONLINE"},
            "actuator-01": {"type": "pump", "value": "OFF", "status": "ONLINE"}
        }
        self._state["subscriptions"] = []

    def read_sensor(self, device_id: str) -> Any:
        """Reads the current value of a sensor."""
        if device_id not in self._state["devices"]:
            raise ShimError(f"IoT Device '{device_id}' not found.")
        return self._state["devices"][device_id]["value"]

    def send_command(self, device_id: str, command: str) -> str:
        """Sends a command to an IoT actuator."""
        if device_id not in self._state["devices"]:
            raise ShimError(f"IoT Device '{device_id}' not found.")
        self._state["devices"][device_id]["value"] = command
        return f"Command '{command}' sent to device '{device_id}'."

    def list_devices(self) -> List[Dict[str, Any]]:
        """Lists all registered IoT devices and their status."""
        return [{"id": k, **v} for k, v in self._state["devices"].items()]

    def subscribe_alert(self, device_id: str, threshold: float) -> str:
        """Subscribes the agent to alerts for a specific sensor threshold."""
        self._state["subscriptions"].append({"device": device_id, "threshold": threshold})
        return f"Subscribed to alerts for '{device_id}' at threshold {threshold}."

    def get_tool_specs(self) -> List[Tuple[str, Any, str]]:
        return [
            ("iot_read", self.read_sensor, "Read the current value of an IoT sensor."),
            ("iot_command", self.send_command, "Send a control command to an IoT device."),
            ("iot_list", self.list_devices, "List all active IoT devices and their status."),
            ("iot_subscribe", self.subscribe_alert, "Subscribe to threshold-based alerts for an IoT sensor.")
        ]