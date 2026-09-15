import numpy as np
from typing import List, Dict, Tuple, Optional, Union

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

def _split_by_line_2d(pts_2d, p1, p2, tol=1e-9):

    poly = np.asarray(pts_2d, dtype=float)
    p1 = np.asarray(p1, dtype=float)
    p2 = np.asarray(p2, dtype=float)

    if len(poly) < 3:
        return np.empty((0, 2)), np.empty((0, 2))

    line = p2 - p1

    if np.linalg.norm(line) <= tol:
        raise ValueError("p1 ve p2 aynı nokta olamaz.")

    # ------------------------------------------------------------
    # Poligon yönü
    # ------------------------------------------------------------

    area2 = np.sum(
        poly[:, 0] * np.roll(poly[:, 1], -1)
        - poly[:, 1] * np.roll(poly[:, 0], -1)
    )

    if abs(area2) <= tol:
        raise ValueError("Poligon alanı sıfıra çok yakın.")

    ccw = area2 > 0

    # ------------------------------------------------------------
    # p1 -> p2 doğrusuna göre işaret
    #
    # + : sol
    # - : sağ
    # ------------------------------------------------------------

    def side(point):
        v = point - p1
        return line[0] * v[1] - line[1] * v[0]

    # ------------------------------------------------------------
    # Sutherland-Hodgman
    # ------------------------------------------------------------

    def clip(keep_left):

        result = []

        def inside(point):
            s = side(point)

            if keep_left:
                return s >= -tol
            else:
                return s <= tol

        def intersection(a, b):

            da = side(a)
            db = side(b)

            denom = da - db

            if abs(denom) <= tol:
                return a.copy()

            t = da / denom

            return a + t * (b - a)

        s = poly[-1]

        for e in poly:

            s_inside = inside(s)
            e_inside = inside(e)

            if e_inside:

                if not s_inside:
                    result.append(intersection(s, e))

                result.append(e.copy())

            elif s_inside:

                result.append(intersection(s, e))

            s = e

        if not result:
            return np.empty((0, 2))

        result = np.asarray(result)

        # Ardışık aynı noktaları temizle
        cleaned = [result[0]]

        for point in result[1:]:
            if np.linalg.norm(point - cleaned[-1]) > tol:
                cleaned.append(point)

        # İlk = son ise kapalı poligonun tekrarını kaldır
        if (
            len(cleaned) > 1
            and np.linalg.norm(cleaned[0] - cleaned[-1]) <= tol
        ):
            cleaned.pop()

        result = np.asarray(cleaned)

        if len(result) < 3:
            return np.empty((0, 2))

        return result

    left = clip(True)
    right = clip(False)

    # ------------------------------------------------------------
    # Clipping vertex sırasını korur.
    # Yine de yönü garanti edelim.
    # ------------------------------------------------------------

    def area2(p):

        return np.sum(
            p[:, 0] * np.roll(p[:, 1], -1)
            - p[:, 1] * np.roll(p[:, 0], -1)
        )

    def fix_orientation(p):

        if len(p) < 3:
            return p

        if (area2(p) > 0) != ccw:
            return p[::-1].copy()

        return p

    left = fix_orientation(left)
    right = fix_orientation(right)

    return left, right

def _clip_line_to_polygon_2d(line_p1, line_p2, polygon) -> Optional[Tuple[np.ndarray, np.ndarray]]:
    """Sonsuz 2D çizginin (line_p1 -> line_p2) 2D poligon sınırıyla kesiştiği noktaları bulur."""
    p1 = np.asarray(line_p1, dtype=float)
    p2 = np.asarray(line_p2, dtype=float)
    direction = p2 - p1
    norm = np.linalg.norm(direction)
    if norm < 1e-8:
        return None
    
    direction = direction / norm  # Birim yön vektörü

    pts = _open_polygon(polygon)
    n = len(pts)
    intersections = []

    for i in range(n):
        a = pts[i]
        b = pts[(i + 1) % n]
        edge = b - a

        # Çapraz çarpım (2D cross product)
        cross = direction[0] * edge[1] - direction[1] * edge[0]
        if abs(cross) < 1e-10:
            continue  # Doğru ile poligon kenarı paralel

        q = a - p1
        
        # t: Sonsuz doğru üzerindeki parametre
        # u: Poligon kenarı (a->b) üzerindeki parametre [0, 1]
        t = (q[0] * edge[1] - q[1] * edge[0]) / cross
        u = (q[0] * direction[1] - q[1] * direction[0]) / cross

        # Kesişim noktası poligon kenarının (a -> b) ÜZERİNDE mi?
        if -1e-8 <= u <= 1 + 1e-8:
            pt = p1 + t * direction
            # Mükerrer kesişim noktalarını ekleme
            if not any(np.linalg.norm(pt - prev) < 1e-6 for prev in intersections):
                intersections.append(pt)

    if len(intersections) < 2:
        return None

    # Noktaları çizgi yönündeki hizasına göre sırala
    intersections.sort(key=lambda p: np.dot(p - p1, direction))
    return intersections[0], intersections[-1]


def offset_edge_2d(polygon_2d, p1_2d, p2_2d, w_vector_2d, d_L):
    """Kenarı 2D düzlemde w yönünde offsetler."""
    p1 = np.asarray(p1_2d, dtype=float)
    p2 = np.asarray(p2_2d, dtype=float)
    edge_vec = p2 - p1
    edge_len = np.linalg.norm(edge_vec)
    if edge_len < 1e-8:
        return None
    edge_dir = edge_vec / edge_len

    w_2d = np.asarray(w_vector_2d, dtype=float)
    w_len = np.linalg.norm(w_2d)
    if w_len < 1e-8:
        return None
    w_dir = w_2d / w_len

    for sign in [1.0, -1.0]:
        line_L_p1 = p1 + (sign * w_dir) * d_L
        line_L_p2 = p2 + (sign * w_dir) * d_L
        
        result = _clip_line_to_polygon_2d(
            line_L_p1,
            line_L_p2,
            polygon_2d
        )
        
        # Eğer bu yön poligonda geçerli bir kesişim hattı (2 nokta) üretiyorsa doğru yön budur
        if result is not None and len(result) == 2:
            return result

    return None
    
def create_edge_perp_2d(polygon_2d, p1_2d, p2_2d, w_vector_2d, d_L):
    """Kenarı 2D düzlemde w yönünde kenara dik yönde yeni çizgi oluşturur."""
    EXT = d_L*2
    p1 = np.asarray(p1_2d, dtype=float)
    p2 = np.asarray(p2_2d, dtype=float)
    edge_vec = p2 - p1
    edge_len = np.linalg.norm(edge_vec)
    if edge_len < 1e-8:
        return None
    edge_dir = edge_vec / edge_len
    perp_dir = np.array([-edge_dir[1], edge_dir[0]])
    
    line_L_p1 = p1 + edge_dir * d_L
    line_L_p2 = line_L_p1 + perp_dir * EXT

    line_R_p1 = p2 - edge_dir * d_L
    line_R_p2 = line_R_p1 + perp_dir * EXT
    
    result_L = _clip_line_to_polygon_2d(
        line_L_p1,
        line_L_p2,
        polygon_2d
    )
    result_R = _clip_line_to_polygon_2d(
        line_R_p1,
        line_R_p2,
        polygon_2d
    )

    if (result_L is None or len(result_L) != 2) and (result_R is None or len(result_R) != 2):
        return None
        
    return (result_L, result_R)

def _unproject_local_2d_to_3d(pts_2d, local_sys):

    pts_2d = np.asarray(pts_2d, dtype=float)

    origin = local_sys["origin_3d"]
    u_dir = local_sys["u_dir"]
    v_dir = local_sys["v_dir"]

    pts_3d = []

    for u, v in pts_2d:
        point = (
            origin
            + u * u_dir
            + v * v_dir
        )

        pts_3d.append(point)

    return np.asarray(pts_3d)
    
def valid_polygon(poly):
        return poly is not None and len(poly) >= 3
    
def split(poly, p1, p2):
    """
    Split işlemini güvenli şekilde yapar.
    """

    if not valid_polygon(poly):
        return None, None

    result = _split_by_line_2d(poly, p1, p2)

    if result is None or len(result) != 2:
        return None, None

    left, right = result

    if not valid_polygon(left):
        left = None

    if not valid_polygon(right):
        right = None

    return left, right

def to_3d(poly, local_sys):
    if not valid_polygon(poly):
        return None

    return _unproject_local_2d_to_3d(poly, local_sys)
    
def create_region_KJI_poly(plane1, e):
    regions_2d= []
    edges= plane1.edges

    exposed_edges = [k for k, ed in edges.items() if ed.exposed]
    leading_edges = [k for k, ed in edges.items() if ed.leading]
    pts_2d= plane1.pts_2d
    w_vector_3d= plane1.properties.get("wind_vector", [1,0,0])
    w_vector_2d= w_vector_3d[:2]
    remain_ = pts_2d.copy()
    
    # İşlenecek tüm kenar indekslerini birleştiriyoruz
    target_edges = leading_edges + [k for k in exposed_edges if k not in leading_edges]
    
    for idx_ in target_edges:
        edge= edges[idx_]
        p1_2d = edge.p1_2d
        p2_2d = edge.p2_2d

        offset = offset_edge_2d(
                                pts_2d,
                                p1_2d,
                                p2_2d,
                                w_vector_2d,
                                e / 10.0,
                            )
        if offset is None:
            print("leading_edges",idx_,"offset is None")
            print("p1_2d",p1_2d,"p2_2d",p2_2d, "pts_2d:",pts_2d)
            continue

        offset_p1, offset_p2 = offset
        left, right = split(
                            remain_,
                            offset_p1,
                            offset_p2,
                        )
        if left is None or right is None:
            print("leading_edges",idx_,"left is None or right is None")
            continue

        regions_2d.append(right)
        print("leading_edges",idx_,"left eklendi")
        remain_= left
        
        
    regions_2d.append(remain_)
    print("remain_ eklendi")

    return [
        close_polygon(to_3d(region, plane1.proj_info))
        for region in regions_2d
        if valid_polygon(region)
    ]
        

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

from windcalc.windengine import BuildingWindEngine, SurfaceType, dict_tree
from windcalc.zone import Zone

w_list = {"x+": [1, 0, 0], "y+": [0, 1, 0], "x-": [-1, 0, 0], "y-": [0, -1, 0]}
w= "x-"

building = BuildingWindEngine(points=points,
                              polygons=polygons,
                              v_b0= 28.0,
                              terrain="Kategori III",
                              w_dir= w_list[w],
                              scale_factor=1000)

wind_parameters = building.get_summary()
print("\nwind_parameters:\n", dict_tree(wind_parameters))


render_lines= []
for p_name in ['C1', 'C2','C3']:
    all_surfaces= building.analysis_all_roof_wind(w_list[w])

    plane1= all_surfaces[p_name]

    # for kk in ['name', 'surface_type', 'polygon', 'angle', 'pitch',
               # 'wind_vector', 'polygon_direction_xy', 'wind_relation',
               # 'global_leading', 'any_shared']:
        # print(f" > {kk:20}: {plane1.properties.get(kk, '')}")

    # edges= plane1.edges

    # exposed_edges = [k for k, ed in edges.items() if ed.exposed]
    # leading_edges = [k for k, ed in edges.items() if ed.leading]
    # print("leading_edges:", leading_edges)
    # print("exposed_edges:", exposed_edges)

    # w_vector_2d= w_list[w][:2]

    # pts_2d = plane1.pts_2d
    # print("w_vector_2d:", w_vector_2d)
    # # print("local_sys:", local_sys)
    # print("pts_2d:", pts_2d)

    render_lines1= create_region_KJI_poly(plane1, building.e)
    
    render_lines.extend(render_lines1)

from canvas3d import View3D

import sys
from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)







view = View3D()
view.set_data(points= {"O": [0,0,0]}, lines= render_lines)

view.resize(1000, 700)
view.show()
# view.zoom_extents()

sys.exit(app.exec())