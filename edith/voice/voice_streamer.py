"""Full-Duplex Real-Time Voice Streaming and Barge-in Engine.

Implements Sections 22, 60, and 61 of the Engineering Constitution.
Processes live incoming PCM audio frames, computes RMS energy for Voice Activity Detection,
and triggers instant barge-in interruption events when user speaks while EDITH is vocalizing.
"""

from __future__ import annotations

import logging
import math
import struct
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from edith.core.event_bus import BUS

logger = logging.getLogger("edith.voice.voice_streamer")


class RealTimeVoiceStreamer:
    """Manages real-time audio chunk processing and conversational barge-in."""

    def __init__(self, sample_rate: int = 16000, vad_threshold: float = 0.035):
        self.sample_rate = sample_rate
        self.vad_threshold = vad_threshold
        self._is_speaking_lock = threading.Lock()
        self._edith_is_vocalizing = False
        self._buffer: bytearray = bytearray()
        self._on_speech_detected: Optional[Callable[[], None]] = None

    def set_vocalizing(self, vocalizing: bool) -> None:
        """Inform voice streamer whether EDITH is currently speaking."""
        with self._is_speaking_lock:
            self._edith_is_vocalizing = vocalizing

    def is_vocalizing(self) -> bool:
        """Check if EDITH is vocalizing."""
        with self._is_speaking_lock:
            return self._edith_is_vocalizing

    def calculate_rms(self, pcm_data: bytes) -> float:
        """Compute Root-Mean-Square (RMS) amplitude of 16-bit PCM samples."""
        if not pcm_data or len(pcm_data) < 2:
            return 0.0

        num_samples = len(pcm_data) // 2
        try:
            samples = struct.unpack(f"<{num_samples}h", pcm_data[: num_samples * 2])
            sum_squares = sum(s * s for s in samples)
            rms = math.sqrt(sum_squares / num_samples) / 32768.0
            return float(rms)
        except Exception:
            return 0.0

    def process_incoming_chunk(self, chunk: bytes) -> Dict[str, Any]:
        """Analyze incoming audio chunk for speech and barge-in."""
        if not chunk:
            return {"has_speech": False, "barge_in": False, "rms": 0.0}

        rms = self.calculate_rms(chunk)
        has_speech = rms >= self.vad_threshold
        barge_in = False

        if has_speech:
            self._buffer.extend(chunk)
            # Check for Barge-in Interruption
            if self.is_vocalizing():
                barge_in = True
                logger.info("Barge-in detected! User voice RMS: %.3f (EDITH speaking)", rms)
                BUS.publish_sync("voice:barge_in", {"rms": rms})
                if self._on_speech_detected:
                    try:
                        self._on_speech_detected()
                    except Exception as ex:
                        logger.error("Barge-in handler error: %s", ex)
        else:
            # Silence padding / windowing
            if len(self._buffer) > self.sample_rate * 2:  # over 1 second
                self._buffer.clear()

        return {
            "has_speech": has_speech,
            "barge_in": barge_in,
            "rms": rms,
        }

    def set_barge_in_callback(self, callback: Callable[[], None]) -> None:
        """Set callback invoked on barge-in speech detection."""
        self._on_speech_detected = callback

    def reset_buffer(self) -> None:
        """Clear incoming speech buffer."""
        self._buffer.clear()

    def get_status(self) -> Dict[str, Any]:
        """Return streamer state."""
        return {
            "sample_rate": self.sample_rate,
            "vad_threshold": self.vad_threshold,
            "edith_vocalizing": self.is_vocalizing(),
            "buffer_bytes": len(self._buffer),
        }


# Global Singleton Instance
VOICE_STREAMER = RealTimeVoiceStreamer()
