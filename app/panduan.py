"""Konten panduan & daftar fitur WaifuUpscaler yang TERTANAM di aplikasi.

Ditampilkan oleh jendela "Panduan & Fitur" (menu Bantuan / tombol ❓ / F1)
sehingga panduan tetap tersedia walau folder docs/ tidak ikut saat
aplikasi dibagikan. Sumber naratif panjang tetap docs/PANDUAN.md —
jaga keduanya tetap selaras saat mengubah fitur.

Struktur SECTIONS: list of {"judul": str, "isi": [(kind, teks), ...]}.
Kind yang dikenal renderer (gui.PanduanWindow):
  "p"   paragraf biasa
  "b"   bullet (penanda •  otomatis)
  "h"   sub-judul kecil (tebal)
  "n"   catatan kecil miring (abu-abu)
  "row" baris tabel monospace (kolom dipadding manual)
  "pre" blok monospace (pertahankan spasi)
"""
from __future__ import annotations

from typing import List

SECTIONS: List[dict] = [
    {
        "judul": "🚀 Alur Dasar",
        "isi": [
            ("p", "Lima langkah dari buka aplikasi sampai hasil jadi:"),
            ("b", "1.  Klik dua kali run.bat (setup pertama berjalan otomatis)."),
            ("b", "2.  Tarik & lepas gambar/folder ke jendela — atau klik dua kali "
                  "area daftar, atau pakai tombol ＋ Tambah File / 📁 Tambah Folder."),
            ("b", "3.  Atur Engine → Model → Skala → Denoise di panel Engine & Kualitas."),
            ("b", "4.  Tekan ▶ Mulai Proses — pantau progres & panel Log."),
            ("b", "5.  Klik dua kali baris berstatus Selesai untuk pratinjau "
                  "sebelum/sesudah."),
            ("n", "Tekan F1 kapan saja untuk membuka jendela panduan ini."),
        ],
    },
    {
        "judul": "✨ Fitur Lengkap",
        "isi": [
            ("b", "🖱️ Drag & drop gambar atau folder ke mana saja di jendela; drop "
                  "folder memindai subfolder (bisa dimatikan lewat checkbox "
                  "\"Ikuti subfolder saat menambah folder\"). Format dikenali: "
                  "PNG, JPG/JPEG, WEBP, BMP, TIF/TIFF, GIF."),
            ("b", "🔄 Opsi model otomatis — model/skala/denoise yang tampil di UI "
                  "dipindai dari file model asli di tools/, jadi kombinasi yang "
                  "tidak ada tidak pernah ditawarkan."),
            ("b", "🧑‍🎤 Kategori model (dropdown Kategori): filter daftar model jadi "
                  "Semua / Anime / Foto — model foto real manusia langsung "
                  "kelihatan tanpa menabur daftar anime."),
            ("b", "📥 Kelola model foto (tombol Kelola foto…): unduh model foto ncnn "
                  "tambahan — Upscayl Lite (±2,4 MB, cepat) dan Upscayl Standard "
                  "(±33 MB, kualitas umum terbaik) — yang berjalan di engine "
                  "Real-ESRGAN bawaan. File diambil dari clone upscayl lokal bila "
                  "ada, selain itu GitHub (commit ter-pin). Model siap otomatis "
                  "muncul di dropdown."),
            ("b", "🎚️ Emulasi skala 1x-3x untuk model fixed-4x ala Upscayl "
                  "(\"Downscayl\"): upscale native 4x lalu diturunkan LANCZOS — "
                  "dropdown skala model 4x menawarkan 1x-4x lengkap."),
            ("b", "🧯 Preflight: kombinasi divalidasi saat menekan Mulai — kalau "
                  "bermasalah, muncul dialog penjelasan alih-alih gagal diam-diam "
                  "per file."),
            ("b", "🎚️ Denoise tersinkron per skala: saat ganti skala, slider "
                  "otomatis menyesuaikan level yang tersedia untuk model itu."),
            ("b", "🧱 Ukuran tile: VRAM kecil → pilih 64/128; Auto mengikuti ukuran "
                  "gambar."),
            ("b", "🧪 Mode TTA (Test-Time Augmentation): hasil sedikit lebih bagus, "
                  "sekitar 2× lebih lambat."),
            ("b", "🖥️ Pilihan GPU: terdeteksi otomatis; tersedia mode CPU (-1) "
                  "darurat (sangat lambat)."),
            ("b", "📊 Progres keseluruhan antrean + waktu per file + statistik "
                  "ringkasan di status bar; tombol ■ Batalkan aktif kapan saja."),
            ("b", "☑️ Checkbox per gambar: tandai beberapa gambar (atau Pilih Semua / "
                  "klik header kolom ☐) lalu tekan 🗑 Hapus Tercentang. Tombol "
                  "🧹 Bersihkan Daftar mengosongkan seluruh antrean, 🧹 Bersihkan "
                  "Log mengosongkan panel log. Klik kanan baris membuka menu "
                  "centang/buka file/gambar. Gambar yang sedang diproses selalu "
                  "dilindungi dari penghapusan."),
            ("b", "🖼️ Pratinjau sebelum/sesudah: radio Sesudah/Sebelum, zoom "
                  "Ctrl+scroll atau slider, pan dengan drag, tombol Fit, Esc untuk "
                  "menutup."),
            ("b", "🗂️ Mode tampilan daftar (dropdown Tampilan:): Detail, Ikon Kecil, "
                  "Ikon Sedang, Ikon Besar, Ikon Ekstra Besar — thumbnail tampil "
                  "berdampingan dengan nama file, pilihan tersimpan otomatis."),
            ("b", "🗂️ Section bisa dilipat: klik strip judul Daftar Gambar, "
                  "Pengaturan, atau Log (chevron ▾/▸). Saat satu section dilipat, "
                  "section di bawahnya otomatis naik mengisi ruang kosongnya."),
            ("b", "📖 Menu Bantuan: jendela Panduan & Fitur (yang sedang kamu baca), "
                  "pembuka file docs/PANDUAN.md, dan dialog Tentang. Bisa dibuka "
                  "dengan tombol ❓ Panduan di pojok kanan atas atau tombol F1."),
            ("n", "Detail teknis tiap fitur ada di docs/PANDUAN.md dan "
                  "docs/ARSITEKTUR.md di folder aplikasi."),
        ],
    },
    {
        "judul": "⚙️ Engine & Model",
        "isi": [
            ("p", "Tiga engine ncnn-Vulkan berjalan penuh di GPU (NVIDIA/AMD/Intel "
                  "dengan driver Vulkan) lewat executable portabel di folder "
                  "tools/ — tanpa PyTorch. Engine diunduh otomatis saat pertama "
                  "kali dipakai."),
            ("h", "waifu2x-ncnn-vulkan — anime klasik"),
            ("b", "CUNET · kualitas terbaik (1x/2x/4x) — pilihan utama untuk anime "
                  "dan ilustrasi."),
            ("b", "UPCONV7 anime (2x/4x) — paling responsif; ada juga varian "
                  "UPCONV7 foto untuk foto cepat."),
            ("h", "real-cugan-ncnn-vulkan — anime tajam"),
            ("b", "Model SE dan PRO (2x-4x). Khusus anime — kurang cocok untuk "
                  "foto."),
            ("h", "real-esrgan-ncnn-vulkan — serbaguna + foto"),
            ("b", "AnimeVideoV3 (2x/3x/4x) — ideal untuk batch anime super cepat."),
            ("b", "x4plus · umum/foto (1x-4x, skala 1x-3x diemulasi) — model "
                  "dunia-nyata bawaan."),
            ("b", "Upscayl Lite & Standard · foto (1x-4x, skala 1x-3x diemulasi) — "
                  "unduh dulu lewat tombol Kelola foto…."),
            ("n", "Baris Upscayl perlu diunduh dulu; semua model lain tersedia "
                  "setelah engine-nya terunduh — tanpa unduhan tambahan."),
        ],
    },
    {
        "judul": "🎯 Rekomendasi Model",
        "isi": [
            ("p", "Panduan cepat memilih model (filter dropdown Kategori jadi Foto "
                  "untuk menyembunyikan model anime):"),
            ("row", "JENIS GAMBAR                  ENGINE      MODEL          SKALA"),
            ("row", "─" * 66),
            ("row", "Anime/ilustrasi terbaik       Waifu2x     CUNET          1x/2x/4x"),
            ("row", "Anime/ilustrasi cepat         Waifu2x     UPCONV7 anime  2x/4x"),
            ("row", "Anime tajam                   Real-CUGAN  SE / PRO       2x-4x"),
            ("row", "Anime batch super cepat       Real-ESRGAN AnimeVideoV3   2x/3x/4x"),
            ("row", "Foto manusia/objek terbaik    Real-ESRGAN Upscayl Std    1x-4x"),
            ("row", "Foto/gambar umum              Real-ESRGAN x4plus         1x-4x"),
            ("row", "Foto cepat & ringan           Real-ESRGAN Upscayl Lite   1x-4x"),
            ("row", "Foto cepat (waifu2x)          Waifu2x     UPCONV7 foto   2x/4x"),
            ("b", "Denoise 1-2 disarankan untuk JPEG ber-noise; 0 (tanpa denoise) "
                  "untuk gambar yang sudah bersih."),
        ],
    },
    {
        "judul": "📂 Output & Penamaan File",
        "isi": [
            ("h", "Folder output"),
            ("b", "Folder asal — hasil tersimpan di samping gambar aslinya, "
                  "dengan akhiran nama (bawaan: _upscaled, bisa diubah)."),
            ("b", "Folder khusus — semua hasil terkumpul di satu folder pilihan "
                  "(bawaan: folder output/ di dalam folder aplikasi)."),
            ("h", "Penamaan otomatis ber-cap waktu"),
            ("b", "Semua nama file output diawali tanggal-jam sampai detik: "
                  "YYYYMMDD-HHMMSS-namafile.ext."),
            ("b", "Contoh: 20261120-143052-gambar.png — folder asal menghasilkan "
                  "20261120-143052-gambar_upscaled.png."),
            ("b", "Karena cap waktunya beda tiap proses, gambar yang SAMA bisa "
                  "di-upscale berkali-kali tanpa pernah menimpa hasil lama — "
                  "setiap proses menghasilkan file baru."),
            ("b", "Dua sumber bernama sama yang diproses di antrean yang sama "
                  "otomatis diberi akhiran (2) agar tidak saling menimpa."),
            ("h", "Format & kualitas"),
            ("b", "PNG — lossless, aman untuk transparan."),
            ("b", "JPG — file kecil; WEBP — modern & ringan; keduanya punya "
                  "slider kualitas 40-100."),
            ("h", "Lainnya"),
            ("b", "Checkbox Buka folder output setelah selesai membuka folder "
                  "hasil otomatis ketika antrean tuntas."),
            ("b", "Semua pengaturan (engine, model, skala, folder output, "
                  "tampilan, ukuran jendela) tersimpan otomatis di config.json."),
        ],
    },
    {
        "judul": "📁 Format File",
        "isi": [
            ("b", "Input langsung: PNG, JPG/JPEG, WEBP."),
            ("b", "Dikonversi otomatis ke PNG sementara: BMP, TIF/TIFF, GIF "
                  "(frame pertama)."),
            ("b", "Output: PNG (transparan aman) · JPG · WEBP + slider kualitas "
                  "(40-100)."),
        ],
    },
    {
        "judul": "🧾 Membaca Panel Log",
        "isi": [
            ("b", "[HH:MM:SS] +N gambar masuk antrean — file berhasil ditambahkan."),
            ("b", "Selesai · 2.4s — waktu proses per file (kolom Status)."),
            ("b", "[GAGAL] nama.png — <pesan> — pesan asli dari engine; baris "
                  "Catatan: di bawahnya adalah saran perbaikan otomatis (mis. "
                  "Vulkan tidak tersedia → perbarui driver GPU)."),
            ("b", "Ringkasan akhir di status bar: total waktu, berhasil, gagal."),
        ],
    },
    {
        "judul": "🧯 Troubleshooting",
        "isi": [
            ("b", "\"Vulkan tidak tersedia\" / engine langsung gagal → perbarui "
                  "driver GPU (NVIDIA/AMD/Intel). Darurat: pilih CPU (-1) di "
                  "dropdown GPU (sangat lambat)."),
            ("b", "Dialog \"Kombinasi tidak tersedia\" → skala/denoise tidak punya "
                  "file modelnya — pilih kombinasi lain; UI memang hanya "
                  "menampilkan yang valid."),
            ("b", "Drag & drop tidak jalan → pastikan tkinterdnd2 terpasang; "
                  "jalankan lewat run.bat (memasang otomatis dari "
                  "requirements.txt). Alternatif: tombol ＋ Tambah File."),
            ("b", "Engine diunduh ulang terus → folder tools/ jangan dihapus atau "
                  "dibersihkan antivirus; whitelist jika perlu."),
            ("b", "Hasil aneh di foto → jangan pakai model anime: filter "
                  "Kategori: Foto lalu pilih Upscayl Standard · foto umum atau "
                  "x4plus · umum/foto (Real-ESRGAN)."),
            ("b", "Proses lambat / VRAM penuh → kecilkan Ukuran tile (128/64), "
                  "matikan TTA, atau turunkan skala."),
        ],
    },
    {
        "judul": "📁 Struktur Folder",
        "isi": [
            ("pre",
             "waifu-upscaler/\n"
             "├── run.bat            ← klik dua kali file ini\n"
             "├── requirements.txt\n"
             "├── config.json        ← dibuat otomatis (pengaturan tersimpan)\n"
             "├── app/               ← kode Python (GUI + integrasi engine) + assets/\n"
             "├── scripts/           ← generator aset (make_icon.py)\n"
             "├── tools/             ← engine ncnn-Vulkan + model (unduh otomatis)\n"
             "├── output/            ← folder output bawaan\n"
             "└── docs/              ← dokumentasi (PANDUAN.md, ARSITEKTUR.md)"),
        ],
    },
    {
        "judul": "🌸 Tentang & Kredit",
        "isi": [
            ("p", "WaifuUpscaler — upscale gambar anime & foto di GPU, tanpa "
                  "PyTorch, tanpa ribet."),
            ("b", "waifu2x-ncnn-vulkan — nihui (github.com/nihui/waifu2x-ncnn-vulkan)"),
            ("b", "realcugan-ncnn-vulkan — nihui (github.com/nihui/realcugan-ncnn-vulkan)"),
            ("b", "Real-ESRGAN — xinntao (github.com/xinntao/Real-ESRGAN)"),
            ("b", "Model foto Upscayl Standard & Lite — tim Upscayl "
                  "(github.com/upscayl/upscayl)"),
            ("n", "Lisensi tiap engine/model mengikuti repo asalnya; model Upscayl "
                  "untuk pemakaian pribadi."),
            ("n", "Panduan lengkap versi file: docs/PANDUAN.md · Riwayat versi: "
                  "CHANGELOG.md · Arsitektur internal: docs/ARSITEKTUR.md."),
        ],
    },
]
