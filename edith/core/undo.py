"""Reversible Action Undo Stack for EDITH.

Inspired by Mark-LV core/undo.py architecture.
Maintains a bounded stack of reversible operations (volume, mute, windows, etc.).
Allows instantaneous user voice ("undo") or HUD button reversals without blocking.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional

logger = logging.getLogger("edith.core.undo")

MAX_DEPTH = 15


@dataclass
class UndoEntry:
    label: str
    undo_fn: Callable[[], str]
    created_at: float = field(default_factory=time.monotonic)


class UndoManager:
    """Thread-safe undo stack manager."""

    def __init__(self, max_depth: int = MAX_DEPTH):
        self.max_depth = max_depth
        self._stack: List[UndoEntry] = []
        self._lock = threading.Lock()

    def push(self, label: str, undo_fn: Callable[[], str]) -> None:
        """Register a reversible action."""
        if not callable(undo_fn):
            return
        with self._lock:
            self._stack.append(UndoEntry(label=str(label)[:120], undo_fn=undo_fn))
            while len(self._stack) > self.max_depth:
                self._stack.pop(0)
            logger.info("Registered undoable action: %s (depth=%d)", label, len(self._stack))

    def can_undo(self) -> bool:
        """Return True if there are actions to reverse."""
        with self._lock:
            return bool(self._stack)

    def peek(self) -> str:
        """Return the label of the most recent reversible action or empty string."""
        with self._lock:
            return self._stack[-1].label if self._stack else ""

    def history(self) -> List[str]:
        """Return list of reversible action labels, most recent first."""
        with self._lock:
            return [e.label for e in reversed(self._stack)]

    def undo_last(self) -> str:
        """Execute the reversal for the most recent action."""
        with self._lock:
            if not self._stack:
                return "Nothing to undo, sir."
            entry = self._stack.pop()

        try:
            logger.info("Executing undo for action: %s", entry.label)
            res = entry.undo_fn()
            return f"Undone: {entry.label}. {res or ''}".strip()
        except Exception as e:
            logger.error("Undo execution failed for %s: %s", entry.label, e)
            return f"Could not undo {entry.label}: {e}"

    def clear(self) -> None:
        """Clear all undo entries."""
        with self._lock:
            self._stack.clear()


# Global singleton
UNDO_MANAGER = UndoManager()
