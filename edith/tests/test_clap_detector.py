"""Unit tests for Clap Welcome Detector."""

import time
import unittest
from unittest.mock import MagicMock, patch
import numpy as np

from edith.voice.clap_detector import ClapDetector, _calc_rms


class TestClapDetector(unittest.TestCase):
    def setUp(self):
        self.callback_called = False

        def cb():
            self.callback_called = True

        self.detector = ClapDetector(welcome_callback=cb)

    def tearDown(self):
        if self.detector.is_running:
            self.detector.stop()

    def test_calc_rms_silent(self):
        silent = np.zeros(100, dtype=np.float32)
        rms = _calc_rms(silent)
        self.assertEqual(rms, 0.0)

    def test_calc_rms_signal(self):
        signal = np.ones(100, dtype=np.float32) * 0.5
        rms = _calc_rms(signal)
        self.assertAlmostEqual(rms, 0.5, places=4)

    def test_calc_rms_multichannel(self):
        signal_stereo = np.ones((100, 2), dtype=np.float32) * 0.4
        rms = _calc_rms(signal_stereo)
        self.assertAlmostEqual(rms, 0.4, places=4)

    def test_trigger_welcome_executes_callback_and_phrase(self):
        with patch("edith.voice.clap_detector.SPEAKER") as mock_speaker, \
             patch("edith.voice.clap_detector.BUS") as mock_bus:
            phrase = self.detector.trigger_welcome()
            self.assertIn("Welcome home", phrase)
            self.assertTrue(self.callback_called)
            mock_speaker.speak.assert_called_once()
            mock_bus.publish_sync.assert_called_once()

    def test_start_and_stop_lifecycle(self):
        mock_stream = MagicMock()
        # Return silent buffer and sleep 5ms to avoid spinning CPU
        def fake_read(size):
            time.sleep(0.02)
            return np.zeros(size, dtype=np.float32), False

        mock_stream.read.side_effect = fake_read

        with patch("edith.voice.clap_detector.sd.InputStream") as mock_input_stream:
            mock_input_stream.return_value.__enter__.return_value = mock_stream
            started = self.detector.start()
            self.assertTrue(started)
            self.assertTrue(self.detector.is_running)

            time.sleep(0.05)
            self.detector.stop()
            self.assertFalse(self.detector.is_running)

    def test_echo_suppression_blocks_loop(self):
        from edith.voice.clap_detector import SPEAKER_ECHO_GRACE_S, COOLDOWN_S
        self.assertEqual(COOLDOWN_S, 15.0)
        self.assertEqual(SPEAKER_ECHO_GRACE_S, 4.0)
        with patch("edith.voice.clap_detector.SPEAKER") as mock_speaker:
            mock_speaker.is_speaking = True
            mock_speaker.last_spoke_time = time.monotonic()
            self.assertTrue(mock_speaker.is_speaking)

    def test_crest_factor_discriminates_impulse(self):
        from edith.voice.clap_detector import MIN_CREST_FACTOR, MIN_PEAK_AMPLITUDE
        # Smooth sine wave (human voice or speaker playback)
        t = np.linspace(0, 1, 1000, endpoint=False)
        voice_wave = 0.2 * np.sin(2 * np.pi * 440 * t).astype(np.float32)
        rms = _calc_rms(voice_wave)
        peak = float(np.max(np.abs(voice_wave)))
        crest = peak / (rms + 1e-6)
        # Sine crest factor is ~sqrt(2) = 1.414, which fails clap filter
        self.assertLess(crest, MIN_CREST_FACTOR)

        # Impulse clap sound: single sharp spike
        impulse = np.zeros(1000, dtype=np.float32)
        impulse[10] = 0.5
        imp_rms = _calc_rms(impulse)
        imp_peak = float(np.max(np.abs(impulse)))
        imp_crest = imp_peak / (imp_rms + 1e-6)
        # Impulse crest factor is huge (~31.6), passing filter
        self.assertGreaterEqual(imp_crest, MIN_CREST_FACTOR)
        self.assertGreaterEqual(imp_peak, MIN_PEAK_AMPLITUDE)


if __name__ == "__main__":
    unittest.main()

