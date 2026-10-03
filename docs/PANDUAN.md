# 📖 Panduan Lengkap WaifuUpscaler

Panduan penggunaan sehari-hari: fitur detail, memilih model, dan mengatasi masalah.
Untuk ringkasan singkat lihat [README](../README.md); untuk riwayat versi lihat [CHANGELOG](../CHANGELOG.md).

---

## 🚀 Alur Dasar

1. Klik dua kali **`run.bat`** (setup pertama berjalan otomatis).
2. **Tarik & lepas** gambar/folder ke jendela — atau klik dua kali area daftar, atau pakai tombol *Tambah File/Folder*.
3. Atur **Engine → Model → Skala → Denoise** di panel *Engine & Kualitas*.
4. Tekan **▶ Mulai Proses** — pantau progres & panel Log.
5. Klik dua kali baris berstatus *Selesai* untuk pratinjau **sebelum/sesudah**.

## ✨ Fitur

- 🖱️ **Drag & drop** ke mana saja di jendela; drop folder memindai subfolder (bisa dimatikan).
- 🔄 **Opsi model otomatis**: model/skala/denoise yang tampil di UI dipindai dari file model asli di `tools/`, jadi kombinasi yang tidak ada tidak akan pernah ditawarkan.
- 🧯 **Preflight**: kombinasi divalidasi saat menekan Mulai — kalau bermasalah, muncul dialog penjelasan alih-alih gagal diam-diam per file.
- 🎚️ **Denoise tersinkron per skala**: saat ganti skala, slider otomatis menyesuaikan level yang tersedia.
- 🧱 **Ukuran tile**: VRAM kecil → pilih 64/128; Auto mengikuti ukuran gambar.
- 🧪 **Mode TTA**: hasil sedikit lebih bagus, ±2× lebih lambat.
- 🖥️ **Pilihan GPU**: terdeteksi otomatis; tersedia mode CPU (sangat lambat).
- 📊 Progres keseluruhan antrean, statistik, tombol **Batalkan** kapan saja.
- ☑️ **Checkbox per gambar**: tandai beberapa gambar (atau **Pilih Semua** / klik header kolom ☐) lalu tekan **🗑 Hapus Tercentang** untuk menghapus sekaligus. Tombol **🧹 Bersihkan Daftar** mengosongkan seluruh antrean, **🧹 Bersihkan Log** mengosongkan panel log. Gambar yang sedang diproses selalu dilindungi dari penghapusan.
- 🖼️ Pratinjau sebelum/sesudah: zoom Ctrl+scroll, pan, tombol Fit.
- 📂 Output ke folder asal (dengan akhiran nama) atau folder khusus; opsi lewati file yang sudah ada; dua sumber bernama sama otomatis diberi akhiran ` (2)`.
- 💾 Ukuran jendela & semua pengaturan tersimpan otomatis di `config.json`.
- 🌸 Ikon aplikasi kustom (sakura) di title bar & taskbar — bisa dibuat ulang via `python scripts/make_icon.py`.

## 🎯 Memilih Model: Anime vs Foto

| Jenis gambar | Engine | Model | Skala | Catatan |
|---|---|---|---|---|
| Anime / ilustrasi (terbaik) | Waifu2x | CUNET · kualitas terbaik | 1x/2x/4x | Denoise 1–2 untuk JPEG ber-noise |
| Anime / ilustrasi (cepat) | Waifu2x | UPCONV7 anime | 2x/4x | Paling responsif |
| Anime tajam | Real-CUGAN | SE / PRO | 2x–4x | **Khusus anime** — kurang cocok untuk foto |
| Anime super cepat (batch) | Real-ESRGAN | AnimeVideoV3 | 2x/3x/4x | Ideal untuk banyak file |
| **Foto / gambar umum** | **Real-ESRGAN** | **x4plus · umum / foto** | 4x | Model dunia-nyata, hasil natural |
| **Foto (cepat)** | **Waifu2x** | **UPCONV7 foto** | 2x/4x | Varian foto waifu2x |

> Tidak perlu unduh model tambahan — semua model di atas sudah tersedia setelah engine terunduh.

## 📁 Format File

- **Input langsung**: PNG, JPG/JPEG, WEBP
- **Dikonversi otomatis** ke PNG sementara: BMP, TIF/TIFF, GIF (frame pertama)
- **Output**: PNG (transparan aman) · JPG · WEBP + slider kualitas (40–100)

## 🧾 Membaca Panel Log

- `[HH:MM:SS] +N gambar masuk antrean` — file berhasil ditambahkan.
- `Selesai · 2.4s` — waktu proses per file.
- `[GAGAL] nama.png — <pesan>` — pesan asli dari engine; baris **Catatan:** di bawahnya adalah saran perbaikan otomatis (mis. Vulkan tidak tersedia → perbarui driver GPU).

## 🧯 Troubleshooting

| Masalah | Solusi |
|---|---|
| "Vulkan tidak tersedia" / engine langsung gagal | Perbarui driver GPU (NVIDIA/AMD/Intel). Darurat: pilih `CPU (-1)` di dropdown GPU (sangat lambat). |
| Dialog "Kombinasi tidak tersedia" | Skala/denoise tidak punya file model — pilih kombinasi lain; UI memang hanya menampilkan yang valid. |
| Drag & drop tidak jalan | Pastikan `tkinterdnd2` terpasang — jalankan lewat `run.bat` (memasang otomatis dari `requirements.txt`). |
| Engine diunduh ulang terus? | Folder `tools/` jangan dihapus/dibersihkan antivirus; whitelist jika perlu. |
| Hasil aneh di foto | Jangan pakai model anime — pilih `x4plus · umum / foto` (Real-ESRGAN). |
| Proses lambat / VRAM penuh | Kecilkan **Ukuran tile** (128/64), matikan **TTA**, atau turunkan skala. |

## 📁 Struktur Folder

```
waifu-upscaler/
├── run.bat            ← klik dua kali file ini
├── requirements.txt
├── config.json        ← dibuat otomatis (pengaturan tersimpan)
├── app/               ← kode Python (GUI + integrasi engine) + assets/ (ikon)
├── scripts/           ← generator aset (make_icon.py)
├── tools/             ← engine ncnn-Vulkan + model (diabaikan git; unduh otomatis)
├── output/            ← folder output bawaan
└── docs/              ← dokumentasi
```
