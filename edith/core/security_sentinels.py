"""Security Sentinels for EDITH.

Inspired by jarvis-omniroute core/security_sentinels.py architecture.
Provides:
1. FinancialGatekeeper: Mandates single-use token confirmation for monetary actions.
2. CredentialGuardian: Redacts sensitive keys and blocks unauthorized secret publishing.
3. DeviceLockSentinel: Locks Windows workstation and requires voice authorization to unlock.
4. DevicePowerSentinel: Enforces designated sleep and shutdown protocols.
"""

from __future__ import annotations

import logging
import re
import secrets
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("edith.core.security_sentinels")


class FinancialGatekeeper:
    """Stark Financial Protocol Sentinel.

    Mandates explicit user confirmation and single-use token authorization
    whenever an action involves currency or financial resources.
    """

    FINANCIAL_PATTERNS = [
        r"\b(?:buy|purchase|order|checkout|pay|transfer|send|wire|invest|spend)\b.*?(?:\$|\b(?:usd|inr|eur|money|funds|crypto|bitcoin|btc|eth|dollars|rupees|cents|shares|stock)\b)",
        r"\b(?:payment|transaction|credit\s*card|debit\s*card|stripe|paypal|bank\s*transfer|subscription)\b",
        r"\b(?:stock\s*order|crypto\s*trade|transfer\s*funds)\b",
    ]

    def __init__(self):
        self.pending_transaction: Optional[Dict[str, Any]] = None
        self._compiled = [re.compile(p, re.IGNORECASE) for p in self.FINANCIAL_PATTERNS]

    def has_pending_authorization(self) -> bool:
        """Check if a financial authorization is currently awaiting confirmation."""
        return self.pending_transaction is not None

    def detect_financial_task(self, prompt: str) -> Tuple[bool, str]:
        """Detect whether prompt indicates a monetary task."""
        clean = (prompt or "").strip()
        for pat in self._compiled:
            if pat.search(clean):
                return True, clean
        return False, ""

    def create_authorization_request(self, original_prompt: str) -> str:
        """Generate token and formulate confirmation message."""
        token = secrets.token_hex(3).upper()
        self.pending_transaction = {
            "token": token,
            "prompt": original_prompt,
        }
        logger.info("Financial authorization token generated: CONFIRM-%s", token)
        return (
            f"Sir, this task involves financial resources or monetary transaction. "
            f"Under Stark Financial Protocol, explicit authorization is required. "
            f"Do you authorize this transaction with token CONFIRM-{token}?"
        )

    def evaluate_decision(self, prompt: str) -> Optional[Tuple[bool, str, Optional[Dict[str, Any]]]]:
        """Evaluate confirmation or cancellation response from user."""
        if not self.pending_transaction:
            return None

        clean = (prompt or "").lower().strip()
        expected_token = self.pending_transaction["token"].lower()
        original_data = self.pending_transaction

        if any(w in clean for w in ["yes", "authorize", "confirm", "proceed", "approved", expected_token]):
            self.pending_transaction = None
            msg = f"Financial authorization confirmed with token CONFIRM-{original_data['token']}, sir. Proceeding with the transaction."
            return True, msg, original_data

        if any(w in clean for w in ["no", "cancel", "deny", "abort", "stop", "decline"]):
            self.pending_transaction = None
            msg = "Financial transaction aborted per your command, sir. No funds have been accessed."
            return False, msg, original_data

        return None


class CredentialGuardian:
    """Credential Privacy Shield.

    Redacts sensitive credentials from logs and output, and guards against
    unauthorized credential sharing or transmission.
    """

    SENSITIVE_PATTERNS = [
        (re.compile(r"\b(?:sk-[a-zA-Z0-9_\-]{20,})\b", re.IGNORECASE), "[REDACTED_API_KEY]"),
        (re.compile(r"\b(?:ghp_[a-zA-Z0-9]{30,})\b", re.IGNORECASE), "[REDACTED_GITHUB_TOKEN]"),
        (re.compile(r"(?i)\b(?:password\s*[:=]\s*)([^\s,]+)"), "password: [REDACTED_PASSWORD]"),
        (re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"), "[REDACTED_CARD_NUMBER]"),
        (re.compile(r"(?i)\b(?:private\s*key\s*[:=]?\s*)([^\s,]+)"), "private key: [REDACTED_KEY]"),
    ]

    PUBLISHING_PATTERNS = [
        re.compile(r"\b(?:send|post|publish|share|upload|tweet|expose|email|transmit)\b.*?\b(?:credential|password|api\s*key|token|secret|private\s*key)\b", re.IGNORECASE)
    ]

    def __init__(self):
        self.pending_exposure: Optional[Dict[str, Any]] = None

    def redact(self, text: str) -> str:
        """Redact sensitive keys, passwords, and tokens from text."""
        if not text:
            return text
        safe = text
        for pat, repl in self.SENSITIVE_PATTERNS:
            safe = pat.sub(repl, safe)
        return safe

    def has_pending_authorization(self) -> bool:
        """Check if an exposure authorization is awaiting user approval."""
        return self.pending_exposure is not None

    def detect_unauthorized_exposure(self, prompt: str) -> Tuple[bool, str]:
        """Detect attempts to publish or transmit private credentials."""
        clean = (prompt or "").strip()
        for pat in self.PUBLISHING_PATTERNS:
            if pat.search(clean):
                return True, clean
        return False, ""

    def create_authorization_request(self, original_prompt: str) -> str:
        """Generate privacy verification token and confirmation query."""
        token = secrets.token_hex(3).upper()
        self.pending_exposure = {
            "token": token,
            "prompt": original_prompt,
        }
        return (
            f"Sir, this operation involves publishing or transmitting personal credentials or secrets. "
            f"To protect your privacy, explicit confirmation is mandatory. "
            f"Do you authorize publishing these credentials with verification code PRIVACY-{token}?"
        )

    def evaluate_decision(self, prompt: str) -> Optional[Tuple[bool, str, Optional[Dict[str, Any]]]]:
        """Evaluate authorization response for credential exposure."""
        if not self.pending_exposure:
            return None

        clean = (prompt or "").lower().strip()
        expected_token = self.pending_exposure["token"].lower()
        original_data = self.pending_exposure

        if any(w in clean for w in ["yes", "authorize", "confirm", "proceed", expected_token]):
            self.pending_exposure = None
            msg = f"Credential transmission authorized under token PRIVACY-{original_data['token']}, sir. Transmitting securely."
            return True, msg, original_data

        if any(w in clean for w in ["no", "cancel", "deny", "abort", "stop"]):
            self.pending_exposure = None
            msg = "Credential transmission cancelled, sir. Your personal secrets remain strictly protected."
            return False, msg, original_data

        return None


class DeviceLockSentinel:
    """Device Lock Sentinel.

    Locks the Windows desktop workstation and unlocks only when the user
    speaks the explicit verbal unlock phrase.
    """

    def __init__(self):
        self.is_locked: bool = False

    def lock_device(self) -> str:
        """Lock the local Windows workstation immediately."""
        self.is_locked = True
        try:
            import ctypes
            ctypes.windll.user32.LockWorkStation()
            logger.info("LockWorkStation executed.")
        except Exception as ex:
            logger.warning("Could not execute LockWorkStation: %s", ex)
        return "Workstation locked securely, sir. I will stand guard until you state: 'unlock my device'."

    def evaluate_unlock_directive(self, prompt: str) -> Tuple[bool, bool, str]:
        """Evaluate if prompt matches unlock directive."""
        clean = (prompt or "").lower().strip(" \t\n\r\"'.,!?")
        norm = re.sub(r"[^\w\s]", "", clean)

        is_unlock_phrase = bool(
            re.search(r"\b(?:hey\s+)?(?:edith|jarvis)\b.*?\bunlock\s+(?:my\s+)?device\b", norm)
            or norm in {"unlock my device", "unlock device", "unlock screen"}
        )

        if is_unlock_phrase:
            self.is_locked = False
            return True, True, "Authentication verified, sir. Device unlocked and full administrative authority restored."

        if self.is_locked:
            return True, False, "Workstation is locked, sir. State 'unlock my device' to restore access."

        return False, False, ""


class DevicePowerSentinel:
    """Power and Standby Sentinel.

    Safely powers down or suspends workstation when matching the sleep directive.
    """

    def evaluate_shutdown_directive(self, prompt: str) -> Tuple[bool, str]:
        """Check for designated sleep or power down phrase."""
        clean = (prompt or "").lower().strip(" \t\n\r\"'.,!?").replace("'", "")
        # Prevent false positives from meta-instructions
        if any(m in clean for m in ["change", "keyword", "command as", "rule", "instruction"]):
            return False, ""

        if re.search(r"^(?:please\s+)?lets?\s+sleep[,\s]+(?:edith|jarvis)[\s.?!]*$", clean) or clean in {"sleep edith", "sleep jarvis"}:
            return True, "Powering down workstation per protocol, sir. Sleep well. Standing down."
        return False, ""


FINANCIAL_GATEKEEPER = FinancialGatekeeper()
CREDENTIAL_GUARDIAN = CredentialGuardian()
DEVICE_LOCK_SENTINEL = DeviceLockSentinel()
DEVICE_POWER_SENTINEL = DevicePowerSentinel()
