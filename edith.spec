# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

block_cipher = None

added_files = [
    ('edith/ui/public', 'edith/ui/public'),
    ('edith/phone/tunnel_config.json', 'edith/phone'),
]

a = Analysis(
    ['edith_entry.py'],
    pathex=['.'],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        'pyttsx3.drivers',
        'pyttsx3.drivers.sapi5',
        'sounddevice',
        'numpy',
        'scipy',
        'PIL',
        'PIL.Image',
        'edith',
        'edith.main',
        'edith.core',
        'edith.providers',
        'edith.tools',
        'edith.voice',
        'edith.phone',
        'edith.ui',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest', 'unittest'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='EDITH',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='edith/ui/public/favicon.ico',
)
