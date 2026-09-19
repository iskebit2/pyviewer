# main.py
import sys
import traceback
from typing import Any, Dict
import numpy as np


from windcalc.windengine import BuildingWindEngine
from windcalc.windplane import WindPlane
from ui.menu_bar import MenuBar
from ui.button_bar import ButtonBar
from ui.data_dialog import DataDialog


def dict_tree(data, indent=""):
    lines = []

    items = list(data.items())

    for i, (key, value) in enumerate(items):
        last = i == len(items) - 1

        branch = "└── " if last else "├── "
        lines.append(f"{indent}{branch}{key}")

        if isinstance(value, dict):
            new_indent = indent + ("    " if last else "│   ")
            lines.append(dict_tree(value, new_indent))

        else:
            # Yukarıdaki key satırını value ile birleştir
            lines[-1] = f"{indent}{branch}{key} : {value}"

    return "\n".join(lines)

def get_polygon_coords(polygon_points, points, scale_=1000.0):
    """Poligon noktalarını koordinatlara dönüştürür ve ölçekler."""
    coords = []
    for pt_name in polygon_points:
        if pt_name not in points:
            raise ValueError(f"Nokta '{pt_name}' bulunamadı!")
        pt = points[pt_name]
        coords.append([pt[0] / scale_, pt[1] / scale_, pt[2] / scale_])
    return np.array(coords)



from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QTextEdit
)
from PySide6.QtCore import Qt, Signal

from core.canvas3d import View3D
import logging
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s - %(message)s")

class QTextEditHandler(logging.Handler):
    def __init__(self, text_edit):
        super().__init__()
        self.text_edit = text_edit

    def emit(self, record):
        
        self.text_edit.append(self.format(record))

class MainWindow(QMainWindow):
    wind_vector_changed = Signal(object)
    def __init__(self):
        super().__init__()
        self.setWindowTitle("3D Viewer")
        self.setGeometry(100, 100, 800, 600)

        # Veri
        self.view3d = View3D(self)
        self.current_file_path = None
        self.wind_vector = np.array([1.0, 0.0, 0.0])
        self.v_b0 = 28.0
        self.terrain = "Kategori III"
        self.building = None
        self.e = 6000.0

        # UI
        self.setup_ui()
        

        # Sinyaller
        self.view3d.element_selected.connect(self.handle_selection)
        self.view3d.context_menu_action.connect(self.on_context_menu_action)
        if hasattr(self.view3d, 'multi_selection_changed'):
            self.view3d.multi_selection_changed.connect(self.update_buttons)

        self.wind_vector_changed.connect(self.on_wind_vector_changed)
        self.wind_vector_changed.emit(self.wind_vector)

    def setup_logging(self):
        handler = QTextEditHandler(self.log_box)
        handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        logging.getLogger().addHandler(handler)     

    def setup_ui(self):
        # Log
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMaximumHeight(150)
        self.log_box.setStyleSheet("""
            QTextEdit {
                background: #1e1e1e;
                color: #d4d4d4;
                font-family: monospace;
                font-size: 11px;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
            }
        """)
        self.setup_logging()
        self.setMenuBar(MenuBar(self))
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setSpacing(6)
        layout.setContentsMargins(6, 6, 6, 6)

        # Button Bar
        buttons = [
            {"text": "🧪 Test", "callback": self.create_sample_data, "tooltip": "Örnek veri oluştur"},
            {"text": "⚙️ Parameters", "callback": self.set_wind_parameters, "tooltip": "Rüzgar parametreleri"},
            {"text": "🏗️ Building", "callback": self.building_wind_calc, "tooltip": "Bina yükü hesapla"},
            {"text": "📊 Analysis", "callback": self.analyze_selected, "tooltip": "Analiz yap", "enabled": False},
            {"text": "Item", "callback": self.item_selected, "tooltip": "Seçim nesnesini incele", "enabled": False},
        ]

        self.buttonbar = ButtonBar(self, buttons)
        self.buttonbar.add_separator()
        self.buttonbar.add_button("📐 get_from_points", self.get_from_points,
                                  "Seçili 2 noktaya dik vektör", enabled=False)
        self.buttonbar.add_stretch()
        self.buttonbar.add_button("❌ Close", self.close, "Uygulamayı kapat")
        layout.addWidget(self.buttonbar)

        # 3D View
        layout.addWidget(self.view3d, 1)

        layout.addWidget(self.log_box)

    def on_wind_vector_changed(self, vector):
        logging.info("Wind vec... {vector}")
        self.statusBar().showMessage(
            f"Wind dir: {vector}"
        )


    # ==================== BUTON DURUM GÜNCELLEME ====================

    def update_buttons(self, selection=None):
        """Seçime göre buton durumlarını güncelle"""
    
        if not self.buttonbar:
            return

        # Nokta sayısı
        point_count = 0
        if hasattr(self.view3d, 'selected_items'):
            point_count = len(self.view3d.selected_items.get('POINT', []))

        self.buttonbar.set_enabled("📐 get_from_points", point_count == 2)

    def item_selected(self):
        selected_type = self.view3d.selected_type
        selected_id = self.view3d.selected_id

        if not selected_type or not selected_id:
            logging.warning("Lütfen bir öğe seçin!")
            return

        data = self.view3d.get_element_data(selected_type, selected_id)
        if not data:
            logging.warning(f"{selected_type} '{selected_id}' verisi bulunamadı!")
            return

        self.show_data(data, f"{selected_type} Parameters - {selected_id}")
           
        logging.info("{selected_type} Parameters... {selected_id}")
            

    # ==================== RÜZGAR ANALİZİ ====================

    def analyze_selected(self):
        """Seçili elemanı analiz et"""
        if not self.building:
            logging.warning("Önce 'Building' butonuna tıklayarak bina verilerini oluşturun!")
            return

        selected_type = self.view3d.selected_type
        selected_id = self.view3d.selected_id

        if not selected_type or not selected_id:
            logging.warning("Lütfen bir poligon seçin!")
            return

        if selected_type != "POLYGON":
            logging.warning("Lütfen bir poligon seçin!")
            return
        
        try:
            if selected_id not in self.view3d.polygons:
                logging.warning(f"Poligon '{selected_id}' bulunamadı!")
                return

            coords = get_polygon_coords(
                self.view3d.polygons[selected_id],
                self.view3d.points,
                1000
            )

            plane = WindPlane(coords, name=selected_id)
            plane.analysis_(self.wind_vector, self.building)
            self.show_data(plane.edges, "Edge Parameters")
            info = dict_tree(plane.properties)
            # show_data(plane.properties, "Surface Parameters", self)

            logging.info("Surface Wind Analysis...\n"+info)
            

        except Exception as e:
            logging.error(f"Analiz hatası: {e}")
            logging.error(traceback.format_exc())

   

    # ==================== RÜZGAR PARAMETRELERİ ====================

    def set_wind_parameters(self):
        """Rüzgar yönü ve arazi parametrelerini ayarla"""
        from PySide6.QtWidgets import (
            QDialog, QVBoxLayout, QHBoxLayout, QLabel,
            QDoubleSpinBox, QPushButton, QComboBox,
            QGroupBox, QFormLayout
        )

        ARAZI = {
            "Kategori 0": {"z0": 0.003, "zmin": 1.0},
            "Kategori I": {"z0": 0.01, "zmin": 1.0},
            "Kategori II": {"z0": 0.05, "zmin": 2.0},
            "Kategori III": {"z0": 0.3, "zmin": 5.0},
            "Kategori IV": {"z0": 1.0, "zmin": 10.0}
        }

        dialog = QDialog(self)
        dialog.setWindowTitle("Rüzgar Parametreleri")
        dialog.setModal(True)
        dialog.resize(350, 400)

        main_layout = QVBoxLayout(dialog)

        # Terrain
        terrain_group = QGroupBox("Arazi Kategorisi")
        terrain_layout = QFormLayout(terrain_group)

        terrain_combo = QComboBox()
        terrain_combo.addItems(ARAZI.keys())
        terrain_combo.setCurrentText(self.terrain)

        z0_label = QLabel(f"z₀: {ARAZI[self.terrain]['z0']:.3f} m")
        zmin_label = QLabel(f"z_min: {ARAZI[self.terrain]['zmin']:.1f} m")

        terrain_layout.addRow("Kategori:", terrain_combo)
        terrain_layout.addRow("Pürüzlülük Uzunluğu:", z0_label)
        terrain_layout.addRow("Min. Yükseklik:", zmin_label)

        def update_terrain_info():
            selected = terrain_combo.currentText()
            z0_label.setText(f"z₀: {ARAZI[selected]['z0']:.3f} m")
            zmin_label.setText(f"z_min: {ARAZI[selected]['zmin']:.1f} m")

        terrain_combo.currentTextChanged.connect(update_terrain_info)
        main_layout.addWidget(terrain_group)

        # Hız
        speed_group = QGroupBox("Temel Rüzgar Hızı")
        speed_layout = QHBoxLayout(speed_group)
        speed_label = QLabel("v_b0 (m/s):")
        speed_spin = QDoubleSpinBox()
        speed_spin.setRange(10, 100)
        speed_spin.setSingleStep(0.5)
        speed_spin.setValue(self.v_b0)
        speed_layout.addWidget(speed_label)
        speed_layout.addWidget(speed_spin)
        main_layout.addWidget(speed_group)

        # Vektör
        vector_group = QGroupBox("Rüzgar Yönü (Vektör)")
        vector_layout = QVBoxLayout(vector_group)

        self.x_spin = QDoubleSpinBox()
        self.y_spin = QDoubleSpinBox()
        self.z_spin = QDoubleSpinBox()
        for spin in [self.x_spin, self.y_spin, self.z_spin]:
            spin.setRange(-100, 100)
            spin.setSingleStep(0.1)

        self.x_spin.setValue(self.wind_vector[0])
        self.y_spin.setValue(self.wind_vector[1])
        self.z_spin.setValue(self.wind_vector[2])

        for label, spin in [("X:", self.x_spin), ("Y:", self.y_spin), ("Z:", self.z_spin)]:
            h = QHBoxLayout()
            h.addWidget(QLabel(label))
            h.addWidget(spin)
            vector_layout.addLayout(h)

        # get_from_points butonu
        btn_layout = QHBoxLayout()
        get_btn = QPushButton("📐 get_from_points")
        get_btn.setToolTip("Seçili 2 noktaya dik vektör hesapla")

        # Nokta kontrolü
        point_count = len(self.view3d.selected_items.get('point', [])) if hasattr(self.view3d, 'selected_items') else 0
        get_btn.setEnabled(point_count == 2)
        if point_count != 2:
            get_btn.setToolTip(f"2 nokta seçin (Şu an: {point_count})")

        get_btn.clicked.connect(lambda: self._get_from_points_dialog(self.x_spin, self.y_spin, self.z_spin))
        btn_layout.addWidget(get_btn)
        btn_layout.addStretch()
        vector_layout.addLayout(btn_layout)
        main_layout.addWidget(vector_group)

        # OK/Cancel
        btn_layout2 = QHBoxLayout()
        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("İptal")
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout2.addWidget(ok_btn)
        btn_layout2.addWidget(cancel_btn)
        main_layout.addLayout(btn_layout2)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.terrain = terrain_combo.currentText()
            self.v_b0 = speed_spin.value()

            wind_vec = np.array([
                self.x_spin.value(),
                self.y_spin.value(),
                self.z_spin.value()
            ])

            if np.linalg.norm(wind_vec) < 1e-6:
                logging.warning("Rüzgar vektörü sıfır olamaz! Varsayılan kullanılıyor.")
                self.wind_vector = np.array([1.0, 0.0, 0.0])
            else:
                self.wind_vector = wind_vec
                self.wind_vector_changed.emit(self.wind_vector)

            terrain_data = ARAZI[self.terrain]
            self.z0 = terrain_data["z0"]
            self.zmin = terrain_data["zmin"]
            logging.info(f"Arazi: {self.terrain}, z0={self.z0}, zmin={self.zmin}")

    def _get_from_points_dialog(self, x_spin, y_spin, z_spin):
        """Diyalog içinden get_from_points çağrısı"""
        vec = self._calculate_perpendicular_vector()
        if vec is not None:
            x_spin.setValue(vec[0])
            y_spin.setValue(vec[1])
            z_spin.setValue(vec[2])
            self.wind_vector = vec

    def get_from_points(self):
        """Ana butondan get_from_points çağrısı"""
        p1_selected,p2_selected,vec = self._calculate_perpendicular_vector()

        if self.building:
            geom_results = self.building.calculate_obb_and_geometry(p1_selected, p2_selected, self.building.raw_points)
            render_lines = self.building.generate_render_lines(geom_results)

            # if not isinstance(self.view3d.lines, list):
            #     # Eğer dict geldiyse, değerlerine çevir
            #     if isinstance(self.view3d.lines, dict):
            #         self.view3d.lines = list(self.view3d.lines.values())
            #     else:
            #         self.view3d.lines = []
            
            self.view3d.lines= render_lines
            self.view3d.draw_scene()
            
        if vec is not None:
            self.wind_vector = vec
            logging.info(f"📐 Dik vektör: {vec}")

    def _calculate_perpendicular_vector(self):
        """Seçili 2 noktaya dik vektör hesapla"""
        pts = []
        if hasattr(self.view3d, 'selected_items') and hasattr(self.view3d, 'points'):
            sayac=0
            for pid in self.view3d.selected_items.get('POINT', []):
                print(f"{sayac} pid: {pid}")
                sayac+=1
                if pid in self.view3d.points:
                    pts.append(self.view3d.points[pid])

        if len(pts) != 2:
            logging.warning(f"{len(pts)} nokta seçili, 2 gerekli")
            return None

        p1, p2 = np.array(pts[0]), np.array(pts[1])
        vec = p2 - p1
        perp = np.array([-vec[1], vec[0], 0.0])
        norm = np.linalg.norm(perp)

        if norm < 1e-6:
            logging.warning("Vektör sıfır, varsayılan kullanılıyor")
            return np.array([1.0, 0.0, 0.0])

        perp = perp / norm
        logging.info(f"Dik vektör hesaplandı: {perp}")
        return p1,p2,perp

    # ==================== BİNA İŞLEMLERİ ====================
    def building_wind_calc(self):
        """Bina rüzgar yükü hesapla"""

        missing = []

        if not self.view3d.points:
            missing.append("points")

        if not self.view3d.polygons:
            missing.append("polygons")

        if self.v_b0 is None:
            missing.append("v_b0")

        if self.terrain is None:
            missing.append("terrain")

        if self.wind_vector is None:
            missing.append("wind_vector")

        if missing:
            logging.error("Eksik bilgi: %s", ", ".join(missing))
            return

        self.statusBar().showMessage("Building Wind Calc...")

        self.building = BuildingWindEngine(
            points=self.view3d.points,
            polygons=self.view3d.polygons,
            v_b0=self.v_b0,
            terrain=self.terrain,
            w_dir=self.wind_vector,
            scale_factor=1000.0
        )

        info = dict_tree(self.building.get_summary())
        logging.info("Building Wind Calc...\n%s", info)
    # ==================== ÖRNEK VERİ ====================

    def create_sample_data(self):
        """Örnek 3D veriler oluştur"""
        points = {
            "P1": (0.0, 0.0, 0.0),
            "P2": (12000.0, 0.0, 0.0),
            "P3": (12000.0, 8000.0, 0.0),
            "P4": (0.0, 8000.0, 0.0),
            "P5": (0.0, 0.0, 4000.0),
            "P6": (12000.0, 0.0, 4000.0),
            "P7": (12000.0, 8000.0, 4000.0),
            "P8": (0.0, 8000.0, 4000.0),
            "P9": (3000.0, 4000.0, 5000.0),
            "P10": (12000.0, 4000.0, 5000.0),
        }

        polygons = {
            "D1": ["P1", "P2", "P6", "P5"],
            "D2": ["P1", "P5", "P8", "P4"],
            "D3": ["P2", "P3", "P7", "P10", "P6"],
            "D4": ["P3", "P4", "P8", "P7"],
            "C1": ["P5", "P6", "P10", "P9"],
            "C2": ["P8", "P9", "P10", "P7"],
            "C3": ["P8", "P5", "P9"],
        }

        frames = {}
        for name, poly in polygons.items():
            for i in range(len(poly)):
                frames[f"{name}_F{i+1}"] = (poly[i], poly[(i + 1) % len(poly)])

        self.view3d.set_data(points, polygons, {}, frames)
        self.view3d.zoom_extents()
        logging.info("Örnek veri oluşturuldu")

    # ==================== EVENT HANDLER'LAR ====================

    def on_context_menu_action(self, action_name: str, data: dict):
        """Context menu aksiyonlarını işler"""
        actions = {
            "ANALYZE": self.analyze_selected,
            "SET_WIND": self.set_wind_parameters,
            "SET_E": self.set_building_size,
        }
        if action_name in actions:
            try:
                actions[action_name]()
            except Exception as e:
                logging.error(f"Action error: {e}")

    def handle_selection(self, elem_type: str, elem_id: str, data: Any):
        """Seçim işlemini handle eder"""
        if elem_type in ["POLYGON", "FRAME", "POINT", "EDGE"]:
            self.buttonbar.set_enabled("Item", True)
        else:
            self.buttonbar.set_enabled("Item", False)


        if elem_type =="POLYGON":
            self.buttonbar.set_enabled("📊 Analysis", True)
            
        else:
            self.buttonbar.set_enabled("📊 Analysis", False)
            


        if elem_type == "EDGE" and isinstance(data, dict):
            poly_name = data.get("selected_polygon")
            if poly_name:
                logging.debug(f"Edge selected in polygon: {poly_name}")

    def set_building_size(self):
        """Bina boyutunu (e) ayarla"""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QDoubleSpinBox, QPushButton

        dialog = QDialog(self)
        dialog.setWindowTitle("Bina Boyutu")
        dialog.setModal(True)
        dialog.resize(300, 150)

        layout = QVBoxLayout(dialog)
        h = QHBoxLayout()
        h.addWidget(QLabel("e Değeri (mm):"))
        spin = QDoubleSpinBox()
        spin.setRange(100, 100000)
        spin.setSingleStep(100)
        spin.setValue(self.e)
        h.addWidget(spin)
        layout.addLayout(h)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("İptal")
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.e = spin.value()
            logging.info(f"e değeri: {self.e} mm")

    def closeEvent(self, event):
        """Pencere kapanırken temizlik"""
        try:
            if hasattr(self, 'view3d') and self.view3d:
                self.view3d.scene.clear()
                for attr in ['point_items', 'polygon_items', 'edge_items', 'frame_items', 'line_items']:
                    if hasattr(self.view3d, attr):
                        getattr(self.view3d, attr).clear()
        except Exception as e:
            logging.warning(f"Cleanup error: {e}")
        event.accept()

    def show_data(self, data, title= "Data"):
        
        self.data_dialog = DataDialog(
                                data,
                                title= title,
                                parent=self
                            )

        self.data_dialog.setModal(False)
        self.data_dialog.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())