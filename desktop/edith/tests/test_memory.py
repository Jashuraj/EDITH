"""Unit tests for Local SQLite Store."""

import tempfile
import unittest
from pathlib import Path
from edith.memory.local_store import LocalStore


class TestLocalStore(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        db_path = Path(self.tmpdir.name) / "test_memory.db"
        self.store = LocalStore(db_path=db_path)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_preferences_set_get(self):
        self.store.set_preference("voice_enabled", True)
        self.store.set_preference("user_name", "Jashwanth")

        self.assertTrue(self.store.get_preference("voice_enabled"))
        self.assertEqual(self.store.get_preference("user_name"), "Jashwanth")
        self.assertIsNone(self.store.get_preference("non_existent"))

    def test_audit_log(self):
        row_id = self.store.log_audit(
            action="execute_tool",
            tool_name="open_app",
            parameters={"app": "chrome"},
            risk_level="LOW",
            status="SUCCESS",
            result="Launched Chrome",
        )
        self.assertGreater(row_id, 0)

        logs = self.store.get_recent_audit_logs(limit=10)
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["action"], "execute_tool")
        self.assertEqual(logs[0]["tool_name"], "open_app")

    def test_checkpoints(self):
        self.store.save_checkpoint(
            task_id="task-101",
            goal="Build release package",
            step_index=2,
            total_steps=5,
            status="IN_PROGRESS",
            context_data={"files_copied": 12},
        )

        cp = self.store.get_checkpoint("task-101")
        self.assertIsNotNone(cp)
        self.assertEqual(cp["step_index"], 2)
        self.assertEqual(cp["context_data"]["files_copied"], 12)


if __name__ == "__main__":
    unittest.main()
