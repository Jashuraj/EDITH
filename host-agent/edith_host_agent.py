#!/usr/bin/env python3
"""
EDITH Host Agent (Windows 10/11): connects THIS PC to an EDITH gateway, outbound-only.

  First run:  python edith_host_agent.py --gateway http://127.0.0.1:3000 --code 123456
  Afterwards: python edith_host_agent.py
  Needs:      Python 3.9+ and `pip install pillow`  (optional: `pip install mss` = faster capture)

Screen frames are captured ONLY while a paired viewer is watching; they are never written to disk.
A topmost "REMOTE SESSION ACTIVE" window with a Disconnect button is shown during sessions.
`--synthetic` sends a labelled TEST PATTERN instead of the screen (for relay testing on any OS).
"""
from __future__ import annotations

import argparse
import hashlib
import http.client
import io
import json
import os
import platform
import subprocess
import sys
import threading
import time
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import winput  # noqa: E402
import wtools  # noqa: E402

AGENT_VERSION = "1.0.0"
CONFIG_DIR = Path(os.environ.get("APPDATA") or Path.home()) / "EDITH"
CONFIG_FILE = CONFIG_DIR / "host_agent.json"

try:
    from PIL import Image, ImageDraw  # type: ignore
    try:
        from PIL import ImageGrab  # type: ignore
    except Exception:
        ImageGrab = None  # type: ignore
except Exception:
    Image = ImageDraw = ImageGrab = None  # type: ignore
try:
    import mss  # type: ignore
except Exception:
    mss = None  # type: ignore


def log(*a):
    print(time.strftime("%H:%M:%S"), "[edith-agent]", *a, flush=True)


class Gateway:
    """Keep-alive HTTP(S) client, one connection per thread."""

    def __init__(self, base: str, token: str | None):
        u = urllib.parse.urlparse(base.rstrip("/"))
        if u.scheme not in ("http", "https") or not u.hostname:
            raise SystemExit("--gateway must look like http(s)://host:port")
        self.base, self.scheme, self.host, self.port, self.prefix = base.rstrip("/"), u.scheme, u.hostname, u.port, u.path.rstrip("/")
        self.token = token
        self.local = threading.local()

    def request(self, method, path, body=None, headers=None, timeout=15.0):
        h = {"User-Agent": f"edith-host-agent/{AGENT_VERSION}"}
        if self.token:
            h["X-Host-Token"] = self.token
        data = None
        if isinstance(body, dict):
            data, h["Content-Type"] = json.dumps(body).encode(), "application/json"
        elif isinstance(body, (bytes, bytearray)):
            data, h["Content-Type"] = bytes(body), "image/jpeg"
        h.update(headers or {})
        for attempt in range(2):
            c = getattr(self.local, "conn", None)
            if c is None:
                cls = http.client.HTTPSConnection if self.scheme == "https" else http.client.HTTPConnection
                c = self.local.conn = cls(self.host, self.port, timeout=timeout)
            c.timeout = timeout
            if c.sock is not None:
                c.sock.settimeout(timeout)
            try:
                c.request(method, self.prefix + path, body=data, headers=h)
                r = c.getresponse()
                raw = r.read()
                try:
                    return r.status, json.loads(raw or b"{}")
                except Exception:
                    return r.status, {}
            except Exception:
                try:
                    c.close()
                except Exception:
                    pass
                self.local.conn = None
                if attempt:
                    raise
        return 0, {}


class Agent:
    def __init__(self, gw: Gateway, synthetic: bool, monitor: int):
        self.gw, self.synthetic, self.monitor = gw, synthetic, monitor
        self.stream = {"active": False, "scale": 1280, "quality": 60, "fps": 15}
        self.stream_evt = threading.Event()
        self.local_block_until = 0.0
        self.killed_seen = int(time.time() * 1000)
        self.stop = threading.Event()
        self.done_jobs: set[str] = set()
        self.indicator = None
        self.stats = {"frames": 0, "bytes": 0, "inputs": 0}

    # ------------------------------------------------------------- capture
    def grab(self):
        if self.synthetic:
            if Image is None:
                raise RuntimeError("--synthetic needs Pillow")
            img = Image.new("RGB", (1280, 720), (8, 15, 21))
            d = ImageDraw.Draw(img)
            t = time.time()
            x = int((t * 200) % 1180)
            d.rectangle([x, 300, x + 100, 400], fill=(107, 221, 207))
            d.text((40, 40), "EDITH RELAY TEST PATTERN - NOT A REAL DESKTOP", fill=(255, 80, 80))
            d.text((40, 80), time.strftime("%H:%M:%S") + f".{int((t % 1) * 1000):03d}", fill=(220, 230, 238))
            return img
        if mss is not None:
            with mss.mss() as s:
                mon = s.monitors[min(self.monitor, len(s.monitors) - 1)]
                raw = s.grab(mon)
                return Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
        if ImageGrab is None:
            raise RuntimeError("Install Pillow: pip install pillow")
        return ImageGrab.grab(all_screens=False)

    def capture_loop(self):
        last_hash, last_sent, fps_target, quality_adj = None, 0.0, 15.0, 0
        while not self.stop.is_set():
            if not self.stream["active"] or time.time() < self.local_block_until:
                self.stream_evt.wait(2)
                self.stream_evt.clear()
                continue
            t0 = time.time()
            try:
                img = self.grab()
                w = int(self.stream.get("scale") or 1280)
                if img.width > w:
                    img = img.resize((w, int(img.height * w / img.width)), Image.BILINEAR)
                small = img.resize((64, 36)).tobytes()
                h = hashlib.blake2b(small, digest_size=8).digest()
                if h == last_hash and time.time() - last_sent < 2.0:  # unchanged screen: send keepalive every 2 s
                    time.sleep(1.0 / max(1, fps_target))
                    continue
                buf = io.BytesIO()
                q = max(25, min(90, int(self.stream.get("quality") or 60) + quality_adj))
                img.save(buf, "JPEG", quality=q, optimize=False)
                cap_ms = int((time.time() - t0) * 1000)
                t1 = time.time()
                st, j = self.gw.request("POST", "/api/host/frame", buf.getvalue(), {"X-Frame-Width": str(img.width), "X-Frame-Height": str(img.height), "X-Capture-Ms": str(cap_ms)}, timeout=10)
                up_ms = (time.time() - t1) * 1000
                last_hash, last_sent = h, time.time()
                self.stats["frames"] += 1
                self.stats["bytes"] += len(buf.getvalue())
                if st == 200 and isinstance(j.get("stream"), dict):
                    self.stream.update(j["stream"])
                    if j.get("accepted") is False:
                        self.stream["active"] = False
                # Adaptive: slow uplink -> fewer frames & lower quality; fast -> recover.
                cap = float(self.stream.get("fps") or 15)
                if up_ms > 400:
                    fps_target, quality_adj = max(2.0, fps_target * 0.7), max(-30, quality_adj - 5)
                elif up_ms < 120:
                    fps_target, quality_adj = min(cap, fps_target + 1), min(0, quality_adj + 2)
                fps_target = min(fps_target, cap)
            except Exception as e:
                log("capture/upload error:", e)
                time.sleep(1)
            elapsed = time.time() - t0
            time.sleep(max(0.0, 1.0 / max(1.0, fps_target) - elapsed))

    # ------------------------------------------------------------- poll (inputs, jobs, notifications)
    def poll_loop(self):
        backoff = 1
        while not self.stop.is_set():
            try:
                st, j = self.gw.request("GET", f"/api/host/poll?wait=20&killed_since={self.killed_seen}", timeout=30)
                if st == 401:
                    log("Host token rejected (revoked?). Re-link with --code.")
                    self.stop.set()
                    return
                if st != 200:
                    raise RuntimeError(f"HTTP {st}")
                backoff = 1
                self.handle(j)
            except Exception as e:
                log("gateway unreachable:", e, f"(retry in {backoff}s)")
                self.set_stream(False)
                time.sleep(backoff)
                backoff = min(30, backoff * 2)

    def set_stream(self, active: bool):
        was = self.stream["active"]
        self.stream["active"] = active
        if active and not was:
            log("REMOTE SESSION ACTIVE - screen is being shared")
            self.stream_evt.set()
        elif was and not active:
            log("remote session ended")
        if self.indicator:
            self.indicator.show(active)

    def handle(self, j: dict):
        s = j.get("stream") or {}
        if j.get("killed_at"):
            self.killed_seen = int(j["killed_at"])
            log("sessions disconnected by owner")
        self.stream.update({k: v for k, v in s.items() if k in ("scale", "quality", "fps")})
        self.set_stream(bool(s.get("active")) and time.time() >= self.local_block_until)
        if time.time() >= self.local_block_until:
            for ev in j.get("inputs") or []:
                try:
                    r = winput.dispatch(ev.get("action", ""), ev.get("params") or {})
                    self.stats["inputs"] += 1
                    if r != "ok":
                        log("input", ev.get("action"), "->", r)
                except Exception as e:
                    log("input error:", e)
        for job in j.get("jobs") or []:
            jid = job.get("id")
            if not jid or jid in self.done_jobs:  # idempotent: never run a job twice
                continue
            self.done_jobs.add(jid)
            log("job:", job.get("summary"))
            res = wtools.run_tool(job.get("tool", ""), job.get("args") or {})
            try:
                self.gw.request("POST", "/api/host/result", {"job_id": jid, **res}, timeout=10)
            except Exception as e:
                log("result upload failed:", e)
        for n in j.get("notifications") or []:
            threading.Thread(target=wtools.toast, args=(f"⏰ {n.get('title', 'Reminder')}", n.get("body") or ""), daemon=True).start()

    def heartbeat_loop(self):
        caps = {"capture": "synthetic-test-pattern" if self.synthetic else ("mss" if mss else ("ImageGrab" if ImageGrab else "none")),
                "input": "SendInput" if winput.IS_WIN else "unavailable", "os": platform.platform()}
        while not self.stop.is_set():
            try:
                st, j = self.gw.request("POST", "/api/host/heartbeat", {"metrics": wtools.metrics(), "capabilities": caps, "agent_version": AGENT_VERSION}, timeout=10)
                if st == 401:
                    self.stop.set()
                    return
            except Exception:
                pass
            self.stop.wait(5)

    def local_disconnect(self):
        """Local kill switch on the PC: stop sharing for 60 s and ask the gateway to drop viewers."""
        self.local_block_until = time.time() + 60
        self.set_stream(False)
        try:
            self.gw.request("POST", "/api/host/kill", {}, timeout=5)
        except Exception:
            pass
        log("Disconnected locally; remote view blocked for 60 s")


class Indicator:
    """Small always-on-top window shown while the screen is shared (tkinter, stdlib)."""

    def __init__(self, on_disconnect):
        self.on_disconnect, self.root, self.visible = on_disconnect, None, False
        try:
            import tkinter as tk  # noqa: F401
            threading.Thread(target=self._run, daemon=True).start()
        except Exception:
            log("tkinter unavailable: no on-screen session indicator (console only)")

    def _run(self):
        import tkinter as tk
        self.root = tk.Tk()
        self.root.title("EDITH remote session")
        self.root.attributes("-topmost", True)
        self.root.overrideredirect(True)
        self.root.configure(bg="#2a0710")
        self.root.geometry(f"+{self.root.winfo_screenwidth() // 2 - 170}+6")
        tk.Label(self.root, text="●  EDITH REMOTE SESSION ACTIVE", fg="#ffd6dc", bg="#2a0710", font=("Segoe UI", 10, "bold")).pack(side="left", padx=10, pady=6)
        tk.Button(self.root, text="Disconnect", command=self.on_disconnect, bg="#ff1744", fg="white", relief="flat").pack(side="left", padx=8, pady=4)
        self.root.withdraw()
        self.root.mainloop()

    def show(self, on: bool):
        if self.root is None or on == self.visible:
            return
        self.visible = on
        self.root.after(0, self.root.deiconify if on else self.root.withdraw)


def main():
    ap = argparse.ArgumentParser(description="EDITH host agent")
    ap.add_argument("--gateway", help="Gateway URL, e.g. http://127.0.0.1:3000")
    ap.add_argument("--code", help="6-digit host link code from HUD > Devices & Remote")
    ap.add_argument("--name", default=platform.node() or "Windows PC")
    ap.add_argument("--synthetic", action="store_true", help="send a labelled test pattern instead of the screen")
    ap.add_argument("--monitor", type=int, default=1, help="monitor index for mss (1 = primary)")
    ap.add_argument("--no-indicator", action="store_true")
    ap.add_argument("--forget", action="store_true", help="delete saved token")
    a = ap.parse_args()

    cfg = {}
    try:
        cfg = json.loads(CONFIG_FILE.read_text("utf-8"))
    except Exception:
        pass
    if a.forget:
        CONFIG_FILE.unlink(missing_ok=True)
        print("Saved host token removed.")
        return
    wtools.load_allowlist(Path(__file__).with_name("allowlist.json"))
    gateway = a.gateway or cfg.get("gateway")
    if not gateway:
        raise SystemExit("First run: --gateway <url> --code <6 digits>")
    gw = Gateway(gateway, cfg.get("host_token") if cfg.get("gateway") == gateway.rstrip("/") else None)
    if a.code or not gw.token:
        if not a.code:
            raise SystemExit("Not linked yet. Get a code in HUD > Devices & Remote > Link this PC, then pass --code.")
        st, j = gw.request("POST", "/api/host/link", {"code": a.code, "name": a.name, "platform": platform.platform(), "agent_version": AGENT_VERSION})
        if st != 200 or not j.get("host_token"):
            raise SystemExit(f"Linking failed: {j.get('error') or st}")
        gw.token = j["host_token"]
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps({"gateway": gateway.rstrip("/"), "host_token": gw.token, "host_id": j.get("host_id")}, indent=2), "utf-8")
        if winput.IS_WIN:
            subprocess.run(["icacls", str(CONFIG_FILE), "/inheritance:r", "/grant:r", f"{os.environ.get('USERNAME', '')}:F"], capture_output=True)
        log("Linked. Token saved to", CONFIG_FILE)
    if not winput.IS_WIN and not a.synthetic:
        log("WARNING: not on Windows - screen capture/input may be unavailable. Use --synthetic for relay tests.")
    agent = Agent(gw, a.synthetic, a.monitor)
    if not a.no_indicator and winput.IS_WIN:
        agent.indicator = Indicator(agent.local_disconnect)
    for fn in (agent.heartbeat_loop, agent.poll_loop, agent.capture_loop):
        threading.Thread(target=fn, daemon=True).start()
    log(f"EDITH host agent {AGENT_VERSION} connected to {gateway} (Ctrl+C to quit)")
    try:
        while not agent.stop.is_set():
            time.sleep(10)
            if agent.stream["active"]:
                log(f"streaming: {agent.stats['frames']} frames, {agent.stats['bytes'] // 1024} KB sent, {agent.stats['inputs']} inputs")
    except KeyboardInterrupt:
        pass
    agent.stop.set()
    log("stopped")


if __name__ == "__main__":
    main()
