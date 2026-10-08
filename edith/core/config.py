"""EDITH System Configuration and Dynamic Hardware Profile Detector.

Optimized for Windows 11 on Dell Latitude 5490 (Intel Core i5-8350U, 8GB RAM).
"""

from __future__ import annotations

import os
import platform
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict


@dataclass
class HardwareProfile:
    """Runtime detected hardware characteristics."""
    cpu_name: str = "Unknown CPU"
    cpu_cores: int = 4
    cpu_threads: int = 8
    total_ram_gb: float = 8.0
    free_ram_gb: float = 4.0
    gpu_name: str = "Intel UHD Graphics 620"
    vram_mb: int = 1024
    os_name: str = "Windows 11"
    os_version: str = "10.0"
    is_windows: bool = True
    disk_free_gb: float = 50.0
    disk_total_gb: float = 250.0
    battery_percent: int = 100
    is_ac_powered: bool = True
    ollama_available: bool = False
    ollama_endpoint: str = "http://localhost:11434"

    @classmethod
    def detect(cls) -> HardwareProfile:
        """Dynamically detect host system hardware on Windows."""
        is_win = platform.system() == "Windows"
        profile = cls(
            cpu_name=platform.processor() or "Intel Core i5",
            cpu_cores=os.cpu_count() or 4,
            cpu_threads=os.cpu_count() or 8,
            os_name=f"{platform.system()} {platform.release()}",
            os_version=platform.version(),
            is_windows=is_win,
        )

        # Detect storage
        try:
            usage = shutil.disk_usage(Path(__file__).anchor or "C:\\")
            profile.disk_free_gb = round(usage.free / (1024**3), 2)
            profile.disk_total_gb = round(usage.total / (1024**3), 2)
        except Exception:
            pass

        # Windows-specific CIM / WMI or psutil queries if available
        if is_win:
            try:
                import ctypes
                class MEMORYSTATUSEX(ctypes.Structure):
                    _fields_ = [
                        ("dwLength", ctypes.c_ulong),
                        ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                    ]
                stat = MEMORYSTATUSEX()
                stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
                if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                    profile.total_ram_gb = round(stat.ullTotalPhys / (1024**3), 2)
                    profile.free_ram_gb = round(stat.ullAvailPhys / (1024**3), 2)
            except Exception:
                pass

            # Battery via GetSystemPowerStatus
            try:
                import ctypes
                class SYSTEM_POWER_STATUS(ctypes.Structure):
                    _fields_ = [
                        ("ACLineStatus", ctypes.c_byte),
                        ("BatteryFlag", ctypes.c_byte),
                        ("BatteryLifePercent", ctypes.c_byte),
                        ("SystemStatusFlag", ctypes.c_byte),
                        ("BatteryLifeTime", ctypes.c_ulong),
                        ("BatteryFullLifeTime", ctypes.c_ulong),
                    ]
                sps = SYSTEM_POWER_STATUS()
                if ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(sps)):
                    pct = sps.BatteryLifePercent
                    # 255 means "unknown" (desktop / AC-only)
                    if pct != 255:
                        profile.battery_percent = int(pct)
                    profile.is_ac_powered = bool(sps.ACLineStatus == 1)
            except Exception:
                pass

        return profile


@dataclass
class ResourceCeilings:
    """Configurable system limits preventing CPU / RAM starvation."""
    max_ram_usage_gb: float = 6.0
    max_cpu_percent: int = 80
    max_concurrent_tasks: int = 3
    max_models_loaded: int = 1
    vision_fps_cap: int = 15
    keep_alive_minutes: int = 5


@dataclass
class SystemConfig:
    """Master configuration for the EDITH runtime."""
    system_name: str = "EDITH"
    creator: str = "Jashwanth Raj"
    version: str = "1.0.0"
    base_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent)
    workspace_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent)
    data_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent / "data")
    manual_mode: str = "auto"  # "auto", "online", "offline"
    offline_mode: bool = False
    zero_credit_mode: bool = False
    privacy_mode: bool = False
    emergency_stopped: bool = False
    clap_welcome_enabled: bool = False
    hardware: HardwareProfile = field(default_factory=HardwareProfile.detect)
    ceilings: ResourceCeilings = field(default_factory=ResourceCeilings)
    primary_local_model: str = "hermes3:3b"
    reflex_local_model: str = "tinydolphin:1.1b"
    vision_local_model: str = "qwen3-vl:2b"
    coder_local_model: str = "hhao/qwen2.5-coder-tools:0.5b"
    cloud_model: str = "gemini-2.5-flash"
    ui_port: int = 8794
    phone_port: int = 8795

    def __post_init__(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        # Apply low resource mode if detected RAM is <= 8GB
        if self.hardware.total_ram_gb <= 8.5:
            self.ceilings.max_ram_usage_gb = 5.5
            self.ceilings.max_models_loaded = 1
            self.ceilings.max_concurrent_tasks = 2
            self.ceilings.vision_fps_cap = 10

    def set_manual_mode(self, mode: str) -> str:
        """Switch operating mode between auto, online, and offline."""
        cleaned = (mode or "").strip().lower()
        if cleaned not in ("auto", "online", "offline"):
            cleaned = "auto"
        self.manual_mode = cleaned
        if cleaned == "offline":
            self.offline_mode = True
            self._user_locked_offline = True
        elif cleaned == "online":
            self.offline_mode = False
            self._user_locked_offline = False
        else:
            self._user_locked_offline = False
            self.offline_mode = not self.check_internet(timeout_seconds=0.8)
        return self.manual_mode

    def is_effectively_online(self) -> bool:
        """Evaluate if system is allowed to make external cloud queries."""
        if self.privacy_mode or self.zero_credit_mode or self.offline_mode:
            return False
        if self.manual_mode == "offline":
            return False
        if self.manual_mode == "online":
            return True
        return self.check_internet(timeout_seconds=0.8)

    @staticmethod
    def check_internet(timeout_seconds: float = 1.0) -> bool:
        """Probe internet connectivity with caching and multiple fallback endpoints."""
        import socket
        import time
        now = time.time()
        # Use class-level attributes for thread-safe caching
        cached_time = getattr(SystemConfig, "_last_internet_time", 0.0)
        cached_status = getattr(SystemConfig, "_cached_internet_status", True)
        if now - cached_time < 3.0:
            return cached_status

        targets = [("8.8.8.8", 53), ("1.1.1.1", 53), ("1.1.1.1", 443)]
        is_ok = False
        for host, port in targets:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(timeout_seconds)
                    s.connect((host, port))
                is_ok = True
                break
            except Exception:
                continue

        SystemConfig._last_internet_time = now
        SystemConfig._cached_internet_status = is_ok
        return is_ok

    def refresh_dynamic_stats(self) -> Dict[str, Any]:
        """Update and return dynamic telemetry."""
        is_win = platform.system() == "Windows"
        if is_win:
            try:
                import ctypes
                class MEMORYSTATUSEX(ctypes.Structure):
                    _fields_ = [
                        ("dwLength", ctypes.c_ulong),
                        ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                    ]
                stat = MEMORYSTATUSEX()
                stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
                if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                    self.hardware.total_ram_gb = round(stat.ullTotalPhys / (1024**3), 2)
                    self.hardware.free_ram_gb = round(stat.ullAvailPhys / (1024**3), 2)
            except Exception:
                pass

        try:
            usage = shutil.disk_usage(Path(__file__).anchor or "C:\\")
            self.hardware.disk_free_gb = round(usage.free / (1024**3), 2)
        except Exception:
            pass

        if self.manual_mode == "auto":
            has_net = self.check_internet(timeout_seconds=0.8)
            if has_net and self.offline_mode and not getattr(self, "_user_locked_offline", False):
                self.offline_mode = False
            elif not has_net:
                self.offline_mode = True

        eff_online = self.is_effectively_online()
        if self.manual_mode == "offline":
            status_text = "OFFLINE (FORCED LOCAL)"
        elif self.manual_mode == "online":
            status_text = "ONLINE (FORCED CLOUD)" if eff_online else "ONLINE (DISCONNECTED)"
        else:
            status_text = "ONLINE (HYBRID AI)" if eff_online else "OFFLINE (LOCAL AI)"

        bat_pct = self.hardware.battery_percent
        power_plug = self.hardware.is_ac_powered
        try:
            import psutil
            b = psutil.sensors_battery()
            if b:
                bat_pct = int(round(b.percent))
                power_plug = bool(b.power_plugged)
        except Exception:
            pass

        return {
            "online": eff_online,
            "manual_mode": self.manual_mode,
            "status_text": status_text,
            "free_ram_gb": self.hardware.free_ram_gb,
            "total_ram_gb": self.hardware.total_ram_gb,
            "disk_free_gb": self.hardware.disk_free_gb,
            "battery_percent": bat_pct,
            "power_plugged": power_plug,
        }


# Global singleton instance
CONFIG = SystemConfig()
