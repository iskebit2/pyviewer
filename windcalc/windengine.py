# windengine.py
"""
BuildingWindEngine
==================
Bina rüzgar analizi motoru (TS EN 1991-1-4).

Bu modül, daha önce ayrı dosyalarda bulunan:
  - BuildingWindEngine (geometri + rüzgar parametreleri)
  - Zone bölme / kırpma yardımcıları (_split_by_line_2d, _clip_line_to_polygon_2d, ...)
  - _get_roof_zones, _get_wall_zones, get_definition_regions

fonksiyonlarını tek bir sınıf çatısı altında birleştirir.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from windcalc.zone import Zone, TOL, EPS, ARAZI_KATEGORILERI
from windcalc.windplane import WindPlane, SurfaceType


# ================================================================
# Geometri yardımcıları (modül seviyesinde, saf fonksiyonlar)
# ================================================================

def _close_polygon(polygon: np.ndarray, tol: float = TOL) -> np.ndarray:
    """Poligonu kapatır (ilk nokta == son nokta)."""
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
    """İki katlı işaretli alan (shoelace)."""
    poly = np.asarray(poly, dtype=float)
    return float(np.sum(
        poly[:, 0] * np.roll(poly[:, 1], -1)
        - poly[:, 1] * np.roll(poly[:, 0], -1)
    ))


def _clean_vertices(pts: np.ndarray, tol: float = EPS) -> np.ndarray:
    """Ardışık mükerrer noktaları ve kapanış tekrarını temizler."""
    pts = np.asarray(pts, dtype=float)
    if len(pts) == 0:
        return pts
    cleaned = [pts[0]]
    for p in pts[1:]:
        if np.linalg.norm(p - cleaned[-1]) > tol:
            cleaned.append(p)
    if len(cleaned) > 1 and np.linalg.norm(cleaned[0] - cleaned[-1]) <= tol:
        cleaned.pop()
    return np.asarray(cleaned)


def _split_by_line_2d(pts_2d, p1, p2, tol: float = EPS):
    """Poligonu p1->p2 doğrusu boyunca ikiye böler (Sutherland-Hodgman)."""
    poly = np.asarray(pts_2d, dtype=float)
    p1 = np.asarray(p1, dtype=float)
    p2 = np.asarray(p2, dtype=float)

    empty = np.empty((0, 2))
    if len(poly) < 3:
        return empty, empty

    line = p2 - p1
    if np.linalg.norm(line) <= tol:
        raise ValueError("p1 ve p2 aynı nokta olamaz.")

    area2 = _area2(poly)
    if abs(area2) <= tol:
        raise ValueError("Poligon alanı sıfıra çok yakın.")
    ccw = area2 > 0

    def side(pt: np.ndarray) -> float:
        v = pt - p1
        return line[0] * v[1] - line[1] * v[0]

    def clip(keep_left: bool) -> np.ndarray:
        result: List[np.ndarray] = []
        s = poly[-1]
        s_s = side(s)

        for e in poly:
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

            s, s_s = e, e_s

        if not result:
            return empty
        cleaned = _clean_vertices(np.asarray(result), tol)
        return cleaned if len(cleaned) >= 3 else empty

    def fix_orientation(p: np.ndarray) -> np.ndarray:
        if len(p) < 3:
            return p
        if (_area2(p) > 0) != ccw:
            return p[::-1].copy()
        return p

    return fix_orientation(clip(True)), fix_orientation(clip(False))


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
    if n < 3:
        return None

    intersections: List[np.ndarray] = []
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

    intersections.sort(key=lambda p: float(np.dot(p - p1, direction)))
    return intersections[0], intersections[-1]


def _unproject_local_2d_to_3d(pts_2d: np.ndarray, local_sys: dict) -> np.ndarray:
    pts_2d = np.asarray(pts_2d, dtype=float)
    origin = local_sys["origin_3d"]
    u_dir = local_sys["u_dir"]
    v_dir = local_sys["v_dir"]
    return origin + pts_2d[:, 0:1] * u_dir + pts_2d[:, 1:2] * v_dir


def _valid_polygon(poly) -> bool:
    return poly is not None and len(poly) >= 3


# ================================================================
# BuildingWindEngine
# ================================================================

class BuildingWindEngine:

    def __init__(
        self,
        points: Dict[str, Tuple[float, float, float]],
        polygons: Dict[str, List[str]],
        v_b0: float = 28.0,
        terrain: str = "Kategori III",
        w_dir: List[float] = (1.0, 0.0, 0.0),
        scale_factor: float = 1000.0,
        rho: float = 1.25,
        ct: float = 1.0,
        kI: float = 1.0,
    ):
        self.raw_points = points
        self.polygons = polygons
        self.v_b0 = float(v_b0)
        self.terrain = terrain
        self.w_dir = np.array(w_dir, dtype=float)
        self.scale_factor = float(scale_factor)
        
        self.rho = float(rho)
        self.ct = float(ct)
        self.kI = float(kI)

        self.e: Optional[float] = None
        self.all_roof_polygons: Dict[str, Any] = {}
        self.surfaces_items: Dict[str, WindPlane] = {}
        self.surfaces: Dict[str, Dict[str, Any]] = {}
        self.geometry: Dict[str, float] = {}

        self.points = self._scale_points()

        if self.terrain not in ARAZI_KATEGORILERI:
            raise ValueError(f"Geçersiz arazi kategorisi: {self.terrain}")

        self.z0 = ARAZI_KATEGORILERI[self.terrain]["z0"]
        self.zmin = ARAZI_KATEGORILERI[self.terrain]["zmin"]

        # 1. Ölçekle
        self.scaled_points = self._scale_points()

        # 2. Yüzeyleri analiz et
        self.surfaces = self._analyze_surfaces()

        # 3. Geometriyi tamamla
        self.geometry = self._calculate_building_geometry()

        # 4. Rüzgar parametreleri
        self._calculate_wind_parameters()

    # ------------------------------------------------------------
    # Kurulum / parametre
    # ------------------------------------------------------------

    def _scale_points(self) -> Dict[str, np.ndarray]:
        return {
            name: np.array(pt, dtype=float) / self.scale_factor
            for name, pt in self.raw_points.items()
        }

    def _analyze_surfaces(self, w: Optional[np.ndarray] = None) -> Dict[str, Dict[str, Any]]:
        """Her poligonu WindPlane'e dönüştürür ve temel bilgileri çıkarır."""
        if w is None:
            w = self.w_dir

        surfaces: Dict[str, Dict[str, Any]] = {}
        self.surfaces_items = {}
        self.all_roof_polygons = {}

        for poly_name, pt_names in self.polygons.items():
            pts = np.array([self.scaled_points[pt] for pt in pt_names])
            surface = WindPlane(pts, name=poly_name)
            self.surfaces_items[poly_name] = surface

            if surface.surface_type.value == "ROOF":
                self.all_roof_polygons[poly_name] = surface.properties["coords"]

            surfaces[poly_name] = {
                "type": surface.properties["surface_type"],
                "pitch": surface.properties["pitch"],
                "relation": surface.analyze_wind_relation(self.w_dir),
                "zmin": surface.properties["zmin"],
                "zmax": surface.properties["zmax"],
                "coords": surface.properties["coords"],
            }
        return surfaces

    def _calculate_building_geometry(self) -> Dict[str, float]:
        """Saçak kotu ve kritik `e` uzunluğunu hesaplar."""
        pts_matrix = np.array(list(self.scaled_points.values()))

        w_xy = self.w_dir[:2] / np.linalg.norm(self.w_dir[:2])
        v_vec = np.array([-w_xy[1], w_xy[0]])

        u_vals = pts_matrix[:, :2] @ w_xy
        v_vals = pts_matrix[:, :2] @ v_vec

        b = float(v_vals.max() - v_vals.min())
        d = float(u_vals.max() - u_vals.min())

        z_ground = float(pts_matrix[:, 2].min())
        z_ridge = float(pts_matrix[:, 2].max())

        # Saçak kotu: çatı yüzeylerinin zmin'lerinin maksimumu
        wall_z_maxs = [
            s["zmin"] for s in self.surfaces.values()
            if s["type"] == SurfaceType.ROOF
        ]
        z_eaves = max(wall_z_maxs) if wall_z_maxs else z_ridge

        h_total = z_ridge - z_ground
        h_eaves = z_eaves - z_ground
        e = min(b, 2.0 * h_total)
        self.e = e

        return {
            "b": b,
            "d": d,
            "h": h_total,
            "h_eaves": h_eaves,
            "z0_ground": z_ground,
            "z1_eaves": z_eaves,
            "z2_ridge": z_ridge,
            "e": e,
        }

    def _calculate_wind_parameters(self) -> None:
        self.q_b = 0.5 * self.rho * (self.v_b0 ** 2) / 1000.0
        self.z_ref = max(self.geometry["z2_ridge"], self.zmin)

        self.kr = 0.19 * ((self.z0 / 0.05) ** 0.07)
        self.cr = self.kr * math.log(self.z_ref / self.z0)
        self.Iv = self.kI / math.log(self.z_ref / self.z0)

        self.ce = (self.cr * self.ct) ** 2 * (1.0 + 7.0 * self.Iv)
        self.q_p = self.ce * self.q_b

    def get_summary(self) -> Dict[str, Any]:
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
                "zmin (m)": self.zmin,
            },
        }

    # ------------------------------------------------------------
    # Ana analiz akışı
    # ------------------------------------------------------------

    def analysis_all_roof_wind(self, w) -> Dict[str, WindPlane]:
        w = np.asarray(w, dtype=float)
        w_len = np.linalg.norm(w)
        if w_len < 1e-12:
            return self.surfaces_items
        w_norm = w / w_len

        # 1. FAZ: Lokal analiz
        self._analyze_surfaces(w_norm)

        roof_surfaces: Dict[str, WindPlane] = {}
        for surface_name, surface in self.surfaces_items.items():
            surface.analysis_(w_norm, self)
            surface.global_leading = False
            surface.properties["global_leading"] = False

            if surface.surface_type.value == "ROOF":
                roof_surfaces[surface_name] = surface

        if not roof_surfaces:
            return self.surfaces_items

        # 2. FAZ: Global leading analizi
        self._global_analysis_all_roof_wind(self.surfaces_items, w_norm)

        for surface in roof_surfaces.values():
            has_global = any(getattr(edge, "_global", False) for edge in surface.edges.values())
            surface.properties["global_leading"] = has_global
            surface.global_leading = has_global

        render_lines: Dict[str, Dict[str, np.ndarray]] = {}
        for name in self.polygons:
            surface = self.surfaces_items[name]
            st = surface.surface_type.value
            if st == "WALL":
                render_lines[name] = self._get_wall_zones(surface, self.e, False)
            elif st == "ROOF":
                render_lines[name] = self._get_roof_zones(surface, self.e, False)
            else:
                render_lines[name] = {}

        self.all_wind_zones = self.get_definition_regions(self.surfaces_items, render_lines)
        for id_, data in self.all_wind_zones.items():
            self.surfaces_items[id_].zones= data

        return self.all_wind_zones

    def _global_analysis_all_roof_wind(self, all_surfaces, w, tol=1e-3):
        w = np.asarray(w, dtype=float)
        w_2d = w[:2]
        w_len = np.linalg.norm(w_2d)
        if w_len < 1e-12:
            return []

        w_norm = w_2d / w_len
        w_perp = np.array([-w_norm[1], w_norm[0]])

        candidates = []
        for surface in all_surfaces.values():
            if surface.surface_type.value != "ROOF":
                continue
            for edge in surface.edges.values():
                p1_2d = np.asarray(edge.p1[:2], dtype=float)
                p2_2d = np.asarray(edge.p2[:2], dtype=float)
                pos1 = float(np.dot(p1_2d, w_norm))
                pos2 = float(np.dot(p2_2d, w_norm))
                candidates.append({
                    "edge": edge,
                    "front_pos": min(pos1, pos2),
                    "mid_pos": (pos1 + pos2) / 2.0,
                    "proj_len": abs(float(np.dot(p2_2d - p1_2d, w_perp))),
                })

        if not candidates:
            return []

        # Aşamalı filtreleme
        min_front = min(c["front_pos"] for c in candidates)
        front_cands = [c for c in candidates if abs(c["front_pos"] - min_front) <= tol]

        min_mid = min(c["mid_pos"] for c in front_cands)
        mid_cands = [c for c in front_cands if abs(c["mid_pos"] - min_mid) <= tol]

        max_proj = max(c["proj_len"] for c in mid_cands)
        global_leading = [c for c in mid_cands if abs(c["proj_len"] - max_proj) <= tol]

        for c in global_leading:
            c["edge"].leading = True
            c["edge"]._global = True

        return global_leading

    # ================================================================
    # OFFSET / KENAR YARDIMCILARI
    # ================================================================

    @staticmethod
    def _offset_edge_2d(polygon_2d, p1_2d, p2_2d, w_vector_2d, d_L):
        """Kenarı w yönünde offsetler ve poligona kırpar."""
        p1 = np.asarray(p1_2d, dtype=float)
        p2 = np.asarray(p2_2d, dtype=float)
        w_2d = np.asarray(w_vector_2d, dtype=float)
        w_len = np.linalg.norm(w_2d)
        if w_len < TOL:
            return None
        offset = (w_2d / w_len) * d_L
        return _clip_line_to_polygon_2d(p1 + offset, p2 + offset, polygon_2d)

    @staticmethod
    def _create_edge_perp_2d(polygon_2d, p1_2d, p2_2d, w_vector_2d, d_L):
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
    # ÇATI BÖLGELERİ
    # ================================================================

    def _get_roof_zones(
        self, plane1: WindPlane, e: float, debug: bool = False
    ) -> Dict[str, np.ndarray]:
        """
        Çatı yüzeyini rüzgar bölgelerine ayırır.

        Returns
        -------
        {zone_label: 3D coords (Nx3, kapalı)}
        """
        edges = plane1.edges
        pts_2d = np.asarray(plane1.pts_2d, dtype=float)
        is_ccw = plane1.is_ccw

        exposed_edges = [k for k, ed in edges.items() if ed.exposed]
        leading_edges = [k for k, ed in edges.items() if ed.leading]
        target_edges = leading_edges + [k for k in exposed_edges if k not in leading_edges]

        if debug:
            print(f"[_get_roof_zones] {plane1.polygon_name} leading={leading_edges}")

        wind_3d = np.asarray(plane1.properties["wind_vector"], dtype=float)
        u_dir = np.asarray(plane1.proj_info["u_dir"], dtype=float)
        v_dir = np.asarray(plane1.proj_info["v_dir"], dtype=float)

        w_plane = np.array([np.dot(wind_3d, u_dir), np.dot(wind_3d, v_dir)])
        w_plane /= np.linalg.norm(w_plane)

        regions_2d: Dict[str, np.ndarray] = {}
        remain_ = pts_2d.copy()

        # ---- Alt işlevler ----
        def split_FG(poly_FG, edge):
            """WINDWARD kenar için F1, F2, G bölgelerini üretir."""
            res = self._create_edge_perp_2d(
                pts_2d, edge.p1_2d, edge.p2_2d, edge.wind_to_2d, e / 4.0
            )
            if res is None:
                return
            result_L, result_R = res
            if result_L is None or result_R is None:
                return

            F_1, F_G = _split_by_line_2d(poly_FG, *result_L)
            if not (_valid_polygon(F_1) and _valid_polygon(F_G)):
                return

            G_, F_2 = _split_by_line_2d(F_G, *result_R)
            if not (_valid_polygon(G_) and _valid_polygon(F_2)):
                return

            regions_2d["F1"] = F_1
            regions_2d["F2"] = F_2
            regions_2d["G"] = G_

        def split_MN(poly_M):
            """PARALLEL kenar için M, N bölgelerini üretir."""
            edge = edges[leading_edges[0]]
            p0e = np.asarray(edge.pos_front_pt, dtype=float) + w_plane * (e / 2.0)
            w_perp = np.array([-w_plane[1], w_plane[0]])
            L = 10.0 * max(np.ptp(pts_2d[:, 0]), np.ptp(pts_2d[:, 1]))

            cut = _clip_line_to_polygon_2d(p0e - w_perp * L, p0e + w_perp * L, remain_)
            if cut is None:
                regions_2d["M"] = poly_M
                return

            M_, N_ = _split_by_line_2d(poly_M, *cut)
            if not (_valid_polygon(M_) and _valid_polygon(N_)):
                regions_2d["M"] = poly_M
                return
            regions_2d["M"] = M_
            regions_2d["N"] = N_

        # ---- Ana döngü ----
        counter = 0
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

            H_, FG_ = _split_by_line_2d(remain_, *clipped)
            if not (_valid_polygon(H_) and _valid_polygon(FG_)):
                continue

            if getattr(edge, "_global", False):
                split_FG(FG_, edge)
            else:
                if (
                    edge.leading
                    and plane1.wind_relation.value == "LEEWARD"
                    and len(leading_edges) == 1
                ):
                    regions_2d["K"] = FG_
                else:
                    counter += 1
                    regions_2d[f"L{counter}"] = FG_

            remain_ = H_

        # ---- Kalan bölge ----
        if plane1.wind_relation.value == "PARALLEL":
            split_MN(remain_)
        else:
            regions_2d["M"] = remain_

        # ---- F1/F2 → Fu/Fl ----
        if "F1" in regions_2d and "F2" in regions_2d:
            f1_3d = _unproject_local_2d_to_3d(regions_2d["F1"], plane1.proj_info)
            f2_3d = _unproject_local_2d_to_3d(regions_2d["F2"], plane1.proj_info)
            z1 = float(np.mean(f1_3d[:, 2]))
            z2 = float(np.mean(f2_3d[:, 2]))

            f1 = regions_2d.pop("F1")
            f2 = regions_2d.pop("F2")
            if z1 >= z2:
                regions_2d["Fu"], regions_2d["Fl"] = f1, f2
            else:
                regions_2d["Fu"], regions_2d["Fl"] = f2, f1

            if debug:
                print(f"  Fu/Fl: z1={z1:.3f} z2={z2:.3f}")

        # ---- 2D → 3D ----
        result: Dict[str, np.ndarray] = {}
        for label, poly_2d in regions_2d.items():
            if not _valid_polygon(poly_2d):
                continue
            poly_3d = _unproject_local_2d_to_3d(poly_2d, plane1.proj_info)
            result[label] = _close_polygon(poly_3d)

        if debug:
            print(f"  final zones={list(result.keys())}")

        return result

    # ================================================================
    # DUVAR BÖLGELERİ
    # ================================================================

    def _get_wall_zones(
        self, plane1: WindPlane, e: float, debug: bool = False
    ) -> Dict[str, np.ndarray]:
        """Duvar yüzeyini A/B/C bölgelerine ayırır."""
        pts_2d = np.asarray(plane1.pts_2d, dtype=float)
        u_dir = np.asarray(plane1.proj_info["u_dir"], dtype=float)
        v_dir = np.asarray(plane1.proj_info["v_dir"], dtype=float)

        pts_2d_closed = _close_polygon(pts_2d)

        wind_3d = np.asarray(plane1.properties["wind_vector"], dtype=float)
        w_plane = np.array([np.dot(wind_3d, u_dir), np.dot(wind_3d, v_dir)])
        w_norm = np.linalg.norm(w_plane)
        if w_norm < 1e-12:
            return {"A": _close_polygon(plane1.pts_3d)}
        w_dir_2d = w_plane / w_norm
        perp_2d = np.array([-w_dir_2d[1], w_dir_2d[0]])

        proj_vals = pts_2d_closed[:-1] @ w_dir_2d
        min_p = float(proj_vals.min())
        max_p = float(proj_vals.max())
        d_len = max_p - min_p

        if d_len < 1e-6:
            return {"A": _close_polygon(plane1.pts_3d)}

        if e <= 0:
            e = d_len

        a_len = e / 5.0
        b_len = 4.0 * e / 5.0

        # Bölge sınırları (rüzgar yönü boyunca)
        splits = [a_len, a_len + b_len]
        zone_names = ["A", "B", "C"]
        if a_len + b_len >= d_len - 1e-5:
            splits = [a_len] if a_len < d_len - 1e-5 else []
            zone_names = ["A", "B"]

        current_poly_2d = pts_2d_closed
        zones: Dict[str, np.ndarray] = {}

        for idx, offset in enumerate(splits):
            if offset >= d_len - 1e-5:
                break

            split_p = min_p + offset
            ref_pt = w_dir_2d * split_p
            p1 = ref_pt - perp_2d * 10000.0
            p2 = ref_pt + perp_2d * 10000.0

            part1_2d, part2_2d = _split_by_line_2d(current_poly_2d, p1, p2)
            if not (_valid_polygon(part1_2d) and _valid_polygon(part2_2d)):
                break

            center1 = np.mean(part1_2d[:-1], axis=0) @ w_dir_2d
            center2 = np.mean(part2_2d[:-1], axis=0) @ w_dir_2d

            if center1 < center2:
                zone_2d, current_poly_2d = part1_2d, _close_polygon(part2_2d)
            else:
                zone_2d, current_poly_2d = part2_2d, _close_polygon(part1_2d)

            zone_3d = _unproject_local_2d_to_3d(zone_2d, plane1.proj_info)
            zones[zone_names[idx]] = _close_polygon(zone_3d)

        # Kalan bölge
        remaining_name = zone_names[len(zones)] if len(zones) < len(zone_names) else "C"
        remaining_3d = _unproject_local_2d_to_3d(current_poly_2d, plane1.proj_info)
        zones[remaining_name] = _close_polygon(remaining_3d)

        if debug:
            print(f"[_get_wall_zones] {plane1.polygon_name} zones={list(zones.keys())}")

        return zones

    # ================================================================
    # BÖLGE → ZONE EŞLEŞTİRME
    # ================================================================

    def get_definition_regions(
        self,
        all_surfaces: Dict[str, WindPlane],
        regions: Dict[str, Dict[str, np.ndarray]],
    ) -> Dict[str, List[Zone]]:
        """
        `_get_roof_zones` / `_get_wall_zones` çıktılarındaki ham bölgeleri
        TS EN 1991-1-4 zone etiketlerine dönüştürür.
        """
        surface_all_zones: Dict[str, List[Zone]] = {}

        # 1. Çatı genel MONOPITCH mi?
        roof_surfaces = {
            name: s for name, s in all_surfaces.items()
            if getattr(s.surface_type, "value", s.surface_type) == "ROOF"
        }
        roof_relations = [
            s.properties.get("wind_relation").value
            for s in roof_surfaces.values()
            if s.properties.get("wind_relation") is not None
        ]
        is_overall_monopitch = (
            len(roof_relations) > 0
            and all(x == roof_relations[0] for x in roof_relations)
        )

        # 2. Yüzey bazlı sınıflandırma
        for sname, plane1 in all_surfaces.items():
            wind_relation = plane1.properties.get("wind_relation", None)
            if wind_relation is None:
                continue

            all_coords = np.vstack(list(plane1.pts_3d))
            x_range = all_coords[:, 0].max() - all_coords[:, 0].min()
            y_range = all_coords[:, 1].max() - all_coords[:, 1].min()
            z_range = all_coords[:, 2].max() - all_coords[:, 2].min()
            d = max(x_range, y_range)
            h = z_range

            surface_type = getattr(plane1.surface_type, "value", plane1.surface_type)
            global_leading = plane1.properties.get("global_leading", False)

            # --- Tablo tipi ve yönü ---
            if surface_type == "ROOF":
                if not is_overall_monopitch:
                    if wind_relation.value == "PARALLEL" and global_leading:
                        table_type, table_type_dir = "DUOPITCH", 90
                    else:
                        table_type, table_type_dir = "HIPPED", 0
                else:
                    table_type = "MONOPITCH"
                    if wind_relation.value == "WINDWARD":
                        table_type_dir = 0
                    elif wind_relation.value == "LEEWARD":
                        table_type_dir = 180
                    else:
                        table_type_dir = 90
            else:
                table_type, table_type_dir = "WALL", 0

            # --- Pitch ---
            if table_type == "WALL":
                if d <= 0:
                    continue
                pitch = h / d
            else:
                pitch = plane1.pitch

            # --- Bölgeleri etiketle ---
            zones_list: List[Zone] = []
            for reg_name, coords in regions.get(sname, {}).items():
                label = self._label_region(
                    reg_name, wind_relation.value, table_type
                )
                if label is None:
                    continue

                zones_list.append(Zone(
                    label=label,
                    coords=coords,
                    surface=sname,
                    table_type=table_type,
                    table_type_dir=table_type_dir,
                    pitch=pitch,
                ))

            surface_all_zones[sname] = zones_list

        return surface_all_zones

    @staticmethod
    def _label_region(reg_name: str, wind_relation: str, table_type: str) -> Optional[str]:
        """Ham bölge adını TS EN 1991-1-4 zone etiketine çevirir."""
        if wind_relation == "WINDWARD":
            if table_type == "WALL":
                return "D"
            label = reg_name[:1]
            return "H" if label == "M" else label

        if wind_relation == "LEEWARD":
            
            if table_type == "WALL":
                return "E"
            label = reg_name[:1]
            
            if label == "M":
              if table_type == "MONOPITCH":
                return "H"
              else:
                return "I"
            if label == "L":
                return "J"
            return label

        if wind_relation == "PARALLEL":
            if table_type == "WALL":
                return reg_name
            if table_type == "MONOPITCH":
                if reg_name == "M":
                    return "H"
                if reg_name == "N":
                    return "I"
                return reg_name
            if table_type == "DUOPITCH":
                if reg_name == "Fl":
                    return "F"
                if reg_name == "Fu":
                    return "G"
                if reg_name == "M":
                    return "H"
                if reg_name == "N":
                    return "I"
                return reg_name
            return reg_name[:1]

        return None

    # ================================================================
    # YARDIMCI: OBB / render
    # ================================================================

    def get_polygon_coords(self, polygon_points, points, scale_=1000.0) -> np.ndarray:
        """Poligon nokta isimlerini ölçekli koordinatlara çevirir."""
        coords = []
        for pt_name in polygon_points:
            if pt_name not in points:
                raise ValueError(f"Nokta '{pt_name}' bulunamadı!")
            pt = points[pt_name]
            coords.append([pt[0] / scale_, pt[1] / scale_, pt[2] / scale_])
        return np.array(coords)

    
    def calculate_obb_and_geometry(self,
        p1: List[float]= None,
        p2: List[float]= None,
        points_dict: Dict[str, List[float]]= None,
    ) -> Optional[Dict[str, Any]]:
        """
        Seçilen P1-P2 doğrultusunu ve tüm noktaları kullanarak
        rüzgara göre dönmüş sınırlayıcı kutu (OBB) ve geometriyi türetir.
        """
        if p1 is None and p2 is None and points_dict is None:
            if not self.w_dir is None:
                p1 = np.array([-self.w_dir[1], self.w_dir[0], 0.0])
                p2 = np.array([0.0, 0.0, 0.0])
                points_dict= self.points
            else:
                return

    
        du_x, du_y = p2[0] - p1[0], p2[1] - p1[1]
        L_u = math.hypot(du_x, du_y)
        if L_u < 1e-6:
            return None

        ux, uy = du_x / L_u, du_y / L_u
        vx, vy = -uy, ux

        u_vals, v_vals, z_vals = [], [], []
        for pt in points_dict.values():
            rx, ry, rz = pt[0] - p1[0], pt[1] - p1[1], pt[2]
            u_vals.append(rx * ux + ry * uy)
            v_vals.append(rx * vx + ry * vy)
            z_vals.append(rz)

        if not u_vals:
            return None

        u_min, u_max = min(u_vals), max(u_vals)
        v_min, v_max = min(v_vals), max(v_vals)
        z_min, z_max = min(z_vals), max(z_vals)

        B = u_max - u_min
        d = v_max - v_min
        H = z_max - z_min
        e = min(B, 2.0 * H)

        def corner(u, v):
            return [
                p1[0] + ux * u + vx * v,
                p1[1] + uy * u + vy * v,
                0.0,
            ]

        c1 = corner(u_min, v_min)
        c2 = corner(u_max, v_min)
        c3 = corner(u_max, v_max)
        c4 = corner(u_min, v_max)

        u_mid = (u_min + u_max) / 2.0
        impact_point = corner(u_mid, v_min)

        return {
            "b": B,
            "d": d,
            "h": H,
            "e": e,
            "impact_point": impact_point,
            "wind_dir": [vx, vy, 0.0],
            "parallel_dir": [ux, uy, 0.0],
            "obb_corners": [c1, c2, c3, c4],
            "z0_ground": z_min,
            "z_max": z_max,
        }

    @classmethod
    def generate_render_lines(cls, geom: Dict[str, Any]) -> List[List[List[float]]]:
        """View3D için saf [ [start_pt, end_pt], ... ] çizgi dizileri."""
        lines: List[List[List[float]]] = []

        # OBB kenarları
        c1, c2, c3, c4 = geom["obb_corners"]
        lines.extend([[c1, c2], [c2, c3], [c3, c4], [c4, c1]])

        # Rüzgar oku
        imp = geom["impact_point"]
        vx, vy = geom["wind_dir"][0], geom["wind_dir"][1]
        ux, uy = geom["parallel_dir"][0], geom["parallel_dir"][1]
        B = geom["b"]

        arrow_len = max(B * 0.35, 2.5)
        head_len = arrow_len * 0.25
        head_wing = arrow_len * 0.15

        tail = [imp[0] - vx * arrow_len, imp[1] - vy * arrow_len, 0.0]
        h1 = [
            imp[0] - vx * head_len + ux * head_wing,
            imp[1] - vy * head_len + uy * head_wing,
            0.0,
        ]
        h2 = [
            imp[0] - vx * head_len - ux * head_wing,
            imp[1] - vy * head_len - uy * head_wing,
            0.0,
        ]

        lines.append([tail, imp])
        lines.append([imp, h1])
        lines.append([imp, h2])

        # 'W' sembolü
        w_size = arrow_len * 0.12
        w_base = [tail[0] - vx * (w_size * 1.5), tail[1] - vy * (w_size * 1.5), 0.0]

        wp0 = [w_base[0] - ux * w_size, w_base[1] - uy * w_size, 0.0]
        wp1 = [
            w_base[0] - ux * (w_size * 0.5) - vx * w_size,
            w_base[1] - uy * (w_size * 0.5) - vy * w_size,
            0.0,
        ]
        wp2 = [w_base[0], w_base[1], 0.0]
        wp3 = [
            w_base[0] + ux * (w_size * 0.5) - vx * w_size,
            w_base[1] + uy * (w_size * 0.5) - vy * w_size,
            0.0,
        ]
        wp4 = [w_base[0] + ux * w_size, w_base[1] + uy * w_size, 0.0]

        lines.extend([[wp0, wp1], [wp1, wp2], [wp2, wp3], [wp3, wp4]])

        return lines

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

from matplotlib import pyplot as plt
def show_at_matplotlib(all_lines):

    # Tüm noktaları topla
    all_coords = np.vstack(all_lines)

    # Eksen limitleri
    mins = all_coords.min(axis=0)
    maxs = all_coords.max(axis=0)

    center = (mins + maxs) / 2.0
    max_range = float((maxs - mins).max())

    # Sıfır boyutlu geometri kontrolü
    if max_range == 0:
        max_range = 1.0

    # Figure
    fig = plt.figure(figsize=(10, 10))
    ax = fig.add_subplot(111, projection="3d")

    half = max_range / 2.0

    ax.set_xlim(center[0] - half, center[0] + half)
    ax.set_ylim(center[1] - half, center[1] + half)
    ax.set_zlim(center[2] - half, center[2] + half)

    ax.set_box_aspect([1, 1, 1])

    # Çizgileri çiz
    for line in all_lines:

        coords = np.asarray(line)

        if coords.shape[0] < 2:
            continue

        ax.plot(
            coords[:, 0],
            coords[:, 1],
            coords[:, 2],
            linewidth=1.5
        )

    # Eksen / tema temizliği
    ax.axis("off")
    ax.grid(False)

    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        axis.pane.fill = False
        axis.pane.set_edgecolor("none")

    plt.show()

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

    W_LIST = {
        "x+": [1, 0, 0],
        "y+": [0, 1, 0],
        "x-": [-1, 0, 0],
        "y-": [0, -1, 0],
    }

    scale = 0.001  # mm → m    
    points = {
                        name: tuple(coord * scale for coord in coords)
                        for name, coords in points.items()
                    }  

    w= "y+"
    building = BuildingWindEngine(
                points=points,
                polygons=polygons,
                v_b0=28.0,
                terrain="Kategori III",
                w_dir=W_LIST[w],
                scale_factor=1,
            )

    print(dict_tree(building.__dict__))

    geom= building.calculate_obb_and_geometry()

    print(dict_tree(geom))
    render_lines= building.generate_render_lines(geom)
    show_at_matplotlib(render_lines)

