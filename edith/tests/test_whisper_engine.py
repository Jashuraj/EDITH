"""Unit tests for Offline Whisper Speech Engine."""

import unittest
from edith.voice.whisper_engine import OfflineWhisperEngine, WHISPER_ENGINE


class TestWhisperEngine(unittest.TestCase):

    def setUp(self):
        self.engine = OfflineWhisperEngine(model_size="tiny.en")

    def test_singleton_exists(self):
        self.assertIsNotNone(WHISPER_ENGINE)
        self.assertTrue(hasattr(WHISPER_ENGINE, "transcribe_audio_bytes"))

    def test_engine_availability(self):
        avail = self.engine.is_available()
        self.assertIsInstance(avail, bool)

    def test_engine_status_dict(self):
        status = self.engine.get_status()
        self.assertIn("available", status)
        self.assertIn("model_loaded", status)
        self.assertIn("model_size", status)
        self.assertEqual(status["model_size"], "tiny.en")

    def test_empty_audio_bytes(self):
        text = self.engine.transcribe_audio_bytes(b"")
        self.assertEqual(text, "")
        short_bytes = b"RIFF" + b"\x00" * 10
        self.assertEqual(self.engine.transcribe_audio_bytes(short_bytes), "")

    def test_ensure_wav_format_header(self):
        fake_wav = b"RIFF\x24\x00\x00\x00WAVEfmt " + b"\x00" * 32
        out = self.engine._ensure_wav_format(fake_wav)
        self.assertEqual(out, fake_wav)


if __name__ == "__main__":
    unittest.main()
