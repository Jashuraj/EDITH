"""Unit tests for Model Context Protocol (MCP) Client."""

from __future__ import annotations

import json
import unittest
from unittest.mock import MagicMock, patch

from edith.tools.registry import ToolRegistry
from edith.tools.mcp_client import MCPClient


class TestMCPClient(unittest.TestCase):
    """Test suite for MCP tool client and mounting logic."""

    def setUp(self):
        self.client = MCPClient()

    @patch("urllib.request.urlopen")
    def test_connect_http_server(self, mock_urlopen):
        tools_payload = {
            "result": {
                "tools": [
                    {
                        "name": "read_weather",
                        "description": "Fetch live weather report",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"city": {"type": "string"}},
                            "required": ["city"],
                        },
                    }
                ]
            }
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(tools_payload).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        res = self.client.connect_http_server("weather_server", "http://127.0.0.1:9090")
        self.assertTrue(res["success"])
        self.assertEqual(res["tools_count"], 1)
        self.assertIn("read_weather", res["tools"])

        status = self.client.get_status()
        self.assertIn("weather_server", status["servers"])
        self.assertEqual(status["tools_count"], 1)

    @patch("urllib.request.urlopen")
    def test_call_mcp_tool(self, mock_urlopen):
        # Register server first
        tools_payload = {
            "result": {
                "tools": [{"name": "calculator", "description": "Calc", "inputSchema": {}}]
            }
        }
        mock_resp1 = MagicMock()
        mock_resp1.read.return_value = json.dumps(tools_payload).encode("utf-8")
        mock_resp1.__enter__.return_value = mock_resp1
        mock_urlopen.return_value = mock_resp1
        self.client.connect_http_server("calc_server", "http://127.0.0.1:9091")

        # Now mock call
        call_payload = {"result": {"answer": 42}}
        mock_resp2 = MagicMock()
        mock_resp2.read.return_value = json.dumps(call_payload).encode("utf-8")
        mock_resp2.__enter__.return_value = mock_resp2
        mock_urlopen.return_value = mock_resp2

        result = self.client.call_mcp_tool("calc_server", "calculator", {"expr": "6*7"})
        self.assertEqual(result, {"answer": 42})

    @patch("urllib.request.urlopen")
    def test_register_mcp_tools_into_registry(self, mock_urlopen):
        tools_payload = {
            "result": {
                "tools": [
                    {
                        "name": "status_check",
                        "description": "Check device health",
                        "inputSchema": {},
                    }
                ]
            }
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(tools_payload).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        self.client.connect_http_server("diagnostics", "http://127.0.0.1:9092")
        registry = ToolRegistry()
        count = self.client.register_mcp_tools(registry)
        self.assertEqual(count, 1)

        tool = registry.get("mcp_diagnostics_status_check")
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "mcp_diagnostics_status_check")


if __name__ == "__main__":
    unittest.main()
