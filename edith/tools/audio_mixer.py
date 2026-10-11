"""Remote Per-App Audio Mixer and Media Controller.

Implements Sections 24, 25, and 69 of the EDITH Master Engineering Constitution.
Provides precision master volume control, per-application audio stream balancing
(Spotify, Chrome, games, Discord), and global media playback keys.
"""

from __future__ import annotations

import ctypes
import logging
import threading
from typing import Any, Dict, List, Optional

logger = logging.getLogger("edith.tools.audio_mixer")

VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3


class AudioMixer:
    """Master audio and per-application volume mixer with media playback keys."""

    def __init__(self):
        self._lock = threading.Lock()

    def _ensure_com(self):
        """Initialize COM for calling thread."""
        try:
            import comtypes
            comtypes.CoInitialize()
        except Exception:
            pass

    def _uninit_com(self):
        """Uninitialize COM for calling thread."""
        try:
            import comtypes
            comtypes.CoUninitialize()
        except Exception:
            pass

    def get_master_volume(self) -> Dict[str, Any]:
        """Query current master output volume level (0-100) and mute state."""
        with self._lock:
            self._ensure_com()
            try:
                from pycaw.pycaw import AudioUtilities
                device = AudioUtilities.GetSpeakers()
                if hasattr(device, "EndpointVolume") and device.EndpointVolume:
                    vol_ctl = device.EndpointVolume
                else:
                    from pycaw.pycaw import IAudioEndpointVolume
                    from comtypes import CLSCTX_ALL
                    inter = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                    vol_ctl = inter.QueryInterface(IAudioEndpointVolume)

                level_scalar = vol_ctl.GetMasterVolumeLevelScalar()
                level_pct = int(round(level_scalar * 100))
                is_muted = bool(vol_ctl.GetMute())
                return {"success": True, "volume": level_pct, "muted": is_muted}
            except Exception as ex:
                logger.warning("Master volume query error: %s", ex)
                return {"success": False, "volume": 50, "muted": False, "error": str(ex)}
            finally:
                self._uninit_com()

    def set_master_volume(self, level: int) -> Dict[str, Any]:
        """Set master volume to an exact percentage (0-100)."""
        target = max(0, min(100, int(level)))
        with self._lock:
            self._ensure_com()
            try:
                from pycaw.pycaw import AudioUtilities
                device = AudioUtilities.GetSpeakers()
                if hasattr(device, "EndpointVolume") and device.EndpointVolume:
                    vol_ctl = device.EndpointVolume
                else:
                    from pycaw.pycaw import IAudioEndpointVolume
                    from comtypes import CLSCTX_ALL
                    inter = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                    vol_ctl = inter.QueryInterface(IAudioEndpointVolume)

                vol_ctl.SetMasterVolumeLevelScalar(target / 100.0, None)
                if target > 0 and vol_ctl.GetMute():
                    vol_ctl.SetMute(0, None)
                logger.info("Master volume set to %d%%.", target)
                return {"success": True, "volume": target, "muted": bool(vol_ctl.GetMute())}
            except Exception as ex:
                logger.warning("Set master volume error: %s", ex)
                return {"success": False, "error": str(ex)}
            finally:
                self._uninit_com()

    def set_master_mute(self, mute: Optional[bool] = None) -> Dict[str, Any]:
        """Toggle or set master mute state."""
        with self._lock:
            self._ensure_com()
            try:
                from pycaw.pycaw import AudioUtilities
                device = AudioUtilities.GetSpeakers()
                if hasattr(device, "EndpointVolume") and device.EndpointVolume:
                    vol_ctl = device.EndpointVolume
                else:
                    from pycaw.pycaw import IAudioEndpointVolume
                    from comtypes import CLSCTX_ALL
                    inter = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                    vol_ctl = inter.QueryInterface(IAudioEndpointVolume)

                current_mute = bool(vol_ctl.GetMute())
                target_mute = not current_mute if mute is None else bool(mute)
                vol_ctl.SetMute(1 if target_mute else 0, None)
                return {"success": True, "muted": target_mute, "volume": int(round(vol_ctl.GetMasterVolumeLevelScalar() * 100))}
            except Exception as ex:
                logger.warning("Master mute toggle error: %s", ex)
                return {"success": False, "error": str(ex)}
            finally:
                self._uninit_com()

    def get_app_sessions(self) -> List[Dict[str, Any]]:
        """List active audio sessions emitting or configured for audio output."""
        with self._lock:
            self._ensure_com()
            results = []
            try:
                from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
                sessions = AudioUtilities.GetAllSessions()
                seen = set()

                for s in sessions:
                    try:
                        p = s.Process
                        pname = p.name() if p else "System Sounds"
                        pid = p.pid if p else 0

                        vol_ctl = s._ctl.QueryInterface(ISimpleAudioVolume)
                        vol_scalar = vol_ctl.GetMasterVolume()
                        is_muted = bool(vol_ctl.GetMute())

                        # Dedup sessions with same process name & pid
                        key = (pname.lower(), pid)
                        if key in seen:
                            continue
                        seen.add(key)

                        results.append({
                            "process_name": pname,
                            "pid": pid,
                            "volume": int(round(vol_scalar * 100)),
                            "muted": is_muted,
                        })
                    except Exception:
                        continue
            except Exception as ex:
                logger.warning("Audio session enumeration error: %s", ex)
            finally:
                self._uninit_com()

            return results

    def set_app_volume(self, process_name: str, level: int) -> Dict[str, Any]:
        """Set volume level (0-100) for a specific application process."""
        target = max(0, min(100, int(level)))
        target_name = process_name.lower().strip()
        matched = 0

        with self._lock:
            self._ensure_com()
            try:
                from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
                sessions = AudioUtilities.GetAllSessions()

                for s in sessions:
                    try:
                        p = s.Process
                        pname = p.name() if p else "System Sounds"
                        if target_name in pname.lower():
                            vol_ctl = s._ctl.QueryInterface(ISimpleAudioVolume)
                            vol_ctl.SetMasterVolume(target / 100.0, None)
                            if target > 0 and vol_ctl.GetMute():
                                vol_ctl.SetMute(0, None)
                            matched += 1
                    except Exception:
                        continue
            except Exception as ex:
                logger.warning("App volume adjustment error: %s", ex)
                return {"success": False, "error": str(ex)}
            finally:
                self._uninit_com()

        if matched > 0:
            logger.info("Adjusted audio volume for %s to %d%% (%d sessions).", process_name, target, matched)
            return {"success": True, "process_name": process_name, "volume": target, "matched_sessions": matched}
        return {"success": False, "error": f"Process '{process_name}' not found among active audio sessions."}

    def set_app_mute(self, process_name: str, mute: Optional[bool] = None) -> Dict[str, Any]:
        """Toggle or set mute for a specific application process."""
        target_name = process_name.lower().strip()
        matched = 0

        with self._lock:
            self._ensure_com()
            try:
                from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
                sessions = AudioUtilities.GetAllSessions()

                for s in sessions:
                    try:
                        p = s.Process
                        pname = p.name() if p else "System Sounds"
                        if target_name in pname.lower():
                            vol_ctl = s._ctl.QueryInterface(ISimpleAudioVolume)
                            current = bool(vol_ctl.GetMute())
                            target_mute = not current if mute is None else bool(mute)
                            vol_ctl.SetMute(1 if target_mute else 0, None)
                            matched += 1
                    except Exception:
                        continue
            except Exception as ex:
                logger.warning("App mute toggle error: %s", ex)
                return {"success": False, "error": str(ex)}
            finally:
                self._uninit_com()

        if matched > 0:
            return {"success": True, "process_name": process_name, "matched_sessions": matched}
        return {"success": False, "error": f"Process '{process_name}' not found among active audio sessions."}

    def media_control(self, action: str) -> Dict[str, Any]:
        """Dispatch native Windows media keystroke."""
        action_map = {
            "play": VK_MEDIA_PLAY_PAUSE,
            "pause": VK_MEDIA_PLAY_PAUSE,
            "play_pause": VK_MEDIA_PLAY_PAUSE,
            "next": VK_MEDIA_NEXT_TRACK,
            "prev": VK_MEDIA_PREV_TRACK,
            "previous": VK_MEDIA_PREV_TRACK,
            "stop": VK_MEDIA_STOP,
            "mute": VK_VOLUME_MUTE,
            "volume_up": VK_VOLUME_UP,
            "volume_down": VK_VOLUME_DOWN,
        }

        vk = action_map.get(action.lower().strip())
        if not vk:
            return {"success": False, "error": f"Unsupported media action: {action}"}

        try:
            user32 = ctypes.windll.user32
            user32.keybd_event(vk, 0, 0, 0)
            user32.keybd_event(vk, 0, 2, 0)
            logger.info("Dispatched media key: %s (VK: 0x%X)", action, vk)
            return {"success": True, "action": action}
        except Exception as ex:
            logger.error("Media key dispatch error: %s", ex)
            return {"success": False, "error": str(ex)}


# Global audio mixer singleton
AUDIO_MIXER = AudioMixer()
