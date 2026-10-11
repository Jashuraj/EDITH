"""Voice Transcript Stream and Fast Interim Recognition for EDITH.

Inspired by animcin84-dev/jarvis-fable-5 lib/voice/helpers.ts and JARVIS_VOICE_SPECS.md.
Provides:
1. Fast interim transcript commitment (180ms for trigger words, 450ms for phrases).
2. Transcript normalization and deduplication across interim/final phases.
3. Clean speech language detection.
"""

from __future__ import annotations

import re
from typing import Optional, Set

FAST_INTERIM_PHRASES: Set[str] = {
    "hi",
    "hey",
    "hello",
    "edith",
    "jarvis",
    "thanks",
    "thank you",
    "ok",
    "okay",
    "yes",
    "stop",
    "mute",
}


def normalize_speech_transcript(text: Optional[str]) -> str:
    """Collapse internal whitespace and strip trailing noise from voice transcript."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def merge_speech_transcript(interim: Optional[str], final: Optional[str]) -> str:
    """Merge interim and final transcripts avoiding stutter or duplicate words."""
    interim_clean = normalize_speech_transcript(interim)
    final_clean = normalize_speech_transcript(final)

    if not interim_clean:
        return final_clean
    if not final_clean:
        return interim_clean

    interim_lower = interim_clean.lower()
    final_lower = final_clean.lower()

    if interim_lower == final_lower:
        return interim_clean
    if interim_lower.endswith(final_lower):
        return interim_clean
    if interim_lower.startswith(final_lower):
        return interim_clean

    return final_clean


def should_commit_interim_transcript(interim: Optional[str], stable_ms: float) -> bool:
    """Determine whether an interim speech stream should be committed immediately.

    Short trigger commands commit in 180ms to provide near zero latency,
    while full sentences wait 450ms for phonetic stability.
    """
    clean = normalize_speech_transcript(interim).lower()
    if not clean:
        return False

    if clean in FAST_INTERIM_PHRASES and stable_ms >= 180.0:
        return True

    words = [w for w in clean.split() if w]
    return stable_ms >= 450.0 and len(clean) >= 10 and len(words) >= 3
