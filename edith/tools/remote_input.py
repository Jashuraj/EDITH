"""High-Performance Remote Input Dispatcher & Virtual Gamepad Engine.

Dispatches zero-latency mouse motion, mouse clicks, keyboard keystrokes, unicode typing,
analog joystick directional motion (WASD / Arrows), and gamepad action buttons
directly into the Windows active desktop.
"""

from __future__ import annotations

import ctypes
import logging
import math
import platform
import threading
import time
from ctypes import wintypes
from typing import Any, Dict, List, Optional, Set

from edith.tools.mouse_controller import MOUSE

logger = logging.getLogger("edith.tools.remote_input")

# Virtual-Key Codes
VK_MAP: Dict[str, int] = {
    # Special keys
    "backspace": 0x08,
    "back": 0x08,
    "tab": 0x09,
    "enter": 0x0D,
    "return": 0x0D,
    "shift": 0x10,
    "ctrl": 0x11,
    "control": 0x11,
    "alt": 0x12,
    "pause": 0x13,
    "capslock": 0x14,
    "escape": 0x1B,
    "esc": 0x1B,
    "space": 0x20,
    "pageup": 0x21,
    "pagedown": 0x22,
    "end": 0x23,
    "home": 0x24,
    "left": 0x25,
    "up": 0x26,
    "right": 0x27,
    "down": 0x28,
    "printscreen": 0x2C,
    "insert": 0x2D,
    "delete": 0x2E,
    "del": 0x2E,
    "win": 0x5B,
    "windows": 0x5B,
    # Function keys
    "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73,
    "f5": 0x74, "f6": 0x75, "f7": 0x76, "f8": 0x77,
    "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
}

# Add standard alphanumeric keys
for code in range(ord("0"), ord("9") + 1):
    VK_MAP[chr(code).lower()] = code
for code in range(ord("A"), ord("Z") + 1):
    VK_MAP[chr(code).lower()] = code

# OEM Punctuation keys
OEM_KEYS: Dict[str, int] = {
    ",": 0xBC, ".": 0xBE, "/": 0xBF, ";": 0xBA, "'": 0xDE,
    "[": 0xDB, "]": 0xDD, "\\": 0xDC, "-": 0xBD, "=": 0xBB,
    "`": 0xC0,
}
VK_MAP.update(OEM_KEYS)

# Browser key string normalization map
BROWSER_KEY_MAP: Dict[str, str] = {
    "arrowup": "up",
    "arrowdown": "down",
    "arrowleft": "left",
    "arrowright": "right",
    "escape": "esc",
    "enter": "enter",
    "return": "enter",
    "backspace": "backspace",
    "delete": "del",
    "tab": "tab",
    "shift": "shift",
    "control": "ctrl",
    "alt": "alt",
    "meta": "win",
    "os": "win",
    " ": "space",
    "spacebar": "space",
    "pageup": "pageup",
    "pagedown": "pagedown",
    "home": "home",
    "end": "end",
    "insert": "insert",
}

# Gamepad Action Button to Keyboard Key Mappings
GAME_BUTTON_MAP: Dict[str, str] = {
    "A": "space",       # Primary Action / Jump
    "B": "c",           # Secondary Action / Crouch
    "X": "e",           # Use / Interact
    "Y": "r",           # Reload / Heavy Attack
    "JUMP": "space",    # Dedicated Jump
    "SPRINT": "shift",  # Dedicated Sprint
    "PAUSE": "escape",  # Game Pause / Menu
    "MENU": "escape",   # Menu
    "LB": "q",          # Left Bumper
    "RB": "f",          # Right Bumper
    "LT": "ctrl",       # Left Trigger (Aim / Sneak)
    "FIRE": "mouse_left",       # Primary Attack / Fire
    "ATTACK": "mouse_left",     # Attack
    "AIM": "mouse_right",       # Secondary Aim / Block
    "BLOCK": "mouse_right",     # Block
    "LCLICK": "mouse_left",     # Left Mouse
    "RCLICK": "mouse_right",    # Right Mouse
    "START": "escape",  # Start
    "SELECT": "tab",    # Scoreboard / Map
}

# Win32 SendInput Structures
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
INPUT_KEYBOARD = 1


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_void_p),
    ]


class INPUT(ctypes.Structure):
    class _INPUT(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT)]

    _anonymous_ = ("_input",)
    _fields_ = [("type", wintypes.DWORD), ("_input", _INPUT)]


class RemoteInputDispatcher:
    """Dispatches remote mouse, keyboard, and virtual gamepad input into Windows."""

    def __init__(self):
        self._lock = threading.Lock()
        self._is_windows = platform.system() == "Windows"
        self._u32 = ctypes.windll.user32 if self._is_windows else None
        self._active_joystick_keys: Set[str] = set()
        self._held_keys: Set[str] = set()
        self._last_action_time: float = time.time()

    def _get_vk(self, key_name: str) -> Optional[int]:
        """Resolve string key name to Win32 virtual key code."""
        cleaned = key_name.strip().lower()
        cleaned = BROWSER_KEY_MAP.get(cleaned, cleaned)
        return VK_MAP.get(cleaned)

    def key_down(self, key_name: str) -> bool:
        """Press and hold down a keyboard key with hardware scan code."""
        with self._lock:
            key_clean = key_name.strip().lower()
            vk = self._get_vk(key_clean)
            if not vk or not self._u32:
                self._held_keys.add(key_clean)
                return bool(vk)

            scan = self._u32.MapVirtualKeyW(vk, 0)
            flags = 0
            if vk in (0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x2D, 0x2E, 0x5B):
                flags |= 0x0001  # KEYEVENTF_EXTENDEDKEY
            self._u32.keybd_event(vk, scan, flags, 0)
            self._held_keys.add(key_clean)
            self._last_action_time = time.time()
            return True

    def key_up(self, key_name: str) -> bool:
        """Release a held keyboard key."""
        with self._lock:
            key_clean = key_name.strip().lower()
            vk = self._get_vk(key_clean)
            self._held_keys.discard(key_clean)
            if not vk or not self._u32:
                return bool(vk)

            scan = self._u32.MapVirtualKeyW(vk, 0)
            flags = KEYEVENTF_KEYUP
            if vk in (0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x2D, 0x2E, 0x5B):
                flags |= 0x0001
            self._u32.keybd_event(vk, scan, flags, 0)
            self._last_action_time = time.time()
            return True

    def key_press(self, key_name: str, hold_sec: float = 0.03) -> bool:
        """Press and immediately release a key."""
        res_down = self.key_down(key_name)
        if hold_sec > 0:
            time.sleep(hold_sec)
        res_up = self.key_up(key_name)
        return res_down and res_up

    def type_text(self, text: str) -> bool:
        """Inject unicode text directly into the foreground window."""
        if not text:
            return True

        if not self._u32:
            return True

        with self._lock:
            for char in text:
                if char == "\n" or char == "\r":
                    # Press Enter
                    self._u32.keybd_event(0x0D, 0, 0, 0)
                    self._u32.keybd_event(0x0D, 0, KEYEVENTF_KEYUP, 0)
                    time.sleep(0.01)
                    continue

                # Use SendInput with KEYEVENTF_UNICODE for seamless utf-8 character entry
                inp_down = INPUT(type=INPUT_KEYBOARD)
                inp_down.ki.wVk = 0
                inp_down.ki.wScan = ord(char)
                inp_down.ki.dwFlags = KEYEVENTF_UNICODE
                self._u32.SendInput(1, ctypes.byref(inp_down), ctypes.sizeof(INPUT))

                inp_up = INPUT(type=INPUT_KEYBOARD)
                inp_up.ki.wVk = 0
                inp_up.ki.wScan = ord(char)
                inp_up.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
                self._u32.SendInput(1, ctypes.byref(inp_up), ctypes.sizeof(INPUT))
                time.sleep(0.005)

            self._last_action_time = time.time()
            return True

    def hotkey(self, keys: List[str]) -> bool:
        """Press a combination of keys together (e.g. ['ctrl', 'c'])."""
        if not keys:
            return False

        # Press all keys in sequence
        for k in keys:
            self.key_down(k)

        time.sleep(0.05)

        # Release all keys in reverse sequence
        for k in reversed(keys):
            self.key_up(k)

        return True

    def handle_joystick(
        self,
        x: float,
        y: float,
        deadzone: float = 0.22,
        mode: str = "wasd",
    ) -> Dict[str, Any]:
        """Convert analog joystick normalized coordinates (-1.0 to 1.0) into keyboard directional input.

        x: -1.0 (full left) to +1.0 (full right)
        y: -1.0 (full up / forward) to +1.0 (full down / backward)
        """
        magnitude = math.hypot(x, y)
        new_active: Set[str] = set()

        # Key mapping based on mode
        key_up_str = "w" if mode == "wasd" else "up"
        key_down_str = "s" if mode == "wasd" else "down"
        key_left_str = "a" if mode == "wasd" else "left"
        key_right_str = "d" if mode == "wasd" else "right"

        if magnitude >= deadzone:
            # Check vertical axis (y < 0 is forward/up)
            if y < -deadzone:
                new_active.add(key_up_str)
            elif y > deadzone:
                new_active.add(key_down_str)

            # Check horizontal axis
            if x < -deadzone:
                new_active.add(key_left_str)
            elif x > deadzone:
                new_active.add(key_right_str)

        # Release keys that are no longer active
        to_release = self._active_joystick_keys - new_active
        for k in to_release:
            self.key_up(k)

        # Press keys that are newly active
        to_press = new_active - self._active_joystick_keys
        for k in to_press:
            self.key_down(k)

        self._active_joystick_keys = new_active
        return {
            "success": True,
            "magnitude": round(magnitude, 3),
            "active_keys": list(new_active),
            "released_keys": list(to_release),
            "pressed_keys": list(to_press),
        }

    def release_all_joystick(self) -> None:
        """Release all currently held joystick movement keys."""
        for k in list(self._active_joystick_keys):
            self.key_up(k)
        self._active_joystick_keys.clear()

    def handle_game_button(self, button: str, is_pressed: bool) -> Dict[str, Any]:
        """Dispatch gamepad action button event (A, B, X, Y, Jump, Sprint, Fire, Aim, etc.)."""
        btn_key = GAME_BUTTON_MAP.get(button.upper(), button.lower())

        # Check for mouse actions (Fire / Aim / Left Click / Right Click)
        if btn_key in ("mouse_left", "lclick", "fire"):
            if is_pressed:
                MOUSE.drag_start()
            else:
                MOUSE.drag_end()
            return {
                "success": True,
                "button": button,
                "mapped_action": "mouse_left",
                "state": "down" if is_pressed else "up",
            }
        elif btn_key in ("mouse_right", "rclick", "aim"):
            if self._u32:
                # 0x0008 = RIGHTDOWN, 0x0010 = RIGHTUP
                flags = 0x0008 if is_pressed else 0x0010
                self._u32.mouse_event(flags, 0, 0, 0, 0)
            return {
                "success": True,
                "button": button,
                "mapped_action": "mouse_right",
                "state": "down" if is_pressed else "up",
            }

        if is_pressed:
            success = self.key_down(btn_key)
        else:
            success = self.key_up(btn_key)

        return {
            "success": success,
            "button": button,
            "mapped_key": btn_key,
            "state": "down" if is_pressed else "up",
        }

    def dispatch(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Universal remote control dispatch handler."""
        action = (action or "").strip().lower()

        # --- Mouse Actions ---
        if action in ("move", "mouse_move"):
            x = float(params.get("x", 0.5))
            y = float(params.get("y", 0.5))
            return {"success": MOUSE.move(x, y), "action": "mouse_move"}

        elif action in ("relative_move", "mouse_relative", "camera_look"):
            dx = int(params.get("dx", 0))
            dy = int(params.get("dy", 0))
            return {"success": MOUSE.move_relative(dx, dy), "action": "camera_look"}

        elif action in ("click", "left_click"):
            # Optional coordinate tap
            if "x" in params and "y" in params:
                MOUSE.move(float(params["x"]), float(params["y"]))
            return {"success": MOUSE.left_click(), "action": "left_click"}

        elif action == "right_click":
            if "x" in params and "y" in params:
                MOUSE.move(float(params["x"]), float(params["y"]))
            return {"success": MOUSE.right_click(), "action": "right_click"}

        elif action == "double_click":
            if "x" in params and "y" in params:
                MOUSE.move(float(params["x"]), float(params["y"]))
            return {"success": MOUSE.double_click(), "action": "double_click"}

        elif action == "mouse_down":
            btn = params.get("button", "left").lower()
            if btn == "right":
                if self._u32: self._u32.mouse_event(0x0008, 0, 0, 0, 0)
            elif btn == "middle":
                if self._u32: self._u32.mouse_event(0x0020, 0, 0, 0, 0)
            else:
                MOUSE.drag_start()
            return {"success": True, "action": "mouse_down", "button": btn}

        elif action == "mouse_up":
            btn = params.get("button", "left").lower()
            if btn == "right":
                if self._u32: self._u32.mouse_event(0x0010, 0, 0, 0, 0)
            elif btn == "middle":
                if self._u32: self._u32.mouse_event(0x0040, 0, 0, 0, 0)
            else:
                MOUSE.drag_end()
            return {"success": True, "action": "mouse_up", "button": btn}

        elif action in ("scroll", "mouse_scroll"):
            delta = int(params.get("delta", 1))
            return {"success": MOUSE.scroll(delta), "action": "scroll"}

        elif action in ("scroll_up", "wheel_up"):
            delta = int(params.get("delta", 1))
            return {"success": MOUSE.scroll(abs(delta)), "action": "scroll_up"}

        elif action in ("scroll_down", "wheel_down"):
            delta = int(params.get("delta", -1))
            return {"success": MOUSE.scroll(-abs(delta)), "action": "scroll_down"}

        # --- Keyboard Actions ---
        elif action == "type_text":
            text = str(params.get("text", ""))
            return {"success": self.type_text(text), "action": "type_text"}

        elif action == "key_down":
            key = str(params.get("key", ""))
            return {"success": self.key_down(key), "action": "key_down", "key": key}

        elif action == "key_up":
            key = str(params.get("key", ""))
            return {"success": self.key_up(key), "action": "key_up", "key": key}

        elif action == "key_press":
            key = str(params.get("key", ""))
            return {"success": self.key_press(key), "action": "key_press", "key": key}

        elif action == "hotkey":
            keys = params.get("keys", [])
            return {"success": self.hotkey(keys), "action": "hotkey", "keys": keys}

        # --- Virtual Joystick & Gamepad Actions ---
        elif action in ("joystick", "joystick_move"):
            x = float(params.get("x", 0.0))
            y = float(params.get("y", 0.0))
            deadzone = float(params.get("deadzone", 0.22))
            mode = str(params.get("mode", "wasd"))
            return self.handle_joystick(x, y, deadzone=deadzone, mode=mode)

        elif action in ("joystick_release", "stick_release"):
            self.release_all_joystick()
            return {"success": True, "action": "joystick_release"}

        elif action in ("game_button", "button"):
            button = str(params.get("button", params.get("key", "A")))
            pressed = bool(params.get("pressed", params.get("is_pressed", True)))
            return self.handle_game_button(button, pressed)

        elif action in ("game_button_down", "btn_down"):
            button = str(params.get("button", params.get("key", "A")))
            return self.handle_game_button(button, True)

        elif action in ("game_button_up", "btn_up"):
            button = str(params.get("button", params.get("key", "A")))
            return self.handle_game_button(button, False)

        elif action in ("key_down", "keydown"):
            key = str(params.get("key", ""))
            return {"success": self.key_down(key), "action": "key_down", "key": key}

        elif action in ("key_up", "keyup"):
            key = str(params.get("key", ""))
            return {"success": self.key_up(key), "action": "key_up", "key": key}

        # --- OS Shortcut Actions ---
        elif action == "switch_window":
            return {"success": MOUSE.switch_window(), "action": "switch_window"}

        elif action == "media_toggle":
            return {"success": MOUSE.media_play_pause(), "action": "media_play_pause"}

        return {"success": False, "error": f"Unknown remote input action: '{action}'"}


# Global singleton dispatcher
REMOTE_INPUT = RemoteInputDispatcher()
