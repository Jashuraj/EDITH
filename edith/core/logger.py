"""EDITH Master Unified Logging and Telemetry System.

Writes all system events, runtime telemetry, tool invocations, and error traces
to edith/data/logs/edith.log with automatic log rotation and thread exception hooks.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys
import threading
import traceback
from typing import Optional

# Base directories
if getattr(sys, "frozen", False):
    _exe_dir = Path(sys.executable).resolve().parent
    if (_exe_dir.parent / "edith" / "data").exists():
        _DATA_DIR = _exe_dir.parent / "edith" / "data"
    elif (_exe_dir / "edith" / "data").exists():
        _DATA_DIR = _exe_dir / "edith" / "data"
    else:
        _DATA_DIR = _exe_dir / "data"
else:
    _CORE_DIR = Path(__file__).resolve().parent
    _DATA_DIR = _CORE_DIR.parent / "data"

_LOGS_DIR = _DATA_DIR / "logs"
LOG_FILE_PATH = _LOGS_DIR / "edith.log"

_LOGGING_INITIALIZED = False
_LOCK = threading.Lock()


def setup_logging(level: int = logging.INFO) -> Path:
    """Initialize persistent unified logging to edith/data/logs/edith.log."""
    global _LOGGING_INITIALIZED
    with _LOCK:
        if _LOGGING_INITIALIZED:
            return LOG_FILE_PATH

        _LOGS_DIR.mkdir(parents=True, exist_ok=True)

        root = logging.getLogger()
        root.setLevel(level)

        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # 1. Rotating File Handler (10 MB per file, max 5 backups)
        file_handler = RotatingFileHandler(
            filename=str(LOG_FILE_PATH),
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

        # 2. Console Stream Handler (if not already present)
        has_console = any(isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler) for h in root.handlers)
        if not has_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)
            console_handler.setFormatter(formatter)
            root.addHandler(console_handler)

        # 3. Global Exception Hooks
        def _global_excepthook(exc_type, exc_value, exc_traceback):
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return
            err_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
            logging.critical("Uncaught system exception:\n%s", err_msg)

        sys.excepthook = _global_excepthook

        def _threading_excepthook(args):
            if issubclass(args.exc_type, KeyboardInterrupt):
                return
            err_msg = "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback))
            logging.critical("Uncaught thread exception in [%s]:\n%s", args.thread.name, err_msg)

        if hasattr(threading, "excepthook"):
            threading.excepthook = _threading_excepthook

        _LOGGING_INITIALIZED = True
        logging.info("EDITH Unified Logging System active. Log path: %s", LOG_FILE_PATH)
        return LOG_FILE_PATH


def get_recent_logs(max_lines: int = 150, lines: Optional[int] = None) -> str:
    """Read and return the most recent log entries."""
    count = lines if lines is not None else max_lines
    if not LOG_FILE_PATH.exists():
        return "No log records found."
    try:
        with open(LOG_FILE_PATH, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
            return "".join(all_lines[-count:])
    except Exception as e:
        return f"Error reading logs: {e}"
