"""Local UI Server and State Airlock for EDITH.

Implements Sections 55, 56, 57 of the Engineering Constitution.
Integrates live local LLM inference, Level 0 Reflex, Windows automation tools,
audio synthesis endpoints, dynamic hardware telemetry, In-HUD media playback,
and native Win32 gestural mouse control.
"""

from __future__ import annotations

import asyncio
import json
import logging
import urllib.parse
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional

from edith.core.config import CONFIG
from edith.core.logger import get_recent_logs
from edith.core.security import SECURITY, EmergencyStopActiveError
from edith.core.state_machine import STATE, SystemState
from edith.providers.router import ROUTER, TaskCategory
from edith.tools.mouse_controller import MOUSE
from edith.tools.reflex import REFLEX
from edith.tools.registry import REGISTRY
from edith.tools.windows import WIN_TOOLS
from edith.voice.speaker import SPEAKER

logger = logging.getLogger("edith.ui.server")

UI_DIR = Path(__file__).resolve().parent / "public"
STATE_DIR = Path(__file__).resolve().parent / "state"


class EdithUIHandler(SimpleHTTPRequestHandler):
    """Custom HTTP handler serving the holographic frontend and REST API."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(UI_DIR), **kwargs)

    def end_headers(self) -> None:
        """Inject cache-busting headers for local assets."""
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def do_OPTIONS(self) -> None:
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, Bypass-Tunnel-Reminder")
        self.end_headers()

    def do_GET(self) -> None:
        """Handle status, telemetry, and static file requests."""
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/state":
            if STATE.current_state == SystemState.BOOTING:
                STATE.set_state_sync(SystemState.READY, reason="UI connected")
            self._send_json({
                "state": STATE.current_state.value.lower(),
                "emergency_stopped": SECURITY.is_emergency_stopped,
                "privacy_mode": SECURITY.is_privacy_mode,
            })

        elif parsed.path == "/telemetry":
            dyn = CONFIG.refresh_dynamic_stats()
            stats = WIN_TOOLS.get_system_stats()
            stats.update({
                "state": STATE.current_state.value,
                "system_name": CONFIG.system_name,
                "creator": CONFIG.creator,
                "primary_model": CONFIG.primary_local_model,
                "manual_mode": CONFIG.manual_mode,
                "is_online": dyn.get("online", False),
                "runtime_status": dyn.get("status_text", "ONLINE (HYBRID AI)"),
            })
            self._send_json(stats)

        elif parsed.path == "/api/mode":
            dyn = CONFIG.refresh_dynamic_stats()
            self._send_json({
                "manual_mode": CONFIG.manual_mode,
                "offline_mode": CONFIG.offline_mode,
                "is_online": dyn.get("online", False),
                "status_text": dyn.get("status_text", ""),
            })

        elif parsed.path == "/api/logs":
            q_lines = 150
            if "lines=" in parsed.query:
                try:
                    q_lines = int(parsed.query.split("lines=")[1].split("&")[0])
                except Exception:
                    pass
            content = get_recent_logs(lines=q_lines)
            self._send_json({"logs": content, "count": len(content.splitlines())})

        elif parsed.path == "/models":
            try:
                from edith.providers.ollama_provider import OLLAMA
                loop = asyncio.new_event_loop()
                models = loop.run_until_complete(OLLAMA.list_models())
                loop.close()
            except Exception:
                models = []
            if not models:
                models = ["hermes3:3b", "llama3.2:1b", "tinydolphin:1.1b", "gemma3:1b"]
            self._send_json({
                "models": models,
                "active_model": CONFIG.primary_local_model,
            })

        elif parsed.path == "/weather":
            try:
                req = urllib.request.Request(
                    "https://wttr.in/?format=j1",
                    headers={"User-Agent": "curl/7.68.0"}
                )
                with urllib.request.urlopen(req, timeout=2.5) as r:
                    wdata = json.loads(r.read().decode())
                    current = wdata["current_condition"][0]
                    area = wdata["nearest_area"][0]
                    self._send_json({
                        "temp": current.get("temp_C", "24"),
                        "desc": current["weatherDesc"][0]["value"] if current.get("weatherDesc") else "Clear",
                        "city": area["areaName"][0]["value"] if area.get("areaName") else "Local Station",
                        "humidity": current.get("humidity", "45"),
                        "wind_kmh": current.get("windspeedKmph", "10"),
                    })
                    return
            except Exception:
                pass
            self._send_json({"temp": "24", "desc": "Clear Skies", "city": "Local Station", "wind_kmh": "12"})

        elif parsed.path == "/voice/mute_status":
            self._send_json({"muted": SPEAKER.is_muted})

        elif parsed.path == "/audio/devices":
            try:
                import sounddevice as sd
                from edith.voice.clap_detector import CLAP_DETECTOR
                devs = sd.query_devices()
                inputs = []
                for idx, d in enumerate(devs):
                    if d.get("max_input_channels", 0) > 0:
                        name = d.get("name", "")
                        is_bt = any(t in name.lower() for t in ["headset", "bluetooth", "buds", "pods", "hands-free"])
                        if CLAP_DETECTOR._is_device_openable(idx):
                            inputs.append({
                                "index": idx,
                                "name": name,
                                "is_bluetooth": is_bt,
                                "channels": d.get("max_input_channels", 0),
                            })
                active_dev = CLAP_DETECTOR.selected_device if CLAP_DETECTOR.selected_device is not None else CLAP_DETECTOR.get_preferred_input_device()
                self._send_json({
                    "devices": inputs,
                    "active_index": active_dev,
                    "has_bluetooth": any(i["is_bluetooth"] for i in inputs),
                })
            except Exception as e:
                self._send_json({"devices": [], "error": str(e)})

        elif parsed.path == "/vision/analyze_screen":
            from edith.tools.vision import VISION
            res = VISION.analyze_screen()
            self._send_json(res)

        elif parsed.path in ("/ping", "/health"):
            self._send_json({"status": "ok", "system": CONFIG.system_name})

        elif parsed.path == "/mobile/config":
            import socket
            local_ip = "127.0.0.1"
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
            except Exception:
                pass
            from edith.phone.tunnel import TUNNEL_MANAGER
            self._send_json({
                "system_name": CONFIG.system_name,
                "local_ip": local_ip,
                "ui_port": 8794,
                "phone_port": 8795,
                "cloud_url": TUNNEL_MANAGER.get_active_url(),
                "tunnel_status": TUNNEL_MANAGER.get_status(),
            })

        elif parsed.path == "/api/tunnel":
            from edith.phone.tunnel import TUNNEL_MANAGER
            self._send_json(TUNNEL_MANAGER.get_status())

        # Clean redirect for /mobile to /mobile/ to preserve relative paths
        elif parsed.path == "/mobile":
            self.send_response(302)
            self.send_header("Location", "/mobile/")
            self.end_headers()
            return
        elif parsed.path == "/mobile/":
            self.path = "/mobile/index.html"
            super().do_GET()
        elif parsed.path == "/" or parsed.path == "/index.html":
            self.path = "/index.html"
            super().do_GET()
        else:
            super().do_GET()

    def do_POST(self) -> None:
        """Handle incoming command, voice, and emergency stop posts."""
        parsed = urllib.parse.urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"

        try:
            data = json.loads(body)
        except Exception:
            data = {}

        if parsed.path == "/cmd":
            command = data.get("command", "").strip()
            if not command:
                self._send_json({"matched": False, "result": "Empty command provided", "state": "READY"})
                return

            # 1. Level 0 Reflex Fast Path (<15ms)
            match = REFLEX.evaluate(command)
            if match:
                try:
                    STATE.set_state_sync(SystemState.EXECUTING, reason="Executing Level 0 reflex")
                    res = REFLEX.execute_match(match, executor=lambda name, params: REGISTRY.execute_tool(name, params))
                    STATE.set_state_sync(SystemState.READY, reason="Reflex complete")
                    if isinstance(res, dict):
                        res_text = res.get("message") or res.get("result") or str(res)
                        res_url = res.get("url")
                        res_embed = res.get("embed_url")
                        res_vid = res.get("video_id")
                        res_opened = res.get("opened_on_host", False)
                    else:
                        res_text = str(res)
                        res_url = None
                        res_embed = None
                        res_vid = None
                        res_opened = False

                    self._send_json({
                        "matched": True,
                        "result": res_text,
                        "url": res_url,
                        "embed_url": res_embed,
                        "video_id": res_vid,
                        "opened_on_host": res_opened,
                        "model": "REFLEX_ENGINE",
                        "server_spoken": False,
                        "state": STATE.current_state.value,
                    })
                    return
                except EmergencyStopActiveError:
                    STATE.set_state_sync(SystemState.READY, reason="Emergency stop active")
                    stop_msg = "Emergency stop is currently engaged. Click RESUME or say 'resume' to proceed."
                    self._send_json({
                        "matched": True,
                        "result": stop_msg,
                        "model": "SECURITY_GATE",
                        "server_spoken": False,
                        "state": "EMERGENCY_STOP",
                    })
                    return
                except Exception as ex:
                    logger.error("Reflex execution error: %s", ex)
                    STATE.set_state_sync(SystemState.READY, reason="Reflex error recovery")
                    err_text = f"Action error: {ex}"
                    SPEAKER.speak(err_text, async_mode=True)
                    self._send_json({
                        "matched": True,
                        "result": err_text,
                        "model": "ERROR",
                        "server_spoken": True,
                        "state": "READY",
                    })
                    return

            # 2. Local AI Tool-Calling and Reasoning
            STATE.set_state_sync(SystemState.UNDERSTANDING, reason="Analyzing query via model router")
            try:
                tool_keywords = [
                    "open", "launch", "run", "start", "close", "kill", "terminate",
                    "file", "read", "write", "create", "delete", "screenshot",
                    "volume", "mute", "lock", "battery", "stats", "task", "app", "browser",
                    "youtube", "song", "songs", "music", "play"
                ]
                is_tool_intent = any(k in command.lower() for k in tool_keywords)
                schemas = REGISTRY.get_tool_schemas() if is_tool_intent else None
                category = TaskCategory.TOOL_CALLING if is_tool_intent else TaskCategory.GENERAL

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                resp = loop.run_until_complete(
                    ROUTER.execute(
                        prompt=command,
                        category=category,
                        tools=schemas,
                        system_prompt=(
                            "You are EDITH, a concise, autonomous local-first AI operating system "
                            "created by Jashwanth Raj. You run on Windows. If asked to control or check "
                            "the system, invoke the appropriate tools. Answer concisely in 1 to 2 sentences."
                        ),
                    )
                )
                loop.close()

                tool_outputs = []
                action_url = None
                action_embed_url = None
                action_video_id = None
                action_opened = False

                if resp.tool_calls:
                    STATE.set_state_sync(SystemState.EXECUTING, reason="Executing agent tools")
                    for tc in resp.tool_calls:
                        try:
                            kwargs = dict(tc.arguments)
                            # Pass open_browser=False for in-HUD media playback
                            if tc.name == "search_youtube" and "open_browser" not in kwargs:
                                kwargs["open_browser"] = False

                            out = REGISTRY.execute_tool(tc.name, kwargs)
                            if isinstance(out, dict):
                                if out.get("url"):
                                    action_url = out["url"]
                                if out.get("embed_url"):
                                    action_embed_url = out["embed_url"]
                                if out.get("video_id"):
                                    action_video_id = out["video_id"]
                                if out.get("opened_on_host"):
                                    action_opened = out["opened_on_host"]
                            out_display = out.get("message") if isinstance(out, dict) and out.get("message") else str(out)
                            tool_outputs.append(f"[{tc.name}]: {out_display}")
                        except Exception as te:
                            logger.warning("Tool execution error for %s: %s", tc.name, te)
                            tool_outputs.append(f"[{tc.name}]: Execution notice - {te}")

                final_text = resp.content.strip()
                if tool_outputs:
                    prefix = "\n".join(tool_outputs)
                    final_text = f"{prefix}\n\n{final_text}" if final_text else prefix

                if not final_text:
                    final_text = "Action executed successfully, sir."

                STATE.set_state_sync(SystemState.READY, reason="Command processing complete")
                self._send_json({
                    "matched": False,
                    "result": final_text,
                    "url": action_url,
                    "embed_url": action_embed_url,
                    "video_id": action_video_id,
                    "opened_on_host": action_opened,
                    "model": resp.model,
                    "server_spoken": False,
                    "tools_executed": tool_outputs,
                    "state": "READY",
                })
            except Exception as e:
                logger.error("Command execution error: %s", e)
                STATE.set_state_sync(SystemState.READY, reason="Error recovery")
                err_msg = f"System notice: {str(e)}"
                self._send_json({
                    "matched": False,
                    "result": err_msg,
                    "model": "FALLBACK",
                    "server_spoken": False,
                    "state": "READY",
                })

        elif parsed.path == "/api/mouse":
            action = data.get("action", "")
            res = MOUSE.handle_gesture_action(action, data)
            self._send_json(res)

        elif parsed.path == "/api/mode":
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

        elif parsed.path == "/voice/speak":
            text = data.get("text", "")
            success = SPEAKER.speak(text, async_mode=True) if text else False
            self._send_json({"success": success})

        elif parsed.path == "/voice/stop":
            SPEAKER.stop()
            self._send_json({"success": True})

        elif parsed.path == "/voice/toggle_mute":
            new_muted = SPEAKER.toggle_muted()
            self._send_json({"success": True, "muted": new_muted})

        elif parsed.path == "/voice/mute":
            should_mute = data.get("mute", True)
            SPEAKER.set_muted(should_mute)
            self._send_json({"success": True, "muted": SPEAKER.is_muted})

        elif parsed.path == "/audio/select":
            dev_idx = data.get("device_index")
            from edith.voice.clap_detector import CLAP_DETECTOR
            if dev_idx is not None:
                CLAP_DETECTOR.set_input_device(int(dev_idx))
                self._send_json({"success": True, "active_index": int(dev_idx)})
            else:
                self._send_json({"success": False, "error": "No device index provided"}, status=400)

        elif parsed.path == "/vision/analyze_screen":
            prompt = data.get("prompt", "What do you see on my screen?")
            from edith.tools.vision import VISION
            res = VISION.analyze_screen(prompt=prompt)
            self._send_json(res)

        elif parsed.path == "/models/switch":
            new_model = data.get("model", "").strip()
            if new_model:
                CONFIG.primary_local_model = new_model
                from edith.providers.ollama_provider import OLLAMA
                OLLAMA.set_model(new_model)
                self._send_json({
                    "success": True,
                    "active_model": new_model,
                    "message": f"Primary local model switched to {new_model}"
                })
            else:
                self._send_json({"success": False, "error": "No model specified"}, status=400)

        elif parsed.path == "/emergency_stop":
            if SECURITY.is_emergency_stopped:
                SECURITY.reset_emergency_stop()
                CONFIG.emergency_stopped = False
                STATE.set_state_sync(SystemState.READY, reason="Emergency stop cleared")
                self._send_json({"success": True, "state": "READY", "emergency_stopped": False})
            else:
                SECURITY.trigger_emergency_stop("UI Emergency Button Pressed")
                CONFIG.emergency_stopped = True
                SPEAKER.stop()
                STATE.set_state_sync(SystemState.EMERGENCY_STOP, reason="UI Emergency Stop")
                self._send_json({"success": True, "state": "EMERGENCY_STOP", "emergency_stopped": True})

        elif parsed.path == "/emergency_resume":
            SECURITY.reset_emergency_stop()
            CONFIG.emergency_stopped = False
            STATE.set_state_sync(SystemState.READY, reason="User resumed system")
            self._send_json({"success": True, "state": "READY", "emergency_stopped": False})

        elif parsed.path == "/api/tunnel":
            from edith.phone.tunnel import TUNNEL_MANAGER
            action = data.get("action", "status")
            if action == "start":
                provider = data.get("provider", "pinggy")
                url = TUNNEL_MANAGER.start_tunnel(provider=provider, port=8794)
                self._send_json({"success": bool(url), "tunnel_url": url, "provider": provider})
            elif action == "stop":
                TUNNEL_MANAGER.stop_tunnel()
                self._send_json({"success": True, "tunnel_url": None})
            elif action == "set_custom":
                custom_url = data.get("url", "").strip()
                url = TUNNEL_MANAGER.set_custom_url(custom_url)
                self._send_json({"success": True, "tunnel_url": url})
            else:
                self._send_json(TUNNEL_MANAGER.get_status())

        else:
            self.send_error(404, "Endpoint not found")

    def _send_json(self, payload: Dict[str, Any], status: int = 200) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, Bypass-Tunnel-Reminder")
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress standard access logs to avoid terminal noise."""
        pass


def create_ui_server(port: int = 8794, host: str = "0.0.0.0") -> ThreadingHTTPServer:
    """Instantiate the UI server."""
    UI_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((host, port), EdithUIHandler)
    logger.info("EDITH UI Server ready at http://%s:%d", host, port)
    return server
