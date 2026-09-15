import numpy as np
from typing import List, Dict, Tuple, Optional, Union

def _split_by_line_2d(poly_2d, p1, p2, tol=1e-9):

    poly = np.asarray(poly_2d, dtype=float)
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
    
def _make_local_sys(poly_coords, tol=1e-9):
    """
    Düzlemsel 3D bir poligon için sağ elli yerel koordinat sistemi oluşturur.

    Returns
    -------
    dict
        {
            "origin_3d": ...,
            "u_dir": ...,
            "v_dir": ...,
            "normal": ...
        }

    Koordinat sistemi:
        u_dir : poligon düzlemindeki ilk eksen
        v_dir : poligon düzlemindeki ikinci eksen
        normal: u_dir x v_dir
    """

    poly = np.asarray(poly_coords, dtype=float)

    if poly.ndim != 2 or poly.shape[1] != 3:
        raise ValueError("poly_coords (n, 3) şeklinde olmalıdır.")

    if len(poly) < 3:
        raise ValueError("En az üç nokta gerekli.")

    origin = poly[0]

    # ------------------------------------------------------------
    # 1. İlk anlamlı kenarı bul -> u_dir adayı
    # ------------------------------------------------------------

    u_dir = None

    for i in range(1, len(poly)):
        v = poly[i] - origin
        length = np.linalg.norm(v)

        if length > tol:
            u_dir = v / length
            break

    if u_dir is None:
        raise ValueError("Poligon dejenere: bütün noktalar aynı.")

    # ------------------------------------------------------------
    # 2. u_dir'e paralel olmayan bir vektör bul
    #    ve normal'i oluştur
    # ------------------------------------------------------------

    normal = None

    for i in range(1, len(poly)):
        v = poly[i] - origin

        cross = np.cross(u_dir, v)
        cross_len = np.linalg.norm(cross)

        if cross_len > tol:
            normal = cross / cross_len
            break

    if normal is None:
        raise ValueError(
            "Poligon dejenere: bütün noktalar aynı doğru üzerinde."
        )

    # ------------------------------------------------------------
    # 3. Gerçek v_dir'i normal ve u_dir'den üret
    #
    # u x v = normal olacak şekilde
    # ------------------------------------------------------------

    v_dir = np.cross(normal, u_dir)
    v_dir /= np.linalg.norm(v_dir)

    return {
        "origin_3d": origin.copy(),
        "u_dir": u_dir,
        "v_dir": v_dir,
        "normal": normal,
    }

def _project_3d_to_local_2d(poly_coords, local_sys):

    poly = np.asarray(poly_coords, dtype=float)

    origin = local_sys["origin_3d"]
    u_dir = local_sys["u_dir"]
    v_dir = local_sys["v_dir"]

    pts_2d = []

    for pt in poly:
        vec = pt - origin

        u = np.dot(vec, u_dir)
        v = np.dot(vec, v_dir)

        pts_2d.append([u, v])

    return np.asarray(pts_2d)

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

def polygon_edges(polygon: np.ndarray) -> List[Dict]:
    """Poligonun kenarlarını (p1, p2, index) listesi olarak döndürür."""
    pts = _open_polygon(polygon)
    n = len(pts)
    result_= {}
    for i in range(n):
        result_[i] = {"p1": pts[i], "p2": pts[(i + 1) % n]}
        
    return result_
    
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

    line_L_p1 = p1 + w_dir * d_L
    line_L_p2 = p2 + w_dir * d_L
    
    result = _clip_line_to_polygon_2d(
        line_L_p1,
        line_L_p2,
        polygon_2d
    )

    if result is None or len(result) != 2:
        return None

    return result
    
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

def get_polygon_coords(polygon_points, points, scale_=1000.0):
    """Poligon noktalarını koordinatlara dönüştürür ve ölçekler."""
    coords = []
    for pt_name in polygon_points:
        if pt_name not in points:
            raise ValueError(f"Nokta '{pt_name}' bulunamadı!")
        pt = points[pt_name]
        coords.append([pt[0] / scale_, pt[1] / scale_, pt[2] / scale_])
    return np.array(coords)


        
def create_region_FGH_poly(poly_3d, e=12.0, w_vector_2d=(-1.0, 0.0), idx_=0):
    """
    Poligon üzerinde F/G/H bölgelerini oluşturur.

    İşlem:
        1. 3D poligonu yerel 2D sisteme taşır.
        2. Seçilen kenardan e/10 offset alarak ilk bölgeyi ayırır.
        3. Kalan bölgeden iki uçta e/4 mesafede dik kesimler yapar.
        4. Oluşan bölgeleri tekrar 3D'ye taşır.

    Başarısız bir geometrik işlem exception üretmez;
    o aşamada None/boş bölge olarak değerlendirilir.
    """

    poly_3d = np.asarray(poly_3d, dtype=float)

    # ------------------------------------------------------------
    # Girdi kontrolleri
    # ------------------------------------------------------------

    if poly_3d.ndim != 2 or poly_3d.shape[1] != 3:
        raise ValueError("poly_3d (n, 3) şeklinde olmalıdır.")

    if len(poly_3d) < 3:
        raise ValueError("En az üç noktalı bir poligon gerekli.")

    if e <= 0:
        raise ValueError("e sıfırdan büyük olmalıdır.")

    w_vector_2d = np.asarray(w_vector_2d, dtype=float)

    if w_vector_2d.shape != (2,):
        raise ValueError("w_vector_2d iki bileşenli olmalıdır.")

    if np.linalg.norm(w_vector_2d) <= 1e-9:
        raise ValueError("w_vector_2d sıfır vektör olamaz.")

    # ------------------------------------------------------------
    # Local sistem ve 2D projection
    # ------------------------------------------------------------

    local_sys = _make_local_sys(poly_3d)
    poly_2d = _project_3d_to_local_2d(poly_3d, local_sys)
    
    edges = polygon_edges(poly_2d)

    if idx_ not in edges:
        raise IndexError(
            f"idx_={idx_} geçersiz. "
            f"Geçerli indeksler: {list(edges.keys())}"
        )

    edge = edges[idx_]

    p1_2d = edge["p1"]
    p2_2d = edge["p2"]

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

    def to_3d(poly):
        if not valid_polygon(poly):
            return None

        return _unproject_local_2d_to_3d(poly, local_sys)

    offset = offset_edge_2d(
        poly_2d,
        p1_2d,
        p2_2d,
        w_vector_2d,
        e / 10.0,
    )
    
    
    if offset is None:
        
        return []

    offset_p1, offset_p2 = offset
    
    left, right = split(
        poly_2d,
        offset_p1,
        offset_p2,
    )
    

    if left is None or right is None:
        
        return []

    offset_p1 = create_edge_perp_2d(
        right,
        p1_2d,
        p2_2d,
        w_vector_2d,
        e / 4.0,
    )
    
    
    if offset_p1 is None:
        
        return []
        
    (result_L, result_R) = offset_p1
    cut_p1, cut_p2 = result_L

    left_p1, right_p1 = split(right, cut_p1, cut_p2)

    if left_p1 is None or right_p1 is None:
        return []

    cut_p1, cut_p2 = result_R

    left_p2, right_p2 = split(right_p1, cut_p1, cut_p2)
    

    if left_p2 is None or right_p2 is None:
        return []


    regions_3d = [
        to_3d(left),
        to_3d(left_p1),
        to_3d(left_p2),
        to_3d(right_p2),
    ]


    return [
        close_polygon(region)
        for region in regions_3d
        if valid_polygon(region)
    ]
    
def create_region_LMN_poly(
    poly_3d,
    e=12.0,
    w_vector_2d=(-1.0, 0.0),
    idx_=0,
):
    poly_3d = np.asarray(poly_3d, dtype=float)

    if poly_3d.ndim != 2 or poly_3d.shape[1] != 3:
        raise ValueError("poly_3d (n, 3) şeklinde olmalıdır.")

    if len(poly_3d) < 3:
        raise ValueError("En az üç noktalı bir poligon gerekli.")

    if e <= 0:
        raise ValueError("e sıfırdan büyük olmalıdır.")

    w_vector_2d = np.asarray(w_vector_2d, dtype=float)

    if w_vector_2d.shape != (2,):
        raise ValueError("w_vector_2d iki bileşenli olmalıdır.")

    if np.linalg.norm(w_vector_2d) <= 1e-9:
        raise ValueError("w_vector_2d sıfır vektör olamaz.")

    # ---------------------------------------------------------
    # 1. 3D -> lokal 2D
    # ---------------------------------------------------------

    local_sys = _make_local_sys(poly_3d)
    poly_2d = _project_3d_to_local_2d(
        poly_3d,
        local_sys,
    )

    edges = polygon_edges(poly_2d)

    if idx_ not in edges:
        raise IndexError(
            f"idx_={idx_} geçersiz. "
            f"Geçerli indeksler: {list(edges.keys())}"
        )

    edge = edges[idx_]

    p1_2d = edge["p1"]
    p2_2d = edge["p2"]

    # Kenarın orta noktası.
    # Bu nokta, ötelenmiş kesme doğrusunun hangi tarafının
    # rüzgara yakın olduğunu belirlemek için kullanılacak.
    edge_mid = 0.5 * (p1_2d + p2_2d)

    # ---------------------------------------------------------
    # Yardımcılar
    # ---------------------------------------------------------

    def valid_polygon(poly, tol=1e-9):
        if poly is None or len(poly) < 3:
            return False

        area2 = np.sum(
            poly[:, 0] * np.roll(poly[:, 1], -1)
            - poly[:, 1] * np.roll(poly[:, 0], -1)
        )

        return abs(area2) > tol

    def split(poly, cut_p1, cut_p2):
        if not valid_polygon(poly):
            return None, None

        left, right = _split_by_line_2d(
            poly,
            cut_p1,
            cut_p2,
        )

        if not valid_polygon(left):
            left = None

        if not valid_polygon(right):
            right = None

        return left, right

    def side_of_line(point, line_p1, line_p2):
        line = line_p2 - line_p1
        v = point - line_p1

        return (
            line[0] * v[1]
            - line[1] * v[0]
        )

    def to_3d(poly):
        if not valid_polygon(poly):
            return None

        return _unproject_local_2d_to_3d(
            poly,
            local_sys,
        )

    # ---------------------------------------------------------
    # 2. e/10 rüzgar tarafı -> L
    # ---------------------------------------------------------

    offset_L = offset_edge_2d(
        poly_2d,
        p1_2d,
        p2_2d,
        w_vector_2d,
        e / 10.0,
    )

    if offset_L is None:
        return []

    cut_L_p1, cut_L_p2 = offset_L

    left, right = split(
        poly_2d,
        cut_L_p1,
        cut_L_p2,
    )

    if left is None and right is None:
        return []

    # Ötelenmiş çizginin orijinal kenara göre hangi tarafında
    # olduğunu belirliyoruz.
    #
    # Orijinal kenarın bulunduğu taraf = rüzgara yakın taraf = L
    #
    side_edge = side_of_line(
        edge_mid,
        cut_L_p1,
        cut_L_p2,
    )

    if side_edge >= 0:
        L = left
        remaining = right
    else:
        L = right
        remaining = left

    if L is None or remaining is None:
        return []

    # ---------------------------------------------------------
    # 3. Rüzgara en yakın p0 -> e kadar giderek M/N kesimi
    # ---------------------------------------------------------
    
    w_perp = np.array([-w_vector_2d[1], w_vector_2d[0]])
    
    # Rüzgara en yakın nokta
    projections = poly_2d @ w_vector_2d
    p0 = poly_2d[np.argmin(projections)]

    # p0 -> rüzgar doğrultusunda e
    p1 = p0 + w_vector_2d * e/2

    # Rüzgara dik ikinci nokta
    p2 = p1 + w_perp * e

    print("p0:", p0, "p1:", p1, "p2:", p2)
    
    result_MN = _clip_line_to_polygon_2d(
        p1,
        p2,
        remaining,
    )

    print("result_MN:", result_MN)
    
    # Çizgi poligona girmiyorsa N oluşmuyor.
    # Geri kalan bölgenin tamamı M.
    if result_MN is None:
        M = remaining

        regions = [L, M]

    else:
        cut_MN_p1, cut_MN_p2 = result_MN

        near, far = _split_by_line_2d(
            remaining,
            cut_MN_p1,
            cut_MN_p2,
        )

        # p0 rüzgara yakın tarafta olduğundan,
        # kesme çizgisinin p0 tarafı M'dir.
        side = (
            (cut_MN_p2[0] - cut_MN_p1[0])
            * (p0 - cut_MN_p1)[1]
            -
            (cut_MN_p2[1] - cut_MN_p1[1])
            * (p0 - cut_MN_p1)[0]
        )

        if side >= 0:
            M = near
            N = far
        else:
            M = far
            N = near

        regions = [L, M, N]

    # ---------------------------------------------------------
    # 4. 2D -> 3D + kapatma
    # ---------------------------------------------------------

    result = []

    for region in regions:

        if region is None or len(region) < 3:
            continue

        region_3d = _unproject_local_2d_to_3d(
            region,
            local_sys,
        )

        result.append(
            close_polygon(region_3d)
        )

    return result
    
if __name__ == "__main__":
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

    e= 12
    w_vector_2d= [1,0]
    p_name= 'C1'
    idx_= 3
    scale_=1000

    poly_3d= get_polygon_coords(polygons[p_name], points, scale_)

    render_lines= create_region_LMN_poly(poly_3d, e, w_vector_2d, idx_)


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
        points={"O": [0, 0, 0], "O1": [1000, 0, 0]},
        lines=render_lines
    )

    view.resize(1000, 700)
    view.show()
    sys.exit(app.exec())