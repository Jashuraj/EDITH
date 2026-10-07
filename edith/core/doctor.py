"""EDITH Doctor Subsystem and System Health Inspector.

Implements Sections 93 and 94 of the Engineering Constitution.
Inspects hardware, local model availability, database integrity, and system health.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List

from edith.core.config import CONFIG
from edith.core.security import SECURITY
from edith.memory.local_store import MEMORY
from edith.providers.ollama_provider import OLLAMA
from edith.tools.windows import WIN_TOOLS

logger = logging.getLogger("edith.doctor")


@dataclass
class HealthCheckItem:
    name: str
    status: str  # OK, WARN, FAIL
    details: str


class EdithDoctor:
    """Diagnostic inspector auditing all EDITH subsystems."""

    async def run_diagnostics(self) -> List[HealthCheckItem]:
        """Execute comprehensive health checks."""
        items: List[HealthCheckItem] = []

        # 1. Hardware Check
        hw = CONFIG.hardware
        ram_status = "OK" if hw.total_ram_gb >= 7.5 else "WARN"
        items.append(HealthCheckItem(
            name="Hardware / RAM",
            status=ram_status,
            details=f"{hw.cpu_name} | {hw.total_ram_gb} GB RAM ({hw.free_ram_gb} GB free)",
        ))

        # 2. Storage Check
        disk_status = "OK" if hw.disk_free_gb >= 10.0 else "WARN"
        items.append(HealthCheckItem(
            name="Disk Storage",
            status=disk_status,
            details=f"{hw.disk_free_gb} GB free on target drive",
        ))

        # 3. Ollama & Local AI
        ollama_ok = await OLLAMA.is_healthy()
        if ollama_ok:
            models = await OLLAMA.list_models()
            has_hermes = any("hermes3" in m for m in models)
            status = "OK" if has_hermes else "WARN"
            items.append(HealthCheckItem(
                name="Local AI (Ollama)",
                status=status,
                details=f"Ollama Active. Installed: {', '.join(models[:4])} (Hermes 3B: {'Found' if has_hermes else 'Missing'})",
            ))
        else:
            items.append(HealthCheckItem(
                name="Local AI (Ollama)",
                status="FAIL",
                details="Ollama is not running on localhost:11434. Local inference unavailable.",
            ))

        # 4. Local Database
        try:
            MEMORY.get_preference("health_ping")
            items.append(HealthCheckItem(
                name="Local SQLite Memory",
                status="OK",
                details=f"Database active at {MEMORY.db_path.name}",
            ))
        except Exception as e:
            items.append(HealthCheckItem(
                name="Local SQLite Memory",
                status="FAIL",
                details=f"Database error: {e}",
            ))

        # 5. Security & Safety State
        items.append(HealthCheckItem(
            name="Security Gate",
            status="OK",
            details=f"Emergency Stop: {'ACTIVE' if SECURITY.is_emergency_stopped else 'Disengaged'} | Privacy: {'ON' if SECURITY.is_privacy_mode else 'OFF'}",
        ))

        # 6. OmniRoute Gateway
        try:
            from edith.providers.omniroute_provider import OMNIROUTE_CONTROLLER
            omni_status = OMNIROUTE_CONTROLLER.get_status()
            if omni_status.get("online"):
                items.append(HealthCheckItem(
                    name="OmniRoute Gateway",
                    status="OK",
                    details=f"Gateway online on port {OMNIROUTE_CONTROLLER.port} ({omni_status.get('model_count')} models, {omni_status.get('latency_ms')}ms)",
                ))
            else:
                items.append(HealthCheckItem(
                    name="OmniRoute Gateway",
                    status="INFO",
                    details=f"Gateway standby on port {OMNIROUTE_CONTROLLER.port} (Fallback to Local/Reflex)",
                ))
        except Exception:
            pass

        return items


DOCTOR = EdithDoctor()
