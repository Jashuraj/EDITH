"""Biometric Face Presence Sentinel.

Implements Sections 24 and 52 of the EDITH Master Engineering Constitution.
Tracks physical presence via webcam computer vision. Automatically triggers
secure workstation lock when authorized user leaves desk beyond timeout limit.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict, Optional

from edith.core.event_bus import BUS
from edith.tools.windows import WIN_TOOLS

logger = logging.getLogger("edith.tools.face_sentinel")


class BiometricFaceSentinel:
    """Real-time webcam biometric presence sentinel and autonomous auto-lock guard."""

    def __init__(self, absence_timeout: float = 30.0, camera_index: int = 0):
        self.absence_timeout = float(max(5.0, absence_timeout))
        self.camera_index = camera_index
        self._is_active = False
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        self._face_detected = False
        self._last_seen_time = time.time()
        self._total_locks_triggered = 0
        self._mock_mode = False
        self._mock_face_present = True

    @property
    def is_active(self) -> bool:
        return self._is_active

    def start(self, absence_timeout: Optional[float] = None, camera_index: Optional[int] = None) -> Dict[str, Any]:
        """Start the biometric face presence surveillance loop."""
        with self._lock:
            if self._is_active:
                return {"success": True, "message": "Biometric sentinel is already active.", "status": self.get_status()}

            if absence_timeout is not None:
                self.absence_timeout = float(max(5.0, absence_timeout))
            if camera_index is not None:
                self.camera_index = camera_index

            self._is_active = True
            self._stop_event.clear()
            self._last_seen_time = time.time()
            self._face_detected = True

            self._thread = threading.Thread(target=self._sentinel_worker, daemon=True, name="FaceSentinelWorker")
            self._thread.start()
            logger.info("Biometric face sentinel activated. Timeout: %.1fs, Camera: %d", self.absence_timeout, self.camera_index)

        return {"success": True, "message": "Biometric face sentinel started.", "status": self.get_status()}

    def stop(self) -> Dict[str, Any]:
        """Stop the biometric face presence surveillance loop."""
        with self._lock:
            if not self._is_active:
                return {"success": True, "message": "Biometric sentinel is not active.", "status": self.get_status()}

            self._is_active = False
            self._stop_event.set()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

        logger.info("Biometric face sentinel deactivated.")
        return {"success": True, "message": "Biometric face sentinel stopped.", "status": self.get_status()}

    def set_timeout(self, seconds: float) -> Dict[str, Any]:
        """Update absence grace timeout in seconds."""
        with self._lock:
            self.absence_timeout = float(max(5.0, seconds))
        logger.info("Biometric absence timeout adjusted to %.1f seconds.", self.absence_timeout)
        return {"success": True, "absence_timeout": self.absence_timeout}

    def simulate_presence(self, present: bool) -> None:
        """Testing hook for deterministic verification without physical webcam."""
        with self._lock:
            self._mock_mode = True
            self._mock_face_present = present
            if present:
                self._last_seen_time = time.time()
                self._face_detected = True
            else:
                self._face_detected = False

    def get_status(self) -> Dict[str, Any]:
        """Telemetry and sentinel diagnostics."""
        with self._lock:
            now = time.time()
            absent_seconds = max(0.0, round(now - self._last_seen_time, 1)) if not self._face_detected else 0.0
            return {
                "active": self._is_active,
                "face_detected": self._face_detected,
                "absence_timeout": self.absence_timeout,
                "absent_seconds": absent_seconds,
                "total_locks": self._total_locks_triggered,
                "camera_index": self.camera_index,
                "mock_mode": self._mock_mode,
            }

    def _sentinel_worker(self) -> None:
        """Background thread monitoring webcam frames at 1 Hz for near-zero CPU overhead."""
        cap = None
        face_cascade = None

        if not self._mock_mode:
            try:
                import cv2
                cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
                face_cascade = cv2.CascadeClassifier(cascade_path)
                # Open webcam with DirectShow backend for instant initialization on Windows
                cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
                if not cap.isOpened():
                    cap = cv2.VideoCapture(self.camera_index)
            except Exception as cam_err:
                logger.warning("Webcam initialization notice: %s. Entering simulated sentinel mode.", cam_err)
                self._mock_mode = True

        while not self._stop_event.is_set():
            now = time.time()
            detected = False

            if self._mock_mode:
                with self._lock:
                    detected = self._mock_face_present
            else:
                try:
                    import cv2
                    if cap and cap.isOpened():
                        ret, frame = cap.read()
                        if ret and frame is not None:
                            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                            faces = face_cascade.detectMultiScale(
                                gray,
                                scaleFactor=1.1,
                                minNeighbors=4,
                                minSize=(60, 60),
                            )
                            detected = len(faces) > 0
                except Exception as detect_err:
                    logger.debug("Face detection iteration error: %s", detect_err)

            with self._lock:
                self._face_detected = detected
                if detected:
                    self._last_seen_time = now
                else:
                    absent_time = now - self._last_seen_time
                    if absent_time >= self.absence_timeout:
                        logger.warning("Absence timeout reached (%.1fs >= %.1fs). Triggering auto-lock.", absent_time, self.absence_timeout)
                        self._trigger_workstation_lock(absent_time)
                        # Reset last_seen_time to prevent repeated locks in rapid succession
                        self._last_seen_time = time.time()

            # Wait 1.0 second between frames to keep CPU < 1%
            self._stop_event.wait(1.0)

        if cap and hasattr(cap, "release"):
            try:
                cap.release()
            except Exception:
                pass


    def _trigger_workstation_lock(self, absent_seconds: float) -> None:
        """Lock workstation session and emit system event."""
        self._total_locks_triggered += 1
        try:
            WIN_TOOLS.lock_workstation()
            BUS.emit(
                "security:face_sentinel_locked",
                {
                    "reason": "biometric_absence_timeout",
                    "absent_seconds": round(absent_seconds, 1),
                    "total_locks": self._total_locks_triggered,
                },
            )
        except Exception as lock_err:
            logger.error("Failed to execute workstation lock: %s", lock_err)


# Global face sentinel singleton
FACE_SENTINEL = BiometricFaceSentinel()
