"""Integration tests for EDITH full stack."""

import asyncio
import unittest

from edith.core.doctor import DOCTOR
from edith.core.security import SECURITY
from edith.main import setup_builtin_tools
from edith.tools.reflex import REFLEX
from edith.tools.registry import REGISTRY


class TestEdithIntegration(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        setup_builtin_tools()
        SECURITY.reset_emergency_stop()

    async def test_doctor_diagnostics(self):
        items = await DOCTOR.run_diagnostics()
        self.assertGreaterEqual(len(items), 4)
        names = [item.name for item in items]
        self.assertIn("Hardware / RAM", names)
        self.assertIn("Local AI (Ollama)", names)

    def test_reflex_to_tool_execution(self):
        match = REFLEX.evaluate("what is your status")
        self.assertIsNotNone(match)
        res = REFLEX.execute_match(match)
        self.assertIn("EDITH Online", res)

    def test_registered_action_packs(self):
        tools = REGISTRY.get_active_tools()
        tool_names = [t.name for t in tools]
        self.assertIn("get_system_stats", tool_names)
        self.assertIn("read_file", tool_names)
        self.assertIn("write_file", tool_names)


if __name__ == "__main__":
    unittest.main()
