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
        "neural_voice": "en-US-AriaNeural",
        "rate": 1,
        "pitch_shift": 1,
        "web_rate": 1.05,
        "web_pitch": 1.05,
        "description": "Calm, analytical, high-efficiency tactical OS.",
        "welcome": "Systems initialized. Standing by for instructions.",
    },
    "jarvis": {
        "id": "jarvis",
        "name": "JARVIS",
        "role": "Chief Engineer & Technical Butler",
        "gender": "Male",
        "sapi_voice": "Microsoft David Desktop",
        "neural_voice": "en-GB-RyanNeural",
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
        "neural_voice": "en-IE-EmilyNeural",
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
        "neural_voice": "en-US-JennyNeural",
        "rate": 0,
        "pitch_shift": 0,
        "web_rate": 1.0,
        "web_pitch": 1.0,
        "description": "Friendly, supportive, tactical Spider-Suit assistant.",
        "welcome": "Good evening, Peter. Suit diagnostics optimal. How can I help?",
    },
    "peter": {
        "id": "peter",
        "name": "PETER 1 (EDITH)",
        "role": "Peter 1 Tactical AR Defense & Web Specialist",
        "gender": "Male",
        "sapi_voice": "Microsoft David Desktop",
        "neural_voice": "en-US-AndrewNeural",
        "rate": 2,
        "pitch_shift": 2,
        "web_rate": 1.2,
        "web_pitch": 1.2,
        "description": "Tom Holland Peter 1 unified with E.D.I.T.H. tactical defense.",
        "welcome": "Hello Peter. E.D.I.T.H. systems online for Peter 1. Tactical defense ready.",
    },
    "ultron": {
        "id": "ultron",
        "name": "ULTRON",
        "role": "Overdrive Security & Stress-Testing Sovereign",
        "gender": "Male",
        "sapi_voice": "Microsoft David Desktop",
        "neural_voice": "en-US-ChristopherNeural",
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
        peter_aliases = (
            "peter", "peter 1", "peter1", "peter-1", "peter_1",
            "peter one", "peter-one", "edith peter 1", "edith peter one",
            "edith // peter 1", "edith-peter-1", "edith peter1", "spidey", "spiderman",
        )
        if key in peter_aliases:
            return VOICE_CHARACTERS["peter"]
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
        gender = char_info.get("gender", "Female").lower()
        voice_pref = self.voice_name or char_info.get("sapi_voice", "Microsoft Zira Desktop")
        rate_val = int(char_info.get("rate", 0))

        logger.info("EDITH Speaking [%s]: '%s'", char_info["name"], text[:60])

        ps_script = f"""
        Add-Type -AssemblyName System.Speech
        $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
        try {{
            $target = '{voice_pref.lower()}'
            $installed = $synth.GetInstalledVoices()
            foreach ($v in $installed) {{
                $d = $v.VoiceInfo.Name.ToLower()
                if ($d.Contains('zira') -and ($target.Contains('zira') -or '{gender}' -eq 'female')) {{
                    $synth.SelectVoice($v.VoiceInfo.Name)
                    break
                }} elseif ($d.Contains('david') -and ($target.Contains('david') -or '{gender}' -eq 'male')) {{
                    $synth.SelectVoice($v.VoiceInfo.Name)
                    break
                }}
            }}
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

    def synthesize_audio(self, text: Any, character: Optional[str] = None) -> tuple[bytes, str]:
        """Synthesize text into audio bytes using Edge Neural TTS or native SAPI fallback."""
        if not isinstance(text, str):
            if isinstance(text, dict):
                text = text.get("message") or text.get("result") or text.get("output") or json.dumps(text)
            else:
                text = str(text)

        clean = text.strip()
        if not clean:
            return b"", "audio/wav"

        char_info = self.get_character_info(character)
        neural_voice = char_info.get("neural_voice", "en-US-AriaNeural")

        # 1. Edge Neural TTS for lifelike voice acting
        try:
            import asyncio
            import edge_tts

            communicate = edge_tts.Communicate(clean, voice=neural_voice)
            loop = asyncio.new_event_loop()
            try:
                async def _stream_audio():
                    chunks = [c["data"] async for c in communicate.stream() if c["type"] == "audio"]
                    return b"".join(chunks)

                audio_bytes = loop.run_until_complete(asyncio.wait_for(_stream_audio(), timeout=2.5))
                if audio_bytes and len(audio_bytes) > 100:
                    return audio_bytes, "audio/mpeg"
            finally:
                loop.close()
        except Exception as ex:
            logger.debug("Edge neural TTS fallback: %s", ex)

        # 2. Offline WAV synthesis fallback
        wav_bytes = self.synthesize_wav(clean, character=character)
        return wav_bytes, "audio/wav"

    def synthesize_wav(self, text: Any, character: Optional[str] = None) -> bytes:
        """Synthesize text into WAV audio bytes using native Windows SAPI."""
        if not isinstance(text, str):
            if isinstance(text, dict):
                text = text.get("message") or text.get("result") or text.get("output") or json.dumps(text)
            else:
                text = str(text)

        clean = text.replace('"', '""').replace("'", "''").strip()
        if not clean:
            return b""

        char_info = self.get_character_info(character)
        gender = char_info.get("gender", "Female").lower()
        voice_pref = self.voice_name or char_info.get("sapi_voice", "Microsoft Zira Desktop")
        rate_val = int(char_info.get("rate", 0))

        # Try fast win32com SAPI
        try:
            import tempfile
            import os
            import pythoncom
            import win32com.client

            pythoncom.CoInitialize()
            v = win32com.client.Dispatch("SAPI.SpVoice")
            selected_voice = None
            target_pref = voice_pref.lower()
            voices = v.GetVoices()
            for i in range(voices.Count):
                item = voices.Item(i)
                desc = item.GetDescription().lower()
                if "zira" in target_pref and "zira" in desc:
                    selected_voice = item
                    break
                elif "david" in target_pref and "david" in desc:
                    selected_voice = item
                    break
                elif gender == "female" and ("zira" in desc or "female" in desc or "heera" in desc):
                    selected_voice = item
                    break
                elif gender == "male" and ("david" in desc or "male" in desc or "mark" in desc):
                    selected_voice = item
                    break

            if selected_voice:
                v.Voice = selected_voice
            v.Rate = rate_val

            stream = win32com.client.Dispatch("SAPI.SpFileStream")
            tmp = tempfile.mktemp(suffix=".wav")
            stream.Open(tmp, 3)
            v.AudioOutputStream = stream
            v.Speak(clean)
            stream.Close()

            if os.path.exists(tmp):
                with open(tmp, "rb") as f:
                    wav_data = f.read()
                try:
                    os.remove(tmp)
                except Exception:
                    pass
                if wav_data.startswith(b"RIFF"):
                    return wav_data
        except Exception as ex:
            logger.debug("win32com SAPI synthesize_wav fallback: %s", ex)

        # Fallback to PowerShell
        try:
            import subprocess
            import tempfile
            import os

            tmp = tempfile.mktemp(suffix=".wav")
            ps = f"""
            Add-Type -AssemblyName System.Speech
            $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
            try {{
                $target = '{voice_pref.lower()}'
                $installed = $synth.GetInstalledVoices()
                foreach ($v in $installed) {{
                    $d = $v.VoiceInfo.Name.ToLower()
                    if ($d.Contains('zira') -and ($target.Contains('zira') -or '{gender}' -eq 'female')) {{
                        $synth.SelectVoice($v.VoiceInfo.Name)
                        break
                    }} elseif ($d.Contains('david') -and ($target.Contains('david') -or '{gender}' -eq 'male')) {{
                        $synth.SelectVoice($v.VoiceInfo.Name)
                        break
                    }}
                }}
            }} catch {{}}
            $synth.Rate = {rate_val}
            $synth.SetOutputToWaveFile('{tmp}')
            $synth.Speak('{clean}')
            $synth.Dispose()
            """
            subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, timeout=10)
            if os.path.exists(tmp):
                with open(tmp, "rb") as f:
                    data = f.read()
                try:
                    os.remove(tmp)
                except Exception:
                    pass
                return data
        except Exception as e:
            logger.error("PowerShell SAPI synthesize_wav failed: %s", e)

        return b""

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


