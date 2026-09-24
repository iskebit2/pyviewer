from math import isclose

import numpy as np

from windcalc.wind_data import WindRelation

ANGLE_TOL = 1e-6





TABLE_ANGLE = {
    "MONOPITCH": {
        "WINDWARD": 0,
        "LEEWARD": 180,
        "PARALLEL": 90,
    },
    "DUOPITCH": {
        "WINDWARD": 0,
        "LEEWARD": 0,
        "PARALLEL": 90,
    },
    "HIPPED": {
        "WINDWARD": 0,
        "LEEWARD": 0,
        "PARALLEL": 0,
    },
}

def roof_slopes(roof_surfaces, tol=1e-6):

    parallel = [
        p for p in roof_surfaces
        if p.properties["wind_relation"] == WindRelation.PARALLEL
    ]

    angles = [
        p.properties["angle"]
        for p in parallel
    ]

    return angles

def classify_roof(plane, roof_surfaces):

    relations = [
        p.properties["wind_relation"]
        for p in roof_surfaces
    ]

    parallel = [
        p for p in roof_surfaces
        if p.properties["wind_relation"] == WindRelation.PARALLEL
    ]

    windward = [
        p for p in roof_surfaces
        if p.properties["wind_relation"] == WindRelation.WINDWARD
    ]

    leeward = [
        p for p in roof_surfaces
        if p.properties["wind_relation"] == WindRelation.LEEWARD
    ]

    leading = [
        p for p in roof_surfaces
        if p.properties.get("global_leading", False)
    ]

    # --------------------------------------------------
    # HIPPED
    # --------------------------------------------------
    # Global leading yüzey WINDWARD olmalı
    # ve ayrıca PARALLEL yüzey bulunmalı.
    if (
        any(
            p.properties["wind_relation"] == WindRelation.WINDWARD
            for p in leading
        )
        and parallel
    ):
        roof_type = "HIPPED"

    # --------------------------------------------------
    # DUOPITCH
    # --------------------------------------------------
    # Global leading kenar PARALLEL yüzeydeyse
    elif any(
        p.properties["wind_relation"] == WindRelation.PARALLEL
        for p in leading
    ):
        roof_type = "DUOPITCH"

    # WINDWARD + LEEWARD
    elif windward and leeward:
        roof_type = "DUOPITCH"

    # Sadece PARALLEL
    elif len(parallel) == len(roof_surfaces):

        angles = [
            p.properties["angle"]
            for p in parallel
        ]

        # aynı eğim yönü
        if all(abs(a - angles[0]) < 1e-6 for a in angles):
            roof_type = "MONOPITCH"
        else:
            roof_type = "DUOPITCH"

    else:
        roof_type = "MONOPITCH"

    angles = roof_slopes(roof_surfaces)

    if len(angles) >= 2:

        same_direction = all(
            a * angles[0] > 0
            for a in angles[1:]
        )

        if same_direction:
            roof_type = "MONOPITCH"
        else:
            roof_type = "DUOPITCH"
            
    relation = plane.properties["wind_relation"].value

    table_angle = TABLE_ANGLE[roof_type][relation]

    return roof_type, table_angle
    
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
    
    
def get_neighbors(surf, all_surfaces):
    neighbors = {}

    for edge in surf.edges.values():
        for shrd in edge.shared:
            if shrd["is_coplanar_shared"]:
                continue

            name = shrd["surface"]
            neighbors[name] = all_surfaces[name]

    return list(neighbors.values())


def has_global_leading_neighbor(surf, neighbors):
    for n in neighbors:
        if n.global_leading and n.wind_relation == surf.wind_relation:
            return True

    return False

def classify_surface(surf, all_surfaces):

    neighbors = get_neighbors(surf, all_surfaces)
    relations = {n.wind_relation for n in neighbors}

    if surf.wind_relation == WindRelation.WINDWARD:

        if WindRelation.PARALLEL in relations:
            return "HIPPED"

        if relations and relations <= {WindRelation.LEEWARD}:
            return "DUOPITCH"

        return "MONOPITCH"

    if surf.wind_relation == WindRelation.LEEWARD:

        if WindRelation.PARALLEL in relations:
            return "HIPPED"

        if relations and relations <= {WindRelation.WINDWARD}:
            return "DUOPITCH"

        return "MONOPITCH"

    if surf.wind_relation == WindRelation.PARALLEL:

        if not neighbors:
            return "MONOPITCH"

        if all(np.isclose(n.angle, surf.angle, atol=1e-6)
               for n in neighbors):
            return "MONOPITCH"

        if has_global_leading_neighbor(surf, neighbors):
            return "DUOPITCH"

        return "HIPPED"

    return None

def _analysis_classify_all_surface(surfaces_items):

    for surface in surfaces_items.values():
    
        if surface.surface_type.value != "ROOF":
            continue

        surface.roof_type = classify_surface(surface, all_surfaces)
        

def _analysis_global_edges(surfaces_items):

    global_leading = []

    for surface in surfaces_items.values():

        if surface.surface_type.value != "ROOF":
            continue

        # Her rüzgar analizinde sıfırla
        surface.global_leading = False

        for edge in surface.edges.values():

            edge._global = False

            if not edge.leading:
                continue

            # Shared değilse global
            if not edge.shared:
                edge._global = True
                surface.global_leading = True
                global_leading.append(edge)
                continue

            # Shared ise karşı edge'leri kontrol et
            is_global = False

            for shared in edge.shared:

                if shared["same_edge"]:
                    is_global = False
                    break

            if is_global:
                edge._global = True
                surface.global_leading = True
                global_leading.append(edge)

    return global_leading