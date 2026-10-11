"""Level 0 Deterministic Reflex Engine for EDITH.

Matches common voice and text intents via compiled regex patterns and dispatches
direct OS actions in <15ms without querying an LLM.
"""

from __future__ import annotations

import logging
import re
import subprocess
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from edith.core.config import CONFIG
from edith.core.security import SECURITY

logger = logging.getLogger("edith.reflex")


@dataclass
class ReflexMatch:
    """Outcome of reflex pattern evaluation."""
    matched: bool
    command_name: str
    action_type: str
    params: Dict[str, Any]
    duration_ms: float


class ReflexEngine:
    """Deterministic regex pattern matcher and instant command dispatcher."""

    def __init__(self):
        self._patterns: List[Tuple[re.Pattern, str, str, Dict[str, Any]]] = []
        self._register_default_reflexes()

    def _register_default_reflexes(self) -> None:
        """Register the 16 core deterministic intents defined in Section 16."""
        # Open / Close Applications
        app_prefix = r"^(?:(?:hey\s+|ok\s+)?edith[,\s]*|can\s+you\s+|please\s+)?"
        self.register(app_prefix + r"(?:open|launch|start)\s+(?:the\s+)?(?:google\s+)?(?:chrome|brave|edge|browser|web\s+browser)$", "open_app", "windows", {"app": "chrome"})
        self.register(app_prefix + r"(?:close|exit|quit|kill)\s+(?:the\s+)?(?:google\s+)?(?:chrome|brave|edge|browser|web\s+browser)$", "close_app", "windows", {"app": "chrome"})
        self.register(app_prefix + r"(?:open|launch|start)\s+(?:the\s+)?(?:terminal|powershell|cmd|command\s+prompt)$", "open_app", "windows", {"app": "wt"})
        self.register(app_prefix + r"(?:close|exit|quit)\s+(?:the\s+)?(?:terminal|powershell|cmd|command\s+prompt)$", "close_app", "windows", {"app": "wt"})
        self.register(app_prefix + r"(?:open|launch|start)\s+(?:the\s+)?(?:vs\s*code|code|visual\s+studio\s+code)$", "open_app", "windows", {"app": "code"})
        self.register(app_prefix + r"(?:open|launch|start)\s+(?:the\s+)?notepad$", "open_app", "windows", {"app": "notepad"})
        self.register(app_prefix + r"(?:close|exit|quit)\s+(?:the\s+)?notepad$", "close_app", "windows", {"app": "notepad"})
        self.register(app_prefix + r"(?:open|launch|start)\s+(?:the\s+)?(?:calc|calculator)$", "open_app", "windows", {"app": "calc"})
        self.register(app_prefix + r"(?:close|exit|quit|kill)\s+(?:the\s+)?(?:calc|calculator)$", "close_app", "windows", {"app": "calc"})
        self.register(app_prefix + r"(?:open|launch|start)\s+(?:the\s+)?(?:paint|mspaint)$", "open_app", "windows", {"app": "paint"})
        self.register(app_prefix + r"(?:close|exit|quit|kill)\s+(?:the\s+)?(?:paint|mspaint)$", "close_app", "windows", {"app": "paint"})
        self.register(app_prefix + r"(?:open|launch|start)\s+(?:the\s+)?(?:explorer|files|file\s+explorer)$", "open_app", "windows", {"app": "explorer"})
        self.register(app_prefix + r"(?:open|launch|start)\s+(?:the\s+)?(?:task\s*manager|taskmgr)$", "open_app", "windows", {"app": "taskmgr"})
        self.register(app_prefix + r"(?:close|exit|quit|kill)\s+(?:the\s+)?(?:task\s*manager|taskmgr)$", "close_app", "windows", {"app": "taskmgr"})

        # Shorthand direct app launches
        self.register(r"^(?:chrome|brave|edge|google\s+chrome)$", "open_app", "windows", {"app": "chrome"})
        self.register(r"^(?:notepad)$", "open_app", "windows", {"app": "notepad"})
        self.register(r"^(?:calc|calculator)$", "open_app", "windows", {"app": "calc"})
        self.register(r"^(?:paint|mspaint)$", "open_app", "windows", {"app": "paint"})
        self.register(r"^(?:code|vscode|vs\s*code)$", "open_app", "windows", {"app": "code"})
        self.register(r"^(?:terminal|powershell|cmd)$", "open_app", "windows", {"app": "wt"})
        self.register(r"^(?:task\s*manager|taskmgr)$", "open_app", "windows", {"app": "taskmgr"})

        # YouTube & Media Search Reflexes (<15ms)
        self.register(app_prefix + r"(?:open|launch|start|show)\s+(?:youtube|yt)$", "open_app", "windows", {"app": "youtube"})
        self.register(r"^(?:youtube|yt)$", "open_app", "windows", {"app": "youtube"})
        self.register(app_prefix + r"open\s+youtube\s+and\s+(?:play|search(?:\s+for)?)\s+(?P<query>.+)$", "search_youtube", "windows", {})
        self.register(app_prefix + r"(?:play|open|switch\s+to)\s+(?P<query>.+?)\s+in\s+(?:the\s+)?same\s+tab$", "search_youtube_same_tab", "windows", {})
        self.register(app_prefix + r"(?:play\s+another\s+video|open\s+another\s+video|play\s+another\s+song|open\s+another\s+song)(?:\s+(?P<query>.+))?$", "search_youtube_same_tab", "windows", {})
        self.register(app_prefix + r"(?:open|play)\s+(?:this|that)\s+video(?:\s+or\s+that)?\s+in\s+(?:the\s+)?same\s+tab$", "search_youtube_same_tab", "windows", {"query": "popular video"})
        self.register(app_prefix + r"(?:open|play)\s+(?P<query>.+?)\s+video\s+in\s+(?:the\s+)?same\s+tab$", "search_youtube_same_tab", "windows", {})
        self.register(app_prefix + r"play\s+(?P<query>.+?)(?:\s+(?:on|in)\s+(?:youtube|browser|the\s+browser|chrome|brave|edge))?$", "search_youtube", "windows", {})
        self.register(app_prefix + r"(?:open\s+(?:the\s+)?(?:browser|chrome|brave|edge)\s+and\s+)?play\s+(?P<query>.+)$", "search_youtube", "windows", {})
        self.register(app_prefix + r"search\s+youtube\s+(?:for\s+)?(?P<query>.+)$", "search_youtube", "windows", {})
        self.register(app_prefix + r"youtube\s+(?P<query>.+)$", "search_youtube", "windows", {})

        # Lifelong Learning and User Memory Reflexes (<15ms)
        self.register(app_prefix + r"remember(?:\s+that)?\s+(?P<fact>.+)$", "remember_fact", "memory", {})
        self.register(app_prefix + r"my\s+(?P<attr>name|favorite\s+\w+|job|hobby|browser|os)\s+is\s+(?P<val>.+)$", "remember_fact", "memory", {})
        self.register(app_prefix + r"i\s+prefer\s+(?P<pref>.+)$", "remember_fact", "memory", {})
        self.register(app_prefix + r"(?:what\s+do\s+you\s+remember|show(?:\s+my)?\s+memories|what\s+did\s+i\s+tell\s+you\s+to\s+remember|list\s+memories)$", "show_memories", "memory", {})
        self.register(app_prefix + r"forget(?:\s+memory)?\s+(?P<query>.+)$", "forget_memory", "memory", {})
        self.register(app_prefix + r"teach\s+command\s+(?P<trigger>.+?)\s+(?:as|to|=|is)\s+(?P<action>.+)$", "teach_command", "memory", {})
        self.register(app_prefix + r"when\s+i\s+say\s+(?P<trigger>.+?)[,\s]+(?:you\s+)?(?:do|execute|run|open)\s+(?P<action>.+)$", "teach_command", "memory", {})

        # PowerShell Execution & Autonomous Self-Learning (<15ms)
        self.register(app_prefix + r"(?:run\s+powershell|powershell\s+cmd|powershell\s+command|exec\s+ps)\s+(?P<command>.+)$", "run_powershell", "windows", {})
        self.register(app_prefix + r"(?:solve(?:\s+task)?|autonomously\s+do|figure\s+out\s+how\s+to)\s+(?P<goal>.+)$", "solve_task", "system", {})
        self.register(app_prefix + r"(?:show|list|what\s+are)\s+(?:learned\s+skills|my\s+skills|all\s+skills)$", "show_skills", "system", {})

        # Clap Welcome Detection (<15ms)
        self.register(app_prefix + r"(?:enable|start)\s+clap(?:\s+welcome|\s+detection|\s+listener)?$", "enable_clap", "voice", {})
        self.register(app_prefix + r"(?:disable|stop)\s+clap(?:\s+welcome|\s+detection|\s+listener)?$", "disable_clap", "voice", {})
        self.register(app_prefix + r"(?:welcome\s+me|welcome\s+home|trigger\s+welcome)$", "trigger_welcome", "voice", {})

        # Google & Web Search Reflexes (<15ms)
        self.register(app_prefix + r"(?:search\s+google\s+(?:for\s+)?|google\s+)(?P<query>.+)$", "search_google", "windows", {})
        self.register(app_prefix + r"(?:search\s+(?:the\s+)?(?:web|internet)\s+(?:for\s+)?|search\s+for\s+)(?P<query>.+)$", "search_google", "windows", {})

        # Typing & Keyboard Control Reflexes (<15ms)
        self.register(app_prefix + r"type\s+(?P<text>.+?)(?:\s+(?:in|into|on)\s+(?P<target_app>notepad|chrome|code|word|document|notes))?$", "type_text", "windows", {})
        self.register(app_prefix + r"write\s+(?P<text>.+?)\s+(?:in|into|on)\s+(?P<target_app>notepad|chrome|code|word|document|notes)$", "type_text", "windows", {})
        self.register(app_prefix + r"press\s+(?P<key_name>enter|return|tab|backspace|delete|del|escape|esc|space|up|down|left|right)$", "press_key", "windows", {})
        self.register(app_prefix + r"(?P<key_name>select\s+all|copy|paste|save|undo|new\s+tab|close\s+tab|switch\s+window|alt\s+tab)$", "press_key", "windows", {})

        # Window & Folder Controls (<15ms)
        self.register(app_prefix + r"(?P<action>show\s+desktop|minimize\s+all(?:\s+windows)?|restore\s+windows)$", "window_action", "windows", {})
        self.register(app_prefix + r"open\s+(?:the\s+)?(?P<folder_name>downloads|documents|desktop|pictures|music|videos|c\s+drive)(?:\s+folder)?$", "open_folder", "windows", {})

        # Universal open / launch app and website reflex (<15ms)
        self.register(
            app_prefix + r"(?:open|launch|start|run)\s+(?:the\s+)?(?P<app>[a-zA-Z0-9_\-\.\:\/]+(?:\s+[a-zA-Z0-9_\-\.\:\/]+)?)$",
            "open_app",
            "windows",
            {},
        )
        # Universal close / kill app reflex (<15ms)
        self.register(
            app_prefix + r"(?:close|exit|quit|kill|terminate)\s+(?:the\s+)?(?P<app>[a-zA-Z0-9_\-\.\:\/]+(?:\s+[a-zA-Z0-9_\-\.\:\/]+)?)$",
            "close_app",
            "windows",
            {},
        )

        # Audio & Media Controls
        self.register(r"^(?:hey\s+edith[,\s]*)?mute(?:\s+audio|\s+sound|\s+volume)?$", "mute", "windows", {"action": "mute"})
        self.register(r"^(?:hey\s+edith[,\s]*)?unmute(?:\s+audio|\s+sound|\s+volume)?$", "unmute", "windows", {"action": "unmute"})
        self.register(r"^(?:hey\s+edith[,\s]*)?volume\s+up$", "volume_up", "windows", {"delta": 5})
        self.register(r"^(?:hey\s+edith[,\s]*)?volume\s+down$", "volume_down", "windows", {"delta": -5})
        self.register(app_prefix + r"(?:set\s+)?volume\s+(?:to\s+)?(?P<volume>\d{1,3})(?:%|percent)?$", "set_master_volume", "windows", {})
        self.register(app_prefix + r"(?:pause|resume|play|stop)\s+(?:the\s+)?(?:music|song|track|playback|video)$", "media_action", "windows", {"kind": "play_pause"})
        self.register(app_prefix + r"(?:next|skip)\s+(?:the\s+)?(?:song|track|music)$", "media_action", "windows", {"kind": "next"})
        self.register(app_prefix + r"(?:previous|prev)\s+(?:the\s+)?(?:song|track|music)$", "media_action", "windows", {"kind": "prev"})

        # Biometric Face Sentinel Reflexes (<15ms)
        self.register(app_prefix + r"(?:start|enable|activate)\s+face(?:\s+sentinel|\s+presence|\s+lock)?$", "start_face_sentinel", "windows", {})
        self.register(app_prefix + r"(?:stop|disable|deactivate)\s+face(?:\s+sentinel|\s+presence|\s+lock)?$", "stop_face_sentinel", "windows", {})
        self.register(app_prefix + r"face(?:\s+sentinel)?\s+status$", "get_face_sentinel_status", "windows", {})

        # Clipboard & AirDrop Reflexes (<15ms)
        self.register(app_prefix + r"(?:get|read|show)\s+(?:the\s+)?clipboard$", "get_clipboard", "windows", {})
        self.register(app_prefix + r"(?:list|show)\s+(?:airdrop\s+|shared\s+)?files$", "list_airdrop_files", "files", {})

        # Voice Mute & JARVIS Speech Synthesis Toggle (<15ms)
        self.register(app_prefix + r"(?:mute|turn\s+off|disable|stop)\s+(?:jarvis\s+|edith\s+)?(?:voice|speech|speaker)$", "mute_voice", "voice", {})
        self.register(app_prefix + r"(?:unmute|turn\s+on|enable|start)\s+(?:jarvis\s+|edith\s+)?(?:voice|speech|speaker)$", "unmute_voice", "voice", {})

        # Voice Character & Personality Switching (<15ms)
        self.register(app_prefix + r"(?:switch|change|set)\s+(?:voice|character|personality)\s+(?:to\s+)?(?P<character>edith|jarvis|friday|karen|peter|spiderman|ultron)$", "switch_voice_character", "voice", {})
        self.register(app_prefix + r"(?:activate|switch\s+to|change\s+to)\s+(?P<character>edith|jarvis|friday|karen|peter|spiderman|ultron)\s+(?:voice|mode|personality)$", "switch_voice_character", "voice", {})
        self.register(app_prefix + r"(?:list|show|what\s+are)\s+(?:available\s+)?(?:voices|characters|personalities)$", "list_voice_characters", "voice", {})

        # Theme Switching (<15ms)
        self.register(app_prefix + r"(?:switch|change|set)\s+theme\s+(?:to\s+)?(?P<theme>default|cyan|jarvis|bnd|focus|tactical|spiderman)$", "switch_theme", "ui", {})

        # Bluetooth Microphone Selection (<15ms)
        self.register(app_prefix + r"(?:switch|change|set|use)\s+(?:mic|microphone)\s+(?:to\s+)?bluetooth$", "switch_mic_bluetooth", "voice", {})
        self.register(app_prefix + r"(?:switch|change|set|use)\s+bluetooth\s+(?:mic|microphone|headset|earphone)$", "switch_mic_bluetooth", "voice", {})

        # Optical & Screen Vision Perception (<15ms)
        self.register(app_prefix + r"(?:look\s+at\s+(?:my\s+)?screen|what\s+do\s+you\s+see|what\s+am\s+i\s+looking\s+at|see\s+(?:my\s+)?screen|analyze\s+(?:my\s+)?screen|read\s+(?:my\s+)?screen|describe\s+(?:my\s+)?screen)$", "analyze_screen", "windows", {})

        # High-Utility Offline System Tools (<15ms)
        self.register(app_prefix + r"(?:flush\s+dns|clear\s+dns)$", "flush_dns", "system", {})
        self.register(app_prefix + r"(?:empty\s+recycle\s+bin|clean\s+recycle\s+bin)$", "empty_recycle_bin", "system", {})
        self.register(app_prefix + r"(?:list\s+processes|running\s+processes|tasklist)$", "list_processes", "system", {})
        self.register(app_prefix + r"(?:network\s+status|ipconfig|check\s+ip)$", "network_status", "system", {})


        # Mouse & Pointer Controls
        self.register(app_prefix + r"(?:left\s+)?click$", "mouse_action", "windows", {"kind": "click"})
        self.register(app_prefix + r"double\s+click$", "mouse_action", "windows", {"kind": "double_click"})
        self.register(app_prefix + r"right\s+click$", "mouse_action", "windows", {"kind": "right_click"})
        self.register(app_prefix + r"scroll\s+down$", "mouse_action", "windows", {"kind": "scroll_down"})
        self.register(app_prefix + r"scroll\s+up$", "mouse_action", "windows", {"kind": "scroll_up"})

        # System & Battery
        self.register(r"^(?:hey\s+edith[,\s]*)?(?:take\s+a?\s*screenshot|capture\s+screen)$", "screenshot", "windows", {})
        self.register(r"^(?:(?:hey\s+|ok\s+)?edith[,\s]*)?(?:show\s+|check\s+|what\s+is\s+the\s+)?battery(?:\s+status|\s+level|\s+percentage|\s+percent|\s+info)?$", "battery_status", "windows", {})
        self.register(r"^(?:hey\s+edith[,\s]*)?(?:lock|lock\s+my|lock\s+the)\s+(?:pc|computer|screen|workstation)$", "lock_workstation", "windows", {})
        self.register(r"^(?:hey\s+edith[,\s]*)?(?:unlock|unlock\s+my|unlock\s+the)\s+(?:pc|computer|screen|laptop|workstation)$", "unlock_workstation", "windows", {})
        self.register(r"^(?:unlock\s+screen|unlock\s+pc|unlock\s+laptop)$", "unlock_workstation", "windows", {})
        self.register(app_prefix + r"(?:switch\s+to|change\s+to|enter|open|launch)\s+(?:the\s+)?camera(?:\s+mode)?$", "switch_to_camera_mode", "windows", {})
        self.register(r"^(?:camera\s+mode|switch\s+to\s+camera|open\s+camera)$", "switch_to_camera_mode", "windows", {})
        self.register(r"^(?:hey\s+edith[,\s]*)?(?:take\s+(?:a\s+)?(?:picture|photo)|snap\s+(?:a\s+)?photo|capture\s+(?:a\s+)?photo|click\s+(?:a\s+)?(?:picture|photo))$", "take_picture", "windows", {})
        self.register(r"^(?:hey\s+edith[,\s]*)?(?:open|show|display|view)\s+(?:the\s+)?(?:picture|photo|pic)(?:s)?(?:\s+(?:which|that)?\s*(?:u|you)?\s*(?:have\s*)?(?:clicked|taken|captured|snapped))?$", "open_latest_picture", "windows", {})
        self.register(r"^(?:hey\s+edith[,\s]*)?(?:open|show)\s+(?:the\s+|my\s+)?latest\s+(?:picture|photo|pic)$", "open_latest_picture", "windows", {})
        self.register(app_prefix + r"(?:sleep|suspend)\s+(?:the\s+)?(?:pc|computer|system)$", "power_action", "windows", {"kind": "sleep"})
        self.register(app_prefix + r"cancel\s+(?:the\s+)?(?:shutdown|restart)$", "power_action", "windows", {"kind": "cancel_shutdown"})

        # System Control / Emergency Stop
        self.register(r"^(?:hey\s+edith[,\s]*)?(?:stop|emergency\s+stop|halt|freeze)(?:\s+edith)?$", "emergency_stop", "system", {})
        self.register(r"^(?:hey\s+edith[,\s]*)?(?:pause|hold\s+on)(?:\s+edith)?$", "pause_edith", "system", {})
        self.register(r"^(?:(?:hey\s+|ok\s+)?edith[,\s]*)?(?:resume|continue|unpause|unfreeze|unstop|start|go)(?:\s+edith)?$", "resume_edith", "system", {})
        self.register(r"^(?:hey\s+edith[,\s]*)?(?:show|what\s+is\s+your)\s+status$", "show_status", "system", {})
        self.register(r"^(?:hey\s+edith[,\s]*)?enable\s+privacy\s+mode$", "enable_privacy", "system", {"enabled": True})
        self.register(r"^(?:hey\s+edith[,\s]*)?disable\s+privacy\s+mode$", "disable_privacy", "system", {"enabled": False})

        # Conversational & System Queries (<1ms reflex)
        self.register(r"^(?:hey\s+edith[,\s]*)?(?:who\s+are\s+you|what\s+are\s+you|introduce\s+yourself|who\s+r\s+u)$", "who_are_you", "system", {})
        self.register(r"^(?:hey\s+edith[,\s]*)?(?:who\s+(?:is\s+your\s+creator|created\s+you|made\s+you|built\s+you))$", "creator_info", "system", {})
        self.register(r"^(?:hey+\s+edith[,\s]*)?(?:hello+|hi+|hey+|good\s+(?:morning|afternoon|evening))(?:\s+edith)?$", "greeting", "system", {})
        self.register(r"^(?:hey\s+edith[,\s]*)?(?:what\s+can\s+you\s+do|help|commands|show\s+commands)$", "capabilities", "system", {})
        self.register(r"^(?:hey\s+edith[,\s]*)?(?:what\s+time\s+is\s+it|current\s+time|time)$", "get_time", "system", {})
        self.register(r"^(?:hey\s+edith[,\s]*)?(?:what\s+is\s+(?:today'?s\s+)?date|current\s+date|date|today'?s\s+date)$", "get_date", "system", {})
        self.register(r"^(?:hey+\s+edith[,\s]*)?(?:switch|change|use)\s+(?:model\s+to\s+|to\s+model\s+|model\s+)?(?P<model>[a-zA-Z0-9_\.\-:\/]+)$", "switch_model", "system", {})

        # Mark-LV Reversible Undo & Safety Confirmation Reflexes (<15ms)
        self.register(app_prefix + r"(?:undo|revert|undo\s+that|undo\s+last\s+action|cancel\s+last\s+action)$", "undo_action", "system", {})
        self.register(app_prefix + r"(?:confirm|approve|confirm\s+action|yes\s+confirm|proceed)$", "confirm_action", "system", {"approved": True})
        self.register(app_prefix + r"(?:abort|cancel\s+action|reject\s+action|no\s+cancel|deny)$", "confirm_action", "system", {"approved": False})
        self.register(app_prefix + r"(?:system\s+metrics|system\s+stats|hardware\s+stats|performance\s+stats)$", "system_metrics", "system", {})


    def register(self, regex_pattern: str, command_name: str, action_type: str, params: Dict[str, Any]) -> None:
        """Register a new deterministic pattern."""
        self._patterns.append((
            re.compile(regex_pattern, re.IGNORECASE),
            command_name,
            action_type,
            params,
        ))

    def evaluate(self, user_utterance: str) -> Optional[ReflexMatch]:
        """Check if utterance matches any Level 0 reflex pattern (<15ms)."""
        t0 = time.perf_counter()
        cleaned = user_utterance.strip().lower()

        # Check custom learned commands from memory first
        try:
            from edith.memory.local_store import MEMORY
            custom_action = MEMORY.get_custom_command(cleaned)
            if custom_action:
                inner_match = self.evaluate(custom_action)
                if inner_match:
                    return inner_match
                dt_ms = (time.perf_counter() - t0) * 1000.0
                return ReflexMatch(
                    matched=True,
                    command_name="custom_command",
                    action_type="custom",
                    params={"action": custom_action},
                    duration_ms=round(dt_ms, 3),
                )
        except Exception:
            pass

        for pattern, cmd_name, action_type, default_params in self._patterns:
            match = pattern.match(cleaned)
            if match:
                dt_ms = (time.perf_counter() - t0) * 1000.0
                params = dict(default_params)
                params.update(match.groupdict())
                return ReflexMatch(
                    matched=True,
                    command_name=cmd_name,
                    action_type=action_type,
                    params=params,
                    duration_ms=round(dt_ms, 3),
                )

        return None

    def execute_match(self, match: ReflexMatch, executor: Optional[Callable[[str, Dict[str, Any]], Any]] = None) -> Any:
        """Execute the matched deterministic command immediately."""
        if match.command_name == "emergency_stop":
            SECURITY.trigger_emergency_stop("Voice/text emergency stop triggered")
            return "Emergency stop engaged."
        elif match.command_name == "pause_edith":
            CONFIG.emergency_stopped = False
            return "EDITH paused."
        elif match.command_name == "resume_edith":
            SECURITY.reset_emergency_stop()
            CONFIG.emergency_stopped = False
            return "Emergency stop cleared. EDITH is back online and ready for orders."
        elif match.command_name == "enable_privacy":
            SECURITY.set_privacy_mode(True)
            return "Privacy mode active. Camera and telemetry muted."
        elif match.command_name == "disable_privacy":
            SECURITY.set_privacy_mode(False)
            return "Privacy mode disabled."
        elif match.command_name == "show_status":
            return f"EDITH Online. Mode: {'Privacy' if SECURITY.is_privacy_mode else 'Standard'}."
        elif match.command_name == "who_are_you":
            return f"I am {CONFIG.system_name} (Even Dead, I'm The Hero), an autonomous local-first AI operating system created by {CONFIG.creator}."
        elif match.command_name == "creator_info":
            return f"I was created and engineered by {CONFIG.creator}."
        elif match.command_name == "greeting":
            return "Online and ready, sir. What are your orders?"
        elif match.command_name == "capabilities":
            return (
                "EDITH Full OS Automation Capabilities:\n"
                "• Apps: 'open chrome', 'close chrome', 'open notepad', 'open vs code', 'open calc', 'open terminal'\n"
                "• Media & Search: 'open youtube and play <topic>', 'search google for <query>', 'open <url>'\n"
                "• Typing & Keys: 'type <text>', 'press enter', 'select all', 'copy', 'paste', 'save', 'undo'\n"
                "• Windows & Folders: 'show desktop', 'minimize all', 'open downloads', 'open documents', 'open c drive'\n"
                "• Audio & Power: 'mute', 'unmute', 'volume up', 'volume down', 'battery status', 'take screenshot'\n"
                "• System & AI: 'lock pc', 'switch model to <name>', 'time', 'date', 'emergency stop'"
            )
        elif match.command_name == "remember_fact":
            from edith.memory.local_store import MEMORY
            fact = match.params.get("fact")
            if not fact and "attr" in match.params and "val" in match.params:
                fact = f"My {match.params['attr']} is {match.params['val']}"
            elif not fact and "pref" in match.params:
                fact = f"I prefer {match.params['pref']}"
            saved = MEMORY.remember_fact(fact or "")
            return f"Understood, sir. I have committed to memory: '{saved}'."
        elif match.command_name == "show_memories":
            from edith.memory.local_store import MEMORY
            mems = MEMORY.get_memories()
            if not mems:
                return "My memory is currently clear. No personal facts or preferences stored."
            bullet_list = "\n".join(f"• {m}" for m in mems)
            return f"Here is what I have remembered about you, sir:\n{bullet_list}"
        elif match.command_name == "forget_memory":
            from edith.memory.local_store import MEMORY
            q = match.params.get("query", "").strip()
            success = MEMORY.forget_memory(q)
            if success:
                return f"Memory cleared for '{q}', sir."
            return f"Could not find any stored memory matching '{q}'."
        elif match.command_name == "teach_command":
            from edith.memory.local_store import MEMORY
            trig = match.params.get("trigger", "").strip()
            act = match.params.get("action", "").strip()
            res = MEMORY.teach_command(trig, act)
            return res
        elif match.command_name == "custom_command":
            act = match.params.get("action", "").strip()
            from edith.tools.windows import WIN_TOOLS
            return WIN_TOOLS.launch_app(act)
        elif match.command_name == "run_powershell":
            from edith.tools.windows import WIN_TOOLS
            cmd = match.params.get("command", "").strip()
            return WIN_TOOLS.run_powershell(cmd)
        elif match.command_name == "solve_task":
            from edith.tasks.self_learner import SELF_LEARNER
            goal = match.params.get("goal", "").strip()
            return SELF_LEARNER.solve_task_sync(goal)
        elif match.command_name == "show_skills":
            from edith.tasks.self_learner import SELF_LEARNER
            skills = SELF_LEARNER.get_learned_skills()
            if not skills:
                return "No autonomous skills learned yet, sir. Give me any task to solve and learn!"
            items = [f"• {s['goal']} -> {s['command']} (success count: {s.get('success_count', 1)})" for s in skills]
            return "Here are the autonomous skills I have learned:\n" + "\n".join(items)
        elif match.command_name == "enable_clap":
            from edith.voice.clap_detector import CLAP_DETECTOR
            CLAP_DETECTOR.start()
            return "Clap welcome detection activated, sir. Two claps will trigger the welcome protocol."
        elif match.command_name == "disable_clap":
            from edith.voice.clap_detector import CLAP_DETECTOR
            CLAP_DETECTOR.stop()
            return "Clap welcome detection deactivated."
        elif match.command_name == "trigger_welcome":
            from edith.voice.clap_detector import CLAP_DETECTOR
            return CLAP_DETECTOR.trigger_welcome()
        elif match.command_name == "mute_voice":
            from edith.voice.speaker import SPEAKER
            SPEAKER.set_muted(True)
            return "Jarvis voice output is now muted. Visual HUD responses remain active."
        elif match.command_name == "unmute_voice":
            from edith.voice.speaker import SPEAKER
            SPEAKER.set_muted(False)
            return "Jarvis voice output has been unmuted."
        elif match.command_name == "switch_voice_character":
            from edith.voice.speaker import SPEAKER
            raw_target = match.params.get("character", "edith")
            char_info = SPEAKER.set_character(raw_target)
            msg = f"Voice protocol switched to {char_info['name']}. {char_info['welcome']}"
            SPEAKER.speak(msg, async_mode=True)
            return {
                "message": msg,
                "character": char_info,
                "action": "switch_voice_character",
            }
        elif match.command_name == "list_voice_characters":
            from edith.voice.speaker import SPEAKER
            chars = SPEAKER.list_characters()
            lines = [f"• {c['name']} ({c['role']}) - {c['description']}" for c in chars]
            return "Available voice characters:\n" + "\n".join(lines)
        elif match.command_name == "switch_theme":
            raw_mode = match.params.get("theme", "spiderman")
            mode = "spiderman" if "spider" in raw_mode.lower() else ("bnd" if "bnd" in raw_mode.lower() else ("focus" if "tactical" in raw_mode.lower() or "focus" in raw_mode.lower() else "default"))
            return {
                "message": f"HUD theme switched to {mode.upper()}.",
                "theme": mode,
                "action": "switch_theme",
            }
        elif match.command_name == "switch_mic_bluetooth":
            from edith.voice.clap_detector import CLAP_DETECTOR
            import sounddevice as sd
            dev = CLAP_DETECTOR.get_preferred_input_device()
            if dev is not None:
                CLAP_DETECTOR.set_input_device(dev)
                try:
                    dname = sd.query_devices(dev).get("name", "Bluetooth Audio")
                except Exception:
                    dname = "Bluetooth Headset"
                return f"Audio input switched to Bluetooth microphone: {dname}."
            return "No Bluetooth audio input device detected. Please ensure your headset is connected in Windows Bluetooth settings."
        elif match.command_name == "analyze_screen":
            from edith.tools.vision import VISION
            res = VISION.analyze_screen()
            return res.get("message") or res.get("perception") or "Screen analyzed."
        elif match.command_name == "flush_dns":
            from edith.tools.windows import WIN_TOOLS
            res = WIN_TOOLS.run_powershell("Clear-DnsClientCache; 'DNS resolver cache cleared successfully.'")
            return res.get("output", "DNS cache flushed.")
        elif match.command_name == "empty_recycle_bin":
            from edith.tools.windows import WIN_TOOLS
            res = WIN_TOOLS.run_powershell("Clear-RecycleBin -Force -ErrorAction SilentlyContinue; 'Windows Recycle Bin emptied.'")
            return res.get("output", "Recycle Bin emptied.")
        elif match.command_name == "list_processes":
            from edith.tools.windows import WIN_TOOLS
            res = WIN_TOOLS.run_powershell("Get-Process | Sort-Object CPU -Descending | Select-Object -First 8 ProcessName, CPU, WorkingSet64 | Format-Table -AutoSize | Out-String")
            return res.get("output", "Active processes listed.")
        elif match.command_name == "network_status":
            from edith.tools.windows import WIN_TOOLS
            res = WIN_TOOLS.run_powershell("Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.*' } | Select-Object InterfaceAlias, IPAddress | Format-Table -AutoSize | Out-String")
            return res.get("output", "Active network adapters verified.")
        elif match.command_name == "search_youtube":
            from edith.tools.windows import WIN_TOOLS
            q = match.params.get("query", "").strip()
            return WIN_TOOLS.search_youtube(q, open_browser=True)
        elif match.command_name == "search_youtube_same_tab":
            from edith.tools.windows import WIN_TOOLS
            q = match.params.get("query", "").strip()
            return WIN_TOOLS.search_youtube(q, open_browser=True, same_tab=True)
        elif match.command_name == "search_google":
            from edith.tools.windows import WIN_TOOLS
            q = match.params.get("query", "").strip()
            return WIN_TOOLS.search_google(q)
        elif match.command_name == "type_text":
            from edith.tools.windows import WIN_TOOLS
            txt = match.params.get("text", "").strip()
            target_app = match.params.get("target_app")
            res = WIN_TOOLS.type_text(txt, target_app=target_app)
            return res.get("message") or f"Typed '{txt}'."
        elif match.command_name == "press_key":
            from edith.tools.windows import WIN_TOOLS
            k = match.params.get("key_name", "").strip()
            res = WIN_TOOLS.press_key(k)
            return res.get("message") or f"Pressed {k}."
        elif match.command_name == "window_action":
            from edith.tools.windows import WIN_TOOLS
            act = match.params.get("action", "").strip()
            res = WIN_TOOLS.window_action(act)
            return res.get("message") or f"Window action '{act}' executed."
        elif match.command_name == "open_folder":
            from edith.tools.windows import WIN_TOOLS
            fld = match.params.get("folder_name", "").strip()
            res = WIN_TOOLS.open_folder(fld)
            return res.get("message") or f"Opened {fld} folder."
        elif match.command_name == "open_app":
            from edith.tools.windows import WIN_TOOLS
            app = match.params.get("app", "").strip()
            return WIN_TOOLS.launch_app(app)
        elif match.command_name == "close_app":
            from edith.tools.windows import WIN_TOOLS
            app = match.params.get("app", "").strip()
            return WIN_TOOLS.kill_process(app)
        elif match.command_name == "get_time":
            from datetime import datetime
            return f"The current time is {datetime.now().strftime('%I:%M %p')}."
        elif match.command_name == "get_date":
            from datetime import datetime
            return f"Today is {datetime.now().strftime('%A, %B %d, %Y')}."
        elif match.command_name == "switch_model":
            target_model = match.params.get("model", "").strip()
            if target_model:
                CONFIG.primary_local_model = target_model
                from edith.providers.ollama_provider import OLLAMA
                OLLAMA.set_model(target_model)
                return f"Switched primary AI model to {target_model}."
            return "Please specify a target model name."
        elif match.command_name == "battery_status":
            stats = CONFIG.refresh_dynamic_stats()
            bat = stats.get("battery_percent")
            ac = stats.get("power_plugged")
            if bat is not None:
                ac_str = "plugged in and charging" if ac else "running on battery"
                return f"Battery is at {bat}%, {ac_str}."
            return "Battery power status is normal."
        elif match.command_name == "media_action":
            from edith.tools.windows import WIN_TOOLS
            kind = match.params.get("kind", "play_pause")
            res = WIN_TOOLS.media_action(kind)
            return res.get("message") or f"Executed media action: {kind}."
        elif match.command_name == "mouse_action":
            from edith.tools.windows import WIN_TOOLS
            kind = match.params.get("kind", "click")
            amount = match.params.get("amount", 3)
            res = WIN_TOOLS.mouse_action(kind, amount=amount)
            return res.get("message") or f"Executed mouse action: {kind}."
        elif match.command_name == "power_action":
            from edith.tools.windows import WIN_TOOLS
            kind = match.params.get("kind", "lock")
            res = WIN_TOOLS.power_action(kind)
            return res.get("message") or f"Executed power action: {kind}."
        elif match.command_name == "lock_workstation":
            from edith.tools.windows import WIN_TOOLS
            res = WIN_TOOLS.lock_workstation()
            return res.get("message") or "Workstation locked."
        elif match.command_name == "unlock_workstation":
            from edith.tools.windows import WIN_TOOLS
            pin = match.params.get("pin")
            res = WIN_TOOLS.unlock_workstation(pin=pin)
            return res.get("message") or "Workstation unlocked."
        elif match.command_name == "switch_to_camera_mode":
            from edith.tools.windows import WIN_TOOLS
            res = WIN_TOOLS.switch_to_camera_mode()
            return res.get("message") or "Switched to camera mode."
        elif match.command_name == "take_picture":
            from edith.tools.windows import WIN_TOOLS
            res = WIN_TOOLS.take_picture()
            return res.get("message") or "Photo captured."
        elif match.command_name == "open_latest_picture":
            from edith.tools.windows import WIN_TOOLS
            res = WIN_TOOLS.open_latest_picture()
            return res.get("message") or "Opened latest picture."
        elif match.command_name == "undo_action":
            from edith.core.undo import UNDO_MANAGER
            return UNDO_MANAGER.undo_last()
        elif match.command_name == "confirm_action":
            from edith.core.confirm import CONFIRMATION_GATE
            pending = CONFIRMATION_GATE.get_pending()
            if not pending:
                return "No pending actions awaiting confirmation."
            approved = match.params.get("approved", True)
            res = CONFIRMATION_GATE.resolve(pending["id"], approved=approved)
            return res.get("message", "Confirmation processed.")
        elif match.command_name == "system_metrics":
            import psutil
            import platform
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()
            disk_path = "C:\\" if platform.system() == "Windows" else "/"
            disk = psutil.disk_usage(disk_path)
            return f"System telemetry nominal. CPU: {cpu}%, RAM: {mem.percent}% ({mem.used // (1024*1024)}MB / {mem.total // (1024*1024)}MB), Disk: {disk.percent}% used."


        if executor:
            raw_out = executor(match.command_name, match.params)
            if isinstance(raw_out, dict):
                return raw_out.get("message") or raw_out.get("result") or f"Executed {match.command_name} successfully."
            return str(raw_out)

        return f"Reflex '{match.command_name}' processed in {match.duration_ms}ms"


# Global reflex engine singleton
REFLEX = ReflexEngine()
REFLEX_ENGINE = REFLEX
