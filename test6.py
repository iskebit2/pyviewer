from typing import Dict

import numpy as np
from zone import Zone, TOL,EPS
from buildingwindengine import BuildingWindEngine

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
    
def close_polygon(polygon: np.ndarray, tol: float = TOL) -> np.ndarray:
    """Poligonu kapatır (ilk nokta = son nokta)."""
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
    """İki katlı alan (işaretli)."""
    return float(np.sum(
        poly[:, 0] * np.roll(poly[:, 1], -1)
        - poly[:, 1] * np.roll(poly[:, 0], -1)
    ))


def _clean_vertices(pts: np.ndarray, tol: float = EPS) -> np.ndarray:
    """Ardışık mükerrer noktaları ve kapanış tekrarını temizler."""
    if len(pts) == 0:
        return pts
    cleaned = [pts[0]]
    for p in pts[1:]:
        if np.linalg.norm(p - cleaned[-1]) > tol:
            cleaned.append(p)
    if len(cleaned) > 1 and np.linalg.norm(cleaned[0] - cleaned[-1]) <= tol:
        cleaned.pop()
    return np.asarray(cleaned)


# ================================================================
# 2D BÖLME / KIRPMA
# ================================================================

def _split_by_line_2d(pts_2d, p1, p2, tol: float = EPS):
    """Poligonu p1->p2 doğrusu boyunca ikiye böler (Sutherland-Hodgman)."""
    poly = np.asarray(pts_2d, dtype=float)
    p1 = np.asarray(p1, dtype=float)
    p2 = np.asarray(p2, dtype=float)

    if len(poly) < 3:
        return np.empty((0, 2)), np.empty((0, 2))

    line = p2 - p1
    if np.linalg.norm(line) <= tol:
        raise ValueError("p1 ve p2 aynı nokta olamaz.")

    area2 = _area2(poly)
    if abs(area2) <= tol:
        raise ValueError("Poligon alanı sıfıra çok yakın.")
    ccw = area2 > 0

    # p1->p2 doğrusuna göre işaretli uzaklık
    def side(pt):
        v = pt - p1
        return line[0] * v[1] - line[1] * v[0]

    def clip(keep_left: bool) -> np.ndarray:
        result = []
        s = poly[-1]

        for e in poly:
            s_s = side(s)
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

            s = e

        if not result:
            return np.empty((0, 2))

        cleaned = _clean_vertices(np.asarray(result), tol)
        if len(cleaned) < 3:
            return np.empty((0, 2))
        return cleaned

    left = clip(True)
    right = clip(False)

    def fix_orientation(p: np.ndarray) -> np.ndarray:
        if len(p) < 3:
            return p
        if (_area2(p) > 0) != ccw:
            return p[::-1].copy()
        return p

    return fix_orientation(left), fix_orientation(right)


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

        if -TOL <= u <= 1 + TOL:
            pt = p1 + t * direction
            if not any(np.linalg.norm(pt - prev) < 1e-6 for prev in intersections):
                intersections.append(pt)

    if len(intersections) < 2:
        return None

    intersections.sort(key=lambda p: np.dot(p - p1, direction))
    return intersections[0], intersections[-1]


# ================================================================
# OFFSET / KENAR YARDIMCILARI
# ================================================================

def offset_edge_2d(polygon_2d, p1_2d, p2_2d, w_vector_2d, d_L):
    """Kenarı w yönünde offsetler."""
    p1 = np.asarray(p1_2d, dtype=float)
    p2 = np.asarray(p2_2d, dtype=float)
    w_2d = np.asarray(w_vector_2d, dtype=float)
    w_len = np.linalg.norm(w_2d)
    if w_len < TOL:
        return None
    offset = (w_2d / w_len) * d_L
    return _clip_line_to_polygon_2d(p1 + offset, p2 + offset, polygon_2d)


def create_edge_perp_2d(polygon_2d, p1_2d, p2_2d, w_vector_2d, d_L):
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
# 3D <-> 2D
# ================================================================

def _unproject_local_2d_to_3d(pts_2d, local_sys):
    pts_2d = np.asarray(pts_2d, dtype=float)
    origin = local_sys["origin_3d"]
    u_dir = local_sys["u_dir"]
    v_dir = local_sys["v_dir"]
    return origin + pts_2d[:, 0:1] * u_dir + pts_2d[:, 1:2] * v_dir


def valid_polygon(poly) -> bool:
    return poly is not None and len(poly) >= 3


def split(poly, p1, p2):
    if not valid_polygon(poly):
        return None, None
    left, right = _split_by_line_2d(poly, p1, p2)
    return (
        left if valid_polygon(left) else None,
        right if valid_polygon(right) else None,
    )


def to_3d(poly, local_sys):
    if not valid_polygon(poly):
        return None
    return _unproject_local_2d_to_3d(poly, local_sys)

def _get_roof_zones(plane1, e: float, debug: bool = False) -> Dict[str, np.ndarray]:
    """
    Çatı yüzeyini rüzgar bölgelerine ayırır.

    Returns
    -------
    dict
        {zone_label: 3D coords (np.ndarray Nx3)}
        Örn: {"F": ..., "G": ..., "H": ...}
        veya {"Fu": ..., "Fl": ..., "G": ..., "H": ..., "I": ...}
    """
    edges = plane1.edges
    pts_2d = np.asarray(plane1.pts_2d, dtype=float)
    is_ccw = plane1.is_ccw

    exposed_edges = [k for k, ed in edges.items() if ed.exposed]
    leading_edges = [k for k, ed in edges.items() if ed.leading]
    target_edges = leading_edges + [k for k in exposed_edges if k not in leading_edges]

    print("debug",plane1.polygon_name, leading_edges)

    wind_3d = np.asarray(plane1.properties["wind_vector"], dtype=float)
    u_dir = np.asarray(plane1.proj_info["u_dir"], dtype=float)
    v_dir = np.asarray(plane1.proj_info["v_dir"], dtype=float)

    w_plane = np.array([np.dot(wind_3d, u_dir), np.dot(wind_3d, v_dir)])
    w_plane /= np.linalg.norm(w_plane)

    # -------- DICT TABANLI BÖLGE TOPLAYICI --------
    regions_2d: Dict[str, np.ndarray] = {}
    remain_ = pts_2d.copy()

    if debug:
        print(f"\n[_get_roof_zones] {plane1.polygon_name} | rel={plane1.wind_relation.value}")
        print(f"  leading={leading_edges} exposed={exposed_edges} ccw={is_ccw}")

    # ---------------- İç fonksiyonlar ----------------

    def split_FG(poly_FG, edge):
        """WINDWARD kenar için F1, F2, G bölgelerini üretir."""
        result_L, result_R = create_edge_perp_2d(
            pts_2d, edge.p1_2d, edge.p2_2d, edge.wind_to_2d, e / 4.0
        ) or (None, None)

        if result_L is None or result_R is None:
            return

        F_1, F_G = split(poly_FG, *result_L)
        if F_1 is None or F_G is None:
            return

        G_, F_2 = split(F_G, *result_R)
        if G_ is None or F_2 is None:
            return

        # Dict'e etiketli ekle
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
        if cut is not None:
            M_, N_ = split(poly_M, *cut)
            if M_ is None or N_ is None:
                regions_2d["M"] = poly_M
                return
            regions_2d["M"] = M_
            regions_2d["N"] = N_
        else:
            regions_2d["M"] = poly_M

    # ---------------- Ana döngü ----------------
    sayac=0
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

        H_, FG_ = split(remain_, *clipped)
        if H_ is None or FG_ is None:
            continue

        if edge._global:
            split_FG(FG_, edge)
        else:
            if edge.leading and plane1.wind_relation.value == "LEEWARD" and len(leading_edges)==1:
                regions_2d["K"] = FG_
            else:
                sayac+=1
                regions_2d[f"L{sayac}"] = FG_
            

        remain_ = H_

    # ---------------- Kalan bölge ----------------
    if plane1.wind_relation.value == "PARALLEL":
        split_MN(remain_)
    else:
        regions_2d["M"] = remain_

    # ---------------- F1 vs F2: Z eksenine göre Fu/Fl ata ----------------
    if "F1" in regions_2d and "F2" in regions_2d:
        f1_3d = to_3d(regions_2d["F1"], plane1.proj_info)
        f2_3d = to_3d(regions_2d["F2"], plane1.proj_info)

        if f1_3d is not None and f2_3d is not None:
            # Ortalama Z karşılaştırması
            z1 = float(np.mean(f1_3d[:, 2]))
            z2 = float(np.mean(f2_3d[:, 2]))

            if z1 >= z2:
                regions_2d["Fu"] = regions_2d.pop("F1")
                regions_2d["Fl"] = regions_2d.pop("F2")
            else:
                regions_2d["Fu"] = regions_2d.pop("F2")
                regions_2d["Fl"] = regions_2d.pop("F1")

            if debug:
                print(f"  [F1/F2 → Fu/Fl] z1={z1:.3f} z2={z2:.3f} "
                      f"→ Fu={'F1' if z1 >= z2 else 'F2'}")

    # ---------------- 2D → 3D dönüşümü ----------------
    result: Dict[str, np.ndarray] = {}
    for label, poly_2d in regions_2d.items():
        if not valid_polygon(poly_2d):
            continue
        poly_3d = to_3d(poly_2d, plane1.proj_info)
        if poly_3d is None:
            continue
        result[label] = close_polygon(poly_3d)

    if debug:
        print(f"  [_get_roof_zones] final zones={list(result.keys())}")

    return result



def _get_wall_zones(plane1, e: float, debug: bool = False) -> Dict[str, np.ndarray]:
  
  # --- Projeksiyon bilgisi (roof fonksiyonuyla aynı mantık) ---
  pts_2d = np.asarray(plane1.pts_2d, dtype=float)
  u_dir = np.asarray(plane1.proj_info["u_dir"], dtype=float)
  v_dir = np.asarray(plane1.proj_info["v_dir"], dtype=float)

  # Kapalı poligon
  pts_2d_closed = close_polygon(pts_2d)

  # --- Rüzgar yönünü 2D düzlemde hesapla ---
  wind_3d = np.asarray(plane1.properties["wind_vector"], dtype=float)
  w_plane = np.array([np.dot(wind_3d, u_dir), np.dot(wind_3d, v_dir)])
  w_norm = np.linalg.norm(w_plane)
  if w_norm < 1e-12:
      # Rüzgar duvar düzlemine dik → PARALLEL olamaz, tek bölge dön
      return {"A": close_polygon(plane1.pts_3d)}
  w_dir_2d = w_plane / w_norm

  # Rüzgara dik yön (duvar üzerinde)
  perp_2d = np.array([-w_dir_2d[1], w_dir_2d[0]])

  # --- Duvarın rüzgar yönü boyunca projeksiyon uzunluğu ---
  proj_vals = pts_2d_closed[:-1] @ w_dir_2d
  min_p, max_p = float(np.min(proj_vals)), float(np.max(proj_vals))
  d_len = max_p - min_p

  if d_len < 1e-6:
      return {"A": close_polygon(plane1.pts_3d)}

  # --- e değerini normalize et ---
  # Duvar için bölge uzunlukları e cinsinden ifade edilir.
  # e genelde min(b, h) olarak verilir; burada e/5, 4e/5 kullanılır.
  if e <= 0:
      e = d_len

  a_len = e / 5.0
  b_len = 4.0 * e / 5.0

  # Bölge sınırları (rüzgar yönü boyunca)
  # A: [min_p, min_p + a_len]
  # B: [min_p + a_len, min_p + a_len + b_len]
  # C: kalan
  splits = [a_len, a_len + b_len]
  zone_names = ["A", "B", "C"]

  # Eğer e >= d_len ise, C bölgesi oluşmaz (A+B yeterli)
  if a_len + b_len >= d_len - 1e-5:
      splits = [a_len] if a_len < d_len - 1e-5 else []
      zone_names = ["A", "B"]

  current_poly_2d = pts_2d_closed
  zones: Dict[str, np.ndarray] = {}

  # --- Bölme döngüsü ---
  for idx, offset in enumerate(splits):
      if offset >= d_len - 1e-5:
          break

      split_p = min_p + offset
      ref_pt = w_dir_2d * split_p
      # Rüzgara dik sonsuz çizgi
      p1 = ref_pt - perp_2d * 10000.0
      p2 = ref_pt + perp_2d * 10000.0

      res = _split_by_line_2d(current_poly_2d, p1, p2)
      if res is None:
          break

      part1_2d, part2_2d = res
      if len(part1_2d) < 3 or len(part2_2d) < 3:
          break

      center1 = np.mean(part1_2d[:-1], axis=0) @ w_dir_2d
      center2 = np.mean(part2_2d[:-1], axis=0) @ w_dir_2d

      if center1 < center2:
          zone_2d, current_poly_2d = part1_2d, close_polygon(part2_2d)
      else:
          zone_2d, current_poly_2d = part2_2d, close_polygon(part1_2d)

      # 2D → 3D
      zone_3d = _unproject_local_2d_to_3d(zone_2d, plane1.proj_info)
      zones[zone_names[idx]] = close_polygon(zone_3d)
      if debug:
        print("zone_names[idx]",close_polygon(zone_3d))


  # --- Kalan bölge (C veya B) ---
  remaining_name = zone_names[len(zones)] if len(zones) < len(zone_names) else "C"
  remaining_3d = _unproject_local_2d_to_3d(current_poly_2d, plane1.proj_info)
  zones[remaining_name] = close_polygon(remaining_3d)

  if debug:
      print(f"\n[_get_wall_parallel_zones] {plane1.polygon_name}")
      print(f"  w_dir_2d={w_dir_2d}, d_len={d_len:.3f}, e={e:.3f}")
      print(f"  splits={splits}, zones={list(zones.keys())}")

  return zones
  
  
def get_definition_regions(all_surfaces, regions):
    
    # 1. Determine if the overall roof structure is MONOPITCH
    surface_all_zones= {}
    table_type= None
    table_type_dir= 0
    roof_surfaces = {name: s for name, s in all_surfaces.items() if getattr(s.surface_type, "value", s.surface_type) == "ROOF"}
    roof_relations = [s.properties.get("wind_relation", None).value for s in roof_surfaces.values()]

    is_overall_monopitch = False
    if len(roof_relations) > 0 and all(x == roof_relations[0] for x in roof_relations):
    
        is_overall_monopitch = True

    # 2. Iterate through all surfaces for individual classification
    for sname, plane1 in all_surfaces.items():
        all_zones= []
        wind_relation = plane1.properties.get("wind_relation", None)
        if wind_relation is None:
            continue

        global_leading = plane1.properties.get("global_leading", False)
        surface_type = getattr(plane1.surface_type, "value", plane1.surface_type)

        if surface_type == "ROOF":
            if not is_overall_monopitch: # Apply DUOPITCH/HIPPED if the roof is not overall MONOPITCH
                if wind_relation.value == "PARALLEL" and global_leading:
                    print(f"DUOPITCH ROOF SURFACE: {sname}")
                    table_type = "DUOPITCH"
                    table_type_dir= 90
                else:
                    print(f"HIPPED ROOF SURFACE: {sname}")
                    table_type = "HIPPED"
                    table_type_dir= 0
            else:
                table_type= "MONOPITCH"
                if wind_relation.value == "WINDWARD":
                    table_type_dir= 0
                elif wind_relation.value == "LEEWARD":
                    table_type_dir= 180
                elif wind_relation.value == "PARALLEL":
                    table_type_dir= 90
          
        else: # It's a WALL surface
            table_type = "WALL"

          
        all_coords = np.vstack(list(plane1.pts_3d))
        x_range = all_coords[:, 0].max() - all_coords[:, 0].min()
        y_range = all_coords[:, 1].max() - all_coords[:, 1].min()
        z_range = all_coords[:, 2].max() - all_coords[:, 2].min()
        d= max(x_range, y_range)
        h=z_range

        if table_type == "WALL":
            if d>0:
                pitch= h/d
            else:
                continue
        else:
            pitch= plane1.pitch


        for reg_name,coords in regions[sname].items():
          
          
            if wind_relation.value == "WINDWARD":
                if table_type == "WALL":
                    label= "D"
                else:
                    label= reg_name[:1]
                    if label=="M":
                        label = "H"
            elif wind_relation.value == "LEEWARD":
                if table_type == "WALL":
                  label= "E"
                else:
                  label= reg_name[:1]
                  if label=="M":
                        label = "I"
                  elif label=="L":
                        label = "J"

            elif wind_relation.value == "PARALLEL":
                if table_type == "WALL":
                    label= reg_name
                elif table_type == "MONOPITCH":
                    if reg_name=="M":
                        label="H"
                    elif reg_name=="N":
                        label="I"
                    else:
                        label= reg_name

                elif table_type == "DUOPITCH":
                    if reg_name=="Fl":
                        label="F"
                    elif reg_name=="Fu":
                        label="G"
                    elif reg_name=="M":
                        label="H"
                    elif reg_name=="N":
                        label="I"
                    else:
                        label= reg_name
                else:
                    label= reg_name[:1]
            zone = Zone(
              label= label,
              coords=coords,
              surface=sname,
              table_type=table_type,
              table_type_dir=table_type_dir,
              pitch= pitch,
            )

            all_zones.append(zone)
        surface_all_zones[sname]= all_zones
    return surface_all_zones
      
def show_zones(building, all_wind_zones):
    import matplotlib.pyplot as plt
    import matplotlib
    from mpl_toolkits.mplot3d import Axes3D
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    import numpy as np

    # ================================================================
    # Data Source: all_wind_zones (List of Zone objects)
    # ================================================================

    # ---- Tüm koordinatları düzleştir ----
    all_polys = []
    for poly_zones in all_wind_zones.values():
        for zone_obj in poly_zones:
            all_polys.append(np.asarray(zone_obj.coords, dtype=float))

    if not all_polys:
        raise ValueError("all_wind_zones boş!")

    all_coords = np.vstack(all_polys)

    fig = plt.figure(figsize=(13, 10))
    ax = fig.add_subplot(111, projection='3d')

    # ---- Eksen aralıkları ----
    x_range = all_coords[:, 0].max() - all_coords[:, 0].min()
    y_range = all_coords[:, 1].max() - all_coords[:, 1].min()
    z_range = all_coords[:, 2].max() - all_coords[:, 2].min()
    max_range = max(x_range, y_range, z_range)

    mid_x = (all_coords[:, 0].max() + all_coords[:, 0].min()) / 2
    mid_y = (all_coords[:, 1].max() + all_coords[:, 1].min()) / 2
    mid_z = (all_coords[:, 2].max() + all_coords[:, 2].min()) / 2

    ax.set_xlim(mid_x - max_range / 2, mid_x + max_range / 2)
    ax.set_ylim(mid_y - max_range / 2, mid_y + max_range / 2)
    ax.set_zlim(mid_z - max_range / 2, mid_z + max_range / 2)
    ax.set_box_aspect([1, 1, 1])

    # ---- CPE10 değerlerini topla ve normalize et ----
    cpe10_values = []
    for poly_zones in all_wind_zones.values():
        for zone_obj in poly_zones:
            cpe = zone_obj.cpe10
            if isinstance(cpe, tuple):
                cpe10_values.append(cpe[0]) # Tuple ise ilk değeri al
            else:
                cpe10_values.append(cpe)

    # Negatif ve pozitif cpe10 değerlerini ayır
    neg_cpe = [v for v in cpe10_values if v < 0]
    pos_cpe = [v for v in cpe10_values if v >= 0]

    min_neg_abs = abs(min(neg_cpe)) if neg_cpe else 0
    max_pos = max(pos_cpe) if pos_cpe else 0

    # Renk haritaları
    # Negatif değerler için: LightBlue -> DarkBlue
    neg_cmap = matplotlib.colormaps.get_cmap('Blues')
    # Pozitif değerler için: LightRed -> DarkRed
    pos_cmap = matplotlib.colormaps.get_cmap('Reds')

    # ================================================================
    # HER POLİGONU ÇİZ + ETİKETİNİ YAZ
    # ================================================================
    for poly_zones in all_wind_zones.values():
        for zone_obj in poly_zones:
            coords = np.asarray(zone_obj.coords, dtype=float)
            zlabel = zone_obj.label

            cpe = zone_obj.cpe10
            if isinstance(cpe, tuple):
                current_cpe = cpe[0]
            else:
                current_cpe = cpe

            # CPE değerine göre renk ataması
            if current_cpe < 0:
                if min_neg_abs > 0:
                    # Negatif değerleri 0-1 aralığına normalize et (mutlak değer olarak)
                    norm_val = abs(current_cpe) / min_neg_abs
                    facecolor = neg_cmap(norm_val)
                else:
                    facecolor = neg_cmap(0.5) # Fallback if no negative values
            else:
                if max_pos > 0:
                    # Pozitif değerleri 0-1 aralığına normalize et
                    norm_val = current_cpe / max_pos
                    facecolor = pos_cmap(norm_val)
                else:
                    facecolor = pos_cmap(0.5) # Fallback if no positive values

            # Poligonu çiz
            col = Poly3DCollection(
                [coords],
                alpha=0.6, # Şeffaflığı biraz artır
                facecolor=facecolor,
                edgecolor='black',
                linewidths=1.0,
            )
            ax.add_collection3d(col)

            # ---- Etiket konumu: ağırlık merkezi ----
            pts = coords
            if len(pts) > 1 and np.allclose(pts[0], pts[-1], atol=1e-9):
                pts = pts[:-1]

            centroid = pts.mean(axis=0)

            # Etiket metni: "Bölge (CPE10)"
            text = f"{zlabel} ({current_cpe:.2f})"

            ax.text(
                centroid[0],
                centroid[1],
                centroid[2],
                text,
                fontsize=8,
                fontweight='bold',
                color='black',
                ha='center',
                va='center',
                bbox=dict(
                    boxstyle='round,pad=0.2',
                    facecolor='white',
                    edgecolor='gray',
                    alpha=0.7,
                    linewidth=0.5,
                ),
                zorder=10,
            )

    # ================================================================
    # RÜZGAR VEKTÖRÜ
    # ================================================================
    wind_vector = building.w_dir
    w_norm = np.linalg.norm(wind_vector)
    wind_dir_norm = wind_vector / w_norm if w_norm > 0 else np.array([1.0, 0.0, 0.0])

    arrow_start_x = mid_x - max_range / 2 - 2 * max_range / 10
    arrow_start_y = mid_y
    arrow_start_z = mid_z
    arrow_length = max_range / 5

    ax.quiver(
        arrow_start_x,
        arrow_start_y,
        arrow_start_z,
        wind_dir_norm[0] * arrow_length,
        wind_dir_norm[1] * arrow_length,
        wind_dir_norm[2] * arrow_length,
        color='red',
        arrow_length_ratio=0.3,
        label='Wind Vector',
        linewidth=2,
    )

    # ================================================================
    # EKSEN VE BAŞLIK
    # ================================================================
    ax.set_xlabel('X Coordinate')
    ax.set_ylabel('Y Coordinate')
    ax.set_zlabel('Z Coordinate')
    ax.set_title('3D Visualization of Wind Zones by CPE10')
    ax.grid(True)

    # Renk çubuklarını ekle (opsiyonel)
    # Negatif için
    if min_neg_abs > 0:
        cbar_neg_ax = fig.add_axes([0.02, 0.3, 0.02, 0.3]) # x, y, width, height
        norm_neg = matplotlib.colors.Normalize(vmin=-min_neg_abs, vmax=0)
        cbar_neg = matplotlib.colorbar.ColorbarBase(cbar_neg_ax, cmap=neg_cmap, norm=norm_neg, orientation='vertical')
        cbar_neg.set_label('Negative CPE10')

    # Pozitif için
    if max_pos > 0:
        cbar_pos_ax = fig.add_axes([0.06, 0.3, 0.02, 0.3]) # x, y, width, height
        norm_pos = matplotlib.colors.Normalize(vmin=0, vmax=max_pos)
        cbar_pos = matplotlib.colorbar.ColorbarBase(cbar_pos_ax, cmap=pos_cmap, norm=norm_pos, orientation='vertical')
        cbar_pos.set_label('Positive CPE10')

    plt.tight_layout(rect=[0.1, 0, 1, 1]) # Colorbar'lar için alanı ayarla
    plt.show()

import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton
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
    

class WindViewer(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wind Viewer")

        self.view = View3D()

        buttons = QHBoxLayout()
        for name in W_LIST:
            btn = QPushButton(name)
            btn.clicked.connect(lambda _, w=name: self.set_wind(w))
            buttons.addWidget(btn)

        layout = QVBoxLayout(self)
        layout.addLayout(buttons)
        layout.addWidget(self.view)

        # self.set_wind("y+")
        self.view.set_data(points=points,polygons=polygons)
        self.view.data_changed.connect(lambda t, i, v: print(f"{t}:{i} -> {v}"))

    def set_wind(self, w: str):
        print(f"\n{'=' * 40}\nWIND: {w}\n{'=' * 40}")
        view_data= self.view.get_all_data()
        points= view_data["points"]
        
        polygons= view_data["polygons"]
        building = BuildingWindEngine(
            points=points,
            polygons=polygons,
            v_b0=28.0,
            terrain="Kategori III",
            w_dir=W_LIST[w],
            scale_factor=1,
        )
        
        print("\nwind_parameters:\n", dict_tree(building.get_summary()))
        all_surfaces = building.analysis_all_roof_wind(W_LIST[w])
        render_lines = {}
        for name in polygons:
            print(name)
            if all_surfaces[name].surface_type.value=="WALL":
                render_lines[name]= {}
                zones= _get_wall_zones(all_surfaces[name], building.e, False)
                render_lines[name].update(zones)
    
            elif all_surfaces[name].surface_type.value=="ROOF":
                render_lines[name]= {}
                
                zones= _get_roof_zones(all_surfaces[name], building.e, False)
                
                render_lines[name].update(zones)
            
    
        all_wind_zones= get_definition_regions(all_surfaces, render_lines)

        # all_polys = []
        # for poly_zones in all_wind_zones.values():
        #     for zone_obj in poly_zones:
        #         all_polys.append(np.asarray(zone_obj.coords, dtype=float))

        # print(all_wind_zones)
        w_vec= W_LIST[w]
        w_perp_dir = np.array([-w_vec[1], w_vec[0],0])
        geom= building.calculate_obb_and_geometry(w_perp_dir, [0,0,0], points)
        w_render_lines= building.generate_render_lines(geom)
        self.view.zones = all_wind_zones
        self.view.lines = w_render_lines
        
        self.view._visibility_states.clear()
        self.view.rebuild()
        self.view.update()

if __name__ == "__main__":
    
    app = QApplication(sys.argv)
    window = WindViewer()
    window.resize(1000, 700)
    window.show()
    sys.exit(app.exec())