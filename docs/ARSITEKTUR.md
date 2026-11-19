# 🏗️ Arsitektur WaifuUpscaler

Dokumen untuk kontributor: cara kerja internal, kontrak engine, dan aturan pemindaian model.
Untuk penggunaan harian lihat [Panduan](PANDUAN.md).

---

## Gambaran Umum

```
┌──────────── GUI (tkinter + tkinterdnd2) ────────────┐
│  Antrean (Treeview) · Pengaturan · Progress · Log   │
└──────────────┬──────────────────────────────────────┘
               │  ui_q (queue.Queue)  ←── worker thread
               ▼
┌──────────── engines.py ─────────────────────────────┐
│ list_models()  → pindai tools/ (sumber kebenaran)   │
│ validate_combo() → preflight sebelum antrean        │
│ resolve_pass_scale() → skala native utk binary      │
│ build_commands() → susun argv engine                │
│ run_engine()   → subprocess + parse progres %       │
│ downscale_png() → emulasi skala 1x-3x (Downscayl)   │
└──────────────┬──────────────────────────────────────┘
               │ subprocess (CREATE_NO_WINDOW)
               ▼
   tools/*/…-ncnn-vulkan.exe  (GPU via Vulkan)
```

Prinsip: **GUI tidak pernah memanggil engine langsung**; semua eksekusi lewat `subprocess` dengan daftar argumen, sehingga tidak butuh PyTorch dan engine bisa diganti/diunduh secara independen.

## Struktur Proyek

```
app/
├── __init__.py     ← APP_NAME & APP_VERSION (sumber tunggal versi)
├── config.py       ← konstanta path + load/save config.json
├── engines.py      ← spesifikasi engine, scan model, validasi, eksekusi,
│                       kategori foto/anime, katalog model foto terpin
├── downloader.py   ← unduh & ekstrak zip engine; unduh model foto
│                       (mirror lokal clone upscayl → fallback GitHub raw)
├── gui.py          ├── seluruh UI (tkinter, ttk clam, tema gelap)
├── assets/         ← icon.ico (multi-ukuran 16–256 px) + icon.png (fallback)
└── main.py         ← entry point (python -m app.main)
scripts/
└── make_icon.py    ← generator aset ikon (Pillow) — hasil deterministik
```

## Alur Satu File

1. `_worker` mengambil antrean → `_process_one(src, cfg, progress_cb)`.
2. `_output_path` menentukan tujuan (folder asal + akhiran, atau folder khusus + dedupe ` (2)`).
3. `prepare_input` — format di luar png/jpg/webp dikonversi ke PNG sementara (Pillow).
4. `build_commands` menyusun argv sesuai aturan engine (lihat tabel di bawah).
5. `run_engine` menjalankan subprocess, mem-parse persentase progres dari stdout (`%.2f%%`), membatalkan lewat `terminate()` bila `cancel_event` ter-set.
6. **Emulasi skala** (`resolve_pass_scale`): model fixed-4x realesrgan yang diminta di skala 1x-3x dijalankan penuh di skala native 4x, lalu `downscale_png` menurunkan hasilnya LANCZOS di Python — binary official tidak punya downscale (pola "Downscayl" Upscayl).
7. Output engine selalu PNG sementara → `png` langsung dipindah; `jpg/webp` di-encode ulang via Pillow (kualitas terkontrol, alpha diratakan ke putih untuk JPG).

## Kontrak Engine (dari source resmi)

| Engine | Argumen kunci | Aturan nama file model |
|---|---|---|
| **waifu2x** | `-n` denoise (-1..3), `-s` 1/2/4/8/16/32 | `noiseN_scale2.0x_model` (2x; skala 4 = model 2x diulang 2×), `noiseN_model` (1x/denoise-saja), `scale2.0x_model` (noise -1) |
| **Real-CUGAN** | `-n` (-1/0/1/2/3), `-s` 1/2/3/4, `-m` folder | `up{S}x-conservative` (noise -1), `up{S}x-no-denoise` (noise 0), `up{S}x-denoiseNx` (noise N) |
| **Real-ESRGAN** | `-n` nama model, `-s` 2/3/4 (hanya animevideov3; model fixed-4x selalu dijalankan di `-s 4` lalu diturunkan di Python), `-m` folder `models` | `{nama}-x{S}.param` untuk model bertingkat (animevideov3); `{nama}.param` tanpa akhiran = 4x bawaan (x4plus, model foto Upscayl dkk.) |

Konsekuensi penting: **ketersediaan denoise berbeda per skala** (contoh: Real-CUGAN SE hanya punya denoise 1x/2x di skala 2). Karena itu UI menampilkan opsi hasil **pemindaian disk**, bukan hardcode.

## Pemindaian Model (`list_models`)

- Untuk setiap folder `models*` di samping exe (waifu2x/realcugan), atau folder `models/` (realesrgan), file `*.param` di-parse dengan regex sesuai tabel di atas.
- Hasilnya `ModelSpec.options: {skala: (level denoise, ...)}`.
- Folder yang tidak dikenali polanya **tidak ditawarkan** — mencegah kombinasi yang pasti gagal.
- `validate_combo(engine, model, skala, denoise)` memverifikasi keberadaan file `.param` + `.bin` yang tepat; dipanggil sebagai preflight di `_on_start` sebelum antrean berjalan.

## Threading Model

- **Worker thread** (daemon) memproses antrean berurutan; semua pembaruan UI dikirim via `queue.Queue` dan dikonsumsi `root.after(80, _poll)` di thread utama.
- `cancel_event` (threading.Event) membatalkan proses berjalan + menandai sisa antrean.
- Enumerasi GPU & unduhan engine juga berjalan di thread terpisah agar UI tidak macet.

## Unduhan Engine

`downloader.download_zip` mengunduh zip release resmi (User-Agent sendiri, 3× retry, bisa dibatalkan) lalu mengekstrak ke `tools/`. `find_exe` mencari exe dengan `rglob` dan hasilnya di-cache (`invalidate_exe_cache` dipanggil setelah unduhan). Engine tidak ikut di repo — ukuran besar dan lisensinya terpisah.

## Model Foto (katalog terpin)

- `PHOTO_CATALOG` (engines.py) mendefinisikan model foto yang bisa diunduh via dialog **Kelola foto…**: `upscayl-lite-4x` (±2,4 MB) dan `upscayl-standard-4x` (±33 MB) — keduanya `.param`/`.bin` ncnn yang kompatibel dengan binary realesrgan official (konvensi input blob `data`).
- `downloader.download_model` mengambil tiap file dengan urutan hemat: **salin dari `LOCAL_MIRROR`** (clone upscayl di sebelah repo, `<root>/../upscayl/resources/models`) bila ada, selain itu **unduh GitHub raw** `upscayl/upscayl` di commit ter-pin `PHOTO_MODEL_REF` (file yang diterima tidak pernah berubah diam-diam). Tujuan: `tools/models/` — langsung ketahuan oleh `list_models` tanpa ubah kode.
- Kategori foto/anime diturunkan dari `FOTO_MODEL_IDS` / `FOTO_FOLDER_IDS` saat scan; filter UI menyaring `ModelSpec.category`.
- Lisensi: pemakaian pribadi aman. Untuk rilis publik, ceklis lisensi per model di openmodeldb (varian komunitas Upscayl seperti Remacri/UltraSharp berlabel Non-Commercial dan sengaja tidak masuk katalog).

## Menambah Model Baru

1. Letakkan folder model di samping exe engine (mis. `tools/waifu2x-ncnn-vulkan-20220728-windows/models-swintt/`).
2. Pastikan penamaan file mengikuti kontrak engine (tabel di atas).
3. Jalankan ulang aplikasi — model otomatis muncul di dropdown lengkap dengan opsi skala/denoise yang valid. Tidak ada kode yang perlu diubah.

## Standar Dokumentasi

- Versi mengikuti [Semantic Versioning](https://semver.org/lang/id/).
- Riwayat perubahan mengikuti [Keep a Changelog](https://keepachangelog.com/id/1.1.0/) di `CHANGELOG.md`.
- Saat merilis: naikkan `APP_VERSION` di `app/__init__.py`, tambahkan entri changelog, sesuaikan tautan pembanding versi di bagian bawah changelog.
