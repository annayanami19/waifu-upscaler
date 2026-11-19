# Changelog

Semua perubahan penting pada proyek ini akan didokumentasikan di file ini.

Format mengikuti [Keep a Changelog](https://keepachangelog.com/id/1.1.0/),
dan versi mengikuti [Semantic Versioning](https://semver.org/lang/id/).

## [1.6.0] - 2026-11-20

### Ditambahkan

- **Menu Bantuan bawaan** — menubar baru di atas jendela berisi *Panduan & Fitur…*, *Buka PANDUAN.md di editor*, dan *Tentang WaifuUpscaler*. Jendela *Panduan & Fitur* menampilkan panduan lengkap + daftar seluruh fitur yang **tertanam di aplikasi** (`app/panduan.py`, tetap ada walau folder `docs/` tidak ikut) dengan dropdown *Lompat ke bagian*, tombol ⬆ Ke Atas, scroll roda mouse, dan Esc untuk menutup. Dibuka juga lewat tombol **❓ Panduan** di pojok kanan atas header atau tombol **F1**.
- **Penamaan output ber-cap waktu** — semua nama file output kini diawali tanggal-jam sampai detik (`YYYYMMDD-HHMMSS-namafile.ext`, contoh: `20261120-143052-gambar.png`). Mode folder asal ikut memakai cap waktu di depan (akhiran `_upscaled` tetap dipertahankan), mode folder khusus memakai `tanggal-jam-namafile.ext`.

### Diubah

- **Fitur "Lewati file yang output-nya sudah ada" dihapus** — digantikan cap waktu di atas: gambar yang sama kini bisa di-upscale berkali-kali dan setiap hasil tersimpan sebagai file baru, tidak pernah menimpa hasil sebelumnya. Checkbox serta kunci `skip_existing` di `config.json` tidak lagi dipakai (nilai sisa di config lama diabaikan otomatis).

### Diperbaiki

- **Navigasi "Lompat ke bagian" di jendela Panduan & Fitur** — lompatan sebelumnya tidak sesuai karena dua hal: gravitasi mark bawaan (`right`) mendorong mark ke baris kosong sesudah judul, dan `yview_pickplace` tidak menggerakkan view bila bagian tujuan kebetulan sudah terlihat. Kini mark dipasang dengan gravitasi `left` (persis di baris judulnya) dan lompatan mengukur posisi piksel baris judul (`see` + `dlineinfo` + `yview_scroll`) sehingga judul bagian selalu mendarat di puncak jendela.

## [1.5.0] - 2026-11-18

### Ditambahkan

- **Dukungan foto real manusia** — tiga fitur baru dari referensi arsitektur Upscayl:
  - **Kategori model (Semua/Anime/Foto)** — dropdown *Kategori* baru di panel *Engine & Kualitas* memfilter daftar model; kategori ditandai otomatis dari id model (`realesrgan-x4plus`, `upscayl-*`, `upconv7-photo` = foto; sisanya anime). Pilihan tersimpan di `config.json`.
  - **Kelola model foto** — dialog baru (tombol *Kelola foto…*) berisi katalog model foto ncnn yang kompatibel dengan engine Real-ESRGAN yang sudah ada: **Upscayl Lite** (±2,4 MB, cepat) dan **Upscayl Standard** (±33 MB, kualitas umum terbaik). File diambil hemat: disalin dari clone upscayl lokal bila ada, selain itu diunduh dari repo resmi `upscayl/upscayl` (commit ter-pin). Model siap langsung muncul di dropdown tanpa ubah kode.
  - **Emulasi skala 1x-3x ala Upscayl ("Downscayl")** — model fixed-4x (x4plus, model foto Upscayl) kini bisa dipakai di skala 1x/2x/3x: inferensi dijalankan penuh di skala native 4x lalu hasilnya diturunkan LANCZOS di Python (binary official realesrgan tidak punya downscale bawaan). Dropdown skala model 4x kini menawarkan 1x-4x lengkap dengan catatan emulasi.
- Script uji headless `scripts/test_foto_models.py` — memverifikasi kategori, argumen skala, dan alur end-to-end (PNG uji 64×64 → engine → 256×256 → downscale 128×128) tanpa GUI.

### Catatan

- Model Upscayl yang diunduh berlisensi pemakaian pribadi yang sah; untuk rilis publik, ceklis lisensi per model (varian komunitas seperti Remacri/UltraSharp di Upscayl berlabel Non-Commercial — tidak diikutkan katalog).
- Branding aplikasi kini menyebut anime **& foto** (judul jendela + subtitle header).

## [1.4.0] - 2026-10-03

### Ditambahkan

- **Logo aplikasi di header, beranimasi** — emoji 🌸 pada judul diganti logo bunga sakura asli aplikasi. Bunga **berputar terus-menerus** di header dan **melaju lebih cepat selama proses upscale berjalan**, berhenti menggambar saat jendela diminimize (hemat CPU). Framanya dirender saat aplikasi jalan dari master `app/assets/logo.png` (RGBA resolusi tinggi, dirotasi PIL) — bukan GIF — sehingga bebas artefak bintik palet. Aset dibuat ulang via `python scripts/make_icon.py`.

## [1.3.0] - 2026-10-03

### Ditambahkan

- **Collapse/uncollapse section** — panel **Daftar Gambar**, **Pengaturan**, dan **Log** bisa dilipat/bentangkan lewat strip judul masing-masing (chevron ▾/▸); saat dilipat hanya strip judul yang tampil, section di bawahnya **otomatis naik mengisi ruang**, dan posisi grid tiap panel diingat saat di-expand kembali.
- **Mode tampilan daftar gambar** — seperti menu View di Windows Explorer: **Detail**, **Ikon Kecil**, **Ikon Sedang**, **Ikon Besar**, dan **Ikon Ekstra Besar**. Thumbnail gambar tampil di daftar berdampingan dengan nama file; pilihan tersimpan otomatis di config.
- Thumbnail dibuat di **background thread** (UI tetap responsif), menghormati **orientasi EXIF** kamera, memakai placeholder saat dimuat, dan file yang gagal dibaca ditampilkan sebagai kotak placeholder.

## [1.2.0] - 2026-10-03

### Ditambahkan

- **Ikon aplikasi kustom** (bunga sakura) untuk title bar, taskbar, dan Alt-Tab — tidak lagi memakai ikon Python bawaan. Aset di `app/assets/` (`.ico` multi-ukuran 16–256 px + `.png` fallback), dibuat ulang dengan `python scripts/make_icon.py`.
- **Checkbox per gambar** di kolom paling kiri daftar — klik untuk menandai gambar yang ingin dihapus, lalu hapus semuanya sekaligus lewat tombol **🗑 Hapus Tercentang (N)** (sebelumnya hanya bisa hapus satu per satu).
- **Pilih Semua**: centang/lepas semua gambar sekaligus lewat checkbox di toolbar atau klik header kolom ☐ (menampilkan ▣ saat sebagian tercentang).
- **Bersihkan Daftar**: tombol untuk mengosongkan seluruh daftar gambar sekali klik (dipindah ke toolbar daftar gambar).
- **Bersihkan Log**: tombol untuk mengosongkan panel log.
- Menu klik-kanan kini punya aksi **Centang / Lepas centang pilihan**.

### Diperbaiki

- **Worker crash saat item dihapus dari daftar** ketika antrean sedang berjalan (`KeyError` karena item tidak lagi ada di daftar) — kini item yang sudah dihapus otomatis dilewati dengan aman.
- Hapus borongan melindungi gambar yang **sedang diproses** — item itu dilewati dan jumlahnya diberitahukan di log.
- Klik ganda di kolom centang tidak lagi memicu aksi pratinjau.

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
