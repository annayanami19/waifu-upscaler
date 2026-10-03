"""Entry point WaifuUpscaler. Jalankan dengan: python -m app.main"""
from __future__ import annotations

import ctypes
import sys


def _set_app_user_model_id() -> None:
    """Windows: identitas taskbar sendiri, agar ikon aplikasi dipakai (bukan ikon Python).

    Tanpa ini, Windows mengelompokkan jendela ke python.exe dan taskbar
    menampilkan ikon Python meskipun title bar sudah memakai icon.ico.
    """
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("WaifuUpscaler.App")
    except Exception:
        pass


def main() -> None:
    if sys.platform == "win32":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    _set_app_user_model_id()
    from .config import OUTPUT_DIR
    from .gui import App, create_root

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    root = create_root()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
