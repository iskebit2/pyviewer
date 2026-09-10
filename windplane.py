# windplane.py

import math
import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Tuple, Optional, Union, Any
from data.wind_data import ARAZI_KATEGORILERI, CPI_POSITIVE, CPI_NEGATIVE, RHO,K_I,C0, wall_cpe_table,MONOPITCH_CPE_DATA,DUOPITCH_CPE_DATA,HIPPED_CPE_DATA

EPS = 1.0e-9


class SurfaceType(Enum):
    WALL = "WALL"
    ROOF = "ROOF"
    nodata = ""


class WindRelation(Enum):
    WINDWARD = "WINDWARD"
    LEEWARD = "LEEWARD"
    PARALLEL = "PARALLEL"
    nodata = ""


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
        self.coords = pts
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
            "coords": pts,
            "zmin": float(np.min(pts[:, 2])),
            "zmax": float(np.max(pts[:, 2])),
            "wind_vector": None,
            "wind_relation": WindRelation.nodata,
            "edges": []
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
        
    def _edges(self, w: np.ndarray, all_roof_polygons= []) -> List[Dict[str, Any]]:
        """
        Hem Duvar (WALL) hem Çatı (ROOF) elemanları için 3B uzayda
        rüzgara maruz kalan (exposed) kenarları tespit eder.
        """
        polygon = self.pts_3d
        if np.allclose(polygon[0], polygon[-1]):
            polygon = polygon[:-1]
            
        n = len(polygon)
        shared_poly = []
    
        # 3B Rüzgarın geldiği yön (Wind From Vector)
        w_3d = np.asarray(w, dtype=float)
        w_norm = np.linalg.norm(w_3d)
        if w_norm < 1e-12:
            return []
        
        wind_from = -(w_3d / w_norm)
        surface_normal = self.normal_unit  # 3B yüzey birim normali

        self_polygon = polygon
        self_centroid = polygon_centroid(self_polygon)
        self_position = np.dot(self_centroid, wind_from)
        
        poly_edges= {}
        
        for i in range(n):
            
            p1 = polygon[i]
            p2 = polygon[(i + 1) % n]
    
            edge_vec = p2 - p1
            edge_len = np.linalg.norm(edge_vec)
    
            if edge_len < 1e-12:
                continue
    
            edge_unit = edge_vec / edge_len
    
            
            p1_pos = np.dot(p1, wind_from)
            p2_pos = np.dot(p2, wind_from)
    
            front_positions = sorted([p1_pos, p2_pos], reverse=True)
            
            
            outward_normal_3d = np.cross(edge_unit, surface_normal)
            outward_normal_3d_len = np.linalg.norm(outward_normal_3d)
    
            if outward_normal_3d_len < 1e-12:
                continue
                
            outward_normal_3d /= outward_normal_3d_len
    
            
            exposure = np.dot(outward_normal_3d, wind_from)
    
            # Kenarın rüzgar vektörü ile yaptığı açı
            cos_angle = np.clip(abs(np.dot(edge_unit, wind_from)), -1.0, 1.0)
            angle = np.degrees(np.arccos(cos_angle))
    
            tol = 1e-6
    
            
    
            poly_edges[i]= {
                    "p1": p1,
                    "p2": p2,
                    "angle": angle,
                    "exposed": exposure > tol,
                    "front_positions": front_positions,
                    "leading": False,
                    "shared": False
                }
    
        
    
        best_positions = max(edge["front_positions"] for edge in poly_edges.values())
    
        def is_at_leading_position(edge):
            a = edge["front_positions"]
            b = best_positions
            return (abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol)
        
        for edge in poly_edges.values():
            edge["leading"] = False
            shared_with= []

            if edge["exposed"]:
                if is_at_leading_position(edge):
                    edge["leading"] = True
                
                
            for polygon_name, polygon in all_roof_polygons.items():
                if polygon_name == self.polygon_name:
                    continue
                other_polygon = all_roof_polygons[polygon_name]
                other_centroid = polygon_centroid(other_polygon)
                other_position = np.dot(other_centroid, wind_from)
                    
                for other_edge in polygon_edges(polygon):
                    if same_edge(edge, other_edge, tol=tol):
                        shared_with.append({
                            "polygon": polygon_name,
                            "upstream": other_position > self_position + tol
                        })
                        
                edge["shared"] = shared_with
        
        
        return poly_edges
        
    def analysis_(self, w, building) -> None:
        """Tam çatı rüzgar analizini yapar."""
        
        all_roof_polygons= building.all_roof_polygons
        rel_ = self.analyze_wind_relation(w)
        self.results["wind_relation"] = rel_

        
        
        self.results["edges"] = self._edges(w, all_roof_polygons)
        self.results["any_shared"] = any([True for k in self.results["edges"].values() if k['shared']])
        self.results["global"] = any([True for k in self.results["edges"].values() if k['leading'] and not k['shared']])
        
        
        self.results["wind_vector"] = w

        if self.surface_type.value == "WALL":
            self.results["regions"] = self.calculate_wall_cpe_from_polygon(
                w,
                building.geometry
            )
        else:
            pass
            # self.results["roof_reg_type"] = self.roof_region_types_topological(w, all_roof_polygons)

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

    def _get_wall_local_system(self, poly_coords):
        """
        Düşey veya eğimli duvar poligonu için lokal 2D koordinat sistemi (u, v) kurar.
        u: Duvar taban çizgisi boyuncaki hat (Rüzgar yönü/uzunluk)
        v: Düşey eksen (Yükseklik)
        """
        # Taban ve tavan Z seviyelerini bul
        z_min = np.min(poly_coords[:, 2])
        z_max = np.max(poly_coords[:, 2])
        
        # Taban çizgisi üzerindeki ilk ve son 3D noktaları tespit et
        base_pts = poly_coords[np.abs(poly_coords[:, 2] - z_min) < 1e-3]
        if len(base_pts) < 2:
            base_pts = poly_coords # Fallback
            
        # u ekseni vektörü (XY düzlemindeki yön)
        p0 = base_pts[0]
        p1 = base_pts[-1]
        u_dir = p1[:2] - p0[:2]
        u_len = np.linalg.norm(u_dir)
        
        if u_len > 1e-6:
            u_dir = u_dir / u_len
        else:
            u_dir = np.array([1.0, 0.0]) # Fallback
            
        return {
            "origin_3d": p0,
            "u_dir": u_dir,
            "z_min": z_min,
            "z_max": z_max,
            "length": u_len
        }

    def _project_3d_to_local_2d(self, poly_coords, local_sys):
        """3D duvar koordinatlarını 2D (u, v) local parametrik alana taşır."""
        p0 = local_sys["origin_3d"]
        u_dir = local_sys["u_dir"]
        
        pts_2d = []
        for pt in poly_coords:
            # u: origin'den taban çizgisi boyunca olan mesafe
            vec_xy = pt[:2] - p0[:2]
            u = np.dot(vec_xy, u_dir)
            # v: Z yüksekliği
            v = pt[2]
            pts_2d.append([u, v])
            
        return np.array(pts_2d)

    def _unproject_local_2d_to_3d(self, pts_2d, local_sys):
        """2D (u, v) koordinatlarını tekrar gerçek 3D uzaya dönüştürür."""
        p0 = local_sys["origin_3d"]
        u_dir = local_sys["u_dir"]
        
        pts_3d = []
        for u, v in pts_2d:
            x = p0[0] + u * u_dir[0]
            y = p0[1] + u * u_dir[1]
            z = v
            pts_3d.append([x, y, z])
            
        return np.array(pts_3d)
    
    def calculate_wall_cpe_from_polygon(self, w_dir: List[float], building_geo: Dict[str, float]) -> Dict[str, Any]:
        poly_coords = np.array(self.coords)
        local_sys = self._get_wall_local_system(poly_coords)
        pts_2d = self._project_3d_to_local_2d(poly_coords, local_sys)
        
        relation = self.analyze_wind_relation(w_dir)
        self.results['wind_relation']= relation
        
        # Parametreleri building_geo dictionary'sinden güvenle al
        d_building = building_geo.get("d", local_sys["length"])
        e = building_geo.get("e", 2.0 * building_geo.get("h", 10.0))
        len_u = local_sys["length"]
        d = len_u if len_u > 1e-3 else d_building
    
        # Sadece bölge sınırlarını (u_start, u_end) tutan geçici sözlük
        zone_bounds = {}
    
        if relation == WindRelation.WINDWARD:  # PERPENDICULAR (D Bölgesi)
            zone_bounds["D"] = (0.0, len_u)
        elif relation == WindRelation.LEEWARD:  # PERPENDICULAR (E Bölgesi)
            zone_bounds["E"] = (0.0, len_u)
        else:  # PARALLEL (A, B, C Bölgeleri - TS EN 1991-1-4)
            if e >= 5.0 * d:
                zone_bounds["A"] = (0.0, round(d, 3))
            elif e > d:
                zone_bounds["A"] = (0.0, round(e / 5.0, 3))
                zone_bounds["B"] = (round(e / 5.0, 3), round(d, 3))
            else:
                zone_bounds["A"] = (0.0, round(e / 5.0, 3))
                zone_bounds["B"] = (round(e / 5.0, 3), round(4.0 * e / 5.0, 3))
                zone_bounds["C"] = (round(4.0 * e / 5.0, 3), round(d, 3))
    
        zones = {}
        current_poly_2d = pts_2d
    
        # 2D Local alanda dik kesit hatları ile poligon parçalama
        for z_code, (u_start, u_end) in zone_bounds.items():
            v_min, v_max = local_sys["z_min"] - 1.0, local_sys["z_max"] + 1.0
            
            sub_poly_2d = current_poly_2d
            
            # u_start sol sınırı kes
            if u_start > 1e-4:
                p1 = np.array([u_start, v_min], dtype=float)
                p2 = np.array([u_start, v_max], dtype=float)
                res = self._split_by_line_2d(sub_poly_2d, p1, p2)
                if res is not None:
                    _, sub_poly_2d = res  # Sağda kalan parça
        
            # u_end sağ sınırı kes
            if u_end < (len_u - 1e-4):
                p1 = np.array([u_end, v_min], dtype=float)
                p2 = np.array([u_end, v_max], dtype=float)
                res = self._split_by_line_2d(sub_poly_2d, p1, p2)
                if res is not None:
                    sub_poly_2d, current_poly_2d = res  # Solda kalan mevcut bölgenin, sağda kalan bir sonrakinin
        
            # 3D koordinatlara dönüştür
            if sub_poly_2d is not None and len(sub_poly_2d) >= 3:
                sub_poly_3d = self._unproject_local_2d_to_3d(sub_poly_2d, local_sys)
                cpe10, cpe1 = self.get_wall_cpe_values(z_code, building_geo)
                
                zones[z_code] = {
                    "cpe10": cpe10,
                    "cpe1": cpe1,
                    "polygon": np.round(sub_poly_3d, 4).tolist()
                }
        
        return zones

    def get_wall_cpe_values(self, zone_code: str, building_geo: Dict[str, float]) -> Tuple[float, float]:
        """
        TS EN 1991-1-4 Tablo 7.1'e göre h/d oranına bağlı lineer interpolasyon yaparak
        ilgili bölge (A, B, C, D, E) için cpe10 ve cpe1 değerlerini döndürür.
        """
        h = building_geo.get("h", 10.0)
        d = building_geo.get("d", 10.0)
        
        # h/d oranını hesapla
        h_d = h / d if d > 0 else 1.0
        
        table = wall_cpe_table
        
        # 1. Sınır Durumlar (Extrapolation engelleme)
        if h_d >= 5.0:
            return table[5.0][zone_code]["cpe10"], table[5.0][zone_code]["cpe1"]
        elif h_d <= 0.25:
            return table[0.25][zone_code]["cpe10"], table[0.25][zone_code]["cpe1"]
        
        # 2. İnterpolasyon Aralığının Tespiti
        if h_d > 1.0:
            h_d_low, h_d_high = 1.0, 5.0
        else:
            h_d_low, h_d_high = 0.25, 1.0
            
        cpe10_low = table[h_d_low][zone_code]["cpe10"]
        cpe10_high = table[h_d_high][zone_code]["cpe10"]
        
        cpe1_low = table[h_d_low][zone_code]["cpe1"]
        cpe1_high = table[h_d_high][zone_code]["cpe1"]
        
        # 3. Lineer İnterpolasyon Hesabı: y = y0 + (x - x0) * (y1 - y0) / (x1 - x0)
        t = (h_d - h_d_low) / (h_d_high - h_d_low)
        
        cpe10 = cpe10_low + t * (cpe10_high - cpe10_low)
        cpe1 = cpe1_low + t * (cpe1_high - cpe1_low)
        
        return round(cpe10, 3), round(cpe1, 3)

class BuildingWindEngine:
    

    def __init__(
        self, 
        points: Dict[str, Tuple[float, float, float]], 
        polygons: Dict[str, List[str]], 
        v_b0: float = 28.0, 
        terrain: str = "Kategori III",
        w_dir: List[float] = [1.0, 0.0, 0.0],
        scale_factor: float = 1000.0,
        rho: float = 1.25,
        ct: float = 1.0,
        kI: float = 1.0
    ):
        self.raw_points = points
        self.polygons = polygons
        self.v_b0 = float(v_b0)
        self.terrain = terrain
        self.w_dir = np.array(w_dir, dtype=float)
        self.scale_factor = float(scale_factor)
        self.rho = rho
        self.ct = ct
        self.kI = kI
        self.e= None
        self.all_roof_polygons = {}

        if self.terrain not in ARAZI_KATEGORILERI:
            raise ValueError(f"Geçersiz arazi kategorisi: {self.terrain}")
        
        self.z0 = ARAZI_KATEGORILERI[self.terrain]["z0"]
        self.zmin = ARAZI_KATEGORILERI[self.terrain]["zmin"]

        # 1. Noktaları ölçekle
        self.scaled_points = self._scale_points()
        
        # 2. Yüzeyleri analiz et (Duvar/Çatı ayrımı ve kotlar)
        self.surfaces = self._analyze_surfaces()
        
        # 3. Yüzeylerden gelen verilerle bina geometrisini bağla (Artık çakışma yok)
        self.geometry = self._calculate_building_geometry()
        
        # 4. Rüzgar parametrelerini (q_b, q_p) hesapla
        self._calculate_wind_parameters()

    def _scale_points(self) -> Dict[str, np.ndarray]:
        return {
            name: np.array(pt, dtype=float) / self.scale_factor 
            for name, pt in self.raw_points.items()
        }

    def _analyze_surfaces(self) -> Dict[str, Dict[str, Any]]:
        """Poligon bağımsız yüzey tipini ve kotlarını çıkarır."""
        surfaces = {}
        self.all_roof_polygons = {}
        for poly_name, pt_names in self.polygons.items():
            pts = np.array([self.scaled_points[pt] for pt in pt_names])
            surface_= WindPlane(pts, name=poly_name)
            if surface_.surface_type.value=="ROOF":
                self.all_roof_polygons[poly_name]= surface_.results['coords']


            surfaces[poly_name] = {
                "type": surface_.results['surface_type'],
                "pitch": surface_.results['pitch'],
                "relation": surface_.analyze_wind_relation(self.w_dir),
                "zmin": surface_.results['zmin'],
                "zmax": surface_.results['zmax'],
                "coords": surface_.results['coords']
            }
        return surfaces

    def _calculate_building_geometry(self) -> Dict[str, float]:
        """Hazır self.surfaces üzerinden saçak kotunu çekerek geometriyi tamamlar."""
        pts_matrix = np.array(list(self.scaled_points.values()))

        # Rüzgar eksenleri
        w_xy = self.w_dir[:2] / np.linalg.norm(self.w_dir[:2])
        v_vec = np.array([-w_xy[1], w_xy[0]])

        u_vals = [np.dot(pt[:2], w_xy) for pt in pts_matrix]
        v_vals = [np.dot(pt[:2], v_vec) for pt in pts_matrix]

        b = max(v_vals) - min(v_vals)
        d = max(u_vals) - min(u_vals)
        
        z_ground = float(min(pt[2] for pt in pts_matrix))
        z_ridge = float(max(pt[2] for pt in pts_matrix))

        # Saçak kotu tespiti (Duvarların maksimum z kotu)
        wall_z_maxs = [s["zmin"] for s in self.surfaces.values() if s["type"] == SurfaceType.ROOF]
        z_eaves = max(wall_z_maxs) if wall_z_maxs else z_ridge

        h_total = z_ridge - z_ground    # Mahya bazlı bina toplam yüksekliği
        h_eaves = z_eaves - z_ground    # Saçak yüksekliği
        e = min(b, 2.0 * h_total)
        self.e= e
        return {
            "b": b,
            "d": d,
            "h": h_total,
            "h_eaves": h_eaves,
            "z0_ground": z_ground,
            "z1_eaves": z_eaves,
            "z2_ridge": z_ridge,
            "e": e
        }

    def _calculate_wind_parameters(self):
        self.q_b = 0.5 * self.rho * (self.v_b0 ** 2) / 1000.0
        self.z_ref = max(self.geometry["z2_ridge"], self.zmin)

        self.kr = 0.19 * ((self.z0 / 0.05) ** 0.07)
        self.cr = self.kr * math.log(self.z_ref / self.z0)
        self.Iv = self.kI / math.log(self.z_ref / self.z0)

        self.ce = (self.cr * self.ct) ** 2 * (1.0 + 7.0 * self.Iv)
        self.q_p = self.ce * self.q_b

    def get_summary(self) -> Dict[str, Any]:
        """Tüm özet sonuçları temiz bir dict olarak döndürür."""
        return {
            "Geometri": self.geometry,
            "Rüzgar Parametreleri": {
                "q_b (kN/m²)": round(self.q_b, 3),
                "q_p (kN/m²)": round(self.q_p, 3),
                "c_e": round(self.ce, 3),
                "I_v": round(self.Iv, 3),
                "c_r": round(self.cr, 3),
                "k_r": round(self.kr, 3),
                "z_ref (m)": round(self.z_ref, 3),
            },
            "Arazi": {
                "Kategori": self.terrain,
                "z0 (m)": self.z0,
                "zmin (m)": self.zmin
            }
        }

    def get_polygon_coords(self, polygon_points, points, scale_=1000.0):
        """Poligon noktalarını koordinatlara dönüştürür ve ölçekler."""
        coords = []
        for pt_name in polygon_points:
            if pt_name in points:
                pt = points[pt_name]
                coords.append([pt[0] / scale_, pt[1] / scale_, pt[2] / scale_])
            else:
                raise ValueError(f"Nokta '{pt_name}' bulunamadı!")
        return np.array(coords)    