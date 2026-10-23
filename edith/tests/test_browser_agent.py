"""Unit tests for Headless Browser and Web Intelligence Agent."""

from __future__ import annotations

import io
import unittest
from unittest.mock import MagicMock, patch

from edith.tools.browser_agent import HeadlessBrowserAgent


class TestBrowserAgent(unittest.TestCase):
    """Test suite for autonomous page fetching and parsing."""

    def setUp(self):
        self.agent = HeadlessBrowserAgent()

    @patch("urllib.request.urlopen")
    def test_fetch_page_parsing(self, mock_urlopen):
        html_content = """
        <!DOCTYPE html>
        <html>
        <head><title>Stark Industries AI</title></head>
        <body>
            <h1>Project EDITH</h1>
            <p>Even Dead, I'm The Hero.</p>
            <a href="/defense">Defense Systems</a>
            <script>console.log("ignore me");</script>
        </body>
        </html>
        """
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = html_content.encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        page = self.agent.fetch_page("https://starkindustries.test")
        self.assertEqual(page.status_code, 200)
        self.assertEqual(page.title, "Stark Industries AI")
        self.assertIn("Project EDITH", page.text_content)
        self.assertIn("Even Dead, I'm The Hero", page.text_content)
        self.assertNotIn("console.log", page.text_content)
        self.assertEqual(len(page.links), 1)
        self.assertEqual(page.links[0]["url"], "https://starkindustries.test/defense")

    @patch("urllib.request.urlopen")
    def test_fetch_page_network_failure(self, mock_urlopen):
        mock_urlopen.side_effect = Exception("DNS Resolution Error")
        page = self.agent.fetch_page("https://unreachable.test")
        self.assertEqual(page.status_code, 500)
        self.assertIn("Error fetching URL", page.text_content)


if __name__ == "__main__":
    unittest.main()
