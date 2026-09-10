import sys




from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
)

from canvas3d import View3D

class ButtonBar(QWidget):

    def __init__(self, parent=None, buttons=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        if buttons:
            for text, callback in buttons.items():
                button = QPushButton(text)
                button.clicked.connect(callback)

                # Buton kendi boyutunda kalsın
                button.setFixedWidth(70)

                layout.addWidget(button)


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("3D Viewer")
        self.setGeometry(100, 100, 800, 600)

        self.view3d = View3D(self)

        self.setup_ui()

    def setup_ui(self):

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # -----------------
        # ButtonBar
        # -----------------

        buttons = {
            "Yeni": self.new_file,
            "Aç": self.open_file,
            "Kaydet": self.save_file,
            "Sil": self.delete_file,
        }

        buttonbar = ButtonBar(self, buttons)

        # ButtonBar üstte, kendi boyutunda
        main_layout.addWidget(buttonbar)

        # View3D kalan bütün alanı kaplar
        main_layout.addWidget(self.view3d, 1)

        # -----------------
        # StatusBar
        # -----------------

        self.statusBar().showMessage("Hazır")

    def new_file(self):
        self.statusBar().showMessage("Yeni dosya")

    def open_file(self):
        self.statusBar().showMessage("Dosya açılıyor...")

    def save_file(self):
        self.statusBar().showMessage("Dosya kaydedildi")

    def delete_file(self):
        self.statusBar().showMessage("Silindi")


app = QApplication(sys.argv)

window = MainWindow()
window.show()

sys.exit(app.exec())

