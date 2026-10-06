"""Local Phone Gateway Server for Paired Android/Mobile Clients.

Implements Sections 69, 70, 71, 74 of the Engineering Constitution.
"""

from __future__ import annotations

import json
import logging
import urllib.parse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict

from edith.core.config import CONFIG
from edith.core.security import SECURITY
from edith.core.state_machine import STATE
from edith.phone.protocol import PHONE_PROTOCOL
from edith.tools.windows import WIN_TOOLS

logger = logging.getLogger("edith.phone.gateway")


class PhoneGatewayHandler(SimpleHTTPRequestHandler):
    """HTTP endpoint handler for paired phone devices."""

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"

        try:
            data = json.loads(body)
        except Exception:
            data = {}

        if parsed.path == "/pair":
            device_id = data.get("device_id", "phone_1")
            device_name = data.get("device_name", "Android Phone")
            token = PHONE_PROTOCOL.pair_device(device_id, device_name)
            self._send_json({"paired": True, "token": token, "system": CONFIG.system_name})
            return

        # Authenticate all subsequent operations
        device_id = data.get("device_id", "")
        token = data.get("token", "")
        if not PHONE_PROTOCOL.verify_token(device_id, token):
            self._send_json({"error": "Unauthorized device token."}, status=401)
            return

        if parsed.path == "/cmd":
            command = data.get("command", "")
            queue_len = PHONE_PROTOCOL.queue_command(device_id, command, data.get("params"))
            self._send_json({"success": True, "queued": True, "queue_length": queue_len})
        elif parsed.path == "/emergency_stop":
            SECURITY.trigger_emergency_stop(f"Emergency stop triggered from phone {device_id}")
            self._send_json({"success": True, "state": "EMERGENCY_STOP"})
        else:
            self.send_error(404, "Endpoint not found")

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/status":
            stats = WIN_TOOLS.get_system_stats()
            stats["state"] = STATE.current_state.value
            stats["emergency_stopped"] = SECURITY.is_emergency_stopped
            self._send_json(stats)
        else:
            self.send_error(404, "Endpoint not found")

    def _send_json(self, payload: Dict[str, Any], status: int = 200) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, format: str, *args: Any) -> None:
        pass


def create_phone_gateway(port: int = 8795) -> ThreadingHTTPServer:
    """Instantiate the phone communication gateway server."""
    server = ThreadingHTTPServer(("127.0.0.1", port), PhoneGatewayHandler)
    logger.info("EDITH Phone Gateway listening at http://127.0.0.1:%d", port)
    return server
