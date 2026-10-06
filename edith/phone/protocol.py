"""Device Pairing and Command Queue Protocol for Paired Mobile Devices.

Implements Sections 70, 71, 72, 115 of the Engineering Constitution.
"""

from __future__ import annotations

import hmac
import json
import logging
import secrets
from dataclasses import dataclass, field
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


class PhoneProtocol:
    """Authentication and command queue manager for mobile devices."""

    def __init__(self):
        self._paired_devices: Dict[str, DeviceSession] = {}
        self._command_queue: List[Dict[str, Any]] = []

    def pair_device(self, device_id: str, device_name: str) -> str:
        """Issue a cryptographic pairing token for a new mobile device."""
        token = secrets.token_hex(24)
        session = DeviceSession(device_id=device_id, device_name=device_name, token=token)
        self._paired_devices[device_id] = session
        logger.info("Paired new mobile device '%s' (ID: %s)", device_name, device_id)
        return token

    def verify_token(self, device_id: str, token: str) -> bool:
        """Validate mobile token against paired device registry."""
        session = self._paired_devices.get(device_id)
        if not session:
            return False
        return hmac.compare_digest(session.token, token)

    def queue_command(self, device_id: str, command: str, params: Optional[Dict[str, Any]] = None) -> int:
        """Enqueue command from authenticated phone."""
        entry = {
            "device_id": device_id,
            "command": command,
            "params": params or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._command_queue.append(entry)
        logger.info("Queued command from phone '%s': %s", device_id, command)
        return len(self._command_queue)

    def pop_next_command(self) -> Optional[Dict[str, Any]]:
        """Pop next queued mobile command for execution."""
        if self._command_queue:
            return self._command_queue.pop(0)
        return None


# Global phone protocol singleton
PHONE_PROTOCOL = PhoneProtocol()
