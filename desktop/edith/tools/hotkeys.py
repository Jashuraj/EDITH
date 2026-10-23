"""Windows Native Global Hotkey and Desktop Daemon for EDITH.

Implements Sections 22 and 67 of the Engineering Constitution.
Registers native OS-level global hotkeys via Win32 user32.dll:
- Ctrl + Alt + Space: Toggle / Summon Holographic HUD
- Ctrl + Alt + V: Trigger Voice Command / Push-To-Talk
- Ctrl + Alt + S: Announce System Status
"""

from __future__ import annotations

import ctypes
import logging
import os
import sys
import threading
import time
import webbrowser
from typing import Callable, Dict, Optional

from edith.core.event_bus import BUS

logger = logging.getLogger("edith.tools.hotkeys")

# Win32 Constants
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

WM_HOTKEY = 0x0312
VK_SPACE = 0x20
VK_V = 0x56
VK_S = 0x53


class GlobalHotkeyDaemon:
    """Manages system-wide Windows hotkeys without third-party dependencies."""

    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callbacks: Dict[int, Callable[[], None]] = {}
        self._user32 = None

        if sys.platform == "win32":
            try:
                self._user32 = ctypes.windll.user32
            except Exception as ex:
                logger.warning("Win32 ctypes user32 unavailable: %s", ex)

        # Default action bindings
        self.bind_hotkey(1, MOD_CONTROL | MOD_ALT, VK_SPACE, self._on_toggle_hud)
        self.bind_hotkey(2, MOD_CONTROL | MOD_ALT, VK_V, self._on_push_to_talk)
        self.bind_hotkey(3, MOD_CONTROL | MOD_ALT, VK_S, self._on_system_status)

    def bind_hotkey(self, hotkey_id: int, modifiers: int, vk_code: int, callback: Callable[[], None]) -> None:
        """Register a hotkey binding."""
        self._callbacks[hotkey_id] = callback

    def start(self) -> bool:
        """Start global hotkey listener in background daemon thread."""
        if self._running or not self._user32:
            return False

        self._running = True
        self._thread = threading.Thread(target=self._hotkey_loop, name="EdithHotkeyDaemon", daemon=True)
        self._thread.start()
        logger.info("Global hotkey daemon started.")
        return True

    def stop(self) -> None:
        """Stop listening to global hotkeys."""
        self._running = False
        if self._user32:
            try:
                self._user32.PostQuitMessage(0)
            except Exception:
                pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        logger.info("Global hotkey daemon stopped.")

    def _hotkey_loop(self) -> None:
        """Win32 message pump for WM_HOTKEY events."""
        if not self._user32:
            return

        # Register hotkeys for this thread
        self._user32.RegisterHotKey(None, 1, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, VK_SPACE)
        self._user32.RegisterHotKey(None, 2, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, VK_V)
        self._user32.RegisterHotKey(None, 3, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, VK_S)

        class MSG(ctypes.Structure):
            _fields_ = [
                ("hwnd", ctypes.c_void_p),
                ("message", ctypes.c_uint),
                ("wParam", ctypes.c_void_p),
                ("lParam", ctypes.c_void_p),
                ("time", ctypes.c_ulong),
                ("pt", ctypes.c_ulong * 2),
            ]

        msg = MSG()
        while self._running:
            # PeekMessage to allow non-blocking exit
            if self._user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
                if msg.message == WM_HOTKEY:
                    hid = int(msg.wParam)
                    cb = self._callbacks.get(hid)
                    if cb:
                        try:
                            cb()
                        except Exception as ex:
                            logger.error("Hotkey %d error: %s", hid, ex)
            time.sleep(0.05)

        # Unregister hotkeys upon shutdown
        for hid in (1, 2, 3):
            try:
                self._user32.UnregisterHotKey(None, hid)
            except Exception:
                pass

    def _on_toggle_hud(self) -> None:
        """Summon or focus Holographic HUD in browser."""
        logger.info("Hotkey Triggered: Toggle HUD (Ctrl+Alt+Space)")
        webbrowser.open("http://127.0.0.1:8794")
        BUS.publish_sync("hotkey:triggered", {"action": "toggle_hud"})

    def _on_push_to_talk(self) -> None:
        """Trigger instant voice input push-to-talk."""
        logger.info("Hotkey Triggered: Voice Push-To-Talk (Ctrl+Alt+V)")
        BUS.publish_sync("hotkey:triggered", {"action": "push_to_talk"})

    def _on_system_status(self) -> None:
        """Trigger telemetry vocalization."""
        logger.info("Hotkey Triggered: System Status (Ctrl+Alt+S)")
        BUS.publish_sync("hotkey:triggered", {"action": "system_status"})

    def get_status(self) -> Dict[str, Any]:
        """Return daemon running state and registered bindings."""
        return {
            "running": self._running,
            "supported": self._user32 is not None,
            "hotkeys": [
                {"id": 1, "keys": "Ctrl+Alt+Space", "action": "Toggle HUD"},
                {"id": 2, "keys": "Ctrl+Alt+V", "action": "Voice Push-To-Talk"},
                {"id": 3, "keys": "Ctrl+Alt+S", "action": "System Status"},
            ],
        }


# Global Singleton Instance
HOTKEY_DAEMON = GlobalHotkeyDaemon()
