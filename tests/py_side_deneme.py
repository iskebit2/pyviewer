import sys
import copy

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QLabel,
    QLineEdit,
    QCheckBox,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QScrollArea,
    QGroupBox,
    QMessageBox,
)


class dataPanel(QGroupBox):

    def __init__(self, parent, data, title="Parametreler"):
        super().__init__(title, parent)

        self.data = data
        self.original = copy.deepcopy(data)

        self.entries = {}

        self._build()

    # ---------------------------------------------------------
    # GUI
    # ---------------------------------------------------------

    def _build(self):

        main_layout = QVBoxLayout(self)

        # -----------------------------------------------------
        # Scroll area
        # -----------------------------------------------------

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        frame = QWidget()
        grid = QGridLayout(frame)

        grid.setColumnStretch(1, 1)

        scroll.setWidget(frame)

        main_layout.addWidget(scroll)

        # -----------------------------------------------------
        # Parametreler
        # -----------------------------------------------------

        for row, (key, value) in enumerate(self.data.items()):

            label = QLabel(key)

            grid.addWidget(
                label,
                row,
                0
            )

            if isinstance(value, bool):

                widget = QCheckBox()

                widget.setChecked(value)

            else:

                widget = QLineEdit(
                    str(value)
                )

            grid.addWidget(
                widget,
                row,
                1
            )

            self.entries[key] = widget

        # -----------------------------------------------------
        # Butonlar
        # -----------------------------------------------------

        buttons = QHBoxLayout()

        reset_button = QPushButton("Geri Al")
        cancel_button = QPushButton("İptal")
        save_button = QPushButton("✓ Kaydet")
        analysis_button = QPushButton("Hesapla")

        buttons.addWidget(reset_button)

        buttons.addStretch()

        buttons.addWidget(cancel_button)
        buttons.addWidget(save_button)
        buttons.addWidget(analysis_button)

        main_layout.addLayout(buttons)

        # -----------------------------------------------------
        # Signal → Slot
        # -----------------------------------------------------

        reset_button.clicked.connect(self.reset)
        cancel_button.clicked.connect(self.cancel)
        save_button.clicked.connect(self.save)
        analysis_button.clicked.connect(self.analysis)

    # -----

    def analysis(self):
        print("analysis")
    # ---------------------------------------------------------

    def _convert(self, value, original):

        if isinstance(original, bool):
            return value

        if isinstance(original, int):
            return int(value)

        if isinstance(original, float):
            return float(value)

        if original is None:
            return value

        return value

    # ---------------------------------------------------------

    def save(self):

        try:

            for key, original in self.original.items():

                widget = self.entries[key]

                if isinstance(original, bool):

                    value = widget.isChecked()

                else:

                    value = widget.text()

                self.data[key] = self._convert(
                    value,
                    original
                )

            self.original = copy.deepcopy(self.data)

        except (ValueError, TypeError) as e:

            QMessageBox.critical(
                self,
                "Geçersiz Değer",
                f"'{key}' için geçersiz değer:\n\n{e}"
            )

    # ---------------------------------------------------------

    def reset(self):

        for key, value in self.original.items():

            widget = self.entries[key]

            if isinstance(value, bool):

                widget.setChecked(value)

            else:

                widget.setText(str(value))

    # ---------------------------------------------------------

    def cancel(self):

        self.data.clear()

        self.data.update(
            copy.deepcopy(self.original)
        )

        self.window().close()

    # ---------------------------------------------------------

    def get(self):

        return self.data


# =============================================================
# Test
# =============================================================

if __name__ == "__main__":

    myconfig = {
        'b': 8.21,
        'd': 4.56,
        'z0': 0.0,
        'z1': 10.45,
        'z2': 11.344,
        'v_b0': 28.0,
        'egim': 21.43,
        'roof_type': 'Beşik',
        'mahya_paralel': 'b',
        'terrain': 'Kategori III'
    }

    config = {
        "slope": 23.41,
        "snow_region": 2,
        "altitude": 50,
        "Ce": 1.0,
        "Ct": 1.0
    }
    app = QApplication(sys.argv)

    window = QMainWindow()
    window.setWindowTitle("Rüzgar Parametreleri")
    window.resize(500, 450)

    panel = dataPanel(
        window,
        config,
        title="Rüzgar Parametreleri"
    )

    window.setCentralWidget(panel)

    window.show()

    sys.exit(app.exec())