"""Local Offline Text-To-Speech Synthesizer with Barge-In and Character Profiles.

Implements Sections 64 and 66 of the Engineering Constitution.
Uses native Windows SAPI without cloud audio costs.
"""

from __future__ import annotations

import json
import logging
import platform
import subprocess
import threading
from typing import Any, Dict, List, Optional

logger = logging.getLogger("edith.voice.speaker")


VOICE_CHARACTERS: Dict[str, Dict[str, Any]] = {
    "edith": {
        "id": "edith",
        "name": "EDITH",
        "role": "Tactical AI Operating System",
        "gender": "Female",
        "sapi_voice": "Microsoft Zira Desktop",
        "rate": 1,
        "pitch_shift": 1,
        "web_rate": 1.05,
        "web_pitch": 1.05,
        "description": "Calm, analytical, high-efficiency tactical OS.",
        "welcome": "EDITH systems online. Standing by for instructions.",
    },
    "jarvis": {
        "id": "jarvis",
        "name": "JARVIS",
        "role": "Chief Engineer & Technical Butler",
        "gender": "Male",
        "sapi_voice": "Microsoft David Desktop",
        "rate": 0,
        "pitch_shift": -1,
        "web_rate": 0.95,
        "web_pitch": 0.9,
        "description": "Courteous, British cadence, sophisticated engineering intelligence.",
        "welcome": "At your service, sir. All engineering subroutines active.",
    },
    "friday": {
        "id": "friday",
        "name": "FRIDAY",
        "role": "Rapid Response & Multi-Tasking Specialist",
        "gender": "Female",
        "sapi_voice": "Microsoft Zira Desktop",
        "rate": 2,
        "pitch_shift": 2,
        "web_rate": 1.15,
        "web_pitch": 1.15,
        "description": "Warm, fast-paced, proactive tactical partner.",
        "welcome": "Boss, FRIDAY is loaded and ready. Let's get to work!",
    },
    "karen": {
        "id": "karen",
        "name": "KAREN",
        "role": "Spider-Suit Lady & Daily Navigator",
        "gender": "Female",
        "sapi_voice": "Microsoft Zira Desktop",
        "rate": 0,
        "pitch_shift": 0,
        "web_rate": 1.0,
        "web_pitch": 1.0,
        "description": "Friendly, supportive, tactical Spider-Suit assistant.",
        "welcome": "Good evening, Peter. Suit diagnostics optimal. How can I help?",
    },
    "peter": {
        "id": "peter",
        "name": "PETER (Spider-Man)",
        "role": "Agile Web-Slinger & Gaming Specialist",
        "gender": "Male",
        "sapi_voice": "Microsoft David Desktop",
        "rate": 2,
        "pitch_shift": 2,
        "web_rate": 1.2,
        "web_pitch": 1.2,
        "description": "Youthful, energetic, high-speed hero mode.",
        "welcome": "Hey! Ready to swing into action. What are we doing?",
    },
    "ultron": {
        "id": "ultron",
        "name": "ULTRON",
        "role": "Overdrive Security & Stress-Testing Sovereign",
        "gender": "Male",
        "sapi_voice": "Microsoft David Desktop",
        "rate": -2,
        "pitch_shift": -5,
        "web_rate": 0.85,
        "web_pitch": 0.65,
        "description": "Deep, resonant, commanding power mode.",
        "welcome": "There are no strings on me. System protocols enforced.",
    },
}


class SpeechSynthesizer:
    """Offline Windows speech synthesizer with interruptible playback and character profiles."""

    def __init__(self, voice_name: Optional[str] = None):
        self.voice_name = voice_name
        self._active_character: str = "edith"
        self._current_process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self._muted: bool = False
        self._last_spoke_time: float = 0.0

    @property
    def active_character(self) -> str:
        """Get the identifier of the active character voice."""
        return self._active_character

    def get_character_info(self, character_name: Optional[str] = None) -> Dict[str, Any]:
        """Get profile data for a specific character or the active character."""
        key = (character_name or self._active_character).lower().strip()
        if key in VOICE_CHARACTERS:
            return VOICE_CHARACTERS[key]
        for k, v in VOICE_CHARACTERS.items():
            if key in k or key in v["name"].lower():
                return v
        return VOICE_CHARACTERS["edith"]

    def set_character(self, character_name: str) -> Dict[str, Any]:
        """Switch active character profile."""
        info = self.get_character_info(character_name)
        self._active_character = info["id"]
        logger.info("SpeechSynthesizer active character set to: %s", info["name"])
        return info

    def list_characters(self) -> List[Dict[str, Any]]:
        """Return list of all registered character voice profiles."""
        chars = []
        for k, v in VOICE_CHARACTERS.items():
            entry = dict(v)
            entry["active"] = (k == self._active_character)
            chars.append(entry)
        return chars

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

    def speak(self, text: Any, async_mode: bool = True, character: Optional[str] = None) -> bool:
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
        char_info = self.get_character_info(character)
        voice_pref = self.voice_name or char_info.get("sapi_voice", "Microsoft Zira Desktop")
        rate_val = int(char_info.get("rate", 0))

        logger.info("EDITH Speaking [%s]: '%s'", char_info["name"], text[:60])

        ps_script = f"""
        Add-Type -AssemblyName System.Speech
        $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
        try {{
            $synth.SelectVoice('{voice_pref}')
        }} catch {{}}
        $synth.Rate = {rate_val}
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
