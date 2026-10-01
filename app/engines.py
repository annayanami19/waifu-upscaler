"""Integrasi engine upscaler ncnn-Vulkan: waifu2x, Real-CUGAN, Real-ESRGAN.

Opsi model/skala/denoise TIDAK di-hardcode: semuanya dipindai dari file model
yang benar-benar ada di folder tools/, mengikuti aturan penamaan file di source
resmi tiap engine (nihui/waifu2x-ncnn-vulkan, nihui/realcugan-ncnn-vulkan,
xinntao/Real-ESRGAN-ncnn-vulkan). Dengan begitu aplikasi tidak pernah
menawarkan kombinasi yang tidak ada — penyebab umum kegagalan saat Start.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

from PIL import Image

TOOLS_DIR = Path(__file__).resolve().parent.parent / "tools"

# Format yang langsung diterima engine; selain itu dikonversi ke PNG sementara.
SUPPORTED_DIRECT = {".png", ".jpg", ".jpeg", ".webp"}

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0

_PERCENT_RE = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*%")

# Petunjuk tambahan saat engine gagal (dicocokkan ke pesan keluarannya).
_FAIL_HINTS = (
    (("vkenumeratephysicaldevices", "vkcreateinstance", "no vulkan", "vulkan device"),
     "Vulkan tidak tersedia. Perbarui driver GPU, atau pilih mode CPU (sangat lambat) di pengaturan GPU."),
    (("invalid gpu device",),
     "GPU yang dipilih tidak tersedia — pilih 'Auto' di pengaturan GPU."),
    (("decode image", "failed to open"),
     "File gambar tidak bisa dibaca. Coba simpan ulang sebagai PNG/JPG."),
    (("no such file", "not found", "failed"),
     "File model tidak ditemukan — pilih kombinasi model/skala/denoise lain."),
)


class EngineError(RuntimeError):
    """Kegagalan menjalankan engine upscaler."""


class TaskCancelled(RuntimeError):
    """Antrean dibatalkan oleh pengguna."""


@dataclass(frozen=True)
class ModelSpec:
    """Satu model: label tampilan + opsi {skala: tuple level denoise}."""

    label: str
    options: Dict[int, Tuple[int, ...]]  # tuple kosong = model tanpa opsi denoise

    @property
    def scales(self) -> Tuple[int, ...]:
        return tuple(sorted(self.options))

    def denoise_levels(self, scale: int) -> Tuple[int, ...]:
        return tuple(self.options.get(scale, ()))


@dataclass(frozen=True)
class Engine:
    key: str
    label: str
    exe_name: str
    zip_url: str
    default_model: str
    note: str


ENGINES: Dict[str, Engine] = {
    "waifu2x": Engine(
        "waifu2x",
        "Waifu2x · klasik anime",
        "waifu2x-ncnn-vulkan.exe",
        "https://github.com/nihui/waifu2x-ncnn-vulkan/releases/download/20220728/waifu2x-ncnn-vulkan-20220728-windows.zip",
        "models-cunet",
        "Model legendaris untuk ilustrasi & anime.",
    ),
    "realcugan": Engine(
        "realcugan",
        "Real-CUGAN · anime tajam",
        "realcugan-ncnn-vulkan.exe",
        "https://github.com/nihui/realcugan-ncnn-vulkan/releases/download/20220728/realcugan-ncnn-vulkan-20220728-windows.zip",
        "models-se",
        "Kualitas tinggi khusus anime; opsi skala mengikuti model.",
    ),
    "realesrgan": Engine(
        "realesrgan",
        "Real-ESRGAN · modern & cepat",
        "realesrgan-ncnn-vulkan.exe",
        "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-windows.zip",
        "realesr-animevideov3",
        "Sangat cepat, cocok untuk batch besar.",
    ),
}

# Label ramah untuk nama model (opsi tetap dipindai dari disk).
REALESRGAN_LABELS = {
    "realesr-animevideov3": "AnimeVideoV3 · super cepat (anime)",
    "realesrgan-x4plus-anime": "x4plus-anime · kualitas tinggi",
    "realesrgan-x4plus": "x4plus · umum / foto",
    "realesrnet-x4plus": "realesrnet-x4plus · restorasi foto",
}
KNOWN_MODEL_LABELS = {
    "models-cunet": "CUNET · kualitas terbaik (anime)",
    "models-upconv_7_anime_style_art_rgb": "UPCONV7 anime · tercepat",
    "models-upconv_7_photo": "UPCONV7 foto · tercepat",
    "models-se": "SE · seimbang",
    "models-pro": "PRO · paling tajam",
    "models-nose": "NOSE · denoise saja",
}

_EXE_CACHE: Dict[str, Optional[Path]] = {}


def invalidate_exe_cache() -> None:
    _EXE_CACHE.clear()


def find_exe(engine: Engine) -> Optional[Path]:
    if engine.key in _EXE_CACHE:
        return _EXE_CACHE[engine.key]
    found: Optional[Path] = None
    if TOOLS_DIR.is_dir():
        for candidate in TOOLS_DIR.rglob(engine.exe_name):
            found = candidate
            break
    _EXE_CACHE[engine.key] = found
    return found


# ---------------------------------------------------------------------------
# Pemindaian file model — sumber kebenaran untuk opsi yang ditampilkan di UI.
#
# Aturan nama file (dari source resmi):
#   waifu2x   : noiseN_scale2.0x_model (skala 2x; skala 4 = model 2x diulang 2x),
#               noiseN_model (skala 1 / denoise-saja), scale2.0x_model (noise -1).
#   realcugan : up{S}x-{conservative|no-denoise|denoiseNx}
#               (conservative = noise -1, no-denoise = noise 0).
#   realesrgan: {nama}-x{S} untuk model bertingkat (animevideov3);
#               {nama} tanpa akhiran = 4x bawaan (x4plus dkk).

_W2X_SCALE2_RE = re.compile(r"^noise(-?\d+)_scale2\.0x_model$")
_W2X_1X_RE = re.compile(r"^noise(-?\d+)_model$")
_RC_RE = re.compile(r"^up(\d)x-(conservative|no-denoise|denoise(\d)x)$")
_ESR_SCALED_RE = re.compile(r"^(.+)-x(\d)$")


def _scan_waifu2x_folder(folder: Path) -> Dict[int, Tuple[int, ...]]:
    combos: Dict[int, set] = {}
    for param in folder.glob("*.param"):
        name = param.stem
        m = _W2X_SCALE2_RE.match(name)
        if m:
            noise = int(m.group(1))
            combos.setdefault(2, set()).add(noise)
            combos.setdefault(4, set()).add(noise)  # model 2x diterapkan 2×
            continue
        m = _W2X_1X_RE.match(name)
        if m:
            combos.setdefault(1, set()).add(int(m.group(1)))
            continue
        if name == "scale2.0x_model":
            combos.setdefault(2, set()).add(-1)
            combos.setdefault(4, set()).add(-1)
    return {scale: tuple(sorted(levels)) for scale, levels in combos.items()}


def _scan_realcugan_folder(folder: Path) -> Dict[int, Tuple[int, ...]]:
    combos: Dict[int, set] = {}
    for param in folder.glob("*.param"):
        m = _RC_RE.match(param.stem)
        if not m:
            continue
        scale = int(m.group(1))
        variant = m.group(2)
        if variant == "conservative":
            noise = -1
        elif variant == "no-denoise":
            noise = 0
        else:
            noise = int(m.group(3))
        combos.setdefault(scale, set()).add(noise)
    return {scale: tuple(sorted(levels)) for scale, levels in combos.items()}


def _scan_realesrgan_models(folder: Path) -> Dict[str, Dict[int, Tuple[int, ...]]]:
    found: Dict[str, Dict[int, Tuple[int, ...]]] = {}
    if not folder.is_dir():
        return found
    for param in folder.glob("*.param"):
        m = _ESR_SCALED_RE.match(param.stem)
        if m:
            found.setdefault(m.group(1), {})[int(m.group(2))] = ()
        else:
            found.setdefault(param.stem, {})[4] = ()  # x4plus: 4x bawaan
    return found


def list_models(engine: Engine) -> Dict[str, ModelSpec]:
    """Model + opsi (skala & denoise) yang benar-benar tersedia di disk."""
    exe = find_exe(engine)
    if exe is None:
        return {
            engine.default_model: ModelSpec(
                "Default bawaan (engine belum diunduh)", {2: (-1, 0, 1, 2, 3)}
            )
        }

    models: Dict[str, ModelSpec] = {}
    if engine.key == "realesrgan":
        for name, options in sorted(_scan_realesrgan_models(exe.parent / "models").items()):
            models[name] = ModelSpec(REALESRGAN_LABELS.get(name, name), options)
    else:
        scan = _scan_waifu2x_folder if engine.key == "waifu2x" else _scan_realcugan_folder
        for child in sorted(exe.parent.iterdir()):
            if not (child.is_dir() and child.name.lower().startswith("models")):
                continue
            options = scan(child)
            if not options:
                continue  # folder tak dikenali — jangan ditawarkan
            models[child.name] = ModelSpec(KNOWN_MODEL_LABELS.get(child.name, child.name), options)

    if not models:
        models = {
            engine.default_model: ModelSpec(
                KNOWN_MODEL_LABELS.get(engine.default_model, engine.default_model),
                {2: (-1, 0, 1, 2, 3)},
            )
        }
    return models


# ---------------------------------------------------------------------------
# Validasi kombinasi sebelum antrean dimulai.

def _expected_param(engine_key: str, exe: Path, model_id: str,
                    scale: int, denoise: int) -> Tuple[Optional[Path], Optional[str]]:
    """Path .param yang diharapkan engine, mengikuti aturan nama di source-nya."""
    if engine_key == "realesrgan":
        model_dir = exe.parent / "models"
        if not model_dir.is_dir():
            return None, "Folder 'models' Real-ESRGAN tidak ditemukan di folder tools/."
        if model_id == "realesr-animevideov3":
            return model_dir / f"{model_id}-x{scale}.param", None
        return model_dir / f"{model_id}.param", None

    model_dir = exe.parent / model_id
    if not model_dir.is_dir():
        return None, f"Folder model '{model_id}' tidak ditemukan di folder tools/."

    if engine_key == "waifu2x":
        if denoise < 0:
            if scale == 1:
                return None, ("Waifu2x: denoise -1 tidak tersedia untuk skala 1x.\n"
                              "Pilih skala 2x/4x, atau denoise 0-3.")
            return model_dir / "scale2.0x_model.param", None
        if scale == 1:
            return model_dir / f"noise{denoise}_model.param", None
        return model_dir / f"noise{denoise}_scale2.0x_model.param", None

    # realcugan
    if denoise < 0:
        variant = "conservative"
    elif denoise == 0:
        variant = "no-denoise"
    else:
        variant = f"denoise{denoise}x"
    return model_dir / f"up{scale}x-{variant}.param", None


def validate_combo(engine_key: str, model_id: str, scale: int, denoise: int) -> Optional[str]:
    """Cek kombinasi engine/model/skala/denoise. Return pesan error atau None."""
    engine = ENGINES[engine_key]
    exe = find_exe(engine)
    if exe is None:
        return f"Engine '{engine.label}' belum diunduh ke folder tools/."

    param, err = _expected_param(engine_key, exe, model_id, scale, denoise)
    if err:
        return err
    assert param is not None

    if not param.is_file():
        return (
            f"Kombinasi tidak tersedia untuk {engine.label}:\n"
            f"model '{model_id}', skala {scale}x, denoise {denoise}.\n\n"
            f"File model yang dicari: {param.name}\n\n"
            "Pilih kombinasi skala/denoise lain, atau model lain."
        )
    if not param.with_suffix(".bin").is_file():
        return f"File bobot model tidak lengkap: {param.with_suffix('.bin').name} tidak ditemukan."
    return None


# ---------------------------------------------------------------------------
# Eksekusi engine.

def enumerate_gpus(exe: Path) -> list:
    """Coba ambil daftar GPU dari teks bantuan engine. Return list[(id, nama)]."""
    try:
        proc = subprocess.run(
            [str(exe)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            creationflags=CREATE_NO_WINDOW,
        )
    except Exception:
        return []
    text = proc.stdout or ""
    gpus = []
    for m in re.finditer(r"gpu\s*(\d+)\s*:\s*([^\r\n]+)", text, re.IGNORECASE):
        name = m.group(2).strip().rstrip(".")
        if name:
            gpus.append((m.group(1), name))
    return gpus


def build_commands(
    engine_key: str,
    model_id: str,
    scale: int,
    denoise: int,
    tta: bool,
    tile: int,
    gpu: str,
    src: Path,
    dst: Path,
) -> list:
    """Susun argv untuk engine terpilih. Output engine selalu PNG (re-encode dilakukan GUI)."""
    engine = ENGINES[engine_key]
    exe = find_exe(engine)
    if exe is None:
        raise EngineError(f"Engine '{engine.label}' belum diunduh ke folder tools/.")

    common: list = []
    if gpu not in (None, "", "auto"):
        common += ["-g", str(gpu)]
    if tta:
        common += ["-x"]
    common += ["-t", str(int(tile or 0))]

    if engine_key == "realesrgan":
        model_dir = exe.parent / "models"
        return [
            [
                str(exe),
                "-i", str(src),
                "-o", str(dst),
                "-n", model_id,
                "-s", str(scale),
                "-m", str(model_dir),
                *common,
            ]
        ]

    model_dir = exe.parent / model_id
    return [
        [
            str(exe),
            "-i", str(src),
            "-o", str(dst),
            "-s", str(scale),
            "-n", str(denoise),
            "-m", str(model_dir),
            *common,
        ]
    ]


def run_engine(argv: list, progress_cb: Callable[[float], None],
               cancel_event=None) -> None:
    """Jalankan satu perintah engine sambil mem-parse persentase progres."""
    try:
        proc = subprocess.Popen(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=CREATE_NO_WINDOW,
        )
    except OSError as exc:
        raise EngineError(f"Gagal menjalankan engine: {exc}")

    tail: deque = deque(maxlen=12)
    try:
        for line in proc.stdout:  # type: ignore[union-attr]
            line = line.strip()
            if not line:
                continue
            tail.append(line)
            if cancel_event is not None and cancel_event.is_set():
                proc.terminate()
                raise TaskCancelled()
            m = _PERCENT_RE.search(line)
            if m:
                try:
                    progress_cb(min(99.5, float(m.group(1))))
                except Exception:
                    pass
        proc.wait(timeout=120)
    finally:
        if proc.stdout is not None:
            try:
                proc.stdout.close()
            except Exception:
                pass

    if cancel_event is not None and cancel_event.is_set():
        raise TaskCancelled()
    if proc.returncode != 0:
        msg = "\n".join(tail) or f"engine keluar dengan kode {proc.returncode}"
        low = msg.lower()
        for needles, hint in _FAIL_HINTS:
            if any(n in low for n in needles):
                msg += f"\nCatatan: {hint}"
                break
        raise EngineError(msg)
    progress_cb(100.0)


def prepare_input(src: Path, tmpdir: Path) -> Path:
    """Format selain png/jpg/webp dikonversi dulu ke PNG sementara."""
    if src.suffix.lower() in SUPPORTED_DIRECT:
        return src
    img = Image.open(src)
    img.load()
    out = tmpdir / (src.stem + ".png")
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA" if "A" in img.getbands() or img.mode == "P" else "RGB")
    img.save(out, "PNG")
    return out


def encode_output(png_path: Path, out: Path, fmt: str, quality: int) -> None:
    """PNG hasil engine di-encode ulang ke jpg/webp (kualitas terkontrol, alpha diratakan)."""
    img = Image.open(png_path)
    img.load()
    if fmt == "jpg":
        if img.mode != "RGB":
            if "A" in img.getbands():
                rgba = img.convert("RGBA")
                bg = Image.new("RGB", rgba.size, (255, 255, 255))
                bg.paste(rgba, mask=rgba.split()[-1])
                img = bg
            else:
                img = img.convert("RGB")
        img.save(out, "JPEG", quality=int(quality), optimize=True)
    elif fmt == "webp":
        img.save(out, "WEBP", quality=int(quality))
    else:
        img.save(out, "PNG")


def move_file(src: Path, dst: Path) -> None:
    shutil.move(str(src), str(dst))
