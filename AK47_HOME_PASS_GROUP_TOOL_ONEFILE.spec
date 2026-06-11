# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

app_name = "HomePass Group Tool"
source_file = "AK47_HOME_PASS_GROUP_TOOL_EXE_READY.py"
icon_file = "LOGO_APLIKASI_ALL_SIZE.ico"

datas = [(icon_file, ".")]
datas += collect_data_files("customtkinter")

hiddenimports = []
hiddenimports += collect_submodules("customtkinter")


a = Analysis(
    [source_file],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file,
)
