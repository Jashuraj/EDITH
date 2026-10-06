"""Autonomous Android APK Builder and Signer for EDITH.

Packages the Spider-Man HUD PWA into an installable Android APK with:
- Spider-Man launcher icons (all densities)
- Embedded mobile assets in assets/
- Signed with Android v1 PKCS#7 signature (CERT.RSA, CERT.SF, MANIFEST.MF)
"""

import base64
import datetime
import hashlib
import io
import os
import shutil
import sys
import zipfile
from pathlib import Path
from PIL import Image

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs7
from cryptography.x509.oid import NameOID

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Import icon renderer
from scripts.render_icons import draw_spiderman_icon
DIST_DIR = BASE_DIR / "dist"
DIST_MOBILE_DIR = BASE_DIR / "dist_mobile"
MOBILE_ASSETS = BASE_DIR / "edith" / "ui" / "public" / "mobile"
TEMPLATE_APK = DIST_MOBILE_DIR / "webapps_template.apk"


def ensure_template_apk():
    """Ensure template APK exists, downloading if necessary."""
    if TEMPLATE_APK.exists() and TEMPLATE_APK.stat().st_size > 1000000:
        return TEMPLATE_APK

    import urllib.request
    url = "https://github.com/tobykurien/WebApps/releases/download/v4.3/release.apk"
    print("Downloading Android WebView base template...")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        TEMPLATE_APK.write_bytes(r.read())
    return TEMPLATE_APK


def build_edith_apk():
    """Construct, patch, and sign EDITH.apk."""
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    DIST_MOBILE_DIR.mkdir(parents=True, exist_ok=True)
    template_path = ensure_template_apk()

    # Pre-render Spider-Man icons for all Android densities
    icon_sizes = {
        "mdpi": 48,
        "hdpi": 72,
        "xhdpi": 96,
        "xxhdpi": 144,
        "xxxhdpi": 192,
    }
    rendered_icons = {}
    for density, size in icon_sizes.items():
        img = draw_spiderman_icon(size)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        rendered_icons[density] = buf.getvalue()

    apk_files = {}

    # 1. Read files from template APK (excluding old META-INF signatures)
    with zipfile.ZipFile(template_path, "r") as zf:
        for info in zf.infolist():
            if info.filename.startswith("META-INF/"):
                continue

            content = zf.read(info.filename)

            # Patch launcher icons with Spider-Man icon
            replaced = False
            for density, icon_bytes in rendered_icons.items():
                if f"mipmap-{density}" in info.filename and "ic_launcher" in info.filename:
                    apk_files[info.filename] = icon_bytes
                    replaced = True
                    break

            if not replaced:
                # Patch resources.arsc string table for branding
                if info.filename == "resources.arsc":
                    # Patch default app title
                    content = content.replace(b"WebApps\x00\x10\x10", b"E.D.I.T.H.\x00")
                apk_files[info.filename] = content

    # 2. Inject EDITH mobile assets into assets/edith/
    for file in MOBILE_ASSETS.rglob("*"):
        if file.is_file():
            rel_name = f"assets/edith/{file.relative_to(MOBILE_ASSETS).as_posix()}"
            apk_files[rel_name] = file.read_bytes()

    # 3. Generate Android v1 Signing Manifests
    manifest_lines = [
        "Manifest-Version: 1.0",
        "Built-By: EDITH Autonomous Compiler",
        "Created-By: 1.0 (Android)",
        "",
    ]
    sf_lines = [
        "Signature-Version: 1.0",
        "Created-By: 1.0 (Android)",
        "",
    ]

    # Calculate SHA-256 for all payload files
    sorted_filenames = sorted(apk_files.keys())
    for fname in sorted_filenames:
        data = apk_files[fname]
        file_sha256 = base64.b64encode(hashlib.sha256(data).digest()).decode("ascii")

        entry_manifest = (
            f"Name: {fname}\r\n"
            f"SHA-256-Digest: {file_sha256}\r\n"
            f"\r\n"
        )
        manifest_lines.append(f"Name: {fname}")
        manifest_lines.append(f"SHA-256-Digest: {file_sha256}")
        manifest_lines.append("")

        entry_sha256 = base64.b64encode(hashlib.sha256(entry_manifest.encode("utf-8")).digest()).decode("ascii")
        sf_lines.append(f"Name: {fname}")
        sf_lines.append(f"SHA-256-Digest: {entry_sha256}")
        sf_lines.append("")

    manifest_bytes = ("\r\n".join(manifest_lines) + "\r\n").encode("utf-8")
    manifest_sha256 = base64.b64encode(hashlib.sha256(manifest_bytes).digest()).decode("ascii")

    sf_header = [
        "Signature-Version: 1.0",
        "Created-By: 1.0 (Android)",
        f"SHA-256-Digest-Manifest: {manifest_sha256}",
        "",
    ]
    sf_full = "\r\n".join(sf_header + sf_lines[3:]) + "\r\n"
    sf_bytes = sf_full.encode("utf-8")

    # 4. Generate RSA Key, Certificate, and PKCS#7 Signature
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "EDITH Mobile"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Stark Industries"),
    ])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1))
        .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=10000))
        .sign(key, hashes.SHA256())
    )

    builder = (
        pkcs7.PKCS7SignatureBuilder()
        .set_data(sf_bytes)
        .add_signer(cert, key, hashes.SHA256())
    )
    rsa_bytes = builder.sign(serialization.Encoding.DER, [pkcs7.PKCS7Options.Binary])

    # 5. Add META-INF signatures
    apk_files["META-INF/MANIFEST.MF"] = manifest_bytes
    apk_files["META-INF/CERT.SF"] = sf_bytes
    apk_files["META-INF/CERT.RSA"] = rsa_bytes

    # 6. Write final signed APKs
    target_apk_dist = DIST_DIR / "EDITH.apk"
    target_apk_mobile = DIST_MOBILE_DIR / "EDITH.apk"

    for target in [target_apk_dist, target_apk_mobile]:
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zout:
            for fname in sorted(apk_files.keys()):
                zout.writestr(fname, apk_files[fname])

    print(f"Successfully generated signed Android APK: {target_apk_dist}")
    print(f"APK Size: {target_apk_dist.stat().st_size} bytes")


if __name__ == "__main__":
    build_edith_apk()
