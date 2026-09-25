"""
Cloudflare Worker Edge Isolate Mock for agent testing.
Simulates V8 Isolate edge execution with non-blocking async telemetry pushes to an external drift receiver endpoint.
"""

import logging
import time

import requests

logger = logging.getLogger("cf-worker-mock")


class CloudflareWorkerIsolateMock:
    def __init__(
        self,
        telemetry_endpoint: str = "http://localhost:5000/api/v1/compliance/telemetry",
    ):
        self.telemetry_endpoint = telemetry_endpoint
        self.buffer = []
        self.max_buffer_size = 100  # V8 Isolate OOM Ceiling Protection
        self.flush_timeout_sec = 0.5  # Hard-Kill Timeout Protection

    def record_trace_span(self, name: str, duration_ms: float, status: str = "ok"):
        """Records a trace span into bounded ring buffer."""
        if len(self.buffer) >= self.max_buffer_size:
            self.buffer.pop(0)  # Drop oldest trace to maintain memory ceiling

        span = {
            "traceId": f"tr_{int(time.time() * 1000)}",
            "spanId": f"sp_{len(self.buffer) + 1}",
            "name": name,
            "timestamp": time.time() * 1000.0,
            "durationMs": duration_ms,
            "attributes": {"status": status, "isolate": "cloudflare-v8-mock"},
        }
        self.buffer.append(span)

    def flush_background(self, token: str = "valid_jws_token") -> bool:
        """Simulates ctx.waitUntil() background telemetry flush."""
        if not self.buffer:
            return True

        payload = {"spans": list(self.buffer)}
        self.buffer.clear()

        try:
            resp = requests.post(
                self.telemetry_endpoint,
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
                timeout=self.flush_timeout_sec,
            )
            return resp.status_code == 200
        except Exception as e:
            logger.warning(
                "Cloudflare worker mock background flush timed out / offline: %s", e
            )
            return False
