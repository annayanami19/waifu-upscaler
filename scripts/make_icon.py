"""Generator ikon aplikasi WaifuUpscaler — bunga sakura di panel gelap.

Jalankan: .venv/Scripts/python.exe scripts/make_icon.py

Output (aman dijalankan ulang, hasil deterministik):
  app/assets/icon.ico  — 16/24/32/48/64/128/256 px untuk window & taskbar Windows
  app/assets/icon.png  — 256 px untuk fallback lintas platform (iconphoto)

Palet mengikuti tema GUI di app/gui.py agar ikon menyatu dengan aplikasi.
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

SIZE = 1024
CENTER = SIZE / 2

# --- Palet (samakan dengan C[] di app/gui.py) ---
BG_TOP = (35, 38, 51, 255)         # #232633 (panel2)
BG_BOTTOM = (20, 21, 26, 255)      # #14151a (bg)
BORDER = (130, 170, 255, 255)      # #82aaff (accent)
PETAL = (255, 179, 193, 255)       # #ffb3c1 — kelopak sakura
PETAL_DEEP = (231, 122, 149, 255)  # #e77a95 — pangkal kelopak
PETAL_HL = (255, 214, 222, 255)    # #ffd6de — highlight
CORE = (255, 217, 125, 255)        # #ffd97d — inti bunga
CORE_RING = (232, 184, 75, 255)    # #e8b84b
GLOW = (130, 170, 255, 36)         # halo accent transparan
SPARKLE = (255, 255, 255, 215)


def _lerp(a: tuple, b: tuple, t: float) -> tuple:
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def _background() -> Image.Image:
    """Panel gelap rounded dengan gradasi vertikal + garis accent."""
    grad = Image.new("RGB", (1, SIZE))
    for y in range(SIZE):
        grad.putpixel((0, y), _lerp(BG_TOP, BG_BOTTOM, y / (SIZE - 1))[:3])
    grad = grad.resize((SIZE, SIZE), Image.Resampling.NEAREST)

    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, SIZE - 1, SIZE - 1), radius=212, fill=255)

    bg = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    bg.paste(grad, (0, 0), mask)
    ImageDraw.Draw(bg).rounded_rectangle((10, 10, SIZE - 11, SIZE - 11),
                                         radius=202, outline=BORDER, width=18)
    return bg


def _petal() -> Image.Image:
    """Satu kelopak menghadap ke atas (pusat bunga = CENTER, CENTER)."""
    layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.ellipse((CENTER - 122, 96, CENTER + 122, CENTER), fill=PETAL)           # badan kelopak
    d.ellipse((CENTER - 96, 300, CENTER + 96, CENTER + 10), fill=PETAL_DEEP)  # pangkal lebih tua
    d.ellipse((CENTER - 62, 148, CENTER + 62, 294), fill=PETAL_HL)            # highlight
    d.ellipse((CENTER - 62, 32, CENTER + 62, 156), fill=(0, 0, 0, 0))         # lekuk ujung
    return layer


def _flower() -> Image.Image:
    flower = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    base = _petal()
    for i in range(5):
        rot = base.rotate(72 * i, resample=Image.Resampling.BICUBIC, center=(CENTER, CENTER))
        flower = Image.alpha_composite(flower, rot)
    d = ImageDraw.Draw(flower)
    d.ellipse((CENTER - 136, CENTER - 136, CENTER + 136, CENTER + 136), fill=PETAL_DEEP)  # penutup celah
    r = 92
    d.ellipse((CENTER - r, CENTER - r, CENTER + r, CENTER + r),
              fill=CORE, outline=CORE_RING, width=14)
    for i in range(6):  # benang sari
        ang = math.radians(60 * i + 18)
        px = CENTER + math.cos(ang) * 126
        py = CENTER + math.sin(ang) * 126
        d.ellipse((px - 15, py - 15, px + 15, py + 15), fill=CORE_RING)
    return flower


def _sparkle(cx: float, cy: float, outer: float) -> Image.Image:
    """Bintang 4 sudut kecil — kesan 'magic/upscale'."""
    layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    inner = outer * 0.30
    pts = []
    for i in range(8):
        ang = math.radians(45 * i - 90)
        rad = outer if i % 2 == 0 else inner
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    ImageDraw.Draw(layer).polygon(pts, fill=SPARKLE)
    return layer


def build_icon() -> Image.Image:
    img = _background()
    glow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((CENTER - 335, CENTER - 335, CENTER + 335, CENTER + 335), fill=GLOW)
    img = Image.alpha_composite(img, glow)
    img = Image.alpha_composite(img, _flower())
    img = Image.alpha_composite(img, _sparkle(196, 226, 74))
    img = Image.alpha_composite(img, _sparkle(832, 808, 52))
    return img


def main() -> None:
    out_dir = Path(__file__).resolve().parent.parent / "app" / "assets"
    out_dir.mkdir(parents=True, exist_ok=True)

    icon = build_icon()
    png = icon.resize((256, 256), Image.Resampling.LANCZOS, reducing_gap=3.0)
    png.save(out_dir / "icon.png")
    png.save(out_dir / "icon.ico",
             sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(f"OK — {out_dir / 'icon.ico'}")
    print(f"OK — {out_dir / 'icon.png'}")


if __name__ == "__main__":
    main()
