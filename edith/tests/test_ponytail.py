"""Unit tests for Ponytail Minimalist Lazy Senior Dev Engine."""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from edith.providers.base import ModelResponse
from edith.tools.ponytail import PonytailEngine
from edith.tools.reflex import REFLEX
from edith.tools.registry import REGISTRY


class TestPonytail(unittest.TestCase):
    """Test suite for /pony commands, levels, and minimalist execution."""

    def setUp(self):
        self.engine = PonytailEngine()

    def test_status_command(self):
        res = self.engine.handle_command("")
        self.assertIn("Ponytail Mode", res)
        self.assertIn("The best code is the code never written", res)

    def test_toggle_commands(self):
        res_on = self.engine.handle_command("on")
        self.assertTrue(self.engine.active)
        self.assertIn("ACTIVE", res_on)

        res_off = self.engine.handle_command("off")
        self.assertFalse(self.engine.active)
        self.assertIn("DEACTIVATED", res_off)

    def test_intensity_levels(self):
        self.engine.handle_command("lite")
        self.assertEqual(self.engine.level, "lite")

        self.engine.handle_command("ultra")
        self.assertEqual(self.engine.level, "ultra")

        self.engine.handle_command("full")
        self.assertEqual(self.engine.level, "full")

    @patch("edith.providers.router.ROUTER.execute")
    def test_task_execution(self, mock_router):
        mock_router.return_value = ModelResponse(
            content="Use built-in dict.\nSkipped: custom hash table.\nRisk: None.",
            model="mock",
            provider="mock",
        )
        res = self.engine.handle_command("build a fast lookup")
        self.assertIn("Use built-in dict", res)

    def test_reflex_slash_pony_matching(self):
        match1 = REFLEX.evaluate("/pony")
        self.assertIsNotNone(match1)
        self.assertEqual(match1.command_name, "ponytail_mode")

        match2 = REFLEX.evaluate("/pony ultra")
        self.assertIsNotNone(match2)
        self.assertEqual(match2.command_name, "ponytail_mode")
        self.assertEqual(match2.params.get("args"), "ultra")

        match3 = REFLEX.evaluate("pony review this code")
        self.assertIsNotNone(match3)
        self.assertEqual(match3.command_name, "ponytail_mode")

    def test_registry_builtin_tool(self):
        tool = REGISTRY.get("ponytail_exec")
        self.assertIsNotNone(tool)
        res = REGISTRY.execute_tool("ponytail_exec", {"command": "lite"})
        self.assertIn("LITE", str(res))


if __name__ == "__main__":
    unittest.main()
