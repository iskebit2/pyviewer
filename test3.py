from windcalc.windengine import BuildingWindEngine, SurfaceType
import numpy as np
from typing import List, Dict, Tuple, Optional, Union

# ---------- Geometri yardımcıları ----------

def close_polygon(polygon: np.ndarray, tol: float = 1e-8) -> np.ndarray:
    """Poligonu kapatır (ilk nokta = son nokta)."""
    polygon = np.asarray(polygon, dtype=float)
    if len(polygon) == 0:
        return polygon
    if not np.allclose(polygon[0], polygon[-1], atol=tol):
        polygon = np.vstack([polygon, polygon[0]])
    return polygon


def _open_polygon(polygon: np.ndarray, tol: float = 1e-8) -> np.ndarray:
    """Kapalı poligondan tekrar eden son noktayı kaldırır."""
    polygon = np.asarray(polygon, dtype=float)
    if len(polygon) > 1 and np.allclose(polygon[0], polygon[-1], atol=tol):
        return polygon[:-1]
    return polygon


def polygon_signed_area(polygon: np.ndarray) -> float:
    """Poligonun işaretli alanı (yön bilgisi için)."""
    pts = _open_polygon(polygon)
    if len(pts) < 3:
        return 0.0
    x, y = pts[:, 0], pts[:, 1]
    return 0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)


def polygon_edges(polygon: np.ndarray) -> List[Dict]:
    """Poligonun kenarlarını (p1, p2, index) listesi olarak döndürür."""
    pts = _open_polygon(polygon)
    n = len(pts)
    return [
        {"index": i, "p1": pts[i], "p2": pts[(i + 1) % n]}
        for i in range(n)
    ]


def polygon_edges_to_render(polygon):
    """Poligonun kenarlarını çizim/render için çiftler halinde döndürür."""
    if polygon is None:
        return []
    pts = np.asarray(polygon, dtype=float)
    if len(pts) == 0:
        return []

    # Ardışık tekrarları temizle
    cleaned = [pts[0]]
    for p in pts[1:]:
        if not np.allclose(cleaned[-1], p, atol=1e-8):
            cleaned.append(p)

    # İlk = son ise kaldır (kapalıysa)
    if len(cleaned) > 1 and np.allclose(cleaned[0], cleaned[-1], atol=1e-8):
        cleaned = cleaned[:-1]

    if len(cleaned) < 2:
        return []

    # Kapat
    pts = np.array(cleaned + [cleaned[0]])

    return [[pts[i], pts[i + 1]] for i in range(len(pts) - 1)]


def _clip_line_to_polygon_2d(line_p1, line_p2, polygon) -> Optional[Tuple[np.ndarray, np.ndarray]]:
    """Sonsuz 2D çizginin 2D poligon sınırıyla kesiştiği iki ucu bulur."""
    p1 = np.asarray(line_p1, dtype=float)
    p2 = np.asarray(line_p2, dtype=float)
    direction = p2 - p1
    if np.linalg.norm(direction) < 1e-8:
        return None

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

        if -1e-10 <= u <= 1 + 1e-10:
            intersections.append(p1 + t * direction)

    if len(intersections) < 2:
        return None

    intersections.sort(key=lambda p: np.dot(p - p1, direction))
    return intersections[0], intersections[-1]


def offset_edge_2d(polygon_2d, p1_2d, p2_2d, w_vector_2d, e, perp=False):
    """Kenarı 2D düzlemde w yönünde veya dik yönde offsetler."""
    p1 = np.asarray(p1_2d, dtype=float)
    p2 = np.asarray(p2_2d, dtype=float)
    edge_vec = p2 - p1
    edge_len = np.linalg.norm(edge_vec)
    if edge_len < 1e-8:
        return None
    edge_dir = edge_vec / edge_len

    if perp:
        perp_dir = np.array([-edge_dir[1], edge_dir[0]])
        d_L = e / 4
        EXT = e / 10
        split1 = p1 + edge_dir * d_L
        split2 = p2 - edge_dir * d_L
        return (
            (split1, split1 + perp_dir * EXT),
            (split2, split2 + perp_dir * EXT),
        )

    w_2d = np.asarray(w_vector_2d, dtype=float)
    w_len = np.linalg.norm(w_2d)
    if w_len < 1e-8:
        return None
    w_dir = w_2d / w_len

    d_L = e / 10
    line_L_p1 = p1 + w_dir * d_L
    line_L_p2 = p2 + w_dir * d_L

    return _clip_line_to_polygon_2d(line_L_p1, line_L_p2, polygon_2d)


# ---------- Poligon bölme ----------

# Sentinel: bölme başarısız olduğunda
SPLIT_FAIL = ([], [])


def _split_by_line_2d(poly_2d, p1, p2) -> Tuple[np.ndarray, np.ndarray]:
    """
    2D poligonu bir çizgi ile ikiye böler.
    Başarısız olursa ([], []) döner (her ikisi de boş array).
    """
    empty = (np.empty((0, 2)), np.empty((0, 2)))

    line_dir = p2 - p1
    if np.linalg.norm(line_dir) < 1e-8:
        return empty

    def side(p):
        return line_dir[0] * (p[1] - p1[1]) - line_dir[1] * (p[0] - p1[0])

    pts = _open_polygon(poly_2d)
    if len(pts) < 3:
        return empty

    pos, neg = [], []
    n = len(pts)

    for i in range(n):
        A, B = pts[i], pts[(i + 1) % n]
        sa, sb = side(A), side(B)

        if sa >= -1e-8:
            pos.append(A.copy())
        if sa <= 1e-8:
            neg.append(A.copy())

        if sa * sb < -1e-8:
            t = sa / (sa - sb)
            inter = A + t * (B - A)
            pos.append(inter)
            neg.append(inter)

    if len(pos) < 3 or len(neg) < 3:
        return empty

    pos = close_polygon(np.array(pos))
    neg = close_polygon(np.array(neg))

    def area(p):
        return 0.5 * abs(np.sum(p[:-1, 0] * p[1:, 1] - p[1:, 0] * p[:-1, 1]))

    a_pos, a_neg = area(pos), area(neg)
    if a_pos < 1e-4 or a_neg < 1e-4:
        return empty

    return pos, neg


def _is_empty(poly) -> bool:
    """Boş poligon kontrolü."""
    if poly is None:
        return True
    if isinstance(poly, tuple):
        return len(poly) == 0 or (isinstance(poly, tuple) and all(_is_empty(p) for p in poly))
    if isinstance(poly, list):
        return len(poly) == 0
    arr = np.asarray(poly)
    return arr.size == 0 or len(arr) < 3


# ---------- Debug yardımcıları ----------

def dict_tree(data, indent=""):
    lines = []
    items = list(data.items())
    for i, (key, value) in enumerate(items):
        last = i == len(items) - 1
        branch = "└── " if last else "├── "
        if isinstance(value, dict):
            lines.append(f"{indent}{branch}{key}")
            new_indent = indent + ("    " if last else "│   ")
            lines.append(dict_tree(value, new_indent))
        else:
            lines.append(f"{indent}{branch}{key} : {value}")
    return "\n".join(lines)


# ---------- Same-axis kenarları ----------

def get_same_axis_edge(edges_: dict, leading_edges: list) -> dict:
    """
    Leading kenarların same_axis listesinden, kendisiyle aynı olmayan
    (surface, surface_edge) çiftlerini çıkarır.
    """
    result = {}
    for ke1_ in leading_edges:
        ed1_ = edges_.get(ke1_)
        if ed1_ is None or not getattr(ed1_, "same_axis", None):
            continue

        temp_same = []
        for item in ed1_.same_axis:
            # item dict olabilir ya da obje; güvenli erişim
            if isinstance(item, dict):
                same_edge = item.get("same_edge", False)
                surface = item.get("surface", False)
                surface_edge = item.get("surface_edge", False)
            else:
                same_edge = getattr(item, "same_edge", False)
                surface = getattr(item, "surface", False)
                surface_edge = getattr(item, "surface_edge", False)

            if not same_edge:
                temp_same.append([surface, surface_edge])

        if temp_same:
            result[ke1_] = temp_same

    return result

from typing import List, Dict, Optional
import numpy as np


def _is_empty_poly(poly) -> bool:
    """Boş/geçersiz poligon kontrolü."""
    if poly is None:
        return True
    arr = np.asarray(poly) if not isinstance(poly, np.ndarray) else poly
    return arr.size == 0 or len(arr) < 3


def _add_region(regions, zone_name, poly):
    """Boş olmayan poligonu regions listesine ekler."""
    if not _is_empty_poly(poly):
        regions.append({'zone': zone_name, 'poly': np.asarray(poly, dtype=float)})


def _pick_low_eave_side(edge, w_vector, plane_normal):
    """
    Monopitch'te Fl (alçak saçak) ve Fu (yüksek saçak) ayrımı.
    Çatının eğim yönüne göre edge'in hangi taraf olduğunu belirler.
    """
    # Basit yaklaşım: edge'in ortalama z'si, çatının ortalama z'sinden düşükse Fl
    edge_z = (edge.p1[2] + edge.p2[2]) / 2.0
    return edge_z  # Küçük olan Fl, büyük olan Fu


def process_surface_zones(plane1, w_vector, e, same_axis, building):
    """
    Eurocode 1 / TS EN 1991-1-4 Çatı Rüzgar Yüzey Alanı Bölümleme Mantığı
    
    Dönüş: [{'zone': 'F', 'poly': np.ndarray}, ...]
    """
    wind_rel = plane1.wind_relation.value
    any_shared_ = plane1.properties.get("any_shared", False)

    pts_2d = plane1.pts_2d
    edges = plane1.edges

    exposed_edges = [k for k, ed in edges.items() if ed.exposed]
    leading_edges = [k for k, ed in edges.items() if ed.leading]

    regions = []

    # Yardımcı: 2D offset (offset_edge_2d zaten e/10 uygular, o yüzden base_e ver)
    def off(edge_idx, scale, polygon=pts_2d, perp=False):
        ed = edges[edge_idx]
        return offset_edge_2d(
            polygon, ed.p1[:2], ed.p2[:2], w_vector[:2],
            e, perp=perp
        )

    # =========================================================================
    # 1. WINDWARD
    # =========================================================================
    if wind_rel == "WINDWARD":
        # Tablo 0: FGH — leading edge'den e/10 offset → FG şeridi
        # FG şeridi, iki uçtan e/4 offset ile F1 | G | F2 olarak bölünür
        # Kalan → H
        for idx in leading_edges:
            # İlk bölme: e/10 offset → FG vs H
            res_fg = off(idx, 0.10, polygon=pts_2d)
            if res_fg is None:
                continue
            pos_H, neg_FG = _split_by_line_2d(pts_2d, res_fg[0], res_fg[1])
            if _is_empty_poly(pos_H) or _is_empty_poly(neg_FG):
                continue

            _add_region(regions, 'H', pos_H)

            # İkinci bölme: iki uçtan dik çizgi → F1 | G | F2
            # Not: offset_edge_2d'deki perp modu e/4 ve e/10 sabitlerini kullanır
            res_perp = off(idx, 1.0, polygon=pts_2d, perp=True)
            if res_perp is None:
                _add_region(regions, 'FG', neg_FG)
                continue

            (perp1_a, perp1_b), (perp2_a, perp2_b) = res_perp

            pos_F1, neg_GF = _split_by_line_2d(neg_FG, perp1_a, perp1_b)
            if _is_empty_poly(pos_F1) or _is_empty_poly(neg_GF):
                _add_region(regions, 'FG', neg_FG)
                continue

            pos_F2, neg_G = _split_by_line_2d(neg_GF, perp2_a, perp2_b)
            if _is_empty_poly(pos_F2):
                _add_region(regions, 'FG', neg_GF)
                _add_region(regions, 'F1', pos_F1)
                continue

            _add_region(regions, 'F', pos_F1)
            _add_region(regions, 'F', pos_F2)
            _add_region(regions, 'G', neg_G)

    # =========================================================================
    # 2. LEEWARD
    # =========================================================================
    elif wind_rel == "LEEWARD":
        if not any_shared_:
            # MONOPITCH (Tablo 180): Fl, Fu, H
            # Leading edge'lerden e/10 offset → Fl/Fu (kot'a göre) + H
            if not leading_edges:
                leading_edges = exposed_edges

            # Fl ve Fu'yu kot farkına göre ayır
            edge_z_values = []
            for idx in leading_edges:
                ed = edges[idx]
                edge_z_values.append((idx, (ed.p1[2] + ed.p2[2]) / 2.0))

            if len(edge_z_values) >= 2:
                edge_z_values.sort(key=lambda x: x[1])
                low_idx = edge_z_values[0][0]
                high_idx = edge_z_values[-1][0]
                zone_map = {low_idx: 'Fl', high_idx: 'Fu'}
            else:
                zone_map = {leading_edges[0]: 'F'}

            remaining = pts_2d
            for idx in leading_edges:
                res = off(idx, 0.10, polygon=remaining)
                if res is None:
                    continue
                pos_H, neg_F = _split_by_line_2d(remaining, res[0], res[1])
                if _is_empty_poly(pos_H) or _is_empty_poly(neg_F):
                    continue
                _add_region(regions, zone_map.get(idx, 'F'), neg_F)
                remaining = pos_H

            _add_region(regions, 'H', remaining)

        else:
            # DUOPITCH / HIPPED (Tablo 0): K (leading), J (exposed), I (kalan)
            remaining = pts_2d

            for idx in leading_edges:
                res = off(idx, 0.10, polygon=remaining)
                if res is None:
                    continue
                pos_rem, neg_K = _split_by_line_2d(remaining, res[0], res[1])
                if _is_empty_poly(pos_rem) or _is_empty_poly(neg_K):
                    continue
                _add_region(regions, 'K', neg_K)
                remaining = pos_rem

            for idx in exposed_edges:
                if idx in leading_edges:
                    continue
                res = off(idx, 0.10, polygon=remaining)
                if res is None:
                    continue
                pos_rem, neg_J = _split_by_line_2d(remaining, res[0], res[1])
                if _is_empty_poly(pos_rem) or _is_empty_poly(neg_J):
                    continue
                _add_region(regions, 'J', neg_J)
                remaining = pos_rem

            _add_region(regions, 'I', remaining)

    # =========================================================================
    # 3. PARALLEL
    # =========================================================================
    elif wind_rel == "PARALLEL":
        if not any_shared_:
            # MONOPITCH (Tablo 90): FG (e/10), H (e/2), I (kalan)
            for idx in leading_edges:
                res_fg = off(idx, 0.10)
                res_h = off(idx, 0.50)
                if res_fg is None or res_h is None:
                    continue

                pos_rem, neg_FG = _split_by_line_2d(pts_2d, res_fg[0], res_fg[1])
                if _is_empty_poly(pos_rem) or _is_empty_poly(neg_FG):
                    continue
                _add_region(regions, 'FG', neg_FG)

                pos_I, neg_H = _split_by_line_2d(pos_rem, res_h[0], res_h[1])
                if not _is_empty_poly(neg_H):
                    _add_region(regions, 'H', neg_H)
                if not _is_empty_poly(pos_I):
                    _add_region(regions, 'I', pos_I)

        elif any_shared_ and not same_axis:
            # HIPPED (Tablo 0): L (e/10), M (e/2), N (kalan)
            for idx in leading_edges:
                res_l = off(idx, 0.10)
                res_m = off(idx, 0.50)
                if res_l is None or res_m is None:
                    continue

                pos_rem, neg_L = _split_by_line_2d(pts_2d, res_l[0], res_l[1])
                if _is_empty_poly(pos_rem) or _is_empty_poly(neg_L):
                    continue
                _add_region(regions, 'L', neg_L)

                pos_N, neg_M = _split_by_line_2d(pos_rem, res_m[0], res_m[1])
                if not _is_empty_poly(neg_M):
                    _add_region(regions, 'M', neg_M)
                if not _is_empty_poly(pos_N):
                    _add_region(regions, 'N', pos_N)

        elif any_shared_ and same_axis:
            # DUOPITCH (Tablo 90): FG (e/10), F (e/4), G, H (e/2), I
            for idx in leading_edges:
                res_fg = off(idx, 0.10)
                res_f = off(idx, 0.25)   # e/4
                res_h = off(idx, 0.50)   # e/2
                if res_fg is None or res_h is None:
                    continue

                pos_rem, neg_FG = _split_by_line_2d(pts_2d, res_fg[0], res_fg[1])
                if _is_empty_poly(pos_rem) or _is_empty_poly(neg_FG):
                    continue

                # F ve G ayrımı (e/4 sınırı)
                if res_f is not None:
                    pos_G, neg_F = _split_by_line_2d(neg_FG, res_f[0], res_f[1])
                    if not _is_empty_poly(neg_F):
                        _add_region(regions, 'F', neg_F)
                    if not _is_empty_poly(pos_G):
                        _add_region(regions, 'G', pos_G)
                else:
                    _add_region(regions, 'FG', neg_FG)

                # H ve I ayrımı (e/2 sınırı)
                pos_I, neg_H = _split_by_line_2d(pos_rem, res_h[0], res_h[1])
                if not _is_empty_poly(neg_H):
                    _add_region(regions, 'H', neg_H)
                if not _is_empty_poly(pos_I):
                    _add_region(regions, 'I', pos_I)

    return regions
# ---------- Ana yüzey işleme ----------

def get_surface_results(plane_name, w, all_surfaces_w, w_list, building):
    plane1 = all_surfaces_w[w][plane_name]
    if plane1.surface_type == SurfaceType.WALL:
        return []

    leading_edges = [k for k, ed in plane1.edges.items() if ed.leading]
    same_axis = get_same_axis_edge(plane1.edges, leading_edges)

    regions = process_surface_zones(
        plane1, w_list[w], building.e, same_axis, building
    )

    render_lines = []
    for region in regions:
        poly_3d = plane1._unproject_to_3d(region['poly'])
        edges_3d = polygon_edges_to_render(poly_3d)
        render_lines.append({
            'zone': region['zone'],
            'edges': edges_3d,
        })
    return render_lines

if __name__ == "__main__":
    points = {
        "P1": (0.0, 0.0, 0.0),
        "P2": (12.0, 0.0, 0.0),
        "P3": (12.0, 9.0, 0.0),
        "P4": (0.0, 9.0, 0.0),
        "P5": (0.0, 0.0, 4.0),
        "P6": (12.0, 0.0, 4.0),
        "P7": (12.0, 9.0, 4.0),
        "P8": (0.0, 9.0, 4.0),
        "P9": (3.0, 4.0, 5.0),
        "P10": (12.0, 4.0, 5.0),
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

    building = BuildingWindEngine(points=points, polygons=polygons, scale_factor=1)

    print("\nbuilding analysis:\n")
    wind_parameters = building.get_summary()
    print("\nwind_parameters:\n", dict_tree(wind_parameters))

    w_list = {"x+": [1, 0, 0], "y+": [0, 1, 0], "x-": [-1, 0, 0], "y-": [0, -1, 0]}

    all_surfaces_w = {}
    for w in w_list:
        all_surfaces_w[w] = building.analysis_all_roof_wind(w_list[w])

    render_lines = []
    w = "x+"

    for plane_name in polygons:
        plane1 = all_surfaces_w[w][plane_name]
        # print(plane1.wind_relation)
        # for kk in ['name', 'surface_type', 'polygon', 'angle', 'pitch',
        #            'wind_vector', 'polygon_direction_xy', 'wind_relation',
        #            'global_leading', 'any_shared']:
        #     print(f" > {kk:20}: {plane1.properties.get(kk, '')}")

        render_lines1 = get_surface_results(plane_name, w, all_surfaces_w, w_list, building)
        render_lines2= [xyz["edges"] for xyz in render_lines1]
        print("render_lines1:", render_lines2)
        if render_lines1:
            render_lines.extend(render_lines2)

    from canvas3d import View3D

    import sys
    from PySide6.QtWidgets import QApplication

    def get_app():
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app


    app = get_app()

    view = View3D()
    view.set_data(
        points=points,
        polygons=polygons,
        lines=render_lines
    )

    view.resize(1000, 700)
    view.show()

    sys.exit(app.exec())