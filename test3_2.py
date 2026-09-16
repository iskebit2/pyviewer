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
        print("CLIP FAILURE")
        print("line_p1:", line_p1)
        print("line_p2:", line_p2)
        print("polygon:", polygon)
        print("intersections:", intersections)
        
        
        return None

    # Noktaları çizgi yönündeki hizasına göre sırala
    intersections.sort(key=lambda p: np.dot(p - p1, direction))
    return intersections[0], intersections[-1]


def offset_edge_2d(polygon_2d, p1_2d, p2_2d, w_vector_2d, d_L):
    """Kenarı 2D düzlemde w yönünde offsetler."""
    p1 = np.asarray(p1_2d, dtype=float)
    p2 = np.asarray(p2_2d, dtype=float)
    

    w_2d = np.asarray(w_vector_2d, dtype=float)
    w_len = np.linalg.norm(w_2d)
    if w_len < 1e-8:
        return None
    w_dir = w_2d / w_len
    
    offset = w_dir * d_L
    

    return _clip_line_to_polygon_2d(
        p1 + offset,
        p2 + offset,
        polygon_2d
    )
    
    
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
    regions_2d = []
    edges = plane1.edges

    exposed_edges = [
        k for k, ed in edges.items()
        if ed.exposed
    ]

    leading_edges = [
        k for k, ed in edges.items()
        if ed.leading
    ]

    pts_2d = np.asarray(plane1.pts_2d, dtype=float)

    
    is_ccw = plane1.is_ccw

    # ---------------------------------------------------------
    # İşlenecek tüm kenarlar
    # ---------------------------------------------------------
    target_edges = (
        leading_edges
        + [k for k in exposed_edges if k not in leading_edges]
    )

    remain_ = pts_2d.copy()
    
    print("\nplane1.polygon_name:", plane1.polygon_name)
    print("plane1.wind_relation.value:", plane1.wind_relation.value)
    print("plane1.pts_3d:", plane1.pts_3d)
    print("plane1.proj_info:", plane1.proj_info)
    print("plane1.pts_2d:", plane1.pts_2d)
    print("polygon is_ccw:", is_ccw)
    print("leading_edges:", leading_edges)
    print("exposed_edges:", exposed_edges)
    print()

    wind_3d = np.asarray(
    plane1.properties["wind_vector"],
    dtype=float
)

    u_dir = np.asarray(
        plane1.proj_info["u_dir"],
        dtype=float
    )

    v_dir = np.asarray(
        plane1.proj_info["v_dir"],
        dtype=float
    )

    w_plane = np.array([
        np.dot(wind_3d, u_dir),
        np.dot(wind_3d, v_dir),
    ])

    w_plane /= np.linalg.norm(w_plane)

    def split_FG(poly_FG, edge):
        print("split_FG.....")
        print(edge.log)
        w_vector_2d= edge.wind_to_2d
        offset_fg1 = create_edge_perp_2d(
        pts_2d,
        edge.p1_2d,
        edge.p2_2d,
        w_vector_2d,
        e / 4.0,
    )
    
    
        if offset_fg1 is None:
            
            return []
            
        (result_L, result_R) = offset_fg1
        cut_p1, cut_p2 = result_L

        left_p1, right_p1 = split(poly_FG, cut_p1, cut_p2)

        if left_p1 is None or right_p1 is None:
            return []

        cut_p1, cut_p2 = result_R

        left_p2, right_p2 = split(right_p1, cut_p1, cut_p2)
        

        if left_p2 is None or right_p2 is None:
            return []

        regions_2d.append(left_p1)
        regions_2d.append(left_p2)
        regions_2d.append(right_p2)
        
    def split_MN(poly_M):
        idxx_= leading_edges[0]
        edge= edges[idxx_]
        
        w_plane = np.array([
            np.dot(wind_3d, u_dir),
            np.dot(wind_3d, v_dir),
        ])
        w_plane /= np.linalg.norm(w_plane)

        p0e = (
            np.asarray(edge.pos_front_pt, dtype=float)
            + w_plane * (e / 2.0)
        )

        w_perp = np.array([
            -w_plane[1],
             w_plane[0]
        ])

        L = 10.0 * max(
            np.ptp(pts_2d[:, 0]),
            np.ptp(pts_2d[:, 1])
        )

        cut = _clip_line_to_polygon_2d(
            p0e - w_perp * L,
            p0e + w_perp * L,
            remain_
        )
        print("\nsplit e/2...:")
        print("poly_M:", poly_M)
        print("edge:", edge)
        print("w_plane:", w_plane)
        print("w_perp:", w_perp)
        print("L:", L)
        print("cut:", cut)
        print()
        
        
        if cut is not None:
            cut_p1, cut_p2= cut
            left_MN, right_MN = split(poly_M, cut_p1, cut_p2)
            
            
            regions_2d.append(left_MN)
            regions_2d.append(right_MN)
        else:
            regions_2d.append(poly_M)
            
        
    # ---------------------------------------------------------
    # Her exposed / leading kenarı içeri offsetle
    # ---------------------------------------------------------
    for idx_ in target_edges:

        edge = edges[idx_]
        
        
        p1 = np.asarray(edge.p1_2d, dtype=float)
        p2 = np.asarray(edge.p2_2d, dtype=float)

        edge_vec = p2 - p1
        edge_len = np.linalg.norm(edge_vec)

        if edge_len < 1e-10:
            continue

        edge_dir = edge_vec / edge_len

        # CCW polygon:
        #   iç taraf = kenarın solu
        #
        # CW polygon:
        #   iç taraf = kenarın sağı
        left_normal = np.array([
            -edge_dir[1],
             edge_dir[0]
        ])

        if is_ccw:
            inward = left_normal
        else:
            inward = -left_normal

        offset_distance = e / 10.0
        offset = inward * offset_distance

        offset_p1 = p1 + offset
        offset_p2 = p2 + offset

        
            
            
            
        print(
            "REGION EDGE:",
            idx_,
            "p1 =", p1,
            "p2 =", p2,
            "inward =", inward,
            "offset =", offset
        )

        # -----------------------------------------------------
        # Offset doğrusu ile mevcut poligonu kes
        # -----------------------------------------------------
        clipped = _clip_line_to_polygon_2d(
            offset_p1,
            offset_p2,
            remain_
        )

        if clipped is None:
            print(
                "edge", idx_,
                "offset/clipping is None"
            )
            continue

        offset_p1, offset_p2 = clipped

        # -----------------------------------------------------
        # Poligonu offset doğrusu ile böl
        # -----------------------------------------------------
        left, right = split(
            remain_,
            offset_p1,
            offset_p2,
        )

        if left is None or right is None:
            print(
                "edge", idx_,
                "left/right is None"
            )
            continue
        if plane1.wind_relation.value == "WINDWARD":
            split_FG(right, edge)
        else:
            regions_2d.append(right)

        remain_ = left

        print(
            "edge", idx_,
            "region eklendi"
        )

    # ---------------------------------------------------------
    # Geriye kalan bölge
    # ---------------------------------------------------------
    if plane1.wind_relation.value == "PARALLEL":
        split_MN(remain_)
    else:
        regions_2d.append(remain_)

    print("remain_ eklendi")

    return [
        close_polygon(
            to_3d(region, plane1.proj_info)
        )
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
# "C4": ["P6", "P7", "P10"],
}

from windcalc.windengine import BuildingWindEngine, SurfaceType, dict_tree
from windcalc.zone import Zone

w_list = {"x+": [1, 0, 0], "y+": [0, 1, 0], "x-": [-1, 0, 0], "y-": [0, -1, 0]}
w= "y+"

# building = BuildingWindEngine(points=points,
                              # polygons=polygons,
                              # v_b0= 28.0,
                              # terrain="Kategori III",
                              # w_dir= w_list[w],
                              # scale_factor=1000)

# wind_parameters = building.get_summary()
# print("\nwind_parameters:\n", dict_tree(wind_parameters))


# render_lines= []
# for p_name in ['C1', 'C2','C3']:
    # all_surfaces= building.analysis_all_roof_wind(w_list[w])

    # plane1= all_surfaces[p_name]

    # # for kk in ['name', 'surface_type', 'polygon', 'angle', 'pitch',
               # # 'wind_vector', 'polygon_direction_xy', 'wind_relation',
               # # 'global_leading', 'any_shared']:
        # # print(f" > {kk:20}: {plane1.properties.get(kk, '')}")

    # # edges= plane1.edges

    # # exposed_edges = [k for k, ed in edges.items() if ed.exposed]
    # # leading_edges = [k for k, ed in edges.items() if ed.leading]
    # # print("leading_edges:", leading_edges)
    # # print("exposed_edges:", exposed_edges)

    # # w_vector_2d= w_list[w][:2]

    # # pts_2d = plane1.pts_2d
    # # print("w_vector_2d:", w_vector_2d)
    # # # print("local_sys:", local_sys)
    # # print("pts_2d:", pts_2d)

    # render_lines1= create_region_KJI_poly(plane1, building.e)
    
    # render_lines.extend(render_lines1)

from canvas3d import View3D

# import sys
# from PySide6.QtWidgets import QApplication

# app = QApplication(sys.argv)







# view = View3D()
# view.set_data(points= {"O": [0,0,0]}, lines= render_lines)

# view.resize(1000, 700)
# view.show()
# # view.zoom_extents()

# sys.exit(app.exec())

import sys
from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout, QPushButton





class WindViewer(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Wind Viewer")

        self.w = "y+"

        # ---------------------------------------------------------
        # 3D görünüm
        # ---------------------------------------------------------

        self.view = View3D()

        # ---------------------------------------------------------
        # Rüzgar butonları
        # ---------------------------------------------------------

        buttons = QHBoxLayout()

        for name in w_list:
            button = QPushButton(name)
            button.clicked.connect(
                lambda checked=False, w=name:
                    self.set_wind(w)
            )
            buttons.addWidget(button)

        # ---------------------------------------------------------
        # Layout
        # ---------------------------------------------------------

        layout = QVBoxLayout(self)

        layout.addLayout(buttons)
        layout.addWidget(self.view)

        self.setLayout(layout)

        # İlk görüntü
        self.set_wind(self.w)

    # -------------------------------------------------------------
    # WIND
    # -------------------------------------------------------------

    def set_wind(self, w):

        self.w = w

        print("\n==============================")
        print("WIND:", w)
        print("==============================")

        building = BuildingWindEngine(
            points=points,
            polygons=polygons,
            v_b0=28.0,
            terrain="Kategori III",
            w_dir=w_list[w],
            scale_factor=1000,
        )

        wind_parameters = building.get_summary()

        print(
            "\nwind_parameters:\n",
            dict_tree(wind_parameters)
        )

        render_lines = []

        all_surfaces = building.analysis_all_roof_wind(
            w_list[w]
        )

        for p_name in ["C1", "C2", "C3"]:

            plane1 = all_surfaces[p_name]

            render_lines1 = create_region_KJI_poly(
                plane1,
                building.e
            )

            render_lines.extend(render_lines1)

        # ---------------------------------------------------------
        # Görüntüyü yenile
        # ---------------------------------------------------------

        self.view.set_data(
            points={"O": [0, 0, 0]},
            lines=render_lines
        )

        self.view.update()


# ================================================================
# MAIN
# ================================================================

app = QApplication(sys.argv)

window = WindViewer()
window.resize(1000, 700)
window.show()

sys.exit(app.exec())