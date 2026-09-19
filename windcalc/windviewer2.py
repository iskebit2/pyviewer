# import os
# import sys

# # SHIBOKEN İZLEMESİNİ DİĞER TÜM İMPORTLARDAN ÖNCE KAPAT
# os.environ['SHIBOKEN_DISABLE_FEATURE'] = '1'

# try:
#     import shibokensupport.feature

#     shibokensupport.feature.import_hook_disabled = True
# except Exception:
#     pass
import sys
from typing import Any, Dict
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton
import numpy as np
from core.canvas3d import View3D

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

W_LIST = {
    "x+": [1, 0, 0],
    "y+": [0, 1, 0],
    "x-": [-1, 0, 0],
    "y-": [0, -1, 0],
}

scale = 0.001  # mm → m    
points = {
                    name: tuple(coord * scale for coord in coords)
                    for name, coords in points.items()
                }  
    
from windcalc.windengine import BuildingWindEngine

class WindViewer(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wind Viewer")

        self.points = points
        self.polygons = polygons
        self.w_list = W_LIST
        self.building = None

        self.view = View3D()
        

        buttons = QHBoxLayout()
        for name in self.w_list:
            btn = QPushButton(name)
            btn.clicked.connect(lambda _, w=name: self.set_wind(w))
            buttons.addWidget(btn)

        btn_report = QPushButton("Report")
        btn_report.clicked.connect(self.get_report)
        buttons.addWidget(btn_report)

        layout = QVBoxLayout(self)
        layout.addLayout(buttons)
        layout.addWidget(self.view)

        self.view.set_data(points=self.points, polygons=self.polygons)
        self.view.data_changed.connect(lambda t, i, v: print(f"{t}:{i} -> {v}"))

    # ------------------------------------------------------------
    # Yardımcılar
    # ------------------------------------------------------------

    @staticmethod
    def _as_3d(vec) -> np.ndarray:
        """Herhangi bir vektörü 3D'ye tamamlar (z=0)."""
        v = np.asarray(vec, dtype=float).ravel()
        if v.size == 2:
            return np.array([v[0], v[1], 0.0])
        if v.size >= 3:
            return v[:3].copy()
        raise ValueError(f"Geçersiz yön vektörü: {vec}")

    @staticmethod
    def _print_summary(summary: Dict[str, Any]) -> None:
        """dict_tree olmadan okunabilir özet yazdırır."""
        import json
        print(json.dumps(summary, indent=2, ensure_ascii=False, default=str))

    # ------------------------------------------------------------
    # Ana akış
    # ------------------------------------------------------------
    def get_report(self):
        if self.building is None:
            print("Önce rüzgar yönü seçin.")
            return

        from windcalc.wind_report import get_report as _get_report

        # View'dan doğrudan PNG byte'ları al
        image_bytes = self.view.render_to_png_bytes(scale=2.0, transparent=False)

        _get_report(self.building, image_bytes=image_bytes)
        
    def set_wind(self, w: str):
        print(f"\n{'=' * 40}\nWIND: {w}\n{'=' * 40}")

        view_data = self.view.get_all_data()
        points = view_data["points"]
        polygons = view_data["polygons"]

        w_dir = self._as_3d(self.w_list[w])

        self.building = BuildingWindEngine(
            points=points,
            polygons=polygons,
            v_b0=28.0,
            terrain="Kategori III",
            w_dir=w_dir,
            scale_factor=1.0,
        )
        self._print_summary(self.building.get_summary())

        all_wind_zones = self.building.analysis_all_roof_wind(w_dir)

        

        # İki nokta: kullanıcı seçtiyse onlar, seçmediyse rüzgara dik varsayılan
        p1_sel = getattr(self, "p1_sel", np.array([-w_dir[1], w_dir[0], 0.0]))
        p2_sel = getattr(self, "p2_sel", np.array([0.0, 0.0, 0.0]))

        geom = self.building.calculate_obb_and_geometry(
            list(p1_sel), list(p2_sel), points
        )
        w_render_lines = (
            self.building.generate_render_lines(geom) if geom is not None else []
        )

        self.view.zones = all_wind_zones
        self.view.lines = w_render_lines
        self.view._visibility_states.clear()
        self.view.rebuild()
        self.view.update()

if __name__ == "__main__":
    
    app = QApplication(sys.argv)
    window = WindViewer()
    window.resize(1000, 700)
    window.show()
    sys.exit(app.exec())