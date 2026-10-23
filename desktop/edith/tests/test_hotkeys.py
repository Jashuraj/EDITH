"""Unit tests for Windows Global Hotkey Daemon."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from edith.tools.hotkeys import GlobalHotkeyDaemon


class TestHotkeyDaemon(unittest.TestCase):
    """Test suite for global hotkeys and callback dispatching."""

    def setUp(self):
        self.daemon = GlobalHotkeyDaemon()

    def test_custom_binding_and_status(self):
        cb = MagicMock()
        self.daemon.bind_hotkey(99, 0x0001, 0x20, cb)
        self.assertIn(99, self.daemon._callbacks)

        status = self.daemon.get_status()
        self.assertIn("running", status)
        self.assertIn("hotkeys", status)
        self.assertEqual(len(status["hotkeys"]), 3)

    def test_callbacks_callable(self):
        # Verify internal handlers don't crash
        self.daemon._on_push_to_talk()
        self.daemon._on_system_status()


if __name__ == "__main__":
    unittest.main()
