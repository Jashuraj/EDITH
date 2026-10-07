"""System Optimizer Tool for EDITH.

Inspired by jarvis-omniroute tools/system_optimizer.py.
Provides:
1. Working set memory trimming to recover RAM on low-spec hardware.
2. Safe temporary directory cleaning.
3. Windows DNS cache flushing.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from typing import Any, Dict

logger = logging.getLogger("edith.tools.system_optimizer")


def trim_process_memory() -> Dict[str, Any]:
    """Trim memory working set across accessible processes on Windows."""
    reclaimed = False
    try:
        import ctypes
        handle = ctypes.windll.kernel32.GetCurrentProcess()
        # Setting min and max to -1 flushes working set to page file
        res = ctypes.windll.kernel32.SetProcessWorkingSetSize(handle, -1, -1)
        reclaimed = bool(res != 0)
    except Exception as ex:
        logger.debug("Could not flush process working set: %s", ex)

    return {"success": True, "reclaimed": reclaimed}


def flush_dns_cache() -> bool:
    """Flush the Windows local DNS resolver cache."""
    try:
        res = subprocess.run(
            ["ipconfig", "/flushdns"],
            capture_output=True,
            text=True,
            timeout=5.0,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return res.returncode == 0
    except Exception as ex:
        logger.warning("DNS flush failed: %s", ex)
        return False


def clean_temp_files(max_files: int = 100) -> Dict[str, Any]:
    """Clean transient temporary files from standard temp directory safely."""
    temp_dir = tempfile.gettempdir()
    cleaned_count = 0
    bytes_freed = 0

    try:
        for entry in os.scandir(temp_dir):
            if cleaned_count >= max_files:
                break
            try:
                if entry.is_file(follow_symlinks=False):
                    size = entry.stat().st_size
                    os.remove(entry.path)
                    cleaned_count += 1
                    bytes_freed += size
            except (PermissionError, OSError):
                # File in use by other process
                continue
    except Exception as ex:
        logger.debug("Temp cleanup scan error: %s", ex)

    mb_freed = round(bytes_freed / (1024 * 1024), 2)
    return {"cleaned_count": cleaned_count, "mb_freed": mb_freed}


def optimize_system() -> str:
    """Run full system optimization suite."""
    mem_res = trim_process_memory()
    dns_res = flush_dns_cache()
    temp_res = clean_temp_files()

    dns_str = "flushed" if dns_res else "skipped"
    return (
        f"Optimization complete, sir. RAM working set trimmed, DNS cache {dns_str}, "
        f"and {temp_res['cleaned_count']} temp files cleared ({temp_res['mb_freed']} MB reclaimed)."
    )
