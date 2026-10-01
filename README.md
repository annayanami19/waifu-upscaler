# 🌸 WaifuUpscaler

<p align="center">
  <b>Upscale gambar anime &amp; foto di GPU — tanpa PyTorch, tanpa ribet.</b><br>
  Klik dua kali <code>run.bat</code>, tarik-lepas gambarnya, selesai.
</p>

---

**WaifuUpscaler** adalah aplikasi GUI Windows untuk *image upscaling* yang ditenagai tiga engine ncnn-Vulkan terbukti di komunitas: **waifu2x**, **Real-CUGAN**, dan **Real-ESRGAN**. Semua model berjalan di GPU kamu (NVIDIA/AMD/Intel dengan driver Vulkan) lewat executable portabel — tanpa install PyTorch atau environment AI berat.

## ✨ Sekilas Fitur

- 🖱️ **Drag & drop** gambar atau folder (bisa rekursif) ke jendela
- ⚙️ 3 engine + model **anime & foto** — opsi dipindai otomatis dari folder `tools/`
- 🔍 Skala 1x–4x, level denoise tersinkron otomatis dengan skala & model terpilih
- 📦 Batch queue + progres, output PNG / JPG / WebP, folder output fleksibel
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

Lisensi tiap engine mengikuti repo asalnya (lihat tautan di atas).

## 📄 Lisensi

Kode aplikasi: belum ditetapkan — tambahkan file `LICENSE` sebelum rilis publik jika diperlukan.
