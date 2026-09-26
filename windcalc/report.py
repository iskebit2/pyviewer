# windcalc/report.py
"""
ZoneBundle tabanlı raporlama katmanı.
Tüm rüzgar yönleri için:
  - Parametre raporu (tek seferlik)
  - Her yön için 3D görsel
  - Her yön için CPE özeti
  - Her yön için tasarım yükleri
"""
import io
from typing import Iterable, Optional, Dict, Any

import numpy as np
import pandas as pd

from utils.my_document import myDocument, Cm
from utils.report_dataframe import ReportDataFrame

from windcalc.visualize import draw_zone_result
from windcalc.wind_data import CPI_POSITIVE, CPI_NEGATIVE


# ---------------------------------------------------------------------------
# YARDIMCILAR
# ---------------------------------------------------------------------------

def _first(v):
    return v[0] if isinstance(v, (tuple, list, np.ndarray)) else v


def _second(v):
    return v[1] if isinstance(v, (tuple, list, np.ndarray)) else 0.0


def _iter_result_zones(result) -> Iterable:
    """ZoneResult içindeki tüm Zone nesnelerini gezer."""
    for surf in result.all_surfaces.values():
        for zone in getattr(surf, "zones", []) or []:
            yield zone


_TYPE_ABBR = {
    "WALL": "W",
    "MONOPITCH": "M",
    "DUOPITCH": "D",
    "HIPPED": "H",
}


# ---------------------------------------------------------------------------
# 1. PARAMETRE RAPORU (tüm yönler için ortak)
# ---------------------------------------------------------------------------
def create_parameters_report(bundle) -> ReportDataFrame:
    """İlk ZoneResult'ın engine'inden parametreleri alır."""
    engine = bundle.results[0].engine
    h = engine.geometry["h"]
    z_ref = max(h, engine.zmin)

    params = [
        ("Bina Yüksekliği (h)",              f"{h:.2f} m"),
        ("Arazi Kategorisi",                 engine.terrain),
        ("Pürüzlülük Uzunluğu (z₀)",         f"{engine.z0:.3f} m"),
        ("Minimum Yükseklik (z_min)",        f"{engine.zmin:.1f} m"),
        ("Referans Yükseklik (z_ref)",       f"{z_ref:.3f} m"),
        ("Temel Rüzgar Hızı (v_b0)",         f"{engine.v_b0:.1f} m/s"),
        ("Hava Yoğunluğu (ρ)",               f"{engine.rho:.2f} kg/m³"),
        ("Temel Hız Basıncı (q_b)",          f"{engine.q_b:.3f} kN/m²"),
        ("Pürüzlülük Katsayısı (k_r)",       f"{engine.kr:.3f}"),
        ("Arazi Faktörü (c_r)",              f"{engine.cr:.3f}"),
        ("Türbülans Şiddeti (I_v)",          f"{engine.Iv:.3f}"),
        ("Maruziyet Katsayısı (c_e)",        f"{engine.ce:.3f}"),
        ("Pik Hız Basıncı (q_p)",            f"{engine.q_p:.3f} kN/m²"),
        ("İç Basınç (+)",                    f"{CPI_POSITIVE:+.2f}"),
        ("İç Basınç (-)",                    f"{CPI_NEGATIVE:+.2f}"),
    ]

    data = {
        "Parametre": [p[0] for p in params],
        "Değer":     [p[1] for p in params],
    }

    desc = f"""
    Rüzgar Yükü Analizi - TS EN 1991-1-4

    Arazi Kategorisi: {engine.terrain}

    Hesaplama Formülleri:
    q_b = 0.5 × ρ × v_b0² = {engine.q_b:.3f} kN/m²
    k_r = 0.19 × (z₀/0.05)^0.07 = {engine.kr:.3f}
    c_r = k_r × ln(z/z₀) = {engine.cr:.3f}
    I_v = k_I / ln(z/z₀) = {engine.Iv:.3f}
    c_e = c_r² × (1 + 7·I_v) = {engine.ce:.3f}
    q_p = c_e × q_b = {engine.q_p:.3f} kN/m²
    """

    return ReportDataFrame(
        data,
        custom_title="Rüzgar Yükü Parametreleri",
        custom_desc=desc,
    )


# ---------------------------------------------------------------------------
# 2. CPE ÖZET TABLOSU (tek yön)
# ---------------------------------------------------------------------------
def create_cpe_summary_df(result) -> ReportDataFrame:
    cpi_pos, cpi_neg = CPI_POSITIVE, CPI_NEGATIVE
    rows = []

    for zone in _iter_result_zones(result):
        try:
            cpe10_min = float(_first(zone.cpe10))
            cpe10_max = float(_second(zone.cpe10))
            cpe1_min  = float(_first(zone.cpe1))
            cpe1_max  = float(_second(zone.cpe1))
        except (KeyError, TypeError):
            continue

        rows.append({
            "Bölge": zone.label,
            "Tablo": zone.table_type,
            "Pitch (or h/d)": round(float(zone.pitch), 3),
            "CPE10":  round(cpe10_min, 3),
            "CPE10m": round(cpe10_max, 3),
            "CPE1":   round(cpe1_min, 3),
            "CPE1m":  round(cpe1_max, 3),
            "Cp10TPMn": round(cpe10_min - cpi_pos, 3),
            "Cp10TNMn": round(cpe10_min - cpi_neg, 3),
            "Cp10TPMx": round(cpe10_max - cpi_pos, 3),
            "Cp10TNMx": round(cpe10_max - cpi_neg, 3),
            "Cp1TPMn":  round(cpe1_min  - cpi_pos, 3),
            "Cp1TNMn":  round(cpe1_min  - cpi_neg, 3),
            "Cp1TPMx":  round(cpe1_max  - cpi_pos, 3),
            "Cp1TNMx":  round(cpe1_max  - cpi_neg, 3),
        })

    df = pd.DataFrame(rows).sort_values("Bölge") if rows else pd.DataFrame()

    desc = f"""
    Dış ve Net Basınç Katsayıları Özeti (TS EN 1991-1-4) — Rüzgar: {result.w_key}

    • CPE10 / CPE10m : 10 m² için min/max dış basınç katsayıları
    • CPE1  / CPE1m  : 1 m²  için min/max dış basınç katsayıları
    • c_pi(+) = {cpi_pos:+.2f},  c_pi(-) = {cpi_neg:+.2f}
    • Net: c_pe - c_pi
    """

    return ReportDataFrame(
        df,
        custom_title=f"Dış ve Net Basınç Katsayıları — {result.w_key}",
        custom_desc=desc,
    )


# ---------------------------------------------------------------------------
# 3. TASARIM YÜKLERİ (tek yön)
# ---------------------------------------------------------------------------
def create_wind_force_df(result) -> ReportDataFrame:
    q_p = result.engine.q_p
    cpi_pos, cpi_neg = CPI_POSITIVE, CPI_NEGATIVE
    rows = []

    for zone in _iter_result_zones(result):
        try:
            cpe10_min = float(_first(zone.cpe10))
            cpe10_max = float(_second(zone.cpe10))
            cpe1_min  = float(_first(zone.cpe1))
            cpe1_max  = float(_second(zone.cpe1))
        except (KeyError, TypeError):
            continue

        def _f(cpe, cpi):
            return q_p * (cpe - cpi)

        rows.append({
            "Bölge": zone.label,
            "Type": _TYPE_ABBR.get(zone.table_type, zone.table_type),
            "Pitch": round(float(zone.pitch), 3),
            "F10PMn (kN/m²)": round(_f(cpe10_min, cpi_pos), 3),
            "F10NMn (kN/m²)": round(_f(cpe10_min, cpi_neg), 3),
            "F10PMx (kN/m²)": round(_f(cpe10_max, cpi_pos), 3),
            "F10NMx (kN/m²)": round(_f(cpe10_max, cpi_neg), 3),
            "F1PMn  (kN/m²)": round(_f(cpe1_min,  cpi_pos), 3),
            "F1NMn  (kN/m²)": round(_f(cpe1_min,  cpi_neg), 3),
            "F1PMx  (kN/m²)": round(_f(cpe1_max,  cpi_pos), 3),
            "F1NMx  (kN/m²)": round(_f(cpe1_max,  cpi_neg), 3),
        })

    df = pd.DataFrame(rows).sort_values("Bölge") if rows else pd.DataFrame()

    desc = f"""
    Rüzgar Yükü (w = q_p × (c_pe - c_pi)) — Rüzgar: {result.w_key}

    q_p = {q_p:.3f} kN/m²
    c_pi(+) = {cpi_pos:+.2f},  c_pi(-) = {cpi_neg:+.2f}

    F10xx : 10 m² yüzey (ana taşıyıcı)
    F1xx  : 1 m² yüzey (eleman/kaplama)
    P/N   : pozitif/negatif iç basınç
    Mn/Mx : min/max dış basınç
    """

    return ReportDataFrame(
        df,
        custom_title=f"Tasarım Rüzgar Yükleri — {result.w_key}",
        custom_desc=desc,
    )


# ---------------------------------------------------------------------------
# 4. 3D GÖRSEL → PNG stream
# ---------------------------------------------------------------------------
def render_result_to_png(result, dpi: int = 200, figsize=(8, 6)) -> io.BytesIO:
    """
    Tek bir ZoneResult'ı offscreen matplotlib figürüne çizip PNG stream döner.
    """
    import matplotlib
    matplotlib.use("Agg", force=False)   # docx için güvenli backend
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=figsize, dpi=dpi)
    ax = fig.add_subplot(111, projection="3d")

    draw_zone_result(ax, result, title_suffix=f"Rüzgar: {result.w_key}")

    stream = io.BytesIO()
    fig.savefig(stream, format="png", bbox_inches="tight",
                pad_inches=0.1, transparent=False, dpi=dpi)
    plt.close(fig)
    stream.seek(0)
    return stream


# ---------------------------------------------------------------------------
# 5. TÜM YÖNLER RAPORU (ana fonksiyon)
# ---------------------------------------------------------------------------
def build_full_report(
    bundle,
    filename: str = "ruzgar_raporu.docx",
    image_width_cm: float = 15.0,
) -> None:
    """
    ZoneBundle için tüm yönleri kapsayan tam rapor üretir.
    """
    doc = myDocument()
    doc.apply_visual_settings()

    doc.add_heading_numbered("RÜZGAR ANALİZİ", level=1)

    # --- Parametreler (tek seferlik) ---
    create_parameters_report(bundle).save_to_docx(doc, level=2)

    # --- Her yön için ---
    for result in bundle.results:
        doc.add_heading_numbered(
            f"RÜZGAR YÖNÜ: {result.w_key} — {tuple(result.w_dir)}",
            level=2,
        )

        # 3D görsel
        try:
            png = render_result_to_png(result)
            doc.doc.add_picture(png, width=Cm(image_width_cm))
        except Exception as e:
            print(f"[Report] Görsel üretilemedi ({result.w_key}): {e}")

        # CPE tablosu
        cpe_report = create_cpe_summary_df(result)
        if not cpe_report.empty:
            cpe_report.save_to_docx(doc, level=2)

        # Tasarım yükleri
        force_report = create_wind_force_df(result)
        if not force_report.empty:
            force_report.save_to_docx(doc, level=2)

    doc.doc.save(filename)
    print(f"[Report] Kaydedildi: {filename}")


# ---------------------------------------------------------------------------
# 6. KONSOL ÖZETİ (docx istemeyenler için)
# ---------------------------------------------------------------------------
def print_console_summary(bundle) -> None:
    """Tüm yönler için zone'ları konsola döker."""
    print()
    report_= bundle.get_summary()
    for result in bundle.results:

        for surf in result.all_surfaces.values():
            report_[surf.name] = {}
            info_ = f"  {surf.name:8s} | {surf.surface_type.value:5s} | "
            info_ += f"{surf.wind_relation.value:8s} | "
            info_ += f"roof={surf.roof_type or '-':10s} | "
            report_[surf.name]["properties"]= info_
            
            zones = getattr(surf, "zones", []) or []
            if not zones:
                continue

            report_[surf.name]["zones"] = [z.label for z in zones]
            report_[surf.name]["cpe_report"] = create_cpe_summary_df(result)
            report_[surf.name]["force_report"] = create_wind_force_df(result)

    return f'Rüzgar hesabı\n\n{report_}'