import os
import sys
import traceback
from tkinter import messagebox

APP_TITLE = "HomePass Group Tool"
MODULE_NAME = "homepassed_boundary_fat_gui_prototype_v6_modern_ui"


def resource_path(relative_path: str) -> str:
    """Return path for normal run and PyInstaller onefile mode."""
    base_path = getattr(sys, "_MEIPASS", os.path.abspath(os.path.dirname(__file__)))
    return os.path.join(base_path, relative_path)


def main() -> None:
    try:
        import homepassed_boundary_fat_gui_prototype_v6_modern_ui as app_module

        if not hasattr(app_module, "HomepassedBoundaryGUI"):
            raise AttributeError("Class HomepassedBoundaryGUI tidak ditemukan di module .pyd")

        app = app_module.HomepassedBoundaryGUI()

        # Set window/taskbar icon when supported by tkinter/customtkinter.
        icon_file = resource_path("HomePass_all_sizes.ico")
        if os.path.exists(icon_file):
            try:
                app.iconbitmap(icon_file)
            except Exception:
                pass

        app.mainloop()

    except Exception as exc:
        err = traceback.format_exc()
        try:
            messagebox.showerror(
                "HomePass gagal dibuka",
                f"Aplikasi gagal dijalankan.\n\n{exc}\n\nDetail teknis:\n{err}",
            )
        except Exception:
            print(err)
        raise


if __name__ == "__main__":
    main()
