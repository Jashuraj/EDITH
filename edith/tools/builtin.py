"""EDITH Built-in Tools Registration.

Populates ToolRegistry with all native Windows and Filesystem tools.
"""

from __future__ import annotations

from edith.core.config import CONFIG
from edith.core.security import RiskLevel
from edith.tools.filesystem import FS_TOOLS
from edith.tools.windows import WIN_TOOLS


def register_builtin_tools(registry) -> None:
    """Register all native Windows and Filesystem tools into the given registry."""
    # Windows system telemetry & battery
    registry.register(
        name="get_system_stats",
        description="Query host CPU, RAM, battery, and disk telemetry",
        action_pack="WINDOWS_PACK",
        risk=RiskLevel.LOW,
        fn=WIN_TOOLS.get_system_stats,
    )
    registry.register(
        name="battery_status",
        description="Check current battery charge percentage and power state",
        action_pack="WINDOWS_PACK",
        risk=RiskLevel.LOW,
        fn=lambda: f"Battery: {CONFIG.hardware.battery_percent}% (AC Connected: {CONFIG.hardware.is_ac_powered})",
    )

    # Windows App controls
    registry.register(
        name="open_app",
        description="Launch an allowed Windows application (browser, chrome, notepad, terminal, calc, paint, vs code, etc.)",
        action_pack="WINDOWS_PACK",
        risk=RiskLevel.LOW,
        fn=lambda app=None, **kwargs: WIN_TOOLS.launch_app(app or kwargs.get("app_name") or kwargs.get("name") or "notepad"),
        parameters_schema={"type": "object", "properties": {"app": {"type": "string"}}, "required": ["app"]},
    )
    registry.register(
        name="close_app",
        description="Close a Windows application",
        action_pack="WINDOWS_PACK",
        risk=RiskLevel.MEDIUM,
        fn=lambda app=None, **kwargs: WIN_TOOLS.kill_process(app or kwargs.get("app_name") or kwargs.get("name") or "notepad"),
        parameters_schema={"type": "object", "properties": {"app": {"type": "string"}}, "required": ["app"]},
    )

    # Audio Controls
    registry.register(
        name="mute",
        description="Mute system sound",
        action_pack="WINDOWS_PACK",
        risk=RiskLevel.LOW,
        fn=lambda **kwargs: WIN_TOOLS.set_volume("mute"),
    )
    registry.register(
        name="unmute",
        description="Unmute system sound",
        action_pack="WINDOWS_PACK",
        risk=RiskLevel.LOW,
        fn=lambda **kwargs: WIN_TOOLS.set_volume("unmute"),
    )
    registry.register(
        name="volume_up",
        description="Increase system volume",
        action_pack="WINDOWS_PACK",
        risk=RiskLevel.LOW,
        fn=lambda delta=5, **kwargs: WIN_TOOLS.set_volume("volume_up", delta=delta),
    )
    registry.register(
        name="volume_down",
        description="Decrease system volume",
        action_pack="WINDOWS_PACK",
        risk=RiskLevel.LOW,
        fn=lambda delta=-5, **kwargs: WIN_TOOLS.set_volume("volume_down", delta=delta),
    )

    # Desktop controls
    registry.register(
        name="screenshot",
        description="Take screen capture",
        action_pack="WINDOWS_PACK",
        risk=RiskLevel.LOW,
        fn=WIN_TOOLS.take_screenshot,
    )
    registry.register(
        name="lock_workstation",
        description="Lock Windows computer",
        action_pack="WINDOWS_PACK",
        risk=RiskLevel.LOW,
        fn=WIN_TOOLS.lock_workstation,
    )
    registry.register(
        name="search_youtube",
        description="Search and play a video or topic directly on YouTube",
        action_pack="WINDOWS_PACK",
        risk=RiskLevel.LOW,
        fn=lambda query="", **kwargs: WIN_TOOLS.search_youtube(query or kwargs.get("q") or kwargs.get("text") or ""),
        parameters_schema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
    )
    registry.register(
        name="search_google",
        description="Search Google for a query in the default browser",
        action_pack="WINDOWS_PACK",
        risk=RiskLevel.LOW,
        fn=lambda query="", **kwargs: WIN_TOOLS.search_google(query or kwargs.get("q") or kwargs.get("text") or ""),
        parameters_schema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
    )
    registry.register(
        name="type_text",
        description="Type text into active window or focused application",
        action_pack="WINDOWS_PACK",
        risk=RiskLevel.LOW,
        fn=lambda text="", **kwargs: WIN_TOOLS.type_text(text or kwargs.get("content") or "", target_app=kwargs.get("target_app") or kwargs.get("app")),
        parameters_schema={"type": "object", "properties": {"text": {"type": "string"}, "target_app": {"type": "string"}}, "required": ["text"]},
    )
    registry.register(
        name="press_key",
        description="Send special key press to active window (enter, tab, backspace, esc, space, select all, copy, paste, save, undo, new tab, close tab, switch window)",
        action_pack="WINDOWS_PACK",
        risk=RiskLevel.LOW,
        fn=lambda key_name="enter", **kwargs: WIN_TOOLS.press_key(key_name or kwargs.get("key") or "enter"),
        parameters_schema={"type": "object", "properties": {"key_name": {"type": "string"}}, "required": ["key_name"]},
    )
    registry.register(
        name="window_action",
        description="Control window state (show desktop, minimize all, restore windows)",
        action_pack="WINDOWS_PACK",
        risk=RiskLevel.LOW,
        fn=lambda action="show desktop", **kwargs: WIN_TOOLS.window_action(action or kwargs.get("act") or "show desktop"),
        parameters_schema={"type": "object", "properties": {"action": {"type": "string"}}, "required": ["action"]},
    )
    registry.register(
        name="open_folder",
        description="Open common user folder in File Explorer (downloads, documents, desktop, pictures, music, videos, c drive)",
        action_pack="WINDOWS_PACK",
        risk=RiskLevel.LOW,
        fn=lambda folder_name="downloads", **kwargs: WIN_TOOLS.open_folder(folder_name or kwargs.get("folder") or "downloads"),
        parameters_schema={"type": "object", "properties": {"folder_name": {"type": "string"}}, "required": ["folder_name"]},
    )
    registry.register(
        name="media_action",
        description="Control media playback and volume (play, pause, next, prev, stop, mute, volume_up, volume_down)",
        action_pack="WINDOWS_PACK",
        risk=RiskLevel.LOW,
        fn=lambda kind="play_pause", **kwargs: WIN_TOOLS.media_action(kind or kwargs.get("action") or "play_pause"),
        parameters_schema={"type": "object", "properties": {"kind": {"type": "string"}}, "required": ["kind"]},
    )
    registry.register(
        name="mouse_action",
        description="Perform mouse actions (click, double_click, right_click, scroll_up, scroll_down)",
        action_pack="WINDOWS_PACK",
        risk=RiskLevel.LOW,
        fn=lambda kind="click", amount=3, **kwargs: WIN_TOOLS.mouse_action(kind or kwargs.get("action") or "click", amount=amount or kwargs.get("steps") or 3),
        parameters_schema={"type": "object", "properties": {"kind": {"type": "string"}, "amount": {"type": "integer"}}, "required": ["kind"]},
    )
    registry.register(
        name="power_action",
        description="Trigger system power actions (lock, sleep, shutdown, restart, cancel_shutdown)",
        action_pack="WINDOWS_PACK",
        risk=RiskLevel.MEDIUM,
        fn=lambda kind="lock", **kwargs: WIN_TOOLS.power_action(kind or kwargs.get("action") or "lock"),
        parameters_schema={"type": "object", "properties": {"kind": {"type": "string"}}, "required": ["kind"]},
    )

    # Filesystem Pack
    registry.register(
        name="read_file",
        description="Read lines from a jailed workspace file",
        action_pack="FILES_PACK",
        risk=RiskLevel.LOW,
        fn=FS_TOOLS.read_file,
        parameters_schema={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
    )
    registry.register(
        name="write_file",
        description="Write text into a jailed workspace file",
        action_pack="FILES_PACK",
        risk=RiskLevel.MEDIUM,
        fn=FS_TOOLS.write_file,
        parameters_schema={"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]},
    )
    registry.register(
        name="list_dir",
        description="List files in a jailed directory",
        action_pack="FILES_PACK",
        risk=RiskLevel.LOW,
        fn=FS_TOOLS.list_dir,
    )

    # PowerShell & Autonomous Execution Pack
    registry.register(
        name="run_powershell",
        description="Execute a PowerShell command on the Windows host and capture output",
        action_pack="WINDOWS_PACK",
        risk=RiskLevel.MEDIUM,
        fn=lambda command="", **kwargs: WIN_TOOLS.run_powershell(command or kwargs.get("cmd") or ""),
        parameters_schema={"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]},
    )
    registry.register(
        name="solve_task",
        description="Autonomously solve any OS or computer task using PowerShell and commit learned procedure to memory",
        action_pack="SYSTEM_PACK",
        risk=RiskLevel.MEDIUM,
        fn=lambda goal="", **kwargs: __import__("edith.tasks.self_learner", fromlist=["SELF_LEARNER"]).SELF_LEARNER.solve_task_sync(goal or kwargs.get("task") or ""),
        parameters_schema={"type": "object", "properties": {"goal": {"type": "string"}}, "required": ["goal"]},
    )
    registry.register(
        name="get_learned_skills",
        description="List all self-learned autonomous skills and procedures",
        action_pack="SYSTEM_PACK",
        risk=RiskLevel.LOW,
        fn=lambda **kwargs: __import__("edith.tasks.self_learner", fromlist=["SELF_LEARNER"]).SELF_LEARNER.get_learned_skills(),
    )

    # Audio & Clap Welcome Pack
    registry.register(
        name="start_clap_detector",
        description="Activate microphone double-clap welcome listener",
        action_pack="VOICE_PACK",
        risk=RiskLevel.LOW,
        fn=lambda **kwargs: __import__("edith.voice.clap_detector", fromlist=["CLAP_DETECTOR"]).CLAP_DETECTOR.start(),
    )
    registry.register(
        name="stop_clap_detector",
        description="Deactivate microphone double-clap welcome listener",
        action_pack="VOICE_PACK",
        risk=RiskLevel.LOW,
        fn=lambda **kwargs: __import__("edith.voice.clap_detector", fromlist=["CLAP_DETECTOR"]).CLAP_DETECTOR.stop(),
    )

    # Screen & Optical Vision Pack
    registry.register(
        name="analyze_screen",
        description="Look at user screen, analyze active desktop windows, and describe visible content",
        action_pack="WINDOWS_PACK",
        risk=RiskLevel.LOW,
        fn=lambda prompt="What do you see on my screen?", **kwargs: __import__("edith.tools.vision", fromlist=["VISION"]).VISION.analyze_screen(prompt or kwargs.get("text") or "What do you see on my screen?"),
        parameters_schema={"type": "object", "properties": {"prompt": {"type": "string"}}},
    )

    # System Optimizer Pack
    registry.register(
        name="optimize_system",
        description="Trim memory working set, flush Windows DNS cache, and purge temporary file cache",
        action_pack="WINDOWS_PACK",
        risk=RiskLevel.LOW,
        fn=lambda **kwargs: __import__("edith.tools.system_optimizer", fromlist=["optimize_system"]).optimize_system(),
    )
