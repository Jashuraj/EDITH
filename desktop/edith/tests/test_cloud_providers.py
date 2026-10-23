"""Unit tests for Universal Multi-Provider Cloud AI Engine and API endpoints."""

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from edith.providers.cloud_provider import UniversalCloudProvider, PROVIDER_METADATA, LLM_ENV_FILE


class TestCloudProviderEngine(unittest.TestCase):
    """Test UniversalCloudProvider configuration, saving, and targeting."""

    def setUp(self):
        self._orig_env = None
        if LLM_ENV_FILE.exists():
            try:
                self._orig_env = LLM_ENV_FILE.read_text(encoding="utf-8")
            except Exception:
                pass
        self.provider = UniversalCloudProvider()

    def tearDown(self):
        if self._orig_env is not None:
            try:
                LLM_ENV_FILE.write_text(self._orig_env, encoding="utf-8")
            except Exception:
                pass
        elif LLM_ENV_FILE.exists():
            try:
                LLM_ENV_FILE.unlink()
            except Exception:
                pass

    def test_provider_metadata_definitions(self):
        """Verify all supported providers exist with proper endpoints."""
        for pid in ("codecraft", "gemini", "groq", "openai", "openrouter", "gateway"):
            self.assertIn(pid, PROVIDER_METADATA)
            self.assertTrue(len(PROVIDER_METADATA[pid]["url"]) > 0)
            self.assertTrue(len(PROVIDER_METADATA[pid]["default_model"]) > 0)
        self.assertEqual(PROVIDER_METADATA["codecraft"]["default_model"], "claude-opus-5.5")

    def test_get_public_providers_sanitizes_keys(self):
        """Ensure API keys are not leaked in public provider listing."""
        self.provider.keys["gemini"] = "AIzaSySecretKey"
        self.provider.keys["codecraft"] = "cc_SecretKeyTest123"
        public_info = self.provider.get_public_providers()
        self.assertIn("providers", public_info)
        self.assertIn("active_provider", public_info)
        self.assertTrue(public_info["keys"]["gemini"])
        self.assertTrue(public_info["keys"]["codecraft"])
        # Ensure full raw key is never directly exposed in public description
        for p in public_info["providers"]:
            self.assertNotIn("AIzaSySecretKey", json.dumps(p))
            self.assertNotIn("cc_SecretKeyTest123", json.dumps(p))

    def test_resolve_target_without_keys_returns_none(self):
        """Ensure auto mode returns None when no keys configured."""
        self.provider.active_provider = "auto"
        self.provider.keys.clear()
        target = self.provider.resolve_target()
        self.assertIsNone(target)

    def test_resolve_target_with_codecraft_key(self):
        """Ensure resolve_target prioritizes codecraft with claude-opus-5.5."""
        self.provider.active_provider = "auto"
        self.provider.keys.clear()
        self.provider.keys["codecraft"] = "cc_test_key"
        target = self.provider.resolve_target()
        self.assertIsNotNone(target)
        pid, url, key, model = target
        self.assertEqual(pid, "codecraft")
        self.assertEqual(key, "cc_test_key")
        self.assertEqual(model, "claude-opus-5.5")
        self.assertIn("codecraftapi.com", url)

    def test_resolve_target_with_gemini_key(self):
        """Ensure resolve_target selects gemini when only gemini key provided."""
        self.provider.active_provider = "auto"
        self.provider.keys.clear()
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
            provider="codecraft",
            api_key="cc_test_save_key",
            model="claude-opus-5.5"
        )
        self.assertEqual(self.provider.active_provider, "codecraft")
        self.assertEqual(self.provider.keys["codecraft"], "cc_test_save_key")
        self.assertEqual(self.provider.models["codecraft"], "claude-opus-5.5")
        self.assertEqual(res["active_provider"], "codecraft")


if __name__ == "__main__":
    unittest.main()
