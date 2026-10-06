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


if __name__ == "__main__":
    unittest.main()
