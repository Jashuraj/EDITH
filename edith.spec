# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['edith/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('edith/ui/public', 'edith/ui/public'),
        ('edith/ui/state', 'edith/ui/state'),
        ('edith/phone/tunnel_config.json', 'edith/phone'),
    ],
    hiddenimports=[
        'sounddevice',
        'numpy',
        'edith',
        'edith.core.logger',
        'edith.core.undo',
        'edith.core.confirm',
        'edith.core.echo',
        'edith.tools.mouse_controller',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='EDITH',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
