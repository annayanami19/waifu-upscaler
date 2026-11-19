"""Pengunduh engine ncnn-Vulkan (zip) dan model foto (raw GitHub -> tools/)."""
from __future__ import annotations

import shutil
import threading
import time
import urllib.request
import zipfile
from pathlib import Path
from typing import Callable, Optional

from .engines import PHOTO_MODEL_REF, TOOLS_DIR, EngineError


class DownloadCancelled(RuntimeError):
    pass


_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) WaifuUpscaler/1.0"}

# Folder model realesrgan di dalam aplikasi ini.
MODELS_DIR = TOOLS_DIR / "models"

# Mirror lokal opsional: clone repo upscayl yang diletakkan di sebelah repo
# ini (…/aplikasi-01/upscayl). Kalau ada, file model disalin dari situ —
# tanpa bandwidth. Tidak ada / path tidak cocok → langsung unduh GitHub.
LOCAL_MIRROR = TOOLS_DIR.parent.parent / "upscayl" / "resources" / "models"


def _cleanup(tmp: Path) -> None:
    try:
        tmp.unlink()
    except OSError:
        pass


def _download_to(
    url: str,
    dest: Path,
    progress: Optional[Callable[[int, int], None]] = None,
    cancel: Optional[threading.Event] = None,
    retries: int = 3,
) -> None:
    """Unduh satu file ke dest dengan retry + cancel. progress(done_bytes, total_bytes).

    total bisa 0 bila server tidak mengirim Content-Length.
    """
    last_err: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers=_UA)
            with urllib.request.urlopen(req, timeout=90) as resp:
                total = int(resp.headers.get("Content-Length") or 0)
                done = 0
                with open(dest, "wb") as f:
                    while True:
                        if cancel is not None and cancel.is_set():
                            raise DownloadCancelled()
                        chunk = resp.read(1 << 16)
                        if not chunk:
                            break
                        f.write(chunk)
                        done += len(chunk)
                        if progress is not None:
                            progress(done, total)
            return
        except DownloadCancelled:
            _cleanup(dest)
            raise
        except Exception as exc:  # noqa: BLE001 — simpan pesan terakhir lalu coba lagi
            last_err = exc
            _cleanup(dest)
            if attempt < retries:
                time.sleep(1.5 * attempt)

    raise EngineError(f"Gagal mengunduh: {last_err}")


def download_zip(
    url: str,
    progress: Optional[Callable[[int, int], None]] = None,
    cancel: Optional[threading.Event] = None,
    retries: int = 3,
) -> None:
    """Unduh zip release lalu ekstrak isinya ke folder tools/."""
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    tmp = TOOLS_DIR / ".unduhan-engine.zip"
    _download_to(url, tmp, progress, cancel, retries)
    try:
        with zipfile.ZipFile(tmp) as z:
            z.extractall(TOOLS_DIR)
    finally:
        _cleanup(tmp)


def download_model(
    model_id: str,
    progress: Optional[Callable[[int, int], None]] = None,
    cancel: Optional[threading.Event] = None,
    retries: int = 3,
) -> None:
    """Siapkan pasangan .param + .bin satu model foto di tools/models/.

    Urutan sumber (hemat bandwidth):
      1. salin dari mirror lokal (clone upscayl di sebelah repo ini) bila ada,
      2. unduh dari GitHub raw repo resmi upscayl/upscayl (commit ter-pin).
    """
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    for ext in (".param", ".bin"):
        dest = MODELS_DIR / (model_id + ext)
        if dest.is_file():
            continue  # sudah ada — jangan unduh ulang
        mirror = LOCAL_MIRROR / (model_id + ext)
        if mirror.is_file():
            shutil.copyfile(mirror, dest)
            continue
        url = (f"https://raw.githubusercontent.com/upscayl/upscayl/"
               f"{PHOTO_MODEL_REF}/resources/models/{model_id}{ext}")
        _download_to(url, dest, progress, cancel, retries)
