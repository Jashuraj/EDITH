"""Asynchronous Event Bus for EDITH subsystem decoupling."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict, List, Optional

logger = logging.getLogger("edith.event_bus")


@dataclass
class Event:
    """An event emitted across the EDITH system."""
    topic: str
    data: Dict[str, Any] = field(default_factory=dict)
    source: str = "core"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


EventHandler = Callable[[Event], Coroutine[Any, Any, None]]


class EventBus:
    """Thread-safe and async Pub/Sub event dispatcher."""

    def __init__(self):
        self._subscribers: Dict[str, List[EventHandler]] = {}
        self._history: List[Event] = []
        self._max_history = 1000

    def subscribe(self, topic: str, handler: EventHandler) -> None:
        """Register an async event handler for a topic (supports wildcard '*')."""
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        self._subscribers[topic].append(handler)

    def unsubscribe(self, topic: str, handler: EventHandler) -> None:
        """Remove a registered handler."""
        if topic in self._subscribers and handler in self._subscribers[topic]:
            self._subscribers[topic].remove(handler)

    async def publish(self, topic: str, data: Optional[Dict[str, Any]] = None, source: str = "core") -> Event:
        """Publish an event and invoke all matching subscribers concurrently."""
        event = Event(topic=topic, data=data or {}, source=source)
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history.pop(0)

        handlers = list(self._subscribers.get(topic, []))
        if topic != "*":
            handlers.extend(self._subscribers.get("*", []))

        if handlers:
            tasks = [asyncio.create_task(self._safe_invoke(h, event)) for h in handlers]
            await asyncio.gather(*tasks, return_exceptions=True)

        return event

    async def _safe_invoke(self, handler: EventHandler, event: Event) -> None:
        try:
            await handler(event)
        except Exception as e:
            logger.error("Error executing handler %s for event %s: %s", handler, event.topic, e)

    def get_recent_events(self, limit: int = 50, topic_prefix: Optional[str] = None) -> List[Event]:
        """Fetch recent event history for auditing and telemetry."""
        filtered = self._history
        if topic_prefix:
            filtered = [e for e in filtered if e.topic.startswith(topic_prefix)]
        return filtered[-limit:]


# Global event bus singleton
BUS = EventBus()
