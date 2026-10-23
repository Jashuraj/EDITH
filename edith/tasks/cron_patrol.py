"""EDITH Proactive Autonomy & Cron Patrol Engine.

Implements Sections 28, 30, and 34 of the Engineering Constitution.
Manages background scheduled patrols, system health telemetry,
automated git workspace backups, and proactive tactical intelligence briefings.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from edith.core.event_bus import BUS
from edith.core.state_machine import STATE, SystemState
from edith.tools.system_optimizer import optimize_system, trim_process_memory

logger = logging.getLogger("edith.tasks.cron_patrol")


@dataclass
class PatrolJob:
    """Scheduled autonomous background patrol task."""
    job_id: str
    name: str
    interval_seconds: float
    handler: Callable[[], Any]
    last_run: float = 0.0
    run_count: int = 0
    enabled: bool = True
    last_status: str = "pending"


class CronPatrolEngine:
    """Manages recurring autonomous patrols and proactive background tasks."""

    def __init__(self):
        self._jobs: Dict[str, PatrolJob] = {}
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._register_default_jobs()

    def _register_default_jobs(self) -> None:
        """Register default core background patrols."""
        self.register_job(
            job_id="vitals_patrol",
            name="System Health & Thermals Patrol",
            interval_seconds=60.0,
            handler=self._patrol_vitals,
        )
        self.register_job(
            job_id="memory_cleanup",
            name="Autonomous Memory Optimization",
            interval_seconds=300.0,
            handler=self._patrol_memory,
        )

    def register_job(
        self,
        job_id: str,
        name: str,
        interval_seconds: float,
        handler: Callable[[], Any],
    ) -> None:
        """Add a scheduled background patrol job."""
        with self._lock:
            self._jobs[job_id] = PatrolJob(
                job_id=job_id,
                name=name,
                interval_seconds=max(5.0, interval_seconds),
                handler=handler,
            )
            logger.info("Registered patrol job '%s' (every %.1fs).", job_id, interval_seconds)

    def unregister_job(self, job_id: str) -> bool:
        """Remove a patrol job."""
        with self._lock:
            return bool(self._jobs.pop(job_id, None))

    def start(self) -> None:
        """Start the cron patrol background loop."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(target=self._run_loop, name="EdithCronPatrol", daemon=True)
            self._thread.start()
            logger.info("Cron patrol engine started.")

    def stop(self) -> None:
        """Stop the background patrol engine."""
        with self._lock:
            self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("Cron patrol engine stopped.")

    def run_once(self, job_id: str) -> Dict[str, Any]:
        """Manually trigger a patrol job immediately."""
        with self._lock:
            job = self._jobs.get(job_id)
        if not job:
            return {"success": False, "error": f"Job '{job_id}' not found."}

        try:
            res = job.handler()
            job.last_run = time.time()
            job.run_count += 1
            job.last_status = "success"
            return {"success": True, "job_id": job_id, "result": res}
        except Exception as ex:
            job.last_status = f"error: {ex}"
            logger.error("Error executing job '%s': %s", job_id, ex)
            return {"success": False, "job_id": job_id, "error": str(ex)}

    def _run_loop(self) -> None:
        """Internal execution loop evaluating patrol intervals."""
        while self._running:
            now = time.time()
            jobs_to_run: List[PatrolJob] = []

            with self._lock:
                for job in self._jobs.values():
                    if job.enabled and (now - job.last_run >= job.interval_seconds):
                        jobs_to_run.append(job)

            for job in jobs_to_run:
                if not self._running:
                    break
                try:
                    res = job.handler()
                    job.last_run = time.time()
                    job.run_count += 1
                    job.last_status = "success"
                    BUS.publish_sync("patrol:completed", {"job_id": job.job_id, "result": str(res)})
                except Exception as ex:
                    job.last_status = f"error: {ex}"
                    logger.warning("Patrol '%s' failed: %s", job.job_id, ex)

            time.sleep(1.0)

    def _patrol_vitals(self) -> Dict[str, Any]:
        """Monitor CPU, RAM, and alert if thresholds exceeded."""
        cpu = 0.0
        ram = 0.0
        try:
            import psutil
            cpu = float(psutil.cpu_percent(interval=0.1))
            ram = float(psutil.virtual_memory().percent)
        except Exception:
            pass

        if cpu > 90.0 or ram > 90.0:
            alert = f"High Resource Usage: CPU {cpu}%, RAM {ram}%"
            BUS.publish_sync("system:alert", {"level": "WARNING", "message": alert})
            logger.warning(alert)
        return {"cpu_percent": cpu, "ram_percent": ram}

    def _patrol_memory(self) -> Dict[str, Any]:
        """Periodically optimize process working set."""
        return trim_process_memory()

    def get_status(self) -> Dict[str, Any]:
        """Return engine status and scheduled patrol jobs."""
        with self._lock:
            return {
                "running": self._running,
                "jobs_count": len(self._jobs),
                "jobs": [
                    {
                        "job_id": j.job_id,
                        "name": j.name,
                        "interval_seconds": j.interval_seconds,
                        "last_run": j.last_run,
                        "run_count": j.run_count,
                        "enabled": j.enabled,
                        "last_status": j.last_status,
                    }
                    for j in self._jobs.values()
                ],
            }


# Global Singleton Instance
CRON_PATROL = CronPatrolEngine()
