"""Unit tests for LlamaCppProvider local inference engine."""

from __future__ import annotations

import io
import json
import unittest
from unittest.mock import MagicMock, patch

from edith.providers.base import ProviderUnavailableError
from edith.providers.llamacpp_provider import LlamaCppProvider


class TestLlamaCppProvider(unittest.IsolatedAsyncioTestCase):
    """Test suite for Llama.cpp local GGUF provider."""

    def setUp(self):
        self.provider = LlamaCppProvider(endpoint="http://127.0.0.1:8080")

    @patch("urllib.request.urlopen")
    async def test_is_healthy_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        healthy = await self.provider.is_healthy()
        self.assertTrue(healthy)

    @patch("urllib.request.urlopen")
    async def test_is_healthy_failure(self, mock_urlopen):
        mock_urlopen.side_effect = Exception("Connection refused")

        healthy = await self.provider.is_healthy()
        self.assertFalse(healthy)

    @patch("urllib.request.urlopen")
    async def test_generate_chat_completions(self, mock_urlopen):
        resp_data = {
            "choices": [
                {
                    "message": {
                        "content": "Hello, Peter. Local inference ready."
                    }
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps(resp_data).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        res = await self.provider.generate(prompt="Status check", system_prompt="Peter Mode")
        self.assertIn("Hello, Peter", res.content)
        self.assertEqual(res.provider, "llama_cpp")

    @patch("urllib.request.urlopen")
    async def test_generate_native_completion_fallback(self, mock_urlopen):
        def side_effect(req, timeout=None):
            if "/v1/chat/completions" in req.full_url:
                raise Exception("404 Not Found")
            # Native /completion endpoint
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps({"content": "Fallback native response"}).encode("utf-8")
            mock_resp.__enter__.return_value = mock_resp
            return mock_resp

        mock_urlopen.side_effect = side_effect

        res = await self.provider.generate(prompt="Test fallback")
        self.assertEqual(res.content, "Fallback native response")

    @patch("urllib.request.urlopen")
    async def test_generate_with_tools(self, mock_urlopen):
        resp_data = {
            "choices": [
                {
                    "message": {
                        "content": "Running diagnostic",
                        "tool_calls": [
                            {
                                "function": {
                                    "name": "system_optimizer",
                                    "arguments": json.dumps({"aggressive": True}),
                                }
                            }
                        ],
                    }
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(resp_data).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        tools = [
            {
                "name": "system_optimizer",
                "description": "Optimize system memory",
                "parameters": {"type": "object", "properties": {"aggressive": {"type": "boolean"}}},
            }
        ]

        res = await self.provider.generate_with_tools(prompt="Optimize system", tools=tools)
        self.assertEqual(len(res.tool_calls), 1)
        self.assertEqual(res.tool_calls[0].name, "system_optimizer")
        self.assertEqual(res.tool_calls[0].arguments, {"aggressive": True})


if __name__ == "__main__":
    unittest.main()
