"""Standalone Windows Executable Entrypoint for EDITH AI Assistant."""

import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

# Adjust path for PyInstaller bundle
if getattr(sys, "frozen", False):
    base_dir = Path(sys._MEIPASS)
    os.chdir(sys._MEIPASS)
else:
    base_dir = Path(__file__).resolve().parent

from edith.main import serve_all


def _launch_browser() -> None:
    time.sleep(1.5)
    try:
        webbrowser.open("http://127.0.0.1:8794")
    except Exception:
        pass


if __name__ == "__main__":
    # Launch browser HUD in parallel
    threading.Thread(target=_launch_browser, daemon=True).start()
    # Serve all subsystems (UI on 8794, Phone Gateway on 8795)
    serve_all(ui_port=8794, phone_port=8795)
