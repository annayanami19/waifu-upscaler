"""GUI WaifuUpscaler — tkinter + drag & drop (tkinterdnd2), tema gelap.

Struktur jendela:
  baris 0 : header (tetap)
  baris 1 : konten scrollable (daftar gambar + pengaturan + log)
  baris 2 : footer (progress, status, tombol Mulai) — SELALU terlihat
"""
from __future__ import annotations

import os
import queue
import re
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
import traceback
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Optional

from PIL import Image, ImageDraw, ImageOps, ImageTk

from .config import (
    APP_NAME,
    APP_VERSION,
    ICON_ICO,
    ICON_PNG,
    OUTPUT_DIR,
    load_config,
    save_config,
)
from .downloader import DownloadCancelled, download_zip
from .engines import (
    ENGINES,
    EngineError,
    TaskCancelled,
    build_commands,
    encode_output,
    enumerate_gpus,
    find_exe,
    invalidate_exe_cache,
    list_models,
    move_file,
    prepare_input,
    run_engine,
    validate_combo,
)

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD

    HAS_DND_LIB = True
except Exception:  # pragma: no cover - fallback tanpa drag & drop
    DND_FILES = "DND_Files"
    HAS_DND_LIB = False

IMG_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff", ".gif"}

# --- Mode tampilan daftar gambar (meniru menu View di Windows Explorer) ---
VIEW_LABELS = {  # key config -> label combobox (urutan dict = urutan tampil)
    "detail": "Detail",
    "small": "Ikon Kecil",
    "medium": "Ikon Sedang",
    "large": "Ikon Besar",
    "xlarge": "Ikon Ekstra Besar",
}
VIEW_PX = {"small": 32, "medium": 64, "large": 128, "xlarge": 256}      # sisi thumbnail
VIEW_ROW = {"detail": 26, "small": 46, "medium": 86, "large": 152, "xlarge": 280}
VIEW_COL0 = {"small": 290, "medium": 350, "large": 500, "xlarge": 680}  # lebar kolom nama+gambar
VIEW_H = {"detail": 8, "small": 6, "medium": 4, "large": 3, "xlarge": 2}  # jumlah baris minimum

FORMAT_LABELS = {
    "PNG · lossless, dukung transparan": "png",
    "JPG · file kecil": "jpg",
    "WEBP · modern, ringan": "webp",
}
TILE_LABELS = {
    "Auto (ikut ukuran gambar)": 0,
    "64 · VRAM kecil": 64,
    "128 · VRAM hemat": 128,
    "256": 256,
    "512 · VRAM besar": 512,
}
DEN_LABELS = {
    -1: "-1 · tanpa denoise",
    0: "0 · ringan",
    1: "1 · sedang",
    2: "2 · kuat",
    3: "3 · maksimal",
}

C = {
    "bg": "#14151a",
    "panel": "#1c1e26",
    "panel2": "#232633",
    "field": "#262a37",
    "border": "#343a4a",
    "fg": "#e8eaf0",
    "mut": "#8d95a8",
    "acc": "#82aaff",
    "accd": "#5b7bd5",
    "ok": "#8ce99a",
    "warn": "#ffd43b",
    "err": "#ff8787",
    "sel": "#35507e",
}

STATUS_TAGS = {
    "Selesai": "ok",
    "Gagal": "err",
    "Dilewati": "mut",
    "Dibatalkan": "warn",
    "Memproses": "acc",
    "Menunggu": "fg",
}

# Widget yang punya scroll sendiri — roda mouse di atasnya jangan menggulir konten.
_WIDGET_SCROLL_SENDIRI = (ttk.Treeview, tk.Text, tk.Listbox, ttk.Scrollbar)


def _fmt_size(path: Path) -> str:
    try:
        n = path.stat().st_size
    except OSError:
        return "-"
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return "-"


def create_root() -> tk.Tk:
    if HAS_DND_LIB:
        try:
            return TkinterDnD.Tk()
        except Exception:
            pass
    return tk.Tk()


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.cfg = load_config()
        self.items: Dict[str, dict] = {}
        self.order: List[str] = []
        self.results: Dict[str, str] = {}
        self.produced: Dict[str, str] = {}  # path output -> path sumber (cegah tabrakan nama)
        self.ui_q: "queue.Queue[tuple]" = queue.Queue()
        self.cancel_event = threading.Event()
        self.dl_cancel = threading.Event()
        self.running = False
        self.t_start = 0.0
        self._auto_start = False
        self._icon_photo = None
        self._thumb_cache: Dict[str, Dict[str, ImageTk.PhotoImage]] = {}
        self._placeholder_cache: Dict[tuple, ImageTk.PhotoImage] = {}
        self._thumb_q: "queue.Queue[tuple]" = queue.Queue()
        self._thumb_gen = 0
        self._thumb_worker_started = False
        self._section_header: Dict[str, ttk.Frame] = {}
        self._section_chev: Dict[str, ttk.Label] = {}
        self._section_body: Dict[str, ttk.Widget] = {}
        self._collapsed: Dict[str, bool] = {}
        self.dl_win: Optional[tk.Toplevel] = None
        self._gpu_cache: Dict[str, list] = {}
        self._gpu_running: Dict[str, bool] = {}

        self.engine_by_label: Dict[str, str] = {e.label: k for k, e in ENGINES.items()}
        self.model_by_label: Dict[str, str] = {}
        self.scale_by_label: Dict[str, int] = {}
        self.gpu_map: Dict[str, str] = {}

        root.title(f"{APP_NAME} v{APP_VERSION} — Upscale Gambar Anime")
        root.minsize(760, 520)
        root.configure(bg=C["bg"])
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)  # hanya area konten yang melar

        self._apply_geometry()
        self._apply_icon()

        self._build_styles()
        self._build_vars()
        self._build_header()
        self._build_content()
        self._build_queue()
        self._build_settings()
        self._build_log()
        self._relayout_section_weights()  # baris fleksibel bawaan: Daftar Gambar
        self._build_footer()
        self._bind_dnd()
        self._restore_settings()
        self._engine_changed()
        self._refresh_engine_status()
        self._update_counts()
        self._update_check_state()
        self._apply_view_mode()

        root.bind_all("<MouseWheel>", self._on_mousewheel)
        root.protocol("WM_DELETE_WINDOW", self._on_close)
        root.after(80, self._poll)
        root.after(150, self._sync_scrollbar)

    # ------------------------------------------------------- geometri

    def _apply_geometry(self):
        root = self.root
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        w = int(self.cfg.get("window_w") or min(1150, sw - 100))
        h = int(self.cfg.get("window_h") or min(820, sh - 120))
        w = min(max(w, 760), max(760, sw - 40))
        h = min(max(h, 520), max(520, sh - 80))
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 3)
        root.geometry(f"{w}x{h}+{x}+{y}")
        if self.cfg.get("window_zoomed"):
            root.after(60, lambda: self._safe_zoom())

    def _safe_zoom(self):
        try:
            self.root.state("zoomed")
        except Exception:
            pass

    def _apply_icon(self):
        """Ikon aplikasi untuk title bar & taskbar.

        Windows: icon.ico multi-ukuran via iconbitmap(-default) — berlaku juga
        untuk semua Toplevel (pratinjau, dialog unduhan). iconphoto TIDAK
        dipakai di Windows karena menimpa .ico (lihat man page wm).
        Fallback lintas platform: icon.png via iconphoto.
        Kegagalan tidak boleh menghalangi aplikasi jalan.
        """
        if sys.platform == "win32" and ICON_ICO.exists():
            try:
                self.root.iconbitmap(default=str(ICON_ICO))
                return
            except Exception:
                pass
        if ICON_PNG.exists():
            try:
                photo = tk.PhotoImage(file=str(ICON_PNG))
                self.root.iconphoto(True, photo)
                self._icon_photo = photo  # cegah GC — PhotoImage harus tetap hidup
            except Exception:
                pass

    # ------------------------------------------------------------ UI

    def _build_styles(self):
        st = ttk.Style(self.root)
        self._style = st  # referensi untuk mengubah rowheight saat ganti mode tampilan
        st.theme_use("clam")
        st.configure(".", background=C["panel"], foreground=C["fg"], bordercolor=C["border"],
                     lightcolor=C["panel"], darkcolor=C["panel"], troughcolor=C["field"],
                     focuscolor=C["panel"], selectbackground=C["sel"], selectforeground=C["fg"])
        st.configure("Bg.TFrame", background=C["bg"])
        st.configure("TFrame", background=C["panel"])
        st.configure("Bg.TLabel", background=C["bg"], foreground=C["fg"])
        st.configure("Mut.TLabel", background=C["panel"], foreground=C["mut"])
        st.configure("BgMut.TLabel", background=C["bg"], foreground=C["mut"])
        st.configure("Section.TLabel", background=C["panel"], foreground=C["acc"],
                     font=("Segoe UI", 9, "bold"))
        st.configure("Chevron.TLabel", background=C["panel"], foreground=C["acc"],
                     font=("Segoe UI", 10, "bold"), width=3, anchor="center")
        st.configure("Acc.TLabel", background=C["panel"], foreground=C["acc"])
        st.configure("TLabel", background=C["panel"], foreground=C["fg"])
        st.configure("TLabelframe", background=C["panel"], bordercolor=C["border"], relief="solid")
        st.configure("TLabelframe.Label", background=C["panel"], foreground=C["acc"],
                     font=("Segoe UI", 9, "bold"))
        st.configure("TButton", background=C["panel2"], foreground=C["fg"], borderwidth=0,
                     focusthickness=0, padding=(12, 8))
        st.map("TButton",
               background=[("disabled", C["panel"]), ("active", "#2e3342")],
               foreground=[("disabled", C["mut"])])
        st.configure("Primary.TButton", background=C["accd"], foreground="#ffffff",
                     borderwidth=0, focusthickness=0, padding=(20, 10),
                     font=("Segoe UI", 10, "bold"))
        st.map("Primary.TButton",
               background=[("disabled", C["field"]), ("pressed", C["acc"]), ("active", C["acc"])],
               foreground=[("disabled", C["mut"])])
        st.configure("Danger.TButton", background="#5c2b2b", foreground="#ffb4b4",
                     borderwidth=0, focusthickness=0, padding=(14, 9))
        st.map("Danger.TButton",
               background=[("disabled", C["panel"]), ("active", "#7a3636")],
               foreground=[("disabled", C["mut"])])
        st.configure("TEntry", fieldbackground=C["field"], foreground=C["fg"],
                     bordercolor=C["border"], lightcolor=C["border"], darkcolor=C["border"],
                     insertcolor=C["fg"])
        st.configure("TCombobox", fieldbackground=C["field"], background=C["panel2"],
                     foreground=C["fg"], arrowcolor=C["fg"], bordercolor=C["border"],
                     lightcolor=C["border"], darkcolor=C["border"], padding=4)
        st.map("TCombobox", fieldbackground=[("readonly", C["field"])],
               foreground=[("disabled", C["mut"])])
        st.configure("TCheckbutton", background=C["panel"], foreground=C["fg"], focuscolor=C["panel"])
        st.map("TCheckbutton", background=[("active", C["panel"])],
               foreground=[("disabled", C["mut"])])
        st.configure("TRadiobutton", background=C["panel"], foreground=C["fg"], focuscolor=C["panel"])
        st.map("TRadiobutton", background=[("active", C["panel"])])
        st.configure("TScale", troughcolor=C["field"], background=C["accd"],
                     bordercolor=C["panel"], lightcolor=C["accd"], darkcolor=C["accd"])
        st.configure("Accent.Horizontal.TProgressbar", troughcolor=C["field"],
                     background=C["acc"], borderwidth=0, thickness=12)
        st.configure("Treeview", background=C["panel2"], fieldbackground=C["panel2"],
                     foreground=C["fg"], rowheight=26, borderwidth=0)
        st.map("Treeview", background=[("selected", C["sel"])],
               foreground=[("selected", C["fg"])])
        st.configure("Treeview.Heading", background=C["panel"], foreground=C["mut"],
                     relief="flat", padding=(6, 6))
        st.map("Treeview.Heading", background=[("active", C["panel"])])
        st.configure("Vertical.TScrollbar", background=C["panel2"], troughcolor=C["panel"],
                     bordercolor=C["panel"], arrowcolor=C["mut"], relief="flat")
        st.configure("Horizontal.TScrollbar", background=C["panel2"], troughcolor=C["panel"],
                     bordercolor=C["panel"], arrowcolor=C["mut"], relief="flat")
        self.root.option_add("*TCombobox*Listbox.background", C["panel2"])
        self.root.option_add("*TCombobox*Listbox.foreground", C["fg"])
        self.root.option_add("*TCombobox*Listbox.selectBackground", C["accd"])
        self.root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
        self.root.option_add("*TCombobox*Listbox.font", ("Segoe UI", 9))

    def _build_vars(self):
        self.var_engine = tk.StringVar()
        self.var_model = tk.StringVar()
        self.var_scale = tk.StringVar(value="2x")
        self.var_denoise = tk.DoubleVar(value=self.cfg.get("denoise", 0))
        self.var_tile = tk.StringVar(value="Auto (ikut ukuran gambar)")
        self.var_gpu = tk.StringVar(value="Auto (pilihan Vulkan)")
        self.var_tta = tk.BooleanVar(value=False)
        self.var_format = tk.StringVar(value="PNG · lossless, dukung transparan")
        self.var_quality = tk.IntVar(value=self.cfg.get("quality", 90))
        self.var_out_mode = tk.StringVar(value="custom")
        self.var_out_dir = tk.StringVar(value=str(OUTPUT_DIR))
        self.var_suffix = tk.StringVar(value=self.cfg.get("suffix", "_upscaled"))
        self.var_subfolders = tk.BooleanVar(value=True)
        self.var_skip = tk.BooleanVar(value=True)
        self.var_auto_open = tk.BooleanVar(value=False)
        self.var_check_all = tk.BooleanVar(value=False)
        self.var_view = tk.StringVar(value=VIEW_LABELS["detail"])

    def _build_header(self):
        head = ttk.Frame(self.root, style="Bg.TFrame")
        head.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 6))
        head.columnconfigure(0, weight=1)
        left = ttk.Frame(head, style="Bg.TFrame")
        left.grid(row=0, column=0, sticky="w")
        ttk.Label(left, text="🌸 WaifuUpscaler", style="Bg.TLabel",
                  font=("Segoe UI", 17, "bold"), foreground=C["acc"]).pack(anchor="w")
        ttk.Label(left, text="Upscale gambar anime di GPU (Vulkan) · waifu2x · Real-CUGAN · Real-ESRGAN",
                  style="BgMut.TLabel").pack(anchor="w")
        self.lbl_engines = ttk.Label(head, text="", style="BgMut.TLabel", justify="right")
        self.lbl_engines.grid(row=0, column=1, sticky="e")

    def _build_content(self):
        """Area yang bisa di-scroll: daftar gambar + pengaturan + log."""
        outer = ttk.Frame(self.root, style="Bg.TFrame")
        outer.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 6))
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(outer, bg=C["bg"], highlightthickness=0, bd=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vsb = ttk.Scrollbar(outer, orient="vertical", command=self.canvas.yview)
        self.vsb.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=self.vsb.set)

        self.content = ttk.Frame(self.canvas, style="Bg.TFrame")
        self.content.columnconfigure(0, weight=1)
        # Baris body yang melar diatur dinamis oleh _relayout_section_weights():
        # hanya section yang sedang terbuka yang mengisi sisa ruang, supaya
        # section lain tidak tertinggal/terdorong ke bawah saat ada yang
        # dilipat. grid_anchor "nw" membuat konten menempel atas saat tidak
        # ada baris yang melar (mis. semua section dilipat).
        self.content.grid_anchor("nw")
        self._content_win = self.canvas.create_window((0, 0), window=self.content, anchor="nw")

        self.content.bind("<Configure>", self._on_content_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

    def _on_canvas_configure(self, event):
        self._sync_content_size(width=event.width, height=event.height)

    def _sync_content_size(self, width: Optional[int] = None,
                           height: Optional[int] = None, refresh: bool = False):
        """Selaraskan ukuran jendela konten di dalam canvas: selebar canvas
        (agar layout ikut saat maximize) dan minimal setinggi canvas — atau
        lebih tinggi bila konten butuh ruang (muncul scrollbar).

        Wajib dipanggil ulang setiap tinggi konten berubah — collapse/expand
        section dan ganti mode tampilan (refresh=True agar reqheight dihitung
        ulang dulu) — supaya sisa ruang tidak tertinggal sebagai celah kosong
        yang mendorong section di bawahnya keluar dari layar.
        """
        try:
            if refresh:
                self.content.update_idletasks()  # hitung ulang reqheight dulu
            w = width or self.canvas.winfo_width()
            h = max(height or self.canvas.winfo_height(), self.content.winfo_reqheight())
            self.canvas.itemconfigure(self._content_win, width=w, height=h)
            self._sync_scrollbar()
        except Exception:
            pass

    def _on_content_configure(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._sync_scrollbar()

    def _sync_scrollbar(self):
        try:
            need = self.content.winfo_reqheight() > self.canvas.winfo_height() + 1
            mapped = bool(self.vsb.winfo_ismapped())
            if need and not mapped:
                self.vsb.grid()
            elif not need and mapped:
                self.vsb.grid_remove()
        except Exception:
            pass

    def _on_mousewheel(self, event):
        widget = event.widget
        if isinstance(widget, _WIDGET_SCROLL_SENDIRI):
            return
        try:
            if widget.winfo_toplevel() is not self.root:
                return  # jangan gulir jendela utama dari jendela pratinjau
        except Exception:
            return
        if self.content.winfo_reqheight() <= self.canvas.winfo_height():
            return
        self.canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")

    # ---------------------------------------------- section collapse/expand

    def _make_section(self, parent, key: str, title: str) -> ttk.Widget:
        """Buat pasangan section: header strip (chevron + judul — selalu tampil)
        + body Labelframe yang di-grid_remove SELURUHNYA saat di-collapse
        (bukan cuma isiannya) sehingga saat lipat yang tersisa hanya judul.

        Return body-nya; header bisa diakses lewat self._section_header[key].
        """
        header = ttk.Frame(parent)
        chev = ttk.Label(header, text="▾", style="Chevron.TLabel", cursor="hand2")
        ttl = ttk.Label(header, text=f" {title}", style="Section.TLabel", cursor="hand2")
        chev.pack(side="left", padx=(4, 0))
        ttl.pack(side="left", padx=(0, 6))
        for w in (header, chev, ttl):
            w.bind("<Button-1>", lambda _e, k=key: self._toggle_section(k))
        lf = ttk.Labelframe(parent)
        self._section_header[key] = header
        self._section_chev[key] = chev
        self._section_body[key] = lf
        self._collapsed[key] = False
        return lf

    def _toggle_section(self, key: str):
        """Lipat/bentangkan satu section: body di-grid_remove() SELURUHNYA
        (bukan cuma isinya), lalu baris fleksibel & tinggi konten dirapikan."""
        collapsed = not self._collapsed.get(key, False)
        self._collapsed[key] = collapsed
        self._section_chev[key].configure(text="▸" if collapsed else "▾")
        body = self._section_body[key]
        if collapsed:
            body.grid_remove()
        else:
            body.grid()
        self._relayout_section_weights()
        self._sync_content_size(refresh=True)

    def _relayout_section_weights(self):
        """Pindahkan baris grid yang melar ke panel fleksibel yang masih terbuka.

        Prioritas: Daftar Gambar dulu, kalau sedang dilipat baru Log — jadi
        selalu ada satu panel fleksibel yang meregang mengisi sisa ruang.
        Panel yang dilipat tidak menyisakan celah, dan tidak ada baris kosong
        ber-weight yang menyerap ruang lalu mendorong panel lain keluar layar.
        Bila keduanya dilipat, tidak ada baris yang melar dan konten menempel
        atas lewat grid_anchor "nw". Pengaturan tidak pernah melar karena
        tingginya memang tetap.
        """
        rows = {"queue": 1, "settings": 3, "log": 5}
        flex_key = None
        for key in ("queue", "log"):
            if not self._collapsed.get(key, False):
                flex_key = key
                break
        for key, row in rows.items():
            self.content.rowconfigure(row, weight=1 if key == flex_key else 0)

    def _build_queue(self):
        lf = self._make_section(self.content, "queue", "Daftar Gambar")
        self._section_header["queue"].grid(row=0, column=0, sticky="ew")
        lf.grid(row=1, column=0, sticky="nsew", padx=0, pady=(0, 6))
        lf.rowconfigure(0, weight=1)
        lf.columnconfigure(0, weight=1)

        wrap = ttk.Frame(lf)
        wrap.grid(row=0, column=0, sticky="nsew", padx=8, pady=(8, 4))
        wrap.rowconfigure(0, weight=1)
        wrap.columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(wrap, columns=("chk", "file", "status", "info"), show="headings",
                                 displaycolumns=("chk", "file", "status", "info"),
                                 selectmode="extended", height=8)
        self.tree.heading("chk", text="☐", anchor="center")
        self.tree.heading("file", text="Nama File")
        self.tree.heading("status", text="Status")
        self.tree.heading("info", text="Ukuran / Keterangan")
        self.tree.column("chk", width=40, minwidth=40, anchor="center", stretch=False)
        self.tree.column("file", width=430, anchor="w")
        self.tree.column("status", width=180, anchor="w", stretch=False)
        self.tree.column("info", width=260, anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew")
        for tag, color in (("ok", C["ok"]), ("err", C["err"]), ("mut", C["mut"]),
                           ("warn", C["warn"]), ("acc", C["acc"]), ("fg", C["fg"])):
            self.tree.tag_configure(tag, foreground=color)

        vsb = ttk.Scrollbar(wrap, orient="vertical", command=self.tree.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=vsb.set)

        self.ph_label = tk.Label(
            wrap,
            text="⬇  Tarik & lepas gambar / folder ke mana saja di jendela ini\n\n"
                 "atau klik dua kali di sini untuk memilih file",
            bg=C["panel2"], fg=C["mut"], justify="center",
            font=("Segoe UI", 11), cursor="hand2",
        )
        self.ph_label.place(relx=0.5, rely=0.45, anchor="center")
        self.ph_label.bind("<Double-1>", lambda _e: self._pick_files())

        btns = ttk.Frame(lf)
        btns.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 4))
        ttk.Button(btns, text="＋ Tambah File", command=self._pick_files).pack(side="left")
        ttk.Button(btns, text="📁 Tambah Folder", command=self._pick_folder).pack(side="left", padx=(6, 0))
        ttk.Button(btns, text="✖ Hapus Pilihan", command=self._remove_selected).pack(side="left", padx=(6, 0))
        self.lbl_count = ttk.Label(btns, text="", style="Mut.TLabel")
        self.lbl_count.pack(side="right")

        btns2 = ttk.Frame(lf)
        btns2.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 8))
        self.chk_all = ttk.Checkbutton(btns2, text="Pilih Semua", variable=self.var_check_all,
                                       command=self._toggle_check_all)
        self.chk_all.pack(side="left")
        self.btn_remove_checked = ttk.Button(btns2, text="🗑 Hapus Tercentang (0)", style="Danger.TButton",
                                             command=self._remove_checked, state="disabled")
        self.btn_remove_checked.pack(side="left", padx=(10, 0))
        ttk.Button(btns2, text="🧹 Bersihkan Daftar", command=self._clear_all).pack(side="left", padx=(6, 0))
        vf = ttk.Frame(btns2)
        vf.pack(side="right")
        ttk.Label(vf, text="Tampilan:").pack(side="left")
        self.cb_view = ttk.Combobox(vf, textvariable=self.var_view, state="readonly", width=19,
                                    values=[VIEW_LABELS[k] for k in VIEW_LABELS])
        self.cb_view.pack(side="left", padx=(6, 0))
        self.cb_view.bind("<<ComboboxSelected>>", lambda _e: self._apply_view_mode())

        self.tree.bind("<Double-1>", self._on_tree_double)
        self.tree.bind("<Button-3>", self._on_tree_menu)
        self.tree.bind("<Button-1>", self._on_tree_click, add="+")

    def _build_settings(self):
        lf = self._make_section(self.content, "settings", "Pengaturan")
        self._section_header["settings"].grid(row=2, column=0, sticky="ew")
        lf.grid(row=3, column=0, sticky="nsew", pady=(0, 6))
        lf.columnconfigure(0, weight=1)
        wrap = ttk.Frame(lf)
        wrap.grid(row=0, column=0, sticky="nsew", padx=8, pady=(8, 8))
        for i in range(3):
            wrap.columnconfigure(i, weight=1, uniform="setcol")

        # -- Kolom 1: engine & model
        f1 = ttk.Labelframe(wrap, text=" Engine & Kualitas ")
        f1.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        f1.columnconfigure(1, weight=1)
        ttk.Label(f1, text="Engine").grid(row=0, column=0, sticky="w", padx=10, pady=(10, 4))
        self.cb_engine = ttk.Combobox(f1, textvariable=self.var_engine, state="readonly",
                                      values=[e.label for e in ENGINES.values()])
        self.cb_engine.grid(row=0, column=1, sticky="ew", padx=(6, 10), pady=(10, 4))
        self.lbl_engine_note = ttk.Label(f1, text="", style="Mut.TLabel", wraplength=230)
        self.lbl_engine_note.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10)
        ttk.Label(f1, text="Model").grid(row=2, column=0, sticky="w", padx=10, pady=(8, 4))
        self.cb_model = ttk.Combobox(f1, textvariable=self.var_model, state="readonly")
        self.cb_model.grid(row=2, column=1, sticky="ew", padx=(6, 10), pady=(8, 4))
        ttk.Label(f1, text="Skala").grid(row=3, column=0, sticky="w", padx=10, pady=(8, 4))
        self.cb_scale = ttk.Combobox(f1, textvariable=self.var_scale, state="readonly")
        self.cb_scale.grid(row=3, column=1, sticky="ew", padx=(6, 10), pady=(8, 4))
        ttk.Label(f1, text="Denoise").grid(row=4, column=0, sticky="nw", padx=10, pady=(10, 10))
        dwrap = ttk.Frame(f1)
        dwrap.grid(row=4, column=1, sticky="ew", padx=(6, 10), pady=(10, 10))
        dwrap.columnconfigure(0, weight=1)
        self.sc_denoise = ttk.Scale(dwrap, from_=-1, to=3, variable=self.var_denoise,
                                    command=self._on_denoise)
        self.sc_denoise.grid(row=0, column=0, sticky="ew")
        self.lbl_denoise_val = ttk.Label(dwrap, text="", style="Mut.TLabel")
        self.lbl_denoise_val.grid(row=1, column=0, sticky="w")
        f1.bind("<Configure>",
                lambda e: self.lbl_engine_note.configure(wraplength=max(140, e.width - 130)))

        # -- Kolom 2: performa & format
        f2 = ttk.Labelframe(wrap, text=" Performa & Format ")
        f2.grid(row=0, column=1, sticky="nsew", padx=4)
        f2.columnconfigure(1, weight=1)
        ttk.Label(f2, text="Ukuran tile").grid(row=0, column=0, sticky="w", padx=10, pady=(10, 4))
        self.cb_tile = ttk.Combobox(f2, textvariable=self.var_tile, state="readonly",
                                    values=list(TILE_LABELS))
        self.cb_tile.grid(row=0, column=1, sticky="ew", padx=(6, 10), pady=(10, 4))
        ttk.Label(f2, text="VRAM kurang → tile kecil", style="Mut.TLabel").grid(
            row=1, column=0, columnspan=2, sticky="w", padx=10)
        ttk.Label(f2, text="GPU").grid(row=2, column=0, sticky="w", padx=10, pady=(8, 4))
        self.cb_gpu = ttk.Combobox(f2, textvariable=self.var_gpu, state="readonly")
        self.cb_gpu.grid(row=2, column=1, sticky="ew", padx=(6, 10), pady=(8, 4))
        ttk.Checkbutton(f2, text="Mode TTA (lebih bagus, ±2× lebih lambat)",
                        variable=self.var_tta).grid(row=3, column=0, columnspan=2,
                                                    sticky="w", padx=10, pady=(6, 2))
        ttk.Label(f2, text="Format output").grid(row=4, column=0, sticky="w", padx=10, pady=(8, 4))
        self.cb_format = ttk.Combobox(f2, textvariable=self.var_format, state="readonly",
                                      values=list(FORMAT_LABELS))
        self.cb_format.grid(row=4, column=1, sticky="ew", padx=(6, 10), pady=(8, 4))
        qwrap = ttk.Frame(f2)
        qwrap.grid(row=5, column=0, columnspan=2, sticky="ew", padx=10, pady=(8, 12))
        qwrap.columnconfigure(1, weight=1)
        ttk.Label(qwrap, text="Kualitas JPG/WebP").grid(row=0, column=0, sticky="w")
        self.sc_quality = ttk.Scale(qwrap, from_=40, to=100, variable=self.var_quality,
                                    command=self._on_quality)
        self.sc_quality.grid(row=0, column=1, sticky="ew", padx=8)
        self.lbl_quality = ttk.Label(qwrap, text="90", style="Mut.TLabel", width=3)
        self.lbl_quality.grid(row=0, column=2)

        # -- Kolom 3: output
        f3 = ttk.Labelframe(wrap, text=" Folder Output ")
        f3.grid(row=0, column=2, sticky="nsew", padx=(8, 0))
        f3.columnconfigure(1, weight=1)
        self.rb_source = ttk.Radiobutton(f3, text="Folder asal gambar",
                                         value="source", variable=self.var_out_mode,
                                         command=self._on_outmode)
        self.rb_source.grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 2))
        ttk.Label(f3, text="Akhiran nama:").grid(row=1, column=0, sticky="w", padx=(28, 0), pady=2)
        self.en_suffix = ttk.Entry(f3, textvariable=self.var_suffix, width=16)
        self.en_suffix.grid(row=1, column=1, sticky="w", padx=6, pady=2)
        self.rb_custom = ttk.Radiobutton(f3, text="Folder khusus:",
                                         value="custom", variable=self.var_out_mode,
                                         command=self._on_outmode)
        self.rb_custom.grid(row=2, column=0, columnspan=2, sticky="w", padx=10, pady=(8, 2))
        orow = ttk.Frame(f3)
        orow.grid(row=3, column=0, columnspan=2, sticky="ew", padx=(28, 10))
        orow.columnconfigure(0, weight=1)
        self.en_outdir = ttk.Entry(orow, textvariable=self.var_out_dir)
        self.en_outdir.grid(row=0, column=0, sticky="ew")
        ttk.Button(orow, text="…", width=3, command=self._browse_outdir).grid(row=0, column=1, padx=(6, 0))
        ttk.Checkbutton(f3, text="Ikuti subfolder saat menambah folder",
                        variable=self.var_subfolders).grid(row=4, column=0, columnspan=2,
                                                           sticky="w", padx=10, pady=(10, 2))
        ttk.Checkbutton(f3, text="Lewati file yang output-nya sudah ada",
                        variable=self.var_skip).grid(row=5, column=0, columnspan=2,
                                                     sticky="w", padx=10, pady=2)
        ttk.Checkbutton(f3, text="Buka folder output setelah selesai",
                        variable=self.var_auto_open).grid(row=6, column=0, columnspan=2,
                                                          sticky="w", padx=10, pady=(2, 12))

        self.cb_engine.bind("<<ComboboxSelected>>", self._engine_changed)
        self.cb_model.bind("<<ComboboxSelected>>", self._model_changed)
        self.cb_scale.bind("<<ComboboxSelected>>", self._scale_changed)
        self.cb_format.bind("<<ComboboxSelected>>", lambda _e: self._on_outmode())

    def _build_log(self):
        lf = self._make_section(self.content, "log", "Log")
        self._section_header["log"].grid(row=4, column=0, sticky="ew")
        lf.grid(row=5, column=0, sticky="nsew")
        lf.columnconfigure(0, weight=1)
        lf.rowconfigure(1, weight=1)
        hdr = ttk.Frame(lf)
        hdr.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=(8, 0))
        ttk.Button(hdr, text="🧹 Bersihkan Log", command=self._clear_log).pack(side="right")
        self.txt_log = tk.Text(lf, height=7, bg=C["panel2"], fg=C["fg"], relief="flat",
                               font=("Consolas", 9), state="disabled", wrap="word",
                               insertbackground=C["fg"], selectbackground=C["sel"])
        self.txt_log.grid(row=1, column=0, sticky="nsew", padx=(8, 0), pady=8)
        vsb = ttk.Scrollbar(lf, orient="vertical", command=self.txt_log.yview)
        vsb.grid(row=1, column=1, sticky="ns", padx=(0, 8), pady=8)
        self.txt_log.configure(yscrollcommand=vsb.set)
        for tag, color in (("ok", C["ok"]), ("err", C["err"]), ("warn", C["warn"]),
                           ("mut", C["mut"]), ("info", C["fg"])):
            self.txt_log.tag_configure(tag, foreground=color)

    def _build_footer(self):
        """Footer tetap di bawah: progress, status, dan tombol aksi — selalu terlihat."""
        footer = ttk.Frame(self.root, style="Bg.TFrame")
        footer.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 12))
        footer.columnconfigure(0, weight=1)

        self.bar = ttk.Progressbar(footer, style="Accent.Horizontal.TProgressbar", maximum=100)
        self.bar.grid(row=0, column=0, sticky="ew")
        srow = ttk.Frame(footer, style="Bg.TFrame")
        srow.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        srow.columnconfigure(0, weight=1)
        self.lbl_status = ttk.Label(srow, text="Siap. Tambahkan gambar lalu tekan Mulai Proses.",
                                    style="Bg.TLabel")
        self.lbl_status.grid(row=0, column=0, sticky="w")
        self.lbl_elapsed = ttk.Label(srow, text="", style="BgMut.TLabel")
        self.lbl_elapsed.grid(row=0, column=1, sticky="e")

        act = ttk.Frame(footer, style="Bg.TFrame")
        act.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        self.btn_start = ttk.Button(act, text="▶  Mulai Proses", style="Primary.TButton",
                                    command=self._on_start)
        self.btn_start.pack(side="left")
        self.btn_cancel = ttk.Button(act, text="■  Batalkan", style="Danger.TButton",
                                     command=self._on_cancel, state="disabled")
        self.btn_cancel.pack(side="left", padx=(8, 0))
        ttk.Button(act, text="📂 Buka Folder Output", command=self._open_output_folder).pack(side="left", padx=(8, 0))

    # ------------------------------------------------------------- settings

    def _restore_settings(self):
        c = self.cfg
        self.var_denoise.set(int(c.get("denoise", 0)))
        self.var_quality.set(int(c.get("quality", 90)))
        self.lbl_quality.configure(text=str(int(c.get("quality", 90))))
        self.var_out_mode.set(c.get("output_mode", "custom"))
        outdir = c.get("output_dir") or str(OUTPUT_DIR)
        self.var_out_dir.set(outdir)
        self.var_suffix.set(c.get("suffix", "_upscaled"))
        self.var_subfolders.set(bool(c.get("subfolders", True)))
        self.var_skip.set(bool(c.get("skip_existing", True)))
        self.var_auto_open.set(bool(c.get("auto_open", False)))
        self.var_view.set(VIEW_LABELS.get(c.get("view_mode", "detail"), "Detail"))
        fmt = c.get("format", "png")
        for label, key in FORMAT_LABELS.items():
            if key == fmt:
                self.var_format.set(label)
        tile = int(c.get("tile", 0))
        for label, key in TILE_LABELS.items():
            if key == tile:
                self.var_tile.set(label)
        for label, key in self.engine_by_label.items():
            if key == c.get("engine", "waifu2x"):
                self.var_engine.set(label)
        if not self.var_engine.get():
            self.var_engine.set(next(iter(self.engine_by_label)))
        self._on_outmode()

    def _on_quality(self, _val=None):
        self.lbl_quality.configure(text=str(int(float(self.var_quality.get()))))

    def _current_levels(self) -> tuple:
        """Level denoise yang tersedia untuk kombinasi engine/model/skala saat ini."""
        key = self.engine_by_label.get(self.var_engine.get(), "waifu2x")
        models = list_models(ENGINES[key])
        spec = models.get(self.model_by_label.get(self.var_model.get()))
        if spec is None or not spec.scales:
            return ()
        scale = self.scale_by_label.get(self.var_scale.get(), spec.scales[-1])
        return spec.denoise_levels(scale)

    def _on_denoise(self, _val=None):
        d = int(float(self.var_denoise.get()))
        levels = self._current_levels()
        if levels and d not in levels:
            d = min(levels, key=lambda x: abs(x - d))
        if float(self.var_denoise.get()) != d:
            self.var_denoise.set(d)
        self.lbl_denoise_val.configure(text=DEN_LABELS.get(d, str(d)))

    def _on_outmode(self):
        src = self.var_out_mode.get() == "source"
        self.en_suffix.state(["!disabled" if src else "disabled"])
        self.en_outdir.state(["disabled" if src else "!disabled"])
        fmt_key = FORMAT_LABELS.get(self.var_format.get(), "png")
        self.sc_quality.state(["disabled" if fmt_key == "png" else "!disabled"])

    def _browse_outdir(self):
        d = filedialog.askdirectory(initialdir=self.var_out_dir.get() or str(OUTPUT_DIR))
        if d:
            self.var_out_dir.set(d)

    def _engine_changed(self, *_):
        key = self.engine_by_label.get(self.var_engine.get())
        if not key:
            return
        eng = ENGINES[key]
        self.lbl_engine_note.configure(text=eng.note)
        models = list_models(eng)
        self.model_by_label = {spec.label: mid for mid, spec in models.items()}
        self.cb_model["values"] = list(self.model_by_label)
        saved = self.cfg.get(f"model_{key}", eng.default_model)
        if saved in models:
            self.var_model.set(models[saved].label)
        elif eng.default_model in models:
            self.var_model.set(models[eng.default_model].label)
        elif self.model_by_label:
            self.var_model.set(next(iter(self.model_by_label)))
        self._model_changed()
        self._refresh_gpus(key)

    def _model_changed(self, *_):
        key = self.engine_by_label.get(self.var_engine.get(), "waifu2x")
        models = list_models(ENGINES[key])
        mid = self.model_by_label.get(self.var_model.get())
        spec = models.get(mid)
        if spec is None:
            return
        labels = ["1x (denoise saja)" if s == 1 else f"{s}x" for s in spec.scales]
        self.scale_by_label = dict(zip(labels, spec.scales))
        self.cb_scale["values"] = labels
        cur = self.var_scale.get()
        if cur not in labels:
            want_scale = int(self.cfg.get("scale", 2) or 2)
            want_label = "1x (denoise saja)" if want_scale == 1 else f"{want_scale}x"
            self.var_scale.set(want_label if want_label in labels else labels[-1])
        self._scale_changed()

    def _scale_changed(self, *_):
        """Samakan opsi denoise dengan yang benar-benar tersedia di skala terpilih."""
        levels = self._current_levels()
        if not levels:
            self.sc_denoise.state(["disabled"])
            self.lbl_denoise_val.configure(text="tidak tersedia di skala ini")
            return
        self.sc_denoise.state(["!disabled"])
        self.sc_denoise.configure(from_=min(levels), to=max(levels))
        d = int(float(self.var_denoise.get()))
        if d not in levels:
            d = min(levels, key=lambda x: abs(x - d))
            self.var_denoise.set(d)
        self.lbl_denoise_val.configure(text=DEN_LABELS.get(d, str(d)))

    # ------------------------------------------------------------ GPU (non-blocking)

    def _fill_gpu_combo(self, pairs):
        self.gpu_map = {"Auto (pilihan Vulkan)": "auto", "CPU (-1) · sangat lambat": "-1"}
        values = ["Auto (pilihan Vulkan)"]
        for gid, name in pairs:
            label = f"GPU {gid} · {name}"
            self.gpu_map[label] = str(gid)
            values.append(label)
        values.append("CPU (-1) · sangat lambat")
        self.cb_gpu["values"] = values
        if self.var_gpu.get() not in values:
            self.var_gpu.set(values[0])

    def _refresh_gpus(self, engine_key: str):
        exe = find_exe(ENGINES[engine_key])
        if exe is None:
            self._fill_gpu_combo([])
            return
        key = str(exe)
        self._fill_gpu_combo(self._gpu_cache.get(key, []))
        if key not in self._gpu_cache and not self._gpu_running.get(key):
            self._gpu_running[key] = True
            threading.Thread(target=self._gpu_worker, args=(exe,), daemon=True).start()

    def _gpu_worker(self, exe: Path):
        try:
            pairs = enumerate_gpus(exe)
        except Exception:
            pairs = []
        self._post(("gpus", str(exe), pairs))

    def _refresh_engine_status(self):
        parts = []
        for eng in ENGINES.values():
            name = eng.label.split(" ·")[0]
            parts.append(("✔ " if find_exe(eng) else "✖ ") + name)
        self.lbl_engines.configure(text="   ".join(parts))

    def _gather(self) -> dict:
        key = self.engine_by_label.get(self.var_engine.get(), "waifu2x")
        eng = ENGINES[key]
        models = list_models(eng)
        mid = self.model_by_label.get(self.var_model.get(), eng.default_model)
        if mid not in models:
            mid = eng.default_model if eng.default_model in models else next(iter(models))
        spec = models.get(mid)
        scale = self.scale_by_label.get(self.var_scale.get(), 2)
        if spec and spec.scales and scale not in spec.scales:
            scale = spec.scales[-1]
        levels = spec.denoise_levels(scale) if spec else ()
        denoise = int(float(self.var_denoise.get())) if levels else 0
        if levels and denoise not in levels:
            denoise = min(levels, key=lambda x: abs(x - denoise))
        self.cfg.update({
            "engine": key,
            "model": mid,
            "scale": scale,
            "denoise": denoise,
            "tile": TILE_LABELS.get(self.var_tile.get(), 0),
            "gpu": self.gpu_map.get(self.var_gpu.get(), "auto"),
            "tta": bool(self.var_tta.get()),
            "format": FORMAT_LABELS.get(self.var_format.get(), "png"),
            "quality": int(float(self.var_quality.get())),
            "output_mode": self.var_out_mode.get(),
            "output_dir": self.var_out_dir.get().strip(),
            "suffix": self.var_suffix.get().strip() or "_upscaled",
            "subfolders": bool(self.var_subfolders.get()),
            "skip_existing": bool(self.var_skip.get()),
            "auto_open": bool(self.var_auto_open.get()),
            "view_mode": self._view_key(),
        })
        self.cfg[f"model_{key}"] = mid
        return self.cfg

    # ------------------------------------------------------------ antrean

    def _bind_dnd(self):
        if not (HAS_DND_LIB and hasattr(self.root, "drop_target_register")):
            self._log("tkinterdnd2 tidak terpasang — drag & drop nonaktif, gunakan tombol Tambah.", "warn")
            return
        for widget in (self.root, self.tree, self.ph_label):
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", self._on_drop)

    def _on_drop(self, event):
        try:
            paths = list(self.root.tk.splitlist(event.data))
        except Exception:
            paths = [event.data]
        self._add_paths(paths)
        return event.action

    def _pick_files(self):
        files = filedialog.askopenfilenames(
            title="Pilih gambar",
            filetypes=[("Gambar", "*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff *.gif"),
                       ("Semua file", "*.*")],
        )
        self._add_paths(files)

    def _pick_folder(self):
        d = filedialog.askdirectory(title="Pilih folder berisi gambar")
        if d:
            self._add_paths([d])

    def _add_paths(self, paths):
        added = 0
        for raw in paths:
            p = Path(raw)
            if p.is_dir():
                if self.var_subfolders.get():
                    files = [f for f in p.rglob("*") if f.is_file() and f.suffix.lower() in IMG_EXTS]
                else:
                    files = [f for f in p.iterdir() if f.is_file() and f.suffix.lower() in IMG_EXTS]
                files.sort()
            elif p.is_file() and p.suffix.lower() in IMG_EXTS:
                files = [p]
            else:
                files = []
            for f in files:
                s = str(f)
                if s in self.items:
                    continue
                self.items[s] = {"status": "Menunggu", "out": None, "checked": False}
                self.order.append(s)
                self.tree.insert("", "end", iid=s, text=f.name,
                                 values=("☐", f.name, "Menunggu", _fmt_size(f)), tags=("fg",))
                if self._view_key() != "detail":
                    self._ensure_thumb(s, self._view_key())
                added += 1
        if added:
            self.ph_label.place_forget()
            self._update_counts()
            self._update_check_state()
            self._log(f"+{added} gambar masuk antrean.", "ok")

    def _remove_selected(self):
        self._remove_iids(list(self.tree.selection()))

    def _remove_checked(self):
        targets = self._checked_items()
        if not targets:
            return
        self._remove_iids(targets)

    def _remove_iids(self, iids: List[str]):
        """Hapus sekumpulan item dari daftar; item yang sedang diproses dilindungi."""
        removed = skipped = 0
        for iid in iids:
            if self.running and self.items.get(iid, {}).get("status") == "Memproses":
                skipped += 1
                continue
            if not self.tree.exists(iid):
                continue
            self.tree.delete(iid)
            self.items.pop(iid, None)
            self._thumb_cache.pop(iid, None)
            self.order = [s for s in self.order if s != iid]
            removed += 1
        if not self.order:
            self.ph_label.place(relx=0.5, rely=0.45, anchor="center")
        self._update_counts()
        self._update_check_state()
        if removed:
            self._log(f"−{removed} gambar dihapus dari daftar.", "mut")
        if skipped:
            self._log(f"{skipped} gambar sedang diproses — tidak dihapus.", "warn")

    # ------------------------------------------------------ centang (checkbox)

    def _checked_items(self) -> List[str]:
        return [s for s in self.order if self.items.get(s, {}).get("checked")]

    def _set_checked(self, iid: str, checked: bool):
        info = self.items.get(iid)
        if info is None:
            return
        info["checked"] = bool(checked)
        if self.tree.exists(iid):
            self.tree.set(iid, "chk", "☑" if checked else "☐")
        self._update_check_state()

    def _set_all_checked(self, checked: bool):
        for s in self.order:
            info = self.items.get(s)
            if info is None:
                continue
            info["checked"] = checked
            if self.tree.exists(s):
                self.tree.set(s, "chk", "☑" if checked else "☐")
        self._update_check_state()

    def _set_checked_many(self, iids: List[str], checked: bool):
        for iid in iids:
            info = self.items.get(iid)
            if info is None:
                continue
            info["checked"] = bool(checked)
            if self.tree.exists(iid):
                self.tree.set(iid, "chk", "☑" if checked else "☐")
        self._update_check_state()

    def _toggle_check_all(self):
        """Dipanggil checkbutton 'Pilih Semua' di toolbar."""
        self._set_all_checked(bool(self.var_check_all.get()))

    def _toggle_all_from_heading(self):
        """Klik header kolom ☐ — centang semua, atau lepas semua bila sudah penuh."""
        if not self.order:
            return
        target = not all(self.items.get(s, {}).get("checked") for s in self.order)
        self._set_all_checked(target)

    def _column_name(self, col_id: str) -> Optional[str]:
        """Terjemahkan id kolom tampilan ('#0', '#1', ...) ke nama kolom.

        identify_column mengembalikan urutan TAMPILAN — di mode ikon sebagian
        kolom disembunyikan, jadi '#1' dipetakan lewat displaycolumns agar
        selalu mengenai kolom yang benar (mis. kolom centang).
        """
        if not col_id:
            return None
        if col_id == "#0":
            return "#0"
        try:
            idx = int(col_id[1:]) - 1
        except ValueError:
            return None
        disp = self.tree.cget("displaycolumns")
        cols = tuple(disp) if not isinstance(disp, str) else ("chk", "file", "status", "info")
        return cols[idx] if 0 <= idx < len(cols) else None

    def _on_tree_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        name = self._column_name(self.tree.identify_column(event.x))
        if region == "heading":
            if name == "chk":
                self._toggle_all_from_heading()
                return "break"
            return
        if region != "cell" or name != "chk":
            return
        iid = self.tree.identify_row(event.y)
        info = self.items.get(iid)
        if info is None:
            return
        self._set_checked(iid, not info.get("checked"))
        return "break"

    def _update_check_state(self):
        total = len(self.order)
        checked = len(self._checked_items())
        self.tree.heading("chk", text="☑" if total and checked == total else ("▣" if checked else "☐"))
        self.var_check_all.set(bool(total) and checked == total)
        if checked:
            self.btn_remove_checked.configure(text=f"🗑 Hapus Tercentang ({checked})", state="!disabled")
        else:
            self.btn_remove_checked.configure(text="🗑 Hapus Tercentang (0)", state="disabled")

    def _clear_all(self):
        if self.running:
            messagebox.showinfo(APP_NAME, "Proses sedang berjalan — batalkan dulu sebelum mengosongkan daftar.")
            return
        self.tree.delete(*self.tree.get_children())
        self.items.clear()
        self.order.clear()
        self.results.clear()
        self.produced.clear()
        self._thumb_cache.clear()
        self._thumb_gen += 1  # buang tugas thumbnail yang masih mengantre
        self.ph_label.place(relx=0.5, rely=0.45, anchor="center")
        self._update_counts()
        self._update_check_state()
        self._log("Daftar gambar dibersihkan.", "mut")

    def _update_counts(self):
        done = sum(1 for v in self.items.values() if v["status"].startswith("Selesai"))
        self.lbl_count.configure(text=f"{len(self.order)} gambar · {done} selesai")

    def _paint_item(self, path_str: str):
        info = self.items.get(path_str)
        if info is None or not self.tree.exists(path_str):
            return
        status = info["status"]
        base = status.split(" ·")[0]
        tag = "acc" if base.startswith("Memproses") else STATUS_TAGS.get(base, "fg")
        self.tree.set(path_str, "status", status)
        self.tree.item(path_str, tags=(tag,))

    # ------------------------------------------ tampilan daftar & thumbnail

    def _view_key(self) -> str:
        for key, label in VIEW_LABELS.items():
            if self.var_view.get() == label:
                return key
        return "detail"

    def _set_row_height(self, px: int):
        self._style.configure("Treeview", rowheight=px)

    def _apply_view_mode(self):
        """Terapkan mode tampilan daftar: Detail (teks) atau ikon + thumbnail.

        Mode ikon menampilkan thumbnail di kolom tree (#0) berdampingan dengan
        nama file; sebagian kolom disembunyikan agar mirip Windows Explorer.
        """
        key = self._view_key()
        self._thumb_gen += 1  # buang hasil thumbnail yang masih mengantre
        if key == "detail":
            self.tree.configure(show="headings",
                                displaycolumns=("chk", "file", "status", "info"))
            self._set_row_height(VIEW_ROW["detail"])
            self.tree.configure(height=VIEW_H["detail"])
            for iid in self.tree.get_children():
                if self.tree.exists(iid):
                    self.tree.item(iid, image="")
            self._update_check_state()
            self._sync_content_size(refresh=True)  # tinggi konten ikut berubah
            return
        self.tree.configure(show="tree",
                            displaycolumns=("chk", "status") if key in ("large", "xlarge")
                            else ("chk", "status", "info"))
        self._set_row_height(VIEW_ROW[key])
        self.tree.configure(height=VIEW_H[key])
        self.tree.column("#0", width=VIEW_COL0[key],
                         minwidth=VIEW_PX[key] + 100, stretch=True)
        self.tree.heading("#0", text="Gambar")
        self._ensure_all_thumbs(key)
        self._update_check_state()
        self._sync_content_size(refresh=True)  # tinggi konten ikut berubah

    def _placeholder_photo(self, size_key: str, failed: bool = False):
        """Placeholder kotak abu-abu; versi kemerahan bila gambar gagal dimuat."""
        ck = (size_key, failed)
        ph = self._placeholder_cache.get(ck)
        if ph is None:
            px = VIEW_PX[size_key]
            img = Image.new("RGBA", (px, px), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            d.rounded_rectangle(
                (0, 0, px - 1, px - 1), radius=max(3, px // 8), width=max(1, px // 32),
                fill=(74, 52, 56, 255) if failed else (44, 49, 63, 255),
                outline=(190, 100, 100, 255) if failed else (110, 122, 148, 255))
            ph = ImageTk.PhotoImage(img)
            self._placeholder_cache[ck] = ph
        return ph

    def _ensure_thumb(self, path_str: str, size_key: str):
        """Tampilkan thumbnail dari cache, atau jadwalkan pembuatannya di background."""
        cached = self._thumb_cache.get(path_str, {}).get(size_key)
        if cached is not None:
            if self.tree.exists(path_str):
                self.tree.item(path_str, image=cached)
            return
        if self.tree.exists(path_str):
            self.tree.item(path_str, image=self._placeholder_photo(size_key))
        if not self._thumb_worker_started:
            self._thumb_worker_started = True
            threading.Thread(target=self._thumb_worker, daemon=True).start()
        self._thumb_q.put((self._thumb_gen, path_str, size_key))

    def _ensure_all_thumbs(self, size_key: str):
        for path_str in self.order:
            self._ensure_thumb(path_str, size_key)

    def _thumb_worker(self):
        """Background thread: dekode & kecilkan gambar via PIL, lalu kirim hasilnya
        ke UI thread — PhotoImage wajib dibuat di thread utama (Tk tidak thread-safe)."""
        while True:
            gen, path_str, size_key = self._thumb_q.get()
            if gen != self._thumb_gen:
                continue  # mode berubah / daftar dibersihkan — buang tugas lama
            px = VIEW_PX[size_key]
            try:
                with Image.open(path_str) as im:
                    im.draft("RGB", (px, px))  # percepat decode JPEG beresolusi besar
                    im = ImageOps.exif_transpose(im)
                    im.thumbnail((px, px), Image.Resampling.LANCZOS)
                    pil = im.convert("RGBA")
            except Exception:
                pil = None  # file rusak/terkunci → tampilkan placeholder
            self.ui_q.put(("thumb", gen, path_str, size_key, pil))

    # ------------------------------------------------------------- proses

    def _on_start(self):
        if self.running:
            return
        cfg = dict(self._gather())
        save_config(cfg)
        pending = [Path(p) for p in self.order if self.items[p]["status"] != "Selesai"]
        if not pending:
            messagebox.showinfo(APP_NAME, "Belum ada gambar untuk diproses.\n\n"
                                          "Tarik & lepas gambar atau folder ke jendela ini.")
            return
        eng = ENGINES[cfg["engine"]]
        if find_exe(eng) is None:
            if messagebox.askyesno(
                APP_NAME,
                f"Engine '{eng.label}' belum diunduh ke folder tools/.\n"
                "Ukuran unduhan ±35-46 MB (butuh koneksi internet).\n\nUnduh sekarang?",
            ):
                self._auto_start = True
                self._download_engine(eng)
            return
        problem = validate_combo(cfg["engine"], cfg["model"], cfg["scale"], cfg["denoise"])
        if problem:
            self._log(f"Kombinasi tidak valid: {problem.splitlines()[0]}", "err")
            messagebox.showerror(APP_NAME, problem)
            return
        self._begin(pending, cfg)

    def _download_engine(self, eng):
        self.dl_cancel.clear()
        win = tk.Toplevel(self.root)
        win.title(f"Mengunduh {eng.label}")
        win.configure(bg=C["panel"])
        win.geometry("440x140")
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()
        ttk.Label(win, text=f"Mengunduh {eng.label}…", style="TLabel",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=16, pady=(16, 4))
        bar = ttk.Progressbar(win, style="Accent.Horizontal.TProgressbar", maximum=100)
        bar.pack(fill="x", padx=16)
        lbl = ttk.Label(win, text="Menghubungi server…", style="Mut.TLabel")
        lbl.pack(anchor="w", padx=16, pady=6)
        ttk.Button(win, text="Batalkan", command=self.dl_cancel.set).pack(pady=(4, 12))
        self.dl_win = win
        self._dl_bar = bar
        self._dl_lbl = lbl
        threading.Thread(target=self._download_worker, args=(eng,), daemon=True).start()

    def _download_worker(self, eng):
        try:
            download_zip(eng.zip_url, progress=self._on_dl_progress, cancel=self.dl_cancel)
        except DownloadCancelled:
            self._post(("dl_done", False, "cancelled"))
        except EngineError as e:
            self._post(("dl_done", False, str(e)))
        else:
            self._post(("dl_done", True, ""))

    def _on_dl_progress(self, done: int, total: int):
        self._post(("dl", done, total))

    def _begin(self, jobs: List[Path], cfg: dict):
        for p in jobs:
            s = str(p)
            self.items[s]["status"] = "Menunggu"
            self._paint_item(s)
        self.cancel_event.clear()
        self.running = True
        self.t_start = time.time()
        self.btn_start.state(["disabled"])
        self.btn_cancel.state(["!disabled"])
        self.bar.configure(value=0)
        self._set_status(f"Menyiapkan {len(jobs)} gambar…")
        self.lbl_elapsed.configure(text="0 detik")
        threading.Thread(target=self._worker, args=(jobs, cfg), daemon=True).start()

    def _on_cancel(self):
        if self.running:
            self.cancel_event.set()
            self._set_status("Membatalkan…")

    def _post(self, msg: tuple):
        self.ui_q.put(msg)

    def _worker(self, jobs: List[Path], cfg: dict):
        ok = fail = skip = 0
        total = len(jobs)
        t_all = time.time()
        for i, src in enumerate(jobs, 1):
            if self.cancel_event.is_set():
                for rest in jobs[i - 1:]:
                    s = str(rest)
                    info = self.items.get(s)
                    if info is not None and info["status"] in ("Menunggu", "Memproses"):
                        info["status"] = "Dibatalkan"
                        self._post(("item", s, "Dibatalkan", None))
                break
            s_src = str(src)
            info = self.items.get(s_src)
            if info is None:
                continue  # item dihapus dari daftar saat antrean berjalan — lewati
            info["status"] = "Memproses"
            self._post(("item", s_src, "Memproses…", None))
            self._post(("file", i, total, src.name))
            t0 = time.time()

            def file_prog(pct, idx=i, n=total):
                pct = max(0.0, min(100.0, pct))
                overall = ((idx - 1) + pct / 100.0) / n * 100.0
                self._post(("prog", overall))

            try:
                out = self._process_one(src, cfg, file_prog)
                if out is None:
                    skip += 1
                    self._post(("item", str(src), "Dilewati · sudah ada",
                                str(self._output_path(src, cfg))))
                else:
                    ok += 1
                    self._post(("item", str(src), f"Selesai · {time.time() - t0:.1f}s", str(out)))
            except TaskCancelled:
                self._post(("item", s_src, "Dibatalkan", None))
                for rest in jobs[i:]:
                    s = str(rest)
                    info2 = self.items.get(s)
                    if info2 is not None and info2["status"] in ("Menunggu", "Memproses"):
                        info2["status"] = "Dibatalkan"
                        self._post(("item", s, "Dibatalkan", None))
                break
            except EngineError as e:
                fail += 1
                self._post(("item", str(src), "Gagal", None))
                for line in str(e).splitlines():
                    self._post(("log", f"[GAGAL] {src.name} — {line}", "err"))
            except Exception as e:  # noqa: BLE001 — jangan biarkan worker mati
                fail += 1
                self._post(("item", str(src), "Gagal", None))
                detail = "".join(traceback.format_exception_only(type(e), e)).strip()
                self._post(("log", f"[GAGAL] {src.name} — {detail}", "err"))
                self._post(("log", traceback.format_exc().strip().splitlines()[-3], "mut"))
        self._post(("done", ok, fail, skip, time.time() - t_all))

    def _process_one(self, src: Path, cfg: dict, progress_cb) -> Optional[Path]:
        out = self._output_path(src, cfg)
        if cfg["output_mode"] == "custom":
            out = self._dedupe_output(out, src)
        if cfg["skip_existing"] and out.exists():
            progress_cb(100.0)
            return None
        out.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="waifuup_") as td:
            td_path = Path(td)
            work_in = prepare_input(src, td_path)
            tmp_png = td_path / (src.stem + ".out.png")
            cmds = build_commands(
                cfg["engine"], cfg["model"], cfg["scale"], cfg["denoise"],
                cfg["tta"], cfg["tile"], cfg["gpu"], work_in, tmp_png,
            )
            n = len(cmds)
            for idx, cmd in enumerate(cmds):
                off = 100.0 * idx / n
                span = 100.0 / n
                run_engine(
                    cmd,
                    lambda pct, off=off, span=span: progress_cb(off + pct * span / 100.0),
                    self.cancel_event,
                )
            if cfg["format"] == "png":
                move_file(tmp_png, out)
            else:
                encode_output(tmp_png, out, cfg["format"], cfg["quality"])
        self.produced[str(out)] = str(src)
        progress_cb(100.0)
        return out

    def _output_path(self, src: Path, cfg: dict) -> Path:
        ext = "." + cfg["format"]
        if cfg["output_mode"] == "source":
            return src.with_name(src.stem + cfg["suffix"] + ext)
        base = Path(cfg["output_dir"]) if cfg["output_dir"] else OUTPUT_DIR
        return base / (src.stem + ext)

    def _dedupe_output(self, out: Path, src: Path) -> Path:
        """Di folder khusus, dua sumber dengan nama sama tidak boleh saling menimpa."""
        guard = 0
        while str(out) in self.produced and self.produced[str(out)] != str(src) and guard < 1000:
            m = re.match(r"^(.*) \((\d+)\)$", out.stem)
            base = m.group(1) if m else out.stem
            num = (int(m.group(2)) if m else 1) + 1
            out = out.with_name(f"{base} ({num}){out.suffix}")
            guard += 1
        return out

    # ------------------------------------------------------------- event

    def _poll(self):
        try:
            while True:
                self._dispatch(self.ui_q.get_nowait())
        except queue.Empty:
            pass
        if self.running:
            el = time.time() - self.t_start
            self.lbl_elapsed.configure(text=f"{el:.0f} detik" if el < 120 else f"{el / 60:.1f} menit")
        self.root.after(80, self._poll)

    def _dispatch(self, msg: tuple):
        kind = msg[0]
        if kind == "prog":
            self.bar.configure(value=float(msg[1]))
        elif kind == "file":
            _, i, total, name = msg
            self._set_status(f"File {i}/{total} · {name}")
        elif kind == "item":
            _, path_str, status, out = msg
            if path_str in self.items:
                self.items[path_str]["status"] = status
                if out:
                    self.items[path_str]["out"] = out
                    self.results[path_str] = out
                self._paint_item(path_str)
                self._update_counts()
        elif kind == "log":
            self._log(msg[1], msg[2])
        elif kind == "thumb":
            _, gen, path_str, size_key, pil = msg
            if gen == self._thumb_gen and path_str in self.items:
                photo = (ImageTk.PhotoImage(pil) if pil is not None
                         else self._placeholder_photo(size_key, failed=True))
                self._thumb_cache.setdefault(path_str, {})[size_key] = photo
                if self._view_key() == size_key and self.tree.exists(path_str):
                    self.tree.item(path_str, image=photo)
                if pil is None:
                    self._log(f"⚠ Thumbnail gagal dibuat: {Path(path_str).name}", "mut")
        elif kind == "gpus":
            _, exe_key, pairs = msg
            self._gpu_cache[exe_key] = pairs
            self._gpu_running[exe_key] = False
            cur_key = self.engine_by_label.get(self.var_engine.get())
            if cur_key:
                exe = find_exe(ENGINES[cur_key])
                if exe is not None and str(exe) == exe_key:
                    self._fill_gpu_combo(pairs)
        elif kind == "done":
            _, ok, fail, skip, elapsed = msg
            self.running = False
            self.btn_start.state(["!disabled"])
            self.btn_cancel.state(["disabled"])
            if not self.cancel_event.is_set():
                self.bar.configure(value=100)  # item yang dihapus saat antrean berjalan tetap dihitung tuntas
            summary = f"Selesai dalam {elapsed:.0f}s — berhasil {ok}, gagal {fail}, dilewati {skip}"
            self._set_status(summary)
            self._log("✔ " + summary if fail == 0 else "⚠ " + summary, "ok" if fail == 0 else "warn")
            if self.var_auto_open.get() and ok:
                self._open_output_folder()
        elif kind == "dl":
            done, total = msg[1], msg[2]
            if self.dl_win is not None and total:
                self._dl_bar.configure(value=100.0 * done / total)
                self._dl_lbl.configure(text=f"{done / 1e6:.1f} / {total / 1e6:.1f} MB "
                                            f"({100.0 * done / total:.0f}%)")
            elif self.dl_win is not None:
                self._dl_lbl.configure(text=f"{done / 1e6:.1f} MB terunduh…")
        elif kind == "dl_done":
            ok, err = msg[1], msg[2]
            if self.dl_win is not None:
                self.dl_win.grab_release()
                self.dl_win.destroy()
                self.dl_win = None
            self.dl_cancel.clear()
            invalidate_exe_cache()
            self._refresh_engine_status()
            key = self.engine_by_label.get(self.var_engine.get(), "waifu2x")
            self._refresh_gpus(key)
            if ok:
                self._log("Engine berhasil diunduh & diekstrak.", "ok")
                self._engine_changed()
                if self._auto_start:
                    self._auto_start = False
                    self._on_start()
            elif err != "cancelled":
                self._log(f"Gagal mengunduh engine: {err}", "err")
                messagebox.showerror(APP_NAME, f"Gagal mengunduh engine:\n{err}")

    def _set_status(self, text: str):
        self.lbl_status.configure(text=text)

    def _log(self, text: str, tag: str = "info"):
        stamp = time.strftime("%H:%M:%S")
        self.txt_log.configure(state="normal")
        self.txt_log.insert("end", f"[{stamp}] {text}\n", tag)
        self.txt_log.see("end")
        self.txt_log.configure(state="disabled")

    def _clear_log(self):
        self.txt_log.configure(state="normal")
        self.txt_log.delete("1.0", "end")
        self.txt_log.configure(state="disabled")

    def _open_output_folder(self):
        base = self.var_out_dir.get().strip() if self.var_out_mode.get() == "custom" else ""
        target = Path(base) if base else OUTPUT_DIR
        try:
            target.mkdir(parents=True, exist_ok=True)
            os.startfile(str(target))  # noqa: S606 — Windows only, sesuai target aplikasi
        except Exception as e:  # noqa: BLE001
            messagebox.showerror(APP_NAME, f"Tidak bisa membuka folder:\n{e}")

    def _on_tree_double(self, event):
        if (self.tree.identify_region(event.x, event.y) == "cell"
                and self._column_name(self.tree.identify_column(event.x)) == "chk"):
            return  # klik ganda di kolom centang bukan aksi pratinjau
        if not self.order:
            self._pick_files()
            return
        sel = self.tree.selection()
        if not sel:
            return
        out = self.items.get(sel[0], {}).get("out")
        if out and Path(out).exists():
            PreviewWindow(self.root, sel[0], out)
        else:
            self._log("Pratinjau sebelum/sesudah muncul setelah baris berstatus 'Selesai'.", "mut")

    def _on_tree_menu(self, event):
        iid = self.tree.identify_row(event.y)
        if not iid:
            return
        if iid not in self.tree.selection():
            self.tree.selection_set(iid)
        menu = tk.Menu(self.root, tearoff=0, bg=C["panel2"], fg=C["fg"],
                       activebackground=C["sel"], activeforeground=C["fg"])
        sel = list(self.tree.selection())
        all_checked = bool(sel) and all(self.items.get(s, {}).get("checked") for s in sel)
        menu.add_command(label="☐  Lepas centang" if all_checked else "☑  Centang pilihan",
                         command=lambda: self._set_checked_many(sel, not all_checked))
        menu.add_separator()
        out = self.items.get(iid, {}).get("out")
        if out and Path(out).exists():
            menu.add_command(label="🖼  Lihat pratinjau sebelum/sesudah",
                             command=lambda: PreviewWindow(self.root, iid, out))
            menu.add_command(label="📂  Buka lokasi hasil",
                             command=lambda: self._reveal(Path(out)))
        menu.add_command(label="📁  Buka lokasi asal",
                         command=lambda: self._reveal(Path(iid)))
        menu.add_separator()
        menu.add_command(label="✖  Hapus dari daftar", command=self._remove_selected)
        menu.tk_popup(event.x_root, event.y_root)

    @staticmethod
    def _reveal(path: Path):
        try:
            if path.is_file():
                subprocess.Popen(["explorer", "/select,", str(path)])
            else:
                os.startfile(str(path))  # noqa: S606
        except Exception:
            pass

    def _on_close(self):
        if self.running and not messagebox.askyesno(APP_NAME, "Proses masih berjalan. Batalkan dan keluar?"):
            return
        cfg = self._gather()
        try:
            if self.root.state() == "zoomed":
                cfg["window_zoomed"] = True
            else:
                cfg["window_zoomed"] = False
                cfg["window_w"] = self.root.winfo_width()
                cfg["window_h"] = self.root.winfo_height()
        except Exception:
            pass
        save_config(cfg)
        self.cancel_event.set()
        self.root.destroy()


class PreviewWindow(tk.Toplevel):
    """Jendela perbandingan sebelum/sesudah dengan zoom & pan."""

    def __init__(self, master, before: str, after: str):
        super().__init__(master)
        self.configure(bg=C["panel"])
        self.title("Pratinjau — Sebelum / Sesudah")
        self.geometry("1060x720")
        self.minsize(620, 460)
        self._pil: Dict[str, Image.Image] = {}
        self._photos: List[ImageTk.PhotoImage] = []
        self.fit = True
        self._paths = {"before": Path(before), "after": Path(after)}

        top = ttk.Frame(self)
        top.pack(fill="x", padx=10, pady=(10, 6))
        self.var_after = tk.BooleanVar(value=True)
        ttk.Radiobutton(top, text="Sesudah", variable=self.var_after, value=True,
                        command=self._render).pack(side="left")
        ttk.Radiobutton(top, text="Sebelum", variable=self.var_after, value=False,
                        command=self._render).pack(side="left", padx=(6, 14))
        ttk.Button(top, text="Fit", width=6, command=self._fit).pack(side="left")
        ttk.Label(top, text="Zoom", style="Mut.TLabel").pack(side="left", padx=(14, 6))
        self.sc_zoom = ttk.Scale(top, from_=10, to=400, value=100, command=self._on_zoom)
        self.sc_zoom.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.lbl_zoom = ttk.Label(top, text="Fit", style="Mut.TLabel", width=8)
        self.lbl_zoom.pack(side="left")
        self.lbl_info = ttk.Label(top, text="", style="Mut.TLabel")
        self.lbl_info.pack(side="right")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        body.rowconfigure(0, weight=1)
        body.columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(body, bg=C["panel2"], highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        vsb = ttk.Scrollbar(body, orient="vertical", command=self.canvas.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        hsb = ttk.Scrollbar(body, orient="horizontal", command=self.canvas.xview)
        hsb.grid(row=1, column=0, sticky="ew")
        self.canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.canvas.bind("<Configure>", lambda _e: self.fit and self._render())
        self.canvas.bind("<MouseWheel>", self._on_wheel)
        self.bind("<Escape>", lambda _e: self.destroy())
        self.after(120, self._render)

    def _img(self, key: str) -> Image.Image:
        if key not in self._pil:
            img = Image.open(self._paths[key])
            img.load()
            self._pil[key] = img
        return self._pil[key]

    def _fit(self):
        self.fit = True
        self._render()

    def _on_zoom(self, val):
        self.fit = False
        pct = int(float(val))
        self.lbl_zoom.configure(text=f"{pct}%")
        self._render()

    def _on_wheel(self, event):
        if event.state & 0x0004:  # Ctrl + scroll = zoom
            step = 10 if event.delta > 0 else -10
            new = min(400, max(10, int(self.sc_zoom.get()) + step))
            self.sc_zoom.set(new)
        else:
            self.canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")

    def _render(self):
        key = "after" if self.var_after.get() else "before"
        try:
            img = self._img(key)
        except Exception as e:  # noqa: BLE001
            self.lbl_info.configure(text=f"Gagal memuat gambar: {e}")
            return
        cw = max(self.canvas.winfo_width(), 100)
        ch = max(self.canvas.winfo_height(), 100)
        iw, ih = img.size
        scale = min(cw / iw, ch / ih, 1.0) if self.fit else int(self.sc_zoom.get()) / 100.0
        tw, th = max(1, int(iw * scale)), max(1, int(ih * scale))
        try:
            disp = img.resize((tw, th), Image.Resampling.LANCZOS, reducing_gap=3.0)
        except Exception:  # pragma: no cover — gambar luar biasa besar
            disp = img.resize((tw, th), Image.Resampling.BILINEAR)
        photo = ImageTk.PhotoImage(disp)
        self._photos = [photo]
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=photo)
        self.canvas.configure(scrollregion=(0, 0, tw, th))
        b_img, a_img = self._img("before"), self._img("after")
        b_path, a_path = self._paths["before"], self._paths["after"]
        px = (a_img.size[0] * a_img.size[1]) / max(1, b_img.size[0] * b_img.size[1])
        self.lbl_info.configure(
            text=f"{b_path.name} {b_img.size[0]}×{b_img.size[1]} ({_fmt_size(b_path)})   →   "
                 f"{a_img.size[0]}×{a_img.size[1]} ({_fmt_size(a_path)})   ·   {px:.1f}× piksel"
        )
