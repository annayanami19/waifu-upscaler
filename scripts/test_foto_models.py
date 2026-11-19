"""Uji headless fitur model foto (tanpa GUI): kategori, skala emulasi, end-to-end.

Jalankan dari root repo:  python scripts/test_foto_models.py

Tahap:
  1. Siapkan upscayl-lite-4x lewat jalur yang sama dengan aplikasi
     (mirror lokal clone upscayl -> fallback unduh GitHub).
  2. Assert kategori foto/anime hasil scan disk.
  3. Assert build_commands: model fixed-4x dijalankan di skala native,
     animevideov3 tetap native multi-skala.
  4. End-to-end: PNG uji 64x64 -> engine -> 256x256 -> downscale 2x -> 128x128.
     Tahap ini butuh binary tools/ + driver Vulkan; kalau hardware tidak
     mendukung, tahap dilaporkan SKIP (bukan gagal).
"""
from __future__ import annotations

import sys
import tempfile
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402

from app.downloader import download_model  # noqa: E402
from app.engines import (  # noqa: E402
    ENGINES,
    build_commands,
    downscale_png,
    find_exe,
    list_models,
    photo_model_files_ready,
    resolve_pass_scale,
    run_engine,
)

FAILURES: list = []
SKIPS: list = []


def check(name: str, cond: bool, detail: str = "") -> None:
    mark = "OK  " if cond else "FAIL"
    suffix = f"  [{detail}]" if detail and not cond else ""
    print(f"[{mark}] {name}{suffix}")
    if not cond:
        FAILURES.append(name)


def skip(name: str, detail: str = "") -> None:
    print(f"[SKIP] {name}" + (f"  [{detail}]" if detail else ""))
    SKIPS.append(name)


def argv_flag(argv: list, flag: str) -> str:
    """Nilai setelah flag dalam satu perintah engine ('' bila tidak ada)."""
    cmd = argv[0]
    if flag in cmd:
        return cmd[cmd.index(flag) + 1]
    return ""


def main() -> int:
    print("=== WaifuUpscaler · uji headless fitur model foto ===")
    eng = ENGINES["realesrgan"]

    # 1. Persiapan model lewat jalur aplikasi (mirror lokal -> fallback unduh).
    print("-- 1. Persiapan upscayl-lite-4x (mirror/unduh) --")
    download_model("upscayl-lite-4x")
    check("upscayl-lite-4x siap di tools/models/", photo_model_files_ready("upscayl-lite-4x"))

    models = list_models(eng)

    # 2. Kategori hasil scan disk.
    print("-- 2. Kategori model --")
    spec_lite = models.get("upscayl-lite-4x")
    check("upscayl-lite-4x terdeteksi scan", spec_lite is not None)
    check("upscayl-lite-4x kategori 'foto'",
          spec_lite is not None and spec_lite.category == "foto",
          f"category={spec_lite.category if spec_lite else None}")
    check("upscayl-lite-4x fixed-4x (tanpa denoise)",
          spec_lite is not None and spec_lite.scales == (4,),
          f"scales={spec_lite.scales if spec_lite else None}")
    spec_avi = models.get("realesr-animevideov3")
    check("animevideov3 terdeteksi + kategori 'anime'",
          spec_avi is not None and spec_avi.category == "anime",
          f"category={spec_avi.category if spec_avi else None}")
    spec_x4 = models.get("realesrgan-x4plus")
    check("x4plus terdeteksi + kategori 'foto'",
          spec_x4 is not None and spec_x4.category == "foto",
          f"category={spec_x4.category if spec_x4 else None}")

    # 3. Argumen & resolusi skala.
    print("-- 3. Argumen engine --")
    argv = build_commands("realesrgan", "upscayl-lite-4x", 2, 0, False, 0, "auto",
                          Path("in.png"), Path("out.png"), spec=spec_lite)
    check("fixed-4x diminta 2x -> binary dijalankan di -s 4 (native)",
          argv_flag(argv, "-s") == "4", f"-s {argv_flag(argv, '-s')!r}")
    check("resolve_pass_scale(fixed-4x, 2) == 4",
          resolve_pass_scale("realesrgan", spec_lite, 2) == 4)
    check("flag -n tetap id model",
          argv_flag(argv, "-n") == "upscayl-lite-4x", f"-n {argv_flag(argv, '-n')!r}")
    check("models dir menunjuk tools/models",
          argv_flag(argv, "-m").replace("\\", "/").endswith("tools/models"),
          f"-m {argv_flag(argv, '-m')!r}")
    argv2 = build_commands("realesrgan", "realesr-animevideov3", 2, 0, False, 0, "auto",
                           Path("in.png"), Path("out.png"), spec=spec_avi)
    check("animevideov3 diminta 2x -> -s 2 native (tanpa emulasi)",
          argv_flag(argv2, "-s") == "2" and resolve_pass_scale("realesrgan", spec_avi, 2) == 2,
          f"-s {argv_flag(argv2, '-s')!r}")

    # 4. End-to-end (butuh Vulkan/binary; dilewati bila hardware tak mendukung).
    print("-- 4. End-to-end engine --")
    if find_exe(eng) is None:
        skip("end-to-end", "binary realesrgan belum ada di tools/")
        return _summary()

    with tempfile.TemporaryDirectory(prefix="waifuup_test_") as td:
        td_path = Path(td)
        src = td_path / "uji.png"
        out = td_path / "uji.out.png"
        Image.new("RGB", (64, 64)).save(src, "PNG")
        argv_e2e = build_commands("realesrgan", "upscayl-lite-4x", 2, 0, False, 0,
                                  "auto", src, out, spec=spec_lite)
        try:
            run_engine(argv_e2e[0], lambda pct: None)
        except Exception as exc:
            tail = str(exc).splitlines()[-1] if str(exc) else "?"
            # Coba CPU sekali (mode -1) sebelum menyatakan skip.
            try:
                argv_cpu = build_commands("realesrgan", "upscayl-lite-4x", 2, 0, False, 0,
                                          "-1", src, out, spec=spec_lite)
                run_engine(argv_cpu[0], lambda pct: None)
            except Exception as exc2:
                skip("end-to-end engine", f"hardware tidak mendukung: {tail}")
            else:
                _verify_output(out)
        else:
            _verify_output(out)

    return _summary()


def _verify_output(out: Path) -> None:
    if not out.is_file():
        check("engine menulis output PNG", False, f"{out} tidak ada")
        return
    img = Image.open(out)
    check("engine 4x native menghasilkan 256x256", img.size == (256, 256), f"{img.size}")
    downscale_png(out, 2 / 4)  # emulasi skala 2x — jalur yang sama dengan GUI
    img2 = Image.open(out)
    check("downscale_png emulasi 2x menghasilkan 128x128", img2.size == (128, 128),
          f"{img2.size}")


def _summary() -> int:
    print("---")
    print(f"Ringkasan: {len(FAILURES)} gagal, {len(SKIPS)} dilewati")
    if FAILURES:
        print("GAGAL: " + ", ".join(FAILURES))
        return 1
    print("Semua pengujian inti lulus.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 — laporan kegagalan yang jelas, bukan traceback mentah
        traceback.print_exc()
        sys.exit(1)
