"""Local Speech-To-Text and Microphone Listener Interface.

Implements Sections 64 and 65 of the Engineering Constitution.
"""

from __future__ import annotations

import logging
from typing import Callable, Optional

from edith.core.event_bus import BUS
from edith.core.security import SECURITY

logger = logging.getLogger("edith.voice.listener")


class SpeechListener:
    """Microphone listener interface for voice commands."""

    def __init__(self):
        self._is_listening = False
        self._on_phrase_callback: Optional[Callable[[str], None]] = None

    def start_listening(self, callback: Callable[[str], None]) -> None:
        """Start listening for speech input."""
        if SECURITY.is_privacy_mode:
            logger.warning("Privacy mode active: Microphone listener remains disabled.")
            return

        self._is_listening = True
        self._on_phrase_callback = callback
        logger.info("Speech listener activated.")

    def stop_listening(self) -> None:
        """Stop listening."""
        self._is_listening = False
        logger.info("Speech listener deactivated.")

    def inject_simulated_phrase(self, phrase: str) -> None:
        """Simulate incoming voice utterance for testing or CLI bridging."""
        logger.info("Simulated voice input: '%s'", phrase)
        if self._on_phrase_callback:
            self._on_phrase_callback(phrase)

    def transcribe_audio_bytes(self, audio_bytes: bytes) -> str:
        """Transcribe PCM/WAV or WebM audio bytes using offline Whisper engine with fallbacks."""
        if not audio_bytes or len(audio_bytes) < 32:
            return ""
        try:
            from edith.voice.whisper_engine import WHISPER_ENGINE
            return WHISPER_ENGINE.transcribe_audio_bytes(audio_bytes)
        except Exception as ex:
            logger.error("Audio transcription error: %s", ex)
            return ""


# Global listener singleton
LISTENER = SpeechListener()
