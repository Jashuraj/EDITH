"""Persistent Task Engine with Checkpoints for EDITH.

Implements Sections 28, 29, 30 of the Engineering Constitution.
Tracks multi-step goal execution with state persistence, pausing, and resuming.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from edith.core.event_bus import BUS
from edith.core.security import SECURITY
from edith.core.state_machine import STATE, SystemState
from edith.memory.local_store import MEMORY
from edith.tools.registry import REGISTRY

logger = logging.getLogger("edith.tasks.engine")


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class TaskStep:
    """Individual atomic action within a task."""
    step_id: str
    name: str
    tool_name: str
    params: Dict[str, Any]
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None


@dataclass
class Task:
    """Persistent task object representing a user goal."""
    task_id: str
    goal: str
    steps: List[TaskStep] = field(default_factory=list)
    current_index: int = 0
    status: TaskStatus = TaskStatus.PENDING
    context: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_steps(self) -> int:
        return len(self.steps)

    @property
    def is_finished(self) -> bool:
        return self.status in {TaskStatus.COMPLETED, TaskStatus.FAILED}


class TaskEngine:
    """Engine executing and checkpointing multi-step tasks."""

    def __init__(self, memory_store=None, registry=None):
        self.memory = memory_store or MEMORY
        self.registry = registry or REGISTRY
        self._tasks: Dict[str, Task] = {}

    def create_task(self, goal: str, steps: List[Dict[str, Any]]) -> Task:
        """Create a new task instance from planned steps."""
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        task_steps = []
        for i, s in enumerate(steps):
            task_steps.append(TaskStep(
                step_id=f"step_{i+1}",
                name=s.get("name", f"Step {i+1}"),
                tool_name=s["tool"],
                params=s.get("params", {}),
            ))

        task = Task(task_id=task_id, goal=goal, steps=task_steps)
        self._tasks[task_id] = task
        self._save_checkpoint(task)
        logger.info("Created task %s with %d steps: '%s'", task_id, len(task_steps), goal)
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """Fetch task from memory cache or database."""
        if task_id in self._tasks:
            return self._tasks[task_id]

        cp = self.memory.get_checkpoint(task_id)
        if cp:
            # Rehydrate from checkpoint
            task = Task(
                task_id=cp["task_id"],
                goal=cp["goal"],
                current_index=cp["step_index"],
                status=TaskStatus(cp["status"]),
                context=cp["context_data"].get("context", {}),
            )
            # Rehydrate steps if stored
            raw_steps = cp["context_data"].get("steps", [])
            for s in raw_steps:
                task.steps.append(TaskStep(**s))
            self._tasks[task_id] = task
            return task
        return None

    def _save_checkpoint(self, task: Task) -> None:
        """Serialize current state and write to database."""
        context_payload = {
            "context": task.context,
            "steps": [asdict(s) for s in task.steps],
        }
        self.memory.save_checkpoint(
            task_id=task.task_id,
            goal=task.goal,
            step_index=task.current_index,
            total_steps=task.total_steps,
            status=task.status.value,
            context_data=context_payload,
        )

    async def execute_next_step(self, task_id: str, is_autonomous: bool = False) -> TaskStep:
        """Execute the next pending step of a task."""
        task = self.get_task(task_id)
        if not task:
            raise KeyError(f"Task '{task_id}' not found.")

        if task.current_index >= len(task.steps):
            task.status = TaskStatus.COMPLETED
            self._save_checkpoint(task)
            return task.steps[-1]

        step = task.steps[task.current_index]
        step.status = TaskStatus.RUNNING
        task.status = TaskStatus.RUNNING
        self._save_checkpoint(task)

        await BUS.publish("task:step:start", {"task_id": task_id, "step_id": step.step_id, "name": step.name})

        try:
            # Resolve any dynamic variables from task context in params
            resolved_params = dict(step.params)
            for k, v in resolved_params.items():
                if isinstance(v, str) and v.startswith("$context."):
                    var_key = v.replace("$context.", "")
                    resolved_params[k] = task.context.get(var_key, v)

            # Execute via Registry & Security Gate
            res = self.registry.execute_tool(step.tool_name, resolved_params, is_autonomous=is_autonomous)
            step.result = res
            step.status = TaskStatus.COMPLETED

            # Store result in task context
            task.context[f"{step.step_id}_result"] = res
            task.current_index += 1

            if task.current_index >= len(task.steps):
                task.status = TaskStatus.COMPLETED

            self._save_checkpoint(task)
            await BUS.publish("task:step:success", {"task_id": task_id, "step_id": step.step_id, "result": str(res)})
            return step

        except Exception as e:
            step.status = TaskStatus.FAILED
            step.error = str(e)
            task.status = TaskStatus.FAILED
            self._save_checkpoint(task)
            await BUS.publish("task:step:failed", {"task_id": task_id, "step_id": step.step_id, "error": str(e)})
            raise

    async def run_task(self, task_id: str, is_autonomous: bool = False) -> Task:
        """Execute all steps sequentially until done, paused, or blocked."""
        task = self.get_task(task_id)
        if not task:
            raise KeyError(f"Task '{task_id}' not found.")

        await BUS.publish("task:started", {"task_id": task_id, "goal": task.goal})

        while task.current_index < len(task.steps) and task.status != TaskStatus.PAUSED:
            if SECURITY.is_emergency_stopped:
                task.status = TaskStatus.PAUSED
                self._save_checkpoint(task)
                break
            await self.execute_next_step(task_id, is_autonomous=is_autonomous)

        if task.status == TaskStatus.COMPLETED:
            await BUS.publish("task:completed", {"task_id": task_id, "goal": task.goal})

        return task


# Global task engine singleton
TASK_ENGINE = TaskEngine()
