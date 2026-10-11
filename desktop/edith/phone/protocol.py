"""Device Pairing, Bi-Directional Queue, and Clipboard Protocol for Mobile Devices.

Implements Sections 70, 71, 72, 115 of the Engineering Constitution.
Supports bi-directional PC <-> Mobile control, device telemetry tracking,
and real-time clipboard synchronization.
"""

from __future__ import annotations

import hmac
import json
import logging
import secrets
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("edith.phone.protocol")


@dataclass
class DeviceSession:
    """Registered paired mobile device."""
    device_id: str
    device_name: str
    token: str
    paired_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_seen: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    battery_percent: Optional[int] = None
    connection_type: str = "UNKNOWN"
    ip_address: str = ""


class PhoneProtocol:
    """Authentication, bi-directional messaging, and clipboard manager for mobile devices."""

    def __init__(self):
        self._paired_devices: Dict[str, DeviceSession] = {}
        self._command_queue: List[Dict[str, Any]] = []
        # Device-specific outgoing messages from PC to Phone
        self._device_outboxes: Dict[str, List[Dict[str, Any]]] = {}
        # Cached clipboard text
        self._last_synced_clipboard: str = ""

    def pair_device(self, device_id: str, device_name: str) -> str:
        """Issue a cryptographic pairing token for a new mobile device."""
        token = secrets.token_hex(24)
        session = DeviceSession(device_id=device_id, device_name=device_name, token=token)
        self._paired_devices[device_id] = session
        if device_id not in self._device_outboxes:
            self._device_outboxes[device_id] = []
        logger.info("Paired new mobile device '%s' (ID: %s)", device_name, device_id)
        return token

    def verify_token(self, device_id: str, token: str) -> bool:
        """Validate mobile token against paired device registry."""
        session = self._paired_devices.get(device_id)
        if not session:
            # If token matches any registered session, allow verification
            for s in self._paired_devices.values():
                if hmac.compare_digest(s.token, token):
                    return True
            return False
        return hmac.compare_digest(session.token, token)

    def queue_command(self, device_id: str, command: str, params: Optional[Dict[str, Any]] = None) -> int:
        """Enqueue command from authenticated phone for laptop execution."""
        entry = {
            "device_id": device_id,
            "command": command,
            "params": params or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._command_queue.append(entry)
        self.update_device_heartbeat(device_id)
        logger.info("Queued command from phone '%s': %s", device_id, command)
        return len(self._command_queue)

    def pop_next_command(self) -> Optional[Dict[str, Any]]:
        """Pop next queued mobile command for execution."""
        if self._command_queue:
            return self._command_queue.pop(0)
        return None

    def send_message_to_phone(self, device_id: str, message: Dict[str, Any]) -> None:
        """Queue a notification or instruction from PC to a connected mobile device."""
        msg_payload = {
            **message,
            "id": secrets.token_hex(6),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if device_id in self._device_outboxes:
            self._device_outboxes[device_id].append(msg_payload)
        else:
            self._device_outboxes[device_id] = [msg_payload]
        logger.info("Queued push message to mobile device '%s': %s", device_id, message.get("type", "notification"))

    def poll_messages_for_phone(self, device_id: str) -> List[Dict[str, Any]]:
        """Retrieve and flush all pending messages destined for this phone."""
        self.update_device_heartbeat(device_id)
        if device_id in self._device_outboxes:
            msgs = self._device_outboxes[device_id]
            self._device_outboxes[device_id] = []
            return msgs
        return []

    def update_device_heartbeat(
        self,
        device_id: str,
        battery_percent: Optional[int] = None,
        connection_type: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        """Update last seen timestamp and telemetry for device."""
        session = self._paired_devices.get(device_id)
        if session:
            session.last_seen = datetime.now(timezone.utc).isoformat()
            if battery_percent is not None:
                session.battery_percent = battery_percent
            if connection_type:
                session.connection_type = connection_type
            if ip_address:
                session.ip_address = ip_address

    def get_paired_devices(self) -> List[Dict[str, Any]]:
        """Return list of all registered mobile devices."""
        devices = []
        for s in self._paired_devices.values():
            d = asdict(s)
            d.pop("token", None)  # Redact secret token
            devices.append(d)
        return devices

    def sync_clipboard_from_phone(self, text: str, device_id: str) -> Dict[str, Any]:
        """Receive clipboard content from phone and write to Windows desktop clipboard."""
        import time
        copied = False
        last_ex = None
        for _ in range(5):
            try:
                import pyperclip
                pyperclip.copy(text)
                copied = True
                break
            except Exception as ex:
                last_ex = ex
                time.sleep(0.04)

        self._last_synced_clipboard = text
        self.update_device_heartbeat(device_id)

        if copied or (last_ex and "WinError 0" in str(last_ex)):
            logger.info("Synced clipboard from phone '%s' (chars: %d)", device_id, len(text))
            return {"success": True, "length": len(text)}

        # Fallback to internal sync cache if Windows OS clipboard handle is held by another process
        logger.warning("Windows OS clipboard locked by external process (%s), cached internally.", last_ex)
        return {"success": True, "length": len(text), "fallback": True}

    def get_current_clipboard(self) -> str:
        """Read current Windows desktop clipboard content."""
        import time
        for _ in range(3):
            try:
                import pyperclip
                return pyperclip.paste() or ""
            except Exception:
                time.sleep(0.03)
        return self._last_synced_clipboard or ""


# Global phone protocol singleton
PHONE_PROTOCOL = PhoneProtocol()
