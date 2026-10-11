"""Unit tests for Windows Native Automation Toolpack."""

import tempfile
import unittest
from pathlib import Path
from edith.tools.windows import WindowsTools


class TestWindowsTools(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.win = WindowsTools(screenshot_dir=Path(self.tmpdir.name))

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_get_system_stats(self):
        stats = self.win.get_system_stats()
        self.assertIn("cpu", stats)
        self.assertIn("total_ram_gb", stats)
        self.assertIn("free_ram_gb", stats)

    def test_take_screenshot(self):
        res = self.win.take_screenshot()
        self.assertTrue(res["success"])
        self.assertTrue(Path(res["path"]).exists())

    def test_volume_controls(self):
        res = self.win.set_volume("volume_up", delta=2)
        self.assertTrue(res["success"])

    def test_media_action(self):
        res = self.win.media_action("play_pause")
        self.assertTrue(res["success"])
        res_next = self.win.media_action("next")
        self.assertTrue(res_next["success"])

    def test_mouse_action(self):
        res = self.win.mouse_action("click")
        self.assertTrue(res["success"])
        res_scroll = self.win.mouse_action("scroll_down", amount=2)
        self.assertTrue(res_scroll["success"])

    def test_power_action(self):
        res = self.win.power_action("cancel_shutdown")
        self.assertTrue(res["success"])

    def test_search_youtube_url(self):
        res = self.win.search_youtube("brand new day trailer")
        self.assertTrue(res["success"])
        self.assertIn("youtube.com", res.get("url", ""))

    def test_run_powershell_valid(self):
        res = self.win.run_powershell("Write-Output 'EDITH_ONLINE'")
        self.assertTrue(res["success"])
        self.assertIn("EDITH_ONLINE", res.get("output", ""))

    def test_run_powershell_dangerous_blocked(self):
        res = self.win.run_powershell("rmdir /s /q C:\\")
        self.assertFalse(res["success"])
        self.assertIn("Security Gate", res.get("error", ""))

    def test_run_powershell_empty(self):
        res = self.win.run_powershell("")
        self.assertFalse(res["success"])


if __name__ == "__main__":
    unittest.main()

