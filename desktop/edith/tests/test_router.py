"""Unit tests for ModelRouter."""

import unittest
from edith.core.config import CONFIG
from edith.core.security import SECURITY
from edith.providers.base import LLMProvider, ModelResponse
from edith.providers.router import ModelRouter, TaskCategory


class MockCloudProvider(LLMProvider):
    def __init__(self):
        super().__init__(name="mock_cloud", is_local=False)

    async def generate(self, prompt, system_prompt="", model_name=None, temperature=0.2):
        return ModelResponse(content="Cloud answer", provider="mock_cloud")

    async def generate_with_tools(self, prompt, tools, system_prompt="", model_name=None):
        return ModelResponse(content="Cloud tools", provider="mock_cloud")

    async def is_healthy(self):
        return True


class TestModelRouter(unittest.TestCase):
    def setUp(self):
        self.cloud = MockCloudProvider()
        self.router = ModelRouter(cloud_provider=self.cloud)
        self.router.cloud_ai.keys.clear()
        self.router.cloud_ai.active_provider = "auto"
        CONFIG.offline_mode = False
        CONFIG.zero_credit_mode = False
        SECURITY.set_privacy_mode(False)

    def test_offline_mode_forces_local(self):
        CONFIG.offline_mode = True
        dec = self.router.route("Reason about this architecture", category=TaskCategory.REASONING)
        self.assertEqual(dec.provider, "ollama")
        self.assertIn("offline", dec.reason.lower())

    def test_zero_credit_forces_local(self):
        CONFIG.zero_credit_mode = True
        dec = self.router.route("Complex reasoning task", category=TaskCategory.REASONING)
        self.assertEqual(dec.provider, "ollama")
        self.assertIn("zero-credit", dec.reason.lower())

    def test_privacy_mode_forces_local(self):
        SECURITY.set_privacy_mode(True)
        dec = self.router.route("Private confidential question", category=TaskCategory.REASONING)
        self.assertEqual(dec.provider, "ollama")
        self.assertIn("privacy", dec.reason.lower())

    def test_tool_calling_routes_to_hermes3b(self):
        dec = self.router.route("Open Chrome and check issues", category=TaskCategory.TOOL_CALLING, has_tools=True)
        self.assertEqual(dec.provider, "ollama")
        self.assertEqual(dec.model, "hermes3:3b")


if __name__ == "__main__":
    unittest.main()
