# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

APP_NAME = "HomePass_Group_Tool"
MODULE_PYD = "AK47_HP_GROUPING_ADVANCED_V6_MODERN_GUI.pyd"
ICON_FILE = "HomePass_all_size.ico"

customtkinter_datas = collect_data_files("customtkinter")
customtkinter_hidden = collect_submodules("customtkinter")

block_cipher = None

a = Analysis(
    ["run_homepass.py"],
    pathex=[os.path.abspath(".")],
    binaries=[(MODULE_PYD, ".")],
    datas=[(ICON_FILE, ".")] + customtkinter_datas,
    hiddenimports=["customtkinter", "tkinter", "tkinter.filedialog", "tkinter.messagebox", "tkinter.ttk"] + customtkinter_hidden,
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
