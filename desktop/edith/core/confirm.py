"""Interface Confirmation Gate for Irreversible Actions.

Inspired by Mark-LV core/confirm.py architecture.
Provides an unforgeable confirmation mechanism for critical commands
such as system shutdown, reboot, or destructive data removal.
The confirmation token must originate from the UI or explicit user action,
preventing autonomous LLM hallucinations from executing high-risk system calls.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Callable, Dict, Optional

logger = logging.getLogger("edith.core.confirm")

TIMEOUT_SECONDS = 60.0


@dataclass
class PendingConfirmation:
    id: str
    action_key: str
    title: str
    description: str
    action_fn: Callable[[], str]
    timestamp: float


class ConfirmationGate:
    """Thread-safe confirmation gate for high-risk system commands."""

    def __init__(self, timeout_seconds: float = TIMEOUT_SECONDS):
        self.timeout_seconds = timeout_seconds
        self._pending: Optional[PendingConfirmation] = None
        self._lock = threading.Lock()

    def request(
        self,
        action_key: str,
        title: str,
        description: str,
        action_fn: Callable[[], str],
    ) -> Dict[str, str]:
        """Request confirmation for an irreversible operation."""
        req_id = str(uuid.uuid4())[:8]
        entry = PendingConfirmation(
            id=req_id,
            action_key=action_key,
            title=title,
            description=description,
            action_fn=action_fn,
            timestamp=time.monotonic(),
        )
        with self._lock:
            self._pending = entry

        logger.warning("Confirmation requested [%s]: %s - %s", req_id, title, description)
        return {
            "id": req_id,
            "status": "pending_confirmation",
            "action": action_key,
            "title": title,
            "description": description,
            "message": f"Confirmation required: {title}. Please approve on the HUD or say confirm.",
        }

    def get_pending(self) -> Optional[Dict[str, str]]:
        """Return currently pending confirmation if not expired."""
        with self._lock:
            if not self._pending:
                return None
            if time.monotonic() - self._pending.timestamp > self.timeout_seconds:
                self._pending = None
                return None
            return {
                "id": self._pending.id,
                "action": self._pending.action_key,
                "title": self._pending.title,
                "description": self._pending.description,
            }

    def resolve(self, req_id: str, approved: bool) -> Dict[str, str]:
        """Resolve pending confirmation."""
        with self._lock:
            if not self._pending:
                return {"success": False, "message": "No pending confirmation found."}
            if time.monotonic() - self._pending.timestamp > self.timeout_seconds:
                self._pending = None
                return {"success": False, "message": "Confirmation timed out."}
            if self._pending.id != req_id:
                return {"success": False, "message": "Invalid confirmation ID."}

            pending_action = self._pending
            self._pending = None

        if not approved:
            logger.info("Confirmation rejected for %s", pending_action.action_key)
            return {"success": True, "message": f"Action cancelled: {pending_action.title}."}

        try:
            logger.info("Executing approved action: %s", pending_action.action_key)
            res = pending_action.action_fn()
            return {"success": True, "message": f"Executed: {pending_action.title}. {res or ''}".strip()}
        except Exception as e:
            logger.error("Error executing confirmed action: %s", e)
            return {"success": False, "message": f"Action execution error: {e}"}

    def clear(self) -> None:
        """Discard pending confirmation."""
        with self._lock:
            self._pending = None


# Global singleton
CONFIRMATION_GATE = ConfirmationGate()
