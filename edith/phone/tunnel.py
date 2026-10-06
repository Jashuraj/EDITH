"""Global Internet Tunnel Manager for EDITH Remote Mobile Control.

Enables secure remote access from anywhere in the world via:
1. Pinggy SSH zero-config tunnel (using native Windows OpenSSH)
2. Cloudflare Tunnel (cloudflared)
3. Ngrok HTTP tunnel
4. Custom user Cloud / VPS / DDNS endpoint
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("edith.phone.tunnel")

TUNNEL_CONFIG_FILE = Path(__file__).resolve().parent / "tunnel_config.json"


class TunnelManager:
    """Manages cloud tunnels for global remote mobile access."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._active_url: Optional[str] = None
        self._active_provider: Optional[str] = None
        self._process: Optional[subprocess.Popen] = None
        self._custom_url: Optional[str] = None
        self._load_saved_config()

    def _load_saved_config(self) -> None:
        """Load stored tunnel configuration if available."""
        if TUNNEL_CONFIG_FILE.exists():
            try:
                import json
                data = json.loads(TUNNEL_CONFIG_FILE.read_text(encoding="utf-8"))
                self._custom_url = data.get("custom_url")
                if self._custom_url:
                    self._active_url = self._custom_url
                    self._active_provider = "custom"
            except Exception as e:
                logger.warning("Could not read tunnel config: %s", e)

    def _save_config(self) -> None:
        """Persist tunnel configuration."""
        try:
            import json
            data = {"custom_url": self._custom_url}
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
                "custom_url": self._custom_url,
                "has_ssh": bool(shutil.which("ssh")),
                "has_cloudflared": bool(shutil.which("cloudflared")),
                "has_ngrok": bool(shutil.which("ngrok")),
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
            elif self._active_provider == "custom":
                self._active_url = None
                self._active_provider = None
            self._save_config()
            return self._active_url

    def start_tunnel(self, provider: str = "pinggy", port: int = 8794) -> Optional[str]:
        """Start a cloud tunnel process in the background."""
        with self._lock:
            if self._process and self._process.poll() is None:
                self.stop_tunnel()

            if provider == "localtunnel":
                return self._start_localtunnel(port)
            elif provider == "pinggy":
                return self._start_pinggy_tunnel(port)
            elif provider == "cloudflared":
                return self._start_cloudflared_tunnel(port)
            elif provider == "ngrok":
                return self._start_ngrok_tunnel(port)
            else:
                logger.error("Unknown tunnel provider: %s", provider)
                return None

    def _start_localtunnel(self, port: int) -> Optional[str]:
        """Start localtunnel via npx."""
        try:
            npx_bin = "npx.cmd" if os.name == "nt" else "npx"
            p = subprocess.Popen(
                [npx_bin, "--yes", "localtunnel", "--port", str(port)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            self._process = p
            self._active_provider = "localtunnel"
            url_found = None
            start_time = time.time()
            while time.time() - start_time < 12.0:
                line = p.stdout.readline() if p.stdout else ""
                if not line:
                    if p.poll() is not None:
                        break
                    time.sleep(0.1)
                    continue
                match = re.search(r"https://[a-zA-Z0-9\.\-]+\.loca\.lt", line)
                if match:
                    url_found = match.group(0)
                    break

            if url_found:
                self._active_url = url_found
                logger.info("Localtunnel active at: %s", url_found)
                return url_found
            return None
        except Exception as ex:
            logger.error("Failed to start localtunnel: %s", ex)
            return None

    def _start_pinggy_tunnel(self, port: int) -> Optional[str]:
        """Start zero-config SSH tunnel via Pinggy."""
        if not shutil.which("ssh"):
            logger.error("OpenSSH client not found on system.")
            return None

        cmd = [
            "ssh",
            "-p", "443",
            "-R", f"0:localhost:{port}",
            "-o", "StrictHostKeyChecking=no",
            "-o", "ServerAliveInterval=30",
            "a.pinggy.io"
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

            # Parse public URL from Pinggy output (e.g. https://xxx.pinggy.link)
            url_found = None
            start_time = time.time()
            while time.time() - start_time < 8.0:
                line = p.stdout.readline() if p.stdout else ""
                if not line:
                    if p.poll() is not None:
                        break
                    time.sleep(0.1)
                    continue
                match = re.search(r"https://[a-zA-Z0-9\.\-]+\.pinggy\.(?:link|io)", line)
                if match:
                    url_found = match.group(0)
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

        cmd = ["cloudflared", "tunnel", "--url", f"http://localhost:{port}"]
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

            # Query ngrok local api at http://127.0.0.1:4040/api/tunnels
            time.sleep(1.5)
            import urllib.request
            import json
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

    def stop_tunnel(self) -> None:
        """Terminate running cloud tunnel process."""
        with self._lock:
            if self._process:
                try:
                    self._process.terminate()
                    self._process.wait(timeout=2.0)
                except Exception:
                    try:
                        self._process.kill()
                    except Exception:
                        pass
                self._process = None

            if self._active_provider != "custom":
                self._active_url = None
                self._active_provider = None
            logger.info("Cloud tunnel stopped.")


TUNNEL_MANAGER = TunnelManager()
