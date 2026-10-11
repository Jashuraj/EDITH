"""Local Clap-Activated Welcome System for EDITH.

Inspired by hectorg2211/jarvis double-clap audio detection.
Uses native microphone amplitude analysis and default Windows laptop SAPI voices.
Runs completely offline and online without ElevenLabs or cloud API keys.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Callable, Optional

import numpy as np
import sounddevice as sd

from edith.core.event_bus import BUS
from edith.voice.speaker import SPEAKER

logger = logging.getLogger("edith.voice.clap")

# Audio detection constants (tuned for laptop microphone)
DEFAULT_SAMPLE_RATE = 44100
BLOCK_MS = 25
SPIKE_RATIO = 3.0
COOLDOWN_S = 3.0
SPEAKER_ECHO_GRACE_S = 4.0
MIN_CREST_FACTOR = 3.0
MIN_PEAK_AMPLITUDE = 0.075
MIN_DOUBLE_GAP_S = 0.12
MAX_DOUBLE_GAP_S = 0.95
RETRIGGER_RATIO = 0.55
NOISE_FLOOR_ALPHA = 0.990
MIN_RMS = 0.005
QUIET_GATE_MULT = 2.2



def _calc_rms(block: np.ndarray) -> float:
    """Calculate root-mean-square amplitude of audio block."""
    if block.ndim > 1:
        block = np.mean(block.astype(np.float64), axis=1)
    else:
        block = block.astype(np.float64)
    if block.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(block**2)))


class ClapDetector:
    """Microphone double-clap listener triggering the EDITH welcome protocol."""

    def __init__(self, welcome_callback: Optional[Callable[[], None]] = None):
        self._welcome_callback = welcome_callback
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.selected_device: Optional[int] = None
        self._last_double_time: float = 0.0
        self.welcome_phrase = (
            "Welcome home, sir. Systems operational and ready for your instructions."
        )

    @staticmethod
    def _get_working_samplerate(idx: Optional[int]) -> Optional[int]:
        """Determine a functional input sample rate for the device."""
        rates_to_try = [44100, 48000, 16000, 32000, 22050]
        try:
            if idx is not None:
                info = sd.query_devices(idx)
                def_rate = int(info.get("default_samplerate", 0))
                if def_rate > 0 and def_rate not in rates_to_try:
                    rates_to_try.insert(0, def_rate)
                elif def_rate > 0:
                    rates_to_try.remove(def_rate)
                    rates_to_try.insert(0, def_rate)
        except Exception:
            pass

        for rate in rates_to_try:
            try:
                sd.check_input_settings(device=idx, samplerate=rate, channels=1, dtype="float32")
                return rate
            except Exception:
                continue
        return None

    @classmethod
    def _is_device_openable(cls, idx: Optional[int]) -> bool:
        """Verify device can actually be opened for audio input without PortAudio crashes."""
        rate = cls._get_working_samplerate(idx)
        if rate is None:
            return False
        try:
            stream = sd.InputStream(device=idx, samplerate=rate, channels=1, blocksize=256)
            stream.start()
            stream.stop()
            stream.close()
            return True
        except Exception:
            return False

    @classmethod
    def get_preferred_input_device(cls) -> Optional[int]:
        """Detect working Bluetooth/headset mic or working default input."""
        try:
            devs = sd.query_devices()
            # 1. Prefer functional Bluetooth / headset microphone that can actually stream
            for idx, d in enumerate(devs):
                if d.get("max_input_channels", 0) > 0:
                    name = str(d.get("name", "")).lower()
                    if any(term in name for term in ["headset", "bluetooth", "buds", "pods", "hands-free"]):
                        if cls._is_device_openable(idx):
                            logger.info("Auto-selected openable Bluetooth headset microphone [%d]: %s", idx, d.get("name"))
                            return idx

            # 2. Prefer working system default input
            try:
                def_idx = sd.default.device[0]
                if def_idx is not None and def_idx >= 0 and cls._is_device_openable(def_idx):
                    return def_idx
            except Exception:
                pass

            # 3. Fallback to any functional input device (WASAPI / DirectSound / Realtek / MME)
            for idx, d in enumerate(devs):
                if d.get("max_input_channels", 0) > 0:
                    if cls._is_device_openable(idx):
                        return idx

            # 4. Check if default None works
            if cls._is_device_openable(None):
                return None

            return None
        except Exception as e:
            logger.debug("Failed querying audio devices: %s", e)
            return None

    def set_input_device(self, device_idx: int) -> None:
        """Explicitly set audio input device index."""
        self.selected_device = device_idx
        logger.info("Clap detector audio device set to [%s]", device_idx)
        if self.is_running:
            self.stop()
            self.start()

    @property
    def is_running(self) -> bool:
        return self._running and self._thread is not None and self._thread.is_alive()

    def start(self) -> bool:
        """Start listening for double-claps in background thread."""
        if self.is_running:
            logger.info("Clap detector is already active.")
            return True

        self._stop_event.clear()
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True, name="ClapDetectorThread")
        self._thread.start()
        logger.info("Clap welcome detector started.")
        return True

    def stop(self) -> None:
        """Stop background clap listening."""
        self._running = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.5)
        self._thread = None
        logger.info("Clap welcome detector stopped.")

    def trigger_welcome(self) -> str:
        """Execute the EDITH welcome sequence using the default laptop voice."""
        self._last_double_time = time.monotonic()
        logger.info("EDITH Welcome Protocol activated by double-clap.")
        try:
            # Broadcast welcome event
            try:
                BUS.publish_sync("clap:welcome", {"phrase": self.welcome_phrase, "timestamp": time.time()})
            except Exception:
                pass

            # Speak welcome using default laptop voice (Windows SAPI5)
            SPEAKER.speak(self.welcome_phrase, async_mode=True)

            if self._welcome_callback:
                self._welcome_callback()

            return self.welcome_phrase
        except Exception as e:
            logger.error("Error executing welcome protocol: %s", e)
            return "Welcome sequence error."

    def _listen_loop(self) -> None:
        """Core audio stream processing loop with continuous host error resilience."""
        noise_floor = MIN_RMS
        last_spike_time = 0.0
        last_double_time = self._last_double_time
        armed_for_second = False


        while not self._stop_event.is_set():
            try:
                dev_idx = self.selected_device if self.selected_device is not None else self.get_preferred_input_device()
                sample_rate = self._get_working_samplerate(dev_idx)
                if sample_rate is None and self._is_device_openable(None):
                    dev_idx = None
                    sample_rate = self._get_working_samplerate(None)

                if sample_rate is None:
                    # No functional input driver found, enter silent wait
                    logger.debug("No active microphone driver detected. Standby for device connection.")
                    if self._stop_event.wait(timeout=5.0):
                        break
                    continue

                blocksize = max(256, int(sample_rate * BLOCK_MS / 1000))
                with sd.InputStream(
                    device=dev_idx,
                    samplerate=sample_rate,
                    channels=1,
                    dtype="float32",
                    blocksize=blocksize,
                ) as stream:
                    logger.info("Clap detector active on device [%s] at %dHz", dev_idx, sample_rate)
                    while not self._stop_event.is_set():
                        data, overflowed = stream.read(blocksize)
                        rms = _calc_rms(data)
                        now = time.monotonic()

                        # Echo suppression: ignore microphone while speaker is active or echoing
                        if SPEAKER.is_speaking or (now - SPEAKER.last_spoke_time < SPEAKER_ECHO_GRACE_S):
                            armed_for_second = False
                            continue

                        # Debounce check
                        if now < last_double_time + COOLDOWN_S:
                            armed_for_second = False
                            continue

                        # Dynamic noise floor tracking (ambient room only)
                        if rms < noise_floor * QUIET_GATE_MULT:
                            noise_floor = NOISE_FLOOR_ALPHA * noise_floor + (1.0 - NOISE_FLOOR_ALPHA) * rms

                        peak = float(np.max(np.abs(data)))
                        crest_factor = peak / (rms + 1e-6)
                        is_impulse = (crest_factor >= MIN_CREST_FACTOR) and (peak >= MIN_PEAK_AMPLITUDE)

                        threshold = max(MIN_RMS, noise_floor * SPIKE_RATIO)
                        is_spike = (rms > threshold) and is_impulse


                        if is_spike:
                            if armed_for_second:
                                gap = now - last_spike_time
                                if MIN_DOUBLE_GAP_S <= gap <= MAX_DOUBLE_GAP_S:
                                    # Double clap detected!
                                    logger.info("DOUBLE CLAP DETECTED! (gap=%.3fs, rms=%.4f)", gap, rms)
                                    last_double_time = now + 12.0
                                    armed_for_second = False
                                    self.trigger_welcome()
                                    continue
                                elif gap > MAX_DOUBLE_GAP_S:
                                    # First clap timed out; reset with this as new first clap
                                    last_spike_time = now
                                    armed_for_second = True
                                # If gap < MIN_DOUBLE_GAP_S, it is reverberation tail of the first clap; do nothing and remain armed
                            else:
                                last_spike_time = now
                                armed_for_second = True
                        else:
                            # Reset armed state if wait window passed
                            if armed_for_second and (now - last_spike_time) > MAX_DOUBLE_GAP_S:
                                armed_for_second = False

            except Exception as ex:
                logger.debug("Clap detector audio host notice: %s. Standing by.", ex)
                if self._stop_event.wait(timeout=4.0):
                    break

        self._running = False


# Global clap detector singleton
CLAP_DETECTOR = ClapDetector()
