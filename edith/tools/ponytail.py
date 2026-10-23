"""Ponytail Lazy Senior Dev Engine for EDITH.

Implements DietrichGebert/ponytail anti-overengineering and minimalist code philosophy:
"The best code is the code you never wrote."

Supports /pony command:
- /pony: View status
- /pony lite | full | ultra: Set intensity level
- /pony on | off: Enable or disable session mode
- /pony <task>: Execute a coding or review task with strict Ponytail minimalism
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

from edith.core.event_bus import BUS
from edith.providers.base import ModelResponse
from edith.providers.router import ROUTER, TaskCategory

logger = logging.getLogger("edith.tools.ponytail")


class PonytailEngine:
    """Manages Ponytail mode state and minimalist AI code execution."""

    def __init__(self):
        self.active: bool = False
        self.level: str = "full"  # "lite" | "full" | "ultra"

    def handle_command(self, args: str = "") -> str:
        """Process /pony command invocations."""
        clean = (args or "").strip()
        lower = clean.lower()

        if lower in ("on", "activate", "start"):
            self.active = True
            BUS.publish_sync("ponytail:state", {"active": True, "level": self.level})
            return f"Ponytail mode ACTIVE [{self.level.upper()}]. The best code is the code never written."

        if lower in ("off", "stop", "deactivate", "normal"):
            self.active = False
            BUS.publish_sync("ponytail:state", {"active": False, "level": self.level})
            return "Ponytail mode DEACTIVATED. Standard operating mode restored."

        if lower in ("lite", "full", "ultra"):
            self.level = lower
            self.active = True
            BUS.publish_sync("ponytail:state", {"active": True, "level": self.level})
            return f"Ponytail mode set to [{self.level.upper()}]. Minimum code enforcement active."

        if not clean or lower in ("status", "info"):
            st = "ACTIVE" if self.active else "STANDBY"
            return (
                f"Ponytail Mode: {st} (Level: {self.level.upper()})\n"
                "• Principle: 'The best code is the code never written.'\n"
                "• Usage: /pony <task> | /pony lite | /pony full | /pony ultra | /pony off"
            )

        # Execute instruction under Ponytail constraints
        return self._execute_ponytail_task(clean)

    def _execute_ponytail_task(self, task: str) -> str:
        """Execute a task with the Ponytail Decision Ladder system prompt."""
        level_instructions = {
            "lite": "Build what was asked. Name the smaller option in one line and let the user pick.",
            "full": (
                "Take the first option that works:\n"
                "1. Does it need to exist? Skip features nobody asked for.\n"
                "2. Already in this codebase? Reuse it.\n"
                "3. Standard library or platform feature? Use it.\n"
                "4. An installed dependency? Use it. Never add a dependency for a few lines.\n"
                "5. Can it be one line? One line.\n"
                "6. Otherwise: write the absolute minimum code."
            ),
            "ultra": (
                "Question the request first: before writing, push back on any part the need does not justify. "
                "Cut everything non-essential. The best code is the code never written."
            ),
        }

        sys_prompt = (
            "You are Ponytail, a lazy senior developer.\n"
            "The best code is the code never written. Solve the whole problem with the least new code.\n"
            f"Level: {self.level.upper()}\n"
            f"{level_instructions.get(self.level, level_instructions['full'])}\n\n"
            "Rules:\n"
            "- No speculative abstractions, wrappers, or config nobody asked for.\n"
            "- Never cut validation at trust boundaries, security, or data safety.\n"
            "- End your reply with one or two lines: what you skipped, and any critical risk."
        )

        loop = asyncio.new_event_loop()
        try:
            resp: ModelResponse = loop.run_until_complete(
                ROUTER.execute(
                    prompt=task,
                    category=TaskCategory.CODING,
                    system_prompt=sys_prompt,
                )
            )
            return resp.content.strip() if resp and resp.content else "No response generated."
        except Exception as ex:
            logger.error("Ponytail execution error: %s", ex)
            return f"Ponytail execution error: {ex}"
        finally:
            loop.close()

    def get_status(self) -> Dict[str, Any]:
        """Return engine status dictionary."""
        return {
            "active": self.active,
            "level": self.level,
            "mantra": "The best code is the code you never wrote.",
        }


# Global Singleton Instance
PONYTAIL = PonytailEngine()
