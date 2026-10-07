"""Native Android APK Builder for EDITH Operating System.

Builds a pure native Android application (Zero browser chrome / Zero URL bars)
with immersive fullscreen Spider-Man HUD and seamless remote connection to EDITH laptop mainframe.
"""

from __future__ import annotations

import io
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from scripts.render_icons import draw_spiderman_icon

DIST_DIR = BASE_DIR / "dist"
DIST_MOBILE_DIR = BASE_DIR / "dist_mobile"
BUILD_DIR = BASE_DIR / "build" / "android_native"
MOBILE_ASSETS = BASE_DIR / "edith" / "ui" / "public" / "mobile"

TOOLS_DIR = BASE_DIR / "scripts" / "tools"
SDK_TOOLS_DIR = TOOLS_DIR / "android_sdk"
JAVA_EXE = TOOLS_DIR / "jre" / "jdk-17.0.20.1+1-jre" / "bin" / "java.exe"
SIGNER_JAR = TOOLS_DIR / "uber-apk-signer.jar"

AAPT2_EXE = SDK_TOOLS_DIR / "aapt2.exe"
ANDROID_JAR = SDK_TOOLS_DIR / "android.jar"
ECJ_JAR = SDK_TOOLS_DIR / "ecj.jar"
R8_JAR = SDK_TOOLS_DIR / "r8.jar"


def ensure_tools() -> None:
    """Verify all compilers, packaging tools, and Android SDK jars are available."""
    SDK_TOOLS_DIR.mkdir(parents=True, exist_ok=True)

    required_downloads = [
        (ECJ_JAR, "https://repo1.maven.org/maven2/org/eclipse/jdt/ecj/3.33.0/ecj-3.33.0.jar"),
        (R8_JAR, "https://dl.google.com/dl/android/maven2/com/android/tools/r8/8.2.33/r8-8.2.33.jar"),
        (SDK_TOOLS_DIR / "aapt2.jar", "https://dl.google.com/dl/android/maven2/com/android/tools/build/aapt2/8.2.2-10154469/aapt2-8.2.2-10154469-windows.jar"),
        (ANDROID_JAR, "https://raw.githubusercontent.com/Sable/android-platforms/master/android-30/android.jar"),
    ]

    for dest, url in required_downloads:
        if not dest.exists() or dest.stat().st_size < 100000:
            print(f"Downloading required build component: {dest.name}...")
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=120) as r:
                dest.write_bytes(r.read())

    if not AAPT2_EXE.exists():
        with zipfile.ZipFile(SDK_TOOLS_DIR / "aapt2.jar", "r") as zf:
            AAPT2_EXE.write_bytes(zf.read("aapt2.exe"))

    if not JAVA_EXE.exists():
        raise FileNotFoundError(f"Java runtime not found at: {JAVA_EXE}")

    if not SIGNER_JAR.exists():
        raise FileNotFoundError(f"uber-apk-signer.jar not found at: {SIGNER_JAR}")


def prepare_project_files() -> None:
    """Generate Android project source, manifest, icons, and resources."""
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    # Pre-populate server_config.json for Android APK
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        detected_ip = s.getsockname()[0]
        s.close()
    except Exception:
        detected_ip = "127.0.0.1"

    tunnel_url = None
    try:
        from edith.phone.tunnel import TUNNEL_MANAGER
        tunnel_url = TUNNEL_MANAGER.get_active_url()
    except Exception:
        pass

    import json
    cfg_path = MOBILE_ASSETS / "server_config.json"
    cfg_path.write_text(
        json.dumps({
            "local_ip": detected_ip,
            "local_url": f"http://{detected_ip}:8794",
            "cloud_url": tunnel_url,
            "ui_port": 8794,
            "phone_port": 8795
        }, indent=2),
        encoding="utf-8"
    )

    res_dir = BUILD_DIR / "res"
    (res_dir / "values").mkdir(parents=True, exist_ok=True)
    (BUILD_DIR / "bin").mkdir(parents=True, exist_ok=True)

    # 1. Render Spider-Man icons for all densities
    densities = {
        "mdpi": 48,
        "hdpi": 72,
        "xhdpi": 96,
        "xxhdpi": 144,
        "xxxhdpi": 192,
    }
    for density, size in densities.items():
        folder = res_dir / f"mipmap-{density}"
        folder.mkdir(parents=True, exist_ok=True)
        img = draw_spiderman_icon(size)
        img.save(folder / "ic_launcher.png", format="PNG")

    # Default mipmap fallback
    (res_dir / "mipmap").mkdir(parents=True, exist_ok=True)
    draw_spiderman_icon(192).save(res_dir / "mipmap" / "ic_launcher.png", format="PNG")

    # 2. String and Theme Resources
    strings_xml = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<resources>\n'
        '    <string name="app_name">EDITH</string>\n'
        '</resources>\n'
    )
    (res_dir / "values" / "strings.xml").write_text(strings_xml, encoding="utf-8")

    styles_xml = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<resources>\n'
        '    <style name="AppTheme" parent="@android:style/Theme.NoTitleBar.Fullscreen">\n'
        '        <item name="android:windowNoTitle">true</item>\n'
        '        <item name="android:windowFullscreen">true</item>\n'
        '        <item name="android:windowBackground">@android:color/black</item>\n'
        '    </style>\n'
        '</resources>\n'
    )
    (res_dir / "values" / "styles.xml").write_text(styles_xml, encoding="utf-8")

    # 3. Network Security Config (Permit cleartext LAN HTTP on Android 9-14)
    (res_dir / "xml").mkdir(parents=True, exist_ok=True)
    net_sec_xml = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<network-security-config>\n'
        '    <base-config cleartextTrafficPermitted="true">\n'
        '        <trust-anchors>\n'
        '            <certificates src="system" />\n'
        '            <certificates src="user" />\n'
        '        </trust-anchors>\n'
        '    </base-config>\n'
        '</network-security-config>\n'
    )
    (res_dir / "xml" / "network_security_config.xml").write_text(net_sec_xml, encoding="utf-8")

    # 4. AndroidManifest.xml
    manifest_xml = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<manifest xmlns:android="http://schemas.android.com/apk/res/android"\n'
        '    package="com.edith.ai"\n'
        '    android:versionCode="2"\n'
        '    android:versionName="2.0.0">\n'
        '\n'
        '    <uses-sdk\n'
        '        android:minSdkVersion="21"\n'
        '        android:targetSdkVersion="33" />\n'
        '\n'
        '    <uses-permission android:name="android.permission.INTERNET" />\n'
        '    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />\n'
        '    <uses-permission android:name="android.permission.RECORD_AUDIO" />\n'
        '    <uses-permission android:name="android.permission.MODIFY_AUDIO_SETTINGS" />\n'
        '    <uses-permission android:name="android.permission.VIBRATE" />\n'
        '\n'
        '    <application\n'
        '        android:label="@string/app_name"\n'
        '        android:icon="@mipmap/ic_launcher"\n'
        '        android:roundIcon="@mipmap/ic_launcher"\n'
        '        android:hardwareAccelerated="true"\n'
        '        android:usesCleartextTraffic="true"\n'
        '        android:networkSecurityConfig="@xml/network_security_config"\n'
        '        android:theme="@style/AppTheme">\n'
        '\n'
        '        <activity\n'
        '            android:name="com.edith.ai.MainActivity"\n'
        '            android:exported="true"\n'
        '            android:screenOrientation="fullSensor"\n'
        '            android:configChanges="orientation|screenSize|keyboardHidden"\n'
        '            android:windowSoftInputMode="adjustResize"\n'
        '            android:theme="@style/AppTheme">\n'
        '            <intent-filter>\n'
        '                <action android:name="android.intent.action.MAIN" />\n'
        '                <category android:name="android.intent.category.LAUNCHER" />\n'
        '            </intent-filter>\n'
        '        </activity>\n'
        '    </application>\n'
        '</manifest>\n'
    )
    (BUILD_DIR / "AndroidManifest.xml").write_text(manifest_xml, encoding="utf-8")

    # 4. Native MainActivity.java
    src_dir = BUILD_DIR / "src" / "com" / "edith" / "ai"
    src_dir.mkdir(parents=True, exist_ok=True)

    java_code = (
        'package com.edith.ai;\n\n'
        'import android.app.Activity;\n'
        'import android.os.Build;\n'
        'import android.os.Bundle;\n'
        'import android.view.View;\n'
        'import android.view.Window;\n'
        'import android.view.WindowManager;\n'
        'import android.webkit.PermissionRequest;\n'
        'import android.webkit.WebChromeClient;\n'
        'import android.webkit.WebSettings;\n'
        'import android.webkit.WebView;\n'
        'import android.webkit.WebViewClient;\n'
        'import android.webkit.SslErrorHandler;\n'
        'import android.net.http.SslError;\n'
        'import android.util.Log;\n'
        'import android.webkit.ConsoleMessage;\n'
        'import android.Manifest;\n'
        'import android.content.pm.PackageManager;\n\n'
        'public class MainActivity extends Activity {\n'
        '    private WebView webView;\n\n'
        '    @Override\n'
        '    protected void onCreate(Bundle savedInstanceState) {\n'
        '        super.onCreate(savedInstanceState);\n\n'
        '        requestWindowFeature(Window.FEATURE_NO_TITLE);\n'
        '        getWindow().setFlags(\n'
        '            WindowManager.LayoutParams.FLAG_FULLSCREEN,\n'
        '            WindowManager.LayoutParams.FLAG_FULLSCREEN\n'
        '        );\n'
        '        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);\n\n'
        '        hideSystemUI();\n\n'
        '        webView = new WebView(this);\n'
        '        setContentView(webView);\n\n'
        '        WebSettings settings = webView.getSettings();\n'
        '        settings.setJavaScriptEnabled(true);\n'
        '        settings.setDomStorageEnabled(true);\n'
        '        settings.setDatabaseEnabled(true);\n'
        '        settings.setMediaPlaybackRequiresUserGesture(false);\n'
        '        settings.setAllowFileAccess(true);\n'
        '        settings.setAllowContentAccess(true);\n'
        '        settings.setAllowFileAccessFromFileURLs(true);\n'
        '        settings.setAllowUniversalAccessFromFileURLs(true);\n'
        '        settings.setLoadsImagesAutomatically(true);\n'
        '        settings.setBlockNetworkImage(false);\n'
        '        settings.setBlockNetworkLoads(false);\n'
        '        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {\n'
        '            settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);\n'
        '        }\n\n'
        '        webView.setWebViewClient(new WebViewClient() {\n'
        '            @Override\n'
        '            public boolean shouldOverrideUrlLoading(WebView view, String url) {\n'
        '                return false;\n'
        '            }\n'
        '            @Override\n'
        '            public void onReceivedSslError(WebView view, SslErrorHandler handler, SslError error) {\n'
        '                handler.proceed();\n'
        '            }\n'
        '        });\n'
        '        webView.setWebChromeClient(new WebChromeClient() {\n'
        '            @Override\n'
        '            public boolean onConsoleMessage(ConsoleMessage cm) {\n'
        '                Log.d("EDITH_APP", cm.message() + " -- Line " + cm.lineNumber());\n'
        '                return true;\n'
        '            }\n'
        '            @Override\n'
        '            public void onPermissionRequest(final PermissionRequest request) {\n'
        '                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {\n'
        '                    request.grant(request.getResources());\n'
        '                }\n'
        '            }\n'
        '        });\n\n'
        '        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {\n'
        '            if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {\n'
        '                requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, 101);\n'
        '            }\n'
        '        }\n\n'
        '        webView.loadUrl("file:///android_asset/edith/index.html");\n'
        '    }\n\n'
        '    private void hideSystemUI() {\n'
        '        View decorView = getWindow().getDecorView();\n'
        '        decorView.setSystemUiVisibility(\n'
        '            View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY\n'
        '            | View.SYSTEM_UI_FLAG_LAYOUT_STABLE\n'
        '            | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION\n'
        '            | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN\n'
        '            | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION\n'
        '            | View.SYSTEM_UI_FLAG_FULLSCREEN\n'
        '        );\n'
        '    }\n\n'
        '    @Override\n'
        '    public void onWindowFocusChanged(boolean hasFocus) {\n'
        '        super.onWindowFocusChanged(hasFocus);\n'
        '        if (hasFocus) {\n'
        '            hideSystemUI();\n'
        '        }\n'
        '    }\n\n'
        '    @Override\n'
        '    public void onBackPressed() {\n'
        '        if (webView != null && webView.canGoBack()) {\n'
        '            webView.goBack();\n'
        '        } else {\n'
        '            super.onBackPressed();\n'
        '        }\n'
        '    }\n'
        '}\n'
    )
    (src_dir / "MainActivity.java").write_text(java_code, encoding="utf-8")


def compile_native_apk() -> Path:
    """Compile and link resources, bytecode, DEX, and pack assets into signed APK."""
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    DIST_MOBILE_DIR.mkdir(parents=True, exist_ok=True)

    res_dir = BUILD_DIR / "res"
    bin_dir = BUILD_DIR / "bin"
    src_dir = BUILD_DIR / "src" / "com" / "edith" / "ai"

    # Step 1: AAPT2 compile resources
    print("Compiling Android resources with AAPT2...")
    subprocess.run(
        [
            str(AAPT2_EXE),
            "compile",
            "--dir", str(res_dir),
            "-o", str(BUILD_DIR / "res.zip"),
        ],
        check=True,
    )

    # Step 2: AAPT2 link to create initial APK
    print("Linking package with AAPT2...")
    subprocess.run(
        [
            str(AAPT2_EXE),
            "link",
            "-I", str(ANDROID_JAR),
            "--manifest", str(BUILD_DIR / "AndroidManifest.xml"),
            "-o", str(BUILD_DIR / "unaligned.apk"),
            str(BUILD_DIR / "res.zip"),
            "--auto-add-overlay",
        ],
        check=True,
    )

    # Step 3: ECJ Java compile
    print("Compiling MainActivity.java with ECJ compiler...")
    subprocess.run(
        [
            str(JAVA_EXE),
            "-jar", str(ECJ_JAR),
            "-cp", str(ANDROID_JAR),
            "-source", "1.8",
            "-target", "1.8",
            "-d", str(bin_dir),
            str(src_dir / "MainActivity.java"),
        ],
        check=True,
    )

    # Step 4: D8 Dex generation
    print("Generating classes.dex with D8...")
    class_files = [str(f) for f in bin_dir.rglob("*.class")]
    subprocess.run(
        [
            str(JAVA_EXE),
            "-cp", str(R8_JAR),
            "com.android.tools.r8.D8",
            "--lib", str(ANDROID_JAR),
            "--min-api", "21",
            "--output", str(bin_dir),
            *class_files,
        ],
        check=True,
    )

    # Step 5: Pack classes.dex and EDITH mobile assets into APK
    print("Injecting DEX and Spider-Man HUD assets into APK...")
    with zipfile.ZipFile(BUILD_DIR / "unaligned.apk", "a") as zf:
        zf.write(bin_dir / "classes.dex", "classes.dex")
        for asset_file in MOBILE_ASSETS.rglob("*"):
            if asset_file.is_file():
                arcname = f"assets/edith/{asset_file.relative_to(MOBILE_ASSETS).as_posix()}"
                zf.write(asset_file, arcname)

    # Step 6: Sign with uber-apk-signer (V1, V2, V3 + Zipalign)
    print("Signing APK with Android V1, V2, V3 schemes via uber-apk-signer...")
    target_apk = DIST_DIR / "EDITH.apk"
    target_apk_mobile = DIST_MOBILE_DIR / "EDITH.apk"

    # Copy to target before in-place signing
    shutil.copy2(BUILD_DIR / "unaligned.apk", target_apk)
    shutil.copy2(BUILD_DIR / "unaligned.apk", target_apk_mobile)

    subprocess.run(
        [
            str(JAVA_EXE),
            "-jar", str(SIGNER_JAR),
            "-a", str(target_apk), str(target_apk_mobile),
            "--allowResign",
            "--overwrite",
            "--verbose",
        ],
        check=True,
    )

    # Step 7: Verify signature
    print("Verifying signature and zipalign integrity...")
    subprocess.run(
        [
            str(JAVA_EXE),
            "-jar", str(SIGNER_JAR),
            "-y",
            "-a", str(target_apk),
        ],
        check=True,
    )

    print(f"\n=======================================================")
    print(f"  NATIVE EDITH.apk BUILT AND SIGNED SUCCESSFULLY!")
    print(f"  Path: {target_apk}")
    print(f"  Size: {target_apk.stat().st_size} bytes")
    print(f"=======================================================\n")
    return target_apk


def main():
    ensure_tools()
    prepare_project_files()
    compile_native_apk()


if __name__ == "__main__":
    main()
