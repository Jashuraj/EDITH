"""EDITH Master Command-Line Interface and Daemon Entrypoint.

Usage:
  python -m edith.main doctor
  python -m edith.main run "open chrome"
  python -m edith.main serve
  python -m edith.main stop
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import threading
import time

logger = logging.getLogger("edith.main")

from edith.core.config import CONFIG
from edith.core.doctor import DOCTOR
from edith.core.security import SECURITY
from edith.core.state_machine import STATE, SystemState
from edith.phone.gateway import create_phone_gateway
from edith.providers.router import ROUTER, TaskCategory
from edith.tools.filesystem import FS_TOOLS
from edith.tools.reflex import REFLEX
from edith.tools.registry import REGISTRY, RiskLevel
from edith.tools.windows import WIN_TOOLS
from edith.ui.server import create_ui_server


def setup_builtin_tools() -> None:
    """Register all native Windows and Filesystem tools into action packs."""
    from edith.tools.builtin import register_builtin_tools
    register_builtin_tools(REGISTRY)


async def run_doctor() -> None:
    """Print system diagnostics report."""
    print("=" * 65)
    print(f"  {CONFIG.system_name} SYSTEM HEALTH DIAGNOSTICS")
    print(f"  Developer / Creator: {CONFIG.creator}")
    print("=" * 65)
    items = await DOCTOR.run_diagnostics()
    for item in items:
        badge = f"[{item.status}]"
        print(f"  {badge:<8} {item.name:<24} {item.details}")
    print("=" * 65)


async def execute_command(cmd: str) -> None:
    """Process a single instruction via Level 0 Reflex or ModelRouter."""
    setup_builtin_tools()

    if STATE.current_state == SystemState.BOOTING:
        await STATE.transition_to(SystemState.READY, reason="CLI ready")

    print(f"\n[USER COMMAND]: '{cmd}'")
    t0 = time.perf_counter()

    # 1. Level 0 Deterministic Reflex
    match = REFLEX.evaluate(cmd)
    if match:
        await STATE.transition_to(SystemState.EXECUTING, reason="Executing Level 0 reflex")
        result = REFLEX.execute_match(match, executor=lambda name, params: REGISTRY.execute_tool(name, params))
        await STATE.transition_to(SystemState.READY, reason="Reflex complete")
        dt_ms = (time.perf_counter() - t0) * 1000.0
        print(f"[LEVEL 0 REFLEX - {dt_ms:.1f}ms]: {result}")
        return

    # 2. Local AI Tool Calling / Hermes 3B
    await STATE.transition_to(SystemState.UNDERSTANDING, reason="Analyzing command via local model")
    schemas = REGISTRY.get_tool_schemas()
    try:
        resp = await ROUTER.execute(
            prompt=cmd,
            category=TaskCategory.TOOL_CALLING,
            tools=schemas,
            system_prompt="You are EDITH, a concise local-first operating system. Use tools when needed.",
        )
        await STATE.transition_to(SystemState.READY, reason="Model response complete")
        dt_ms = (time.perf_counter() - t0) * 1000.0
        print(f"[{resp.model} - {dt_ms:.1f}ms]: {resp.content}")
        if resp.tool_calls:
            for tc in resp.tool_calls:
                print(f"  -> Invoking tool: {tc.name}({tc.arguments})")
                out = REGISTRY.execute_tool(tc.name, tc.arguments)
                print(f"  -> Result: {out}")
    except Exception as e:
        await STATE.transition_to(SystemState.ERROR, reason=str(e))
        print(f"[ERROR]: {e}")


def serve_all(ui_port: int = 8794, phone_port: int = 8795) -> None:
    """Launch UI server and Phone gateway concurrently."""
    setup_builtin_tools()

    # Transition BOOTING -> READY after servers bind
    STATE._current_state = SystemState.BOOTING
    STATE._sync_mirror_file()

    ui_srv = create_ui_server(port=ui_port)
    phone_srv = create_phone_gateway(port=phone_port)

    t_ui = threading.Thread(target=ui_srv.serve_forever, daemon=True)
    t_phone = threading.Thread(target=phone_srv.serve_forever, daemon=True)
    t_ui.start()
    t_phone.start()

    STATE.set_state_sync(SystemState.READY, reason="EDITH daemon servers online")

    # Start double clap welcome listener in background (disabled by default)
    clap_active = False
    if CONFIG.clap_welcome_enabled:
        try:
            from edith.voice.clap_detector import CLAP_DETECTOR
            CLAP_DETECTOR.start()
            clap_active = True
        except Exception as ex:
            logger.warning("Could not initialize clap detector: %s", ex)

    # Retrieve LAN IP for phone pairing
    import socket
    local_ip = "127.0.0.1"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass

    # Start Cloud Tunnel in background for global remote access
    from edith.phone.tunnel import TUNNEL_MANAGER
    def _run_tunnel():
        try:
            url = TUNNEL_MANAGER.start_tunnel(port=ui_port)
            if url:
                print(f"  >>> [GLOBAL CLOUD LINK ACTIVE]: {url}")
        except Exception as ex:
            logger.warning("Cloud tunnel initial connection notice: %s", ex)

    t_tun = threading.Thread(target=_run_tunnel, daemon=True)
    t_tun.start()

    cloud_display = TUNNEL_MANAGER.get_active_url() or "Connecting in background..."

    print("=" * 65)
    print(f"  {CONFIG.system_name} SERVERS ACTIVE (0.0.0.0)")
    print(f"  • Holographic UI:    http://127.0.0.1:{ui_port} (LAN: http://{local_ip}:{ui_port})")
    print(f"  • Phone Gateway:     http://127.0.0.1:{phone_port} (LAN: http://{local_ip}:{phone_port})")
    print(f"  • Mobile App:        http://{local_ip}:{ui_port}/mobile")
    print(f"  • Global Cloud Link: {cloud_display}")
    if clap_active:
        print("  • Double-Clap Welcome: ACTIVE (Local SAPI Voice)")
    print("  Press Ctrl+C to terminate.")
    print("=" * 65)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down EDITH servers...")
        if clap_active:
            try:
                from edith.voice.clap_detector import CLAP_DETECTOR
                CLAP_DETECTOR.stop()
            except Exception:
                pass
        ui_srv.shutdown()
        phone_srv.shutdown()


def main() -> None:
    parser = argparse.ArgumentParser(description="EDITH Operating System")
    subparsers = parser.add_subparsers(dest="command", help="Subcommand to execute")

    subparsers.add_parser("doctor", help="Run system diagnostics")
    run_parser = subparsers.add_parser("run", help="Run a natural language command")
    run_parser.add_argument("query", type=str, help="Utterance or instruction")

    subparsers.add_parser("serve", help="Start UI and Phone servers")
    subparsers.add_parser("stop", help="Trigger emergency stop")

    args = parser.parse_args()

    if args.command == "doctor":
        asyncio.run(run_doctor())
    elif args.command == "run":
        asyncio.run(execute_command(args.query))
    elif args.command == "serve":
        serve_all()
    elif args.command == "stop":
        SECURITY.trigger_emergency_stop("CLI Stop")
        print("EMERGENCY STOP engaged.")
    else:
        # Launch server daemon by default (e.g. double-clicking EDITH.exe)
        serve_all()


if __name__ == "__main__":
    main()
