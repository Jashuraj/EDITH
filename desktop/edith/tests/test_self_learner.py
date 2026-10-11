"""Unit tests for Autonomous Self-Learner Engine."""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from edith.providers.base import ModelResponse
from edith.tasks.self_learner import SelfLearner


class TestSelfLearner(unittest.TestCase):
    def setUp(self):
        self.learner = SelfLearner()

    def test_clean_command_markdown_block(self):
        raw = "```powershell\nGet-Service -Name W32Time\n```"
        cleaned = self.learner._clean_command(raw)
        self.assertEqual(cleaned, "Get-Service -Name W32Time")

    def test_clean_command_plain(self):
        raw = "Get-Process -Name notepad"
        cleaned = self.learner._clean_command(raw)
        self.assertEqual(cleaned, "Get-Process -Name notepad")

    def test_clean_command_multiline(self):
        raw = "```\n$p = Get-Process\n$p.Count\n```"
        cleaned = self.learner._clean_command(raw)
        self.assertEqual(cleaned, "$p = Get-Process; $p.Count")

    def test_solve_task_empty_goal(self):
        result = asyncio.run(self.learner.solve_task(""))
        self.assertFalse(result["success"])
        self.assertIn("No goal provided", result["error"])

    def test_solve_task_uses_existing_learned_skill(self):
        with patch.object(self.learner.memory, "find_learned_skill") as mock_find, \
             patch.object(self.learner.win, "run_powershell") as mock_ps:
            mock_find.return_value = {
                "goal": "check uptime",
                "command": "(Get-Date) - (gcim Win32_OperatingSystem).LastBootUpTime",
                "description": "uptime check",
            }
            mock_ps.return_value = {
                "success": True,
                "output": "TotalDays: 2",
            }

            result = asyncio.run(self.learner.solve_task("check uptime"))
            self.assertTrue(result["success"])
            self.assertTrue(result["learned"])
            mock_find.assert_called_once_with("check uptime")
            mock_ps.assert_called_once_with("(Get-Date) - (gcim Win32_OperatingSystem).LastBootUpTime")

    def test_solve_task_learns_new_skill_on_success(self):
        with patch.object(self.learner.memory, "find_learned_skill", return_value=None), \
             patch.object(self.learner.memory, "remember_skill") as mock_remember, \
             patch("edith.tasks.self_learner.ROUTER.execute", new_callable=AsyncMock) as mock_router, \
             patch.object(self.learner.win, "run_powershell") as mock_ps:

            mock_router.return_value = ModelResponse(
                content="Get-Volume",
                model="hermes-3:3b",
                provider="ollama",
            )
            mock_ps.return_value = {
                "success": True,
                "output": "Drive C: OK",
            }

            result = asyncio.run(self.learner.solve_task("list all drive volumes", max_attempts=2))
            self.assertTrue(result["success"])
            self.assertFalse(result["learned"])
            self.assertEqual(result["attempts"], 1)
            mock_remember.assert_called_once()
            args = mock_remember.call_args[1]
            self.assertEqual(args["goal"], "list all drive volumes")
            self.assertEqual(args["command"], "Get-Volume")

    def test_solve_task_self_corrects_and_succeeds(self):
        with patch.object(self.learner.memory, "find_learned_skill", return_value=None), \
             patch.object(self.learner.memory, "remember_skill") as mock_remember, \
             patch("edith.tasks.self_learner.ROUTER.execute", new_callable=AsyncMock) as mock_router, \
             patch.object(self.learner.win, "run_powershell") as mock_ps:

            # First router call gives faulty command, second gives fixed command
            mock_router.side_effect = [
                ModelResponse(content="Bad-Cmdlet", model="hermes", provider="ollama"),
                ModelResponse(content="Get-Date", model="hermes", provider="ollama"),
            ]
            # First PS run fails, second succeeds
            mock_ps.side_effect = [
                {"success": False, "exit_code": 1, "stderr": "Bad-Cmdlet not found"},
                {"success": True, "exit_code": 0, "output": "Tuesday, October 6, 2026"},
            ]

            result = asyncio.run(self.learner.solve_task("show today date", max_attempts=3))
            self.assertTrue(result["success"])
            self.assertEqual(result["attempts"], 2)
            self.assertEqual(result["command"], "Get-Date")
            mock_remember.assert_called_once()

    def test_solve_task_max_attempts_exceeded(self):
        with patch.object(self.learner.memory, "find_learned_skill", return_value=None), \
             patch("edith.tasks.self_learner.ROUTER.execute", new_callable=AsyncMock) as mock_router, \
             patch.object(self.learner.win, "run_powershell") as mock_ps:

            mock_router.return_value = ModelResponse(content="Invalid-Cmd", model="test", provider="test")
            mock_ps.return_value = {"success": False, "stderr": "Error"}

            result = asyncio.run(self.learner.solve_task("impossible goal", max_attempts=2))
            self.assertFalse(result["success"])
            self.assertEqual(result["attempts"], 2)
            self.assertIn("Could not accomplish", result["message"])


if __name__ == "__main__":
    unittest.main()
