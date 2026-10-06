"""Deterministic System State Machine for EDITH.

Manages transitions according to Section 155 of the Engineering Constitution.
"""

from __future__ import annotations

import logging
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, Set

from edith.core.event_bus import BUS

logger = logging.getLogger("edith.state_machine")


class SystemState(str, Enum):
    """Discrete runtime states."""
    BOOTING = "BOOTING"
    READY = "READY"
    LISTENING = "LISTENING"
    UNDERSTANDING = "UNDERSTANDING"
    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    WAITING = "WAITING"
    BLOCKED = "BLOCKED"
    PAUSED = "PAUSED"
    OFFLINE = "OFFLINE"
    ONLINE = "ONLINE"
    DEGRADED = "DEGRADED"
    ERROR = "ERROR"
    RECOVERING = "RECOVERING"
    COMPLETED = "COMPLETED"
    EMERGENCY_STOP = "EMERGENCY_STOP"


class InvalidStateTransitionError(Exception):
    """Raised when an illegal state change is attempted."""


class StateMachine:
    """Deterministic state manager with transition validation and UI file mirroring."""

    # Explicit allowed transitions to make invalid states unrepresentable
    ALLOWED_TRANSITIONS: Dict[SystemState, Set[SystemState]] = {
        SystemState.BOOTING: {SystemState.READY, SystemState.ERROR, SystemState.EMERGENCY_STOP},
        SystemState.READY: {
            SystemState.LISTENING,
            SystemState.UNDERSTANDING,
            SystemState.PLANNING,
            SystemState.EXECUTING,
            SystemState.OFFLINE,
            SystemState.ONLINE,
            SystemState.PAUSED,
            SystemState.EMERGENCY_STOP,
        },
        SystemState.LISTENING: {
            SystemState.UNDERSTANDING,
            SystemState.READY,
            SystemState.PAUSED,
            SystemState.EMERGENCY_STOP,
        },
        SystemState.UNDERSTANDING: {
            SystemState.PLANNING,
            SystemState.EXECUTING,
            SystemState.BLOCKED,
            SystemState.ERROR,
            SystemState.READY,
            SystemState.EMERGENCY_STOP,
        },
        SystemState.PLANNING: {
            SystemState.EXECUTING,
            SystemState.BLOCKED,
            SystemState.ERROR,
            SystemState.READY,
            SystemState.EMERGENCY_STOP,
        },
        SystemState.EXECUTING: {
            SystemState.VERIFYING,
            SystemState.WAITING,
            SystemState.BLOCKED,
            SystemState.PAUSED,
            SystemState.ERROR,
            SystemState.RECOVERING,
            SystemState.COMPLETED,
            SystemState.READY,
            SystemState.EMERGENCY_STOP,
        },
        SystemState.VERIFYING: {
            SystemState.COMPLETED,
            SystemState.EXECUTING,
            SystemState.RECOVERING,
            SystemState.ERROR,
            SystemState.READY,
            SystemState.EMERGENCY_STOP,
        },
        SystemState.WAITING: {SystemState.EXECUTING, SystemState.READY, SystemState.EMERGENCY_STOP},
        SystemState.BLOCKED: {SystemState.PLANNING, SystemState.EXECUTING, SystemState.READY, SystemState.EMERGENCY_STOP},
        SystemState.PAUSED: {SystemState.READY, SystemState.EXECUTING, SystemState.EMERGENCY_STOP},
        SystemState.OFFLINE: {SystemState.ONLINE, SystemState.READY, SystemState.EMERGENCY_STOP},
        SystemState.ONLINE: {SystemState.OFFLINE, SystemState.READY, SystemState.EMERGENCY_STOP},
        SystemState.DEGRADED: {SystemState.READY, SystemState.RECOVERING, SystemState.ERROR, SystemState.EMERGENCY_STOP},
        SystemState.ERROR: {SystemState.RECOVERING, SystemState.READY, SystemState.EMERGENCY_STOP},
        SystemState.RECOVERING: {SystemState.READY, SystemState.EXECUTING, SystemState.ERROR, SystemState.EMERGENCY_STOP},
        SystemState.COMPLETED: {SystemState.READY, SystemState.EMERGENCY_STOP},
        SystemState.EMERGENCY_STOP: {SystemState.BOOTING, SystemState.READY},
    }

    def __init__(self, initial_state: SystemState = SystemState.READY, state_dir: Optional[Path] = None):
        self._current_state: SystemState = initial_state
        self._state_dir = state_dir or Path("D:/EDITH final boss/edith/ui/state").resolve()
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._sync_mirror_file()


    @property
    def current_state(self) -> SystemState:
        return self._current_state

    async def transition_to(self, new_state: SystemState, reason: str = "") -> None:
        """Atomically transition state with validation and event dispatch."""
        if new_state == self._current_state:
            return

        # Emergency stop is always allowed from any state
        if new_state != SystemState.EMERGENCY_STOP:
            allowed = self.ALLOWED_TRANSITIONS.get(self._current_state, set())
            if new_state not in allowed:
                msg = f"Cannot transition from {self._current_state.value} to {new_state.value} (Reason: {reason})"
                logger.error(msg)
                raise InvalidStateTransitionError(msg)

        old_state = self._current_state
        self._current_state = new_state
        self._sync_mirror_file()

        logger.info("State transition: %s -> %s (Reason: %s)", old_state.value, new_state.value, reason)
        await BUS.publish(
            "state:changed",
            {"from": old_state.value, "to": new_state.value, "reason": reason},
            source="state_machine",
        )

    def set_state_sync(self, new_state: SystemState, reason: str = "") -> None:
        """Synchronously transition state for daemon and server threads."""
        if new_state == self._current_state:
            return
        old_state = self._current_state
        self._current_state = new_state
        self._sync_mirror_file()
        logger.info("State transition (sync): %s -> %s (Reason: %s)", old_state.value, new_state.value, reason)


    def _sync_mirror_file(self) -> None:
        """Write current state string into state/state file for Ultron & barehands UI."""
        try:
            state_file = self._state_dir / "state"
            state_file.write_text(self._current_state.value.lower(), encoding="utf-8")
        except Exception as e:
            logger.warning("Failed to sync state mirror file: %s", e)


# Global state machine instance
STATE = StateMachine()
