"""Local Phone Gateway Server for Paired Mobile Clients.

Implements Sections 69, 70, 71, 74 of the Engineering Constitution.
Supports WiFi LAN and Cloud Internet remote access.
"""

from __future__ import annotations

import asyncio
import json
import logging
import socket
import time
import urllib.parse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional

from edith.core.config import CONFIG
from edith.core.security import SECURITY, EmergencyStopActiveError
from edith.core.state_machine import STATE, SystemState
from edith.phone.protocol import PHONE_PROTOCOL
from edith.phone.tunnel import TUNNEL_MANAGER
from edith.providers.router import ROUTER, TaskCategory
from edith.tools.reflex import REFLEX
from edith.tools.registry import REGISTRY
from edith.tools.windows import WIN_TOOLS
from edith.voice.speaker import SPEAKER

logger = logging.getLogger("edith.phone.gateway")


def get_local_ip() -> str:
    """Retrieve host machine local network IP."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class PhoneGatewayHandler(SimpleHTTPRequestHandler):
    """HTTP endpoint handler for paired phone devices."""

    def end_headers(self) -> None:
        """Inject cache and CORS headers."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        super().end_headers()

    def do_OPTIONS(self) -> None:
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.end_headers()

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"

        try:
            data = json.loads(body)
        except Exception:
            self._send_json({"error": "Malformed JSON payload."}, status=400)
            return

        if parsed.path == "/pair":
            device_id = str(data.get("device_id", "phone_1")).strip() or "phone_1"
            device_name = str(data.get("device_name", "Android Phone")).strip() or "Android Phone"
            token = PHONE_PROTOCOL.pair_device(device_id, device_name)
            self._send_json({
                "paired": True,
                "token": token,
                "system": CONFIG.system_name,
                "device_id": device_id,
            })
            return

        # Authenticate operations when tokens are registered
        device_id = str(data.get("device_id", "")).strip()
        token = str(data.get("token", "")).strip()
        
        # If any paired devices exist, enforce token validation
        if PHONE_PROTOCOL._paired_devices:
            if not PHONE_PROTOCOL.verify_token(device_id, token):
                self._send_json({"error": "Unauthorized device token."}, status=401)
                return

        if parsed.path == "/cmd":
            command = str(data.get("command", "")).strip()
            if not command:
                self._send_json({"error": "Empty command string."}, status=400)
                return

            if len(command) > 1000:
                self._send_json({"error": "Command exceeds 1000 character limit."}, status=400)
                return

            # Record in protocol queue history
            queue_len = PHONE_PROTOCOL.queue_command(device_id or "direct_mobile", command, data.get("params"))

            # 1. Level 0 Reflex Fast Path
            match = REFLEX.evaluate(command)
            if match:
                try:
                    STATE.set_state_sync(SystemState.EXECUTING, reason=f"Executing reflex from phone: {command}")
                    res = REFLEX.execute_match(match, executor=lambda name, params: REGISTRY.execute_tool(name, params))
                    STATE.set_state_sync(SystemState.READY, reason="Phone reflex complete")
                    if isinstance(res, dict):
                        res_text = res.get("message") or res.get("result") or str(res)
                        res_url = res.get("url")
                    else:
                        res_text = str(res)
                        res_url = None

                    self._send_json({
                        "success": True,
                        "matched": True,
                        "result": res_text,
                        "url": res_url,
                        "model": "REFLEX_ENGINE",
                        "queued": True,
                        "queue_length": queue_len,
                        "state": STATE.current_state.value,
                    })
                    return
                except EmergencyStopActiveError:
                    STATE.set_state_sync(SystemState.READY, reason="Emergency stop active")
                    self._send_json({
                        "success": False,
                        "matched": True,
                        "result": "Emergency stop is active on laptop. Resume first.",
                        "model": "SECURITY_GATE",
                        "state": "EMERGENCY_STOP",
                    })
                    return
                except Exception as ex:
                    logger.error("Phone reflex error: %s", ex)
                    STATE.set_state_sync(SystemState.READY, reason="Phone reflex recovery")
                    self._send_json({
                        "success": False,
                        "error": str(ex),
                        "model": "ERROR",
                        "state": "READY",
                    })
                    return

            # 2. Local AI Tool-calling and General Reasoning
            STATE.set_state_sync(SystemState.UNDERSTANDING, reason=f"Phone query reasoning: {command}")
            try:
                tool_keywords = [
                    "open", "launch", "run", "start", "close", "kill", "terminate",
                    "file", "read", "write", "create", "delete", "screenshot",
                    "volume", "mute", "lock", "battery", "stats", "task", "app", "browser",
                    "youtube", "song", "songs", "music", "play"
                ]
                is_tool = any(k in command.lower() for k in tool_keywords)
                schemas = REGISTRY.get_tool_schemas() if is_tool else None
                category = TaskCategory.TOOL_CALLING if is_tool else TaskCategory.GENERAL

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                resp = loop.run_until_complete(
                    ROUTER.execute(
                        prompt=command,
                        category=category,
                        tools=schemas,
                        system_prompt=(
                            "You are EDITH, an autonomous AI operating system running on Windows. "
                            "You are responding to a mobile client. Answer concisely in 1 to 2 sentences."
                        ),
                    )
                )
                loop.close()

                tool_outputs = []
                if resp.tool_calls:
                    STATE.set_state_sync(SystemState.EXECUTING, reason="Executing phone tool calls")
                    for tc in resp.tool_calls:
                        out = REGISTRY.execute_tool(tc.name, tc.arguments)
                        tool_outputs.append(f"{tc.name}: {out}")

                STATE.set_state_sync(SystemState.READY, reason="Phone query complete")
                full_reply = resp.content
                if tool_outputs:
                    full_reply = f"{full_reply}\nActions: {'; '.join(tool_outputs)}"

                self._send_json({
                    "success": True,
                    "matched": False,
                    "result": full_reply,
                    "model": resp.model,
                    "queued": True,
                    "queue_length": queue_len,
                    "state": STATE.current_state.value,
                })
            except Exception as ex:
                logger.error("Phone AI reasoning error: %s", ex)
                STATE.set_state_sync(SystemState.READY, reason="Phone AI recovery")
                self._send_json({
                    "success": False,
                    "error": str(ex),
                    "model": "ERROR",
                    "state": "READY",
                })

        elif parsed.path == "/emergency_stop":
            SECURITY.trigger_emergency_stop(f"Emergency stop triggered from phone {device_id or 'client'}")
            CONFIG.emergency_stopped = True
            SPEAKER.stop()
            STATE.set_state_sync(SystemState.EMERGENCY_STOP, reason="Phone emergency stop")
            self._send_json({"success": True, "state": "EMERGENCY_STOP"})
        elif parsed.path == "/resume":
            SECURITY.reset_emergency_stop()
            CONFIG.emergency_stopped = False
            STATE.set_state_sync(SystemState.READY, reason="Phone user resumed system")
            self._send_json({"success": True, "state": "READY"})
        else:
            self._send_json({"error": "Endpoint not found"}, status=404)

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ("/ping", "/health"):
            self._send_json({"status": "ok", "time": time.time(), "system": CONFIG.system_name})
        elif parsed.path == "/status":
            stats = WIN_TOOLS.get_system_stats()
            stats["state"] = STATE.current_state.value
            stats["emergency_stopped"] = SECURITY.is_emergency_stopped
            stats["local_ip"] = get_local_ip()
            stats["cloud_url"] = TUNNEL_MANAGER.get_active_url()
            stats["active_model"] = CONFIG.primary_local_model
            self._send_json(stats)
        elif parsed.path == "/tunnel":
            self._send_json(TUNNEL_MANAGER.get_status())
        else:
            self._send_json({"error": "Endpoint not found"}, status=404)

    def _send_json(self, payload: Dict[str, Any], status: int = 200) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, format: str, *args: Any) -> None:
        pass


def create_phone_gateway(port: int = 8795, host: str = "0.0.0.0") -> ThreadingHTTPServer:
    """Instantiate the phone communication gateway server."""
    server = ThreadingHTTPServer((host, port), PhoneGatewayHandler)
    logger.info("EDITH Phone Gateway listening at http://%s:%d", host, port)
    return server
