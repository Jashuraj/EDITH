"""Unit tests for Persistent Task Engine."""

import asyncio
import tempfile
import unittest
from pathlib import Path

from edith.core.security import RiskLevel
from edith.memory.local_store import LocalStore
from edith.tasks.engine import TaskEngine, TaskStatus
from edith.tools.registry import ToolRegistry


class TestTaskEngine(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        db_path = Path(self.tmpdir.name) / "task_test.db"
        self.memory = LocalStore(db_path=db_path)
        self.registry = ToolRegistry()

        # Register sample tools
        self.registry.register(
            name="test_echo",
            description="echo text",
            action_pack="WINDOWS_PACK",
            risk=RiskLevel.LOW,
            fn=lambda text: f"echo: {text}",
        )
        self.engine = TaskEngine(memory_store=self.memory, registry=self.registry)

    def tearDown(self):
        self.tmpdir.cleanup()

    async def test_multi_step_task_execution(self):
        steps = [
            {"name": "Say step 1", "tool": "test_echo", "params": {"text": "hello"}},
            {"name": "Say step 2", "tool": "test_echo", "params": {"text": "world"}},
        ]
        task = self.engine.create_task(goal="Greet user", steps=steps)
        self.assertEqual(task.status, TaskStatus.PENDING)
        self.assertEqual(len(task.steps), 2)

        # Run task
        finished_task = await self.engine.run_task(task.task_id)
        self.assertEqual(finished_task.status, TaskStatus.COMPLETED)
        self.assertEqual(finished_task.current_index, 2)
        self.assertEqual(finished_task.steps[0].result, "echo: hello")
        self.assertEqual(finished_task.steps[1].result, "echo: world")

        # Verify checkpoint in database
        cp = self.memory.get_checkpoint(task.task_id)
        self.assertIsNotNone(cp)
        self.assertEqual(cp["status"], "COMPLETED")


if __name__ == "__main__":
    unittest.main()
