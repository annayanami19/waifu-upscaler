"""Pengunduh engine ncnn-Vulkan dari GitHub Releases (zip -> folder tools/)."""
from __future__ import annotations

import threading
import time
import urllib.request
import zipfile
from pathlib import Path
from typing import Callable, Optional

from .engines import TOOLS_DIR, EngineError


class DownloadCancelled(RuntimeError):
    pass


_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) WaifuUpscaler/1.0"}


def _cleanup(tmp: Path) -> None:
    try:
        tmp.unlink()
    except OSError:
        pass


def download_zip(
    url: str,
    progress: Optional[Callable[[int, int], None]] = None,
    cancel: Optional[threading.Event] = None,
    retries: int = 3,
) -> None:
    """Unduh zip release lalu ekstrak isinya ke folder tools/.

    progress(done_bytes, total_bytes) dipanggil berkala; total bisa 0 bila
    server tidak mengirim Content-Length.
    """
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    tmp = TOOLS_DIR / ".unduhan-engine.zip"
    last_err: Optional[Exception] = None

    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers=_UA)
            with urllib.request.urlopen(req, timeout=90) as resp:
                total = int(resp.headers.get("Content-Length") or 0)
                done = 0
                with open(tmp, "wb") as f:
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
            with zipfile.ZipFile(tmp) as z:
                z.extractall(TOOLS_DIR)
            _cleanup(tmp)
            return
        except DownloadCancelled:
            _cleanup(tmp)
            raise
        except Exception as exc:  # noqa: BLE001 — simpan pesan terakhir lalu coba lagi
            last_err = exc
            _cleanup(tmp)
            if attempt < retries:
                time.sleep(1.5 * attempt)

    raise EngineError(f"Gagal mengunduh engine: {last_err}")
