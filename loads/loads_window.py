import ast
import json
import sys

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from loads.dead_load import DeadLoad
from loads.live_load import LiveLoad
from loads.snow_load import SnowLoad
from windcalc.windengine import WindEngine
from loads.spectrum import EarthquakeLoad
from loads.spectrum_plot import SpectrumPlot



# ----------------------------------------------------------------------
# Analiz tanımları
# ----------------------------------------------------------------------

ANALYSES = [

    (
        "wind",
        "Rüzgar",
        lambda config, data: WindEngine(
            points=config["points"],
            polygons=config["polygons"],
            **data
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

    (
        "dead",
        "Ölü Yük",
        lambda config, data: DeadLoad(data)
    ),

    (
        "live",
        "Hareketli Yük",
        lambda config, data: LiveLoad(data)
    ),
]



# ----------------------------------------------------------------------
# DataPanel
# ----------------------------------------------------------------------

class DataPanel(QGroupBox):

    calculate_requested = Signal()

    def __init__(self, title="", parent=None):
        super().__init__(title, parent)

        self.data = {}
        self.original_data = {}
        self.inputs = {}

        self.main_layout = QVBoxLayout(self)

        self.form = QWidget()
        self.form_layout = QVBoxLayout(self.form)

        self.main_layout.addWidget(self.form)

        buttons = QHBoxLayout()

        self.reset_button = QPushButton("Geri Al")
        self.cancel_button = QPushButton("İptal")
        self.save_button = QPushButton("✓ Kaydet")
        self.calculate_button = QPushButton("Hesapla")

        buttons.addWidget(self.reset_button)
        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.save_button)
        buttons.addWidget(self.calculate_button)

        self.main_layout.addLayout(buttons)

        self.reset_button.clicked.connect(self.reset)
        self.cancel_button.clicked.connect(self.reset)
        self.save_button.clicked.connect(self.save)
        self.calculate_button.clicked.connect(self.calculate)

    # ------------------------------------------------------------------

    def set_data(self, data):
        self.data = dict(data)
        self.original_data = dict(data)

        self._clear()
        self._build()

    # ------------------------------------------------------------------

    def _clear(self):

        self.inputs.clear()

        while self.form_layout.count():

            item = self.form_layout.takeAt(0)

            if item.widget():
                item.widget().deleteLater()

    # ------------------------------------------------------------------

    def _build(self):

        for key, value in self.data.items():

            row = QHBoxLayout()

            label = QLabel(key)

            if isinstance(value, bool):

                widget = QCheckBox()
                widget.setChecked(value)

            else:

                widget = QLineEdit(str(value))

            self.inputs[key] = widget

            row.addWidget(label)
            row.addWidget(widget)

            self.form_layout.addLayout(row)

    # ------------------------------------------------------------------

    def _convert(self, key, widget):

        old_value = self.data[key]

        if isinstance(old_value, bool):
            return widget.isChecked()

        text = widget.text().strip()

        if isinstance(old_value, dict):
            return ast.literal_eval(text)

        if isinstance(old_value, list):
            return ast.literal_eval(text)

        if isinstance(old_value, int):
            return int(text)

        if isinstance(old_value, float):
            return float(text)

        return text

    # ------------------------------------------------------------------

    def get(self):

        return {
            key: self._convert(key, widget)
            for key, widget in self.inputs.items()
        }

    # ------------------------------------------------------------------

    def save(self):

        try:
            self.data = self.get()

        except (ValueError, TypeError) as e:

            QMessageBox.warning(
                self,
                "Geçersiz değer",
                str(e)
            )

            return False

        return True

    # ------------------------------------------------------------------

    def reset(self):

        self.data = dict(self.original_data)

        self._clear()
        self._build()

    # ------------------------------------------------------------------

    def calculate(self):

        if self.save():
            self.calculate_requested.emit()


# ----------------------------------------------------------------------
# MainWindow
# ----------------------------------------------------------------------

class MainWindow(QMainWindow):

    def __init__(self, config=None, parent=None):
        super().__init__()

        self.setWindowTitle("Yapı Analizleri")
        self.resize(800, 600)

        self.config = config
        self.parent_ = parent
        self.panels = {}
        self.analysis_factories = {}

        self.spectrum_button = QPushButton("Grafik")
        self.spectrum_button.hide()

        self.open_button = QPushButton("Dosya Aç")
        self._build_ui()
        if config is not None:
            self.open_button.hide()
            self.load_config(config)



        self.spectrum_button.clicked.connect(self.show_spectrum)
        

    # ------------------------------------------------------------------

    def _build_ui(self):

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)

        # Dosya aç
        top = QHBoxLayout()

        

        top.addWidget(self.open_button)
        top.addWidget(self.spectrum_button)
        top.addStretch()

        main_layout.addLayout(top)

        self.open_button.clicked.connect(self.open_file)

        # Sekmeler
        self.tabs = QTabWidget()

        main_layout.addWidget(self.tabs)

        # Analizler
        for key, title, factory in ANALYSES:

            panel = DataPanel(title)

            panel.calculate_requested.connect(
                lambda key=key: self.calculate(key)
            )

            self.panels[key] = panel
            self.analysis_factories[key] = factory

            self.tabs.addTab(panel, title)

        # Sonuç
        self.result = QTextEdit()
        self.result.setReadOnly(True)

        main_layout.addWidget(self.result)

    # ------------------------------------------------------------------

    def open_file(self):

        filename, _ = QFileDialog.getOpenFileName(
            self,
            "JSON dosyası aç",
            "",
            "JSON Files (*.json)"
        )

        if not filename:
            return

        try:

            with open(filename, "r", encoding="utf-8") as f:
                config = json.load(f)

        except Exception as e:

            QMessageBox.critical(
                self,
                "Dosya Hatası",
                str(e)
            )

            return

        self.load_config(config)

    # ------------------------------------------------------------------

    def load_config(self, config):

        self.config = config

        for key, panel in self.panels.items():

            data = config.get(
                f"{key}_config",
                {}
            )

            panel.set_data(data)

        self.result.clear()

    # ------------------------------------------------------------------

    def calculate(self, key):
        if key == "earthquake":
            self.spectrum_button.hide()
        try:

            data = self.panels[key].get()

            factory = self.analysis_factories[key]

            analysis = factory(
                self.config,
                data
            )

            self.result.setPlainText(
                str(analysis.report())
            )

            if key == "earthquake":
                self.earthquake_analysis = analysis
                self.spectrum_button.show()


        except Exception as e:

            QMessageBox.critical(
                self,
                "Hesap Hatası",
                str(e)
            )

    def show_spectrum(self):

        if not hasattr(self, "earthquake_analysis"):
            return

        self.spectrum_plot = SpectrumPlot()

        self.spectrum_plot.set_spectrum(
            self.earthquake_analysis
        )

        self.spectrum_plot.show()


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------

if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())