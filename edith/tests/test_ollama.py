"""Unit and integration tests for Ollama Local Provider."""

import json
import unittest
from unittest.mock import MagicMock, patch
from edith.providers.ollama_provider import OllamaProvider


class TestOllamaProvider(unittest.IsolatedAsyncioTestCase):
    async def test_ollama_health_and_models_probe(self):
        """Verify host probe returns boolean and list without crashing."""
        provider = OllamaProvider()
        healthy = await provider.is_healthy()
        self.assertIsInstance(healthy, bool)

        models = await provider.list_models()
        self.assertIsInstance(models, list)
        if healthy:
            self.assertGreater(len(models), 0)
        else:
            self.assertEqual(models, [])

    async def test_ollama_mock_reachable(self):
        """Verify model extraction when Ollama daemon responds 200 OK."""
        provider = OllamaProvider()
        mock_payload = json.dumps({"models": [{"name": "hermes3:3b"}, {"name": "tinydolphin:1.1b"}]}).encode("utf-8")
        with patch("urllib.request.urlopen") as mock_open:
            mock_cm = MagicMock()
            mock_cm.status = 200
            mock_cm.read.return_value = mock_payload
            mock_cm.__enter__.return_value = mock_cm
            mock_open.return_value = mock_cm

            healthy = await provider.is_healthy()
            self.assertTrue(healthy)

            models = await provider.list_models()
            self.assertIn("hermes3:3b", models)
            self.assertIn("tinydolphin:1.1b", models)

    async def test_ollama_unreachable_safe_fallback(self):
        """Verify graceful standby when daemon endpoint is unreachable."""
        provider = OllamaProvider(base_url="http://127.0.0.1:99999")
        healthy = await provider.is_healthy()
        self.assertFalse(healthy)

        models = await provider.list_models()
        self.assertEqual(models, [])


if __name__ == "__main__":
    unittest.main()
