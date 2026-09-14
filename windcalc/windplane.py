# windplane.py

from data.wind_data import ARAZI_KATEGORILERI, CPI_POSITIVE, CPI_NEGATIVE, RHO,K_I,C0, wall_cpe_table,MONOPITCH_CPE_DATA,DUOPITCH_CPE_DATA,HIPPED_CPE_DATA
from .edge_analyzer import EdgeAnalyzer
from .edge import Edge
import math
import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Tuple, Optional, Union, Any

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

        if len(pts) > 1 and np.allclose(
            pts[0], pts[-1], atol=1e-8
        ):
            pts = pts[:-1]

        if len(pts) < 3:
            raise ValueError("Poligon en az 3 nokta içermelidir.")

        self.polygon_name = name

        # Açık 3B koordinatlar
        self.coords = pts

        # Kapalı 3B polygon
        self.pts_3d: np.ndarray = self.close_polygon(pts)

        self.n_pts: int = len(pts)

        # Geometrik özellikler
        self.normal, self.normal_unit = self._compute_normal()
        self.centroid = polygon_centroid(self.pts_3d)
        self.pitch: float = self._compute_pitch()

        self.surface_type: SurfaceType = (
            SurfaceType.ROOF
            if self.pitch <= 75.0
            else SurfaceType.WALL
        )

        # En uygun projeksiyon düzlemi
        self.proj_info = self._get_best_projection_plane()

        # 2B projeksiyon
        self.pts_2d: np.ndarray = self._project_to_2d()

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
            "coords": self.coords,
            "pts_2d": self.pts_2d,
            "zmin": float(np.min(pts[:, 2])),
            "zmax": float(np.max(pts[:, 2])),
            "wind_vector": None,
            "wind_relation": WindRelation.nodata,
            "global_leading": None
        }

    def _project_to_2d(self) -> np.ndarray:
        """
        3B polygonu, yüzey için seçilmiş en uygun
        projeksiyon düzlemine taşır.

        XY -> x,y
        XZ -> x,z
        YZ -> y,z
        """

        _, axes, _ = self.proj_info

        return self.coords[:, axes]

    @staticmethod
    def close_polygon(polygon: np.ndarray, tol: float = 1e-8) -> np.ndarray:
        """Poligonu kapatır"""
        polygon = np.asarray(polygon, dtype=float)
        if len(polygon) == 0:
            return polygon
        if not np.allclose(polygon[0], polygon[-1], atol=tol):
            polygon = np.vstack([polygon, polygon[0]])
        return polygon

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
    
    def _unproject_2d_to_3d(self, pts_2d):
        pts_2d = np.asarray(pts_2d, dtype=float)

        _, axes, fixed_axis = self.proj_info

        pts_3d = np.zeros((len(pts_2d), 3), dtype=float)

        pts_3d[:, axes[0]] = pts_2d[:, 0]
        pts_3d[:, axes[1]] = pts_2d[:, 1]

        # Düzlemin gerçek konumundan sabit koordinatı bul.
        pts_3d[:, fixed_axis] = self.coords[0, fixed_axis]

        return pts_3d
    
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
        
        polygon = np.asarray(self.pts_3d, dtype=float)

        if len(polygon) < 3:
            return "DEGENERATE"

        if np.allclose(polygon[0], polygon[-1]):
            polygon = polygon[:-1]

        if len(polygon) < 3:
            return "DEGENERATE"

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

    def _build_edges(self) -> Dict[int, Edge]:
        edges = {}
        for i in range(self.n_pts):
            p1 = self.pts_3d[i]
            p2 = self.pts_3d[(i + 1) % self.n_pts]
            try:
                edges[i] = Edge.from_points(i, p1, p2)
            except ValueError:
                continue
        return edges

    def get_upslope_vector_xy(self) -> Optional[np.ndarray]:
        """
        Poligonun CCW/CW yapısından bağımsız olarak, 
        Z yüksekliğinin arttığı (tırmanma) yönün XY projeksiyonunu döner.
        """
        nx, ny, nz = self.normal_unit
        
        # Tam dikey duvar veya dümdüz çatı
        if abs(nz) < 1e-4 or abs(nz) > 0.9999:
            return None

        # Z'nin artış gösterdiği XY gradyan yönü: (-nx/nz, -ny/nz)
        slope_xy = -np.array([nx / nz, ny / nz], dtype=float)
        norm = np.linalg.norm(slope_xy)
        
        return slope_xy / norm if norm > 1e-12 else None

    def analyze_wind_relation(self, w_vector: np.ndarray, angle_tol_deg: float = 5.0) -> WindRelation:
        # 1. Rüzgar yatay birim vektörü
        w_xy = np.array(w_vector[:2], dtype=float)
        w_norm = np.linalg.norm(w_xy)
        if w_norm < 1e-12:
            raise ValueError("Rüzgar vektörünün yatay bileşeni sıfır olamaz.")
        w_xy /= w_norm

        # 2. DUVAR HESABI
        if self.surface_type == SurfaceType.WALL:
            n_xy = np.array(self.normal_unit[:2], dtype=float)
            n_norm = np.linalg.norm(n_xy)
            if n_norm > 1e-12:
                n_xy /= n_norm
                # Dış normal ile rüzgar karşı karşıya geliyorsa (dot < 0) WINDWARD'dır
                dot = np.dot(n_xy, w_xy)
                tol_sin = np.sin(np.radians(angle_tol_deg))
                if dot < -tol_sin:
                    return WindRelation.WINDWARD
                elif dot > tol_sin:
                    return WindRelation.LEEWARD
            return WindRelation.PARALLEL

        # 3. ÇATI (ROOF) HESABI
        upslope_xy = self.get_upslope_vector_xy()

        if upslope_xy is None:
            return WindRelation.PARALLEL

        # Rüzgar yönü ile tırmanış yönünün iç çarpımı
        dot = np.dot(upslope_xy, w_xy)
        tol_cos = np.sin(np.radians(angle_tol_deg))

        # C2 Örneği Kontrolü:
        # Tırmanış yönü (upslope_xy) = [0, -1]  (Y=4'teki Z=5 yüksekliğine doğru)
        # Rüzgar (w_xy)             = [0, -1]  (Y ekseninde eksiye doğru esiyor)
        # dot = 1.0 (Rüzgar yüksek noktaya doğru esiyor -> Yüzeye vuruyor)

        if dot > tol_cos:
            return WindRelation.WINDWARD
        elif dot < -tol_cos:
            return WindRelation.LEEWARD
        else:
            return WindRelation.PARALLEL
        
    def _analyze_edges(self, w, building=None) -> Dict[int, Edge]:
        is_ccw = (self.polygon_direction_xy() == "CCW")
        rel = self.analyze_wind_relation(w)

        analyzer = EdgeAnalyzer(
            edges=self.edges,
            surface_normal=self.normal_unit,
            is_ccw=is_ccw,
            wind_relation=rel.value,   # "WINDWARD" / "LEEWARD" / "PARALLEL"
            tol=1e-6,
        )
        return analyzer.analyze(
            wind_vector=w,
            building=building,
            current_surface_name=self.polygon_name,
        )

    def analysis_(self, w, building) -> None:
        rel_ = self.analyze_wind_relation(w)
        self.wind_relation = rel_

        self.edges = self._analyze_edges(w, building)

        self.properties["polygon_direction_xy"] = self.polygon_direction_xy()
        self.properties["wind_relation"] = rel_
        self.properties["wind_vector"] = w
        self.properties["any_shared"] = any(e.shared for e in self.edges.values())

        
        
    