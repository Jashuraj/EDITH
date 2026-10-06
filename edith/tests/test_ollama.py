"""Unit and integration tests for Ollama Local Provider."""

import asyncio
import unittest
from edith.providers.ollama_provider import OllamaProvider


class TestOllamaProvider(unittest.IsolatedAsyncioTestCase):
    async def test_ollama_health_and_models(self):
        provider = OllamaProvider()
        healthy = await provider.is_healthy()
        self.assertTrue(healthy, "Host Ollama should be healthy on localhost:11434")

        models = await provider.list_models()
        self.assertGreater(len(models), 0)
        # Check if hermes3:3b or other installed model is present
        has_hermes = any("hermes3" in m for m in models)
        self.assertTrue(has_hermes, f"Hermes 3B should be installed. Found: {models}")


if __name__ == "__main__":
    unittest.main()
