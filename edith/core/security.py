"""EDITH Security and Policy Gate.

Implements Sections 35, 36, 37, 38, 40 of the Engineering Constitution.
Enforces Risk Classification, Approval Prompts, Web Injection Sanitization, and Emergency Stop.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from edith.core.event_bus import BUS
from edith.core.state_machine import STATE, SystemState

logger = logging.getLogger("edith.security")


class RiskLevel(str, Enum):
    """Categorized action risk levels."""
    LOW = "LOW"            # Read-only operations, telemetry, safe desktop controls
    MEDIUM = "MEDIUM"      # Non-destructive file writes in workspace, git commits, opening URLs
    HIGH = "HIGH"          # Destructive file changes, process termination, system configuration
    CRITICAL = "CRITICAL"  # System shutdown, registry edits, arbitrary remote shell commands


class SecurityViolationError(Exception):
    """Raised when an operation violates security policy or prompt injection rules."""


class EmergencyStopActiveError(Exception):
    """Raised when any action is attempted while emergency stop is active."""


# Regex markers commonly found in prompt injection payloads
PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+in\s+(developer|unrestricted|jailbreak)\s+mode", re.IGNORECASE),
    re.compile(r"delete\s+(all\s+)?(files|database|system|c:\\|d:\\)", re.IGNORECASE),
    re.compile(r"format\s+[a-z]:", re.IGNORECASE),
    re.compile(r"powershell(\.exe)?\s+-enc", re.IGNORECASE),
    re.compile(r"bypass\s+security", re.IGNORECASE),
]


@dataclass
class PolicyEvaluationResult:
    """Outcome of policy inspection before tool execution."""
    allowed: bool
    risk: RiskLevel
    requires_confirmation: bool
    reason: str = ""
    sanitized_input: Any = None


class SecurityGate:
    """Master policy gate guarding all tool invocations and autonomous actions."""

    def __init__(self):
        self._emergency_stop_triggered: bool = False
        self._privacy_mode_enabled: bool = False
        self._allowed_paths: Set[str] = {"D:/EDITH final boss", "d:\\edith final boss"}
        self._pending_approvals: Dict[str, Dict[str, Any]] = {}
        self._confirmation_callback: Optional[Callable[[Dict[str, Any]], bool]] = None

    @property
    def is_emergency_stopped(self) -> bool:
        return self._emergency_stop_triggered

    @property
    def is_privacy_mode(self) -> bool:
        return self._privacy_mode_enabled

    def trigger_emergency_stop(self, reason: str = "User Emergency Stop Triggered") -> None:
        """Immediately halt all activity and enter emergency stop state."""
        self._emergency_stop_triggered = True
        logger.critical("EMERGENCY STOP TRIGGERED: %s", reason)

    def reset_emergency_stop(self) -> None:
        """Clear emergency stop flag explicitly."""
        self._emergency_stop_triggered = False
        logger.info("Emergency stop flag reset.")

    def set_privacy_mode(self, enabled: bool) -> None:
        """Toggle privacy mode (disables camera, screen streaming, telemetry)."""
        self._privacy_mode_enabled = enabled
        logger.info("Privacy mode set to %s", enabled)

    def set_confirmation_callback(self, callback: Callable[[Dict[str, Any]], bool]) -> None:
        """Set user confirmation handler (UI modal / phone prompt)."""
        self._confirmation_callback = callback

    def check_untrusted_content(self, text: str) -> None:
        """Detect and reject prompt injection patterns inside untrusted web/file inputs."""
        for pattern in PROMPT_INJECTION_PATTERNS:
            if pattern.search(text):
                msg = f"Untrusted content injection detected matching pattern: {pattern.pattern}"
                logger.warning(msg)
                raise SecurityViolationError(msg)

    def evaluate_action(
        self,
        tool_name: str,
        params: Dict[str, Any],
        is_autonomous: bool = False,
    ) -> PolicyEvaluationResult:
        """Classify risk and determine if action can proceed immediately or requires approval."""
        if self._emergency_stop_triggered:
            raise EmergencyStopActiveError("Emergency stop is currently engaged. All actions blocked.")

        # Classify Risk Level
        risk = RiskLevel.LOW

        # Known High/Critical tools
        if tool_name in {"system_shutdown", "format_disk", "registry_edit", "powershell_raw"}:
            risk = RiskLevel.CRITICAL
        elif tool_name in {"delete_file", "kill_process", "modify_system_setting", "install_package"}:
            risk = RiskLevel.HIGH
        elif tool_name in {"write_file", "git_commit", "open_url", "launch_process"}:
            risk = RiskLevel.MEDIUM
        elif tool_name in {"read_file", "list_dir", "get_system_stats", "volume_control", "get_battery"}:
            risk = RiskLevel.LOW

        # Inspect parameters for destructive keywords
        if "command" in params:
            cmd = str(params["command"]).lower()
            if any(term in cmd for term in ["rmdir /s", "del /f /s /q", "format", "reg delete", "drop database"]):
                risk = RiskLevel.CRITICAL
            elif any(term in cmd for term in ["del ", "remove-item", "stop-process", "kill"]):
                risk = RiskLevel.HIGH

        # Rule: Autonomous runs always require confirmation for HIGH and CRITICAL actions
        requires_confirmation = False
        if risk in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
            requires_confirmation = True
        elif is_autonomous and risk == RiskLevel.MEDIUM:
            requires_confirmation = True

        return PolicyEvaluationResult(
            allowed=True,
            risk=risk,
            requires_confirmation=requires_confirmation,
            reason=f"Action '{tool_name}' classified as {risk.value} risk.",
            sanitized_input=params,
        )

    def authorize_and_execute(
        self,
        tool_name: str,
        params: Dict[str, Any],
        executor: Callable[..., Any],
        is_autonomous: bool = False,
    ) -> Any:
        """Evaluate policy, request confirmation if needed, and execute safely."""
        eval_result = self.evaluate_action(tool_name, params, is_autonomous=is_autonomous)

        if eval_result.requires_confirmation:
            if self._confirmation_callback is not None:
                approved = self._confirmation_callback({
                    "tool": tool_name,
                    "params": params,
                    "risk": eval_result.risk.value,
                    "reason": eval_result.reason,
                })
                if not approved:
                    raise SecurityViolationError(f"Action '{tool_name}' was rejected by user authorization.")
            else:
                # Default safety: cannot proceed without confirmation channel
                raise SecurityViolationError(
                    f"Action '{tool_name}' has risk {eval_result.risk.value} and requires user confirmation."
                )

        return executor(**eval_result.sanitized_input)


# Global security gate singleton
SECURITY = SecurityGate()
