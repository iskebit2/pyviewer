# main_wind.py
import json
import matplotlib.pyplot as plt

from windcalc.analysis import analyze
from windcalc.visualize import draw_bundle_grid
from windcalc.report import build_full_report, print_console_summary


def _load_from_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('points', {}), data.get('polygons', {})
    except Exception as e:
        print(f"Dosya açılamadı: {e}")
        return {}, {}


def main():
    for file_ in [
        # "examples/monopitch_roof.json",
        # "examples/duopitch_roof.json",
        # "examples/hipped_roof.json",
        "examples/complex_roof.json",
    ]:
        raw_points, polygons = _load_from_file(file_)
        if not raw_points or not polygons:
            continue

        scale = 1.0
        points = {n: tuple(c * scale for c in coords)
                  for n, coords in raw_points.items()}

        # 1) ANALİZ
        bundle = analyze(points=points, polygons=polygons,
                         v_b0=28.0, terrain="Kategori III")

        # 2) KONSOL ÖZETİ
        print_console_summary(bundle)

        # 3) TÜM YÖNLER DOCX RAPORU
        base = file_.split("/")[-1].replace(".json", "")
        build_full_report(bundle, filename=f"rapor_{base}.docx")

        # 4) 2x2 GRID GÖRSEL
        fig = draw_bundle_grid(bundle, figsize=(12, 10))
        # plt.show()


if __name__ == "__main__":
    main()

    from utils.report_dataframe import ReportDataFrame
    import pandas as pd

    r = ReportDataFrame({"a": [1, 2]}, custom_title="t")
    print(isinstance(r, pd.DataFrame))   # True beklenir
    print(r.empty)                        # False beklenir
    print(hasattr(r, "df"))               # False beklenir