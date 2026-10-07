"""Acoustic Speech Band Echo Suppression for EDITH.

Inspired by Mark-LV core/echo.py architecture.
Analyzes speech band energies to prevent microphone echo loops when audio is
actively playing through laptop or external speakers.
"""

from __future__ import annotations

import logging
import time
from typing import List, Tuple
import numpy as np

logger = logging.getLogger("edith.core.echo")

# Speech formant frequency bands
_BAND_EDGES = (200, 400, 700, 1100, 1700, 2600, 3800, 5200, 7000)
_HISTORY_S = 2.0


def band_energies(pcm: np.ndarray, sr: int = 16000) -> np.ndarray:
    """Compute raw energy per speech frequency band."""
    x = np.asarray(pcm, dtype=np.float32)
    if x.size < 64:
        return np.zeros(len(_BAND_EDGES) - 1, dtype=np.float32)
    x = x - float(np.mean(x))
    n = 1 << (int(x.size) - 1).bit_length()
    mag = np.abs(np.fft.rfft(x * np.hanning(x.size), n=n))
    freqs = np.fft.rfftfreq(n, 1.0 / sr)
    out = np.empty(len(_BAND_EDGES) - 1, dtype=np.float32)
    for i in range(len(_BAND_EDGES) - 1):
        m = (freqs >= _BAND_EDGES[i]) & (freqs < _BAND_EDGES[i + 1])
        out[i] = float(np.sum(mag[m]))
    return out


class EchoGuard:
    """Monitors speaker audio playback and suppresses acoustic echo in microphone streams."""

    def __init__(self):
        self._history: List[Tuple[float, np.ndarray, float]] = []
        self._last_similarity: float = 0.0

    def note_output(self, pcm: np.ndarray, sr: int = 16000, level: float = 0.5) -> None:
        """Record audio output chunk for echo fingerprint comparison."""
        try:
            t = time.monotonic()
            bands = band_energies(pcm, sr)
            self._history.append((t, bands, float(level)))
            cutoff = t - _HISTORY_S
            if len(self._history) > 16:
                self._history = [h for h in self._history if h[0] >= cutoff]
        except Exception:
            pass

    def is_echo(self, pcm: np.ndarray, sr: int = 16000) -> bool:
        """Determine whether the microphone input represents acoustic echo."""
        if not self._history:
            return False

        t = time.monotonic()
        bands = band_energies(pcm, sr)
        total = float(np.sum(bands))
        if total <= 1e-9:
            return False

        best_res = 1.0
        for ts, ref, _ref_level in self._history:
            if ts > t or t - ts > _HISTORY_S:
                continue
            denom = float(np.dot(ref, ref))
            if denom < 1e-12:
                continue
            alpha = max(0.0, float(np.dot(bands, ref)) / denom)
            residual = np.maximum(bands - alpha * ref, 0.0)
            ratio = float(np.sum(residual)) / total
            if ratio < best_res:
                best_res = ratio

        self._last_similarity = 1.0 - best_res
        # High similarity (> 0.70) indicates self-echo from speaker
        return self._last_similarity > 0.70

    def reset(self) -> None:
        """Clear playback history."""
        self._history.clear()
        self._last_similarity = 0.0


# Global singleton
ECHO_GUARD = EchoGuard()
