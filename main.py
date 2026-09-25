# main.py
"""
3D Viewer — MainWindow.

Bileşenler:
- View3D            : 3D görselleştirme ve seçim
- ElementDataService: View3D + building arasında eşleştirme
- DataDock          : DataPanel'i dock/float barındırır
- WindCalc          : Rüzgar analizi (windcalc.analysis)

Analiz akışı:
    view3d.points + view3d.polygons
        → windcalc.analysis.analyze()  →  ZoneBundle
        → element_service.set_building(bundle)
        → view3d.zones = {surface_name: [zone, ...]}
"""

import sys
import json
import logging
import traceback
from typing import Any, Dict, Optional

import numpy as np

from windcalc.analysis import analyze as wind_analyze, ZoneBundle
from windcalc.windengine import WindEngine  # sadece OBB/render için

from core.canvas3d import View3D
from core.element_service import ElementDataService

from ui.menu_bar import MenuBar
from ui.button_bar import ButtonBar
from ui.data_dock import DataDock

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QTextEdit,
)


# =============================================================
# LOGGING
# =============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s - %(message)s",
)


class QTextEditHandler(logging.Handler):
    """Log kayıtlarını bir QTextEdit'e yazan handler."""

    def __init__(self, text_edit: QTextEdit):
        super().__init__()
        self.text_edit = text_edit

    def emit(self, record):
        try:
            self.text_edit.append(self.format(record))
        except RuntimeError:
            pass


# =============================================================
# YARDIMCILAR
# =============================================================

def dict_tree(data, indent="") -> str:
    """Sözlüğü okunabilir ağaç metnine çevirir."""
    lines = []
    items = list(data.items())

    for i, (key, value) in enumerate(items):
        last = i == len(items) - 1
        branch = "└── " if last else "├── "

        if isinstance(value, dict):
            lines.append(f"{indent}{branch}{key}")
            new_indent = indent + ("    " if last else "│   ")
            sub = dict_tree(value, new_indent)
            if sub:
                lines.append(sub)
        else:
            lines.append(f"{indent}{branch}{key} : {value}")

    return "\n".join(lines)


# =============================================================
# MAIN WINDOW
# =============================================================

class MainWindow(QMainWindow):

    wind_vector_changed = Signal(object)

    def __init__(self):
        super().__init__()

        self.setWindowTitle("3D Viewer")
        self.setGeometry(100, 100, 1200, 800)
        self.maindata = {}
        # ---- Veri ----
        self.wind_vector = np.array([1.0, 0.0, 0.0])
        self.v_b0 = 28.0
        self.terrain = "Kategori III"
        self.bundle: Optional[ZoneBundle] = None   # ← yeni analiz sonucu
        self.building = None                         # geriye dönük uyumluluk
        self.e = 6000.0
        self.current_file_path = None

        # ---- Çekirdek bileşenler ----
        self.view3d = View3D(self)
        self.element_service = ElementDataService(
            view3d=self.view3d,
            building=None,
        )

        # ---- UI ----
        self._setup_ui()
        self._setup_data_dock()
        self._connect_signals()

        self.wind_vector_changed.emit(self.wind_vector)

    # =========================================================
    # UI KURULUM
    # =========================================================

    def _setup_ui(self):
        # Log kutusu
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
        self._setup_logging()

        # Menü
        self.setMenuBar(MenuBar(self))

        # Merkezi widget
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setSpacing(6)
        layout.setContentsMargins(6, 6, 6, 6)

        # Button bar
        buttons = [
            {"text": "🧪 Test",         "callback": self.create_sample_data,
             "tooltip": "Örnek veri oluştur"},
            {"text": "⚙️ Parameters",   "callback": self.set_wind_parameters,
             "tooltip": "Rüzgar parametreleri"},
            {"text": "🏗️ Building",    "callback": self.building_wind_calc,
             "tooltip": "Bina yükü hesapla"},
            {"text": "📊 Analysis",     "callback": self.analyze_selected,
             "tooltip": "Analiz yap", "enabled": False},
            {"text": "Item",            "callback": self.item_selected,
             "tooltip": "Seçim nesnesini incele", "enabled": False},
            {"text": "Yük Analizi",    "callback": self.yuk_analiz,
             "tooltip": "Yük Analizi"},
        ]

        self.buttonbar = ButtonBar(self, buttons)
        self.buttonbar.add_separator()
        self.buttonbar.add_button(
            "📐 get_from_points",
            self.get_from_points,
            "Seçili 2 noktaya dik vektör",
            enabled=False,
        )
        self.buttonbar.add_stretch()
        self.buttonbar.add_button("❌ Close", self.close, "Uygulamayı kapat")

        layout.addWidget(self.buttonbar)
        layout.addWidget(self.view3d, 1)
        layout.addWidget(self.log_box)

    def _setup_logging(self):
        handler = QTextEditHandler(self.log_box)
        handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        logging.getLogger().addHandler(handler)

    def _setup_data_dock(self):
        """DataDock'u sağ tarafa dock et, başlangıçta gizle."""
        self.data_dock = DataDock(
            view3d=self.view3d,
            parent=self,
            title="Data",
        )
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea,
                            self.data_dock)
        self.resizeDocks([self.data_dock], [420],
                          Qt.Orientation.Horizontal)
        self.data_dock.hide()

    def _connect_signals(self):
        self.view3d.element_selected.connect(self.handle_selection)
        self.view3d.context_menu_action.connect(self.on_context_menu_action)
        self.view3d.properties_requested.connect(self.on_properties_requested)

        if hasattr(self.view3d, "multi_selection_changed"):
            self.view3d.multi_selection_changed.connect(self.update_buttons)

        self.wind_vector_changed.connect(self.on_wind_vector_changed)

    # =========================================================
    # DATADOCK KONTROL
    # =========================================================

    def _open_data_dock(self):
        if not self.data_dock.isVisible():
            self.data_dock.show()
        self.data_dock.raise_()

    def on_properties_requested(self, elem_type: str, elem_id: str):
        logging.debug(f"on_properties_requested: {elem_type}:{elem_id}")

        if not elem_type or not elem_id:
            return

        self._open_data_dock()

        info = self.element_service.resolve(elem_type, elem_id)
        self.data_dock.set_element_info(info)

    def show_selected_properties(self):
        """View3D'nin eski API'si ile uyumluluk."""
        sel_type = self.view3d.selected_type
        sel_id = self.view3d.selected_id
        if sel_type and sel_id:
            self.on_properties_requested(sel_type, sel_id)

    # =========================================================
    # SEÇİM
    # =========================================================

    def handle_selection(self, elem_type, elem_id, data):
        logging.debug(f"handle_selection: {elem_type}: {elem_id}")

        self.buttonbar.set_enabled(
            "Item", elem_type in ("POLYGON", "POINT", "EDGE", "FRAME", "ZONE")
        )
        self.buttonbar.set_enabled("📊 Analysis", elem_type == "POLYGON")

        if not self.data_dock.isVisible():
            return

        if elem_type is None or elem_id is None:
            self.data_dock.clear_selection()
            return

        info = self.element_service.resolve(elem_type, elem_id)
        self.data_dock.set_element_info(info)

    def update_buttons(self, selection=None):
        if not self.buttonbar:
            return

        point_count = len(self.view3d.selected_items.get("POINT", []))
        self.buttonbar.set_enabled("📐 get_from_points", point_count == 2)

    # =========================================================
    # ANALİZ
    # =========================================================

    def analyze_selected(self):
        if self.bundle is None:
            logging.warning("Önce 'Building' butonuna tıklayın!")
            return

        sel_type = self.view3d.selected_type
        sel_id = self.view3d.selected_id

        if sel_type and sel_id:
            self.on_properties_requested(sel_type, sel_id)
        else:
            self._open_data_dock()
            self.data_dock.set_data(
                self._all_wind_planes(),
                title="All Surfaces",
            )

    def item_selected(self):
        sel_type = self.view3d.selected_type
        sel_id = self.view3d.selected_id

        if not sel_type or not sel_id:
            logging.warning("Lütfen bir öğe seçin!")
            return

        self.on_properties_requested(sel_type, sel_id)

    def _all_wind_planes(self) -> Dict[str, Any]:
        """ZoneBundle'dan tüm surfaces'leri al (UI uyumu)."""
        if self.bundle is None:
            return {}
        return dict(self.bundle.wind_planes)

    # =========================================================
    # BİNA — YENİ ANALİZ AKIŞI
    # =========================================================

    def building_wind_calc(self):
        """
        Bina rüzgar yükü hesapla.

        Yeni akış:
            view3d.points + view3d.polygons
                → windcalc.analysis.analyze() → ZoneBundle
                → element_service.set_building(bundle)
                → view3d.zones senkronizasyonu
        """
        missing = []
        if not self.view3d.points:      missing.append("points")
        if not self.view3d.polygons:    missing.append("polygons")
        if self.v_b0 is None:           missing.append("v_b0")
        if self.terrain is None:        missing.append("terrain")
        if self.wind_vector is None:    missing.append("wind_vector")

        if missing:
            logging.error("Eksik bilgi: %s", ", ".join(missing))
            return

        self.statusBar().showMessage("Building Wind Calc...")

        try:
            self.bundle = wind_analyze(
                points=self.view3d.points,
                polygons=self.view3d.polygons,
                v_b0=self.v_b0,
                terrain=self.terrain,
                w_list={"w": np.asarray(self.wind_vector, dtype=float)},
                verbose=False,
            )
        except Exception as e:
            logging.error(f"Analiz hatası: {e}")
            logging.error(traceback.format_exc())
            return

        # Geriye dönük uyumluluk — eski kod `self.building` arıyor
        self.building = self.bundle

        # UI servisini besle
        self.element_service.set_building(self.bundle)

        # View3D'ye zone'ları aktar
        self._sync_bundle_to_view3d()

        # Özet log
        first = self.bundle.results[0] if self.bundle.results else None
        if first is not None:
            info_types = {k: type(v).__name__
                          for k, v in first.all_surfaces.items()}
            logging.info("Analiz tamamlandı: %s", info_types)

        self.statusBar().showMessage("Analiz tamamlandı", 3000)

    # =========================================================
    # VIEW3D SENKRONİZASYONU
    # =========================================================

    def _sync_bundle_to_view3d(self):
        """
        ZoneBundle'daki zone'ları View3D'ye aktar.

        Format: {surface_name: [Zone, Zone, ...]}
        """
        if self.bundle is None:
            return

        zones_by_surface: Dict[str, list] = {}
        for surf_name, surf in self.bundle.wind_planes.items():
            zones_by_surface[surf_name] = list(getattr(surf, "zones", []) or [])

        self.view3d.zones = zones_by_surface

        if hasattr(self.view3d, "_visibility_states"):
            self.view3d._visibility_states.clear()
        if hasattr(self.view3d, "rebuild"):
            self.view3d.rebuild()
        if hasattr(self.view3d, "update"):
            self.view3d.update()

    # =========================================================
    # RÜZGAR PARAMETRELERİ
    # =========================================================

    def set_wind_parameters(self):
        """Rüzgar yönü ve arazi parametrelerini ayarla."""
        from PySide6.QtWidgets import (
            QComboBox, QDialog, QDoubleSpinBox, QFormLayout,
            QGroupBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
        )

        ARAZI = {
            "Kategori 0":   {"z0": 0.003, "zmin": 1.0},
            "Kategori I":   {"z0": 0.01,  "zmin": 1.0},
            "Kategori II":  {"z0": 0.05,  "zmin": 2.0},
            "Kategori III": {"z0": 0.3,   "zmin": 5.0},
            "Kategori IV":  {"z0": 1.0,   "zmin": 10.0},
        }

        dialog = QDialog(self)
        dialog.setWindowTitle("Rüzgar Parametreleri")
        dialog.setModal(True)
        dialog.resize(350, 400)

        main_layout = QVBoxLayout(dialog)

        # ---- Terrain ----
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

        # ---- Hız ----
        speed_group = QGroupBox("Temel Rüzgar Hızı")
        speed_layout = QHBoxLayout(speed_group)
        speed_layout.addWidget(QLabel("v_b0 (m/s):"))

        speed_spin = QDoubleSpinBox()
        speed_spin.setRange(10, 100)
        speed_spin.setSingleStep(0.5)
        speed_spin.setValue(self.v_b0)
        speed_layout.addWidget(speed_spin)
        main_layout.addWidget(speed_group)

        # ---- Vektör ----
        vector_group = QGroupBox("Rüzgar Yönü (Vektör)")
        vector_layout = QVBoxLayout(vector_group)

        x_spin = QDoubleSpinBox()
        y_spin = QDoubleSpinBox()
        z_spin = QDoubleSpinBox()
        for spin in (x_spin, y_spin, z_spin):
            spin.setRange(-100, 100)
            spin.setSingleStep(0.1)

        x_spin.setValue(self.wind_vector[0])
        y_spin.setValue(self.wind_vector[1])
        z_spin.setValue(self.wind_vector[2])

        for label, spin in (("X:", x_spin), ("Y:", y_spin), ("Z:", z_spin)):
            h = QHBoxLayout()
            h.addWidget(QLabel(label))
            h.addWidget(spin)
            vector_layout.addLayout(h)

        # get_from_points butonu
        btn_layout = QHBoxLayout()
        get_btn = QPushButton("📐 get_from_points")
        get_btn.setToolTip("Seçili 2 noktaya dik vektör hesapla")

        point_count = len(self.view3d.selected_items.get("POINT", []))
        get_btn.setEnabled(point_count == 2)
        if point_count != 2:
            get_btn.setToolTip(f"2 nokta seçin (Şu an: {point_count})")

        get_btn.clicked.connect(
            lambda: self._get_from_points_dialog(x_spin, y_spin, z_spin)
        )
        btn_layout.addWidget(get_btn)
        btn_layout.addStretch()
        vector_layout.addLayout(btn_layout)
        main_layout.addWidget(vector_group)

        # ---- OK / İptal ----
        btn_layout2 = QHBoxLayout()
        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("İptal")
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout2.addWidget(ok_btn)
        btn_layout2.addWidget(cancel_btn)
        main_layout.addLayout(btn_layout2)

        # ---- Onay ----
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.terrain = terrain_combo.currentText()
            self.v_b0 = speed_spin.value()

            wind_vec = np.array([
                x_spin.value(),
                y_spin.value(),
                z_spin.value(),
            ])

            if np.linalg.norm(wind_vec) < 1e-6:
                logging.warning(
                    "Rüzgar vektörü sıfır olamaz! Varsayılan kullanılıyor."
                )
                self.wind_vector = np.array([1.0, 0.0, 0.0])
            else:
                self.wind_vector = wind_vec
                self.wind_vector_changed.emit(self.wind_vector)

            terrain_data = ARAZI[self.terrain]
            self.z0 = terrain_data["z0"]
            self.zmin = terrain_data["zmin"]
            logging.info(
                f"Arazi: {self.terrain}, z0={self.z0}, zmin={self.zmin}"
            )

    def _get_from_points_dialog(self, x_spin, y_spin, z_spin):
        result = self._calculate_perpendicular_vector()
        if result is None:
            return

        _, _, vec = result
        x_spin.setValue(vec[0])
        y_spin.setValue(vec[1])
        z_spin.setValue(vec[2])
        self.wind_vector = vec

    # =========================================================
    # DİK VEKTÖR
    # =========================================================

    def get_from_points(self):
        result = self._calculate_perpendicular_vector()
        if result is None:
            logging.warning("Dik vektör hesaplanamadı (2 nokta seçin).")
            return

        p1_sel, p2_sel, vec = result

        if self.building is not None:
            geom_results = self.building.calculate_obb_and_geometry(
                p1_sel, p2_sel, self.building.raw_points
            )
            render_lines = self.building.generate_render_lines(geom_results)

            self.view3d.lines = render_lines
            self.view3d.draw_scene()

        self.wind_vector = vec
        self.wind_vector_changed.emit(self.wind_vector)
        logging.info(f"📐 Dik vektör: {vec}")

    def _calculate_perpendicular_vector(self):
        pts = []
        for pid in self.view3d.selected_items.get("POINT", []):
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
            perp = np.array([1.0, 0.0, 0.0])
        else:
            perp = perp / norm

        logging.info(f"Dik vektör hesaplandı: {perp}")
        return p1, p2, perp

    # =========================================================
    # Yük Analizi
    # =========================================================

    def yuk_analiz(self):
        """Komut satırı testi — hızlı building + render."""
        from loads.load_manager import MainWindow
        self.loadmanager = MainWindow(self.maindata)
        self.loadmanager.show()

    def _compute_render_geometry(self, points, w_dir):
        """
        Rüzgar oku için OBB/render çizgileri üretir.
        BuildingWindEngine bu iş için hâlâ kullanılıyor.
        """
        try:
            engine = WindEngine(
                points=points,
                polygons=self.view3d.polygons,
                v_b0=28.0,
                terrain="Kategori III",
                w_dir=w_dir,
                scale_factor=1.0,
            )
            p1_sel = getattr(self, "p1_sel", [-w_dir[1], w_dir[0], 0.0])
            p2_sel = getattr(self, "p2_sel", [0.0, 0.0, 0.0])
            geom = engine.calculate_obb_and_geometry(p1_sel, p2_sel, points)
            return (
                engine.generate_render_lines(geom)
                if geom is not None else []
            )
        except Exception as e:
            print(f"[render_geometry] {e}")
            return []

    @staticmethod
    def _print_summary(summary: Dict[str, Any]) -> None:
        print(json.dumps(summary, indent=2, ensure_ascii=False, default=str))

    # =========================================================
    # ÖRNEK VERİ
    # =========================================================

    def create_sample_data(self):
        """Örnek 3D veriler oluştur."""
        points = {
            "P1":  (0.0, 0.0, 0.0),
            "P2":  (12000.0, 0.0, 0.0),
            "P3":  (12000.0, 8000.0, 0.0),
            "P4":  (0.0, 8000.0, 0.0),
            "P5":  (0.0, 0.0, 4000.0),
            "P6":  (12000.0, 0.0, 4000.0),
            "P7":  (12000.0, 8000.0, 4000.0),
            "P8":  (0.0, 8000.0, 4000.0),
            "P9":  (3000.0, 4000.0, 5000.0),
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

    # =========================================================
    # EVENT HANDLERS
    # =========================================================

    def on_context_menu_action(self, action_name: str, data: dict):
        actions = {
            "ANALYZE":  self.analyze_selected,
            "SET_WIND": self.set_wind_parameters,
            "SET_E":    self.set_building_size,
        }
        handler = actions.get(action_name)
        if handler is None:
            return
        try:
            handler()
        except Exception as e:
            logging.error(f"Action error: {e}")
            logging.error(traceback.format_exc())

    def on_wind_vector_changed(self, vector):
        logging.info(f"Wind vector changed: {vector}")
        self.statusBar().showMessage(f"Wind dir: {vector}")

    def set_building_size(self):
        from PySide6.QtWidgets import (
            QDialog, QDoubleSpinBox, QHBoxLayout, QLabel,
            QPushButton, QVBoxLayout,
        )

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

    # =========================================================
    # KAPATMA
    # =========================================================

    def closeEvent(self, event):
        try:
            if hasattr(self, "data_dock") and self.data_dock is not None:
                try:
                    self.data_dock.close()
                except RuntimeError:
                    pass

            if hasattr(self, "view3d") and self.view3d is not None:
                self.view3d.scene.clear()
                for attr in ("point_items", "polygon_items", "edge_items",
                             "frame_items", "zone_items",
                             "graphics_line_items"):
                    store = getattr(self.view3d, attr, None)
                    if store is not None and hasattr(store, "clear"):
                        store.clear()
        except Exception as e:
            logging.warning(f"Cleanup error: {e}")

        event.accept()


# =============================================================
# ENTRY POINT
# =============================================================

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()