# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

block_cipher = None

APP_NAME = "HomePass_Group_Tool"
ICON_FILE = "HomePass_all_sizes.ico"
PYD_FILE = "homepassed_boundary_fat_gui_prototype_v6_modern_ui.pyd"

ctk_datas, ctk_binaries, ctk_hiddenimports = collect_all("customtkinter")

a = Analysis(
    ["main_launcher.py"],
    pathex=[],
    binaries=[
        (PYD_FILE, "."),
    ] + ctk_binaries,
    datas=[
        (ICON_FILE, "."),
        ("HomePass_logo_1024.png", "."),
    ] + ctk_datas,
    hiddenimports=ctk_hiddenimports + [
        "darkdetect",
        "packaging",
        "tkinter",
        "tkinter.filedialog",
        "tkinter.messagebox",
        "xml.etree.ElementTree",
        "zipfile",
        "threading",
        "pathlib",
        "tempfile",
        "shutil",
        "math",
        "webbrowser",
        "subprocess",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name=APP_NAME,
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
    icon=ICON_FILE,
)
