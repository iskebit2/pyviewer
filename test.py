from windcalc.windengine import BuildingWindEngine

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

p1_selected= (0.0, 0.0, 0.0)
p2_selected= (12000.0, 0.0, 0.0)

building= BuildingWindEngine(points=points, polygons=polygons, scale_factor=1000)

geom_results = building.calculate_obb_and_geometry(
        p1_selected, p2_selected, building.raw_points
    )

render_lines = building.generate_render_lines(geom_results)

print(building.geometry)
print(render_lines)
print(geom_results)