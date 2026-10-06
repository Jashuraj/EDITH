"""Unit tests for Self-Healing and Recovery Engine."""

import tempfile
import unittest
from pathlib import Path
from edith.tasks.recovery import RecoveryEngine, RecoveryStrategy


class TestRecoveryEngine(unittest.TestCase):
    def setUp(self):
        self.engine = RecoveryEngine()

    def test_diagnose_missing_dir(self):
        diag = self.engine.diagnose_error(
            "write_file", "No such file or directory: 'nested/dir/file.txt'", {"path": "nested/dir/file.txt"}
        )
        self.assertEqual(diag.strategy, RecoveryStrategy.CREATE_DIRECTORY)
        self.assertTrue(diag.can_auto_recover)

    def test_diagnose_network_error(self):
        diag = self.engine.diagnose_error("http_get", "Connection refused on port 443", {})
        self.assertEqual(diag.strategy, RecoveryStrategy.FALLBACK_LOCAL)
        self.assertTrue(diag.can_auto_recover)

    def test_attempt_directory_auto_heal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            deep_file = Path(tmpdir) / "sub1" / "sub2" / "test.txt"

            def mock_write(path: str):
                Path(path).write_text("repaired", encoding="utf-8")
                return True

            res = self.engine.attempt_recovery(
                "write_file",
                "No such file or directory",
                {"path": str(deep_file)},
                mock_write,
            )
            self.assertTrue(res)
            self.assertTrue(deep_file.exists())


if __name__ == "__main__":
    unittest.main()
