# launcher.py
# Entry point untuk membungkus modul .pyd menjadi .exe PyInstaller.
# Modul .pyd yang digunakan: AK47_HOME_PASS_GROUP_TOOL_14INCH_SCROLLFIX.cp314-win_amd64.pyd

from __future__ import annotations

import ctypes
import os
import sys
import traceback

APP_NAME = "HomePass Group Tool"
APP_USER_MODEL_ID = "AK47.HomePassGroupTool.1"
ICON_FILE = "HomePass_Group_Tool_icon_all_sizes.ico"


def resource_path(relative_path: str) -> str:
    """Ambil path file saat running normal maupun saat sudah menjadi PyInstaller onefile."""
    base_path = getattr(sys, "_MEIPASS", os.path.abspath(os.path.dirname(__file__)))
    return os.path.join(base_path, relative_path)


def set_windows_taskbar_icon() -> None:
    """Agar icon aplikasi muncul benar di taskbar Windows."""
    if os.name != "nt":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:
        pass


def show_error_dialog(message: str) -> None:
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(APP_NAME, message)
        root.destroy()
    except Exception:
        print(message)


def main() -> None:
    set_windows_taskbar_icon()

    # Import sengaja dibuat di dalam main agar error bisa ditampilkan dengan rapi.
    from AK47_HOME_PASS_GROUP_TOOL_14INCH_SCROLLFIX import HomepassedBoundaryGUI

    app = HomepassedBoundaryGUI()

    # Set icon window; icon .exe tetap diatur dari file .spec PyInstaller.
    icon_path = resource_path(ICON_FILE)
    if os.path.exists(icon_path):
        try:
            app.iconbitmap(icon_path)
        except Exception:
            pass
        try:
            app.wm_iconbitmap(icon_path)
        except Exception:
            pass

    app.mainloop()


if __name__ == "__main__":
    try:
        main()
    except BaseException as exc:
        error_text = traceback.format_exc()
        try:
            with open("HomePass_error_log.txt", "w", encoding="utf-8") as f:
                f.write(error_text)
        except Exception:
            pass
        show_error_dialog(
            "Aplikasi gagal dibuka.\n\n"
            f"Detail singkat: {exc}\n\n"
            "Cek file HomePass_error_log.txt untuk detail error."
        )
        raise
