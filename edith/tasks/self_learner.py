"""Autonomous Self-Learning Task Solver for EDITH.

Enables EDITH to autonomously plan, execute PowerShell commands, inspect output,
self-correct on errors, and commit successful procedures into lifelong SQLite memory.
Provides true agentic self-learning capabilities like Antigravity.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional

from edith.core.state_machine import STATE, SystemState
from edith.memory.local_store import MEMORY
from edith.providers.router import ROUTER, TaskCategory
from edith.tools.windows import WIN_TOOLS

logger = logging.getLogger("edith.tasks.self_learner")


class SelfLearner:
    """Agentic self-learning execution engine for Windows OS automation."""

    def __init__(self):
        self.memory = MEMORY
        self.win = WIN_TOOLS

    def _clean_command(self, raw_cmd: str) -> str:
        """Strip markdown code fences and unnecessary wrapping."""
        cleaned = raw_cmd.strip()
        # Remove ```powershell or ``` blocks
        m = re.search(r"```(?:powershell|ps1|batch)?\s*(.*?)\s*```", cleaned, re.DOTALL | re.IGNORECASE)
        if m:
            cleaned = m.group(1).strip()
        lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
        if lines:
            # If multiple lines, join with semicolon if appropriate, or keep as script
            return "; ".join(lines) if len(lines) <= 4 else "\n".join(lines)
        return cleaned

    async def solve_task(self, goal: str, max_attempts: int = 3) -> Dict[str, Any]:
        """Autonomously accomplish a goal, self-correct on errors, and learn the procedure."""
        clean_goal = (goal or "").strip()
        if not clean_goal:
            return {"success": False, "error": "No goal provided to solve"}

        logger.info("Self-Learner tackling goal: '%s'", clean_goal)
        STATE.set_state_sync(SystemState.PLANNING, reason=f"Solving task: {clean_goal}")

        # 1. Check if this task was previously learned and solved
        existing = self.memory.find_learned_skill(clean_goal)
        if existing:
            cmd = existing["command"]
            logger.info("Found previously learned skill for '%s': %s", clean_goal, cmd)
            STATE.set_state_sync(SystemState.EXECUTING, reason="Executing previously learned skill")
            res = self.win.run_powershell(cmd)
            STATE.set_state_sync(SystemState.READY, reason="Learned skill execution complete")
            if res.get("success"):
                return {
                    "success": True,
                    "goal": clean_goal,
                    "learned": True,
                    "command": cmd,
                    "output": res.get("output", ""),
                    "message": f"Executed learned procedure for '{clean_goal}'.",
                }

        # 2. Autonomous iterative planning and self-correction loop
        last_error = ""
        current_cmd = ""
        attempts_history = []

        system_instruction = (
            "You are EDITH Autonomous System Engineer on Windows 11.\n"
            "Given a user goal, output ONLY the single, robust PowerShell command or script "
            "to achieve it. Do NOT output explanations, introductory text, or markdown blocks. "
            "Output purely the runnable PowerShell command."
        )

        for attempt in range(1, max_attempts + 1):
            STATE.set_state_sync(SystemState.PLANNING, reason=f"Self-learner planning attempt {attempt}")
            if attempt == 1:
                prompt = f"Goal: {clean_goal}\nProvide the PowerShell command to complete this task on Windows."
            else:
                prompt = (
                    f"Goal: {clean_goal}\n"
                    f"Previous command failed: '{current_cmd}'\n"
                    f"Error encountered: '{last_error}'\n"
                    f"Analyze the error and provide a corrected, working PowerShell command."
                )

            try:
                resp = await ROUTER.execute(
                    prompt=prompt,
                    category=TaskCategory.CODING,
                    system_prompt=system_instruction,
                )
                current_cmd = self._clean_command(resp.content)
            except Exception as e:
                logger.warning("Router planning error on attempt %d: %s", attempt, e)
                current_cmd = f"Get-Process | Where-Object {{ $_.Name -like '*{clean_goal}*' }}"

            if not current_cmd:
                last_error = "Model generated empty command."
                continue

            logger.info("Attempt %d executing command: %s", attempt, current_cmd)
            STATE.set_state_sync(SystemState.EXECUTING, reason=f"Executing attempt {attempt}")
            exec_res = self.win.run_powershell(current_cmd)
            attempts_history.append({"attempt": attempt, "command": current_cmd, "result": exec_res})

            if exec_res.get("success"):
                # Success! Persist verified solution into lifelong SQLite memory
                logger.info("Task '%s' succeeded on attempt %d! Persisting to memory.", clean_goal, attempt)
                self.memory.remember_skill(
                    goal=clean_goal,
                    command=current_cmd,
                    description=f"Self-learned autonomous procedure for: {clean_goal}",
                )
                STATE.set_state_sync(SystemState.READY, reason="Self-learning task complete")
                out_msg = exec_res.get("output") or "Task executed successfully."
                return {
                    "success": True,
                    "goal": clean_goal,
                    "learned": False,
                    "attempts": attempt,
                    "command": current_cmd,
                    "output": out_msg,
                    "message": f"Accomplished '{clean_goal}' and committed procedure to lifelong memory.",
                }
            else:
                last_error = exec_res.get("stderr") or exec_res.get("error") or f"Exit code {exec_res.get('exit_code')}"
                logger.warning("Attempt %d failed with error: %s", attempt, last_error)

        STATE.set_state_sync(SystemState.READY, reason="Self-learning task attempts ended")
        return {
            "success": False,
            "goal": clean_goal,
            "attempts": max_attempts,
            "last_error": last_error,
            "message": f"Could not accomplish '{clean_goal}' after {max_attempts} attempts. Error: {last_error}",
        }

    def solve_task_sync(self, goal: str) -> Dict[str, Any]:
        """Synchronous wrapper for solve_task."""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.solve_task(goal))
        finally:
            loop.close()

    def get_learned_skills(self) -> List[Dict[str, Any]]:
        """Retrieve all self-learned autonomous skills."""
        return self.memory.get_all_learned_skills()


# Global self-learner singleton
SELF_LEARNER = SelfLearner()
