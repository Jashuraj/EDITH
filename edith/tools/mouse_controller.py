"""High-Performance Native Windows Mouse & Gesture Screen Controller.

Uses direct Win32 User32 C API for sub-millisecond cursor positioning,
gestural clicks, drag-and-drop, mouse wheel scrolling, and window controls
without third-party lag.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import logging
import platform
import time
from typing import Any, Dict, Optional

logger = logging.getLogger("edith.tools.mouse")

# Win32 Mouse Event Flags
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_ABSOLUTE = 0x8000

# Virtual Key Codes
VK_MENU = 0x12       # Alt
VK_TAB = 0x09        # Tab
VK_CONTROL = 0x11    # Ctrl
VK_MEDIA_PLAY_PAUSE = 0xB3
KEYEVENTF_KEYUP = 0x0002

SM_CXSCREEN = 0
SM_CYSCREEN = 1


class MouseController:
    """Zero-latency OS mouse automation controller."""

    def __init__(self):
        self._is_windows = platform.system() == "Windows"
        self._u32 = ctypes.windll.user32 if self._is_windows else None
        self._is_dragging = False
        self._last_move_time = 0.0

        if self._u32:
            try:
                # Per-Monitor V2 DPI awareness for pixel-perfect 1:1 display mapping
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                try:
                    self._u32.SetProcessDPIAware()
                except Exception:
                    pass

        self.update_screen_metrics()

    def update_screen_metrics(self) -> None:
        """Cache current primary monitor dimensions."""
        if self._u32:
            self.screen_width = max(800, self._u32.GetSystemMetrics(SM_CXSCREEN))
            self.screen_height = max(600, self._u32.GetSystemMetrics(SM_CYSCREEN))
        else:
            self.screen_width = 1920
            self.screen_height = 1080

    def move(self, norm_x: float, norm_y: float) -> bool:
        """Move cursor to normalized coordinates (0.0 to 1.0)."""
        if not self._u32:
            return False

        self.update_screen_metrics()
        clamped_x = max(0.0, min(1.0, float(norm_x)))
        clamped_y = max(0.0, min(1.0, float(norm_y)))

        target_x = int(clamped_x * self.screen_width)
        target_y = int(clamped_y * self.screen_height)

        self._u32.SetCursorPos(target_x, target_y)
        # Also dispatch standard Win32 absolute mouse move event for applications and games
        abs_x = int(clamped_x * 65535)
        abs_y = int(clamped_y * 65535)
        self._u32.mouse_event(MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_MOVE, abs_x, abs_y, 0, 0)
        self._last_move_time = time.perf_counter()
        return True

    def move_relative(self, dx: int, dy: int) -> bool:
        """Move cursor by relative pixel offsets dx and dy for 3D/FPS game look."""
        if not self._u32:
            return False
        self._u32.mouse_event(MOUSEEVENTF_MOVE, int(dx), int(dy), 0, 0)
        self._last_move_time = time.perf_counter()
        return True

    def _get_abs_coords(self) -> tuple[int, int]:
        """Return current cursor position in normalized Win32 0..65535 space."""
        if not self._u32:
            return 0, 0
        self.update_screen_metrics()
        pt = wintypes.POINT()
        if self._u32.GetCursorPos(ctypes.byref(pt)):
            abs_x = int((pt.x / max(1, self.screen_width)) * 65535.0)
            abs_y = int((pt.y / max(1, self.screen_height)) * 65535.0)
            return abs_x, abs_y
        return 0, 0

    def left_click(self) -> bool:
        """Simulate primary left mouse button click reliably."""
        if not self._u32:
            return False
        abs_x, abs_y = self._get_abs_coords()
        flags = MOUSEEVENTF_ABSOLUTE if (abs_x or abs_y) else 0
        self._u32.mouse_event(flags | MOUSEEVENTF_LEFTDOWN, abs_x, abs_y, 0, 0)
        time.sleep(0.025)
        self._u32.mouse_event(flags | MOUSEEVENTF_LEFTUP, abs_x, abs_y, 0, 0)
        return True

    def right_click(self) -> bool:
        """Simulate secondary right mouse button click reliably."""
        if not self._u32:
            return False
        abs_x, abs_y = self._get_abs_coords()
        flags = MOUSEEVENTF_ABSOLUTE if (abs_x or abs_y) else 0
        self._u32.mouse_event(flags | MOUSEEVENTF_RIGHTDOWN, abs_x, abs_y, 0, 0)
        time.sleep(0.025)
        self._u32.mouse_event(flags | MOUSEEVENTF_RIGHTUP, abs_x, abs_y, 0, 0)
        return True

    def double_click(self) -> bool:
        """Simulate rapid double left click."""
        if not self._u32:
            return False
        abs_x, abs_y = self._get_abs_coords()
        flags = MOUSEEVENTF_ABSOLUTE if (abs_x or abs_y) else 0
        self._u32.mouse_event(flags | MOUSEEVENTF_LEFTDOWN, abs_x, abs_y, 0, 0)
        time.sleep(0.02)
        self._u32.mouse_event(flags | MOUSEEVENTF_LEFTUP, abs_x, abs_y, 0, 0)
        time.sleep(0.05)
        self._u32.mouse_event(flags | MOUSEEVENTF_LEFTDOWN, abs_x, abs_y, 0, 0)
        time.sleep(0.02)
        self._u32.mouse_event(flags | MOUSEEVENTF_LEFTUP, abs_x, abs_y, 0, 0)
        return True

    def drag_start(self) -> bool:
        """Engage left mouse button hold for drag and drop."""
        if not self._u32:
            return False
        if not self._is_dragging:
            self._u32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            self._is_dragging = True
        return True

    def drag_end(self) -> bool:
        """Release left mouse button hold."""
        if not self._u32:
            return False
        if self._is_dragging:
            self._u32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            self._is_dragging = False
        return True

    def scroll(self, delta: int) -> bool:
        """Scroll vertical mouse wheel. Positive = Up, Negative = Down."""
        if not self._u32:
            return False
        wheel_amount = int(delta * 120)
        self._u32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, wheel_amount, 0)
        return True

    def switch_window(self) -> bool:
        """Simulate Alt+Tab to cycle active applications."""
        if not self._u32:
            return False
        self._u32.keybd_event(VK_MENU, 0, 0, 0)
        self._u32.keybd_event(VK_TAB, 0, 0, 0)
        self._u32.keybd_event(VK_TAB, 0, KEYEVENTF_KEYUP, 0)
        self._u32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
        return True

    def tab_switch(self) -> bool:
        """Simulate Ctrl+Tab to cycle browser/editor tabs."""
        if not self._u32:
            return False
        self._u32.keybd_event(VK_CONTROL, 0, 0, 0)
        self._u32.keybd_event(VK_TAB, 0, 0, 0)
        self._u32.keybd_event(VK_TAB, 0, KEYEVENTF_KEYUP, 0)
        self._u32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
        return True

    def media_play_pause(self) -> bool:
        """Toggle system media playback."""
        if not self._u32:
            return False
        self._u32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, 0, 0)
        self._u32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, KEYEVENTF_KEYUP, 0)
        return True

    def handle_gesture_action(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch high-level gestural command."""
        action = (action or "").strip().lower()

        if action == "move":
            x = params.get("x", 0.5)
            y = params.get("y", 0.5)
            success = self.move(x, y)
            return {"success": success, "action": "move"}

        elif action in ("click", "left_click"):
            if "x" in params and "y" in params:
                self.move(float(params["x"]), float(params["y"]))
            return {"success": self.left_click(), "action": "left_click"}

        elif action == "right_click":
            if "x" in params and "y" in params:
                self.move(float(params["x"]), float(params["y"]))
            return {"success": self.right_click(), "action": "right_click"}

        elif action == "double_click":
            if "x" in params and "y" in params:
                self.move(float(params["x"]), float(params["y"]))
            return {"success": self.double_click(), "action": "double_click"}

        elif action in ("drag_start", "grab"):
            if "x" in params and "y" in params:
                self.move(float(params["x"]), float(params["y"]))
            return {"success": self.drag_start(), "action": "drag_start"}

        elif action in ("drag_end", "release"):
            return {"success": self.drag_end(), "action": "drag_end"}

        elif action == "scroll":
            delta = int(params.get("delta", 1))
            return {"success": self.scroll(delta), "action": "scroll"}

        elif action == "volume":
            delta = int(params.get("delta", 5))
            from edith.tools.windows import WIN_TOOLS
            res = WIN_TOOLS.set_volume(delta)
            return {"success": True, "action": "volume", "result": res}

        elif action == "desktop":
            from edith.tools.windows import WIN_TOOLS
            res = WIN_TOOLS.perform_window_action("show desktop")
            return {"success": True, "action": "desktop", "result": res}

        elif action in ("switch_window", "alt_tab"):
            return {"success": self.switch_window(), "action": "switch_window"}

        elif action in ("tab_switch", "next_tab"):
            return {"success": self.tab_switch(), "action": "tab_switch"}

        elif action in ("media_toggle", "play_pause"):
            return {"success": self.media_play_pause(), "action": "media_play_pause"}

        return {"success": False, "error": f"Unknown mouse action: {action}"}


# Global singleton controller
MOUSE = MouseController()
