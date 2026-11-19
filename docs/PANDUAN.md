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
- 🧑‍🎤 **Kategori model** (dropdown *Kategori*): filter daftar model jadi **Semua / Anime / Foto** — model foto real manusia langsung kelihatan tanpa menabur daftar anime.
- 📥 **Kelola model foto** (tombol *Kelola foto…*): unduh model foto ncnn tambahan (Upscayl Lite ±2,4 MB, Upscayl Standard ±33 MB) yang berjalan di engine Real-ESRGAN bawaan; file diambil dari clone upscayl lokal bila ada, selain itu GitHub (commit ter-pin). Model siap otomatis muncul di dropdown.
- 🎚️ **Emulasi skala 1x-3x** untuk model fixed-4x ala Upscayl: upscale native 4x lalu diturunkan LANCZOS — dropdown skala model 4x menawarkan 1x-4x lengkap.
- 🧯 **Preflight**: kombinasi divalidasi saat menekan Mulai — kalau bermasalah, muncul dialog penjelasan alih-alih gagal diam-diam per file.
- 🎚️ **Denoise tersinkron per skala**: saat ganti skala, slider otomatis menyesuaikan level yang tersedia.
- 🧱 **Ukuran tile**: VRAM kecil → pilih 64/128; Auto mengikuti ukuran gambar.
- 🧪 **Mode TTA**: hasil sedikit lebih bagus, ±2× lebih lambat.
- 🖥️ **Pilihan GPU**: terdeteksi otomatis; tersedia mode CPU (sangat lambat).
- 📊 Progres keseluruhan antrean, statistik, tombol **Batalkan** kapan saja.
- ☑️ **Checkbox per gambar**: tandai beberapa gambar (atau **Pilih Semua** / klik header kolom ☐) lalu tekan **🗑 Hapus Tercentang** untuk menghapus sekaligus. Tombol **🧹 Bersihkan Daftar** mengosongkan seluruh antrean, **🧹 Bersihkan Log** mengosongkan panel log. Gambar yang sedang diproses selalu dilindungi dari penghapusan.
- 🖼️ Pratinjau sebelum/sesudah: zoom Ctrl+scroll, pan, tombol Fit.
- 🗂️ **Mode tampilan daftar** (dropdown *Tampilan:* di toolbar): Detail, Ikon Kecil, Ikon Sedang, Ikon Besar, Ikon Ekstra Besar — thumbnail gambar tampil berdampingan dengan nama filenya, pilihan tersimpan otomatis.
- 🗂️ **Section bisa dilipat**: klik strip judul **Daftar Gambar**, **Pengaturan**, atau **Log** untuk collapse/expand (chevron ▾/▸). Saat satu section dilipat, section di bawahnya otomatis naik mengisi ruang kosongnya.
- 📖 **Menu Bantuan bawaan**: menu **Bantuan** di atas jendela berisi *Panduan & Fitur…* — jendela panduan lengkap & daftar seluruh fitur yang **tertanam di aplikasi** (tetap ada walau folder `docs/` tidak ikut), lengkap dengan dropdown *Lompat ke bagian*, tombol ⬆ Ke Atas, dan Esc untuk menutup. Bisa dibuka juga lewat tombol **❓ Panduan** di pojok kanan atas header atau tombol **F1**; menu ini juga memuat *Buka PANDUAN.md di editor* dan *Tentang WaifuUpscaler*.
- 📂 Output ke folder asal (dengan akhiran nama) atau folder khusus. Nama file output selalu diawali **tanggal-jam sampai detik** (`YYYYMMDD-HHMMSS-namafile.png`), jadi gambar yang sama bisa di-upscale **berkali-kali** tanpa menimpa hasil sebelumnya; dua sumber bernama sama yang diproses di antrean yang sama otomatis diberi akhiran ` (2)`.
- 💾 Ukuran jendela & semua pengaturan tersimpan otomatis di `config.json`.
- 🌸 Ikon aplikasi kustom (sakura) di title bar & taskbar; logo bunga di header **beranimasi berputar** dan melaju lebih cepat saat proses berjalan. Semua aset bisa dibuat ulang via `python scripts/make_icon.py`.

## 🎯 Memilih Model: Anime vs Foto

Filter dropdown **Kategori** jadi **Foto** untuk menyembunyikan model anime dan hanya menampilkan model foto real.

| Jenis gambar | Engine | Model | Skala | Catatan |
|---|---|---|---|---|
| Anime / ilustrasi (terbaik) | Waifu2x | CUNET · kualitas terbaik | 1x/2x/4x | Denoise 1–2 untuk JPEG ber-noise |
| Anime / ilustrasi (cepat) | Waifu2x | UPCONV7 anime | 2x/4x | Paling responsif |
| Anime tajam | Real-CUGAN | SE / PRO | 2x–4x | **Khusus anime** — kurang cocok untuk foto |
| Anime super cepat (batch) | Real-ESRGAN | AnimeVideoV3 | 2x/3x/4x | Ideal untuk banyak file |
| **Foto manusia/objek (terbaik)** | **Real-ESRGAN** | **Upscayl Standard · foto umum** | 1x–4x | Kualitas foto terbaik di katalog; skala 1x-3x diemulasi |
| **Foto / gambar umum** | **Real-ESRGAN** | **x4plus · umum / foto** | 1x–4x | Model dunia-nyata bawaan; skala 1x-3x diemulasi |
| **Foto (cepat & ringan)** | **Real-ESRGAN** | **Upscayl Lite · foto cepat** | 1x–4x | Cukup 2,4 MB; paling responsif untuk kualitas sekelasnya |
| **Foto (cepat)** | **Waifu2x** | **UPCONV7 foto** | 2x/4x | Varian foto waifu2x |

> Baris **Upscayl Standard / Lite** perlu diunduh dulu lewat tombol **Kelola foto…** di panel *Engine & Kualitas*. Tiga model lainnya sudah tersedia setelah engine terunduh — tidak perlu unduhan tambahan.

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
| Hasil aneh di foto | Jangan pakai model anime — filter **Kategori: Foto** lalu pilih `Upscayl Standard · foto umum` atau `x4plus · umum / foto` (Real-ESRGAN). |
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
