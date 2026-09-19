from typing import Any, Dict, List, Optional, Tuple
from windcalc.zone import ARAZI_KATEGORILERI
from windcalc.windplane import WindPlane, SurfaceType
import numpy as np
import math


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

    def _analyze_surfaces(self, w= None) -> Dict[str, Dict[str, Any]]:
        """Poligon bağımsız yüzey tipini ve kotlarını çıkarır."""
        if w is None:
            w = self.w_dir

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
        w = np.asarray(w, dtype=float)

        w_len = np.linalg.norm(w)

        if w_len < 1e-12:
            return

        w_norm = w / w_len

        # ------------------------------------------------------------
        # 1. FAZ
        # Bütün yüzeylerin lokal analizini tamamla.
        # ------------------------------------------------------------

        self._analyze_surfaces(w)

        roof_surfaces = {}

        for surface_name, surface in self.surfaces_items.items():

            surface.analysis_(w, self)

            surface.global_leading = False
            surface.properties["global_leading"] = False

            if getattr(
                surface.surface_type,
                "value",
                surface.surface_type
            ) == "ROOF":

                roof_surfaces[surface_name] = surface

        if not roof_surfaces:
            return self.surfaces_items

        # ------------------------------------------------------------
        # 2. FAZ
        # Lokal leading kenarları artık bütün yüzeyler arasında
        # karşılaştır.
        # ------------------------------------------------------------

        self._global_analysis_all_roof_wind(self.surfaces_items,w)


        for surface_name, surface in roof_surfaces.items():
            edges= surface.edges
            surface.properties["global_leading"] = any([True for k in edges.values() if k._global])
            surface.global_leading = any([True for k in edges.values() if k._global])

        return self.surfaces_items

    def _global_analysis_all_roof_wind(self, all_surfaces, w, tol=1e-3):
      w = np.asarray(w, dtype=float)
      w_2d = w[:2]
      w_len = np.linalg.norm(w_2d)

      if w_len < 1e-12:
          return []

      # Rüzgarın gidiş yönü (normalize)
      w_norm = w_2d / w_len
      
      # Rüzgara dik dikdik doğrultu (perpendicular vector)
      w_perp = np.array([-w_norm[1], w_norm[0]])

      candidate_edges = []

      for surface in all_surfaces.values():
          surface_type = getattr(surface.surface_type, "value", surface.surface_type)
          if surface_type != "ROOF":
              continue

          for edge in surface.edges.values():
              p1_2d = np.asarray(edge.p1[:2], dtype=float)
              p2_2d = np.asarray(edge.p2[:2], dtype=float)

              # İki ucun rüzgar eksenindeki konumları
              pos1 = float(np.dot(p1_2d, w_norm))
              pos2 = float(np.dot(p2_2d, w_norm))

              # 1. En ön köşe konumu (Rüzgara en yakın uç)
              front_pos = min(pos1, pos2)
              
              # 2. Kenarın rüzgar eksenindeki ORTA noktası (Kenarı bütünsel temsil eder)
              mid_pos = (pos1 + pos2) / 2.0
              
              # 3. Kenarın rüzgara dik izdüşüm uzunluğu (Rüzgarı ne kadar göğüslüyor?)
              # Rüzgara dik olan kenarın bu değeri yüksek, rüzgara paralel giden kenarın 0 olur.
              proj_len = abs(float(np.dot(p2_2d - p1_2d, w_perp)))

              candidate_edges.append({
                  "surface": getattr(surface, "polygon_name", "ROOF"),
                  "edge": edge,
                  "front_pos": front_pos,
                  "mid_pos": mid_pos,
                  "proj_len": proj_len
              })

      if not candidate_edges:
          return []

      # ------------------------------------------------------------------
      # FİLTRELEME MANTIĞI:
      # ------------------------------------------------------------------
      
      # Adım 1: En öndeki köşeye sahip kenarları bul (Tolerans bandında)
      global_min_front = min(item["front_pos"] for item in candidate_edges)
      front_candidates = [
          item for item in candidate_edges
          if abs(item["front_pos"] - global_min_front) <= tol
      ]

      # Adım 2: Bu adaylar arasından "orta noktası" da en önde olanları (gerçek ön kenarları) seç
      min_mid_pos = min(item["mid_pos"] for item in front_candidates)
      mid_candidates = [
          item for item in front_candidates
          if abs(item["mid_pos"] - min_mid_pos) <= tol
      ]

      # Adım 3: Eğer hala eşitlik varsa, rüzgarı en çok göğüsleyen (izdüşümü en büyük) kenarı öne al
      max_proj = max(item["proj_len"] for item in mid_candidates)
      global_leading_edges = [
          item for item in mid_candidates
          if abs(item["proj_len"] - max_proj) <= tol
      ]

      # Kenarları işaretle
      for item in global_leading_edges:
          item["edge"].leading = True
          item["edge"]._global = True

      return global_leading_edges

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