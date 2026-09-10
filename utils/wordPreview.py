import os
import shutil
import tempfile
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox

import pymupdf
from PIL import Image, ImageTk


class WordPreview:
    """DOCX belgesini Tkinter içinde PDF tabanlı olarak önizler."""

    def __init__(self, parent, document):
        self.parent = parent
        self.document = document

        self.temp_dir = tempfile.mkdtemp(prefix="word_preview_")
        self.docx_path = os.path.join(self.temp_dir, "preview.docx")
        self.pdf_path = os.path.join(self.temp_dir, "preview.pdf")

        self.pdf = None
        self.page_index = 0
        self.zoom = 1.0
        self.photo = None

        self.window = tk.Toplevel(parent)
        self.window.title("Belge Önizleme")
        self.window.geometry("1000x800")
        self.window.minsize(700, 500)

        self.window.protocol("WM_DELETE_WINDOW", self.close)

        self._build_ui()
        self._create_preview()

    # ---------------------------------------------------------
    # UI
    # ---------------------------------------------------------

    def _build_ui(self):

        toolbar = ttk.Frame(self.window, padding=(8, 6))
        toolbar.pack(fill="x")

        ttk.Button(
            toolbar,
            text="◀",
            width=4,
            command=self.previous_page
        ).pack(side="left")

        self.page_label = ttk.Label(
            toolbar,
            text="Sayfa 0 / 0",
            width=14,
            anchor="center"
        )
        self.page_label.pack(side="left", padx=5)

        ttk.Button(
            toolbar,
            text="▶",
            width=4,
            command=self.next_page
        ).pack(side="left")

        ttk.Separator(
            toolbar,
            orient="vertical"
        ).pack(side="left", fill="y", padx=10)

        ttk.Button(
            toolbar,
            text="−",
            width=4,
            command=self.zoom_out
        ).pack(side="left")

        self.zoom_label = ttk.Label(
            toolbar,
            text="100%",
            width=7,
            anchor="center"
        )
        self.zoom_label.pack(side="left")

        ttk.Button(
            toolbar,
            text="+",
            width=4,
            command=self.zoom_in
        ).pack(side="left")

        ttk.Button(
            toolbar,
            text="Sayfaya Sığdır",
            command=self.fit_page
        ).pack(side="left", padx=10)

        ttk.Separator(
            toolbar,
            orient="vertical"
        ).pack(side="left", fill="y", padx=10)

        ttk.Button(
            toolbar,
            text="Kapat",
            command=self.close
        ).pack(side="right")

        # -----------------------------------------------------

        content = ttk.Frame(self.window)
        content.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(
            content,
            background="#808080",
            highlightthickness=0
        )

        self.v_scroll = ttk.Scrollbar(
            content,
            orient="vertical",
            command=self.canvas.yview
        )

        self.h_scroll = ttk.Scrollbar(
            content,
            orient="horizontal",
            command=self.canvas.xview
        )

        self.canvas.configure(
            yscrollcommand=self.v_scroll.set,
            xscrollcommand=self.h_scroll.set
        )

        self.canvas.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

        self.v_scroll.grid(
            row=0,
            column=1,
            sticky="ns"
        )

        self.h_scroll.grid(
            row=1,
            column=0,
            sticky="ew"
        )

        content.rowconfigure(0, weight=1)
        content.columnconfigure(0, weight=1)

        self.canvas.bind(
            "<MouseWheel>",
            self._mousewheel
        )

        self.canvas.bind(
            "<Button-4>",
            lambda e: self.canvas.yview_scroll(-1, "units")
        )

        self.canvas.bind(
            "<Button-5>",
            lambda e: self.canvas.yview_scroll(1, "units")
        )

    # ---------------------------------------------------------
    # DOCX -> PDF
    # ---------------------------------------------------------

    def _create_preview(self):

        try:
            self.document.doc.save(self.docx_path)

            libreoffice = self._find_libreoffice()

            if libreoffice is None:
                raise RuntimeError(
                    "LibreOffice bulunamadı.\n\n"
                    "Önizleme için LibreOffice'in kurulu olması gerekiyor."
                )

            result = subprocess.run(
                [
                    libreoffice,
                    "--headless",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    self.temp_dir,
                    self.docx_path
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
                if os.name == "nt" else 0
            )

            if not os.path.exists(self.pdf_path):
                raise RuntimeError(
                    "PDF oluşturulamadı.\n\n"
                    + result.stderr
                )

            self.pdf = pymupdf.open(self.pdf_path)

            if len(self.pdf) == 0:
                raise RuntimeError("Belge boş.")

            self.page_index = 0

            self.window.after(
                100,
                self.fit_page
            )

        except Exception as e:

            messagebox.showerror(
                "Önizleme Hatası",
                str(e),
                parent=self.window
            )

    # ---------------------------------------------------------
    # LibreOffice bul
    # ---------------------------------------------------------

    @staticmethod
    def _find_libreoffice():

        candidates = []

        if os.name == "nt":

            candidates.extend([
                r"C:\Program Files\LibreOffice\program\soffice.exe",
                r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"
            ])

        else:

            candidates.extend([
                "/usr/bin/libreoffice",
                "/usr/bin/soffice"
            ])

        for path in candidates:

            if os.path.exists(path):
                return path

        return shutil.which("libreoffice") or shutil.which("soffice")

    # ---------------------------------------------------------
    # Sayfa çiz
    # ---------------------------------------------------------

    def render_page(self):

        if self.pdf is None:
            return

        page = self.pdf[self.page_index]

        rect = page.rect

        # PDF point -> pixel
        matrix = pymupdf.Matrix(
            self.zoom,
            self.zoom
        )

        pix = page.get_pixmap(
            matrix=matrix,
            alpha=False
        )

        image = Image.frombytes(
            "RGB",
            [pix.width, pix.height],
            pix.samples
        )

        self.photo = ImageTk.PhotoImage(image)

        self.canvas.delete("all")

        # Gri çalışma alanı
        self.canvas.create_image(
            20,
            20,
            anchor="nw",
            image=self.photo
        )

        self.canvas.configure(
            scrollregion=(
                0,
                0,
                pix.width + 40,
                pix.height + 40
            )
        )

        self.page_label.configure(
            text=f"Sayfa {self.page_index + 1} / {len(self.pdf)}"
        )

        self.zoom_label.configure(
            text=f"{self.zoom * 100:.0f}%"
        )

        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)

    # ---------------------------------------------------------
    # Sayfa geçişleri
    # ---------------------------------------------------------

    def previous_page(self):

        if self.pdf is None:
            return

        if self.page_index > 0:

            self.page_index -= 1
            self.render_page()

    def next_page(self):

        if self.pdf is None:
            return

        if self.page_index < len(self.pdf) - 1:

            self.page_index += 1
            self.render_page()

    # ---------------------------------------------------------
    # Zoom
    # ---------------------------------------------------------

    def zoom_in(self):

        self.zoom *= 1.2

        if self.zoom > 4:
            self.zoom = 4

        self.render_page()

    def zoom_out(self):

        self.zoom /= 1.2

        if self.zoom < 0.25:
            self.zoom = 0.25

        self.render_page()

    # ---------------------------------------------------------
    # Sayfaya sığdır
    # ---------------------------------------------------------

    def fit_page(self):

        if self.pdf is None:
            return

        page = self.pdf[self.page_index]

        page_rect = page.rect

        available_width = self.canvas.winfo_width() - 40
        available_height = self.canvas.winfo_height() - 40

        if available_width <= 0 or available_height <= 0:
            return

        zoom_x = available_width / page_rect.width
        zoom_y = available_height / page_rect.height

        self.zoom = min(
            zoom_x,
            zoom_y
        )

        self.render_page()

    # ---------------------------------------------------------
    # Mouse wheel
    # ---------------------------------------------------------

    def _mousewheel(self, event):

        if event.delta:

            self.canvas.yview_scroll(
                int(-event.delta / 120),
                "units"
            )

    # ---------------------------------------------------------
    # Temizle
    # ---------------------------------------------------------

    def close(self):

        try:

            if self.pdf is not None:
                self.pdf.close()

        except Exception:
            pass

        try:

            if os.path.exists(self.temp_dir):
                shutil.rmtree(
                    self.temp_dir,
                    ignore_errors=True
                )

        except Exception:
            pass

        self.window.destroy()