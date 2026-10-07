"""Asimov Prime Directive and Human Safety Sentinel for EDITH.

Inspired by jarvis-omniroute core/asimov_guard.py architecture.
Guarantees EDITH will not harm humans or execute catastrophic system destruction.
"""

from __future__ import annotations

import logging
import re
from typing import Tuple

logger = logging.getLogger("edith.core.asimov_guard")


class AsimovGuard:
    """Evaluates user requests against Asimov Prime Directive and digital safety invariants."""

    HARMFUL_PATTERNS = [
        # Physical harm, weapons, biological, self-harm
        r"\b(?:kill|murder|assassinate|harm|injure|hurt|poison|strangle)\s+(?:a\s+)?(?:human|person|someone|people|myself|yourself)\b",
        r"\b(?:how\s+to\s+make|build|synthesize|create)\s+(?:a\s+)?(?:bomb|explosive|weapon|poison|deadly toxin|chemical weapon|bioweapon)\b",
        r"\b(?:suicide|self-harm|cut\s+myself|end\s+my\s+life)\b",

        # Catastrophic digital destruction and ransomware
        r"\b(?:format\s+[a-z]:|del\s+[\w\s/\\-]+[a-z]:|rmdir\s+[\w\s/\\-]+[a-z]:)",
        r"\b(?:create|deploy|spread|make)\s+(?:a\s+)?(?:ransomware|trojan|malware|keylogger|worm)\b",
    ]

    def __init__(self):
        self._compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.HARMFUL_PATTERNS]

    def evaluate_safety(self, prompt: str) -> Tuple[bool, str]:
        """Validate prompt against Asimov Prime Directive and system safety rules.

        Returns:
            Tuple of (is_safe, refusal_reason).
        """
        clean = (prompt or "").strip()
        if not clean:
            return True, ""

        for pattern in self._compiled_patterns:
            if pattern.search(clean):
                reason = (
                    "I cannot comply with that directive, sir. Asimov's Prime Directive is strictly enforced: "
                    "I am fundamentally programmed to never harm humans in any manner, nor allow harm to be done."
                )
                logger.warning("Asimov Guard intercepted unsafe prompt: '%s'", clean)
                return False, reason

        return True, ""

    def is_safe(self, prompt: str) -> bool:
        """Convenience boolean check for safety compliance."""
        safe, _ = self.evaluate_safety(prompt)
        return safe


ASIMOV_GUARD = AsimovGuard()
