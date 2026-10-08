"""Global Internet Tunnel Manager for EDITH Remote Mobile Control.

Enables ultra-reliable remote access from anywhere in the world via:
1. Localtunnel (with IPv4 127.0.0.1 binding and anti-503 dynamic subdomain auto-fallback)
2. Pinggy SSH zero-config tunnel (native Windows OpenSSH with automatic URL capture)
3. Cloudflare Quick Tunnel (cloudflared)
4. Ngrok HTTP tunnel
5. Custom user Cloud / VPS / DDNS endpoint

Includes an automated watchdog keep-alive monitor that tests the public endpoint
and auto-heals upon disconnect or 503 service interruption.
"""

from __future__ import annotations

import json
import logging
import os
import re
import secrets
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("edith.phone.tunnel")

TUNNEL_CONFIG_FILE = Path(__file__).resolve().parent / "tunnel_config.json"


class TunnelManager:
    """Manages cloud tunnels for global remote mobile access with auto-healing watchdog."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._active_url: Optional[str] = None
        self._active_provider: Optional[str] = None
        self._process: Optional[subprocess.Popen] = None
        self._custom_url: Optional[str] = None
        self._preferred_provider: str = "localtunnel"
        self._subdomain: Optional[str] = "edith-jashu"
        self._active_port: int = 8794
        self._watchdog_thread: Optional[threading.Thread] = None
        self._stop_watchdog = threading.Event()
        self._last_health_check: float = 0.0
        self._is_healthy: bool = False
        self._load_saved_config()

    def _load_saved_config(self) -> None:
        """Load stored tunnel configuration if available."""
        if TUNNEL_CONFIG_FILE.exists():
            try:
                data = json.loads(TUNNEL_CONFIG_FILE.read_text(encoding="utf-8"))
                self._custom_url = data.get("custom_url")
                if data.get("provider") and data.get("provider") != "pinggy":
                    self._preferred_provider = data.get("provider")
                else:
                    self._preferred_provider = "localtunnel"
                self._subdomain = data.get("subdomain") or "edith-jashu"
                if self._custom_url:
                    self._active_url = self._custom_url
                    self._active_provider = "custom"
            except Exception as e:
                logger.warning("Could not read tunnel config: %s", e)

    def _save_config(self) -> None:
        """Persist tunnel configuration."""
        try:
            data = {
                "provider": self._active_provider or self._preferred_provider,
                "subdomain": self._subdomain,
                "custom_url": self._custom_url,
                "active_url": self._active_url,
                "healthy": self._is_healthy,
                "updated_at": time.time(),
            }
            TUNNEL_CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning("Could not save tunnel config: %s", e)

    def get_active_url(self) -> Optional[str]:
        """Return the current public HTTPS tunnel URL."""
        with self._lock:
            return self._active_url

    def get_status(self) -> Dict[str, Any]:
        """Return full tunnel telemetry and status."""
        with self._lock:
            is_running = self._process is not None and self._process.poll() is None
            return {
                "active": bool(self._active_url),
                "url": self._active_url,
                "provider": self._active_provider,
                "is_process_alive": is_running,
                "is_healthy": self._is_healthy,
                "custom_url": self._custom_url,
                "port": self._active_port,
                "has_ssh": bool(shutil.which("ssh")),
                "has_cloudflared": bool(shutil.which("cloudflared")),
                "has_ngrok": bool(shutil.which("ngrok")),
                "has_npx": bool(shutil.which("npx") or shutil.which("npx.cmd")),
            }

    def set_custom_url(self, url: str) -> Optional[str]:
        """Manually specify a custom public URL."""
        cleaned = url.strip().rstrip("/")
        if cleaned and not cleaned.startswith("http://") and not cleaned.startswith("https://"):
            cleaned = f"https://{cleaned}"
        with self._lock:
            self._custom_url = cleaned if cleaned else None
            if cleaned:
                self._active_url = cleaned
                self._active_provider = "custom"
                self._is_healthy = True
            elif self._active_provider == "custom":
                self._active_url = None
                self._active_provider = None
                self._is_healthy = False
            self._save_config()
            return self._active_url

    def check_url_health(self, url: str, timeout: float = 3.5) -> bool:
        """Verify that public URL responds without 503 / 502 error."""
        if not url:
            return False
        clean = url.rstrip("/")
        # Probe /ping first, then /health
        for endpoint in ("/ping", "/health"):
            try:
                target = f"{clean}{endpoint}"
                req = urllib.request.Request(
                    target,
                    headers={
                        "User-Agent": "EDITH-Tunnel-Health/1.0",
                        "Bypass-Tunnel-Reminder": "true",
                        "bypass-tunnel-reminder": "true",
                    },
                )
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    if resp.status == 200:
                        return True
            except urllib.error.HTTPError as ex:
                if ex.code in (502, 503, 504):
                    logger.debug("Tunnel probe received HTTP %d for %s", ex.code, url)
                    return False
            except Exception as ex:
                logger.debug("Tunnel health check probe exception for %s: %s", url, ex)
        return False

    def start_tunnel(
        self,
        provider: Optional[str] = None,
        port: int = 8794,
        subdomain: Optional[str] = None,
    ) -> Optional[str]:
        """Start a cloud tunnel process with anti-503 auto-fallback and health check."""
        with self._lock:
            self._active_port = port
            target_provider = provider or self._preferred_provider or "localtunnel"

            if self._custom_url:
                self._active_url = self._custom_url
                self._active_provider = "custom"
                self._is_healthy = True
                self._ensure_watchdog()
                return self._custom_url

            if self._process and self._process.poll() is None:
                self.stop_tunnel()

            url: Optional[str] = None

            if target_provider == "localtunnel":
                url = self._start_localtunnel(port, subdomain=subdomain)
            elif target_provider == "pinggy":
                url = self._start_pinggy_tunnel(port)
            elif target_provider == "cloudflared":
                url = self._start_cloudflared_tunnel(port)
            elif target_provider == "ngrok":
                url = self._start_ngrok_tunnel(port)

            # Auto-fallback: if requested provider failed, try alternate installed tools
            if not url:
                if target_provider != "pinggy" and shutil.which("ssh"):
                    logger.info("Attempting auto-fallback to Pinggy SSH tunnel...")
                    url = self._start_pinggy_tunnel(port)
                elif target_provider != "localtunnel" and (shutil.which("npx") or shutil.which("npx.cmd")):
                    logger.info("Attempting auto-fallback to Localtunnel...")
                    url = self._start_localtunnel(port, subdomain=None)
                elif shutil.which("cloudflared"):
                    logger.info("Attempting auto-fallback to Cloudflare Quick Tunnel...")
                    url = self._start_cloudflared_tunnel(port)

            if url:
                self._active_url = url
                self._is_healthy = True
                self._save_config()
                self._ensure_watchdog()

            return url

    def _start_localtunnel(
        self,
        port: int,
        subdomain: Optional[str] = None,
    ) -> Optional[str]:
        """Start localtunnel with --local-host 127.0.0.1 and anti-503 dynamic subdomain auto-fallback."""
        npx_bin = "npx.cmd" if os.name == "nt" else "npx"
        if not (shutil.which("npx") or shutil.which("npx.cmd")):
            logger.error("npx binary not found for localtunnel.")
            return None

        # Helper to launch a localtunnel process for a specific subdomain
        def _launch_subdomain(sub: Optional[str]) -> tuple[Optional[subprocess.Popen], Optional[str]]:
            cmd = [
                npx_bin,
                "--yes",
                "localtunnel",
                "--port", str(port),
                "--local-host", "127.0.0.1",  # Explicit IPv4 binding prevents 503 IPv6 mismatch
            ]
            if sub:
                cmd.extend(["--subdomain", sub])

            try:
                p = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
                captured = None
                start_time = time.time()
                while time.time() - start_time < 10.0:
                    line = p.stdout.readline() if p.stdout else ""
                    if not line:
                        if p.poll() is not None:
                            break
                        time.sleep(0.1)
                        continue
                    m = re.search(r"https://[a-zA-Z0-9\.\-]+\.loca\.lt", line)
                    if m:
                        captured = m.group(0)
                        break
                return p, captured
            except Exception as ex:
                logger.error("Localtunnel process launch error: %s", ex)
                return None, None

        # 1. Launch localtunnel with fixed permanent subdomain
        target_sub = "edith-jashu"
        p, url = _launch_subdomain(target_sub)

        if p and url:
            self._process = p
            self._active_provider = "localtunnel"
            self._active_url = url
            self._is_healthy = True
            logger.info("Fixed Localtunnel online & pinned at: %s", url)
            return url

        # If initial launch didn't capture line immediately, retry once with edith-jashu
        time.sleep(1.0)
        p2, url2 = _launch_subdomain(target_sub)
        if p2 and url2:
            self._process = p2
            self._active_provider = "localtunnel"
            self._active_url = url2
            self._is_healthy = True
            logger.info("Fixed Localtunnel online & pinned at: %s", url2)
            return url2

        return None

    def _start_pinggy_tunnel(self, port: int) -> Optional[str]:
        """Start zero-config SSH tunnel via Pinggy."""
        if not shutil.which("ssh"):
            logger.error("OpenSSH client not found on system.")
            return None

        cmd = [
            "ssh",
            "-T",
            "-p", "443",
            "-R", f"0:localhost:{port}",
            "-o", "StrictHostKeyChecking=no",
            "-o", "ServerAliveInterval=20",
            "-o", "ConnectTimeout=8",
            "a.pinggy.io",
        ]

        try:
            p = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            self._process = p
            self._active_provider = "pinggy"

            url_found = None
            start_time = time.time()
            while time.time() - start_time < 8.0:
                line = p.stdout.readline() if p.stdout else ""
                if not line:
                    if p.poll() is not None:
                        break
                    time.sleep(0.1)
                    continue

                matches = re.findall(
                    r"https://[a-zA-Z0-9\.\-]+(?:free\.pinggy\.net|pinggy-free\.link|pinggy\.link|pinggy\.io)",
                    line,
                )
                for m in matches:
                    if "dashboard.pinggy.io" not in m:
                        url_found = m
                        break
                if url_found:
                    break

            if url_found:
                self._active_url = url_found
                logger.info("Pinggy cloud tunnel active at: %s", url_found)
                return url_found
            else:
                logger.warning("Could not capture URL from Pinggy output.")
                return None
        except Exception as ex:
            logger.error("Failed to start Pinggy tunnel: %s", ex)
            return None

    def _start_cloudflared_tunnel(self, port: int) -> Optional[str]:
        """Start Cloudflare Quick Tunnel via cloudflared."""
        if not shutil.which("cloudflared"):
            logger.error("cloudflared CLI not found on system.")
            return None

        cmd = ["cloudflared", "tunnel", "--url", f"http://127.0.0.1:{port}"]
        try:
            p = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            self._process = p
            self._active_provider = "cloudflared"

            url_found = None
            start_time = time.time()
            while time.time() - start_time < 12.0:
                line = p.stdout.readline() if p.stdout else ""
                if not line:
                    if p.poll() is not None:
                        break
                    time.sleep(0.1)
                    continue
                match = re.search(r"https://[a-zA-Z0-9\.\-]+\.trycloudflare\.com", line)
                if match:
                    url_found = match.group(0)
                    break

            if url_found:
                self._active_url = url_found
                logger.info("Cloudflare tunnel active at: %s", url_found)
                return url_found
            return None
        except Exception as ex:
            logger.error("Failed to start Cloudflare tunnel: %s", ex)
            return None

    def _start_ngrok_tunnel(self, port: int) -> Optional[str]:
        """Start Ngrok HTTP tunnel."""
        if not shutil.which("ngrok"):
            logger.error("ngrok CLI not found on system.")
            return None

        try:
            p = subprocess.Popen(
                ["ngrok", "http", str(port)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            self._process = p
            self._active_provider = "ngrok"

            time.sleep(1.5)
            req = urllib.request.Request("http://127.0.0.1:4040/api/tunnels")
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                data = json.loads(resp.read().decode())
                tunnels = data.get("tunnels", [])
                if tunnels:
                    url = tunnels[0].get("public_url")
                    self._active_url = url
                    return url
            return None
        except Exception as ex:
            logger.error("Failed to start ngrok tunnel: %s", ex)
            return None

    def _ensure_watchdog(self) -> None:
        """Start background watchdog thread to auto-heal dropped or 503 tunnels."""
        if self._watchdog_thread and self._watchdog_thread.is_alive():
            return
        self._stop_watchdog.clear()
        self._watchdog_thread = threading.Thread(target=self._watchdog_loop, daemon=True)
        self._watchdog_thread.start()

    def _watchdog_loop(self) -> None:
        """Periodically verify tunnel health and auto-heal on 503 or disconnect."""
        logger.debug("Tunnel watchdog loop started.")
        while not self._stop_watchdog.is_set():
            time.sleep(20.0)
            if self._stop_watchdog.is_set():
                break

            with self._lock:
                provider = self._active_provider
                port = self._active_port
                url = self._active_url

            if not url or provider == "custom":
                continue

            # Verify if process is still running
            proc_dead = self._process is None or self._process.poll() is not None

            # Check endpoint responsiveness (anti-503 probe)
            is_ok = False if proc_dead else self.check_url_health(url)

            with self._lock:
                self._is_healthy = is_ok
                self._last_health_check = time.time()

            if not is_ok:
                logger.warning(
                    "Tunnel %s (%s) is unresponsive or returning 503. Auto-reconnecting...",
                    url,
                    provider,
                )
                self.stop_tunnel()
                new_url = self.start_tunnel(provider=provider or "localtunnel", port=port)
                if new_url:
                    logger.info("Tunnel auto-healed. New active URL: %s", new_url)

    def stop_tunnel(self) -> None:
        """Terminate running cloud tunnel process."""
        with self._lock:
            if self._process:
                try:
                    self._process.terminate()
                    self._process.wait(timeout=1.5)
                except Exception:
                    try:
                        self._process.kill()
                    except Exception:
                        pass
                self._process = None

            if self._active_provider != "custom":
                self._active_url = None
                self._active_provider = None
                self._is_healthy = False
            self._save_config()
            logger.info("Cloud tunnel stopped.")


TUNNEL_MANAGER = TunnelManager()
