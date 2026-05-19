import customtkinter as ctk
from tkinter import filedialog, messagebox
import tkinter as tk
import threading
import re
import urllib.request
from io import BytesIO
from PIL import Image
from downloader import YouTubeDownloader

BG          = "#000000"
SURFACE     = "#0d0d0d"
BORDER      = "#1f1f1f"
THUMB_BG    = "#111111"
TEXT_PRI    = "#f5f5f5"
TEXT_SEC    = "#4a4a4a"
TEXT_MUTED  = "#2a2a2a"
ACCENT      = "#e63030"
ACCENT_HVR  = "#c42626"
PROGRESS_BG = "#1a1a1a"

THUMB_W = 150
THUMB_H = 86

_YT_RE = re.compile(
    r"(?:v=|youtu\.be/|/embed/|/shorts/)([a-zA-Z0-9_-]{11})"
)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("DowTube")
        self.geometry("590x200")
        self.resizable(False, False)
        self.configure(fg_color=BG)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self._center_window()

        self.downloader    = YouTubeDownloader(self._update_progress)
        self.quality_var   = ctk.StringVar(value="720")
        self.save_path     = None
        self._last_video_id = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        wrap = ctk.CTkFrame(self, fg_color=SURFACE,
                            corner_radius=14, border_width=1, border_color=BORDER)
        wrap.grid(row=0, column=0, padx=18, pady=18, sticky="nsew")
        wrap.grid_columnconfigure(0, weight=1)
        wrap.grid_columnconfigure(1, minsize=THUMB_W + 16)

        hdr = ctk.CTkFrame(wrap, fg_color="transparent")
        hdr.grid(row=0, column=0, columnspan=2, padx=20, pady=(16, 10), sticky="ew")
        hdr.grid_columnconfigure(1, weight=1)

        self.hamburger_btn = ctk.CTkButton(
            hdr, text="≡", command=self._open_hamburger_menu,
            width=30, height=26, corner_radius=6,
            fg_color=BORDER, hover_color="#2a2a2a",
            text_color=TEXT_SEC, font=ctk.CTkFont(family="Helvetica", size=15),
        )
        self.hamburger_btn.grid(row=0, column=0, sticky="w", padx=(0, 10))

        ctk.CTkLabel(
            hdr, text="DOWTUBE",
            font=ctk.CTkFont(family="Helvetica", size=13, weight="bold"),
            text_color=TEXT_PRI,
        ).grid(row=0, column=1, sticky="w")

        self.quality_btn = ctk.CTkOptionMenu(
            hdr, values=["360p", "720p", "1080p", "Só Áudio"],
            command=self._quality_callback,
            width=112, height=26, corner_radius=6,
            fg_color=BORDER, button_color=BORDER, button_hover_color="#2a2a2a",
            text_color=TEXT_SEC, dropdown_fg_color="#111111",
            dropdown_hover_color="#1f1f1f", dropdown_text_color=TEXT_PRI,
            dynamic_resizing=False, font=ctk.CTkFont(family="Helvetica", size=11),
        )
        self.quality_btn.set("⊞  Qualidade")
        self.quality_btn.grid(row=0, column=2, sticky="e")

        self._popup = tk.Menu(
            self, tearoff=0, bg="#111111", fg=TEXT_PRI,
            activebackground="#1f1f1f", activeforeground=TEXT_PRI,
            bd=0, relief="flat", font=("Helvetica", 11),
        )
        self._popup.add_command(label="  ⊙  Pasta de destino", command=self._choose_folder)
        self._popup.add_separator()
        self._popup.add_command(label="  ◎  Sobre", command=self._show_about)

        mid = ctk.CTkFrame(wrap, fg_color="transparent")
        mid.grid(row=1, column=0, padx=(20, 10), pady=4, sticky="ew")
        mid.grid_columnconfigure(0, weight=1)

        self.url_entry = ctk.CTkEntry(
            mid, placeholder_text="Cole a URL do YouTube…",
            height=40, corner_radius=8, border_width=1, border_color=BORDER,
            fg_color="#111111", text_color=TEXT_PRI,
            placeholder_text_color=TEXT_SEC,
            font=ctk.CTkFont(family="Helvetica", size=12),
        )
        self.url_entry.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        self.url_entry.bind("<KeyRelease>", self._on_url_change)
        self.url_entry.bind("<<Paste>>",    lambda e: self.after(50, self._on_url_change))

        self.dl_btn = ctk.CTkButton(
            mid, text="↓   Baixar", command=self._start_download,
            height=34, corner_radius=8,
            fg_color=ACCENT, hover_color=ACCENT_HVR,
            text_color="#ffffff",
            font=ctk.CTkFont(family="Helvetica", size=12, weight="bold"),
        )
        self.dl_btn.grid(row=1, column=0, sticky="ew")

        thumb_frame = ctk.CTkFrame(
            wrap, width=THUMB_W, height=THUMB_H,
            corner_radius=8, fg_color=THUMB_BG,
            border_width=1, border_color=BORDER,
        )
        thumb_frame.grid(row=1, column=1, rowspan=2,
                         padx=(0, 20), pady=(4, 4), sticky="ns")
        thumb_frame.grid_propagate(False)
        thumb_frame.grid_columnconfigure(0, weight=1)
        thumb_frame.grid_rowconfigure(0, weight=1)

        self.thumbnail_label = ctk.CTkLabel(
            thumb_frame, text="▶",
            font=ctk.CTkFont(family="Helvetica", size=22),
            text_color=TEXT_MUTED, fg_color="transparent",
        )
        self.thumbnail_label.grid(row=0, column=0, sticky="nsew")

        self.progress_bar = ctk.CTkProgressBar(
            wrap, height=2, corner_radius=1,
            fg_color=PROGRESS_BG, progress_color=ACCENT,
        )
        self.progress_bar.set(0)
        self.progress_bar.grid(row=2, column=0, padx=(20, 10), pady=(10, 3), sticky="ew")

        self.status_lbl = ctk.CTkLabel(
            wrap, text="pronto",
            font=ctk.CTkFont(family="Helvetica", size=10),
            text_color=TEXT_SEC,
        )
        self.status_lbl.grid(row=3, column=0, columnspan=2, padx=20, pady=(0, 12))

    def _on_url_change(self, event=None):
        """Chamado a cada tecla/paste; dispara fetch da capa se URL mudou."""
        url = self.url_entry.get().strip()
        m   = _YT_RE.search(url)
        if not m:
            self._reset_thumbnail()
            return

        video_id = m.group(1)
        if video_id == self._last_video_id:
            return

        self._last_video_id = video_id
        self._reset_thumbnail(loading=True)

        threading.Thread(
            target=self._fetch_thumbnail,
            args=(video_id,),
            daemon=True,
        ).start()

    def _fetch_thumbnail(self, video_id: str):
        """
        Tenta buscar a capa em ordem decrescente de qualidade.
        Roda em thread separada para não travar a UI.
        """
        urls = [
            f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg",    # 320×180
            f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",    # 480×360
            f"https://img.youtube.com/vi/{video_id}/default.jpg",      # 120×90
        ]
        for thumb_url in urls:
            try:
                with urllib.request.urlopen(thumb_url, timeout=6) as resp:
                    data = resp.read()
                img   = Image.open(BytesIO(data)).convert("RGB")
                ctk_img = ctk.CTkImage(
                    light_image=img,
                    dark_image=img,
                    size=(THUMB_W, THUMB_H),
                )
                self.after(0, lambda i=ctk_img: self._set_thumbnail(i))
                return
            except Exception:
                continue

        self.after(0, self._reset_thumbnail)

    def _set_thumbnail(self, img: ctk.CTkImage):
        """Exibe a capa no label (thread principal)."""
        self.thumbnail_label.configure(image=img, text="")

    def _reset_thumbnail(self, loading: bool = False):
        """Volta ao placeholder (ou mostra '…' enquanto carrega)."""
        self.thumbnail_label.configure(
            image=None,
            text="…" if loading else "▶",
        )

    def _center_window(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        x = (self.winfo_screenwidth()  // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _open_hamburger_menu(self):
        btn = self.hamburger_btn
        x   = btn.winfo_rootx()
        y   = btn.winfo_rooty() + btn.winfo_height() + 4
        try:
            self._popup.tk_popup(x, y, 0)
        finally:
            self._popup.grab_release()

    def _choose_folder(self):
        path = filedialog.askdirectory(title="Pasta de destino")
        if path:
            self.save_path = path
            short = path.rstrip("/\\").replace("\\", "/").split("/")[-1] or path
            self.status_lbl.configure(text=f"destino: …/{short}")

    def _show_about(self):
        AboutWindow(self)

    def _quality_callback(self, choice):
        mapping = {"360p": "360", "720p": "720", "1080p": "1080", "Só Áudio": "Audio Only"}
        self.quality_var.set(mapping.get(choice, "720"))
        self.quality_btn.set("⊞  Qualidade")

    def _update_progress(self, percent: float):
        self.progress_bar.set(percent / 100)
        self.status_lbl.configure(text=f"baixando… {int(percent)}%")

    def _start_download(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Aviso", "Insira uma URL válida.")
            return

        if not self.save_path:
            self.save_path = filedialog.askdirectory(title="Pasta de destino")
        if not self.save_path:
            return

        self.dl_btn.configure(state="disabled")
        self.status_lbl.configure(text="conectando…")
        self.progress_bar.set(0)

        threading.Thread(
            target=self._run_download,
            args=(self.save_path,),
            daemon=True,
        ).start()

    def _run_download(self, save_path: str):
        url = self.url_entry.get().strip()
        success, message = self.downloader.download_video(
            url, self.quality_var.get(), save_path
        )
        if success:
            self.after(0, lambda: self.status_lbl.configure(text="concluído ✓"))
            self.after(0, lambda: messagebox.showinfo("Sucesso", "Vídeo baixado com sucesso!"))
        else:
            self.after(0, lambda: self.status_lbl.configure(text="erro no download"))
            self.after(0, lambda: messagebox.showerror("Erro", message))
        self.after(0, lambda: self.dl_btn.configure(state="normal"))

class AboutWindow(ctk.CTkToplevel):
    """Janela modal estilizada com informações do projeto."""

    _W, _H = 380, 320

    def __init__(self, parent):
        super().__init__(parent)

        self.title("")
        self.geometry(f"{self._W}x{self._H}")
        self.resizable(False, False)
        self.configure(fg_color=BG)
        self.grab_set()
        self.focus_force()
        self._center(parent)

        self.overrideredirect(False)

        wrap = ctk.CTkFrame(self, fg_color=SURFACE,
                            corner_radius=16, border_width=1, border_color=BORDER)
        wrap.pack(fill="both", expand=True, padx=14, pady=14)
        wrap.grid_columnconfigure(0, weight=1)

        logo_img = self._load_svg_logo("dowtube-py/icon/logo.svg", size=64)

        if logo_img:
            ctk.CTkLabel(
                wrap, image=logo_img, text="",
                fg_color="transparent",
            ).grid(row=0, column=0, pady=(24, 0))
        else:
            logo_ring = ctk.CTkFrame(wrap, width=56, height=56,
                                     corner_radius=28,
                                     fg_color=ACCENT, border_width=0)
            logo_ring.grid(row=0, column=0, pady=(24, 0))
            logo_ring.grid_propagate(False)
            logo_ring.grid_columnconfigure(0, weight=1)
            logo_ring.grid_rowconfigure(0, weight=1)
            ctk.CTkLabel(
                logo_ring, text="▶",
                font=ctk.CTkFont(family="Helvetica", size=20, weight="bold"),
                text_color="#ffffff",
            ).grid(row=0, column=0)

        ctk.CTkLabel(
            wrap, text="DowTube-Py",
            font=ctk.CTkFont(family="Helvetica", size=18, weight="bold"),
            text_color=TEXT_PRI,
        ).grid(row=1, column=0, pady=(12, 0))

        ctk.CTkLabel(
            wrap, text="v 1.0.0",
            font=ctk.CTkFont(family="Helvetica", size=10),
            text_color=TEXT_SEC,
        ).grid(row=2, column=0, pady=(2, 0))

        ctk.CTkLabel(
            wrap,
            text="App de código aberto em Python\npara baixar vídeos do YouTube.",
            font=ctk.CTkFont(family="Helvetica", size=11),
            text_color=TEXT_SEC,
            justify="center",
        ).grid(row=3, column=0, pady=(10, 0))

        div = ctk.CTkFrame(wrap, height=1, fg_color=BORDER)
        div.grid(row=4, column=0, sticky="ew", padx=24, pady=(16, 12))

        info_frame = ctk.CTkFrame(wrap, fg_color="transparent")
        info_frame.grid(row=5, column=0, padx=24, sticky="ew")
        info_frame.grid_columnconfigure(1, weight=1)

        rows = [
            ("Criador",       "John-BrenoF",                              "https://github.com/John-BrenoF"),
            ("Repositório",   "John-BrenoF/dowtubepy",                    "https://github.com/John-BrenoF/dowtubepy.git"),
            ("Licença",       "GNU General Public License v3",             None),
        ]
        for i, (label, value, link) in enumerate(rows):
            ctk.CTkLabel(
                info_frame, text=label,
                font=ctk.CTkFont(family="Helvetica", size=10),
                text_color=TEXT_SEC, anchor="w",
            ).grid(row=i, column=0, sticky="w", pady=3, padx=(0, 12))

            if link:
                lbl = ctk.CTkLabel(
                    info_frame, text=value,
                    font=ctk.CTkFont(family="Helvetica", size=10, underline=True),
                    text_color=ACCENT, anchor="w", cursor="hand2",
                )
                lbl.grid(row=i, column=1, sticky="w", pady=3)
                lbl.bind("<Button-1>", lambda e, u=link: self._open_url(u))
            else:
                ctk.CTkLabel(
                    info_frame, text=value,
                    font=ctk.CTkFont(family="Helvetica", size=10),
                    text_color=TEXT_PRI, anchor="w",
                ).grid(row=i, column=1, sticky="w", pady=3)

        ctk.CTkButton(
            wrap, text="Fechar",
            command=self.destroy,
            height=32, corner_radius=8,
            fg_color=BORDER, hover_color="#2a2a2a",
            text_color=TEXT_SEC,
            font=ctk.CTkFont(family="Helvetica", size=11),
        ).grid(row=6, column=0, pady=(18, 20), padx=24, sticky="ew")

    @staticmethod
    def _load_svg_logo(path: str, size: int = 64) -> "ctk.CTkImage | None":
        """
        Tenta converter logo.svg → CTkImage usando cairosvg (preferido)
        ou svglib como fallback. Retorna None se nenhum estiver disponível
        ou o arquivo não existir.
        """
        import os
        if not os.path.isfile(path):
            return None
        try:
            import cairosvg
            from io import BytesIO
            png_bytes = cairosvg.svg2png(url=path,
                                         output_width=size,
                                         output_height=size)
            img = Image.open(BytesIO(png_bytes)).convert("RGBA")
            return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
        except ImportError:
            pass
        try:
            from svglib.svglib import svg2rlg
            from reportlab.graphics import renderPM
            from io import BytesIO
            drawing = svg2rlg(path)
            png_bytes = renderPM.drawToString(drawing, fmt="PNG")
            img = Image.open(BytesIO(png_bytes)).convert("RGBA").resize(
                (size, size), Image.LANCZOS
            )
            return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
        except ImportError:
            pass
        return None

    def _center(self, parent):
        self.update_idletasks()
        px = parent.winfo_rootx() + (parent.winfo_width()  - self._W) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - self._H) // 2
        self.geometry(f"{self._W}x{self._H}+{px}+{py}")

    @staticmethod
    def _open_url(url: str):
        import webbrowser
        webbrowser.open(url)