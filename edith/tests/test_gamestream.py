"""Unit tests for Open-Source GameStream Engine (Sunshine / Wolf / Moonlight Architecture)."""

import pytest
from edith.tools.gamestream import GAMESTREAM_ENGINE
from edith.tools.mouse_controller import MOUSE
from edith.tools.remote_input import REMOTE_INPUT


def test_gamestream_status():
    """Verify gamestream status reports hardware and streamer capabilities."""
    status = GAMESTREAM_ENGINE.get_status()
    assert isinstance(status, dict)
    assert "active" in status
    assert "target_fps" in status
    assert status["target_fps"] == 60
    assert "controller_active" in status


def test_gamestream_detect_games():
    """Verify game detection finds desktop and installed gaming launchers."""
    games = GAMESTREAM_ENGINE.detect_games()
    assert isinstance(games, list)
    assert len(games) >= 1
    # Desktop mode is always available
    desktop_game = next((g for g in games if g["id"] == "desktop"), None)
    assert desktop_game is not None
    assert "Desktop" in desktop_game["name"]


def test_gamestream_launch_and_stop():
    """Verify game launch and stop state transitions."""
    res_launch = GAMESTREAM_ENGINE.launch_game("desktop")
    assert res_launch["success"] is True
    assert res_launch["status"] == "active"

    status = GAMESTREAM_ENGINE.get_status()
    assert status["active"] is True

    res_stop = GAMESTREAM_ENGINE.stop_game()
    assert res_stop["success"] is True
    assert res_stop["status"] == "stopped"


def test_gamestream_dispatch_gamepad():
    """Verify Moonlight-compatible gamepad packet dispatching."""
    packet = {
        "left_stick": {"x": 0.5, "y": -0.8},
        "right_stick": {"dx": 5, "dy": -3},
        "buttons": [
            {"name": "A", "pressed": True},
            {"name": "FIRE", "pressed": True},
        ],
    }
    res = GAMESTREAM_ENGINE.dispatch_gamepad(packet)
    assert res["success"] is True

    # Release buttons
    release_packet = {
        "left_stick": {"x": 0.0, "y": 0.0},
        "buttons": [
            {"name": "A", "pressed": False},
            {"name": "FIRE", "pressed": False},
        ],
    }
    res_rel = GAMESTREAM_ENGINE.dispatch_gamepad(release_packet)
    assert res_rel["success"] is True


def test_mouse_relative_move():
    """Verify relative mouse move for 3D camera look."""
    res = MOUSE.move_relative(10, -5)
    assert isinstance(res, bool)


def test_remote_input_camera_look():
    """Verify remote input dispatcher processes camera_look action."""
    res = REMOTE_INPUT.dispatch("camera_look", {"dx": 8, "dy": -4})
    assert res["success"] is True
    assert res["action"] == "camera_look"
