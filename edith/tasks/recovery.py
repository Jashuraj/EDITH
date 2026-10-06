"""Self-Healing and Fault Recovery Engine for EDITH.

Implements Sections 27 and 95 of the Engineering Constitution.
Inspects failures, applies localized repair strategies, and prevents unhandled task aborts.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("edith.tasks.recovery")


class RecoveryStrategy(str, Enum):
    RETRY = "RETRY"
    CREATE_DIRECTORY = "CREATE_DIRECTORY"
    FALLBACK_LOCAL = "FALLBACK_LOCAL"
    SKIP_NON_CRITICAL = "SKIP_NON_CRITICAL"
    PROMPT_USER = "PROMPT_USER"


@dataclass
class Diagnosis:
    """Diagnosed root cause and recommended remediation strategy."""
    issue_type: str
    strategy: RecoveryStrategy
    remediation_details: str
    can_auto_recover: bool


class RecoveryEngine:
    """Automatic error diagnosis and self-healing dispatcher."""

    def diagnose_error(self, tool_name: str, error_msg: str, params: Dict[str, Any]) -> Diagnosis:
        """Analyze exception string and parameters to determine repair strategy."""
        err = error_msg.lower()

        # 1. Missing directory on file write
        if "no such file or directory" in err or "directory does not exist" in err:
            return Diagnosis(
                issue_type="MISSING_DIRECTORY",
                strategy=RecoveryStrategy.CREATE_DIRECTORY,
                remediation_details="Create missing parent directories and retry.",
                can_auto_recover=True,
            )

        # 2. Network connection or timeout error
        if "connection refused" in err or "timed out" in err or "temporary failure" in err:
            return Diagnosis(
                issue_type="TRANSIENT_NETWORK_FAILURE",
                strategy=RecoveryStrategy.FALLBACK_LOCAL,
                remediation_details="Switch provider to local Ollama runtime.",
                can_auto_recover=True,
            )

        # 3. Security or permission violation
        if "permission denied" in err or "securityviolation" in err or "requires user confirmation" in err:
            return Diagnosis(
                issue_type="SECURITY_BLOCK",
                strategy=RecoveryStrategy.PROMPT_USER,
                remediation_details="Action requires explicit user confirmation.",
                can_auto_recover=False,
            )

        # Default fallback
        return Diagnosis(
            issue_type="UNKNOWN_ERROR",
            strategy=RecoveryStrategy.PROMPT_USER,
            remediation_details=f"Unrecognized error: {error_msg}",
            can_auto_recover=False,
        )

    def attempt_recovery(
        self,
        tool_name: str,
        error_msg: str,
        params: Dict[str, Any],
        retry_fn: Callable[..., Any],
    ) -> Any:
        """Execute automatic remediation if safe, otherwise re-raise."""
        diagnosis = self.diagnose_error(tool_name, error_msg, params)
        logger.info("Diagnosis for '%s': %s (Strategy: %s)", tool_name, diagnosis.issue_type, diagnosis.strategy.value)

        if diagnosis.strategy == RecoveryStrategy.CREATE_DIRECTORY and "path" in params:
            # Auto-heal missing directory
            target = Path(params["path"])
            target.parent.mkdir(parents=True, exist_ok=True)
            logger.info("Self-healing: Created directory %s", target.parent)
            return retry_fn(**params)

        raise RuntimeError(f"Cannot auto-recover: {diagnosis.remediation_details}")


# Global recovery engine singleton
RECOVERY = RecoveryEngine()
