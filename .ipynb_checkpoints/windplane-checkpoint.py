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

def same_axis_xy(
    edge1: dict,
    edge2: dict,
    angle_tol: float = 2.0,
    distance_tol: float = 1e-6
) -> bool:

    d1 = edge1["direction_xy"]
    d2 = edge2["direction_xy"]

    if d1 is None or d2 is None:
        return False

    # 1. Doğrultular paralel mi?
    dot = np.clip(abs(np.dot(d1, d2)), -1.0, 1.0)
    angle = np.degrees(np.arccos(dot))

    if angle > angle_tol:
        return False

    # 2. Aynı aks üzerindeler mi?
    p1 = edge1["p1"][:2]
    q1 = edge2["p1"][:2]

    # d1'e dik birim vektör
    normal = np.array([-d1[1], d1[0]])

    distance = abs(np.dot(q1 - p1, normal))

    return distance <= distance_tol

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
        self.centroid = polygon_centroid(self.pts_3d)
        self.pitch: float = self._compute_pitch()
        self.surface_type: SurfaceType = SurfaceType.ROOF if self.pitch <= 75.0 else SurfaceType.WALL
        self.proj_info = self._get_best_projection_plane()
        self.angle = self._compute_angle()
        self.exposed_edge_list = []
        self.edges = self._build_edges()
        self.global_leading = False

        self.properties = {
            "name": self.polygon_name,
            "polygon": self.pts_3d,
            "surface_type": self.surface_type,
            "angle": self.angle,
            "pitch": self.pitch,
            "coords": pts,
            "zmin": float(np.min(pts[:, 2])),
            "zmax": float(np.max(pts[:, 2])),
            "wind_vector": None,
            "wind_relation": WindRelation.nodata,
            "global_leading": None
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

    def _compute_angle(self) -> float:
        if self.pitch < 1e-10:
            return 0.0
        nx, ny, nz = self.normal_unit
        if self.pitch >= 90.0 - 1e-10:
            return float(np.degrees(np.arctan2(ny, nx)))
        horiz_len = np.hypot(nx, ny)
        if horiz_len < 1e-12:
            return 0.0
        sign = np.sign(ny) if abs(ny) > abs(nx) else np.sign(nx)     
        return float(sign * self.pitch)

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

    def _build_edges(self) -> dict:
        edges = {}

        for i in range(self.n_pts):
            p1 = self.pts_3d[i]
            p2 = self.pts_3d[(i + 1) % self.n_pts]

            vector = p2 - p1
            length = np.linalg.norm(vector)

            if length < 1e-12:
                continue

            unit_vector = vector / length

            # XY izdüşümü
            vector_xy = vector[:2]
            length_xy = np.linalg.norm(vector_xy)

            if length_xy < 1e-12:
                direction_xy = None
            else:
                direction_xy = vector_xy / length_xy

            edges[i] = {
                "p1": p1.copy(),
                "p2": p2.copy(),

                # 3B geometri
                "vector": vector.copy(),
                "length": float(length),
                "unit_vector": unit_vector.copy(),

                # XY izdüşümü
                "vector_xy": vector_xy.copy(),
                "length_xy": float(length_xy),
                "direction_xy": (
                    direction_xy.copy()
                    if direction_xy is not None
                    else None
                ),
            }

        return edges
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
        
    def _edges(self, w: np.ndarray, building= None) -> List[Dict[str, Any]]:
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
        tol = 1e-6

        self_position = np.dot(self.centroid, wind_from)

        # ---------------------------------------------------------
        # 1. Kendi kenarlarının rüzgar geometrisini hesapla
        # ---------------------------------------------------------
        poly_edges= {}
        
        for edge_id, base_edge in self.edges.items():
            
            p1 = base_edge["p1"]
            p2 = base_edge["p2"]
            edge_unit = base_edge["unit_vector"]
    
            
            p1_pos = np.dot(p1, wind_from)
            p2_pos = np.dot(p2, wind_from)
    
            front_positions = sorted([p1_pos, p2_pos], reverse=True)
            outward_normal = np.cross(edge_unit, surface_normal)
            outward_normal_len = np.linalg.norm(outward_normal)
    
            if outward_normal_len < 1e-12:
                continue
                
            outward_normal /= outward_normal_len
            
            exposure = np.dot(outward_normal, wind_from)
    
            # Kenarın rüzgar vektörü ile yaptığı açı
            cos_angle = np.clip(abs(np.dot(edge_unit, wind_from)), -1.0, 1.0)
            angle = np.degrees(np.arccos(cos_angle))
    
            poly_edges[edge_id]= {
                    **base_edge,
                    "front_positions": front_positions,
                    "angle": angle,
                    "exposed": exposure > tol,
                    "leading": False,
                    "shared": [],
                    "same_axis": []
                }
    
        
        if not poly_edges:
            return {}
        
        # ---------------------------------------------------------
        # 2. Leading kenarları bul
        # ---------------------------------------------------------

        best_positions = max(edge["front_positions"] for edge in poly_edges.values())
    
        
        for edge in poly_edges.values():
            if not edge["exposed"]:
                continue

            a = edge["front_positions"]

            if (
                abs(a[0] - best_positions[0]) <= tol
                and
                abs(a[1] - best_positions[1]) <= tol
            ):
                edge["leading"] = True

        self._update_edges(poly_edges)

        # ---------------------------------------------------------
        # 3. Diğer çatılarla ortak kenarları bul
        # ---------------------------------------------------------

        if building is not None:

            for polygon_name, surface in building.surfaces_items.items():
                if polygon_name == self.polygon_name:
                    continue
                if not surface.surface_type.value=="ROOF":
                    continue
                
                other_position = np.dot(surface.centroid, wind_from)

                for edge_id, edge in self.edges.items():

                    for other_id, other_edge in surface.edges.items():
                        if same_axis_xy(edge, other_edge):
                            edge["same_axis"].append({
                                        "surface": polygon_name,
                                        "surface_edge": other_id,
                                        "surface_angle": surface.angle,
                                        "direction_xy": other_edge["direction_xy"],
                                        "same_edge": same_edge(edge, other_edge)
                                    })
                        else:
                            continue

                        if same_edge(edge, other_edge, tol=tol):

                            edge["shared"].append({
                                "surface": polygon_name,
                                "surface_edge": other_id,
                                "surface_angle": surface.angle,
                                "upstream":
                                    other_position >
                                    self_position + tol
                            })
        
        
        return poly_edges
    
    def _update_edges(self, new_edges: dict):
        for edge_id, data in new_edges.items():
            if edge_id in self.edges:
                self.edges[edge_id].update(data)
            else:
                self.edges[edge_id] = data.copy()
    
    def analysis_(self, w, building) -> None:
        """Tam çatı rüzgar analizini yapar."""
        
        
        rel_ = self.analyze_wind_relation(w)
        _edges = self._edges(w, building)
        self._update_edges(_edges)

        self.properties["wind_relation"] = rel_        
        self.properties["any_shared"] = any([True for k in self.edges.values() if k['shared']])
        # self.properties["global"] = any([True for k in self.edges.values() if k['leading'] and not k['shared']])
        
        # print("debug:","analysis_","wind_relation",self.properties["wind_relation"])
        self.properties["wind_vector"] = w
        self.compute_surface_topological_properties(building.surfaces_items.values())
        if self.surface_type.value == "WALL":
            self.properties["regions"] = self.calculate_wall_cpe_from_polygon(
                w,
                building.geometry
            )
        else:
            pass
            # self.results["roof_reg_type"] = self.roof_region_types_topological(w, all_roof_polygons)

    def compute_surface_topological_properties(self, surfaces_items):
        
        for surface in surfaces_items:
            props = surface.properties

            # 1. Mahya Komşuluğu Kontrolü
            has_ridge = getattr(surface, "has_ridge_neighbor", False)
            if not has_ridge:
                has_ridge = props.get("has_ridge_neighbor", False)
            props["has_ridge_neighbor"] = bool(has_ridge)

            # 2. Üçgen / Trapez Geometri Kontrolü
            # Yüzeyin köşe/kenar sayısına göre geometri tespiti
            edges_count = len(getattr(surface, "edges", {}))
            vertices_count = len(getattr(surface, "vertices", []))
            
            # 3 veya 4 kenarlı/köşeli yüzeyler (Kalkan veya Kırma çatı uç yüzeyleri)
            is_hipped_shape = (edges_count in [3, 4]) or (vertices_count in [3, 4])
            props["is_triangular_or_trapezoidal"] = is_hipped_shape

            # 3. Kalkan Yüzeyi (Gable Side) Kontrolü
            w = getattr(surface, "wind_vector", None)
            if w is None:
                w = props.get("wind_vector", None)

            if w is None:
                w_vec = np.array([1.0, 0.0, 0.0])
            else:
                w_vec = np.array(w, dtype=float)

            w_len = np.linalg.norm(w_vec)
            is_gable = False

            if w_len > 1e-12:
                w_norm = w_vec / w_len
                rel = getattr(surface.wind_relation, "name", str(surface.wind_relation))

                if "PARALLEL" in rel:
                    for edge in getattr(surface, "edges", {}).values():
                        if isinstance(edge, dict) and edge.get("exposed", False):
                            edge_vec = np.array(edge.get("vector", [0, 0, 0]))
                            e_len = np.linalg.norm(edge_vec)
                            if e_len > 1e-3:
                                edge_dir = edge_vec / e_len
                                if abs(np.dot(edge_dir, w_norm)) < 0.2:
                                    is_gable = True
                                    break

            props["is_gable_side"] = is_gable
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
        self.properties['wind_relation']= relation
        
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
        self.surfaces_items= {}
        self.all_roof_polygons = {}
        for poly_name, pt_names in self.polygons.items():
            pts = np.array([self.scaled_points[pt] for pt in pt_names])
            surface_= WindPlane(pts, name=poly_name)
            self.surfaces_items[poly_name] = surface_
            if surface_.surface_type.value=="ROOF":
                self.all_roof_polygons[poly_name]= surface_.properties['coords']


            surfaces[poly_name] = {
                "type": surface_.properties['surface_type'],
                "pitch": surface_.properties['pitch'],
                "relation": surface_.analyze_wind_relation(self.w_dir),
                "zmin": surface_.properties['zmin'],
                "zmax": surface_.properties['zmax'],
                "coords": surface_.properties['coords']
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

    def analysis_all_roof_wind(self, w):
        w = np.array(w, dtype=float)
        w_len = np.linalg.norm(w)
        if w_len < 1e-12:
            return
        w_norm = w / w_len

        roof_surfaces = {}
        for surface_name, surface in self.surfaces_items.items():
            if getattr(surface.surface_type, "value", surface.surface_type) == "ROOF":
                surface.analysis_(w, self)
                surface.global_leading = False
                surface.properties["global_leading"] = False
                roof_surfaces[surface_name] = surface
                # print("debug:","analysis_all_roof_wind","wind_relation",surface.properties["wind_relation"])
        if not roof_surfaces:
            return

        # 1. Aşama: Bütün binalardaki exposed kenarların EN ÖN noktalarını kıyasla,
        # küresel rüzgarüstü sınır koordinatını (min_global_pos) bul.
        global_min_pos = float("inf")
        
        for surface in roof_surfaces.values():
            for edge in surface.edges.values():
                if not edge.get("exposed", False):
                    continue
                
                p1_pos = np.dot(np.array(edge["p1"]), w_norm)
                p2_pos = np.dot(np.array(edge["p2"]), w_norm)
                
                # Senin metodun: Sıralı liste [ön_nokta, arka_nokta]
                front_positions = sorted([p1_pos, p2_pos])  # min değer rüzgarda en öndedir
                
                if front_positions[0] < global_min_pos:
                    global_min_pos = front_positions[0]

        tol = 1e-4

        # 2. Aşama: Hem front_positions[0] hem de front_positions[1] aynı anda
        # en ön hizada olan kenarı barındıran yüzeyi global_leading yap.
        for surface_name, surface in roof_surfaces.items():
            is_leading = False
            
            for edge in surface.edges.values():
                if not edge.get("exposed", False):
                    continue

                p1_pos = np.dot(np.array(edge["p1"]), w_norm)
                p2_pos = np.dot(np.array(edge["p2"]), w_norm)
                
                # front_positions[0]: en ön nokta, front_positions[1]: en arka nokta
                front_positions = sorted([p1_pos, p2_pos])

                # ŞART: Kenarın SADECE ilk ucu değil, İKİNCİ UCU da (front_positions[1]) 
                # en ön hatta mı? (Yani kenar boydan boya ön cephede mi?)
                is_full_edge_at_front = (
                    abs(front_positions[0] - global_min_pos) <= tol and
                    abs(front_positions[1] - global_min_pos) <= tol
                )

                if is_full_edge_at_front:
                    # Nokta temaslarını elemek için kenar boyu kontrolü
                    edge_len = np.linalg.norm(np.array(edge["p2"]) - np.array(edge["p1"]))
                    if edge_len > 1e-2:
                        is_leading = True
                        break

            if is_leading:
                surface.global_leading = True
                surface.properties["global_leading"] = True



def dict_tree(data, indent=""):
    lines = []

    items = list(data.items())

    for i, (key, value) in enumerate(items):
        last = i == len(items) - 1

        branch = "└── " if last else "├── "
        lines.append(f"{indent}{branch}{key}")

        if isinstance(value, dict):
            new_indent = indent + ("    " if last else "│   ")
            lines.append(dict_tree(value, new_indent))

        else:
            # Yukarıdaki key satırını value ile birleştir
            lines[-1] = f"{indent}{branch}{key} : {value}"

    return "\n".join(lines)

import numpy as np

def compute_surface_topological_properties(surface, all_surfaces):
    """
    Mevcut surface ve edge verilerini kullanarak:
    - has_ridge_neighbor
    - is_triangular_or_trapezoidal
    - is_gable_side
    özelliklerini dinamik olarak türetir ve surface.properties içine yazar.
    """
    
    # -------------------------------------------------------------------------
    # A) is_triangular_or_trapezoidal (Geometri Tipi Kontrolü)
    # -------------------------------------------------------------------------
    # Polygon köşe sayısı (3 = Üçgen, 4 = Dörtgen/Trapezoid)
    num_vertices = len(surface.properties.get("coords", []))
    if num_vertices == 0 and "polygon" in surface.properties:
        # Shapely polygon kullanılıyorsa:
        num_vertices = len(surface.properties["polygon"].exterior.coords) - 1
        
    # Kılavuzlarda Kırma Çatı (Hipped) kalkan yüzeyleri 3 veya 4 köşeli (trapez) olur
    surface.properties["is_triangular_or_trapezoidal"] = num_vertices in [3, 4]

    # -------------------------------------------------------------------------
    # B) has_ridge_neighbor (Mahyada Başka Çatı Yüzeyi İle Komşuluk Var mı?)
    # -------------------------------------------------------------------------
    # Yüzeyin zmax kotundaki kenarlarını bul ve bunların shared (paylaşılan)
    # ve diğer bir ROOF yüzeyine ait olup olmadığını kontrol et.
    zmax = surface.properties.get("zmax", -float("inf"))
    tol = 1e-3
    has_ridge = False

    for edge in surface.edges.values():
        p1_z = edge["p1"][2]
        p2_z = edge["p2"][2]
        
        # Kenar mahya kotunda mı (zmax civarında)?
        if abs(p1_z - zmax) <= tol and abs(p2_z - zmax) <= tol:
            # Kenar başka bir yüzeyle paylaşıyor mu?
            if edge.get("shared", False):
                # Komşu yüzeyin çatı (ROOF) olup olmadığını doğrula
                for other_name, other_s in all_surfaces.items():
                    if other_name == surface.properties["name"]:
                        continue
                    if getattr(other_s.surface_type, "value", other_s.surface_type) == "ROOF":
                        # Kenar bu çatı yüzeyinde de var mı?
                        for o_edge in other_s.edges.values():
                            if o_edge.get("shared", False):
                                # p1-p2 çakışması kontrolü
                                dist1 = np.linalg.norm(np.array(edge["p1"]) - np.array(o_edge["p1"])) + \
                                        np.linalg.norm(np.array(edge["p2"]) - np.array(o_edge["p2"]))
                                dist2 = np.linalg.norm(np.array(edge["p1"]) - np.array(o_edge["p2"])) + \
                                        np.linalg.norm(np.array(edge["p2"]) - np.array(o_edge["p1"]))
                                if dist1 < tol or dist2 < tol:
                                    has_ridge = True
                                    break
                    if has_ridge:
                        break

    surface.properties["has_ridge_neighbor"] = has_ridge

    # -------------------------------------------------------------------------
    # C) is_gable_side (Kalkan Duvar Tarafında / Rüzgara Paralel Yan Yüzey mi?)
    # -------------------------------------------------------------------------
    # Yüzey rüzgara PARALLEL ise ve dışa açık (exposed) kenarları rüzgara paralel uzanıyorsa 
    # veya kalkan duvar hizasındaki yan yüzey sınırını oluşturuyorsa:
    w = getattr(surface, "wind_vector", None)
    if w is None:
        w = surface.properties.get("wind_vector", None)

    # Eğer w hâlâ None ise veya dönüştürülemiyorsa işlemi atla/varsayılan al
    if w is None:
        w = np.array([1.0, 0.0, 0.0])
    else:
        w = np.array(w, dtype=float)

    w_len = np.linalg.norm(w)
    is_gable = False

    if w_len > 1e-12:
        w_norm = w / w_len
        
        rel = surface.properties.get("wind_relation", None)
        
        
        

        if rel.value == "PARALLEL":
            # Yüzey rüzgara paralelse ve exposed olan kenarı rüzgar aksına dik uzanarak ön hattı kapatıyorsa
            for edge in surface.edges.values():
                if edge.get("exposed", False):
                    edge_vec = np.array(edge["vector"])
                    e_len = np.linalg.norm(edge_vec)
                    if e_len > 1e-3:
                        edge_dir = edge_vec / e_len
                        # Kenar rüzgara dik mi? (iç çarpım ~ 0)
                        if abs(np.dot(edge_dir, w_norm)) < 0.2:
                            is_gable = True
                            break

    surface.properties["is_gable_side"] = is_gable

def get_cpe_table_for_surface(surface):
    props = surface.properties
    rel = props.get("wind_relation", None)
    if rel is None:
        return
    is_leading = surface.global_leading if hasattr(surface, "global_leading") else props.get("global_leading", False)
    
    has_ridge = props.get("has_ridge_neighbor", False)
    is_hipped_shape = props.get("is_triangular_or_trapezoidal", False)
    is_gable = props.get("is_gable_side", False)

    print("debug:","get_cpe_table_for_surface", f"rel:{rel}, is_leading:{is_leading}, has_ridge:{has_ridge}, is_hipped_shape: {is_hipped_shape}, is_gable: {is_gable}")

    # 1. RÜZGARÜSTÜ YÜZEYLER (WINDWARD)
    if rel == "WINDWARD":
        # Mahyada komşusu yoksa VE üçgen/trapez geometrideyse -> Kırma çatı rüzgarüstü yüzeyi
        if not has_ridge and is_hipped_shape:
            return "HIPPED_CPE_DATA", 0
        
        # Mahyası olmayan tekil eğim -> Tek eğimli rüzgarüstü
        if not has_ridge:
            return "MONOPITCH_CPE_DATA", 0
            
        # Standart çift eğimli rüzgarüstü
        return "DUOPITCH_CPE_DATA", 0

    # 2. RÜZGARALTI YÜZEYLER (LEEWARD)
    elif rel == "LEEWARD":
        if has_ridge:
            # Üçgen/Trapez rüzgaraltı yüzeyi (Kırma çatı kalkanı)
            if is_hipped_shape:
                return "HIPPED_CPE_DATA", 0
            return "DUOPITCH_CPE_DATA", 0
        else:
            # Mahyada komşu yoksa: Kırma çatı rüzgaraltı mı yoksa Monopitch rüzgaraltı mı?
            if is_hipped_shape:
                return "HIPPED_CPE_DATA", 0
            return "MONOPITCH_CPE_DATA", 180

    # 3. RÜZGARA PARALEL YÜZEYLER (PARALLEL)
    elif rel == "PARALLEL":
        # Rüzgardan ilk nasibini alan yan yüzeyler / kalkanlar:
        # Eğer üçgensel/trapez kalkan yüzeyi paralel rüzgar alıyorsa -> HIPPED 0°
        if is_hipped_shape and not has_ridge:
            return "HIPPED_CPE_DATA", 0
            
        # Çift eğimli çatının yan yüzeyleri rüzgara paralelse (mahya rüzgarları) -> DUOPITCH 90°
        return "DUOPITCH_CPE_DATA", 90

    return "DUOPITCH_CPE_DATA", 0

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

    building= BuildingWindEngine(points=points, polygons=polygons, scale_factor=1000)
    
        
                

    info= dict_tree(building.geometry)
    
    print("\nbuilding.geometry:\n", info)

    wind_parameters= building.get_summary()
    print("\nwind_parameters:\n", dict_tree(wind_parameters))

    for w in [[1,0,0],[0,1,0], [-1,0,0],[0,-1,0]]:
    # for w in [[1,0,0]]:
        print(f"Wind vector: {w}")
        building.analysis_all_roof_wind(w)

        
        for plane_name, plane1 in building.surfaces_items.items():
            
            
            if plane_name in ["C1","C2","C3"]:
                
                
                print([f"{kk}: {plane1.properties.get(kk)}" for kk in ['name','surface_type','angle', 'pitch','wind_vector','wind_relation','global_leading','any_shared',"has_ridge_neighbor", "is_gable_side", "is_triangular_or_trapezoidal"]])
                compute_surface_topological_properties(plane1, building.surfaces_items)
                # info= dict_tree(plane1.properties)
                aa= get_cpe_table_for_surface(plane1)
                print(f"cpe_table_for_surface: {aa}")
    # info= dict_tree(plane1.edges)
    # print("\nplane1.edges:\n", info)

    # for k,v in building.surfaces_items.items():
    #     info= dict_tree(v.properties)
            
    #     print(k,"\n", info)

    