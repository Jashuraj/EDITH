"""Unit tests for Home Assistant and Smart Home IoT Bridge."""

from __future__ import annotations

import json
import unittest
from unittest.mock import MagicMock, patch

from edith.tools.iot_bridge import HomeAssistantBridge


class TestIoTBridge(unittest.TestCase):
    """Test suite for smart home peripherals and Peter Mode ambient illumination."""

    def setUp(self):
        self.bridge = HomeAssistantBridge()

    def test_unconfigured_simulated_mode(self):
        self.bridge.token = ""
        self.assertFalse(self.bridge.is_configured())

        res = self.bridge.set_peter_mode_ambient("light.room")
        self.assertTrue(res["success"])
        self.assertTrue(res["simulated"])

        states = self.bridge.get_states()
        self.assertIsInstance(states, list)
        self.assertGreaterEqual(len(states), 1)

    @patch("urllib.request.urlopen")
    def test_configured_service_call(self, mock_urlopen):
        self.bridge.token = "fake-hass-token"
        self.assertTrue(self.bridge.is_configured())

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps([{"entity_id": "light.desk", "state": "on"}]).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        res = self.bridge.set_light_state("light.desk", state=True, brightness=200)
        self.assertTrue(res["success"])

        status = self.bridge.get_status()
        self.assertTrue(status["configured"])


if __name__ == "__main__":
    unittest.main()
