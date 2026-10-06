"""Mobile Application Package & Distribution Generator for EDITH.

Packages the PWA assets into a standalone mobile distribution bundle.
"""

import shutil
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MOBILE_SRC = BASE_DIR / "edith" / "ui" / "public" / "mobile"
DIST_DIR = BASE_DIR / "dist_mobile"


def package_mobile_app():
    """Package mobile web application for Android / PWA distribution."""
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = DIST_DIR / "edith_spiderman_mobile.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in MOBILE_SRC.rglob("*"):
            if file.is_file():
                arcname = file.relative_to(MOBILE_SRC)
                zf.write(file, arcname)

    print(f"Mobile distribution archive created at: {zip_path}")
    print(f"Total files packaged: {len(list(MOBILE_SRC.rglob('*')))}")


if __name__ == "__main__":
    package_mobile_app()
