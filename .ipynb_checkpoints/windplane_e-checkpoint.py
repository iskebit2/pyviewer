# windplane.py

import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Tuple, Optional, Union, Any

EPS = 1.0e-9


class SurfaceType(Enum):
    WALL = "WALL"
    ROOF = "ROOF"


class WindRelation(Enum):
    WINDWARD = "WINDWARD"
    LEEWARD = "LEEWARD"
    PARALLEL = "PARALLEL"


@dataclass
class Zone:
    name: str
    polygon: np.ndarray
    cpe_neg: Optional[float] = None
    cpe_pos: Optional[float] = None


def close_polygon(polygon: np.ndarray, tol: float = 1e-8) -> np.ndarray:
    """Poligonu kapatır"""
    polygon = np.asarray(polygon, dtype=float)
    if len(polygon) == 0:
        return polygon
    if not np.allclose(polygon[0], polygon[-1], atol=tol):
        polygon = np.vstack([polygon, polygon[0]])
    return polygon


def same_edge(edge1: Dict, edge2: Dict, tol: float = 1e-6) -> bool:
    """İki kenarın aynı olup olmadığını kontrol eder"""
    p1 = np.asarray(edge1["p1"], dtype=float)
    p2 = np.asarray(edge1["p2"], dtype=float)

    q1 = np.asarray(edge2["p1"], dtype=float)
    q2 = np.asarray(edge2["p2"], dtype=float)

    return (
        np.allclose(p1, q1, atol=tol) and np.allclose(p2, q2, atol=tol)
    ) or (
        np.allclose(p1, q2, atol=tol) and np.allclose(p2, q1, atol=tol)
    )


def polygon_edges(polygon: np.ndarray) -> List[Dict]:
    """Poligonun kenarlarını döndürür"""
    polygon = np.asarray(polygon, dtype=float)

    if np.allclose(polygon[0], polygon[-1]):
        polygon = polygon[:-1]

    n = len(polygon)
    edges = []

    for i in range(n):
        edges.append({
            "index": i,
            "p1": polygon[i],
            "p2": polygon[(i + 1) % n],
        })

    return edges


def polygon_centroid(polygon: np.ndarray) -> np.ndarray:
    """Poligonun merkezini hesaplar"""
    pts = np.asarray(polygon, dtype=float)

    if np.allclose(pts[0], pts[-1]):
        pts = pts[:-1]

    return np.mean(pts, axis=0)


class WindPlane:
    def __init__(self, polygon: Union[List, np.ndarray], name: str = "Test"):
        """3B Düzlemsel Poligon Nesnesi"""
        pts = np.asarray(polygon, dtype=float)

        if len(pts) > 1 and np.allclose(pts[0], pts[-1], atol=1e-8):
            pts = pts[:-1]

        if len(pts) < 3:
            raise ValueError("Poligon en az 3 noktadan oluşmalıdır.")

        self.polygon_name = name
        self.pts_3d: np.ndarray = close_polygon(pts)
        self.n_pts: int = len(pts)

        self.normal, self.normal_unit = self._compute_normal()
        self.pitch: float = self._compute_pitch()
        self.surface_type: SurfaceType = SurfaceType.ROOF if self.pitch <= 75.0 else SurfaceType.WALL
        self.proj_info = self._get_best_projection_plane()
        self.exposed_edge_list = []
        
        self.results = {
            "name": self.polygon_name,
            "polygon": self.pts_3d,
            "surface_type": self.surface_type,
            "pitch": self.pitch,
            "wind_relation": None,
            "exposed_edges": None,
            "leading_edges": None,
            "gl_leading_edge": None,
            "shared_edge_neighbors": None,
            "roof_reg_type": None
        }

    @staticmethod
    def close_polygon(polygon: np.ndarray, tol: float = 1e-8) -> np.ndarray:
        return close_polygon(polygon, tol)

    def _compute_normal(self) -> Tuple[np.ndarray, np.ndarray]:
        normal = np.zeros(3)
        for i in range(self.n_pts):
            p_curr, p_next = self.pts_3d[i], self.pts_3d[(i + 1) % self.n_pts]
            normal[0] += (p_curr[1] - p_next[1]) * (p_curr[2] + p_next[2])
            normal[1] += (p_curr[2] - p_next[2]) * (p_curr[0] + p_next[0])
            normal[2] += (p_curr[0] - p_next[0]) * (p_curr[1] + p_next[1])

        norm_len = np.linalg.norm(normal)
        if norm_len < 1e-12:
            raise ValueError(f"Geçersiz/Çökmüş poligon düzlemi: {self.pts_3d}")
        return normal, normal / norm_len

    def _compute_pitch(self) -> float:
        nz_ratio = abs(self.normal_unit[2])
        nz_ratio = np.clip(nz_ratio, -1.0, 1.0)
        return float(np.degrees(np.arccos(nz_ratio)))

    def _get_best_projection_plane(self):
        abs_n = np.abs(self.normal_unit)
        max_idx = np.argmax(abs_n)
        if max_idx == 2:
            return 'XY', (0, 1), 2
        elif max_idx == 1:
            return 'XZ', (0, 2), 1
        else:
            return 'YZ', (1, 2), 0

    def _unproject_to_3d(self, pts_2d: np.ndarray) -> np.ndarray:
        _, (idx1, idx2), missing_idx = self.proj_info
        n_missing = self.normal_unit[missing_idx]
        D = -np.dot(self.normal_unit, self.pts_3d[0])

        pts_3d = []
        for pt in pts_2d:
            p3d = np.zeros(3)
            p3d[idx1] = pt[0]
            p3d[idx2] = pt[1]
            known_sum = self.normal_unit[idx1] * pt[0] + self.normal_unit[idx2] * pt[1] + D
            p3d[missing_idx] = -known_sum / n_missing
            pts_3d.append(p3d)
        return np.array(pts_3d)

    def analyze_wind_relation(self, w_vector: np.ndarray) -> WindRelation:
        w_xy = np.asarray(w_vector[:2], dtype=float)
        w_norm = np.linalg.norm(w_xy)
        if w_norm < 1e-12:
            raise ValueError("Rüzgar vektörünün yatay bileşeni sıfır olamaz.")

        w_xy /= w_norm
        n_xy = self.normal_unit[:2]
        dot = np.dot(n_xy, w_xy)

        if dot < -0.2:
            return WindRelation.WINDWARD
        elif dot > 0.2:
            return WindRelation.LEEWARD
        else:
            return WindRelation.PARALLEL

    def polygon_direction_xy(self) -> str:
        """Poligonun XY düzlemindeki yönünü belirler."""
        polygon = self.pts_3d

        if np.allclose(polygon[0], polygon[-1]):
            polygon = polygon[:-1]

        area2 = 0.0
        n = len(polygon)

        for i in range(n):
            x1, y1 = polygon[i][:2]
            x2, y2 = polygon[(i + 1) % n][:2]
            area2 += x1 * y2 - x2 * y1

        if area2 > EPS:
            return "CCW"
        elif area2 < -EPS:
            return "CW"
        else:
            return "DEGENERATE"

    # ==================== EXPOSED EDGES (3D) ====================
    
    def exposed_edges(self, w: np.ndarray) -> List[Dict[str, Any]]:
        """
        Hem Duvar (WALL) hem Çatı (ROOF) elemanları için 3B uzayda
        rüzgara maruz kalan (exposed) kenarları tespit eder.
        """
        polygon = self.pts_3d
        if np.allclose(polygon[0], polygon[-1]):
            polygon = polygon[:-1]
            
        n = len(polygon)
        exposed_edge = []

        # 3B Rüzgarın geldiği yön (Wind From Vector)
        w_3d = np.asarray(w, dtype=float)
        w_norm = np.linalg.norm(w_3d)
        if w_norm < 1e-12:
            return []
        
        wind_from = -(w_3d / w_norm)
        surface_normal = self.normal_unit  # 3B yüzey birim normali

        for i in range(n):
            p1 = polygon[i]
            p2 = polygon[(i + 1) % n]

            edge_vec = p2 - p1
            edge_len = np.linalg.norm(edge_vec)

            if edge_len < 1e-12:
                continue

            edge_unit = edge_vec / edge_len

            # 1. 3B Kenar Dış Normali
            outward_normal_3d = np.cross(edge_unit, surface_normal)
            outward_normal_3d_len = np.linalg.norm(outward_normal_3d)

            if outward_normal_3d_len < 1e-12:
                continue
                
            outward_normal_3d /= outward_normal_3d_len

            # 2. Exposure Hesabı
            exposure = np.dot(outward_normal_3d, wind_from)

            # Kenarın rüzgar vektörü ile yaptığı açı
            cos_angle = np.clip(abs(np.dot(edge_unit, wind_from)), -1.0, 1.0)
            angle = np.degrees(np.arccos(cos_angle))

            tol = 1e-6

            if exposure > tol:
                exposed_edge.append({
                    "index": i,
                    "p1": p1,
                    "p2": p2,
                    "angle": angle,
                    "exposure": exposure,
                    "leading": False,
                    "shared": False
                })

        self.exposed_edge_list = exposed_edge
        return exposed_edge

    # ==================== LEADING EDGES (3D) ====================
    
    def find_local_leading_edges(self, wind: np.ndarray, tol: float = 1.0) -> List[Dict[str, Any]]:
        """Rüzgar yönüne göre en öndeki kenarları 3B uzayda bulur."""
        # Eğer exposed_edges henüz hesaplanmamışsa hesapla
        if not self.exposed_edge_list:
            self.exposed_edges(wind)
        
        exposed_edges = self.exposed_edge_list
        
        if not exposed_edges:
            return []

        w_3d = np.asarray(wind, dtype=float)
        w_norm = np.linalg.norm(w_3d)
        if w_norm < 1e-12:
            return []

        wind_from = -(w_3d / w_norm)

        candidates = []

        for edge in exposed_edges:
            p1 = np.asarray(edge["p1"], dtype=float)
            p2 = np.asarray(edge["p2"], dtype=float)

            # 3B Noktaların rüzgar geliş hattı üzerindeki izdüşüm mesafesi
            p1_pos = np.dot(p1, wind_from)
            p2_pos = np.dot(p2, wind_from)

            front_positions = sorted([p1_pos, p2_pos], reverse=True)

            candidates.append({
                **edge,
                "p1_front_position": p1_pos,
                "p2_front_position": p2_pos,
                "front_positions": front_positions,
            })

        if not candidates:
            return []

        # En öndeki pozisyonu bul
        best_positions = max(edge["front_positions"] for edge in candidates)

        def is_at_leading_position(edge):
            a = edge["front_positions"]
            b = best_positions
            return (abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol)

        leading_edges = []
        for idx_, edge in enumerate(candidates):
            exposed_edges[idx_]["leading"] = False
            if is_at_leading_position(edge):
                leading_edges.append(edge)
                exposed_edges[idx_]["leading"] = True

        self.exposed_edge_list = exposed_edges
        return leading_edges

    # ==================== GLOBAL LEADING EDGE ANALİZİ ====================
    
    def check_global_roof_leading_edge(
        self,
        candidate_edge: Dict,
        all_roof_polygons: Dict[str, np.ndarray],
        wind: np.ndarray,
        tol: float = 1e-6
    ) -> Dict:
        """Kenarın global leading edge olup olmadığını kontrol eder."""
        w_xy = np.asarray(wind[:2], dtype=float)
        wind_norm = np.linalg.norm(w_xy)

        if wind_norm < 1e-12:
            raise ValueError("Rüzgârın XY yönü sıfır olamaz.")

        w_xy /= wind_norm
        wind_from = -w_xy

        shared_with = []

        for polygon_name, polygon in all_roof_polygons.items():
            if polygon_name == self.polygon_name:
                continue

            for edge in polygon_edges(polygon):
                if same_edge(candidate_edge, edge, tol=tol):
                    shared_with.append({
                        "polygon": polygon_name,
                        "edge_index": edge["index"],
                        "p1": edge["p1"],
                        "p2": edge["p2"],
                    })

        if not shared_with:
            return {
                "status": "GLOBAL_LEADING",
                "shared": False,
                "shared_with": []
            }

        candidate_polygon = all_roof_polygons[self.polygon_name]
        candidate_centroid = polygon_centroid(candidate_polygon)
        candidate_position = np.dot(candidate_centroid[:2], wind_from)

        upstream_polygons = []

        for shared in shared_with:
            other_name = shared["polygon"]
            other_polygon = all_roof_polygons[other_name]
            other_centroid = polygon_centroid(other_polygon)
            other_position = np.dot(other_centroid[:2], wind_from)

            if other_position > candidate_position + tol:
                upstream_polygons.append({
                    "polygon": other_name,
                    "position": other_position,
                })

        if upstream_polygons:
            return {
                "status": "NOT_GLOBAL_LEADING",
                "shared": True,
                "shared_with": shared_with,
                "upstream_polygons": upstream_polygons,
            }

        return {
            "status": "GLOBAL_LEADING",
            "shared": True,
            "shared_with": shared_with,
            "upstream_polygons": [],
        }

    def find_leading_edge_neighbors(
        self,
        global_leading_edge: Dict,
        all_roof_polygons: Dict[str, np.ndarray],
        tol: float = 1e-6
    ) -> Dict:
        """GLOBAL LEADING EDGE'in iki uç noktasındaki komşu kenarları bulur."""
        p1 = np.asarray(global_leading_edge["p1"], dtype=float)
        p2 = np.asarray(global_leading_edge["p2"], dtype=float)

        own_edges = polygon_edges(all_roof_polygons[self.polygon_name])

        p1_neighbor = None
        p2_neighbor = None

        for edge in own_edges:
            if same_edge(edge, global_leading_edge, tol):
                continue

            e_p1 = np.asarray(edge["p1"], dtype=float)
            e_p2 = np.asarray(edge["p2"], dtype=float)

            uses_p1 = np.allclose(e_p1, p1, atol=tol) or np.allclose(e_p2, p1, atol=tol)
            uses_p2 = np.allclose(e_p1, p2, atol=tol) or np.allclose(e_p2, p2, atol=tol)

            if uses_p1:
                p1_neighbor = edge
            if uses_p2:
                p2_neighbor = edge

        p1_shared_with = []
        p2_shared_with = []

        for name, polygon in all_roof_polygons.items():
            if name == self.polygon_name:
                continue

            for edge in polygon_edges(polygon):
                if p1_neighbor is not None and same_edge(p1_neighbor, edge, tol):
                    p1_shared_with.append(name)
                if p2_neighbor is not None and same_edge(p2_neighbor, edge, tol):
                    p2_shared_with.append(name)

        return {
            "p1_neighbor": p1_neighbor,
            "p2_neighbor": p2_neighbor,
            "p1_shared": bool(p1_shared_with),
            "p2_shared": bool(p2_shared_with),
            "p1_shared_with": p1_shared_with,
            "p2_shared_with": p2_shared_with,
        }

    def roof_region_types(self, w: np.ndarray, global_status: Optional[str] = None, 
                          shared_edge_neighbors: bool = False) -> List[str]:
        """Çatı bölge tiplerini belirler."""
        relation = self.analyze_wind_relation(w)

        n_leading = len(self.results.get("leading_edges", []))
        n_exposed = len(self.results.get("exposed_edges", []))

        if relation == WindRelation.WINDWARD:
            return ["F", "G", "H"]

        if relation == WindRelation.LEEWARD:
            if n_leading == 1 and n_exposed > 1:
                return ["I", "J", "K"]
            return ["I", "J"]

        if relation == WindRelation.PARALLEL:
            if global_status == "GLOBAL_LEADING":
                if not shared_edge_neighbors:
                    return ["Fu", "Fl", "G", "H"]
                return ["F", "G", "H"]
            return ["L", "M", "N"]

        return []

    def analysis_(self, w: np.ndarray, all_roof_polygons: Dict[str, np.ndarray]) -> None:
        """Tam çatı rüzgar analizini yapar."""
        self.results = {
            "name": self.polygon_name,
            "polygon": self.pts_3d,
            "surface_type": self.surface_type,
            "pitch": self.pitch,
            "wind_relation": None,
            "exposed_edges": None,
            "leading_edges": None,
            "gl_leading_edge": None,
            "shared_edge_neighbors": None,
            "roof_reg_type": None
        }

        rel_ = self.analyze_wind_relation(w)
        self.results["wind_relation"] = rel_

        leading_edges = self.find_local_leading_edges(w, tol=1.0)
        self.results["leading_edges"] = leading_edges
        self.results["exposed_edges"] = self.exposed_edge_list

        global_status = None
        result_bool = False

        for candidate_edge in self.exposed_edge_list:
            if not candidate_edge.get("leading", False):
                continue

            gl_leading_edge = self.check_global_roof_leading_edge(
                candidate_edge,
                all_roof_polygons,
                w,
                tol=1e-6
            )

            self.results["gl_leading_edge"] = gl_leading_edge

            if gl_leading_edge["status"] == "GLOBAL_LEADING":
                global_status = "GLOBAL_LEADING"

                result_ = self.find_leading_edge_neighbors(
                    candidate_edge,
                    all_roof_polygons,
                    tol=1e-6
                )

                result_bool = result_["p1_shared"] or result_["p2_shared"]
                candidate_edge["shared"] = result_bool

                self.results["find_leading_edge_neighbors"] = result_
                self.results["shared_edge_neighbors"] = result_bool

        roof_reg_type = self.roof_region_types(
            w,
            global_status,
            result_bool,
        )
        self.results["roof_reg_type"] = roof_reg_type

    # ==================== 2D BÖLME METOTLARI ====================
    
    def _split_by_line_2d(self, poly_2d: np.ndarray, p1: np.ndarray, p2: np.ndarray) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """2D poligonu bir çizgi ile ikiye böler."""
        line_dir = p2 - p1
        if np.linalg.norm(line_dir) < 1e-8:
            return None

        def side(p):
            return line_dir[0] * (p[1] - p1[1]) - line_dir[1] * (p[0] - p1[0])

        pts = poly_2d[:-1] if np.allclose(poly_2d[0], poly_2d[-1]) else poly_2d
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
            return None

        pos = close_polygon(pos)
        neg = close_polygon(neg)

        def area(p):
            return 0.5 * abs(np.sum(p[:-1, 0] * p[1:, 1] - p[1:, 0] * p[:-1, 1]))

        return (pos, neg) if area(pos) >= 1e-4 and area(neg) >= 1e-4 else None

    # ==================== DUVAR (WALL) BÖLGE ANALİZİ ====================
    
    def get_wall_zones(self, w_vector: np.ndarray, e: float) -> Dict[str, np.ndarray]:
        """Duvar yüzeyi için tüm bölgeleri hesaplar."""
        if self.surface_type != SurfaceType.WALL:
            raise TypeError("Bu fonksiyon sadece DUVAR (WALL) yüzeylerinde çalışır.")

        # Önce exposed ve leading edges'i bul
        exposed = self.exposed_edges(w_vector)
        leading = self.find_local_leading_edges(w_vector)
        
        # Sonuçları kaydet
        self.exposed_edge_list = exposed
        self.results["exposed_edges"] = exposed
        self.results["leading_edges"] = leading

        wind_rel = self.analyze_wind_relation(w_vector)
        self.results["wind_relation"] = wind_rel
        
        # WINDWARD: Rüzgar doğrudan çarpıyor -> D bölgesi
        if wind_rel == WindRelation.WINDWARD:
            return {'D': self.close_polygon(self.pts_3d)}
        
        # LEEWARD: Rüzgar arkası -> E bölgesi
        if wind_rel == WindRelation.LEEWARD:
            return {'E': self.close_polygon(self.pts_3d)}

        # PARALLEL: Rüzgar yüzeye paralel -> A, B, C bölgeleri
        return self._get_wall_parallel_zones(w_vector, e)

    def _get_wall_parallel_zones(self, w_vector: np.ndarray, e: float) -> Dict[str, np.ndarray]:
        """Rüzgara paralel duvar için A, B, C bölgelerini hesaplar."""
        # Duvar normali
        wall_normal = self.normal_unit
        
        # Duvarın yatay normali
        wall_normal_xy = wall_normal[:2]
        wall_normal_len = np.linalg.norm(wall_normal_xy)
        
        if wall_normal_len < 1e-12:
            return {'A': self.close_polygon(self.pts_3d)}

        wall_normal_xy = wall_normal_xy / wall_normal_len

        # Rüzgar vektörü
        w_xy = np.asarray(w_vector[:2], dtype=float)
        w_norm = np.linalg.norm(w_xy)
        if w_norm < 1e-12:
            return {'A': self.close_polygon(self.pts_3d)}
        w_xy = w_xy / w_norm

        # Duvar düzleminde rüzgar yönüne dik vektör
        wind_on_wall = w_xy - np.dot(w_xy, wall_normal_xy) * wall_normal_xy
        wind_on_wall_norm = np.linalg.norm(wind_on_wall)
        
        if wind_on_wall_norm < 1e-12:
            return {'A': self.close_polygon(self.pts_3d)}
        
        wind_on_wall = wind_on_wall / wind_on_wall_norm

        # Poligonu duvar düzleminde 2D'ye izdüşür
        v1 = np.array([-wall_normal_xy[1], wall_normal_xy[0], 0.0])
        v1_norm = np.linalg.norm(v1)
        if v1_norm < 1e-12:
            return {'A': self.close_polygon(self.pts_3d)}
        v1 = v1 / v1_norm
        
        v2 = np.cross(wall_normal, v1)
        v2_norm = np.linalg.norm(v2)
        if v2_norm < 1e-12:
            return {'A': self.close_polygon(self.pts_3d)}
        v2 = v2 / v2_norm

        # Noktaları 2D'ye izdüşür
        pts_2d = []
        for pt in self.pts_3d:
            u = np.dot(pt, v1)
            v = np.dot(pt, v2)
            pts_2d.append([u, v])
        pts_2d = np.array(pts_2d)
        pts_2d_closed = close_polygon(pts_2d)

        # Rüzgar yönünü 2D'ye izdüşür
        wind_2d = np.array([np.dot(w_vector, v1), np.dot(w_vector, v2)])
        wind_2d_norm = np.linalg.norm(wind_2d)
        if wind_2d_norm < 1e-12:
            return {'A': self.close_polygon(self.pts_3d)}
        wind_dir_2d = wind_2d / wind_2d_norm

        # Projeksiyon uzunluğu
        proj_vals = pts_2d @ wind_dir_2d
        min_p, max_p = np.min(proj_vals), np.max(proj_vals)
        d_len = max_p - min_p

        if d_len < 1e-6:
            return {'A': self.close_polygon(self.pts_3d)}

        # Bölge konfigürasyonu
        if e >= 5.0 * d_len:
            splits, zone_names = [e / 5.0], ['A', 'B']
        elif e >= d_len:
            splits, zone_names = [e / 5.0], ['A', 'B']
        else:
            a_len = e / 5.0
            b_len = 4.0 * e / 5.0
            splits, zone_names = [a_len, a_len + b_len], ['A', 'B', 'C']

        current_poly_2d = pts_2d_closed
        zones: Dict[str, np.ndarray] = {}
        
        perp_dir = np.array([-wind_dir_2d[1], wind_dir_2d[0]])

        for idx, offset in enumerate(splits):
            if offset >= d_len - 1e-5:
                break

            split_p = min_p + offset
            ref_pt = wind_dir_2d * split_p
            p1 = ref_pt - perp_dir * 10000.0
            p2 = ref_pt + perp_dir * 10000.0

            res = self._split_by_line_2d(current_poly_2d, p1, p2)
            if res is None:
                break

            part1_2d, part2_2d = res
            center1 = np.mean(part1_2d[:-1], axis=0) @ wind_dir_2d
            center2 = np.mean(part2_2d[:-1], axis=0) @ wind_dir_2d

            if center1 < center2:
                zone_2d, current_poly_2d = part1_2d, close_polygon(part2_2d)
            else:
                zone_2d, current_poly_2d = part2_2d, close_polygon(part1_2d)

            # 2D'den 3D'ye dönüştür
            zone_3d = []
            for pt in zone_2d:
                p3d = pt[0] * v1 + pt[1] * v2
                zone_3d.append(p3d)
            zones[zone_names[idx]] = np.array(zone_3d)

        # Kalan bölge
        remaining_3d = []
        for pt in current_poly_2d:
            p3d = pt[0] * v1 + pt[1] * v2
            remaining_3d.append(p3d)
        zones[zone_names[len(zones)]] = np.array(remaining_3d)

        return zones

    # ==================== ÇATI BÖLGE ANALİZİ ====================
    
    def split_by_w_offset(self, w_vector: np.ndarray, e: float = 5000.0) -> Optional[List[Dict[str, Any]]]:
        """Rüzgar yönünde offset ile poligonu kesen kenarları bulur."""
        if self.surface_type != SurfaceType.ROOF:
            return None
            
        relation = self.analyze_wind_relation(w_vector)
        regions = self.results.get('roof_reg_type', [])
        
        if not regions:
            return None
            
        d_L = e / 10.0
        d_N = e / 2.0

        pts_3d = self.pts_3d
        n = self.n_pts

        _, (i1, i2), _ = self.proj_info

        poly_2d = pts_3d[:, [i1, i2]]
        poly_2d_closed = self.close_polygon(poly_2d)

        w_3d = np.asarray(w_vector, dtype=float)
        w_2d = w_3d[[i1, i2]]

        w_len = np.linalg.norm(w_2d)
        if w_len < 1e-8:
            return None

        w_dir = w_2d / w_len
        exposed = self.exposed_edge_list

        if not exposed:
            return None

        all_zones = []

        for edge in exposed:
            zones = {}
            edge_index = edge["index"]

            p1_3d = edge["p1"]
            p2_3d = edge["p2"]

            p1 = p1_3d[[i1, i2]]
            p2 = p2_3d[[i1, i2]]

            edge_vec = p2 - p1
            edge_len = np.linalg.norm(edge_vec)

            if edge_len < 1e-8:
                continue

            edge_dir = edge_vec / edge_len

            # e/10 çizgisi
            line_L_p1 = p1 + w_dir * d_L
            line_L_p2 = p2 + w_dir * d_L

            line_L_p1_ext = line_L_p1 - edge_dir * 1000000.0
            line_L_p2_ext = line_L_p2 + edge_dir * 1000000.0

            split_L = self._split_by_line_2d(
                poly_2d_closed,
                line_L_p1_ext,
                line_L_p2_ext
            )

            if split_L is None:
                continue

            part1, part2 = split_L

            def centroid(poly):
                return np.mean(poly[:-1], axis=0)

            c1 = centroid(part1)
            c2 = centroid(part2)

            proj1 = np.dot(c1, w_dir)
            proj2 = np.dot(c2, w_dir)

            edge_proj = np.dot((p1 + p2) / 2.0, w_dir)

            if abs(proj1 - edge_proj) < abs(proj2 - edge_proj):
                L_2d = part1
                remainder_2d = part2
            else:
                L_2d = part2
                remainder_2d = part1

            is_leading = edge.get('leading', False)
            is_shared = edge.get('shared', False)

            # PARALLEL
            if relation == WindRelation.PARALLEL:
                if is_leading and not is_shared:
                    fu_fl_split = self._split_turbulence_corners(L_2d, edge_dir, p1, p2, e / 4.0)
                    if fu_fl_split:
                        zones["Fu"] = self._unproject_to_3d(fu_fl_split["corner1"])
                        zones["Fl"] = self._unproject_to_3d(fu_fl_split["corner2"])
                    else:
                        zones["Fu"] = self._unproject_to_3d(L_2d)

                    zones["H"] = self._unproject_to_3d(remainder_2d)

                elif is_leading and is_shared:
                    fg_split = self._split_turbulence_corners(L_2d, edge_dir, p1, p2, e / 4.0)
                    if fg_split:
                        zones["F"] = self._unproject_to_3d(fg_split["corner1"])
                        zones["G"] = self._unproject_to_3d(fg_split["corner2"])
                    else:
                        zones["F"] = self._unproject_to_3d(L_2d)

                    zones["H"] = self._unproject_to_3d(remainder_2d)

                else:
                    zones["L"] = self._unproject_to_3d(L_2d)
                    mn_split = self._split_by_depth(remainder_2d, p1, p2, w_dir, d_N)
                    if mn_split:
                        zones["M"] = self._unproject_to_3d(mn_split["front"])
                        zones["N"] = self._unproject_to_3d(mn_split["back"])
                    else:
                        zones["M"] = self._unproject_to_3d(remainder_2d)

            # WINDWARD
            elif relation == WindRelation.WINDWARD:
                fg_split = self._split_turbulence_corners(L_2d, edge_dir, p1, p2, e / 4.0)
                if fg_split:
                    zones["F1"] = self._unproject_to_3d(fg_split["corner1"])
                    zones["G"] = self._unproject_to_3d(fg_split["mid"])
                    zones["F2"] = self._unproject_to_3d(fg_split["corner2"])
                else:
                    zones["F"] = self._unproject_to_3d(L_2d)

                zones["H"] = self._unproject_to_3d(remainder_2d)

            # LEEWARD
            elif relation == WindRelation.LEEWARD:
                leading_count = sum(1 for e_item in exposed if e_item.get('leading', False))

                if leading_count == 1 and len(exposed) > 1:
                    zones["J"] = self._unproject_to_3d(L_2d)
                    jk_split = self._split_by_depth(remainder_2d, p1, p2, w_dir, d_N)
                    if jk_split:
                        zones["I"] = self._unproject_to_3d(jk_split["front"])
                        zones["K"] = self._unproject_to_3d(jk_split["back"])
                    else:
                        zones["I"] = self._unproject_to_3d(remainder_2d)
                else:
                    zones["J"] = self._unproject_to_3d(L_2d)
                    zones["I"] = self._unproject_to_3d(remainder_2d)

            all_zones.append({
                "edge_index": edge_index,
                "zones": zones
            })

        return all_zones if all_zones else None

    def _split_turbulence_corners(
        self,
        turb_poly_2d: np.ndarray,
        edge_dir: np.ndarray,
        p1: np.ndarray,
        p2: np.ndarray,
        e_4: float
    ) -> Optional[Dict[str, np.ndarray]]:
        """e/10'luk türbülans poligonunu e/4 offset ile 3 parçaya böler."""
        perp_dir = np.array([-edge_dir[1], edge_dir[0]])

        # p1 köşesinden e/4
        split1_p = p1 + edge_dir * e_4
        p1_line_a = split1_p - perp_dir * 100000.0
        p1_line_b = split1_p + perp_dir * 100000.0

        res1 = self._split_by_line_2d(turb_poly_2d, p1_line_a, p1_line_b)
        if res1 is None:
            return None

        partA, partB = res1
        cA = np.mean(partA[:-1] if np.allclose(partA[0], partA[-1]) else partA, axis=0)
        cB = np.mean(partB[:-1] if np.allclose(partB[0], partB[-1]) else partB, axis=0)

        if np.linalg.norm(cA - p1) < np.linalg.norm(cB - p1):
            p1_corner, remainder = partA, partB
        else:
            p1_corner, remainder = partB, partA

        # p2 köşesinden e/4
        split2_p = p2 - edge_dir * e_4
        p2_line_a = split2_p - perp_dir * 100000.0
        p2_line_b = split2_p + perp_dir * 100000.0

        res2 = self._split_by_line_2d(remainder, p2_line_a, p2_line_b)

        if res2 is not None:
            partC, partD = res2
            cC = np.mean(partC[:-1] if np.allclose(partC[0], partC[-1]) else partC, axis=0)
            cD = np.mean(partD[:-1] if np.allclose(partD[0], partD[-1]) else partD, axis=0)

            if np.linalg.norm(cC - p2) < np.linalg.norm(cD - p2):
                p2_corner, mid_region = partC, partD
            else:
                p2_corner, mid_region = partD, partC

            return {
                "corner1": p1_corner,
                "corner2": p2_corner,
                "mid": mid_region
            }
        else:
            return {
                "corner1": p1_corner,
                "corner2": None,
                "mid": remainder
            }

    def _split_by_depth(
        self,
        poly_2d: np.ndarray,
        p1: np.ndarray,
        p2: np.ndarray,
        w_dir: np.ndarray,
        depth: float
    ) -> Optional[Dict[str, np.ndarray]]:
        """Poligonu derinlemesine böler."""
        edge_vec = p2 - p1
        edge_norm = np.linalg.norm(edge_vec)
        if edge_norm < 1e-8:
            return None
            
        edge_dir = edge_vec / edge_norm

        depth_p1 = p1 + w_dir * depth
        depth_p2 = p2 + w_dir * depth

        line_p1_ext = depth_p1 - edge_dir * 1000000.0
        line_p2_ext = depth_p2 + edge_dir * 1000000.0

        res = self._split_by_line_2d(poly_2d, line_p1_ext, line_p2_ext)
        if res is not None:
            partA, partB = res
            c1 = np.mean(partA[:-1], axis=0)
            c2 = np.mean(partB[:-1], axis=0)

            edge_mid = (p1 + p2) / 2.0
            if np.linalg.norm(c1 - edge_mid) < np.linalg.norm(c2 - edge_mid):
                return {"front": partA, "back": partB}
            else:
                return {"front": partB, "back": partA}
        return None

    # ==================== TÜM BÖLGELER ====================
    
    def get_all_zones(self, w_vector: np.ndarray, e: float) -> Dict[str, np.ndarray]:
        """Yüzey tipine göre tüm bölgeleri hesaplar."""
        if self.surface_type == SurfaceType.WALL:
            return self.get_wall_zones(w_vector, e)
        else:
            # Çatı analizi
            all_roof_polygons = {}  # Gerçek uygulamada bu doldurulmalı
            self.analysis_(w_vector, all_roof_polygons)
            
            zones_list = self.split_by_w_offset(w_vector, e)
            
            if zones_list is None:
                return {"TUM": self.close_polygon(self.pts_3d)}
            
            all_zones = {}
            for zone_dict in zones_list:
                for zone_name, polygon in zone_dict["zones"].items():
                    all_zones[zone_name] = polygon
            
            return all_zones
            
    # ==================== EXPOSED EDGES (3D) ====================
        
    def exposed_edges(self, w: np.ndarray) -> List[Dict[str, Any]]:
        """
        Hem Duvar (WALL) hem Çatı (ROOF) elemanları için 3B uzayda
        rüzgara maruz kalan (exposed) kenarları tespit eder.
        """
        polygon = self.pts_3d
        if np.allclose(polygon[0], polygon[-1]):
            polygon = polygon[:-1]
            
        n = len(polygon)
        exposed_edge = []

        # 3B Rüzgarın geldiği yön (Wind From Vector)
        w_3d = np.asarray(w, dtype=float)
        w_norm = np.linalg.norm(w_3d)
        if w_norm < 1e-12:
            return []
        
        wind_from = -(w_3d / w_norm)
        surface_normal = self.normal_unit  # 3B yüzey birim normali

        for i in range(n):
            p1 = polygon[i]
            p2 = polygon[(i + 1) % n]

            edge_vec = p2 - p1
            edge_len = np.linalg.norm(edge_vec)

            if edge_len < 1e-12:
                continue

            edge_unit = edge_vec / edge_len

            # 1. 3B Kenar Dış Normali
            outward_normal_3d = np.cross(edge_unit, surface_normal)
            outward_normal_3d_len = np.linalg.norm(outward_normal_3d)

            if outward_normal_3d_len < 1e-12:
                continue
                
            outward_normal_3d /= outward_normal_3d_len

            # 2. Exposure Hesabı
            exposure = np.dot(outward_normal_3d, wind_from)

            # Kenarın rüzgar vektörü ile yaptığı açı
            cos_angle = np.clip(abs(np.dot(edge_unit, wind_from)), -1.0, 1.0)
            angle = np.degrees(np.arccos(cos_angle))

            tol = 1e-6

            if exposure > tol:
                exposed_edge.append({
                    "index": i,
                    "p1": p1,
                    "p2": p2,
                    "angle": angle,
                    "exposure": exposure,
                    "leading": False,
                    "shared": False
                })

        self.exposed_edge_list = exposed_edge
        return exposed_edge

    # ==================== LEADING EDGES (3D) ====================
    
    def find_local_leading_edges(self, wind: np.ndarray, tol: float = 1.0) -> List[Dict[str, Any]]:
        """Rüzgar yönüne göre en öndeki kenarları 3B uzayda bulur."""
        # Eğer exposed_edges henüz hesaplanmamışsa hesapla
        if not self.exposed_edge_list:
            self.exposed_edges(wind)
        
        exposed_edges = self.exposed_edge_list
        
        if not exposed_edges:
            return []

        w_3d = np.asarray(wind, dtype=float)
        w_norm = np.linalg.norm(w_3d)
        if w_norm < 1e-12:
            return []

        wind_from = -(w_3d / w_norm)

        candidates = []

        for edge in exposed_edges:
            p1 = np.asarray(edge["p1"], dtype=float)
            p2 = np.asarray(edge["p2"], dtype=float)

            # 3B Noktaların rüzgar geliş hattı üzerindeki izdüşüm mesafesi
            p1_pos = np.dot(p1, wind_from)
            p2_pos = np.dot(p2, wind_from)

            front_positions = sorted([p1_pos, p2_pos], reverse=True)

            candidates.append({
                **edge,
                "p1_front_position": p1_pos,
                "p2_front_position": p2_pos,
                "front_positions": front_positions,
            })

        if not candidates:
            return []

        # En öndeki pozisyonu bul
        best_positions = max(edge["front_positions"] for edge in candidates)

        def is_at_leading_position(edge):
            a = edge["front_positions"]
            b = best_positions
            return (abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol)

        leading_edges = []
        for idx_, edge in enumerate(candidates):
            exposed_edges[idx_]["leading"] = False
            if is_at_leading_position(edge):
                leading_edges.append(edge)
                exposed_edges[idx_]["leading"] = True

        self.exposed_edge_list = exposed_edges
        return leading_edges

    # ==================== GLOBAL LEADING EDGE ANALİZİ ====================
    
    def check_global_roof_leading_edge(
        self,
        candidate_edge: Dict,
        all_roof_polygons: Dict[str, np.ndarray],
        wind: np.ndarray,
        tol: float = 1e-6
    ) -> Dict:
        """Kenarın global leading edge olup olmadığını kontrol eder."""
        w_xy = np.asarray(wind[:2], dtype=float)
        wind_norm = np.linalg.norm(w_xy)

        if wind_norm < 1e-12:
            raise ValueError("Rüzgârın XY yönü sıfır olamaz.")

        w_xy /= wind_norm
        wind_from = -w_xy

        shared_with = []

        for polygon_name, polygon in all_roof_polygons.items():
            if polygon_name == self.polygon_name:
                continue

            for edge in polygon_edges(polygon):
                if same_edge(candidate_edge, edge, tol=tol):
                    shared_with.append({
                        "polygon": polygon_name,
                        "edge_index": edge["index"],
                        "p1": edge["p1"],
                        "p2": edge["p2"],
                    })

        if not shared_with:
            return {
                "status": "GLOBAL_LEADING",
                "shared": False,
                "shared_with": []
            }

        candidate_polygon = all_roof_polygons[self.polygon_name]
        candidate_centroid = polygon_centroid(candidate_polygon)
        candidate_position = np.dot(candidate_centroid[:2], wind_from)

        upstream_polygons = []

        for shared in shared_with:
            other_name = shared["polygon"]
            other_polygon = all_roof_polygons[other_name]
            other_centroid = polygon_centroid(other_polygon)
            other_position = np.dot(other_centroid[:2], wind_from)

            if other_position > candidate_position + tol:
                upstream_polygons.append({
                    "polygon": other_name,
                    "position": other_position,
                })

        if upstream_polygons:
            return {
                "status": "NOT_GLOBAL_LEADING",
                "shared": True,
                "shared_with": shared_with,
                "upstream_polygons": upstream_polygons,
            }

        return {
            "status": "GLOBAL_LEADING",
            "shared": True,
            "shared_with": shared_with,
            "upstream_polygons": [],
        }

    def find_leading_edge_neighbors(
        self,
        global_leading_edge: Dict,
        all_roof_polygons: Dict[str, np.ndarray],
        tol: float = 1e-6
    ) -> Dict:
        """GLOBAL LEADING EDGE'in iki uç noktasındaki komşu kenarları bulur."""
        p1 = np.asarray(global_leading_edge["p1"], dtype=float)
        p2 = np.asarray(global_leading_edge["p2"], dtype=float)

        own_edges = polygon_edges(all_roof_polygons[self.polygon_name])

        p1_neighbor = None
        p2_neighbor = None

        for edge in own_edges:
            if same_edge(edge, global_leading_edge, tol):
                continue

            e_p1 = np.asarray(edge["p1"], dtype=float)
            e_p2 = np.asarray(edge["p2"], dtype=float)

            uses_p1 = np.allclose(e_p1, p1, atol=tol) or np.allclose(e_p2, p1, atol=tol)
            uses_p2 = np.allclose(e_p1, p2, atol=tol) or np.allclose(e_p2, p2, atol=tol)

            if uses_p1:
                p1_neighbor = edge
            if uses_p2:
                p2_neighbor = edge

        p1_shared_with = []
        p2_shared_with = []

        for name, polygon in all_roof_polygons.items():
            if name == self.polygon_name:
                continue

            for edge in polygon_edges(polygon):
                if p1_neighbor is not None and same_edge(p1_neighbor, edge, tol):
                    p1_shared_with.append(name)
                if p2_neighbor is not None and same_edge(p2_neighbor, edge, tol):
                    p2_shared_with.append(name)

        return {
            "p1_neighbor": p1_neighbor,
            "p2_neighbor": p2_neighbor,
            "p1_shared": bool(p1_shared_with),
            "p2_shared": bool(p2_shared_with),
            "p1_shared_with": p1_shared_with,
            "p2_shared_with": p2_shared_with,
        }

    def roof_region_types_topological(
        self, 
        w: np.ndarray, 
        all_roof_polygons: Dict[str, np.ndarray]
    ) -> List[str]:
        """
        Gelişmiş kenar topolojisi (Exposed -> Local Leading -> Global Leading) 
        kullanılarak sıfır geometrik varsayım ile Eurocode bölge tespiti.
        """
        relation = self.analyze_wind_relation(w)
        
        gl_info = self.results.get("gl_leading_edge") or {}
        is_global_leading = gl_info.get("status") == "GLOBAL_LEADING"
        has_upstream = len(gl_info.get("upstream_polygons", [])) > 0
        
        neighbors_info = self.results.get("find_leading_edge_neighbors") or {}
        has_roof_neighbor = (
            neighbors_info.get("p1_shared", False) or 
            neighbors_info.get("p2_shared", False) or 
            has_upstream
        )
        has_shared_neighbors = self.results.get("shared_edge_neighbors", False)
        
        # Poligonun üçgen kalkan yüzey olup olmadığı tespiti (C3 gibi)
        is_triangular_hip = (len(self.coords) == 3)

        # -------------------------------------------------------------
        # 1. WINDWARD (Rüzgarı Karşılayan Yüzey)
        # -------------------------------------------------------------
        if relation == WindRelation.WINDWARD:
            self.results["cpe_lookup_theta"] = 0
            
            # Üst/mahya kenarında komşu yüzey varsa DUOPITCH, yoksa MONOPITCH
            if has_roof_neighbor or self.results.get("shared_edge_neighbors"):
                self.results["cpe_table"] = "DUOPITCH"
            else:
                self.results["cpe_table"] = "MONOPITCH"
                
            return ["F", "G", "H"]

        # -------------------------------------------------------------
        # 2. LEEWARD (Rüzgar Altı Yüzey)
        # -------------------------------------------------------------
        elif relation == WindRelation.LEEWARD:
            self.results["cpe_lookup_theta"] = 0
            
            # Önünde rüzgarı kesecek hiçbir çatı yoksa -> Monopitch theta=180
            if not has_upstream and not has_roof_neighbor:
                self.results["cpe_table"] = "MONOPITCH"
                self.results["cpe_lookup_theta"] = 180
                return ["F", "G", "H"]
            
            # Eğer rüzgar altındaki yüzey ÜÇGEN bir kırma yüzey ise -> HIPPED (I, J, K)
            if is_triangular_hip:
                self.results["cpe_table"] = "HIPPED"
                return ["I", "J", "K"]
            
            # Standart Beşik Rüzgar Altı Yüzeyi -> DUOPITCH (I, J)
            self.results["cpe_table"] = "DUOPITCH"
            return ["I", "J"]

        # -------------------------------------------------------------
        # 3. PARALLEL (Rüzgara Paralel Akış - theta = 90°)
        # -------------------------------------------------------------
        elif relation == WindRelation.PARALLEL:
            self.results["cpe_lookup_theta"] = 90
            
            # Monopitch Paralel Durumu (Komşusu olmayan tek çatı)
            if not has_roof_neighbor and not is_global_leading:
                self.results["cpe_table"] = "MONOPITCH"
                return ["F", "G", "H", "I"]

            # Kırma/Beşik Paralel Akış:
            # Akışı ilk karşılayan dış edge (Rüzgar başı)
            if is_global_leading:
                self.results["cpe_table"] = "DUOPITCH"
                if not has_shared_neighbors:
                    return ["Fu", "Fl", "G", "H"]
                return ["F", "G", "H"]

            # Eğer yüzey eğimli bir Kalkan Üçgen ise (C3 gibi) paralel akışta L, M, N alır
            if is_triangular_hip or (self.pitch > 5.0 and has_roof_neighbor and len(self.coords) == 3):
                self.results["cpe_table"] = "HIPPED"
                return ["L", "M", "N"]
            
            # Akış altı devam eden paralel beşik yüzeyleri
            self.results["cpe_table"] = "DUOPITCH"
            return ["I", "J"]

        return []