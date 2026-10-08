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
        """Transcribe PCM/WAV or WebM audio bytes using speech_recognition / Google / Whisper."""
        if not audio_bytes or len(audio_bytes) < 32:
            return ""
        try:
            # Check if audio is WebM/Opus or non-WAV container; convert to WAV via ffmpeg
            if not audio_bytes.startswith(b"RIFF"):
                try:
                    import subprocess
                    p = subprocess.run(
                        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", "pipe:0", "-f", "wav", "-ar", "16000", "-ac", "1", "pipe:1"],
                        input=audio_bytes,
                        capture_output=True,
                        timeout=5,
                    )
                    if p.returncode == 0 and p.stdout:
                        audio_bytes = p.stdout
                except Exception as conv_err:
                    logger.debug("FFmpeg audio decode notice: %s", conv_err)

            import io
            import speech_recognition as sr
            r = sr.Recognizer()
            buf = io.BytesIO(audio_bytes)
            with sr.AudioFile(buf) as source:
                audio = r.record(source)
            try:
                text = r.recognize_google(audio)
                return (text or "").strip()
            except sr.UnknownValueError:
                return ""
            except Exception as e:
                logger.debug("Google STT fallback: %s", e)
                try:
                    text = r.recognize_whisper(audio)
                    return (text or "").strip()
                except Exception:
                    return ""
        except Exception as ex:
            logger.error("Audio transcription error: %s", ex)
            return ""


# Global listener singleton
LISTENER = SpeechListener()
