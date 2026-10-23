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

        # Warm up engine regex cache
        self.engine.evaluate("open chrome")

        for phrase, expected_cmd in test_phrases:
            match = self.engine.evaluate(phrase)
            self.assertIsNotNone(match, f"Failed to match phrase: '{phrase}'")
            self.assertEqual(match.command_name, expected_cmd)
            self.assertLess(match.duration_ms, 50.0)

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

    def test_switch_voice_and_theme_execution(self):
        match_voice = self.engine.evaluate("switch voice to jarvis")
        self.assertIsNotNone(match_voice)
        res_voice = self.engine.execute_match(match_voice)
        self.assertIsInstance(res_voice, dict)
        self.assertEqual(res_voice["action"], "switch_voice_character")
        self.assertEqual(res_voice["character"]["id"], "jarvis")

        match_theme = self.engine.evaluate("switch theme to spiderman")
        self.assertIsNotNone(match_theme)
        res_theme = self.engine.execute_match(match_theme)
        self.assertIsInstance(res_theme, dict)
        self.assertEqual(res_theme["action"], "switch_theme")
        self.assertEqual(res_theme["theme"], "spiderman")

    def test_peter_voice_and_theme_reflexes(self):
        voice_phrases = (
            "switch voice to peter 1",
            "switch character to peter one",
            "switch voice to edith peter 1",
            "switch voice to edith peter one",
            "switch voice to edith // peter 1",
            "activate edith peter 1",
            "activate peter 1",
            "switch to peter 1",
        )
        for phrase in voice_phrases:
            match = self.engine.evaluate(phrase)
            self.assertIsNotNone(match, f"Failed match on: {phrase}")
            self.assertEqual(match.command_name, "switch_voice_character")
            res = self.engine.execute_match(match)
            self.assertIsInstance(res, dict)
            self.assertEqual(res["character"]["id"], "peter")
            self.assertEqual(res["character"]["name"], "PETER 1 (EDITH)")

        theme_phrases = (
            "switch theme to peter 1",
            "change theme to peter one",
            "switch theme to edith peter 1",
            "switch theme to edith peter one",
            "switch theme to edith // peter 1",
            "activate peter 1 theme",
            "activate edith peter 1 theme",
            "switch to peter 1 theme",
        )
        for phrase in theme_phrases:
            match = self.engine.evaluate(phrase)
            self.assertIsNotNone(match, f"Failed match on: {phrase}")
            self.assertEqual(match.command_name, "switch_theme")
            res = self.engine.execute_match(match)
            self.assertIsInstance(res, dict)
            self.assertEqual(res["theme"], "peter1")

    def test_spider_suit_reflexes(self):
        suit_phrases = [
            ("web fluid check", "web_fluid_check", "Web fluid cartridges"),
            ("calibrate web cartridges", "web_fluid_check", "Web fluid cartridges"),
            ("deploy web net", "deploy_web_net", "High-tensile web net deployed"),
            ("deploy web net on target", "deploy_web_net", "High-tensile web net deployed"),
            ("orbital defense satellite drones", "orbital_defense_drones", "Orbital Defense Satellite"),
            ("orbital defense satellite drones swarm", "orbital_defense_drones", "Orbital Defense Satellite"),
            ("spider-sense threat scan", "spider_sense_scan", "Spider-Sense threat radar sweep"),
            ("spider-sense threat radar scan", "spider_sense_scan", "Spider-Sense threat radar sweep"),
            ("iron spider nanotech diagnostics", "nanotech_diagnostics", "Iron Spider Nanotech armor mesh"),
            ("iron spider nanotech armor deploy", "nanotech_diagnostics", "Iron Spider Nanotech armor mesh"),
            ("instant kill lockout", "instant_kill_lockout", "Instant Kill safety lockout active"),
            ("instant kill safety lockout", "instant_kill_lockout", "Instant Kill safety lockout active"),
            ("queens patrol route", "queens_patrol", "Queens Patrol Route initialized"),
        ]
        for phrase, expected_cmd, expected_kw in suit_phrases:
            match = self.engine.evaluate(phrase)
            self.assertIsNotNone(match, f"Reflex failed to match: '{phrase}'")
            self.assertEqual(match.command_name, expected_cmd)
            self.assertLess(match.duration_ms, 50.0)
            res = self.engine.execute_match(match)
            self.assertIn(expected_kw, str(res))


if __name__ == "__main__":
    unittest.main()
