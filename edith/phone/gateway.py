"""Local Phone Gateway Server for Paired Mobile Clients & Remote Desktop.

Implements Sections 69, 70, 71, 74 of the Engineering Constitution.
Supports WiFi LAN and Cloud Internet remote access. Serves mobile PWA directly
on port 8795, real-time screen streaming, zero-latency touch/keyboard/joystick controls,
and bi-directional PC <-> Mobile communication.
"""

from __future__ import annotations

import asyncio
import json
import logging
import socket
import time
import urllib.parse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional

from edith.core.config import CONFIG
from edith.core.security import SECURITY, EmergencyStopActiveError
from edith.core.state_machine import STATE, SystemState
from edith.phone.protocol import PHONE_PROTOCOL
from edith.phone.tunnel import TUNNEL_MANAGER
from edith.providers.router import ROUTER, TaskCategory
from edith.tools.reflex import REFLEX
from edith.tools.registry import REGISTRY
from edith.tools.remote_input import REMOTE_INPUT
from edith.tools.screen_stream import SCREEN_STREAMER
from edith.tools.windows import WIN_TOOLS
from edith.voice.speaker import SPEAKER

logger = logging.getLogger("edith.phone.gateway")

MOBILE_DIR = Path(__file__).resolve().parent.parent / "ui" / "public" / "mobile"


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
    """HTTP endpoint handler for paired phone devices and mobile PWA assets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(MOBILE_DIR), **kwargs)

    def end_headers(self) -> None:
        """Inject cache and CORS headers."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, Bypass-Tunnel-Reminder, X-Token")
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

        # 1. Device Pairing
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

        # 2. System Mode Switch
        if parsed.path == "/api/mode":
            mode = data.get("mode", "auto")
            new_mode = CONFIG.set_manual_mode(mode)
            dyn = CONFIG.refresh_dynamic_stats()
            self._send_json({
                "success": True,
                "manual_mode": new_mode,
                "offline_mode": CONFIG.offline_mode,
                "is_online": dyn.get("online", False),
                "status_text": dyn.get("status_text", ""),
            })
            return

        # Authenticate operations when paired tokens exist
        device_id = str(data.get("device_id", "")).strip()
        token = str(data.get("token", "")).strip() or str(self.headers.get("X-Token", "")).strip()

        if PHONE_PROTOCOL._paired_devices:
            if not PHONE_PROTOCOL.verify_token(device_id, token):
                self._send_json({"error": "Unauthorized device token."}, status=401)
                return

        # 3. Remote Input Dispatcher (Mouse, Keyboard, Joystick, Gamepad)
        if parsed.path in ("/api/remote/input", "/api/mouse"):
            action = data.get("action", "")
            params = data.get("params", data)
            res = REMOTE_INPUT.dispatch(action, params)
            self._send_json(res)
            return

        # 4. Bi-Directional Clipboard Sync
        if parsed.path == "/api/clipboard/sync":
            text = str(data.get("text", ""))
            sync_res = PHONE_PROTOCOL.sync_clipboard_from_phone(text, device_id or "mobile")
            sync_res["laptop_clipboard"] = PHONE_PROTOCOL.get_current_clipboard()
            self._send_json(sync_res)
            return

        # 5. PC Sends Command/Push Message to Connected Phone
        if parsed.path == "/api/phone/send_command":
            target_device_id = str(data.get("target_device_id", "edith_mobile_pwa")).strip()
            msg = data.get("message", data)
            PHONE_PROTOCOL.send_message_to_phone(target_device_id, msg)
            self._send_json({"success": True, "target": target_device_id})
            return

        # 6. Tunnel Controls
        if parsed.path in ("/api/tunnel", "/api/tunnel/start"):
            action = str(data.get("action", "start")).strip().lower()
            if action == "stop":
                TUNNEL_MANAGER.stop_tunnel()
                self._send_json({"success": True, "tunnel_url": None, "url": None})
                return
            elif action == "set_custom":
                custom_url = str(data.get("url", "")).strip()
                active_url = TUNNEL_MANAGER.set_custom_url(custom_url)
                self._send_json({"success": True, "active_url": active_url, "tunnel_url": active_url, "url": active_url})
                return
            provider = str(data.get("provider", "localtunnel")).strip()
            port = int(data.get("port", 8794))
            url = TUNNEL_MANAGER.start_tunnel(provider=provider, port=port)
            self._send_json({"success": bool(url), "url": url, "tunnel_url": url, "provider": provider})
            return

        if parsed.path == "/api/tunnel/custom":
            custom_url = str(data.get("url", "")).strip()
            active_url = TUNNEL_MANAGER.set_custom_url(custom_url)
            self._send_json({"success": True, "active_url": active_url, "tunnel_url": active_url, "url": active_url})
            return

        # 7. Standard Command Execution
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

            # Level 0 Reflex Fast Path
            match = REFLEX.evaluate(command)
            if match:
                try:
                    STATE.set_state_sync(SystemState.EXECUTING, reason=f"Executing reflex from phone: {command}")
                    res = REFLEX.execute_match(match, executor=lambda name, params: REGISTRY.execute_tool(name, params))
                    STATE.set_state_sync(SystemState.READY, reason="Phone reflex complete")
                    if isinstance(res, dict):
                        res_text = res.get("message") or res.get("result") or str(res)
                        res_url = res.get("url")
                        res_embed = res.get("embed_url")
                        res_vid = res.get("video_id")
                    else:
                        res_text = str(res)
                        res_url = None
                        res_embed = None
                        res_vid = None

                    self._send_json({
                        "success": True,
                        "matched": True,
                        "result": res_text,
                        "url": res_url,
                        "embed_url": res_embed,
                        "video_id": res_vid,
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

            # Local AI Reasoning
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
                action_url = None
                action_embed = None
                action_vid = None

                if resp.tool_calls:
                    STATE.set_state_sync(SystemState.EXECUTING, reason="Executing phone tool calls")
                    for tc in resp.tool_calls:
                        kwargs = dict(tc.arguments)
                        if tc.name == "search_youtube" and "open_browser" not in kwargs:
                            kwargs["open_browser"] = False
                        out = REGISTRY.execute_tool(tc.name, kwargs)
                        if isinstance(out, dict):
                            if out.get("url"): action_url = out["url"]
                            if out.get("embed_url"): action_embed = out["embed_url"]
                            if out.get("video_id"): action_vid = out["video_id"]
                        tool_outputs.append(f"{tc.name}: {out}")

                STATE.set_state_sync(SystemState.READY, reason="Phone query complete")
                full_reply = resp.content
                if tool_outputs:
                    full_reply = f"{full_reply}\nActions: {'; '.join(tool_outputs)}"

                self._send_json({
                    "success": True,
                    "matched": False,
                    "result": full_reply,
                    "url": action_url,
                    "embed_url": action_embed,
                    "video_id": action_vid,
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
        query_params = urllib.parse.parse_qs(parsed.query)

        # Token authentication check for restricted endpoints
        if PHONE_PROTOCOL._paired_devices:
            token = query_params.get("token", [None])[0] or self.headers.get("X-Token")
            device_id = query_params.get("device_id", [None])[0]
            # Verify if accessing remote stream or controls
            if parsed.path in ("/stream/screen", "/api/screen/capture", "/api/remote/status"):
                if not PHONE_PROTOCOL.verify_token(device_id or "", token or ""):
                    self._send_json({"error": "Unauthorized device token."}, status=401)
                    return

        # 1. Real-Time Screen Streaming (MJPEG)
        if parsed.path in ("/stream/screen", "/stream/mjpeg"):
            fps = int(query_params.get("fps", [20])[0])
            scale = int(query_params.get("scale", [1280])[0])
            quality = int(query_params.get("quality", [60])[0])

            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.send_header("Cache-Control", "no-cache, private")
            self.send_header("Pragma", "no-cache")
            self.end_headers()

            try:
                for frame in SCREEN_STREAMER.generate_mjpeg_stream(fps=fps, scale_width=scale, quality=quality):
                    self.wfile.write(frame)
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                logger.debug("Mobile screen stream client disconnected.")
            except Exception as ex:
                logger.error("Screen stream error: %s", ex)
            return

        # 2. Single Frame Snapshot Capture
        elif parsed.path == "/api/screen/capture":
            scale = int(query_params.get("scale", [1280])[0])
            quality = int(query_params.get("quality", [65])[0])
            data = SCREEN_STREAMER.capture_jpeg_bytes(scale_width=scale, quality=quality)
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-cache, no-store")
            self.end_headers()
            self.wfile.write(data)
            return

        # 3. Remote Desktop & Streamer Status
        elif parsed.path == "/api/remote/status":
            stats = SCREEN_STREAMER.get_stats()
            self._send_json({
                "streamer": stats,
                "input_active": True,
                "system": CONFIG.system_name,
            })
            return

        # 4. Device Telemetry & Bi-directional Messages
        elif parsed.path == "/api/phone/devices":
            self._send_json({"devices": PHONE_PROTOCOL.get_paired_devices()})
            return

        elif parsed.path == "/api/phone/messages":
            dev_id = query_params.get("device_id", [""])[0] or "edith_mobile_pwa"
            battery_str = query_params.get("battery", [None])[0]
            conn = query_params.get("conn", [None])[0]
            battery = int(float(battery_str)) if battery_str not in (None, "", "null") else None
            PHONE_PROTOCOL.update_device_heartbeat(
                dev_id,
                battery_percent=battery,
                connection_type=conn,
            )
            msgs = PHONE_PROTOCOL.poll_messages_for_phone(dev_id)
            self._send_json({"messages": msgs, "count": len(msgs)})
            return

        elif parsed.path == "/api/clipboard":
            self._send_json({"clipboard": PHONE_PROTOCOL.get_current_clipboard()})
            return

        elif parsed.path in ("/ping", "/health"):
            self._send_json({"status": "ok", "time": time.time(), "system": CONFIG.system_name})

        elif parsed.path == "/status":
            stats = WIN_TOOLS.get_system_stats()
            dyn = CONFIG.refresh_dynamic_stats()
            stats["state"] = STATE.current_state.value
            stats["emergency_stopped"] = SECURITY.is_emergency_stopped
            stats["local_ip"] = get_local_ip()
            stats["cloud_url"] = TUNNEL_MANAGER.get_active_url()
            stats["active_model"] = CONFIG.primary_local_model
            stats["manual_mode"] = CONFIG.manual_mode
            stats["is_online"] = dyn.get("online", False)
            self._send_json(stats)

        elif parsed.path == "/api/mode":
            dyn = CONFIG.refresh_dynamic_stats()
            self._send_json({
                "manual_mode": CONFIG.manual_mode,
                "offline_mode": CONFIG.offline_mode,
                "is_online": dyn.get("online", False),
                "status_text": dyn.get("status_text", ""),
            })

        elif parsed.path == "/mobile/config":
            self._send_json({
                "system_name": CONFIG.system_name,
                "local_ip": get_local_ip(),
                "ui_port": 8794,
                "phone_port": 8795,
                "cloud_url": TUNNEL_MANAGER.get_active_url(),
                "tunnel_status": TUNNEL_MANAGER.get_status(),
            })

        elif parsed.path == "/tunnel":
            self._send_json(TUNNEL_MANAGER.get_status())

        elif parsed.path in ("/", "/index.html", "/mobile", "/mobile/"):
            self.path = "/index.html"
            super().do_GET()

        else:
            super().do_GET()

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
    MOBILE_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((host, port), PhoneGatewayHandler)
    logger.info("EDITH Phone Gateway listening at http://%s:%d", host, port)
    return server
