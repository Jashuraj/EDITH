"""EDITH Model Provider Abstraction and Circuit Breaker.

Implements Section 11 (Model Provider Abstraction) and Section 4 (Zero-Credit Guarantee).
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional

logger = logging.getLogger("edith.providers.base")


class CircuitState(str, Enum):
    CLOSED = "CLOSED"      # Normal operation
    OPEN = "OPEN"          # Provider failing, calls blocked and bypassed
    HALF_OPEN = "HALF_OPEN"# Testing provider health after cooldown


class ProviderUnavailableError(Exception):
    """Raised when a model provider is unreachable or circuit is open."""


@dataclass
class CircuitBreaker:
    """Bounded retry and circuit breaker protecting against repeated failed calls."""
    failure_threshold: int = 3
    cooldown_seconds: float = 60.0
    _consecutive_failures: int = 0
    _last_failure_time: float = 0.0
    _state: CircuitState = CircuitState.CLOSED

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if (time.time() - self._last_failure_time) > self.cooldown_seconds:
                self._state = CircuitState.HALF_OPEN
        return self._state

    def record_success(self) -> None:
        """Mark a successful execution."""
        self._consecutive_failures = 0
        self._state = CircuitState.CLOSED

    def record_failure(self, reason: str = "") -> None:
        """Record a provider error, potentially tripping the circuit."""
        self._consecutive_failures += 1
        self._last_failure_time = time.time()
        logger.warning("Provider failure #%d: %s", self._consecutive_failures, reason)

        if self._consecutive_failures >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.error("Circuit breaker TRIPPED to OPEN. Subsequent calls will immediately fail.")

    def can_execute(self) -> bool:
        """Check if calls to this provider are permitted."""
        return self.state != CircuitState.OPEN


@dataclass
class ToolCall:
    """Structured tool call produced by a model."""
    name: str
    arguments: Dict[str, Any]


@dataclass
class ModelResponse:
    """Unified response object returned by all model providers."""
    content: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    model: str = ""
    provider: str = ""
    eval_count: int = 0
    duration_ms: float = 0.0


class LLMProvider(ABC):
    """Base interface for all local and cloud LLM providers."""

    def __init__(self, name: str, is_local: bool = True):
        self.name = name
        self.is_local = is_local
        self.circuit_breaker = CircuitBreaker()

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        model_name: Optional[str] = None,
        temperature: float = 0.2,
    ) -> ModelResponse:
        """Generate text completion."""
        pass

    @abstractmethod
    async def generate_with_tools(
        self,
        prompt: str,
        tools: List[Dict[str, Any]],
        system_prompt: str = "",
        model_name: Optional[str] = None,
    ) -> ModelResponse:
        """Generate with function calling / tool definitions."""
        pass

    @abstractmethod
    async def is_healthy(self) -> bool:
        """Verify provider availability."""
        pass
