"""Unit tests for Universal Multi-Provider Cloud AI Engine and API endpoints."""

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from edith.providers.cloud_provider import UniversalCloudProvider, PROVIDER_METADATA, LLM_ENV_FILE


class TestCloudProviderEngine(unittest.TestCase):
    """Test UniversalCloudProvider configuration, saving, and targeting."""

    def setUp(self):
        self.provider = UniversalCloudProvider()

    def tearDown(self):
        if LLM_ENV_FILE.exists():
            try:
                LLM_ENV_FILE.unlink()
            except Exception:
                pass

    def test_provider_metadata_definitions(self):
        """Verify all supported providers exist with proper endpoints."""
        for pid in ("gemini", "groq", "openai", "openrouter", "gateway"):
            self.assertIn(pid, PROVIDER_METADATA)
            self.assertTrue(len(PROVIDER_METADATA[pid]["url"]) > 0)
            self.assertTrue(len(PROVIDER_METADATA[pid]["default_model"]) > 0)

    def test_get_public_providers_sanitizes_keys(self):
        """Ensure API keys are not leaked in public provider listing."""
        self.provider.keys["gemini"] = "AIzaSySecretKey"
        public_info = self.provider.get_public_providers()
        self.assertIn("providers", public_info)
        self.assertIn("active_provider", public_info)
        self.assertTrue(public_info["keys"]["gemini"])
        # Ensure full raw key is never directly exposed in public description
        for p in public_info["providers"]:
            self.assertNotIn("AIzaSySecretKey", json.dumps(p))

    def test_resolve_target_without_keys_returns_none(self):
        """Ensure auto mode returns None when no keys configured."""
        self.provider.active_provider = "auto"
        self.provider.keys.clear()
        target = self.provider.resolve_target()
        self.assertIsNone(target)

    def test_resolve_target_with_gemini_key(self):
        """Ensure resolve_target selects gemini when key provided."""
        self.provider.active_provider = "auto"
        self.provider.keys["gemini"] = "fake_test_key"
        target = self.provider.resolve_target()
        self.assertIsNotNone(target)
        pid, url, key, model = target
        self.assertEqual(pid, "gemini")
        self.assertEqual(key, "fake_test_key")
        self.assertIn("generativelanguage.googleapis.com", url)

    def test_save_provider_config(self):
        """Verify saving provider configuration updates local cache."""
        res = self.provider.save_provider_config(
            provider="groq",
            api_key="gsk_test123",
            model="llama-3.3-70b-versatile"
        )
        self.assertEqual(self.provider.active_provider, "groq")
        self.assertEqual(self.provider.keys["groq"], "gsk_test123")
        self.assertEqual(self.provider.models["groq"], "llama-3.3-70b-versatile")
        self.assertEqual(res["active_provider"], "groq")


if __name__ == "__main__":
    unittest.main()
