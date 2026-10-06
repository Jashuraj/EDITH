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
SAMPLE_RATE = 44100
BLOCK_MS = 40
SPIKE_RATIO = 6.5
COOLDOWN_S = 1.2
MIN_DOUBLE_GAP_S = 0.05
MAX_DOUBLE_GAP_S = 0.45
RETRIGGER_RATIO = 0.55
NOISE_FLOOR_ALPHA = 0.990
MIN_RMS = 0.010
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
        self.welcome_phrase = (
            "Welcome home, sir. All EDITH subsystems are online and nominal. Ready for your instructions."
        )

    @staticmethod
    def get_preferred_input_device() -> Optional[int]:
        """Detect Bluetooth / Headset microphone or fall back to default input."""
        try:
            devs = sd.query_devices()
            for idx, d in enumerate(devs):
                if d.get("max_input_channels", 0) > 0:
                    name = str(d.get("name", "")).lower()
                    if any(term in name for term in ["headset", "bluetooth", "buds", "pods", "hands-free", "bthhfenum"]):
                        logger.info("Auto-selected Bluetooth headset microphone [%d]: %s", idx, d.get("name"))
                        return idx
            return sd.default.device[0]
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
        """Core audio stream processing loop."""
        blocksize = int(SAMPLE_RATE * BLOCK_MS / 1000)
        noise_floor = MIN_RMS
        last_spike_time = 0.0
        last_double_time = 0.0
        armed_for_second = False

        try:
            dev_idx = self.selected_device if self.selected_device is not None else self.get_preferred_input_device()
            with sd.InputStream(
                device=dev_idx,
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
                blocksize=blocksize,
            ) as stream:
                while not self._stop_event.is_set():
                    data, overflowed = stream.read(blocksize)
                    rms = _calc_rms(data)
                    now = time.monotonic()

                    # Dynamic noise floor tracking
                    if rms < noise_floor * QUIET_GATE_MULT:
                        noise_floor = NOISE_FLOOR_ALPHA * noise_floor + (1.0 - NOISE_FLOOR_ALPHA) * rms

                    threshold = max(MIN_RMS, noise_floor * SPIKE_RATIO)
                    is_spike = rms > threshold

                    # Debounce check
                    if now < last_double_time + COOLDOWN_S:
                        continue

                    if is_spike:
                        if armed_for_second:
                            gap = now - last_spike_time
                            if MIN_DOUBLE_GAP_S <= gap <= MAX_DOUBLE_GAP_S:
                                # Double clap detected!
                                logger.info("DOUBLE CLAP DETECTED! (gap=%.3fs, rms=%.4f)", gap, rms)
                                last_double_time = now
                                armed_for_second = False
                                self.trigger_welcome()
                                continue
                            elif gap > MAX_DOUBLE_GAP_S:
                                # First clap timed out; reset with this as new first clap
                                last_spike_time = now
                        else:
                            last_spike_time = now
                            armed_for_second = True
                    else:
                        # Reset armed state if wait window passed
                        if armed_for_second and (now - last_spike_time) > MAX_DOUBLE_GAP_S:
                            armed_for_second = False

        except Exception as ex:
            logger.warning("Clap detector audio stream exception: %s", ex)
        finally:
            self._running = False


# Global clap detector singleton
CLAP_DETECTOR = ClapDetector()
