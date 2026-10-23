"""Unit tests for EDITH Cron Patrol & Proactive Autonomy Engine."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from edith.tasks.cron_patrol import CronPatrolEngine


class TestCronPatrol(unittest.TestCase):
    """Test suite for background patrol jobs and proactive monitoring."""

    def setUp(self):
        self.engine = CronPatrolEngine()

    def test_default_jobs_registered(self):
        status = self.engine.get_status()
        self.assertGreaterEqual(status["jobs_count"], 2)
        job_ids = [j["job_id"] for j in status["jobs"]]
        self.assertIn("vitals_patrol", job_ids)
        self.assertIn("memory_cleanup", job_ids)

    def test_custom_job_registration_and_run(self):
        mock_handler = MagicMock(return_value="custom_ok")
        self.engine.register_job("test_job", "Test Job", interval_seconds=10.0, handler=mock_handler)

        res = self.engine.run_once("test_job")
        self.assertTrue(res["success"])
        self.assertEqual(res["result"], "custom_ok")
        mock_handler.assert_called_once()

        removed = self.engine.unregister_job("test_job")
        self.assertTrue(removed)

    def test_run_non_existent_job(self):
        res = self.engine.run_once("unknown_job_xyz")
        self.assertFalse(res["success"])
        self.assertIn("not found", res["error"])

    def test_engine_lifecycle(self):
        self.engine.start()
        status = self.engine.get_status()
        self.assertTrue(status["running"])
        self.engine.stop()
        status_after = self.engine.get_status()
        self.assertFalse(status_after["running"])


if __name__ == "__main__":
    unittest.main()
