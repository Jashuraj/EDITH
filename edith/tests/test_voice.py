"""Unit tests for Voice and Speech Synthesizer."""

import unittest
from edith.voice.listener import SpeechListener
from edith.voice.speaker import SpeechSynthesizer


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
        # Verify barge-in stop does not raise errors
        speaker.stop()


if __name__ == "__main__":
    unittest.main()
