# windengine.py

import math
import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Tuple, Optional, Union, Any
from data.wind_data import ARAZI_KATEGORILERI, CPI_POSITIVE, CPI_NEGATIVE, RHO,K_I,C0, wall_cpe_table,MONOPITCH_CPE_DATA,DUOPITCH_CPE_DATA,HIPPED_CPE_DATA
from .windplane import WindPlane, SurfaceType, WindRelation

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
                if not edge.exposed:
                    continue
                
                p1_pos = np.dot(np.array(edge.p1), w_norm)
                p2_pos = np.dot(np.array(edge.p2), w_norm)
                
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
                if not edge.exposed:
                    continue

                p1_pos = np.dot(np.array(edge.p1), w_norm)
                p2_pos = np.dot(np.array(edge.p2), w_norm)
                
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
                    edge_len = np.linalg.norm(np.array(edge.p2) - np.array(edge.p1))
                    if edge_len > 1e-2:
                        is_leading = True
                        break

            if is_leading:
                surface.global_leading = True
                surface.properties["global_leading"] = True
                
    @staticmethod
    def calculate_obb_and_geometry(
        p1: List[float], 
        p2: List[float], 
        points_dict: Dict[str, List[float]]
    ) -> Optional[Dict[str, Any]]:
        """
        Seçilen P1-P2 doğrultusunu ve modeldeki tüm noktaları alarak
        rüzgara göre dönmüş sınırlayıcı kutu (OBB) ve B, d, H geometrisini türetir.
        """
        # 1. Rüzgara Paralel Doğrultu Vektörü (U) ve Dik Doğrultu Vektörü (V)
        du_x, du_y = p2[0] - p1[0], p2[1] - p1[1]
        L_u = math.sqrt(du_x**2 + du_y**2)
        if L_u < 1e-6:
            return None

        ux, uy = du_x / L_u, du_y / L_u  # Rüzgar yüzeyine paralel yön (U)
        vx, vy = -uy, ux                 # Rüzgarın esme yönü / Yapıya DİK yön (V)

        # 2. Tüm Bina Noktalarının U-V Eksenlerine ve Z Kotuna İzdüşümü
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

        # 3. Geometrik Mühendislik Parametreleri (TS EN 1991-1-4)
        B = u_max - u_min                # Rüzgar yönüne dik genişlik (b)
        d = v_max - v_min                # Rüzgar yönüne paralel derinlik (d)
        H = z_max - z_min                # Yapı yüksekliği (h)
        e = min(B, 2.0 * H)              # Kritik referans uzunluk e

        # 4. Z=0 Düzleminde Dönük Sınırlayıcı Kutu (OBB) Köşe Koordinatları
        c1 = [p1[0] + ux * u_min + vx * v_min, p1[1] + uy * u_min + vy * v_min, 0.0]
        c2 = [p1[0] + ux * u_max + vx * v_min, p1[1] + uy * u_max + vy * v_min, 0.0]
        c3 = [p1[0] + ux * u_max + vx * v_max, p1[1] + uy * u_max + vy * v_max, 0.0]
        c4 = [p1[0] + ux * u_min + vx * v_max, p1[1] + uy * u_min + vy * v_max, 0.0]

        # 5. Rüzgar Vektörünün Dışarıdan Kutunun Ön Yüzüne Saplanma Noktası (Z=0)
        u_mid = (u_min + u_max) / 2.0
        impact_point = [p1[0] + ux * u_mid + vx * v_min, p1[1] + uy * u_mid + vy * v_min, 0.0]

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
            "z_max": z_max
        }
    @classmethod
    def generate_render_lines(cls, geom: Dict[str, Any]) -> List[List[List[float]]]:
        """
        View3D'nin (OpenGL) hiçbir hesap yapmadan doğrudan çizeceği
        saf [ [start_pt, end_pt], ... ] çizgi dizilerini üretir.
        """
        lines = []

        # A) Z=0 Düzleminde Dönük Sınırlayıcı Kutu (OBB - 4 Ana Kenar)
        c1, c2, c3, c4 = geom["obb_corners"]
        lines.extend([[c1, c2], [c2, c3], [c3, c4], [c4, c1]])

        # B) Rüzgar Oku (Bina Dışında, OBB Ön Yüzüne Saplanıyor)
        imp = geom["impact_point"]
        vx, vy = geom["wind_dir"][0], geom["wind_dir"][1]
        ux, uy = geom["parallel_dir"][0], geom["parallel_dir"][1]
        B = geom["b"]

        arrow_len = max(B * 0.35, 2.5)
        head_len, head_wing = arrow_len * 0.25, arrow_len * 0.15

        tail = [imp[0] - vx * arrow_len, imp[1] - vy * arrow_len, 0.0]
        h1 = [imp[0] - vx * head_len + ux * head_wing, imp[1] - vy * head_len + uy * head_wing, 0.0]
        h2 = [imp[0] - vx * head_len - ux * head_wing, imp[1] - vy * head_len - uy * head_wing, 0.0]

        lines.append([tail, imp])  # Gövde
        lines.append([imp, h1])    # Sol Ok Başı
        lines.append([imp, h2])    # Sağ Ok Başı

        # C) Rüzgar Okunun Arkasına 'W' Harfi Sembolü
        w_size = arrow_len * 0.12
        w_base = [tail[0] - vx * (w_size * 1.5), tail[1] - vy * (w_size * 1.5), 0.0]

        wp0 = [w_base[0] - ux * w_size, w_base[1] - uy * w_size, 0.0]
        wp1 = [w_base[0] - ux * (w_size * 0.5) - vx * w_size, w_base[1] - uy * (w_size * 0.5) - vy * w_size, 0.0]
        wp2 = [w_base[0], w_base[1], 0.0]
        wp3 = [w_base[0] + ux * (w_size * 0.5) - vx * w_size, w_base[1] + uy * (w_size * 0.5) - vy * w_size, 0.0]
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
        p1_z = edge.p1[2]
        p2_z = edge.p2[2]
        
        # Kenar mahya kotunda mı (zmax civarında)?
        if abs(p1_z - zmax) <= tol and abs(p2_z - zmax) <= tol:
            # Kenar başka bir yüzeyle paylaşıyor mu?
            if edge.shared:
                # Komşu yüzeyin çatı (ROOF) olup olmadığını doğrula
                for other_name, other_s in all_surfaces.items():
                    if other_name == surface.properties["name"]:
                        continue
                    if getattr(other_s.surface_type, "value", other_s.surface_type) == "ROOF":
                        # Kenar bu çatı yüzeyinde de var mı?
                        for o_edge in other_s.edges.values():
                            if o_edge.shared:
                                # p1-p2 çakışması kontrolü
                                dist1 = np.linalg.norm(np.array(edge.p1) - np.array(o_edge.p1)) + \
                                        np.linalg.norm(np.array(edge.p2) - np.array(o_edge.p2))
                                dist2 = np.linalg.norm(np.array(edge.p1) - np.array(o_edge.p2)) + \
                                        np.linalg.norm(np.array(edge.p2) - np.array(o_edge.p1))
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
                if edge.exposed:
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

    # wind_parameters= building.get_summary()
    # print("\nwind_parameters:\n", dict_tree(wind_parameters))

    # for w in [[1,0,0],[0,1,0], [-1,0,0],[0,-1,0]]:
    # # for w in [[1,0,0]]:
    #     print(f"Wind vector: {w}")
    #     building.analysis_all_roof_wind(w)

        
    #     for plane_name, plane1 in building.surfaces_items.items():
            
            
    #         if plane_name in ["C1","C2","C3"]:
                
                
    #             print([f"{kk}: {plane1.properties.get(kk, "")}" for kk in ['name','surface_type','angle', 'pitch','wind_vector','wind_relation','global_leading','any_shared',"has_ridge_neighbor", "is_gable_side", "is_triangular_or_trapezoidal"]])
    #             compute_surface_topological_properties(plane1, building.surfaces_items)                # info= dict_tree(plane1.properties)
    #             print(plane1.edges)
    #             aa= get_cpe_table_for_surface(plane1)
    #             print(f"cpe_table_for_surface: {aa}")
    # info= dict_tree(plane1.edges)
    # print("\nplane1.edges:\n", info)

    # for k,v in building.surfaces_items.items():
    #     info= dict_tree(v.properties)
            
    #     print(k,"\n", info)

    