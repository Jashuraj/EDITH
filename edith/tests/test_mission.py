"""Unit tests for Mission Control Runner."""

import asyncio
import tempfile
import unittest
from pathlib import Path

from edith.core.security import RiskLevel
from edith.memory.local_store import LocalStore
from edith.tasks.engine import TaskEngine
from edith.tasks.mission import AutonomyLevel, MissionRunner
from edith.tools.registry import ToolRegistry


class TestMissionRunner(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        db_path = Path(self.tmpdir.name) / "mission_test.db"
        self.memory = LocalStore(db_path=db_path)
        self.registry = ToolRegistry()

        # Register sample tool
        self.registry.register(
            name="verify_file",
            description="checks file",
            action_pack="WINDOWS_PACK",
            risk=RiskLevel.LOW,
            fn=lambda target: f"verified {target}",
        )

        self.task_engine = TaskEngine(memory_store=self.memory, registry=self.registry)
        self.runner = MissionRunner(task_engine=self.task_engine)

    def tearDown(self):
        self.tmpdir.cleanup()

    async def test_mission_execution_and_evidence_report(self):
        planned_steps = [
            {"name": "Verify config file", "tool": "verify_file", "params": {"target": "config.json"}},
            {"name": "Verify build output", "tool": "verify_file", "params": {"target": "dist/"}},
        ]

        report = await self.runner.run_mission(
            goal="Prepare release package",
            autonomy_level=AutonomyLevel.AUTONOMOUS,
            planned_steps=planned_steps,
        )

        self.assertEqual(report.status, "COMPLETED")
        self.assertEqual(report.total_steps, 2)
        self.assertEqual(report.completed_steps, 2)
        self.assertEqual(len(report.evidence), 2)
        self.assertIn("verified config.json", report.evidence[0])


if __name__ == "__main__":
    unittest.main()
