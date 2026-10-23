"""Unit tests for ChannelBridge external messaging router."""

from __future__ import annotations

import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from edith.phone.channel_bridge import ChannelBridge
from edith.providers.base import ModelResponse


class TestChannelBridge(unittest.TestCase):
    """Test suite for WhatsApp, Telegram, and Webhook dispatching."""

    def setUp(self):
        self.bridge = ChannelBridge()

    def test_empty_message(self):
        res = self.bridge.handle_incoming_message(
            channel="whatsapp",
            sender_id="+15551234567",
            sender_name="Peter",
            text="   ",
        )
        self.assertFalse(res["success"])
        self.assertIn("Empty", res["reply"])

    @patch("edith.tools.reflex.REFLEX.evaluate")
    @patch("edith.tools.reflex.REFLEX.execute_match")
    def test_reflex_fast_path(self, mock_exec, mock_eval):
        mock_eval.return_value = {"intent": "get_status"}
        mock_exec.return_value = {"message": "All systems operational"}

        res = self.bridge.handle_incoming_message(
            channel="telegram",
            sender_id="user123",
            sender_name="Peter",
            text="status",
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["source"], "reflex")
        self.assertEqual(res["reply"], "All systems operational")

    @patch("edith.tools.reflex.REFLEX.evaluate", return_value=None)
    @patch("edith.providers.router.ROUTER.execute")
    def test_model_router_path(self, mock_router_exec, mock_eval):
        mock_resp = ModelResponse(
            content="Mark LV active. Standing by.",
            model="local-model",
            provider="ollama",
        )
        mock_router_exec.return_value = mock_resp

        res = self.bridge.handle_incoming_message(
            channel="webhook",
            sender_id="web_client",
            sender_name="Operator",
            text="What is your armor state?",
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["source"], "model_router")
        self.assertIn("Mark LV active", res["reply"])

    def test_whatsapp_dispatch_unconfigured(self):
        self.bridge.whatsapp_token = ""
        self.bridge.whatsapp_phone_id = ""
        res = self.bridge.send_whatsapp_message("+15550009999", "Alert trigger")
        self.assertFalse(res["success"])
        self.assertEqual(res["status"], "simulated")

    @patch("urllib.request.urlopen")
    def test_whatsapp_dispatch_success(self, mock_urlopen):
        self.bridge.whatsapp_token = "fake-token"
        self.bridge.whatsapp_phone_id = "123456"

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"messages": [{"id": "wamid.123"}]}).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        res = self.bridge.send_whatsapp_message("+15550009999", "Live notification")
        self.assertTrue(res["success"])
        self.assertEqual(res["data"]["messages"][0]["id"], "wamid.123")

    def test_channel_status_and_history(self):
        status = self.bridge.get_status()
        self.assertIn("channels", status)
        self.assertIn("webhook", status["channels"])

        history = self.bridge.get_recent_messages()
        self.assertIsInstance(history, list)


if __name__ == "__main__":
    unittest.main()
