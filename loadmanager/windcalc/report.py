import numpy as np
import pandas as pd

import io
from typing import Iterable, Optional, Dict, List, Tuple, Any
from dataclasses import dataclass, field

from data.wind_data import CPI_NEGATIVE, CPI_POSITIVE, TOL, WindRelation
from utils.report_dataframe import ReportDataFrame
from windcalc.surface import Surface
from windcalc.windengine import WindEngine
from windcalc.zone_generator import _get_roof_zones, _get_wall_zones
from docx.shared import Cm
import matplotlib
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from matplotlib.lines import Line2D
from math import isclose





def get_parameters_report(building) -> ReportDataFrame:
    summary = building.report()
    h = building.geometry.get("h", 1)
    z_ref = max(h, building.zmin)

    params = [
        ("Bina Yüksekliği (h)", f"{h:.2f} m"),
        ("Arazi Kategorisi", building.terrain),
        ("Pürüzlülük Uzunluğu (z₀)", f"{building.z0:.3f} m"),
        ("Minimum Yükseklik (z_min)", f"{building.zmin:.1f} m"),
        ("Referans Yükseklik (z_ref)", f"{z_ref:.3f} m"),
        ("Temel Rüzgar Hızı (v_b0)", f"{building.v_b0:.1f} m/s"),
        ("Hava Yoğunluğu (ρ)", f"{building.rho:.2f} kg/m³"),
        ("Temel Hız Basıncı (q_b)", f"{building.q_b:.3f} kN/m²"),
        ("Pürüzlülük Katsayısı (k_r)", f"{building.kr:.3f}"),
        ("Arazi Faktörü (c_r)", f"{building.cr:.3f}"),
        ("Türbülans Şiddeti (I_v)", f"{building.Iv:.3f}"),
        ("Maruziyet Katsayısı (c_e)", f"{building.ce:.3f}"),
        ("Pik Hız Basıncı (q_p)", f"{building.q_p:.3f} kN/m²"),
        ("İç Basınç (+)", f"{CPI_POSITIVE:.2f}"),
        ("İç Basınç (-)", f"{CPI_NEGATIVE:.2f}"),
    ]

    data = {
        "Parametre": [p[0] for p in params],
        "Değer": [p[1] for p in params],
    }

    desc = f"""
    Rüzgar Yükü Analizi - TS EN 1991-1-4

    Arazi Kategorisi: {building.terrain}

    Hesaplama Formülleri:
    q_b = 0.5 × ρ × v_b0² = {building.q_b:.3f} kN/m²
    k_r = 0.19 × (z₀/0.05)^0.07 = {building.kr:.3f}
    c_r = k_r × ln(z/z₀) = {building.cr:.3f}
    I_v = k_I / ln(z/z₀) = {building.Iv:.3f}
    c_e = c_r² × (1 + 7·I_v) = {building.ce:.3f}
    q_p = c_e × q_b = {building.q_p:.3f} kN/m²

    Not: Referans yükseklik olarak mahya seviyesi (z₂) kullanılmıştır.
    """

    return ReportDataFrame(
        data, custom_title="Rüzgar Yükü Parametreleri", custom_desc=desc,
    )

# ================================================================
# ORTAK YARDIMCILAR
# ================================================================

def _first(v):
    """Tuple ise ilk elemanı, değilse kendisini döner."""
    return v[0] if isinstance(v, tuple) else v


def _second(v):
    """Tuple ise ikinci elemanı, değilse 0 döner."""
    return v[1] if isinstance(v, tuple) else 0

def _iter_zones(results) -> Iterable:
    """Tüm sonuçlardaki yüzeylerde bulunan Zone nesnelerini düz olarak gezer."""
    for bund in results:
        all_surfaces = getattr(bund, "all_surfaces", None) or {}

        for surf in all_surfaces.values():
            for zone in getattr(surf, "zones", None) or []:
                yield zone


def _as_3d(vec) -> np.ndarray:
    v = np.asarray(vec, dtype=float).ravel()
    if v.size == 2:
        return np.array([v[0], v[1], 0.0])
    if v.size >= 3:
        return v[:3].copy()
    return np.array([1.0, 0.0, 0.0])


# ================================================================
# TABLOLAR
# ================================================================

_TYPE_ABBR = {
    "WALL": "W",
    "MONOPITCH": "M",
    "DUOPITCH": "D",
    "HIPPED": "H",
}

def create_cpe_summary_df(zones) -> ReportDataFrame:

    rows = []

    for zone in zones:

        cpe10_min = float(_first(zone.cpe10))
        cpe10_max = float(_second(zone.cpe10))

        cpe1_min = float(_first(zone.cpe1))
        cpe1_max = float(_second(zone.cpe1))

        rows.append({
            "Bölge": zone.label,
            "Yüzey": zone.surface,
            "Tablo": zone.table_type,
            "Yön": zone.table_type_dir,
            "Eğim": zone.pitch,
            "Cpe,10 min": cpe10_min,
            "Cpe,10 max": cpe10_max,
            "Cpe,1 min": cpe1_min,
            "Cpe,1 max": cpe1_max,
        })

    df = pd.DataFrame(rows)
    df = df.sort_values("Bölge")

    desc = f"""
    Dış ve Net Basınç Katsayıları Özeti (TS EN 1991-1-4)

    Semboller ve Tanımlar:
    • CPE10 / CPE10m : 10 m² yüzey alanı için min (basınç/emme) ve max dış basınç katsayıları (c_pe,10).
    • CPE1 / CPE1m   : 1 m² yüzey alanı için min ve max dış basınç katsayıları (c_pe,1).
    • c_pi           : İç basınç katsayısı (Pozitif: {CPI_POSITIVE:+.2f}, Negatif: {CPI_NEGATIVE:+.2f}).

    Kombinasyon Kodları ve Formüller:
    • Cp10TPMn : c_pe,10(min) - c_pi(+)  [10 m² - Min Dış, Pozitif İç Basınç]
    • Cp10TNMn : c_pe,10(min) - c_pi(-)  [10 m² - Min Dış, Negatif İç Basınç]
    • Cp10TPMx : c_pe,10(max) - c_pi(+)  [10 m² - Max Dış, Pozitif İç Basınç]
    • Cp10TNMx : c_pe,10(max) - c_pi(-)  [10 m² - Max Dış, Negatif İç Basınç]
    • Cp1TPMn  : c_pe,1(min)  - c_pi(+)  [1 m²  - Min Dış, Pozitif İç Basınç]
    • Cp1TNMn  : c_pe,1(min)  - c_pi(-)  [1 m²  - Min Dış, Negatif İç Basınç]
    • Cp1TPMx  : c_pe,1(max)  - c_pi(+)  [1 m²  - Max Dış, Pozitif İç Basınç]
    • Cp1TNMx  : c_pe,1(max)  - c_pi(-)  [1 m²  - Max Dış, Negatif İç Basınç]

    Not: Net katsayılar w = q_p × (c_pe - c_pi) bağıntısına esas oluşturmak üzere hesaplanmıştır.
    """

    return ReportDataFrame(
        df,
        custom_title="Dış ve Net Basınç Katsayıları (Cpe & Cp,net)",
        custom_desc=desc,
    )


def create_wind_force_df(zones, engine) -> ReportDataFrame:
    q_p = engine.q_p

    rows = []
    for zone in zones:
        cpe10_min = float(_first(zone.cpe10))
        cpe10_max = float(_second(zone.cpe10))
        cpe1_min = float(_first(zone.cpe1))
        cpe1_max = float(_second(zone.cpe1))

        def _f(cpe, cpi):
            return q_p * (cpe - cpi)

        rows.append(
            {
                "Bölge": zone.label,
                "Type": _TYPE_ABBR.get(zone.table_type, zone.table_type),
                "Pitch": round(float(zone.pitch), 3),
                "F10PMn (kN/m²)": round(_f(cpe10_min, CPI_POSITIVE), 3),
                "F10NMn (kN/m²)": round(_f(cpe10_min, CPI_NEGATIVE), 3),
                "F10PMx (kN/m²)": round(_f(cpe10_max, CPI_POSITIVE), 3),
                "F10NMx (kN/m²)": round(_f(cpe10_max, CPI_NEGATIVE), 3),
                "F1PMn (kN/m²)": round(_f(cpe1_min, CPI_POSITIVE), 3),
                "F1NMn (kN/m²)": round(_f(cpe1_min, CPI_NEGATIVE), 3),
                "F1PMx (kN/m²)": round(_f(cpe1_max, CPI_POSITIVE), 3),
                "F1NMx (kN/m²)": round(_f(cpe1_max, CPI_NEGATIVE), 3),
            }
        )

    df = pd.DataFrame(rows)
    df = df.sort_values("Bölge")

    desc = f"""
    Rüzgar Yükü ve Tasarım Basınçları (TS EN 1991-1-4)

    Hesap Parametreleri:
    • Pik Hız Basıncı (q_p) : {q_p:.3f} kN/m²
    • İç Basınç Katsayıları : c_pi(+) = {CPI_POSITIVE:+.2f}, c_pi(-) = {CPI_NEGATIVE:+.2f}

    Sütun Sembolleri ve Formüller:
    • w = q_p × (c_pe - c_pi)

    Kombinasyon İsimlendirmeleri:
    • F10PMn : q_p × [c_pe,10(min) - c_pi(+)]  (Ana Taşıyıcı Sistem - En Olumsuz Emme / Basınç)
    • F10NMn : q_p × [c_pe,10(min) - c_pi(-)]  (Ana Taşıyıcı Sistem - Negatif İç Basınçlı)
    • F10PMx : q_p × [c_pe,10(max) - c_pi(+)]  (Ana Taşıyıcı Sistem - Maksimum Dış Basınçlı)
    • F10NMx : q_p × [c_pe,10(max) - c_pi(-)]  (Ana Taşıyıcı Sistem - Kombine Max Basınç)
    • F1PMn  : q_p × [c_pe,1(min)  - c_pi(+)]  (Eleman/Kaplama Hesabı - En Olumsuz Emme)
    • F1TNMn : q_p × [c_pe,1(min)  - c_pi(-)]  (Eleman/Kaplama Hesabı - Negatif İç Basınçlı)
    • F1PMx  : q_p × [c_pe,1(max)  - c_pi(+)]  (Eleman/Kaplama Hesabı - Maksimum Dış Basınçlı)
    • F1NMx  : q_p × [c_pe,1(max)  - c_pi(-)]  (Eleman/Kaplama Hesabı - Kombine Max Basınç)

    Not: Pozitif (+) değerler yüzeye doğru basıncı (itme), negatif (-) değerler yüzeyden dışarı doğru basıncı (emme/çekme) ifade eder.
    """

    return ReportDataFrame(
        df, custom_title="Tasarım Rüzgar Yükleri (kN/m²)", custom_desc=desc
    )


def show_zones(zones, building):

    # ---- Zone objelerini tek geçişte topla ----
    zone_records = []  # (coords, label, cpe_scalar)
    cpe10_values = []

    for zone_obj in zones:
        coords = np.asarray(zone_obj.coords, dtype=float)
        cpe = zone_obj.cpe10
        current_cpe = cpe[0] if isinstance(cpe, (tuple, list, np.ndarray)) else cpe
        zone_records.append((coords, zone_obj.label, float(current_cpe)))
        cpe10_values.append(float(current_cpe))

    if not zone_records:
        raise ValueError("all_wind_zones boş!")

    # ---- Bina bounding box ----
    b_coords = np.array(list(building.points.values()), dtype=float)
    min_b = b_coords.min(axis=0)
    max_b = b_coords.max(axis=0)
    mid_b = (min_b + max_b) / 2

    # ---- Plot sınırları ----
    all_coords = np.vstack([r[0] for r in zone_records])
    mins = all_coords.min(axis=0)
    maxs = all_coords.max(axis=0)
    ranges = maxs - mins
    max_range = max(ranges) if max(ranges) > 0 else 1.0
    mid_plot = (mins + maxs) / 2

    # ---- Figür ----
    x_range, y_range, z_range = ranges
    aspect_xy = x_range / max(y_range, 1e-9)
    fig_width = float(np.clip(8 * aspect_xy, 8, 16))
    fig = plt.figure(figsize=(fig_width, 8), dpi=150)
    ax = fig.add_subplot(111, projection="3d")

    ax.set_xlim(mid_plot[0] - max_range / 2, mid_plot[0] + max_range / 2)
    ax.set_ylim(mid_plot[1] - max_range / 2, mid_plot[1] + max_range / 2)
    ax.set_zlim(mid_plot[2] - max_range / 2, mid_plot[2] + max_range / 2)
    ax.set_box_aspect([x_range, y_range, z_range])  # gerçek oran

    # ---- Renk normalizasyonu ----
    neg_cpe = [v for v in cpe10_values if v < 0]
    pos_cpe = [v for v in cpe10_values if v > 0]
    min_neg_abs = abs(min(neg_cpe)) if neg_cpe else 1.0
    max_pos = max(pos_cpe) if pos_cpe else 1.0

    neg_cmap = matplotlib.colormaps.get_cmap("Blues")
    pos_cmap = matplotlib.colormaps.get_cmap("Reds")
    neutral_color = (0.85, 0.85, 0.85, 1.0)

    # ---- Poligonları çiz ----
    for coords, label, cpe in zone_records:
        if cpe < 0:
            facecolor = neg_cmap(abs(cpe) / min_neg_abs)
        elif cpe > 0:
            facecolor = pos_cmap(cpe / max_pos)
        else:
            facecolor = neutral_color

        col = Poly3DCollection(
            [coords],
            alpha=0.6,
            facecolor=facecolor,
            edgecolor="black",
            linewidths=1.0,
        )
        ax.add_collection3d(col)

        # Etiket
        pts = coords[:-1] if np.allclose(coords[0], coords[-1], atol=1e-9) else coords
        centroid = pts.mean(axis=0)
        ax.text(
            centroid[0], centroid[1], centroid[2],
            f"{label} ({cpe:.2f})",
            fontsize=8, fontweight="bold", color="black",
            ha="center", va="center",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="white",
                      edgecolor="gray", alpha=0.7, linewidth=0.5),
        )

    # ---- Rüzgar oku ----
    wind_vector = np.asarray(building.w_dir, dtype=float)
    w_norm = np.linalg.norm(wind_vector)
    if w_norm < 1e-9:
        wind_dir_norm = np.array([1.0, 0.0, 0.0])
    else:
        wind_dir_norm = wind_vector / w_norm

    arrow_length = max_range / 3
    b_size = max_b - min_b

    # Rüzgarın geldiği yönün tersine, bina yüzeyinin merkezinden başlat
    # Okun başlangıcı: rüzgar yönünün tersi yönde, bina sınırının dışında
    face_center = mid_b.copy()
    dominant_axis = int(np.argmax(np.abs(wind_dir_norm)))
    if np.abs(wind_dir_norm[dominant_axis]) > 1e-6:
        sign = np.sign(wind_dir_norm[dominant_axis])
        # Rüzgarın geldiği taraf: binanın -sign tarafı
        face_center[dominant_axis] = mid_b[dominant_axis] - sign * b_size[dominant_axis] / 2
        # Biraz daha dışarı çıkar
        face_center[dominant_axis] -= sign * arrow_length * 0.5
    else:
        face_center[dominant_axis] = mid_plot[dominant_axis] - max_range / 2

    ax.quiver(
        face_center[0], face_center[1], face_center[2],
        wind_dir_norm[0] * arrow_length,
        wind_dir_norm[1] * arrow_length,
        wind_dir_norm[2] * arrow_length,
        color="red", arrow_length_ratio=0.3, linewidth=2,
    )

    # ---- Temizle ----
    ax.set_axis_off()
    ax.grid(False)

    # ---- Kaydet ----
    img_stream = io.BytesIO()
    plt.savefig(
        img_stream, format="png",
        bbox_inches="tight", pad_inches=0,
        transparent=True, dpi=300,
    )
    plt.close(fig)
    img_stream.seek(0)
    return img_stream