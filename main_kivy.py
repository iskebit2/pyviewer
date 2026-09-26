# main_kivy.py
"""
Yük & Analiz Yöneticisi - Birleşik Kivy GUI

Save  → tüm config + dead/live yükleri tek JSON'a yazar.
Open  → aynı JSON'u okur, panelleri ve LoadManager'ı doldurur.

Şema:
{
  "project": {...},
  "points": {...},
  "polygons": {...},
  "dead_config": {...},
  "live_config": {...},
  "wind_config": {...},
  "snow_config": {...},
  "earthquake_config": {...}
}
"""

import os
import traceback



from kivy.app import App
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem

# ---- Mevcut modüller ----
from data.material_data import MATERIAL_WEIGHTS
from data.preset_loader import PresetLibrary
from loads.load_manager import LoadManager

# ---- Yeni proje şeması ----
from data.project_schema import (
    get_default_project,
    load_project,
    save_project,
    config_to_load_manager,
)

# ---- Analiz modülleri ----
from analysis.analysis_runner import (
    run_wind,
    run_snow,
    run_earthquake,
    show_spectrum_plot,
)

# ---- GUI ----
from gui.analysis_panels import AnalysisDataPanel, ResultPanel
from gui.file_dialog import FileDialog


# ======================================================================
# GLOBAL — ÖNCE OLUŞTUR, SONRA PANELLERE BAĞLA
# ======================================================================

load_manager = LoadManager(material_weights=MATERIAL_WEIGHTS)
preset_library = PresetLibrary()

from gui.panels import set_globals
set_globals(load_manager, preset_library)

from gui.panels import (
    YukTanimlamaPaneli,
    HazirYukPaneli,
    ElemanAtamaPaneli,
    RaporPaneli,
    export_dead_config,
    export_live_config,
)


# ======================================================================
# YARDIMCI
# ======================================================================

def show_message(title, message, level="info"):
    content = BoxLayout(orientation="vertical", padding=dp(15), spacing=dp(15))
    text = Label(text=str(message), halign="left", valign="top", size_hint_y=1)
    text.bind(size=text.setter("text_size"))
    content.add_widget(text)

    close = Button(text="Tamam", size_hint_y=None, height=dp(50))
    content.add_widget(close)

    popup = Popup(title=title, content=content, size_hint=(0.9, 0.6))
    close.bind(on_press=popup.dismiss)
    popup.open()
    print(f"[{level.upper()}] {title}: {message}")


# ======================================================================
# PROJE PANELİ — project + points/polygons
# ======================================================================

class ProjectDataPanel(AnalysisDataPanel):
    """
    'project' sözlüğünü düzenler.
    points/polygons ayrı JSON editörüyle düzenlenir (AnalysisDataPanel'in
    _edit_complex metodunu kullanır).
    """

    def __init__(self, project_data: dict, points: dict, polygons: dict, **kwargs):
        # AnalysisDataPanel'i 'project' verisiyle başlat
        super().__init__(
            title="Proje",
            panel_key="project",
            data=project_data,
            **kwargs,
        )
        self.points = dict(points)
        self.polygons = dict(polygons)

        # Form altına points/polygons düzenleme satırları ekle
        self._ekle_nokta_poligon_satirlari()

    def _ekle_nokta_poligon_satirlari(self):
        from kivy.uix.button import Button
        from kivy.uix.textinput import TextInput

        # Points satırı
        p_row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(6),
                          padding=[dp(4), dp(4)])
        p_row.add_widget(Label(text="points (JSON)", size_hint_x=0.35,
                               halign="left", valign="middle"))
        self._points_ti = TextInput(
            text=str(len(self.points)) + " nokta",
            readonly=True,
            size_hint_x=0.55,
        )
        p_row.add_widget(self._points_ti)
        p_btn = Button(text="✎", size_hint_x=0.10,
                       background_color=(0.4, 0.5, 0.8, 1),
                       background_normal="")
        p_btn.bind(on_press=lambda *_: self._edit_points())
        p_row.add_widget(p_btn)
        self.form.add_widget(p_row)

        # Polygons satırı
        pol_row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(6),
                            padding=[dp(4), dp(4)])
        pol_row.add_widget(Label(text="polygons (JSON)", size_hint_x=0.35,
                                 halign="left", valign="middle"))
        self._polygons_ti = TextInput(
            text=str(len(self.polygons)) + " poligon",
            readonly=True,
            size_hint_x=0.55,
        )
        pol_row.add_widget(self._polygons_ti)
        pol_btn = Button(text="✎", size_hint_x=0.10,
                         background_color=(0.4, 0.5, 0.8, 1),
                         background_normal="")
        pol_btn.bind(on_press=lambda *_: self._edit_polygons())
        pol_row.add_widget(pol_btn)
        self.form.add_widget(pol_row)

    def _edit_points(self):
        self._edit_json_dict("points", self.points, self._points_updated)

    def _edit_polygons(self):
        self._edit_json_dict("polygons", self.polygons, self._polygons_updated)

    def _points_updated(self, new_val):
        self.points = dict(new_val)
        self._points_ti.text = f"{len(self.points)} nokta"

    def _polygons_updated(self, new_val):
        self.polygons = dict(new_val)
        self._polygons_ti.text = f"{len(self.polygons)} poligon"

    def _edit_json_dict(self, key, current, on_save):
        import json
        from kivy.uix.popup import Popup

        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        editor = TextInput(
            text=json.dumps(current, ensure_ascii=False, indent=2),
            multiline=True,
            font_size=dp(12),
        )
        content.add_widget(editor)

        btns = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        ok = Button(text="Tamam", background_color=(0.2, 0.7, 0.35, 1),
                    background_normal="")
        iptal = Button(text="İptal", background_color=(0.85, 0.3, 0.3, 1),
                       background_normal="")
        btns.add_widget(ok); btns.add_widget(iptal)
        content.add_widget(btns)

        popup = Popup(title=f"Düzenle: {key}", content=content, size_hint=(0.9, 0.8))

        def _kaydet(*_):
            try:
                yeni = json.loads(editor.text)
            except json.JSONDecodeError as e:
                show_message("JSON Hatası", f"Geçersiz JSON:\n{e}", "error")
                return
            on_save(yeni)
            popup.dismiss()

        ok.bind(on_press=_kaydet)
        iptal.bind(on_press=popup.dismiss)
        popup.open()

    def get_project(self) -> dict:
        return self.get_data()

    def get_points(self) -> dict:
        return dict(self.points)

    def get_polygons(self) -> dict:
        return dict(self.polygons)

    def set_project(self, project: dict, points: dict, polygons: dict):
        self.set_data(project)
        self.points = dict(points)
        self.polygons = dict(polygons)
        if hasattr(self, "_points_ti"):
            self._points_ti.text = f"{len(self.points)} nokta"
        if hasattr(self, "_polygons_ti"):
            self._polygons_ti.text = f"{len(self.polygons)} poligon"


# ======================================================================
# ANA UYGULAMA
# ======================================================================

class YukAtamaApp(App):

    def build(self):
        self.title = "Yük & Analiz Yöneticisi"

        # Proje iskeleti
        self.project_data = get_default_project()
        self.current_config_path = None
        self._last_earthquake = None

        root = BoxLayout(orientation="vertical")
        root.add_widget(self._build_toolbar())

        tabs = TabbedPanel(do_default_tab=False)
        tabs.tab_width = dp(155)

        # 1) PROJE
        self.project_panel = ProjectDataPanel(
            project_data=self.project_data["project"],
            points=self.project_data["points"],
            polygons=self.project_data["polygons"],
        )
        proj_tab = TabbedPanelItem(text="1. Proje")
        proj_tab.add_widget(self.project_panel)
        tabs.add_widget(proj_tab)

        # 2) RÜZGÂR
        self.wind_panel = AnalysisDataPanel(
            title="Rüzgâr", panel_key="wind",
            data=self.project_data["wind_config"],
        )
        self.wind_panel.on_calculate = self._calculate_wind
        wind_tab = TabbedPanelItem(text="2. Rüzgâr")
        wind_tab.add_widget(self.wind_panel)
        tabs.add_widget(wind_tab)

        # 3) KAR
        self.snow_panel = AnalysisDataPanel(
            title="Kar", panel_key="snow",
            data=self.project_data["snow_config"],
        )
        self.snow_panel.on_calculate = self._calculate_snow
        snow_tab = TabbedPanelItem(text="3. Kar")
        snow_tab.add_widget(self.snow_panel)
        tabs.add_widget(snow_tab)

        # 4) DEPREM
        self.eq_panel = AnalysisDataPanel(
            title="Deprem", panel_key="earthquake",
            data=self.project_data["earthquake_config"],
            show_spectrum_button=True,
        )
        self.eq_panel.on_calculate = self._calculate_earthquake
        self.eq_panel.on_spectrum = self._show_spectrum
        eq_tab = TabbedPanelItem(text="4. Deprem")
        eq_tab.add_widget(self.eq_panel)
        tabs.add_widget(eq_tab)

        # 5) YÜK TANIMLA
        tanim_tab = TabbedPanelItem(text="5. Yük Tanımla")
        tanim_tab.add_widget(YukTanimlamaPaneli())
        tabs.add_widget(tanim_tab)

        # 6) HAZIR YÜKLER
        hazir_tab = TabbedPanelItem(text="6. Hazır Yükler")
        self.hazir_panel = HazirYukPaneli()
        hazir_tab.add_widget(self.hazir_panel)
        tabs.add_widget(hazir_tab)

        # 7) ELEMANA ATA
        atama_tab = TabbedPanelItem(text="7. Elemana Ata")
        self.atama_panel = ElemanAtamaPaneli()
        atama_tab.add_widget(self.atama_panel)
        tabs.add_widget(atama_tab)

        # 8) RAPOR
        rapor_tab = TabbedPanelItem(text="8. Rapor")
        self.rapor_panel = RaporPaneli()
        rapor_tab.add_widget(self.rapor_panel)
        tabs.add_widget(rapor_tab)

        tabs.bind(current_tab=self._sekme_degisti)
        root.add_widget(tabs)

        # Sonuç paneli
        self.result_panel = ResultPanel()
        root.add_widget(self.result_panel)

        # Rüzgâr için points varsa hazır
        if self.project_data.get("points"):
            self.wind_panel.set_extra_enabled(True)

        return root

    # ------------------------------------------------------------------
    # ARAÇ ÇUBUĞU
    # ------------------------------------------------------------------

    def _build_toolbar(self):
        bar = BoxLayout(size_hint_y=None, height=dp(52),
                        spacing=dp(6), padding=[dp(6), dp(4)])

        self.open_btn = Button(text="📂  Aç",
                               background_color=(0.15, 0.25, 0.45, 1),
                               background_normal="")
        self.open_btn.bind(on_press=self._on_open_clicked)
        bar.add_widget(self.open_btn)

        self.save_btn = Button(text="💾  Kaydet",
                               background_color=(0.20, 0.55, 0.30, 1),
                               background_normal="")
        self.save_btn.bind(on_press=self._on_save_clicked)
        bar.add_widget(self.save_btn)

        self.new_btn = Button(text="➕  Yeni",
                              background_color=(0.35, 0.35, 0.55, 1),
                              background_normal="")
        self.new_btn.bind(on_press=self._on_new_clicked)
        bar.add_widget(self.new_btn)

        self.config_label = Label(text="(kayıtlı değil)",
                                  size_hint_x=0.6, halign="right", valign="middle",
                                  color=(0.4, 0.4, 0.5, 1), font_size=dp(12))
        self.config_label.bind(size=self.config_label.setter("text_size"))
        bar.add_widget(self.config_label)

        return bar

    # ------------------------------------------------------------------
    # DOSYA İŞLEMLERİ
    # ------------------------------------------------------------------

    def _on_open_clicked(self, *args):
        dialog = FileDialog(callback=self._open_callback, mode="open")
        popup = Popup(title="📂  Proje Aç", content=dialog, size_hint=(0.95, 0.9))
        dialog.popup = popup
        popup.open()

    def _on_save_clicked(self, *args):
        default_name = "proje.json"
        if self.current_config_path:
            default_name = os.path.basename(self.current_config_path)

        dialog = FileDialog(callback=self._save_callback, mode="save",
                            default_name=default_name)
        popup = Popup(title="💾  Proje Kaydet", content=dialog, size_hint=(0.95, 0.9))
        dialog.popup = popup
        popup.open()

    def _on_new_clicked(self, *args):
        self.project_data = get_default_project()
        self.current_config_path = None
        self.config_label.text = "(kayıtlı değil)"

        # Panelleri sıfırla
        self.project_panel.set_project(
            self.project_data["project"],
            self.project_data["points"],
            self.project_data["polygons"],
        )
        self.wind_panel.set_data(self.project_data["wind_config"])
        self.snow_panel.set_data(self.project_data["snow_config"])
        self.eq_panel.set_data(self.project_data["earthquake_config"])

        self.wind_panel.set_extra_enabled(False)
        self.eq_panel.set_spectrum_enabled(False)
        self._last_earthquake = None
        self.result_panel.set_text("")

        # LoadManager'ı sıfırla
        load_manager.definitions.clear()
        load_manager.assignments.clear()

        show_message("Yeni", "Boş proje oluşturuldu.", "info")

    # ------------------------------------------------------------------
    def _open_callback(self, config, path):
        try:
            proj = load_project(path)
            self.project_data = proj

            # Panelleri doldur
            self.project_panel.set_project(
                proj["project"], proj["points"], proj["polygons"],
            )
            self.wind_panel.set_data(proj["wind_config"])
            self.snow_panel.set_data(proj["snow_config"])
            self.eq_panel.set_data(proj["earthquake_config"])

            # Dead/Live → LoadManager
            load_manager.definitions.clear()
            load_manager.assignments.clear()
            config_to_load_manager(proj["dead_config"], load_manager)
            config_to_load_manager(proj["live_config"], load_manager)

            # Yardımcı durumlar
            self.wind_panel.set_extra_enabled(bool(proj.get("points")))
            self.eq_panel.set_spectrum_enabled(False)
            self._last_earthquake = None

            # Elemana Ata ve Rapor panellerini yenile
            if hasattr(self, "atama_panel"):
                self.atama_panel.liste_yenile()
            if hasattr(self, "rapor_panel"):
                self.rapor_panel.rapor_yenile()

            self.current_config_path = path
            self.config_label.text = f"📄  {os.path.basename(path)}"

            show_message(
                "Başarılı",
                f"✅ Proje yüklendi:\n{os.path.basename(path)}",
                "success",
            )
        except Exception as e:
            traceback.print_exc()
            show_message("Açma Hatası", str(e), "error")

    # ------------------------------------------------------------------
    def _save_callback(self, path):
        try:
            # 1) Project + points/polygons
            self.project_data["project"] = self.project_panel.get_project()
            self.project_data["points"] = self.project_panel.get_points()
            self.project_data["polygons"] = self.project_panel.get_polygons()

            # 2) Wind / Snow / Earthquake
            self.project_data["wind_config"] = self.wind_panel.get_data()
            self.project_data["snow_config"] = self.snow_panel.get_data()
            self.project_data["earthquake_config"] = self.eq_panel.get_data()

            # 3) Dead / Live
            self.project_data["dead_config"] = export_dead_config()
            self.project_data["live_config"] = export_live_config()

            # 4) Yaz
            save_project(self.project_data, path)

            self.current_config_path = path
            self.config_label.text = f"📄  {os.path.basename(path)}"

            n_g = len(self.project_data["dead_config"]["definitions"])
            n_q = len(self.project_data["live_config"]["definitions"])
            show_message(
                "Başarılı",
                f"✅ Kaydedildi:\n{path}\n\n"
                f"Ölü yük tanımı: {n_g}\n"
                f"Hareketli yük tanımı: {n_q}",
                "success",
            )
        except Exception as e:
            traceback.print_exc()
            show_message("Kayıt Hatası", str(e), "error")

    # ------------------------------------------------------------------
    def _sekme_degisti(self, instance, value):
        if hasattr(self, "atama_panel"):
            self.atama_panel.liste_yenile()
        if hasattr(self, "rapor_panel"):
            self.rapor_panel.rapor_yenile()

    # ------------------------------------------------------------------
    # ANALİZ
    # ------------------------------------------------------------------

    def _calculate_wind(self, data: dict):
        # Config'i panellerden tazele
        cfg = {
            "points":   self.project_panel.get_points(),
            "polygons": self.project_panel.get_polygons(),
        }
        result = run_wind(cfg, data)
        self._goster_sonuc(result)

    def _calculate_snow(self, data: dict):
        result = run_snow({}, data)
        self._goster_sonuc(result)

    def _calculate_earthquake(self, data: dict):
        result = run_earthquake({}, data)
        self._goster_sonuc(result)
        if result.success:
            self._last_earthquake = result.extra.get("analysis")
            self.eq_panel.set_spectrum_enabled(True)
        else:
            self._last_earthquake = None

    def _goster_sonuc(self, result):
        self.result_panel.set_text(result.as_text())
        if not result.success:
            show_message(f"{result.title} Hatası", result.error, "error")

    # ------------------------------------------------------------------
    def _show_spectrum(self):
        eq = self._last_earthquake
        if eq is None:
            show_message("Uyarı", "Önce deprem analizini hesaplayın!", "warning")
            return
        info = show_spectrum_plot(eq)
        if info["ok"]:
            msg = "📈 Spektrum grafiği oluşturuldu."
            if info["save_path"]:
                msg += f"\n\nPNG:\n{info['save_path']}"
            show_message("Grafik Hazır", msg, "success")
        else:
            show_message("Grafik Hatası", info["error"], "error")


# ======================================================================
# BAŞLAT
# ======================================================================

if __name__ == "__main__":
    print("=" * 50)
    print("Yük & Analiz Yöneticisi başlatılıyor...")
    print("=" * 50)
    try:
        YukAtamaApp().run()
    except Exception as e:
        traceback.print_exc()
        print(f"\n❌ ÇÖKTÜ: {e}")