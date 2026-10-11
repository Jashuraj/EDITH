"""Win32 input injection for the EDITH host agent (SendInput). Windows only."""
from __future__ import annotations

import ctypes
import sys
import time

IS_WIN = sys.platform == "win32"

VK = {
    "enter": 0x0D, "return": 0x0D, "tab": 0x09, "esc": 0x1B, "escape": 0x1B, "backspace": 0x08, "delete": 0x2E, "del": 0x2E,
    "space": 0x20, " ": 0x20, "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27, "arrowup": 0x26, "arrowdown": 0x28,
    "arrowleft": 0x25, "arrowright": 0x27, "home": 0x24, "end": 0x23, "pageup": 0x21, "pagedown": 0x22, "insert": 0x2D,
    "shift": 0x10, "ctrl": 0x11, "control": 0x11, "alt": 0x12, "win": 0x5B, "meta": 0x5B, "capslock": 0x14,
    "printscreen": 0x2C, "volumeup": 0xAF, "volumedown": 0xAE, "volumemute": 0xAD, "mediaplaypause": 0xB3,
    "medianext": 0xB0, "mediaprev": 0xB1,
}
for i in range(1, 13):
    VK[f"f{i}"] = 0x6F + i
EXTENDED_KEYS = {0x26, 0x28, 0x25, 0x27, 0x24, 0x23, 0x21, 0x22, 0x2D, 0x2E, 0x5B}

if IS_WIN:
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # real pixel coordinates on scaled displays
    except Exception:
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass
    ULONG_PTR = ctypes.c_size_t

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                    ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]

    class HARDWAREINPUT(ctypes.Structure):
        _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD), ("wParamH", wintypes.WORD)]

    class _U(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]

    class INPUT(ctypes.Structure):
        _anonymous_ = ("u",)
        _fields_ = [("type", wintypes.DWORD), ("u", _U)]


def _send(*inputs) -> None:
    if not IS_WIN:
        raise RuntimeError("Input injection requires Windows")
    arr = (INPUT * len(inputs))(*inputs)
    user32.SendInput(len(inputs), arr, ctypes.sizeof(INPUT))


def _mouse(flags, dx=0, dy=0, data=0):
    return INPUT(type=0, mi=MOUSEINPUT(dx, dy, data & 0xFFFFFFFF, flags, 0, 0))


def _key(vk=0, scan=0, flags=0):
    return INPUT(type=1, ki=KEYBDINPUT(vk, scan, flags, 0, 0))


MOVE, ABS, LDOWN, LUP, RDOWN, RUP, MDOWN, MUP, WHEEL = 0x1, 0x8000, 0x2, 0x4, 0x8, 0x10, 0x20, 0x40, 0x800
KEYUP, UNICODE, EXTENDED = 0x2, 0x4, 0x1


def _abs(x: float, y: float):
    x = min(1.0, max(0.0, float(x)))
    y = min(1.0, max(0.0, float(y)))
    return int(x * 65535), int(y * 65535)


def move(x, y):
    ax, ay = _abs(x, y)
    _send(_mouse(MOVE | ABS, ax, ay))


def click(x=None, y=None, button="left", double=False):
    seq = []
    if x is not None and y is not None:
        ax, ay = _abs(x, y)
        seq.append(_mouse(MOVE | ABS, ax, ay))
    d, u = {"left": (LDOWN, LUP), "right": (RDOWN, RUP), "middle": (MDOWN, MUP)}.get(button, (LDOWN, LUP))
    for _ in range(2 if double else 1):
        seq += [_mouse(d), _mouse(u)]
    _send(*seq)


def button(button="left", down=True, x=None, y=None):
    seq = []
    if x is not None and y is not None:
        ax, ay = _abs(x, y)
        seq.append(_mouse(MOVE | ABS, ax, ay))
    d, u = {"left": (LDOWN, LUP), "right": (RDOWN, RUP), "middle": (MDOWN, MUP)}.get(button, (LDOWN, LUP))
    seq.append(_mouse(d if down else u))
    _send(*seq)


def relative(dx, dy):
    _send(_mouse(MOVE, int(max(-200, min(200, float(dx)))), int(max(-200, min(200, float(dy))))))


def scroll(delta):
    _send(_mouse(WHEEL, data=int(max(-20, min(20, float(delta)))) * 120))


def _vk_for(name: str):
    n = str(name).lower()
    if n in VK:
        return VK[n]
    if len(name) == 1:
        return None  # use unicode
    return None


def key(name: str, down: bool | None = None):
    """down=None -> press+release."""
    vk = _vk_for(name)
    if vk is None:
        if len(str(name)) == 1:
            if down is False:
                return
            type_text(str(name))
        return
    fl = EXTENDED if vk in EXTENDED_KEYS else 0
    if down is None:
        _send(_key(vk, 0, fl), _key(vk, 0, fl | KEYUP))
    else:
        _send(_key(vk, 0, fl | (0 if down else KEYUP)))


def hotkey(keys):
    vks = [VK.get(str(k).lower().strip()) or (ord(str(k).upper()[0]) if len(str(k).strip()) == 1 else None) for k in keys]
    vks = [v for v in vks if v]
    if not vks:
        return
    _send(*[_key(v) for v in vks], *[_key(v, 0, KEYUP) for v in reversed(vks)])


def type_text(text: str):
    seq = []
    for ch in str(text)[:500]:
        code = ord(ch)
        if code > 0xFFFF:
            continue
        if ch == "\n":
            seq += [_key(0x0D), _key(0x0D, 0, KEYUP)]
            continue
        seq += [_key(0, code, UNICODE), _key(0, code, UNICODE | KEYUP)]
    for i in range(0, len(seq), 40):
        _send(*seq[i:i + 40])
        time.sleep(0.005)


def dispatch(action: str, p: dict) -> str:
    """Map the EDITH phone/VNC input vocabulary onto SendInput."""
    a = action
    if a in ("mouse_move", "move"):
        move(p.get("x", 0), p.get("y", 0))
    elif a in ("click", "left_click"):
        click(p.get("x"), p.get("y"), "left")
    elif a == "right_click":
        click(p.get("x"), p.get("y"), "right")
    elif a == "double_click":
        click(p.get("x"), p.get("y"), "left", double=True)
    elif a == "mouse_down":
        button(p.get("button", "left"), True, p.get("x"), p.get("y"))
    elif a == "mouse_up":
        button(p.get("button", "left"), False, p.get("x"), p.get("y"))
    elif a in ("relative_move", "mouse_relative", "camera_look"):
        relative(p.get("dx", 0), p.get("dy", 0))
    elif a in ("scroll", "mouse_scroll"):
        scroll(p.get("delta", 0))
    elif a in ("scroll_up", "wheel_up"):
        scroll(3)
    elif a in ("scroll_down", "wheel_down"):
        scroll(-3)
    elif a == "type_text":
        type_text(p.get("text", ""))
    elif a in ("key_press",):
        key(p.get("key", ""), None)
    elif a in ("key_down", "keydown"):
        key(p.get("key", ""), True)
    elif a in ("key_up", "keyup"):
        key(p.get("key", ""), False)
    elif a == "hotkey":
        hotkey(p.get("keys", []))
    elif a == "switch_window":
        hotkey(["alt", "tab"])
    elif a == "media_toggle":
        key("mediaplaypause")
    elif a in ("unlock", "unlock_workstation"):
        return "unsupported: Windows does not allow programmatic unlock"
    elif a.startswith("joystick") or a.startswith("game_button") or a in ("button", "btn_down", "btn_up", "stick_release"):
        return "unsupported: virtual gamepad needs a driver (not bundled)"
    else:
        return f"unknown action {a}"
    return "ok"
