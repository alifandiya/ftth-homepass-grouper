"""
Launcher untuk module Cython AK47_HP_GROUPING_ADVANCED_V6_MODERN_GUI.pyd.
File ini dipakai PyInstaller agar .pyd bisa berjalan sebagai aplikasi Windows .exe.
"""
import os
import sys
import traceback
from tkinter import messagebox

APP_ICON = "HomePass_all_size.ico"
MODULE_NAME = "AK47_HP_GROUPING_ADVANCED_V6_MODERN_GUI"


def base_path() -> str:
    """Lokasi file saat mode biasa atau saat sudah dibundel PyInstaller onefile."""
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))


def prepare_runtime_path() -> None:
    base = base_path()
    if base not in sys.path:
        sys.path.insert(0, base)


def main() -> None:
    prepare_runtime_path()
    try:
        import AK47_HP_GROUPING_ADVANCED_V6_MODERN_GUI as app_module

        app = app_module.HomepassedBoundaryGUI()

        icon_path = os.path.join(base_path(), APP_ICON)
        if os.path.exists(icon_path):
            try:
                app.iconbitmap(icon_path)
            except Exception:
                # Tidak fatal: icon exe tetap diatur dari PyInstaller.
                pass

        app.mainloop()
    except Exception as exc:
        detail = traceback.format_exc()
        try:
            messagebox.showerror("HomePass gagal dibuka", f"{exc}\n\nDetail:\n{detail}")
        except Exception:
            print(detail)
        raise


if __name__ == "__main__":
    main()
