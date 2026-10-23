"""Unit tests for Full-Duplex Real-Time Voice Streaming & Barge-in."""

from __future__ import annotations

import struct
import unittest
from unittest.mock import MagicMock

from edith.voice.voice_streamer import RealTimeVoiceStreamer


class TestVoiceStreamer(unittest.TestCase):
    """Test suite for PCM RMS VAD analysis and barge-in detection."""

    def setUp(self):
        self.streamer = RealTimeVoiceStreamer(vad_threshold=0.05)

    def test_silence_chunk(self):
        # 16-bit PCM silence (zeros)
        silence = b"\x00\x00" * 320
        res = self.streamer.process_incoming_chunk(silence)
        self.assertFalse(res["has_speech"])
        self.assertFalse(res["barge_in"])
        self.assertAlmostEqual(res["rms"], 0.0)

    def test_speech_chunk(self):
        # High amplitude square wave
        high_wave = struct.pack("<100h", *([15000, -15000] * 50))
        res = self.streamer.process_incoming_chunk(high_wave)
        self.assertTrue(res["has_speech"])
        self.assertGreater(res["rms"], 0.1)

    def test_barge_in_triggered_when_vocalizing(self):
        callback = MagicMock()
        self.streamer.set_barge_in_callback(callback)
        self.streamer.set_vocalizing(True)

        loud_wave = struct.pack("<100h", *([20000, -20000] * 50))
        res = self.streamer.process_incoming_chunk(loud_wave)

        self.assertTrue(res["has_speech"])
        self.assertTrue(res["barge_in"])
        callback.assert_called_once()

        self.streamer.set_vocalizing(False)
        self.assertFalse(self.streamer.is_vocalizing())


if __name__ == "__main__":
    unittest.main()
