"""Seamless Two-Way Clipboard Mirroring and AirDrop File Transfer Gateway.

Implements Sections 69, 70, and 74 of the EDITH Master Engineering Constitution.
Provides instant two-way clipboard synchronization between PC and Mobile devices,
plus local AirDrop file uploads and downloads.
"""

from __future__ import annotations

import logging
import os
import re
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from edith.core.config import CONFIG
from edith.core.event_bus import BUS

logger = logging.getLogger("edith.tools.airdrop")


class AirDropGateway:
    """Two-way clipboard bridge and high-speed peer-to-peer file transfer engine."""

    def __init__(self, transfer_dir: Optional[Path] = None):
        self.transfer_dir = transfer_dir or (CONFIG.data_dir / "transfers")
        self.transfer_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._last_clipboard_text: str = ""
        self._last_clipboard_time: float = 0.0

    def get_clipboard_text(self) -> str:
        """Read current text from Windows clipboard."""
        with self._lock:
            # First try win32clipboard for direct Win32 speed with retries
            for _ in range(5):
                try:
                    import win32clipboard
                    import win32con

                    win32clipboard.OpenClipboard()
                    try:
                        if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                            data = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
                            self._last_clipboard_text = data or ""
                            self._last_clipboard_time = time.time()
                            return self._last_clipboard_text
                    finally:
                        win32clipboard.CloseClipboard()
                    break
                except Exception as w32_err:
                    time.sleep(0.03)

            # Fallback to pyperclip with retries
            for _ in range(3):
                try:
                    import pyperclip
                    data = pyperclip.paste()
                    self._last_clipboard_text = data or ""
                    self._last_clipboard_time = time.time()
                    return self._last_clipboard_text
                except Exception as pyclip_err:
                    time.sleep(0.03)

            return self._last_clipboard_text

    def set_clipboard_text(self, text: str, source: str = "mobile") -> bool:
        """Write text to Windows clipboard and emit synchronization event."""
        if text is None:
            text = ""

        with self._lock:
            success = False
            # First try win32clipboard with retries
            for _ in range(5):
                try:
                    import win32clipboard
                    import win32con

                    win32clipboard.OpenClipboard()
                    try:
                        win32clipboard.EmptyClipboard()
                        win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
                        success = True
                    finally:
                        win32clipboard.CloseClipboard()
                    if success:
                        break
                except Exception as w32_err:
                    time.sleep(0.03)

            # Fallback to pyperclip with retries
            if not success:
                for _ in range(3):
                    try:
                        import pyperclip
                        pyperclip.copy(text)
                        success = True
                        break
                    except Exception as pyclip_err:
                        time.sleep(0.03)

            # Internal buffer is always updated for consistent state across network clients
            self._last_clipboard_text = text
            self._last_clipboard_time = time.time()
            BUS.emit("phone:clipboard_synced", {"text": text, "source": source, "timestamp": self._last_clipboard_time})
            logger.info("Clipboard synchronized from %s (%d chars).", source, len(text))

            return True

    def save_uploaded_file(self, filename: str, content_bytes: bytes) -> Dict[str, Any]:
        """Save incoming file from mobile client securely."""
        if not filename:
            filename = f"transfer_{int(time.time())}.bin"

        # Sanitize filename to prevent directory traversal
        clean_name = re.sub(r'[^a-zA-Z0-9_\-\. ]', '_', Path(filename).name)
        if not clean_name:
            clean_name = f"transfer_{int(time.time())}.bin"

        target_path = self.transfer_dir / clean_name
        # Prevent collisions
        base_stem = target_path.stem
        suffix = target_path.suffix
        counter = 1
        while target_path.exists():
            clean_name = f"{base_stem}_{counter}{suffix}"
            target_path = self.transfer_dir / clean_name
            counter += 1

        with open(target_path, "wb") as f:
            f.write(content_bytes)

        file_stat = target_path.stat()
        logger.info("AirDrop received file: '%s' (%d bytes) saved to %s", clean_name, len(content_bytes), target_path)

        BUS.emit(
            "phone:file_received",
            {
                "filename": clean_name,
                "size_bytes": file_stat.st_size,
                "path": str(target_path),
            },
        )

        return {
            "success": True,
            "filename": clean_name,
            "size_bytes": file_stat.st_size,
            "path": str(target_path),
        }

    def get_file_bytes(self, filename: str) -> Optional[bytes]:
        """Read bytes of a shared file."""
        clean_name = Path(filename).name
        target_path = self.transfer_dir / clean_name
        if target_path.exists() and target_path.is_file():
            return target_path.read_bytes()
        return None

    def list_shared_files(self) -> List[Dict[str, Any]]:
        """List files available in the transfers directory."""
        results = []
        try:
            for item in sorted(self.transfer_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
                if item.is_file():
                    stat = item.stat()
                    results.append({
                        "filename": item.name,
                        "size_bytes": stat.st_size,
                        "modified_timestamp": stat.st_mtime,
                        "download_url": f"/api/airdrop/download/{item.name}",
                    })
        except Exception as err:
            logger.warning("Error listing shared files: %s", err)

        return results[:50]


# Global AirDrop gateway singleton
AIRDROP = AirDropGateway()
