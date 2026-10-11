"""Unit tests for Remote Per-App Audio Mixer and Media Controller."""

import unittest
from unittest.mock import MagicMock, patch
from edith.tools.audio_mixer import AudioMixer, AUDIO_MIXER


class TestAudioMixer(unittest.TestCase):

    def setUp(self):
        self.mixer = AudioMixer()

    def test_singleton_exists(self):
        self.assertIsNotNone(AUDIO_MIXER)
        self.assertTrue(hasattr(AUDIO_MIXER, "get_master_volume"))
        self.assertTrue(hasattr(AUDIO_MIXER, "set_master_volume"))
        self.assertTrue(hasattr(AUDIO_MIXER, "media_control"))

    def test_get_master_volume(self):
        res = self.mixer.get_master_volume()
        self.assertIn("success", res)
        if res["success"]:
            self.assertIn("volume", res)
            self.assertIn("muted", res)
            self.assertGreaterEqual(res["volume"], 0)
            self.assertLessEqual(res["volume"], 100)

    def test_get_app_sessions(self):
        sessions = self.mixer.get_app_sessions()
        self.assertIsInstance(sessions, list)
        for s in sessions:
            self.assertIn("process_name", s)
            self.assertIn("volume", s)
            self.assertIn("muted", s)

    def test_media_control_valid_actions(self):
        with patch("ctypes.windll.user32.keybd_event") as mock_keybd:
            res_play = self.mixer.media_control("play_pause")
            self.assertTrue(res_play["success"])
            self.assertEqual(res_play["action"], "play_pause")
            self.assertTrue(mock_keybd.called)

            res_next = self.mixer.media_control("next")
            self.assertTrue(res_next["success"])

            res_prev = self.mixer.media_control("prev")
            self.assertTrue(res_prev["success"])

    def test_media_control_invalid_action(self):
        res = self.mixer.media_control("unknown_action_xyz")
        self.assertFalse(res["success"])
        self.assertIn("error", res)


if __name__ == "__main__":
    unittest.main()
