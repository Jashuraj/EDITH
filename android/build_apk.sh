#!/usr/bin/env bash
# Reproducible EDITH companion APK build (Linux/macOS/WSL). Produces a DEBUG-signed APK.
# Tools are downloaded to $TOOLS (default: android/.tools). Usage: bash android/build_apk.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; A="$ROOT/android"; T="${TOOLS:-$A/.tools}"; B="$A/build"
VERSION_CODE=3; VERSION_NAME=2.1.0
mkdir -p "$T"; cd "$T"
dl() { [ -s "$1" ] || curl -fsSL --retry 3 -o "$1" "$2"; }
dl android.jar https://raw.githubusercontent.com/Sable/android-platforms/master/android-30/android.jar
dl aapt2.jar https://dl.google.com/dl/android/maven2/com/android/tools/build/aapt2/8.2.2-10154469/aapt2-8.2.2-10154469-linux.jar
dl r8.jar https://dl.google.com/dl/android/maven2/com/android/tools/r8/8.2.33/r8-8.2.33.jar
dl signer.jar https://github.com/patrickfav/uber-apk-signer/releases/download/v1.3.0/uber-apk-signer-1.3.0.jar
[ -x aapt2 ] || { unzip -o -q aapt2.jar aapt2; chmod +x aapt2; }
if [ -z "${JAVA_HOME:-}" ]; then
  [ -d jdk ] || { dl jdk.tgz "https://api.adoptium.net/v3/binary/latest/17/ga/linux/x64/jdk/hotspot/normal/eclipse"; mkdir jdk && tar xzf jdk.tgz -C jdk --strip-components=1; }
  JAVA_HOME="$T/jdk"
fi
J="$JAVA_HOME/bin"
rm -rf "$B"; mkdir -p "$B/assets/edith" "$B/gen" "$B/classes" "$B/dex" "$B/out"
cp -r "$ROOT/public/mobile/." "$B/assets/edith/"
"$T/aapt2" compile --dir "$A/res" -o "$B/res.zip"
"$T/aapt2" link -o "$B/unsigned.apk" -I "$T/android.jar" --manifest "$A/AndroidManifest.xml" --java "$B/gen" \
  -A "$B/assets" "$B/res.zip" --min-sdk-version 21 --target-sdk-version 33 --version-code $VERSION_CODE --version-name $VERSION_NAME
"$J/javac" -nowarn -source 8 -target 8 -bootclasspath "$T/android.jar" -classpath "$T/android.jar" -d "$B/classes" \
  $(find "$A/src" "$B/gen" -name '*.java') 2>&1 | grep -v "warning" || true
"$J/java" -cp "$T/r8.jar" com.android.tools.r8.D8 --release --min-api 21 --lib "$T/android.jar" --output "$B/dex" $(find "$B/classes" -name '*.class')
(cd "$B/dex" && zip -q -j "$B/unsigned.apk" classes.dex)
"$J/java" -jar "$T/signer.jar" -a "$B/unsigned.apk" -o "$B/out" --allowResign >/dev/null
OUT=$(ls "$B"/out/*.apk | head -1)
mkdir -p "$ROOT/dist"; cp "$OUT" "$ROOT/dist/EDITH.apk"
"$J/java" -jar "$T/signer.jar" -a "$ROOT/dist/EDITH.apk" --onlyVerify | grep -E "VERIFY|signature|Subject|SHA256|scheme|zipalign" | head -20
sha256sum "$ROOT/dist/EDITH.apk" | tee "$ROOT/dist/EDITH.apk.sha256"
"$T/aapt2" dump badging "$ROOT/dist/EDITH.apk" | head -3
