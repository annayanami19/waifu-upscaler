# Changelog

Semua perubahan penting pada proyek ini akan didokumentasikan di file ini.

Format mengikuti [Keep a Changelog](https://keepachangelog.com/id/1.1.0/),
dan versi mengikuti [Semantic Versioning](https://semver.org/lang/id/).

## [1.1.0] - 2026-10-01

### Ditambahkan

- **Pemindaian model otomatis**: daftar model, skala, dan level denoise kini dibaca langsung dari file model di folder `tools/`, mengikuti aturan penamaan source resmi tiap engine — aplikasi tidak pernah menawarkan kombinasi yang tidak ada.
- **Preflight validasi**: kombinasi engine/model/skala/denoise dicek sebelum antrean dimulai; bila tidak valid muncul dialog penjelasan, bukan gagal per-file.
- Slider denoise **tersinkron per skala**: level yang tidak tersedia otomatis di-snap ke terdekat (mis. Real-CUGAN SE 3x hanya punya -1/0/3).
- Ukuran, posisi, dan status **maximize jendela diingat** antar sesi.
- Konten aplikasi **scrollable** (roda mouse) dengan footer tombol aksi yang selalu terlihat.
- Hint diagnostik otomatis pada pesan error engine (Vulkan, GPU invalid, file gambar/model).

### Diperbaiki

- **Tombol Mulai Proses gagal untuk semua file** — `KeyError: 'model'` karena key konfigurasi tidak pernah diisi saat tombol Start ditekan.
- Tombol Mulai **terpotong/tidak terlihat** saat jendela kecil karena tidak ada scroll.
- Layout **tidak mengikuti** saat jendela di-maximize (bobot grid belum diatur).
- **Tabrakan nama file output** di folder khusus — dua sumber bernama sama kini otomatis diberi akhiran ` (2)`.
- Menu klik-kanan **"Buka lokasi hasil"** tidak berfungsi (salah sintaks `os.startfile`).
- **Deteksi GPU membekukan UI** saat berganti engine — kini berjalan di background thread dan di-cache.
- Daftar model tidak cocok dengan isi `tools/` (mis. `realesrnet-x4plus` tidak ada di zip Windows; Real-CUGAN PRO hanya 2x/3x).

### Diubah

- Progress bar kini menampilkan **progres keseluruhan antrean** (sebelumnya hanya per-file yang berulang 0–100).
- README diringkas menjadi deskripsi singkat; detail dipindah ke `docs/`.

## [1.0.0] - 2026-09-28

### Ditambahkan

- Rilis perdana: GUI tkinter bertema gelap dengan **drag & drop** (tkinterdnd2) untuk gambar maupun folder.
- Tiga engine upscaler ncnn-Vulkan siap pakai — **waifu2x**, **Real-CUGAN**, **Real-ESRGAN** — dengan unduhan otomatis saat dibutuhkan.
- Batch queue dengan status per file, progres, tombol batalkan, dan log berwarna.
- Pratinjau **sebelum/sesudah** dengan zoom (Ctrl+scroll) dan pan.
- Output PNG (transparan aman) / JPG / WebP dengan slider kualitas; folder asal atau folder khusus; opsi lewati file yang sudah ada.
- Pengaturan ukuran tile untuk VRAM terbatas, mode TTA, pemilihan GPU/CPU.
- Semua pengaturan tersimpan otomatis ke `config.json`.
