"""Entry point WaifuUpscaler. Jalankan dengan: python -m app.main"""
from __future__ import annotations

import ctypes
import sys


def main() -> None:
    if sys.platform == "win32":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    from .config import OUTPUT_DIR
    from .gui import App, create_root

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    root = create_root()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
