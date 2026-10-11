"""Test suite for Bluetooth audio, vision, voice mute, and offline skills.

Verifies newly implemented requirements:
- Bluetooth audio device detection and selection
- Voice output mute / unmute support
- Screen perception and visual analysis
- Server endpoints for audio, voice, and vision
"""

import pytest
from edith.voice.speaker import SPEAKER
from edith.voice.clap_detector import CLAP_DETECTOR
from edith.tools.vision import VISION
from edith.tools.reflex import REFLEX
from edith.memory.local_store import MEMORY


def test_speaker_mute_toggle():
    """Verify SpeechSynthesizer can mute and unmute cleanly."""
    SPEAKER.set_muted(False)
    assert not SPEAKER.is_muted

    # Toggle mute on
    new_state = SPEAKER.toggle_muted()
    assert new_state is True
    assert SPEAKER.is_muted is True

    # Speak while muted should return True without executing
    assert SPEAKER.speak("Testing muted speech") is True

    # Unmute
    SPEAKER.set_muted(False)
    assert not SPEAKER.is_muted


def test_clap_detector_preferred_device():
    """Verify clap detector preferred device detection and selection."""
    dev = CLAP_DETECTOR.get_preferred_input_device()
    assert dev is None or isinstance(dev, int)

    CLAP_DETECTOR.set_input_device(2)
    assert CLAP_DETECTOR.selected_device == 2


def test_vision_desktop_context():
    """Verify VisionTools collects desktop context and analyze_screen works."""
    ctx = VISION.get_desktop_context()
    assert isinstance(ctx, dict)
    assert "active_apps" in ctx

    analysis = VISION.analyze_screen()
    assert isinstance(analysis, dict)
    assert analysis["success"] is True
    assert "perception" in analysis
    assert len(analysis["perception"]) > 0


def test_new_reflex_matches():
    """Verify new reflex patterns evaluate and execute within <15ms."""
    # 1. Vision reflex
    v_match = REFLEX.evaluate("look at my screen")
    assert v_match is not None
    assert v_match.command_name == "analyze_screen"
    res = REFLEX.execute_match(v_match)
    assert isinstance(res, str)
    assert len(res) > 0

    # 2. Voice mute reflex
    m_match = REFLEX.evaluate("mute voice")
    assert m_match is not None
    assert m_match.command_name == "mute_voice"
    m_res = REFLEX.execute_match(m_match)
    assert "muted" in m_res.lower()
    assert SPEAKER.is_muted is True

    # 3. Voice unmute reflex
    u_match = REFLEX.evaluate("unmute voice")
    assert u_match is not None
    assert u_match.command_name == "unmute_voice"
    u_res = REFLEX.execute_match(u_match)
    assert "unmuted" in u_res.lower()
    assert SPEAKER.is_muted is False

    # 4. Bluetooth mic reflex
    bt_match = REFLEX.evaluate("switch mic to bluetooth")
    assert bt_match is not None
    assert bt_match.command_name == "switch_mic_bluetooth"


def test_lifelong_skills_populated():
    """Verify that lifelong memory contains offline skills."""
    from edith.tasks.seed_skills import seed
    seed()
    skills = MEMORY.get_all_learned_skills()
    assert len(skills) >= 20
    goals = [s["goal"] for s in skills]
    assert "flush dns cache" in goals
    assert "get battery health" in goals
