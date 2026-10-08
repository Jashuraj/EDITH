"""Low-Latency Real-Time Screen Capture & Streaming Engine for EDITH Remote Access.

Supports high-fps screen capture via Windows GDI / Desktop Duplication,
dynamic JPEG compression, resolution downscaling, and MJPEG multipart HTTP streaming.
"""

from __future__ import annotations

import io
import logging
import platform
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, Generator, Optional, Tuple

logger = logging.getLogger("edith.tools.screen_stream")

# Fallback image dimensions when display is unavailable
FALLBACK_WIDTH = 1280
FALLBACK_HEIGHT = 720


class ScreenStreamer:
    """Zero-configuration high-speed screen streamer for remote desktop & gaming."""

    def __init__(self):
        self._lock = threading.Lock()
        self._is_windows = platform.system() == "Windows"
        self._last_frame_bytes: Optional[bytes] = None
        self._last_capture_time: float = 0.0
        self._frame_count: int = 0
        self._screen_size: Tuple[int, int] = (1920, 1080)
        self._last_error: Optional[str] = None

        self._last_scale: Optional[int] = None
        self._last_quality: Optional[int] = None

        if self._is_windows:
            self._init_win32_desktop()

    def _init_win32_desktop(self) -> None:
        """Bind thread desktop to interactive input desktop on Windows."""
        try:
            import ctypes
            u32 = ctypes.windll.user32
            try:
                u32.SetProcessDPIAware()
            except Exception:
                pass
            hdesk = u32.OpenInputDesktop(0, False, 0x01FF)
            if hdesk:
                u32.SetThreadDesktop(hdesk)
            w = max(800, u32.GetSystemMetrics(0))
            h = max(600, u32.GetSystemMetrics(1))
            self._screen_size = (w, h)
        except Exception as ex:
            logger.debug("Win32 desktop initialization notice: %s", ex)

    def _capture_win32_gdi(self, scale_width: Optional[int] = None):
        """Ultra-fast zero-latency Win32 GDI screen capture via ctypes with optional StretchBlt hardware scaling."""
        try:
            import ctypes
            import ctypes.wintypes
            from PIL import Image

            class BITMAPINFOHEADER(ctypes.Structure):
                _fields_ = [
                    ("biSize", ctypes.wintypes.DWORD),
                    ("biWidth", ctypes.wintypes.LONG),
                    ("biHeight", ctypes.wintypes.LONG),
                    ("biPlanes", ctypes.wintypes.WORD),
                    ("biBitCount", ctypes.wintypes.WORD),
                    ("biCompression", ctypes.wintypes.DWORD),
                    ("biSizeImage", ctypes.wintypes.DWORD),
                    ("biXPelsPerMeter", ctypes.wintypes.LONG),
                    ("biYPelsPerMeter", ctypes.wintypes.LONG),
                    ("biClrUsed", ctypes.wintypes.DWORD),
                    ("biClrImportant", ctypes.wintypes.DWORD),
                ]

            u32 = ctypes.windll.user32
            gdi32 = ctypes.windll.gdi32

            w = u32.GetSystemMetrics(0)
            h = u32.GetSystemMetrics(1)
            if w <= 0 or h <= 0:
                return None

            self._screen_size = (w, h)

            # Determine target dimensions
            if scale_width and scale_width < w:
                tw = scale_width
                th = max(1, int(h * tw / w))
                use_stretch = True
            else:
                tw = w
                th = h
                use_stretch = False

            hdc_screen = u32.GetDC(0)
            if not hdc_screen:
                return None

            hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
            hbm = gdi32.CreateCompatibleBitmap(hdc_screen, tw, th)
            old_bm = gdi32.SelectObject(hdc_mem, hbm)

            try:
                if use_stretch:
                    gdi32.SetStretchBltMode(hdc_mem, 3)  # COLORONCOLOR / HALFTONE
                    res = gdi32.StretchBlt(hdc_mem, 0, 0, tw, th, hdc_screen, 0, 0, w, h, 0x00CC0020)
                else:
                    # 0x00CC0020 is SRCCOPY
                    res = gdi32.BitBlt(hdc_mem, 0, 0, w, h, hdc_screen, 0, 0, 0x00CC0020)

                if not res:
                    return None

                bmi = BITMAPINFOHEADER()
                bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
                bmi.biWidth = tw
                bmi.biHeight = -th  # top-down DIB
                bmi.biPlanes = 1
                bmi.biBitCount = 32
                bmi.biCompression = 0

                buf = ctypes.create_string_buffer(tw * th * 4)
                lines = gdi32.GetDIBits(hdc_mem, hbm, 0, th, buf, ctypes.byref(bmi), 0)
                if lines == 0:
                    return None

                im = Image.frombuffer("RGBA", (tw, th), buf, "raw", "BGRA", 0, 1)
                rgb = im.convert("RGB")
                return rgb
            finally:
                if old_bm:
                    gdi32.SelectObject(hdc_mem, old_bm)
                if hbm:
                    gdi32.DeleteObject(hbm)
                if hdc_mem:
                    gdi32.DeleteDC(hdc_mem)
                if hdc_screen:
                    u32.ReleaseDC(0, hdc_screen)
        except Exception as ex:
            self._last_error = f"GDI capture exception: {ex}"
            return None

    def capture_raw_image(self, scale_width: Optional[int] = None):
        """Capture the current display as a PIL Image."""
        if self._is_windows:
            self._init_win32_desktop()
            # 1. Attempt ultra-fast Win32 GDI hardware capture
            gdi_im = self._capture_win32_gdi(scale_width=scale_width)
            if gdi_im is not None:
                return gdi_im

        # 2. Secondary fallback via PIL ImageGrab
        try:
            from PIL import ImageGrab
            im = ImageGrab.grab(all_screens=False)
            if im and im.size[0] > 0 and im.size[1] > 0:
                self._screen_size = im.size
                return im
        except Exception as ex:
            self._last_error = str(ex)

        # 3. Render high-tech fallback HUD canvas if screen is inaccessible
        return self._render_placeholder_frame()

    def _render_placeholder_frame(self):
        """Generate a fallback screen frame when display server is non-interactive."""
        from PIL import Image, ImageDraw

        w, h = self._screen_size if self._screen_size[0] > 0 else (FALLBACK_WIDTH, FALLBACK_HEIGHT)
        im = Image.new("RGB", (w, h), color=(8, 12, 24))
        draw = ImageDraw.Draw(im)

        # Draw grid lines
        grid_step = 80
        for x in range(0, w, grid_step):
            draw.line([(x, 0), (x, h)], fill=(16, 26, 48), width=1)
        for y in range(0, h, grid_step):
            draw.line([(0, y), (w, y)], fill=(16, 26, 48), width=1)

        # Draw tech header
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        msg = f"EDITH REMOTE DESKTOP [STANDBY / HEADLESS MODE] - {ts}"
        draw.text((40, 40), msg, fill=(0, 229, 255))
        draw.text((40, 70), f"RESOLUTION: {w}x{h} | SYSTEM HOST: ACTIVE", fill=(0, 230, 118))
        if self._last_error:
            draw.text((40, 100), f"CAPTURE STATUS: {self._last_error}", fill=(255, 145, 0))

        # Center target reticle
        cx, cy = w // 2, h // 2
        r = 60
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(0, 229, 255), width=2)
        draw.line([cx - r - 20, cy, cx + r + 20, cy], fill=(0, 229, 255), width=2)
        draw.line([cx, cy - r - 20, cx, cy + r + 20], fill=(0, 229, 255), width=2)
        return im

    def capture_jpeg_bytes(
        self,
        scale_width: Optional[int] = 1280,
        quality: int = 70,
    ) -> bytes:
        """Capture screen, optionally downsample, and encode into JPEG bytes."""
        now = time.time()
        with self._lock:
            # Low-latency cache: Return recent frame if requested within 33ms (target 30 FPS)
            if (
                self._last_frame_bytes is not None
                and (now - self._last_capture_time < 0.033)
                and (self._last_scale == scale_width)
            ):
                return self._last_frame_bytes

            try:
                im = self.capture_raw_image(scale_width=scale_width)
            except TypeError:
                im = self.capture_raw_image()

            # Ensure RGB color mode for JPEG encoding (prevent RGBA crash)
            if im.mode != "RGB":
                im = im.convert("RGB")

            # Fallback downsample if hardware GDI scaling was bypassed and image is wider
            if scale_width and im.width > scale_width:
                aspect = im.height / im.width
                target_height = max(1, int(scale_width * aspect))
                from PIL import Image
                im = im.resize((scale_width, target_height), Image.Resampling.BILINEAR)

            buf = io.BytesIO()
            # Fast JPEG compression (720p HD / 1080p FHD)
            im.save(buf, format="JPEG", quality=max(10, min(95, quality)), optimize=False)
            data = buf.getvalue()

            self._last_frame_bytes = data
            self._last_capture_time = now
            self._last_scale = scale_width
            self._last_quality = quality
            self._frame_count += 1
            return data

    def generate_mjpeg_stream(
        self,
        fps: int = 20,
        scale_width: Optional[int] = 1280,
        quality: int = 60,
    ) -> Generator[bytes, None, None]:
        """Generator that yields multipart/x-mixed-replace MJPEG frame boundaries."""
        target_delay = 1.0 / max(1, min(60, fps))
        boundary = b"--frame\r\n"

        while True:
            t0 = time.perf_counter()
            try:
                frame_bytes = self.capture_jpeg_bytes(scale_width=scale_width, quality=quality)
                header = (
                    b"Content-Type: image/jpeg\r\n"
                    b"Content-Length: " + str(len(frame_bytes)).encode("ascii") + b"\r\n\r\n"
                )
                yield boundary + header + frame_bytes + b"\r\n"
            except Exception as ex:
                logger.error("MJPEG streaming frame capture error: %s", ex)
                time.sleep(0.1)

            elapsed = time.perf_counter() - t0
            sleep_time = target_delay - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def get_stats(self) -> Dict[str, Any]:
        """Return screen streamer telemetry."""
        return {
            "screen_width": self._screen_size[0],
            "screen_height": self._screen_size[1],
            "frame_count": self._frame_count,
            "last_capture_time": self._last_capture_time,
            "last_error": self._last_error,
        }


# Global singleton screen streamer
SCREEN_STREAMER = ScreenStreamer()
