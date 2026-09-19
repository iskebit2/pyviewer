#wind_load.py

import json
import io
import sys
import tkinter as tk
from tkinter import filedialog, messagebox

from PIL import Image, ImageTk

from windcalc.windengine import BuildingWindEngine
from windcalc.wind_report import all_wind_report, show_zones
from utils.datapanel import dataPanel
from utils.logger import EnhancedLogger


# --------------------------------------------------
# JSON
# --------------------------------------------------

def save_to_json(points, polygons, file_path, scale=0.001):
    scaled_points = {
        name: [float(coord * scale) for coord in coords]
        for name, coords in points.items()
    }

    data = {
        "points": scaled_points,
        "polygons": polygons
    }

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False,
            default=str
        )


def load_from_json(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return (
        data.get("points", {}),
        data.get("polygons", {})
    )


# --------------------------------------------------
# APP
# --------------------------------------------------

class WindApp:

    def __init__(self, root):

        self.root = root
        self.root.title("Wind Analysis")
        self.root.geometry("1200x700")
        self.root.minsize(900, 550)

        self.points = {}
        self.polygons = {}
        self.rapor = None

        self.wind_config = {
            "v_b0": 28.0,
            "terrain": "Kategori III",
            "w_dir": [1, 0, 0]
        }

        self.tk_resim = None

        self.build_ui()

    # --------------------------------------------------
    # UI
    # --------------------------------------------------

    def build_ui(self):

        # Ana düzen
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Sol panel
        self.left_panel = tk.Frame(
            self.root,
            width=220,
            bd=1,
            relief="solid"
        )

        self.left_panel.grid(
            row=0,
            column=0,
            sticky="ns",
            padx=5,
            pady=5
        )

        self.left_panel.grid_propagate(False)

        dataPanel(
            self.left_panel,
            self.wind_config,
            title="Rüzgar Parametreleri"
        ).pack(
            fill="both",
            expand=True,
            padx=3,
            pady=3
        )

        # Sağ ana alan
        self.main_panel = tk.Frame(self.root)

        self.main_panel.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=5,
            pady=5
        )

        self.main_panel.columnconfigure(0, weight=1)
        self.main_panel.rowconfigure(0, weight=1)
        self.main_panel.rowconfigure(1, weight=1)

        # Görsel
        self.image_frame = tk.LabelFrame(
            self.main_panel,
            text="Rüzgar Bölgeleri"
        )

        self.image_frame.grid(
            row=0,
            column=0,
            sticky="nsew",
            pady=(0, 5)
        )

        self.image_frame.columnconfigure(0, weight=1)
        self.image_frame.rowconfigure(0, weight=1)

        self.image_label = tk.Label(
            self.image_frame,
            text="Henüz analiz yapılmadı",
            bg="white"
        )

        self.image_label.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

        # Log
        self.log_frame = tk.LabelFrame(
            self.main_panel,
            text="Log"
        )

        self.log_frame.grid(
            row=1,
            column=0,
            sticky="nsew"
        )

        self.log_frame.columnconfigure(0, weight=1)
        self.log_frame.rowconfigure(0, weight=1)

        self.text = tk.Text(
            self.log_frame,
            width=80,
            height=10,
            wrap="none"
        )

        self.text.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

        self.logger = EnhancedLogger(self.text)
        self.old_stdout = sys.stdout
        sys.stdout = self.logger

        # Alt buton çubuğu
        self.button_frame = tk.Frame(self.root)

        self.button_frame.grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=5,
            pady=5
        )

        self.create_button("Open", self.open_, 0)
        self.create_button("Run", self.run_, 1)
        self.create_button("All Reports", self.all_reports, 2)

        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def create_button(self, text, command, column):

        tk.Button(
            self.button_frame,
            text=text,
            command=command,
            width=14
        ).grid(
            row=0,
            column=column,
            padx=3
        )

    # --------------------------------------------------
    # FILE
    # --------------------------------------------------

    def load_(self, file_path):

        try:
            self.points, self.polygons = load_from_json(file_path)

            print(f"\nDosya: {file_path}")
            print(f"Point sayısı: {len(self.points)}")
            print(f"Polygon sayısı: {len(self.polygons)}")

            print("Geometri başarıyla yüklendi.")

        except Exception as e:
            self.show_error("Dosya okuma hatası", e)

    def open_(self):

        file_path = filedialog.askopenfilename(
            title="Dosya Aç",
            initialdir="examples/",
            filetypes=[
                ("JSON Dosyaları", "*.json"),
                ("Tüm Dosyalar", "*.*")
            ]
        )

        if file_path:
            self.load_(file_path)

    # --------------------------------------------------
    # ANALYSIS
    # --------------------------------------------------

    def get_wind_config(self):

        return {
            "v_b0": self.wind_config.get("v_b0", 28.0),
            "terrain": self.wind_config.get(
                "terrain",
                "Kategori III"
            ),
            "w_dir": self.wind_config.get(
                "w_dir",
                [1, 0, 0]
            )
        }

    def run_(self):

        if not self.points or not self.polygons:
            messagebox.showwarning(
                "Eksik veri",
                "Önce geçerli bir JSON dosyası açın."
            )
            return

        try:

            config = self.get_wind_config()

            print("\n--- ANALİZ BAŞLADI ---")

            building = BuildingWindEngine(
                points=self.points,
                polygons=self.polygons,
                v_b0=config["v_b0"],
                terrain=config["terrain"],
                w_dir=config["w_dir"],
                scale_factor=1.0
            )

            building.analysis_all_roof_wind(
                config["w_dir"]
            )

            summary = building.get_summary()

            print(json.dumps(
                summary,
                indent=2,
                ensure_ascii=False,
                default=str
            ))

            stream = show_zones(building)

            self.display_image(stream)

            print("--- ANALİZ TAMAMLANDI ---")

        except Exception as e:
            self.show_error("Analiz hatası", e)

    # --------------------------------------------------
    # IMAGE
    # --------------------------------------------------

    def display_image(self, stream):

        pil_image = Image.open(stream).convert("RGB")

        # Mevcut alanın boyutlarını al
        self.root.update_idletasks()

        width = self.image_frame.winfo_width()
        height = self.image_frame.winfo_height()

        width = max(width - 10, 100)
        height = max(height - 10, 100)

        # Oranı koruyarak sığdır
        pil_image.thumbnail(
            (width, height),
            Image.Resampling.LANCZOS
        )

        self.tk_resim = ImageTk.PhotoImage(pil_image)

        self.image_label.configure(
            image=self.tk_resim,
            text=""
        )

    # --------------------------------------------------
    # REPORT
    # --------------------------------------------------

    def all_reports(self):

        if not self.points or not self.polygons:
            messagebox.showwarning(
                "Eksik veri",
                "Önce geçerli bir JSON dosyası açın."
            )
            return

        try:

            config = self.get_wind_config()

            self.rapor = all_wind_report(
                points=self.points,
                polygons=self.polygons,
                v_b0=config["v_b0"],
                terrain=config["terrain"]
            )

            print("Rapor hazır.")

            self.rapor.preview(self.root)

        except Exception as e:
            self.show_error("Rapor hatası", e)

    # --------------------------------------------------
    # ERROR
    # --------------------------------------------------

    def show_error(self, title, error):

        print(f"\n[HATA] {title}")
        print(f"{type(error).__name__}: {error}")

        messagebox.showerror(
            title,
            str(error)
        )

    # --------------------------------------------------
    # CLOSE
    # --------------------------------------------------

    def close(self):

        sys.stdout = self.old_stdout
        self.root.destroy()


# --------------------------------------------------
# MAIN
# --------------------------------------------------

if __name__ == "__main__":
    root = tk.Tk()
    app = WindApp(root)
    root.mainloop()