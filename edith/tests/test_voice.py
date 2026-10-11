"""Unit tests for Voice, Speech Synthesizer, and Character Profiles."""

import unittest
from edith.voice.listener import SpeechListener
from edith.voice.speaker import SpeechSynthesizer, VOICE_CHARACTERS


class TestVoiceSystem(unittest.TestCase):
    def test_listener_callback(self):
        listener = SpeechListener()
        received = []

        def callback(phrase: str):
            received.append(phrase)

        listener.start_listening(callback)
        listener.inject_simulated_phrase("Hey EDITH, check battery")
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0], "Hey EDITH, check battery")

    def test_speaker_barge_in_stop(self):
        speaker = SpeechSynthesizer()
        speaker.stop()

    def test_voice_character_profiles(self):
        speaker = SpeechSynthesizer()
        chars = speaker.list_characters()
        self.assertGreaterEqual(len(chars), 6)
        ids = [c["id"] for c in chars]
        self.assertIn("edith", ids)
        self.assertIn("jarvis", ids)
        self.assertIn("friday", ids)
        self.assertIn("karen", ids)
        self.assertIn("peter", ids)
        self.assertIn("ultron", ids)

    def test_switch_voice_characters(self):
        speaker = SpeechSynthesizer()
        karen_info = speaker.set_character("karen")
        self.assertEqual(speaker.active_character, "karen")
        self.assertEqual(karen_info["name"], "KAREN")

        peter_info = speaker.set_character("peter")
        self.assertEqual(speaker.active_character, "peter")
        self.assertIn("Spider-Man", peter_info["name"])

        edith_info = speaker.set_character("edith")
        self.assertEqual(speaker.active_character, "edith")
        self.assertEqual(edith_info["name"], "EDITH")

    def test_synthesize_wav_bytes(self):
        speaker = SpeechSynthesizer()
        wav = speaker.synthesize_wav("EDITH test", character="edith")
        self.assertIsInstance(wav, bytes)
        self.assertGreater(len(wav), 0)
        self.assertTrue(wav.startswith(b"RIFF"))

    def test_synthesize_wav_empty(self):
        speaker = SpeechSynthesizer()
        self.assertEqual(speaker.synthesize_wav(""), b"")

    def test_synthesize_audio(self):
        speaker = SpeechSynthesizer()
        audio, mime = speaker.synthesize_audio("EDITH systems nominal", character="edith")
        self.assertIsInstance(audio, bytes)
        self.assertGreater(len(audio), 0)
        self.assertIn(mime, ["audio/mpeg", "audio/wav"])

    def test_synthesize_audio_empty(self):
        speaker = SpeechSynthesizer()
        audio, mime = speaker.synthesize_audio("", character="edith")
        self.assertEqual(audio, b"")
        self.assertEqual(mime, "audio/wav")


if __name__ == "__main__":
    unittest.main()
