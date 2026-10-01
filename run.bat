@echo off
setlocal
title WaifuUpscaler - Launcher
cd /d "%~dp0"

echo ==================================================
echo   WaifuUpscaler - Upscale Gambar Anime (GPU)
echo ==================================================
echo.

set "PYCMD="
py -3 --version >nul 2>nul && set "PYCMD=py -3"
if not defined PYCMD python --version >nul 2>nul && set "PYCMD=python"
if not defined PYCMD (
    echo [ERROR] Python 3 tidak ditemukan di komputer ini.
    echo         Install Python 3.9+ dari https://www.python.org/downloads/
    echo         dan centang "Add Python to PATH" saat instalasi.
    echo.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [SETUP] Membuat virtual environment ^(.venv^) - sekali saja...
    %PYCMD% -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Gagal membuat virtual environment.
        pause
        exit /b 1
    )
)

echo [SETUP] Memeriksa dependensi ^("Pillow, tkinterdnd2"^)...
".venv\Scripts\python.exe" -m pip install --quiet --disable-pip-version-check --no-warn-script-location -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Gagal memasang dependensi. Periksa koneksi internet, lalu jalankan lagi.
    pause
    exit /b 1
)

echo [START] Menjalankan aplikasi...
".venv\Scripts\python.exe" -m app.main
if errorlevel 1 (
    echo.
    echo [ERROR] Aplikasi keluar dengan error. Lihat pesan di atas.
    pause
)
endlocal
