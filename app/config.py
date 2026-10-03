"""Konfigurasi aplikasi: konstanta path + persistence settings.json ala config.json."""
from __future__ import annotations

import json
from pathlib import Path

# Sumber tunggal identitas & versi: app/__init__.py (jangan duplikasi di sini).
from . import APP_NAME, APP_VERSION  # noqa: F401

ROOT_DIR = Path(__file__).resolve().parent.parent
TOOLS_DIR = ROOT_DIR / "tools"
OUTPUT_DIR = ROOT_DIR / "output"
CONFIG_PATH = ROOT_DIR / "config.json"

ASSETS_DIR = Path(__file__).resolve().parent / "assets"  # app/assets
ICON_ICO = ASSETS_DIR / "icon.ico"   # jendela & taskbar Windows (multi-ukuran)
ICON_PNG = ASSETS_DIR / "icon.png"   # fallback lintas platform (iconphoto)

DEFAULTS = {
    "engine": "waifu2x",
    "model_waifu2x": "models-cunet",
    "model_realcugan": "models-se",
    "model_realesrgan": "realesr-animevideov3",
    "scale": 2,
    "denoise": 0,
    "tile": 0,               # 0 = auto
    "gpu": "auto",           # "auto" | "0" | "1" | "-1" (cpu)
    "tta": False,
    "format": "png",         # png | jpg | webp
    "quality": 90,
    "output_mode": "custom",  # "source" | "custom"
    "output_dir": "",         # "" -> pakai OUTPUT_DIR bawaan
    "suffix": "_upscaled",
    "subfolders": True,       # scan folder secara rekursif
    "skip_existing": True,
    "auto_open": False,       # buka folder output setelah antrean selesai
    "window_w": 1150,         # ukuran & posisi jendela terakhir
    "window_h": 820,
    "window_zoomed": False,
    "view_mode": "detail",    # tampilan daftar: detail | small | medium | large | xlarge
}


def load_config() -> dict:
    cfg = dict(DEFAULTS)
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return cfg
    if isinstance(data, dict):
        for key in DEFAULTS:
            if key in data:
                cfg[key] = data[key]
    return cfg


def save_config(cfg: dict) -> None:
    payload = {k: cfg.get(k, DEFAULTS[k]) for k in DEFAULTS}
    try:
        CONFIG_PATH.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
            newline="\n",
        )
    except Exception:
        pass
