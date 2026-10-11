"""Allowlisted Windows tools + system metrics for the EDITH host agent."""
from __future__ import annotations

import ctypes
import json
import os
import shutil
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

IS_WIN = sys.platform == "win32"

# name -> (launch command, process image used for verification)
APPS = {
    "chrome": ("chrome", "chrome.exe"), "edge": ("msedge", "msedge.exe"), "firefox": ("firefox", "firefox.exe"),
    "notepad": ("notepad", "notepad.exe"), "calculator": ("calc", "CalculatorApp.exe"), "explorer": ("explorer", "explorer.exe"),
    "taskmgr": ("taskmgr", "Taskmgr.exe"), "settings": ("ms-settings:", None), "terminal": ("wt", "WindowsTerminal.exe"),
    "powershell": ("powershell", "powershell.exe"), "cmd": ("cmd", "cmd.exe"), "vscode": ("code", "Code.exe"),
    "spotify": ("spotify:", "Spotify.exe"), "word": ("winword", "WINWORD.EXE"), "excel": ("excel", "EXCEL.EXE"),
    "powerpoint": ("powerpnt", "POWERPNT.EXE"), "paint": ("mspaint", "mspaint.exe"), "snippingtool": ("ms-screenclip:", None),
    "camera": ("microsoft.windows.camera:", None), "whatsapp": ("whatsapp:", None), "telegram": ("tg:", None),
    "discord": ("discord:", None), "vlc": ("vlc", "vlc.exe"), "outlook": ("outlook", "OUTLOOK.EXE"), "teams": ("msteams:", None),
}
FOLDERS = {"downloads": "Downloads", "documents": "Documents", "desktop": "Desktop", "pictures": "Pictures",
           "music": "Music", "videos": "Videos", "home": ""}
MEDIA_VK = {"play_pause": 0xB3, "next": 0xB0, "prev": 0xB1, "mute": 0xAD, "vol_up": 0xAF, "vol_down": 0xAE}


def load_allowlist(path: Path) -> None:
    """Optional user extension: allowlist.json {"apps": {"obs": ["C:/Program Files/obs-studio/bin/64bit/obs64.exe", "obs64.exe"]}}"""
    try:
        data = json.loads(path.read_text("utf-8"))
        for k, v in (data.get("apps") or {}).items():
            APPS[str(k).lower()] = (v[0], v[1] if len(v) > 1 else None)
    except FileNotFoundError:
        pass
    except Exception as e:
        print("allowlist.json ignored:", e)


# ----------------------------------------------------------------------------- metrics
_cpu_prev = None


def _cpu_percent() -> float | None:
    global _cpu_prev
    if IS_WIN:
        from ctypes import wintypes
        idle, kern, user = wintypes.FILETIME(), wintypes.FILETIME(), wintypes.FILETIME()
        if not ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kern), ctypes.byref(user)):
            return None
        f = lambda ft: (ft.dwHighDateTime << 32) | ft.dwLowDateTime  # noqa: E731
        cur = (f(idle), f(kern), f(user))
    else:
        try:
            vals = list(map(int, open("/proc/stat").readline().split()[1:8]))
            cur = (vals[3] + vals[4], sum(vals), 0)
        except Exception:
            return None
    prev, _cpu_prev = _cpu_prev, cur
    if not prev:
        return None
    if IS_WIN:
        di, dk, du = cur[0] - prev[0], cur[1] - prev[1], cur[2] - prev[2]
        total = dk + du
    else:
        di, total = cur[0] - prev[0], cur[1] - prev[1]
    return round(100.0 * (1 - di / total), 1) if total > 0 else None


def metrics() -> dict:
    m: dict = {"cpu_percent": _cpu_percent()}
    if IS_WIN:
        from ctypes import wintypes

        class MEMSTAT(ctypes.Structure):
            _fields_ = [("dwLength", wintypes.DWORD), ("dwMemoryLoad", wintypes.DWORD), ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong), ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong), ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

        ms = MEMSTAT()
        ms.dwLength = ctypes.sizeof(MEMSTAT)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms)):
            m["ram_percent"] = int(ms.dwMemoryLoad)
            m["ram_used_mb"] = int((ms.ullTotalPhys - ms.ullAvailPhys) / 1048576)
            m["ram_total_mb"] = int(ms.ullTotalPhys / 1048576)

        class PWR(ctypes.Structure):
            _fields_ = [("ACLineStatus", ctypes.c_byte), ("BatteryFlag", ctypes.c_byte), ("BatteryLifePercent", ctypes.c_ubyte),
                        ("SystemStatusFlag", ctypes.c_byte), ("BatteryLifeTime", wintypes.DWORD), ("BatteryFullLifeTime", wintypes.DWORD)]

        p = PWR()
        if ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(p)):
            m["power_plugged"] = p.ACLineStatus == 1
            m["battery_percent"] = None if p.BatteryLifePercent == 255 else int(p.BatteryLifePercent)
        drive = os.environ.get("SystemDrive", "C:") + "\\"
    else:
        try:
            info = dict(l.split(":", 1) for l in open("/proc/meminfo"))
            tot = int(info["MemTotal"].split()[0]); av = int(info["MemAvailable"].split()[0])
            m["ram_percent"] = round(100 * (tot - av) / tot, 1); m["ram_used_mb"] = int((tot - av) / 1024)
        except Exception:
            pass
        m["battery_percent"] = None
        drive = "/"
    try:
        du = shutil.disk_usage(drive)
        m["disk_percent"] = round(100 * du.used / du.total, 1)
        m["disk_free_gb"] = round(du.free / 1e9, 1)
    except Exception:
        pass
    return m


# ----------------------------------------------------------------------------- tools
def _process_running(image: str) -> bool:
    if not IS_WIN or not image:
        return False
    out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {image}", "/NH"], capture_output=True, text=True, timeout=8).stdout
    return image.lower() in out.lower()


def _media(vk: int):
    import winput  # local module
    winput._send(winput._key(vk), winput._key(vk, 0, winput.KEYUP))


def toast(title: str, body: str) -> bool:
    """Native Windows toast via PowerShell (no extra modules)."""
    if not IS_WIN:
        print(f"[notify] {title}: {body}")
        return False
    t = title.replace("'", "''")[:80]
    b = body.replace("'", "''")[:300]
    ps = (
        "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null;"
        "$x = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02);"
        f"$t = $x.GetElementsByTagName('text'); $t.Item(0).AppendChild($x.CreateTextNode('{t}')) > $null; $t.Item(1).AppendChild($x.CreateTextNode('{b}')) > $null;"
        "$n = [Windows.UI.Notifications.ToastNotification]::new($x);"
        "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\WindowsPowerShell\\v1.0\\powershell.exe').Show($n)"
    )
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps], capture_output=True, timeout=15,
                       creationflags=0x08000000)
    return r.returncode == 0


def run_tool(tool: str, args: dict) -> dict:
    """Execute one allowlisted tool. Returns {ok, message, verified}."""
    if not IS_WIN and tool not in ("system_status", "notify"):
        return {"ok": False, "message": f"{tool} requires Windows (agent is running on {sys.platform})."}
    try:
        if tool == "open_app":
            name = str(args.get("app", "")).lower()
            if name not in APPS:
                return {"ok": False, "message": f"{name} is not in the host allowlist."}
            cmd, image = APPS[name]
            already = _process_running(image) if image else False
            if cmd.endswith(":"):
                os.startfile(cmd)  # protocol handler (store apps)
            else:
                subprocess.Popen(["cmd", "/c", "start", "", cmd], creationflags=0x08000000)
            verified = False
            if image:
                for _ in range(10):
                    time.sleep(0.4)
                    if _process_running(image):
                        verified = True
                        break
            msg = f"Opened {name}" + (" ✓ (process running)" if verified else " (launch sent; could not verify)" if not image else " — process not detected; is it installed?")
            return {"ok": verified or not image or already, "message": msg, "verified": verified}
        if tool == "open_url":
            url = str(args.get("url", ""))
            if not url.startswith(("http://", "https://")):
                return {"ok": False, "message": "Only http/https URLs allowed."}
            ok = webbrowser.open(url)
            return {"ok": bool(ok), "message": f"Opened {url} in your default browser" if ok else "Browser did not open", "verified": bool(ok)}
        if tool == "open_folder":
            sub = FOLDERS.get(str(args.get("folder", "")).lower())
            if sub is None:
                return {"ok": False, "message": "Unknown folder"}
            path = Path.home() / sub if sub else Path.home()
            if not path.exists():
                return {"ok": False, "message": f"{path} does not exist"}
            os.startfile(str(path))
            return {"ok": True, "message": f"Opened {path}", "verified": True}
        if tool == "media_control":
            vk = MEDIA_VK.get(str(args.get("action")))
            if not vk:
                return {"ok": False, "message": "Unknown media action"}
            _media(vk)
            return {"ok": True, "message": f"Media key sent: {args.get('action')}"}
        if tool == "set_volume":
            level = max(0, min(100, int(args.get("level", 50))))
            for _ in range(50):
                _media(MEDIA_VK["vol_down"])  # each step = 2%
            for _ in range(level // 2):
                _media(MEDIA_VK["vol_up"])
            return {"ok": True, "message": f"Volume set to ~{level - level % 2}% (media-key steps of 2%)"}
        if tool == "system_status":
            m = metrics()
            return {"ok": True, "message": f"CPU {m.get('cpu_percent')}%, RAM {m.get('ram_percent')}%, battery {m.get('battery_percent')}%", "data": m}
        if tool == "notify":
            ok = toast(str(args.get("title", "EDITH")), str(args.get("body", "")))
            return {"ok": ok, "message": "Notification shown" if ok else "Notification failed"}
        if tool == "lock_pc":
            ok = bool(ctypes.windll.user32.LockWorkStation())
            return {"ok": ok, "message": "PC locked" if ok else "Lock failed", "verified": ok}
        if tool == "type_text":
            import winput
            winput.type_text(str(args.get("text", "")))
            return {"ok": True, "message": f"Typed {len(str(args.get('text', '')))} characters"}
        if tool == "sleep_pc":
            subprocess.Popen(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
            return {"ok": True, "message": "Sleeping now — remote access stops until the PC wakes."}
        if tool == "shutdown_pc":
            r = subprocess.run(["shutdown", "/s", "/t", "30", "/c", "EDITH: shutdown requested (cancel with: shutdown /a)"], capture_output=True)
            return {"ok": r.returncode == 0, "message": "Shutting down in 30 s (cancel on the PC with: shutdown /a)"}
        if tool == "restart_pc":
            r = subprocess.run(["shutdown", "/r", "/t", "30", "/c", "EDITH: restart requested (cancel with: shutdown /a)"], capture_output=True)
            return {"ok": r.returncode == 0, "message": "Restarting in 30 s (cancel on the PC with: shutdown /a)"}
        return {"ok": False, "message": f"Tool {tool} is not implemented on this host."}
    except Exception as e:  # never crash the agent on a tool error
        return {"ok": False, "message": f"{tool} failed: {e}"}
