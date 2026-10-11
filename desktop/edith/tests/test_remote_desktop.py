"""Unit and Integration Tests for EDITH Remote Desktop, Screen Streaming & Gamepad.

Tests ScreenStreamer, RemoteInputDispatcher, PhoneProtocol bi-directional messaging,
and Phone Gateway HTTP endpoints.
"""

from __future__ import annotations

import io
import json
import time
import urllib.request
from typing import Any, Dict

import pytest
from PIL import Image

from edith.phone.protocol import PhoneProtocol
from edith.phone.tunnel import TunnelManager
from edith.tools.remote_input import RemoteInputDispatcher
from edith.tools.screen_stream import ScreenStreamer


class TestScreenStreamer:
    """Tests for real-time display capture and MJPEG frame encoding."""

    def test_capture_raw_image(self):
        streamer = ScreenStreamer()
        im = streamer.capture_raw_image()
        assert isinstance(im, Image.Image)
        assert im.width > 0
        assert im.height > 0

    def test_capture_jpeg_bytes(self):
        streamer = ScreenStreamer()
        data = streamer.capture_jpeg_bytes(scale_width=640, quality=50)
        assert isinstance(data, bytes)
        assert len(data) > 100
        # Check standard JPEG SOI marker
        assert data.startswith(b"\xff\xd8\xff")

    def test_downscale_resolution(self):
        streamer = ScreenStreamer()
        data = streamer.capture_jpeg_bytes(scale_width=320, quality=40)
        im = Image.open(io.BytesIO(data))
        assert im.width <= 320

    def test_mjpeg_stream_generator(self):
        streamer = ScreenStreamer()
        gen = streamer.generate_mjpeg_stream(fps=30, scale_width=320, quality=40)
        frame1 = next(gen)
        assert b"--frame\r\n" in frame1
        assert b"Content-Type: image/jpeg\r\n" in frame1
        assert b"\xff\xd8\xff" in frame1

    def test_streamer_stats(self):
        streamer = ScreenStreamer()
        stats = streamer.get_stats()
        assert "screen_width" in stats
        assert "screen_height" in stats
        assert "frame_count" in stats


class TestRemoteInputDispatcher:
    """Tests for mouse, keyboard, joystick, and gamepad actions."""

    @pytest.fixture
    def dispatcher(self):
        return RemoteInputDispatcher()

    def test_key_press_and_release(self, dispatcher):
        assert dispatcher.key_down("w") is True
        assert "w" in dispatcher._held_keys
        assert dispatcher.key_up("w") is True
        assert "w" not in dispatcher._held_keys

    def test_type_text(self, dispatcher):
        assert dispatcher.type_text("EDITH 2026") is True
        assert dispatcher.type_text("") is True

    def test_hotkey_execution(self, dispatcher):
        assert dispatcher.hotkey(["ctrl", "c"]) is True

    def test_joystick_deadzone(self, dispatcher):
        # Inside deadzone -> no keys active
        res = dispatcher.handle_joystick(0.05, 0.05, deadzone=0.2)
        assert res["success"] is True
        assert res["active_keys"] == []
        dispatcher.release_all_joystick()

    def test_joystick_directional_mapping(self, dispatcher):
        # Up / Forward
        res_up = dispatcher.handle_joystick(0.0, -0.8, deadzone=0.2, mode="wasd")
        assert "w" in res_up["active_keys"]

        # Right
        res_right = dispatcher.handle_joystick(0.8, 0.0, deadzone=0.2, mode="wasd")
        assert "d" in res_right["active_keys"]
        assert "w" in res_right["released_keys"]

        # Down + Left diagonal
        res_diag = dispatcher.handle_joystick(-0.7, 0.7, deadzone=0.2, mode="wasd")
        assert "s" in res_diag["active_keys"]
        assert "a" in res_diag["active_keys"]

        # Return to center
        res_center = dispatcher.handle_joystick(0.0, 0.0, deadzone=0.2, mode="wasd")
        assert res_center["active_keys"] == []
        dispatcher.release_all_joystick()

    def test_game_buttons_mapping(self, dispatcher):
        # Button A (Space / Jump)
        res_a = dispatcher.handle_game_button("A", True)
        assert res_a["success"] is True
        assert res_a["mapped_key"] == "space"
        assert res_a["state"] == "down"

        # Button B (C / Crouch)
        res_b = dispatcher.handle_game_button("B", False)
        assert res_b["mapped_key"] == "c"
        assert res_b["state"] == "up"

        # Shoulder buttons
        res_sprint = dispatcher.handle_game_button("SPRINT", True)
        assert res_sprint["mapped_key"] == "shift"

        dispatcher.handle_game_button("A", False)
        dispatcher.handle_game_button("SPRINT", False)

    def test_dispatch_universal(self, dispatcher):
        res_move = dispatcher.dispatch("mouse_move", {"x": 0.5, "y": 0.5})
        assert res_move["success"] is True

        res_click = dispatcher.dispatch("left_click", {})
        assert res_click["success"] is True

        res_scroll = dispatcher.dispatch("scroll", {"delta": 2})
        assert res_scroll["success"] is True

        res_scroll_up = dispatcher.dispatch("scroll_up", {})
        assert res_scroll_up["success"] is True

        res_scroll_down = dispatcher.dispatch("scroll_down", {})
        assert res_scroll_down["success"] is True

        res_browser_key = dispatcher.key_press("ArrowUp")
        assert res_browser_key is True

        res_invalid = dispatcher.dispatch("unknown_action_xyz", {})
        assert res_invalid["success"] is False


class TestPhoneProtocolBiDirectional:
    """Tests for device sessions, outbox queues, and clipboard sync."""

    @pytest.fixture
    def protocol(self):
        return PhoneProtocol()

    def test_pairing_and_token_verification(self, protocol):
        token = protocol.pair_device("phone_alpha", "Samsung Galaxy")
        assert len(token) > 20
        assert protocol.verify_token("phone_alpha", token) is True
        assert protocol.verify_token("phone_alpha", "wrong_token") is False

    def test_bi_directional_outbox(self, protocol):
        protocol.pair_device("phone_1", "Pixel 8")
        protocol.send_message_to_phone("phone_1", {"type": "push", "text": "Hello phone"})

        msgs = protocol.poll_messages_for_phone("phone_1")
        assert len(msgs) == 1
        assert msgs[0]["text"] == "Hello phone"

        # Outbox should be flushed after polling
        assert protocol.poll_messages_for_phone("phone_1") == []

    def test_paired_devices_telemetry(self, protocol):
        protocol.pair_device("dev_1", "Test Device")
        protocol.update_device_heartbeat("dev_1", battery_percent=85, connection_type="LOCAL")

        devs = protocol.get_paired_devices()
        assert len(devs) == 1
        assert devs[0]["device_id"] == "dev_1"
        assert devs[0]["battery_percent"] == 85
        assert "token" not in devs[0]  # Tokens must not be exposed

    def test_clipboard_synchronization(self, protocol):
        res = protocol.sync_clipboard_from_phone("EDITH_SYNC_CLIPBOARD_TEST", "phone_1")
        assert res["success"] is True
        current = protocol.get_current_clipboard()
        assert current == "EDITH_SYNC_CLIPBOARD_TEST"


class TestTunnelManager:
    """Tests for tunnel manager configuration and status reporting."""

    def test_tunnel_status_fields(self):
        tm = TunnelManager()
        status = tm.get_status()
        assert "active" in status
        assert "url" in status
        assert "provider" in status
        assert "has_ssh" in status

    def test_custom_tunnel_url(self):
        tm = TunnelManager()
        tm.set_custom_url("https://my-edith-tunnel.example.com")
        assert tm.get_active_url() == "https://my-edith-tunnel.example.com"
        tm.set_custom_url("")
        assert tm.get_active_url() is None

    def test_tunnel_reentrancy_no_deadlock(self):
        tm = TunnelManager()
        # Verify calling stop_tunnel does not deadlock on re-entrant lock
        tm.stop_tunnel()
        status = tm.get_status()
        assert status["active"] is False

    def test_tunnel_health_check_invalid_url(self):
        tm = TunnelManager()
        assert tm.check_url_health("") is False
        assert tm.check_url_health("http://invalid-non-existent-local-edith.xyz:9999") is False

    def test_screen_streamer_rgba_handling(self, monkeypatch):
        streamer = ScreenStreamer()
        # Mock raw image as RGBA
        rgba_img = Image.new("RGBA", (200, 200), (255, 50, 50, 128))
        monkeypatch.setattr(streamer, "capture_raw_image", lambda: rgba_img)
        jpeg_bytes = streamer.capture_jpeg_bytes(scale_width=100, quality=50)
        assert isinstance(jpeg_bytes, bytes)
        assert jpeg_bytes.startswith(b"\xff\xd8\xff")

    def test_game_combat_mouse_buttons(self):
        dispatcher = RemoteInputDispatcher()
        res_fire = dispatcher.handle_game_button("FIRE", True)
        assert res_fire["success"] is True
        assert res_fire["mapped_action"] == "mouse_left"
        assert res_fire["state"] == "down"

        res_fire_up = dispatcher.handle_game_button("FIRE", False)
        assert res_fire_up["mapped_action"] == "mouse_left"
        assert res_fire_up["state"] == "up"

        res_aim = dispatcher.handle_game_button("AIM", True)
        assert res_aim["success"] is True
        assert res_aim["mapped_action"] == "mouse_right"
        assert res_aim["state"] == "down"

        res_aim_up = dispatcher.handle_game_button("AIM", False)
        assert res_aim_up["mapped_action"] == "mouse_right"
        assert res_aim_up["state"] == "up"

    def test_gamepad_select_and_start_buttons(self):
        dispatcher = RemoteInputDispatcher()
        res_sel = dispatcher.handle_game_button("SELECT", True)
        assert res_sel["mapped_key"] == "tab"

        res_start = dispatcher.handle_game_button("START", True)
        assert res_start["mapped_key"] == "escape"

    def test_dispatch_lock_and_unlock(self):
        dispatcher = RemoteInputDispatcher()
        res_lock = dispatcher.dispatch("lock", {})
        assert res_lock["success"] is True

        res_unlock = dispatcher.dispatch("unlock", {})
        assert res_unlock["success"] is True

    def test_youtube_same_tab_and_camera_tools(self):
        from edith.tools.windows import WIN_TOOLS
        yt_res = WIN_TOOLS.search_youtube("linkin park in same tab", open_browser=True)
        assert yt_res["success"] is True
        assert yt_res["same_tab"] is True

        cam_mode = WIN_TOOLS.switch_to_camera_mode()
        assert "success" in cam_mode

        pic_res = WIN_TOOLS.take_picture()
        assert "success" in pic_res

        open_res = WIN_TOOLS.open_latest_picture()
        assert "success" in open_res

    def test_camera_and_unlock_reflexes(self):
        from edith.tools.reflex import REFLEX_ENGINE
        m1 = REFLEX_ENGINE.evaluate("unlock pc")
        assert m1 is not None
        assert m1.command_name == "unlock_workstation"

        m2 = REFLEX_ENGINE.evaluate("switch to camera mode")
        assert m2 is not None
        assert m2.command_name == "switch_to_camera_mode"

        m3 = REFLEX_ENGINE.evaluate("take picture")
        assert m3 is not None
        assert m3.command_name == "take_picture"

        m4 = REFLEX_ENGINE.evaluate("open picture which u have clicked")
        assert m4 is not None
        assert m4.command_name == "open_latest_picture"

        m5 = REFLEX_ENGINE.evaluate("play alan walker in same tab")
        assert m5 is not None
        assert m5.command_name == "search_youtube_same_tab"
