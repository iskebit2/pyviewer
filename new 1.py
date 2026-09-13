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


def polygon_edges(polygon: np.ndarray) -> List[Dict]:
    """Poligonun kenarlarını (p1, p2, index) listesi olarak döndürür."""
    pts = _open_polygon(polygon)
    n = len(pts)
    return [
        {"index": i, "p1": pts[i], "p2": pts[(i + 1) % n]}
        for i in range(n)
    ]


def _compute_normal(polygon: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Newell metodu ile poligon normalini hesaplar."""
    pts = _open_polygon(polygon)
    if len(pts) < 3:
        raise ValueError("Poligon en az 3 noktadan oluşmalıdır.")

    # Vektörel Newell formülü
    p_curr = pts
    p_next = np.roll(pts, -1, axis=0)
    normal = np.array([
        np.sum((p_curr[:, 1] - p_next[:, 1]) * (p_curr[:, 2] + p_next[:, 2])),
        np.sum((p_curr[:, 2] - p_next[:, 2]) * (p_curr[:, 0] + p_next[:, 0])),
        np.sum((p_curr[:, 0] - p_next[:, 0]) * (p_curr[:, 1] + p_next[:, 1])),
    ])

    norm_len = np.linalg.norm(normal)
    if norm_len < 1e-12:
        raise ValueError(f"Geçersiz/çökmüş poligon düzlemi: {pts}")
    return normal, normal / norm_len


def _get_best_projection_plane(polygon: np.ndarray) -> Tuple[Tuple[int, int], int]:
    """En iyi projeksiyon düzlemini seçer. ((i1,i2), missing_idx) döndürür."""
    _, normal_unit = _compute_normal(polygon)
    missing_idx = int(np.argmax(np.abs(normal_unit)))
    axes = [(0, 1), (0, 2), (1, 2)]
    # missing_idx 2 -> XY, 1 -> XZ, 0 -> YZ
    plane_map = {2: (0, 1), 1: (0, 2), 0: (1, 2)}
    return plane_map[missing_idx], missing_idx


def point_unproject_to_3d(polygon: np.ndarray, pt_2d: np.ndarray) -> np.ndarray:
    """2D noktayı poligon düzlemine geri yansıtır."""
    normal_unit = _compute_normal(polygon)[1]
    (i1, i2), missing_idx = _get_best_projection_plane(polygon)

    n_missing = normal_unit[missing_idx]
    D = -np.dot(normal_unit, polygon[0])

    p3d = np.zeros(3)
    p3d[i1] = pt_2d[0]
    p3d[i2] = pt_2d[1]
    p3d[missing_idx] = -(normal_unit[i1] * pt_2d[0]
                         + normal_unit[i2] * pt_2d[1] + D) / n_missing
    return p3d

def _clip_line_to_polygon(line_p1, line_p2, polygon, i1, i2):
    """Sonsuz çizginin poligon sınırıyla kesiştiği iki noktayı bulur."""

    p1 = np.asarray(line_p1, dtype=float)
    p2 = np.asarray(line_p2, dtype=float)

    direction = p2 - p1
    intersections = []

    for i in range(len(polygon)):
        a = np.asarray(polygon[i], dtype=float)[[i1, i2]]
        b = np.asarray(polygon[(i + 1) % len(polygon)], dtype=float)[[i1, i2]]

        edge = b - a

        cross = direction[0] * edge[1] - direction[1] * edge[0]

        if abs(cross) < 1e-10:
            continue

        q = a - p1

        t = (q[0] * edge[1] - q[1] * edge[0]) / cross
        u = (q[0] * direction[1] - q[1] * direction[0]) / cross

        # Poligon kenarı üzerinde kesişim
        if -1e-10 <= u <= 1 + 1e-10:
            intersections.append(p1 + t * direction)

    if len(intersections) < 2:
        return None

    # Çizgi üzerindeki en uzak iki kesişim
    intersections.sort(
        key=lambda p: np.dot(p - p1, direction)
    )

    return intersections[0], intersections[-1]

def offset_edge(polygon, p1_3d, p2_3d, w_vector, e, perp=False):
    """Kenarı w_vector yönünde veya ona dik yönde offsetler."""
    (i1, i2), _ = _get_best_projection_plane(polygon)

    EXT = 100

    p1 = np.asarray(p1_3d, dtype=float)[[i1, i2]]
    p2 = np.asarray(p2_3d, dtype=float)[[i1, i2]]

    edge_vec = p2 - p1
    edge_len = np.linalg.norm(edge_vec)
    if edge_len < 1e-8:
        return None
    edge_dir = edge_vec / edge_len

    if perp:
        # Kenara dik yönde, p1 ve p2'den d_L ileri/geri noktalarda kesen çizgiler
        perp_dir = np.array([-edge_dir[1], edge_dir[0]])
        d_L= e/4
        EXT= e/10
        split1 = p1 + edge_dir * d_L
        split2 = p2 - edge_dir * d_L

        line_L_a = point_unproject_to_3d(polygon, split1)
        line_L_b = point_unproject_to_3d(polygon, split1 + perp_dir * EXT)
        line_R_a = point_unproject_to_3d(polygon, split2)
        line_R_b = point_unproject_to_3d(polygon, split2 + perp_dir * EXT)

        return ((line_L_a, line_L_b), (line_R_a, line_R_b))

    # w_vector yönünde offset
    w_2d = np.asarray(w_vector, dtype=float)[[i1, i2]]
    w_len = np.linalg.norm(w_2d)
    if w_len < 1e-8:
        return None
    w_dir = w_2d / w_len

    d_L= e/10
    EXT= 500
    
    line_L_p1 = p1 + w_dir * d_L
    line_L_p2 = p2 + w_dir * d_L

    clipped = _clip_line_to_polygon(
        line_L_p1,
        line_L_p2,
        polygon,
        i1,
        i2
    )

    if clipped is None:
        return None

    line_L_p1_ext, line_L_p2_ext = clipped

    return (
        point_unproject_to_3d(polygon, line_L_p1_ext),
        point_unproject_to_3d(polygon, line_L_p2_ext),
    )
    
    
if __name__ == "__main__":
    from domains import LineItem
    from canvas3d import View3D
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
    
    polygon = np.array([points[pt] for pt in polygons['C1']])
    edges = polygon_edges(polygon)
    e = 8000
    w_vector = np.array([0, 1, 0])
    edge = edges[0]

    p1_3d, p2_3d = edge['p1'], edge['p2']

    res_wind = offset_edge(polygon, p1_3d, p2_3d, w_vector, e)
    res_perp = offset_edge(polygon, p1_3d, p2_3d, w_vector, e, perp=True)

    if res_wind is None or res_perp is None:
        raise RuntimeError("Offset hesaplanamadı")

    line_wind_p1, line_wind_p2 = res_wind
    line_perp1, line_perp2 = res_perp
    (perp1_start, perp1_end), (perp2_start, perp2_end) = res_perp
    
    
    
    
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    

    lines = [res_wind,line_perp1, line_perp2]

    

    view = View3D()
    view.set_data(points=points, polygons=polygons, lines= lines)

    view.resize(1000, 700)
    view.show()
    view.zoom_extents()

    sys.exit(app.exec())
