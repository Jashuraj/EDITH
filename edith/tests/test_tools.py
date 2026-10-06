"""Unit tests for Tool Registry and Action Packs."""

import unittest
from edith.core.security import RiskLevel
from edith.tools.registry import ToolRegistry


class TestToolRegistry(unittest.TestCase):
    def setUp(self):
        self.registry = ToolRegistry()

    def test_register_and_schema_export(self):
        def sample_tool(path: str) -> str:
            return f"read {path}"

        self.registry.register(
            name="test_read",
            description="Reads file contents",
            action_pack="FILES_PACK",
            risk=RiskLevel.LOW,
            fn=sample_tool,
            parameters_schema={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        )

        schemas = self.registry.get_tool_schemas()
        self.assertEqual(len(schemas), 1)
        self.assertEqual(schemas[0]["function"]["name"], "test_read")

    def test_pack_activation_filtering(self):
        self.registry.register("win_op", "Win operation", "WINDOWS_PACK", RiskLevel.LOW, lambda: True)
        self.registry.register("code_op", "Code operation", "CODING_PACK", RiskLevel.MEDIUM, lambda: True)

        # By default CODING_PACK is not in active packs
        active_names = [t.name for t in self.registry.get_active_tools()]
        self.assertIn("win_op", active_names)
        self.assertNotIn("code_op", active_names)

        # Activate CODING_PACK
        self.registry.activate_pack("CODING_PACK")
        active_names = [t.name for t in self.registry.get_active_tools()]
        self.assertIn("code_op", active_names)


class TestWindowsTools(unittest.TestCase):
    def setUp(self):
        from edith.tools.windows import WindowsTools
        self.tools = WindowsTools()

    def test_launch_website_resolution(self):
        res = self.tools.launch_app("youtube")
        self.assertTrue(res.get("success"))
        self.assertIn("Youtube", res.get("message", ""))

    def test_kill_process_result_format(self):
        res = self.tools.kill_process("nonexistent_test_proc_xyz")
        self.assertIn("process", res)
        self.assertIn("message", res)


if __name__ == "__main__":
    unittest.main()
