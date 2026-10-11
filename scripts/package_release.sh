#!/usr/bin/env bash
# Build the distributable ZIP (source + APK + docs), excluding caches, secrets and model weights.
set -euo pipefail
cd "$(dirname "$0")/.."
VER=2.1.0; OUT=release/EDITH-$VER.zip
rm -rf release; mkdir -p release
python3 - "$OUT" <<'PY'
import os, sys, zipfile
out = sys.argv[1]
EXCL_DIRS = {"node_modules", ".next", ".git", "release", ".tools", "build", "__pycache__", "state"}
EXCL_FILES = {".env"}
n = 0
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in EXCL_DIRS]
        for f in files:
            p = os.path.join(root, f)[2:]
            if f in EXCL_FILES or f.endswith((".db", ".log", ".tsbuildinfo")) or f == "host_agent.json":
                continue
            z.write(p, "EDITH-2.1.0/" + p); n += 1
print("files:", n)
PY
SIZE=$(stat -c %s "$OUT")
python3 - "$OUT" "$SIZE" <<'PY'
import sys, zipfile, collections
out, size = sys.argv[1], int(sys.argv[2])
z = zipfile.ZipFile(out)
names = z.namelist()
assert size < 2 * 1024**3, "ZIP exceeds 2 GB"
assert any(n.endswith("dist/EDITH.apk") for n in names), "APK missing"
assert not any("/node_modules/" in n or n.endswith("/.env") for n in names), "forbidden content"
top = collections.Counter(n.split("/")[1] for n in names)
rep = [f"ZIP: {out}", f"Bytes: {size} ({size/1024/1024:.2f} MB) — limit 2147483648", f"Entries: {len(names)}", "Top-level entries:"] + [f"  {k}: {v}" for k, v in sorted(top.items())]
open("release/SIZE_REPORT.txt", "w").write("\n".join(rep) + "\n"); print("\n".join(rep))
PY
sha256sum "$OUT" | tee release/EDITH-$VER.zip.sha256
