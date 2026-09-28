import ast
import json
from pathlib import Path
import traceback

from kivy.app import App
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput

from loads.snow_load import SnowLoad
from windcalc.wind_results import WindResults
from loads.spectrum import EarthquakeLoad
from loads.spectrum_kivy import SpectrumPlot

# ------------------------------------------------------------
# ANALİZLER
# ------------------------------------------------------------

ANALYSES = [
    (
        "wind",
        "Rüzgâr",
        lambda config, data: WindResults(
            points=config.get("points", {}),
            polygons=config.get("polygons", {}),
            wind_config = data
        )
    ),
    (
        "snow",
        "Kar",
        lambda config, data: SnowLoad(data)
    ),
    (
        "earthquake",
        "Deprem",
        lambda config, data: EarthquakeLoad(**data)
    ),
]


# ------------------------------------------------------------
# DATA PANEL
# ------------------------------------------------------------

class DataPanel(BoxLayout):

    def __init__(self, **kwargs):
        super().__init__(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(8),
            **kwargs
        )

        self.data = {}
        self.inputs = {}

        self.form = BoxLayout(
            orientation="vertical",
            spacing=dp(8),
            size_hint_y=None
        )

        self.form.bind(
            minimum_height=self.form.setter("height")
        )

        self.scroll = ScrollView()

        self.scroll.add_widget(self.form)

        self.add_widget(self.scroll)

    def set_data(self, data):
        self.data = dict(data)
        self.inputs.clear()
        self.form.clear_widgets()

        for key, value in self.data.items():

            row = BoxLayout(
                size_hint_y=None,
                height=dp(55),
                spacing=dp(10)
            )

            label = Label(
                text=str(key),
                size_hint_x=0.4,
                halign="left",
                valign="middle"
            )

            label.bind(
                size=lambda obj, size:
                setattr(obj, "text_size", size)
            )

            if isinstance(value, bool):

                widget = CheckBox(
                    active=value,
                    size_hint_x=0.6
                )

            else:

                widget = TextInput(
                    text=str(value),
                    multiline=False,
                    font_size=dp(18),
                    size_hint_x=0.6
                )

            self.inputs[key] = widget

            row.add_widget(label)
            row.add_widget(widget)

            self.form.add_widget(row)

    def get(self):

        result = {}

        for key, widget in self.inputs.items():

            old_value = self.data[key]

            if isinstance(old_value, bool):
                value = widget.active

            else:
                text = widget.text.strip()

                if isinstance(old_value, (dict, list)):
                    value = ast.literal_eval(text)

                elif isinstance(old_value, int):
                    value = int(text)

                elif isinstance(old_value, float):
                    value = float(text)

                else:
                    value = text

            result[key] = value

        return result


# ------------------------------------------------------------
# DOSYA PENCERESİ
# ------------------------------------------------------------

class FileDialog(BoxLayout):

    def __init__(self, callback, path=None, **kwargs):

        super().__init__(
            orientation="vertical",
            spacing=dp(10),
            padding=dp(10),
            **kwargs
        )

        self.callback = callback
        self.popup = None

        self.filechooser = FileChooserListView(
            path=path or str(Path.cwd()),
            filters=["*.json"]
        )

        self.add_widget(self.filechooser)

        buttons = BoxLayout(
            size_hint_y=None,
            height=dp(55),
            spacing=dp(10)
        )

        open_button = Button(text="Aç")
        close_button = Button(text="Kapat")

        buttons.add_widget(open_button)
        buttons.add_widget(close_button)

        self.add_widget(buttons)

        open_button.bind(on_press=self.open)
        close_button.bind(on_press=self.close)

    def open(self, *args):

        if not self.filechooser.selection:
            return

        filename = self.filechooser.selection[0]

        try:

            with open(
                filename,
                "r",
                encoding="utf-8"
            ) as f:
                config = json.load(f)

            self.callback(config)
            self.close()

        except Exception as e:

            self.callback({
                "_error": f"Dosya açılamadı: {e}"
            })

            self.close()

    def close(self, *args):

        if self.popup:
            self.popup.dismiss()


# ------------------------------------------------------------
# ANA PENCERE
# ------------------------------------------------------------

class MainWindow(BoxLayout):

    def __init__(self, config=None, **kwargs):

        super().__init__(
            orientation="vertical",
            spacing=dp(8),
            padding=dp(8),
            **kwargs
        )

        self.config = None
        self.current_analysis = None
        self.panels = {}
        self.analysis_factories = {}
        self.results = {}

        # ----------------------------------------------------
        # ÜST TOOLBAR
        # ----------------------------------------------------

        toolbar = BoxLayout(
            size_hint_y=None,
            height=dp(60),
            spacing=dp(6)
        )

        self.menu_button = Button(text="☰")
        self.calculate_button = Button(text="HESAPLA")
        self.report_button = Button(text="RAPOR")
        self.graph_button = Button(text="GRAFİK")
        self.exit_button = Button(text="ÇIKIŞ")

        toolbar.add_widget(self.menu_button)
        toolbar.add_widget(self.calculate_button)
        toolbar.add_widget(self.report_button)
        toolbar.add_widget(self.graph_button)
        toolbar.add_widget(self.exit_button)

        self.add_widget(toolbar)

        self.menu_button.bind(
            on_press=self.open_menu
        )

        self.calculate_button.bind(
            on_press=self.calculate
        )

        self.report_button.bind(
            on_press=self.report
        )

        self.graph_button.bind(
            on_press=self.graph
        )

        self.exit_button.bind(
            on_press=self.exit_app
        )

        # ----------------------------------------------------
        # AKTİF ANALİZ ALANI
        # ----------------------------------------------------

        self.analysis_area = BoxLayout(
            orientation="vertical"
        )

        self.add_widget(self.analysis_area)

        # ----------------------------------------------------
        # LOG / SONUÇ
        # ----------------------------------------------------

        self.log = TextInput(
            readonly=True,
            multiline=True,
            font_size=dp(15),
            size_hint_y=0.28
        )

        self.add_widget(self.log)

        # ----------------------------------------------------
        # ANALİZ PANELLERİ
        # ----------------------------------------------------

        for key, title, factory in ANALYSES:

            panel = DataPanel()

            self.panels[key] = panel
            self.analysis_factories[key] = factory

        # İlk analiz
        self.switch_analysis("wind")

        # Dışarıdan config geldiyse doğrudan yükle
        if config is not None:

            self.load_config(config)

    # --------------------------------------------------------
    # LOG
    # --------------------------------------------------------

    def write_log(self, message):

        self.log.text += str(message) + "\n"

        self.log.cursor = (0, 0)

    # --------------------------------------------------------
    # MENÜ
    # --------------------------------------------------------

    def open_menu(self, button):

        menu = BoxLayout(
            orientation="vertical",
            spacing=dp(5),
            padding=dp(5)
        )

        popup = Popup(
            title="MENÜ",
            content=menu,
            size_hint=(0.75, 0.75)
        )

        # Dosya
        open_button = Button(
            text="Dosya Aç",
            size_hint_y=None,
            height=dp(55)
        )

        menu.add_widget(open_button)

        open_button.bind(
            on_press=lambda x: (
                popup.dismiss(),
                self.open_file()
            )
        )

        # Analiz başlığı
        menu.add_widget(
            Label(
                text="ANALİZ",
                size_hint_y=None,
                height=dp(45)
            )
        )

        # Analizler
        for key, title, factory in ANALYSES:

            button = Button(
                text=title,
                size_hint_y=None,
                height=dp(55)
            )

            menu.add_widget(button)

            button.bind(
                on_press=lambda x, k=key: (
                    popup.dismiss(),
                    self.switch_analysis(k)
                )
            )

        popup.open()

    # --------------------------------------------------------
    # ANALİZ DEĞİŞTİR
    # --------------------------------------------------------

    def switch_analysis(self, key):

        if key not in self.panels:
            return

        self.current_analysis = key

        self.analysis_area.clear_widgets()

        panel = self.panels[key]

        self.analysis_area.add_widget(panel)

        title = dict(
            (key, title)
            for key, title, factory in ANALYSES
        )[key]

        self.write_log(
            f">> Aktif analiz: {title}"
        )

    # --------------------------------------------------------
    # DOSYA AÇ
    # --------------------------------------------------------

    def open_file(self):

        dialog = FileDialog(
            callback=self.load_config,
            path=str(Path.cwd())
        )

        popup = Popup(
            title="JSON dosyası aç",
            content=dialog,
            size_hint=(0.95, 0.9)
        )

        dialog.popup = popup

        popup.open()

    # --------------------------------------------------------
    # CONFIG YÜKLE
    # --------------------------------------------------------

    def load_config(self, config):

        if "_error" in config:

            self.write_log(
                f"HATA: {config['_error']}"
            )

            return

        self.config = config

        for key, panel in self.panels.items():

            data = config.get(
                f"{key}_config",
                {}
            )

            panel.set_data(data)

        self.log.text = ""

        self.write_log(
            "Dosya yüklendi."
        )

        self.write_log(
            "Aktif analiz: Rüzgâr"
        )

    # --------------------------------------------------------
    # HESAPLA
    # --------------------------------------------------------

    def calculate(self, *args):

        key = self.current_analysis

        if key is None:
            self.write_log(
                "UYARI: Aktif analiz yok."
            )
            return

        if self.config is None:
            self.write_log(
                "UYARI: Önce bir dosya açın."
            )
            return

        panel = self.panels[key]

        try:

            data = panel.get()

            factory = self.analysis_factories[key]

            analysis = factory(
                self.config,
                data
            )

            self.results[key] = analysis

            report = analysis.report()

            self.write_log(
                f"{key} analizi tamamlandı."
            )

            self.write_log(
                str(report)
            )

        except Exception as e:
            traceback.print_exc()
            self.write_log(
                f"HESAP HATASI: {e}"
            )

    # --------------------------------------------------------
    # RAPOR
    # --------------------------------------------------------

    def report(self, *args):
        
        self.write_log(
            "Raporlama henüz uygulanmadı."
        )

    # --------------------------------------------------------
    # GRAFİK
    # --------------------------------------------------------

    def graph(self, *args):

        if self.earthquake_analysis is None:
            self.write_log("Önce deprem analizini hesaplayın!")
            return

        try:
            plot = SpectrumPlot()
            plot.set_spectrum(self.earthquake_analysis)
            plot.show()

            # Kayıt yolu bilgisi
            save_path = None
            if hasattr(plot, "get_default_save_path"):
                save_path = plot.get_default_save_path()
            elif hasattr(plot, "_get_default_save_path"):
                save_path = plot._get_default_save_path()

            msg = "📈 Spektrum grafiği oluşturuldu."
            if save_path:
                msg += f"\n\nPNG dosyası:\n{save_path}"

            self.write_log(f"Grafik Hazır {msg}")

        except Exception as e:
            traceback.print_exc()
            self.write_log("Grafik Hatası", str(e), "error")

    # --------------------------------------------------------
    # ÇIKIŞ
    # --------------------------------------------------------

    def exit_app(self, *args):

        App.get_running_app().stop()


# ------------------------------------------------------------
# APP
# ------------------------------------------------------------

class LoadManagerApp(App):

    def build(self):

        return MainWindow()


if __name__ == "__main__":
    LoadManagerApp().run()