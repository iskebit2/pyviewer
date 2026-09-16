import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton


import numpy as np
from typing import List, Dict, Tuple, Optional
from windcalc.windengine import BuildingWindEngine, SurfaceType, dict_tree
from windcalc.zone import Zone
from canvas3d import View3D


# ================================================================
# GEOMETRİK YARDIMCILAR
# ================================================================

TOL = 1e-8
EPS = 1e-9


def close_polygon(polygon: np.ndarray, tol: float = TOL) -> np.ndarray:
    """Poligonu kapatır (ilk nokta = son nokta)."""
    polygon = np.asarray(polygon, dtype=float)
    if len(polygon) == 0:
        return polygon
    if not np.allclose(polygon[0], polygon[-1], atol=tol):
        polygon = np.vstack([polygon, polygon[0]])
    return polygon


def _open_polygon(polygon: np.ndarray, tol: float = TOL) -> np.ndarray:
    """Kapalı poligondan tekrar eden son noktayı kaldırır."""
    polygon = np.asarray(polygon, dtype=float)
    if len(polygon) > 1 and np.allclose(polygon[0], polygon[-1], atol=tol):
        return polygon[:-1]
    return polygon


def _area2(poly: np.ndarray) -> float:
    """İki katlı alan (işaretli)."""
    return float(np.sum(
        poly[:, 0] * np.roll(poly[:, 1], -1)
        - poly[:, 1] * np.roll(poly[:, 0], -1)
    ))


def _clean_vertices(pts: np.ndarray, tol: float = EPS) -> np.ndarray:
    """Ardışık mükerrer noktaları ve kapanış tekrarını temizler."""
    if len(pts) == 0:
        return pts
    cleaned = [pts[0]]
    for p in pts[1:]:
        if np.linalg.norm(p - cleaned[-1]) > tol:
            cleaned.append(p)
    if len(cleaned) > 1 and np.linalg.norm(cleaned[0] - cleaned[-1]) <= tol:
        cleaned.pop()
    return np.asarray(cleaned)


# ================================================================
# 2D BÖLME / KIRPMA
# ================================================================

def _split_by_line_2d(pts_2d, p1, p2, tol: float = EPS):
    """Poligonu p1->p2 doğrusu boyunca ikiye böler (Sutherland-Hodgman)."""
    poly = np.asarray(pts_2d, dtype=float)
    p1 = np.asarray(p1, dtype=float)
    p2 = np.asarray(p2, dtype=float)

    if len(poly) < 3:
        return np.empty((0, 2)), np.empty((0, 2))

    line = p2 - p1
    if np.linalg.norm(line) <= tol:
        raise ValueError("p1 ve p2 aynı nokta olamaz.")

    area2 = _area2(poly)
    if abs(area2) <= tol:
        raise ValueError("Poligon alanı sıfıra çok yakın.")
    ccw = area2 > 0

    # p1->p2 doğrusuna göre işaretli uzaklık
    def side(pt):
        v = pt - p1
        return line[0] * v[1] - line[1] * v[0]

    def clip(keep_left: bool) -> np.ndarray:
        result = []
        s = poly[-1]

        for e in poly:
            s_s = side(s)
            e_s = side(e)
            s_in = (s_s >= -tol) if keep_left else (s_s <= tol)
            e_in = (e_s >= -tol) if keep_left else (e_s <= tol)

            if e_in:
                if not s_in:
                    denom = s_s - e_s
                    t = s_s / denom if abs(denom) > tol else 0.0
                    result.append(s + t * (e - s))
                result.append(e.copy())
            elif s_in:
                denom = s_s - e_s
                t = s_s / denom if abs(denom) > tol else 0.0
                result.append(s + t * (e - s))

            s = e

        if not result:
            return np.empty((0, 2))

        cleaned = _clean_vertices(np.asarray(result), tol)
        if len(cleaned) < 3:
            return np.empty((0, 2))
        return cleaned

    left = clip(True)
    right = clip(False)

    def fix_orientation(p: np.ndarray) -> np.ndarray:
        if len(p) < 3:
            return p
        if (_area2(p) > 0) != ccw:
            return p[::-1].copy()
        return p

    return fix_orientation(left), fix_orientation(right)


def _clip_line_to_polygon_2d(line_p1, line_p2, polygon):
    """Sonsuz 2D çizginin poligon sınırıyla iki kesişimini döner."""
    p1 = np.asarray(line_p1, dtype=float)
    p2 = np.asarray(line_p2, dtype=float)
    direction = p2 - p1
    norm = np.linalg.norm(direction)
    if norm < TOL:
        return None
    direction /= norm

    pts = _open_polygon(polygon)
    n = len(pts)
    intersections = []

    for i in range(n):
        a = pts[i]
        b = pts[(i + 1) % n]
        edge = b - a

        cross = direction[0] * edge[1] - direction[1] * edge[0]
        if abs(cross) < 1e-10:
            continue

        q = a - p1
        t = (q[0] * edge[1] - q[1] * edge[0]) / cross
        u = (q[0] * direction[1] - q[1] * direction[0]) / cross

        if -TOL <= u <= 1 + TOL:
            pt = p1 + t * direction
            if not any(np.linalg.norm(pt - prev) < 1e-6 for prev in intersections):
                intersections.append(pt)

    if len(intersections) < 2:
        return None

    intersections.sort(key=lambda p: np.dot(p - p1, direction))
    return intersections[0], intersections[-1]


# ================================================================
# OFFSET / KENAR YARDIMCILARI
# ================================================================

def offset_edge_2d(polygon_2d, p1_2d, p2_2d, w_vector_2d, d_L):
    """Kenarı w yönünde offsetler."""
    p1 = np.asarray(p1_2d, dtype=float)
    p2 = np.asarray(p2_2d, dtype=float)
    w_2d = np.asarray(w_vector_2d, dtype=float)
    w_len = np.linalg.norm(w_2d)
    if w_len < TOL:
        return None
    offset = (w_2d / w_len) * d_L
    return _clip_line_to_polygon_2d(p1 + offset, p2 + offset, polygon_2d)


def create_edge_perp_2d(polygon_2d, p1_2d, p2_2d, w_vector_2d, d_L):
    """Kenara dik iki yardımcı çizgi üretir."""
    p1 = np.asarray(p1_2d, dtype=float)
    p2 = np.asarray(p2_2d, dtype=float)
    edge_vec = p2 - p1
    edge_len = np.linalg.norm(edge_vec)
    if edge_len < TOL:
        return None
    edge_dir = edge_vec / edge_len
    perp_dir = np.array([-edge_dir[1], edge_dir[0]])
    EXT = d_L * 2

    line_L_p1 = p1 + edge_dir * d_L
    line_R_p1 = p2 - edge_dir * d_L

    result_L = _clip_line_to_polygon_2d(line_L_p1, line_L_p1 + perp_dir * EXT, polygon_2d)
    result_R = _clip_line_to_polygon_2d(line_R_p1, line_R_p1 + perp_dir * EXT, polygon_2d)

    if result_L is None and result_R is None:
        return None
    return result_L, result_R


# ================================================================
# 3D <-> 2D
# ================================================================

def _unproject_local_2d_to_3d(pts_2d, local_sys):
    pts_2d = np.asarray(pts_2d, dtype=float)
    origin = local_sys["origin_3d"]
    u_dir = local_sys["u_dir"]
    v_dir = local_sys["v_dir"]
    return origin + pts_2d[:, 0:1] * u_dir + pts_2d[:, 1:2] * v_dir


def valid_polygon(poly) -> bool:
    return poly is not None and len(poly) >= 3


def split(poly, p1, p2):
    if not valid_polygon(poly):
        return None, None
    left, right = _split_by_line_2d(poly, p1, p2)
    return (
        left if valid_polygon(left) else None,
        right if valid_polygon(right) else None,
    )


def to_3d(poly, local_sys):
    if not valid_polygon(poly):
        return None
    return _unproject_local_2d_to_3d(poly, local_sys)


# ================================================================
# ANA BÖLGE ÜRETİCİ
# ================================================================

def create_region_KJI_poly(plane1, e, debug: bool = False):
    edges = plane1.edges
    pts_2d = np.asarray(plane1.pts_2d, dtype=float)
    is_ccw = plane1.is_ccw

    exposed_edges = [k for k, ed in edges.items() if ed.exposed]
    leading_edges = [k for k, ed in edges.items() if ed.leading]
    target_edges = leading_edges + [k for k in exposed_edges if k not in leading_edges]

    wind_3d = np.asarray(plane1.properties["wind_vector"], dtype=float)
    u_dir = np.asarray(plane1.proj_info["u_dir"], dtype=float)
    v_dir = np.asarray(plane1.proj_info["v_dir"], dtype=float)

    # w_plane TEK SEFER hesaplanır
    w_plane = np.array([np.dot(wind_3d, u_dir), np.dot(wind_3d, v_dir)])
    w_plane /= np.linalg.norm(w_plane)

    regions_2d: List[np.ndarray] = []
    remain_ = pts_2d.copy()

    if debug:
        print(f"\n[create_region] {plane1.polygon_name} | rel={plane1.wind_relation.value}")
        print(f"  leading={leading_edges} exposed={exposed_edges} ccw={is_ccw}")

    # ---------------- İç fonksiyonlar ----------------

    def split_FG(poly_FG, edge):
        """WINDWARD kenar için ön/arka bölgeleri üretir."""
        result_L, result_R = create_edge_perp_2d(
            pts_2d, edge.p1_2d, edge.p2_2d, edge.wind_to_2d, e / 4.0
        ) or (None, None)

        if result_L is None or result_R is None:
            return

        left_p1, right_p1 = split(poly_FG, *result_L)
        if left_p1 is None or right_p1 is None:
            return

        left_p2, right_p2 = split(right_p1, *result_R)
        if left_p2 is None or right_p2 is None:
            return

        regions_2d.extend([left_p1, left_p2, right_p2])

    def split_MN(poly_M):
        """PARALLEL kenar için e/2 düzleminde bölme."""
        edge = edges[leading_edges[0]]
        p0e = np.asarray(edge.pos_front_pt, dtype=float) + w_plane * (e / 2.0)
        w_perp = np.array([-w_plane[1], w_plane[0]])
        L = 10.0 * max(np.ptp(pts_2d[:, 0]), np.ptp(pts_2d[:, 1]))

        cut = _clip_line_to_polygon_2d(p0e - w_perp * L, p0e + w_perp * L, remain_)
        if cut is not None:
            left_MN, right_MN = split(poly_M, *cut)
            regions_2d.extend([left_MN, right_MN])
        else:
            regions_2d.append(poly_M)

    # ---------------- Ana döngü ----------------

    for idx_ in target_edges:
        edge = edges[idx_]
        p1 = np.asarray(edge.p1_2d, dtype=float)
        p2 = np.asarray(edge.p2_2d, dtype=float)

        edge_vec = p2 - p1
        edge_len = np.linalg.norm(edge_vec)
        if edge_len < 1e-10:
            continue

        edge_dir = edge_vec / edge_len
        left_normal = np.array([-edge_dir[1], edge_dir[0]])
        inward = left_normal if is_ccw else -left_normal
        offset = inward * (e / 10.0)

        clipped = _clip_line_to_polygon_2d(p1 + offset, p2 + offset, remain_)
        if clipped is None:
            continue

        left, right = split(remain_, *clipped)
        if left is None or right is None:
            continue

        if plane1.wind_relation.value == "WINDWARD":
            split_FG(right, edge)
        else:
            regions_2d.append(right)

        remain_ = left

    # ---------------- Kalan bölge ----------------

    if plane1.wind_relation.value == "PARALLEL":
        split_MN(remain_)
    else:
        regions_2d.append(remain_)

    # ---------------- 3D'ye dön ----------------

    return [
        close_polygon(to_3d(r, plane1.proj_info))
        for r in regions_2d
        if valid_polygon(r)
    ]


# ================================================================
# TEST VERİLERİ
# ================================================================

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

ROOF_NAMES = ["C1", "C2", "C3"]


# ================================================================
# ARAYÜZ
# ================================================================

class WindViewer(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wind Viewer")

        self.view = View3D()

        buttons = QHBoxLayout()
        for name in W_LIST:
            btn = QPushButton(name)
            btn.clicked.connect(lambda _, w=name: self.set_wind(w))
            buttons.addWidget(btn)

        layout = QVBoxLayout(self)
        layout.addLayout(buttons)
        layout.addWidget(self.view)

        self.set_wind("y+")

    def set_wind(self, w: str):
        print(f"\n{'=' * 40}\nWIND: {w}\n{'=' * 40}")

        building = BuildingWindEngine(
            points=points,
            polygons=polygons,
            v_b0=28.0,
            terrain="Kategori III",
            w_dir=W_LIST[w],
            scale_factor=1000,
        )

        print("\nwind_parameters:\n", dict_tree(building.get_summary()))

        all_surfaces = building.analysis_all_roof_wind(W_LIST[w])
        render_lines = []
        for name in ROOF_NAMES:
            render_lines.extend(
                create_region_KJI_poly(all_surfaces[name], building.e)
            )

        self.view.set_data(points={"O": [0, 0, 0]}, lines=render_lines)
        self.view.update()


# ================================================================
# MAIN
# ================================================================

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WindViewer()
    window.resize(1000, 700)
    window.show()
    sys.exit(app.exec())