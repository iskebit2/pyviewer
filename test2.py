from windcalc.windengine import BuildingWindEngine, SurfaceType

import numpy as np
from typing import List, Dict, Tuple, Optional

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


def polygon_edges_to_render(polygon: np.ndarray) -> List[Dict]:
    """Poligonun kenarlarını çizim/render için çiftler halinde döndürür."""
    pts = close_polygon(polygon)
    n = len(pts) - 1
    return [
        [pts[i], pts[i + 1]]
        for i in range(n)
    ]


def _clip_line_to_polygon_2d(line_p1: np.ndarray, line_p2: np.ndarray, polygon: np.ndarray) -> Optional[Tuple[np.ndarray, np.ndarray]]:
    """Sonsuz 2D çizginin 2D poligon sınırıyla kesiştiği iki ucu bulur."""
    p1 = np.asarray(line_p1, dtype=float)
    p2 = np.asarray(line_p2, dtype=float)

    direction = p2 - p1
    dir_len = np.linalg.norm(direction)
    if dir_len < 1e-8:
        return None

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

        # Poligon kenarı sınırları içinde kesişim kontrolü
        if -1e-10 <= u <= 1 + 1e-10:
            intersections.append(p1 + t * direction)

    if len(intersections) < 2:
        return None

    # Çizgi yönündeki sıralamaya göre sınır kesişim noktalarını seç
    intersections.sort(key=lambda p: np.dot(p - p1, direction))
    return intersections[0], intersections[-1]


def offset_edge_2d(
    polygon_2d: np.ndarray,
    p1_2d: np.ndarray,
    p2_2d: np.ndarray,
    w_vector_2d: np.ndarray,
    e: float,
    perp: bool = False
) -> Optional[Tuple]:
    """Kenarı saf 2D düzlemde w_vector_2d yönünde veya dik yönde offsetler."""
    polygon_2d = np.asarray(polygon_2d, dtype=float)
    p1 = np.asarray(p1_2d, dtype=float)
    p2 = np.asarray(p2_2d, dtype=float)

    edge_vec = p2 - p1
    edge_len = np.linalg.norm(edge_vec)
    if edge_len < 1e-8:
        return None
    edge_dir = edge_vec / edge_len

    if perp:
        # Kenara dik yönde ayırma çizgileri
        perp_dir = np.array([-edge_dir[1], edge_dir[0]])
        d_L = e / 4
        EXT = e / 10

        split1 = p1 + edge_dir * d_L
        split2 = p2 - edge_dir * d_L

        return (
            (split1, split1 + perp_dir * EXT),
            (split2, split2 + perp_dir * EXT)
        )

    # 2D Rüzgar/Offset yönü
    w_2d = np.asarray(w_vector_2d, dtype=float)
    w_len = np.linalg.norm(w_2d)
    if w_len < 1e-8:
        return None
    w_dir = w_2d / w_len

    d_L = e / 10
    line_L_p1 = p1 + w_dir * d_L
    line_L_p2 = p2 + w_dir * d_L

    # Offsetlenmiş çizgiyi 2D poligon sınırlarına göre kırp
    clipped = _clip_line_to_polygon_2d(line_L_p1, line_L_p2, polygon_2d)
    if clipped is None:
        return None

    return clipped


def _split_by_line_2d(poly_2d: np.ndarray, p1: np.ndarray, p2: np.ndarray) -> Optional[Tuple[np.ndarray, np.ndarray]]:
    """2D poligonu bir çizgi ile ikiye böler."""
    line_dir = p2 - p1
    if np.linalg.norm(line_dir) < 1e-8:
        return ([],[])

    def side(p):
        return line_dir[0] * (p[1] - p1[1]) - line_dir[1] * (p[0] - p1[0])

    pts = _open_polygon(poly_2d)
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
        return ([],[])

    pos = close_polygon(pos)
    neg = close_polygon(neg)

    def area(p):
        return 0.5 * abs(np.sum(p[:-1, 0] * p[1:, 1] - p[1:, 0] * p[:-1, 1]))

    return (pos, neg) if area(pos) >= 1e-4 and area(neg) >= 1e-4 else None

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




def get_same_axis_edge(edges_, leading_edges):
    ed1_same_axis_edges_ = {}
    for ke1_, ed1_ in edges_.items():
        if not ke1_ in leading_edges:
            continue
        
        if ed1_.same_axis:
            
                
            temp_same= []
            for ed1_s in ed1_.same_axis:
                
                
                ed1_surface = ed1_s.get('surface', False)
                ed1_surface_edge = ed1_s.get('surface_edge', False)
                ed1_same_edge = ed1_s.get('same_edge', False)
                if not ed1_same_edge:
                    temp_same.append([ed1_surface, ed1_surface_edge])
            if temp_same:
                ed1_same_axis_edges_[ke1_]= temp_same
                
    return ed1_same_axis_edges_
        
   

def get_surface_results(plane_name, w, all_surfaces_w):
    print("\n>",plane_name)
    print(f"\nWind vector: {w} : {w_list[w]}")

    render_lines = []
    plane1= all_surfaces_w[w][plane_name]
    polygon= plane1.pts_2d
    
    for kk in ['surface_type', 'polygon', 'angle', 'pitch',  'wind_vector', 'polygon_direction_xy', 'wind_relation', 'global_leading', 'any_shared']:
        print(f" > {kk:20}: {plane1.properties.get(kk, '')}")
    if plane1.surface_type == SurfaceType.WALL:
        return

    exposed_edges= [ke_ for ke_, ed_ in plane1.edges.items() if ed_.exposed]
    leading_edges= [ke_ for ke_, ed_ in plane1.edges.items() if ed_.leading]
    print(f" > exposed_edges: {exposed_edges}")
    print(f" > leading_edges: {leading_edges}")

    same_axis= get_same_axis_edge(plane1.edges, leading_edges)
    
    print(f" > same_axis: {same_axis}")
    # for ke_, ed_ in plane1.edges.items():
    #     print("\n > edge:",ke_)
    #     print("   > points:",ed_.p1, ed_.p2)
    #     print("   > vector_xy:",ed_.vector_xy, "| direction_xy:",ed_.direction_xy)
    #     print("   > angle:",ed_.angle, " | length:",ed_.length)
    #     print("   > vertical:",ed_.vertical)
    #     print("   > exposed:",ed_.exposed)
    #     print("   > leading:",ed_.leading)
    #     print("   > shared:",ed_.shared)
    #     print("   > same_axis:",ed_.same_axis)
    any_shared_= plane1.properties.get("any_shared", False)
    print(f"edge indexes:{leading_edges} FG bölgesi herzaman iki kenardan e/4 kadar offset edilip F bölgeleri bulunacak kalan orta bölge G")

    edges= plane1.edges
    e= building.e
    w_vector = w_list[w]
    pts_2d= plane1.pts_2d
    if plane1.wind_relation.value=="WINDWARD":
        print("WINDWARD")
        
        if any_shared_:
            print("DUOPITCH", "HIPPED")
        else:
            print("MONOPITCH")
            
        print("FGH", leading_edges, "kenarlar e/10 offset et ve FG olarak işaretle. poligonun kalan kısmı H")
        print("Bakılacak tablo:",0)

        print("Zone geometry:", polygon)
        for idx_ in leading_edges:
            edge= edges[idx_]
            p1_3d, p2_3d = edge.p1[:2], edge.p2[:2]
            res_wind = offset_edge_2d(polygon, p1_3d, p2_3d, w_vector[:2], e)
            res_perp = offset_edge_2d(polygon, p1_3d, p2_3d, w_vector[:2], e, perp=True)
            if res_wind is None or res_perp is None:
                raise RuntimeError("Offset hesaplanamadı")
            line_wind_p1, line_wind_p2 = res_wind
            (perp1_start, perp1_end), (perp2_start, perp2_end) = res_perp

            print(f"res_wind: {res_wind}")
            print(f"res_wind: {res_perp}")
            

            (pos, neg)= _split_by_line_2d(pts_2d, line_wind_p1, line_wind_p2)

            print("_split_by_line_2d:")
            poly_extract= polygon_edges_to_render(plane1._unproject_2d_to_3d(neg))
            render_lines.append(poly_extract)
            poly_extract= polygon_edges_to_render(plane1._unproject_2d_to_3d(pos))
            render_lines.append(poly_extract)
            
            

            (pos_F1, neg_GF)= _split_by_line_2d(neg, perp1_start, perp1_end)
            (pos_F2, neg_G)= _split_by_line_2d(neg_GF, perp2_start, perp2_end)

            print("_split_by_line_2d:")
            print(" <--:",plane1._unproject_2d_to_3d(neg))
            print(" -->:",plane1._unproject_2d_to_3d(pos))

            print("_split_by_line_2d:")
            print(" <--:F1",plane1._unproject_2d_to_3d(pos_F1))
            print(" -->F2:",plane1._unproject_2d_to_3d(pos_F2))
            print(" -->G:",plane1._unproject_2d_to_3d(neg_G))
            if not pos_F1 is None:
                poly_extract= polygon_edges_to_render(plane1._unproject_2d_to_3d(pos_F1))
                render_lines.append(poly_extract)

            if not pos_F2 is None:
                poly_extract= polygon_edges_to_render(plane1._unproject_2d_to_3d(pos_F2))
                render_lines.append(poly_extract)

            if not neg_G is None:
                poly_extract= polygon_edges_to_render(plane1._unproject_2d_to_3d(neg_G))
                render_lines.append(poly_extract)

            
        

    elif plane1.wind_relation.value=="LEEWARD":
        print("LEEWARD")
        if any_shared_:
            print("DUOPITCH", "HIPPED")
            print("DUOPITCH veya HIPPED çatı tipi farketmiyor ama cpe değerlerini kontrol et")
            print("DUOPITCH için JI HIPPED için KJI.. önce türbülans alanı için leading_edges kenarları e/10 offset yap",  f"edge indexes:{leading_edges}", "K, diğer exposed kenarlar:",f"edge indexes:{exposed_edges}","J olur. yüzeyin geri kalanı her zaman I")

            for idx_ in leading_edges:
                edge= edges[idx_]
                p1_3d, p2_3d = edge.p1[:2], edge.p2[:2]
                res_wind = offset_edge_2d(polygon, p1_3d, p2_3d, w_vector[:2], e)
                
                if res_wind is None:
                    raise RuntimeError("Offset hesaplanamadı")
                line_wind_p1, line_wind_p2 = res_wind
                
                
    
                (pos, neg)= _split_by_line_2d(pts_2d, line_wind_p1, line_wind_p2)
    
                print("_split_by_line_2d:")
                poly_extract= polygon_edges_to_render(plane1._unproject_2d_to_3d(neg))
                render_lines.append(poly_extract)

            for idx in exposed_edges:
                if not idx in leading_edges:
                    edge= edges[idx_]
                    p1_3d, p2_3d = edge.p1[:2], edge.p2[:2]
                    res_wind = offset_edge_2d(neg, p1_3d, p2_3d, w_vector[:2], e)
                    
                    if res_wind is None:
                        raise RuntimeError("Offset hesaplanamadı")
                    line_wind_p1, line_wind_p2 = res_wind
                    
                    
        
                    (pos2, neg2)= _split_by_line_2d(pos, line_wind_p1, line_wind_p2)
                    print("---> neg2:",neg2)
                    if neg2:
                        poly_extract= polygon_edges_to_render(plane1._unproject_2d_to_3d(neg2))
                        render_lines.append(poly_extract)
            if pos2:
                poly_extract= polygon_edges_to_render(plane1._unproject_2d_to_3d(pos2))
                render_lines.append(poly_extract)


        else:
            print("MONOPITCH")
            print("Bakılacak tablo:",180)
            print("FGH", f"edge indexes:{leading_edges}", "kenarlar e/10 offset et ve FG olarak işaretle. alçak saçak tarafı Fl, yüksek saçak tarafı Fu poligonun kalan kısmı H")
        
    elif plane1.wind_relation.value=="PARALLEL":
        print("PARALLEL")
        if any_shared_:
            
            if same_axis:
                print("DUOPITCH")
                print("Bakılacak tablo:",90)
                print("FGHI",  f"edge indexes:{leading_edges}", "kenarlar e/10 offset et ve FG olarak işaretle.")
                print("FG Bölgesi aynı akstaki diğer kenara uzayacak.", f"edge indexes:{leading_edges} alçak kot e/4 mesafede F kalan bölge G")
                print("poligonun kalan kısmı e/2 ye kadar H sonrası I")
            else:
                print("HIPPED")
                print("Bakılacak tablo:",0)
                print("LMN", f"edge indexes:{leading_edges}", "kenarlar e/10 offset et ve L olarak işaretle. poligonun kalan kısmı e/2 ye kadar M sonrası N")
        else:
            print("MONOPITCH")
            print("Bakılacak tablo:",90)
            print("FGH", f"edge indexes:{leading_edges}", "kenarlar e/10 offset et ve FG olarak işaretle. poligonun kalan kısmı e/2 ye kadar H sonrası I")

    return render_lines

points = {
                "P1": (0.0, 0.0, 0.0),
                "P2": (12000.0, 0.0, 0.0),
                "P3": (12000.0, 9000.0, 0.0),
                "P4": (0.0, 9000.0, 0.0),
                "P5": (0.0, 0.0, 4000.0),
                "P6": (12000.0, 0.0, 4000.0),
                "P7": (12000.0, 9000.0, 4000.0),
                "P8": (0.0, 9000.0, 4000.0),
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

print("\nbuilding analysis:\n")

wind_parameters= building.get_summary()
print("\nwind_parameters:\n", dict_tree(wind_parameters))

all_surfaces_w= {}
w_list= {"x+":[1,0,0], "y+":[0,1,0], "x-":[-1,0,0], "y-": [0,-1,0]}
for w in w_list:
    all_surfaces_w[w]= building.analysis_all_roof_wind(w_list[w])

plane_name= "C2"
render_lines= []

w= "y+"
for plane_name in polygons:
    plane1= all_surfaces_w[w][plane_name]
    # plane1.analyze_wind_relation(w_list[w])
    print(plane1.wind_relation)
    for kk in ['name','surface_type', 'polygon', 'angle', 'pitch',  'wind_vector', 'polygon_direction_xy', 'wind_relation', 'global_leading', 'any_shared']:
        print(f" > {kk:20}: {plane1.properties.get(kk, '')}")
    render_lines1=  get_surface_results(plane_name, w, all_surfaces_w)
    if render_lines1:
        render_lines.extend(render_lines1)


from canvas3d import View3D

import sys
from PySide6.QtWidgets import QApplication

def get_app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


app = get_app()

view = View3D()
view.set_data(
    points={"O": [0, 0, 0]},
    lines=render_lines
)

view.resize(1000, 700)
view.show()

sys.exit(app.exec())

