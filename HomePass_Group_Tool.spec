# -*- mode: python ; coding: utf-8 -*-
# HomePass Group Tool - PyInstaller spec
# Build di Windows 64-bit dengan Python 3.14 64-bit karena .pyd adalah cp314-win_amd64.

import os
from PyInstaller.utils.hooks import collect_data_files, copy_metadata

# PyInstaller spec tidak selalu menyediakan __file__, terutama saat spec dieksekusi langsung.
# SPECPATH adalah path folder .spec dari PyInstaller; fallback ke HOMEPASS_BUILD_DIR lalu current folder.
BASE_DIR = os.path.abspath(
    globals().get("SPECPATH")
    or os.environ.get("HOMEPASS_BUILD_DIR")
    or os.getcwd()
)

PYD_FILE = os.path.join(BASE_DIR, "AK47_HOME_PASS_GROUP_TOOL_14INCH_SCROLLFIX.cp314-win_amd64.pyd")
ICON_FILE = os.path.join(BASE_DIR, "HomePass_Group_Tool_icon_all_sizes.ico")
LOGO_FILE = os.path.join(BASE_DIR, "LOGO_APLIKASI.png")
VERSION_FILE = os.path.join(BASE_DIR, "version_info.txt")

for required_file in [PYD_FILE, ICON_FILE, LOGO_FILE, VERSION_FILE]:
    if not os.path.exists(required_file):
        raise FileNotFoundError(f"File wajib tidak ditemukan: {required_file}")

customtkinter_datas = []
try:
    customtkinter_datas += collect_data_files("customtkinter")
    customtkinter_datas += copy_metadata("customtkinter")
except Exception:
    pass

block_cipher = None

a = Analysis(
    [os.path.join(BASE_DIR, "launcher.py")],
    pathex=[BASE_DIR],
    binaries=[
        (PYD_FILE, "."),
    ],
    datas=[
        (ICON_FILE, "."),
        (LOGO_FILE, "."),
    ] + customtkinter_datas,
    hiddenimports=[
        "AK47_HOME_PASS_GROUP_TOOL_14INCH_SCROLLFIX",
        "customtkinter",
        "darkdetect",
        "packaging",
        "tkinter",
        "tkinter.filedialog",
        "tkinter.messagebox",
        "tkinter.ttk",
        "xml.etree.ElementTree",
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
    name="HomePass Group Tool",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON_FILE,
    version=VERSION_FILE,
)
