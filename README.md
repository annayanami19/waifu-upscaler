# 🌸 WaifuUpscaler

<p align="center">
  <b>Upscale gambar anime &amp; foto di GPU — tanpa PyTorch, tanpa ribet.</b><br>
  Klik dua kali <code>run.bat</code>, tarik-lepas gambarnya, selesai.
</p>

---

**WaifuUpscaler** adalah aplikasi GUI Windows untuk *image upscaling* yang ditenagai tiga engine ncnn-Vulkan terbukti di komunitas: **waifu2x**, **Real-CUGAN**, dan **Real-ESRGAN**. Semua model berjalan di GPU kamu (NVIDIA/AMD/Intel dengan driver Vulkan) lewat executable portabel — tanpa install PyTorch atau environment AI berat.

## ✨ Sekilas Fitur

- 🖱️ **Drag & drop** gambar atau folder (bisa rekursif) ke jendela
- 🖼️ **Mode tampilan daftar gambar** — Detail / Ikon Kecil / Sedang / Besar / Ekstra Besar ala Windows Explorer: thumbnail tampil di daftar, nama file tetap terlihat
- 🗂️ **Section bisa dilipat** — panel **Daftar Gambar**, **Pengaturan**, dan **Log** di-collapse/expand lewat strip judulnya (chevron ▾/▸); section di bawahnya otomatis naik mengisi ruang
- 📖 **Menu Bantuan bawaan** — jendela **Panduan & Fitur** berisi panduan lengkap + daftar seluruh fitur yang tertanam di aplikasi (dropdown *Lompat ke bagian*); dibuka via menu **Bantuan**, tombol **❓ Panduan** di header, atau tombol **F1**
- 🌸 **Ikon aplikasi kustom** (sakura) di title bar & taskbar — aset `.ico` multi-ukuran, bisa dibuat ulang via `scripts/make_icon.py`; **logo di header beranimasi** (bunga berputar, makin cepat saat proses jalan)
- ⚙️ 3 engine + model **anime & foto** — opsi dipindai otomatis dari folder `tools/`
- 🧑‍🎤 **Kategori model (Semua/Anime/Foto)** — filter dropdown model; model foto real manusia terpisah rapi dari anime
- 📥 **Kelola model foto** — unduh model foto Upscayl (Lite ±2,4 MB / Standard ±33 MB) yang berjalan di engine Real-ESRGAN bawaan; hemat (mirror lokal dulu, baru GitHub)
- 🔍 Skala 1x–4x, level denoise tersinkron otomatis dengan skala & model terpilih; model fixed-4x mendukung skala 1x-3x via **emulasi Downscayl** ala Upscayl
- 📦 Batch queue + progres, output PNG / JPG / WebP, folder output fleksibel; nama output diawali tanggal-jam sampai detik (`YYYYMMDD-HHMMSS-namafile.png`) — gambar sama bisa di-upscale berkali-kali tanpa saling menimpa
- ☑️ Checkbox per gambar + **Pilih Semua** — hapus banyak gambar sekaligus; tombol **Bersihkan Daftar** & **Bersihkan Log**
- 🖼️ Pratinjau **sebelum/sesudah** dengan zoom (Ctrl+scroll) & pan

## 🚀 Mulai Cepat

1. Pastikan **Python 3.9+** terpasang (centang *Add Python to PATH* saat install) dan GPU punya driver Vulkan.
2. Klik dua kali **`run.bat`** — virtual environment & dependensi dipasang otomatis saat pertama kali.
3. Tarik & lepas gambar/folder → tekan **▶ Mulai Proses**.

> 📦 Folder `tools/` (biner engine, ±35–46 MB per engine) tidak disertakan di repo — aplikasi akan menawarkan **unduhan otomatis** saat engine dibutuhkan.

## 📚 Dokumentasi

| Dokumen | Isi |
|---|---|
| 📖 [Panduan Lengkap](docs/PANDUAN.md) | Fitur detail, rekomendasi model anime vs foto, troubleshooting |
| 📝 [CHANGELOG](CHANGELOG.md) | Riwayat versi & perubahan |
| 🏗️ [Arsitektur](docs/ARSITEKTUR.md) | Cara kerja internal — untuk kontributor |

## 🙏 Engine Pihak Ketiga

- [waifu2x-ncnn-vulkan](https://github.com/nihui/waifu2x-ncnn-vulkan) — nihui
- [realcugan-ncnn-vulkan](https://github.com/nihui/realcugan-ncnn-vulkan) — nihui
- [Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN) — xinntao
- Model foto [Upscayl Standard & Lite](https://github.com/upscayl/upscayl) — tim Upscayl

Lisensi tiap engine/model mengikuti repo asalnya (lihat tautan di atas; model Upscayl untuk pemakaian pribadi).

## 📄 Lisensi

Kode aplikasi: belum ditetapkan — tambahkan file `LICENSE` sebelum rilis publik jika diperlukan.
