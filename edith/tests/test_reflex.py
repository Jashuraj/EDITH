"""Unit tests for Level 0 Reflex Engine."""

import unittest
from edith.core.security import SECURITY
from edith.tools.reflex import ReflexEngine


class TestReflexEngine(unittest.TestCase):
    def setUp(self):
        self.engine = ReflexEngine()
        SECURITY.reset_emergency_stop()

    def test_instant_matches_under_15ms(self):
        test_phrases = [
            ("open chrome", "open_app"),
            ("Hey EDITH, open Chrome", "open_app"),
            ("close chrome", "close_app"),
            ("open notepad", "open_app"),
            ("close notepad", "close_app"),
            ("open youtube", "open_app"),
            ("open discord", "open_app"),
            ("close discord", "close_app"),
            ("mute audio", "mute"),
            ("unmute", "unmute"),
            ("volume up", "volume_up"),
            ("volume down", "volume_down"),
            ("take a screenshot", "screenshot"),
            ("show battery level", "battery_status"),
            ("lock workstation", "lock_workstation"),
            ("pause the music", "media_action"),
            ("next song", "media_action"),
            ("click", "mouse_action"),
            ("double click", "mouse_action"),
            ("scroll down", "mouse_action"),
            ("cancel shutdown", "power_action"),
            ("open youtube and play brand new day trailer", "search_youtube"),
            ("play songs on browser", "search_youtube"),
            ("play music on browser", "search_youtube"),
            ("remember that my favorite project is EDITH", "remember_fact"),
            ("show memories", "show_memories"),
            ("when I say blast off, do open terminal", "teach_command"),
            ("stop EDITH", "emergency_stop"),
            ("enable privacy mode", "enable_privacy"),
            ("what is your status", "show_status"),
            ("switch voice to jarvis", "switch_voice_character"),
            ("change character to karen", "switch_voice_character"),
            ("activate spiderman personality", "switch_voice_character"),
            ("switch theme to spiderman", "switch_theme"),
            ("change theme to tactical", "switch_theme"),
        ]

        for phrase, expected_cmd in test_phrases:
            match = self.engine.evaluate(phrase)
            self.assertIsNotNone(match, f"Failed to match phrase: '{phrase}'")
            self.assertEqual(match.command_name, expected_cmd)
            self.assertLess(match.duration_ms, 15.0)

    def test_non_reflex_phrase_returns_none(self):
        complex_phrase = "Write a python script to parse logs and send a summary email."
        match = self.engine.evaluate(complex_phrase)
        self.assertIsNone(match)

    def test_emergency_stop_execution(self):
        match = self.engine.evaluate("emergency stop")
        self.assertIsNotNone(match)
        res = self.engine.execute_match(match)
        self.assertEqual(res, "Emergency stop engaged.")
        self.assertTrue(SECURITY.is_emergency_stopped)

    def test_memory_reflex_execution(self):
        match = self.engine.evaluate("remember that my favorite color is crimson")
        self.assertIsNotNone(match)
        res = self.engine.execute_match(match)
        self.assertIn("favorite color is crimson", str(res))

        match2 = self.engine.evaluate("show memories")
        self.assertIsNotNone(match2)
        res2 = self.engine.execute_match(match2)
        self.assertIn("favorite color is crimson", str(res2))


if __name__ == "__main__":
    unittest.main()
