"""Local Offline Text-To-Speech Synthesizer with Barge-In Support.

Implements Sections 64 and 66 of the Engineering Constitution.
Uses native Windows SAPI without cloud audio costs.
"""

from __future__ import annotations

import json
import logging
import platform
import subprocess
import threading
from typing import Any, Optional

logger = logging.getLogger("edith.voice.speaker")


class SpeechSynthesizer:
    """Offline Windows speech synthesizer with interruptible playback."""

    def __init__(self, voice_name: Optional[str] = None):
        self.voice_name = voice_name
        self._current_process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self._muted: bool = False
        self._last_spoke_time: float = 0.0

    @property
    def is_speaking(self) -> bool:
        """Check if speech audio is actively playing."""
        with self._lock:
            if self._current_process is not None:
                if self._current_process.poll() is None:
                    return True
                self._current_process = None
                import time
                self._last_spoke_time = time.monotonic()
            return False

    @property
    def last_spoke_time(self) -> float:
        """Monotonic timestamp of when speech finished playing."""
        return self._last_spoke_time

    @property
    def is_muted(self) -> bool:
        """Check if voice output is currently muted."""
        return self._muted

    def set_muted(self, muted: bool) -> None:
        """Set voice mute state."""
        self._muted = bool(muted)
        if self._muted:
            self.stop()
        logger.info("SpeechSynthesizer mute set to: %s", self._muted)

    def toggle_muted(self) -> bool:
        """Toggle mute state and return new state."""
        self.set_muted(not self._muted)
        return self._muted

    def speak(self, text: Any, async_mode: bool = True) -> bool:
        """Synthesize text into audible speech using native Windows SAPI."""
        if self._muted:
            logger.info("Speech synthesis skipped (voice muted).")
            return True

        self.stop()  # Barge-in: interrupt any currently playing speech

        if not isinstance(text, str):
            if isinstance(text, dict):
                text = text.get("message") or text.get("result") or text.get("output") or json.dumps(text)
            else:
                text = str(text)

        clean_text = text.replace('"', '""').replace("'", "''")
        logger.info("EDITH Speaking: '%s'", text[:60])

        ps_script = f"""
        Add-Type -AssemblyName System.Speech
        $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
        $synth.Speak('{clean_text}')
        """

        try:
            if platform.system() == "Windows":
                proc = subprocess.Popen(
                    ["powershell", "-NoProfile", "-Command", ps_script],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                with self._lock:
                    self._current_process = proc

                if not async_mode:
                    proc.wait()
            return True
        except Exception as e:
            logger.error("Speech synthesis failed: %s", e)
            return False

    def stop(self) -> None:
        """Interrupt and terminate current speech (Barge-In)."""
        with self._lock:
            if self._current_process and self._current_process.poll() is None:
                try:
                    self._current_process.terminate()
                    logger.info("Speech playback interrupted (Barge-in).")
                except Exception:
                    pass
                self._current_process = None
                import time
                self._last_spoke_time = time.monotonic()



# Global speaker singleton
SPEAKER = SpeechSynthesizer()
