#wind_report.py
   
import numpy as np
import pandas as pd

import io
from typing import Iterable, Optional


from utils.my_document import myDocument, Cm
from utils.report_dataframe import ReportDataFrame
from zone import CPI_NEGATIVE, CPI_POSITIVE


# ================================================================
# ORTAK YARDIMCILAR
# ================================================================

def _first(v):
    """Tuple ise ilk elemanı, değilse kendisini döner."""
    return v[0] if isinstance(v, tuple) else v


def _second(v):
    """Tuple ise ikinci elemanı, değilse 0 döner."""
    return v[1] if isinstance(v, tuple) else 0


def _iter_zones(building) -> Iterable:
    """Tüm yüzeylerdeki Zone nesnelerini tek düz listede gezer."""
    all_wind_zones = getattr(building, "all_wind_zones", None)
    if not all_wind_zones:
        return
    for zones in all_wind_zones.values():
        for zone in zones:
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

def create_cpe_summary_df(building) -> ReportDataFrame:
    cpi_pos = CPI_POSITIVE
    cpi_neg = CPI_NEGATIVE

    rows = []
    for zone in _iter_zones(building):
        cpe10_min = float(_first(zone.cpe10))
        cpe10_max = float(_second(zone.cpe10))
        cpe1_min = float(_first(zone.cpe1))
        cpe1_max = float(_second(zone.cpe1))

        rows.append(
            {
                "Bölge": zone.label,
                "Tablo": zone.table_type,
                "Pitch (or h/d)": round(float(zone.pitch), 3),
                "CPE10": round(cpe10_min, 3),
                "CPE10m": round(cpe10_max, 3),
                "CPE1": round(cpe1_min, 3),
                "CPE1m": round(cpe1_max, 3),
                "Cp10TPMn": round(cpe10_min - cpi_pos, 3),
                "Cp10TNMn": round(cpe10_min - cpi_neg, 3),
                "Cp10TPMx": round(cpe10_max - cpi_pos, 3),
                "Cp10TNMx": round(cpe10_max - cpi_neg, 3),
                "Cp1TPMn": round(cpe1_min - cpi_pos, 3),
                "Cp1TNMn": round(cpe1_min - cpi_neg, 3),
                "Cp1TPMx": round(cpe1_max - cpi_pos, 3),
                "Cp1TNMx": round(cpe1_max - cpi_neg, 3),
            }
        )

    df = pd.DataFrame(rows)
    df = df.sort_values("Zone")

    desc = f"""
    Dış ve Net Basınç Katsayıları Özeti (TS EN 1991-1-4)

    Semboller ve Tanımlar:
    • CPE10 / CPE10m : 10 m² yüzey alanı için min (basınç/emme) ve max dış basınç katsayıları (c_pe,10).
    • CPE1 / CPE1m   : 1 m² yüzey alanı için min ve max dış basınç katsayıları (c_pe,1).
    • c_pi           : İç basınç katsayısı (Pozitif: {cpi_pos:+.2f}, Negatif: {cpi_neg:+.2f}).

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


def create_wind_force_df(building) -> ReportDataFrame:
    q_p = building.q_p
    cpi_pos = CPI_POSITIVE
    cpi_neg = CPI_NEGATIVE

    rows = []
    for zone in _iter_zones(building):
        cpe10_min = float(_first(zone.cpe10))
        cpe10_max = float(_second(zone.cpe10))
        cpe1_min = float(_first(zone.cpe1))
        cpe1_max = float(_second(zone.cpe1))

        def _f(cpe, cpi):
            return q_p * (cpe - cpi)

        rows.append(
            {
                "Zone": zone.label,
                "Type": _TYPE_ABBR.get(zone.table_type, zone.table_type),
                "Pitch": round(float(zone.pitch), 3),
                "F10PMn (kN/m²)": round(_f(cpe10_min, cpi_pos), 3),
                "F10NMn (kN/m²)": round(_f(cpe10_min, cpi_neg), 3),
                "F10PMx (kN/m²)": round(_f(cpe10_max, cpi_pos), 3),
                "F10NMx (kN/m²)": round(_f(cpe10_max, cpi_neg), 3),
                "F1PMn (kN/m²)": round(_f(cpe1_min, cpi_pos), 3),
                "F1NMn (kN/m²)": round(_f(cpe1_min, cpi_neg), 3),
                "F1PMx (kN/m²)": round(_f(cpe1_max, cpi_pos), 3),
                "F1NMx (kN/m²)": round(_f(cpe1_max, cpi_neg), 3),
            }
        )

    df = pd.DataFrame(rows)
    df = df.sort_values("Zone")

    desc = f"""
    Rüzgar Yükü ve Tasarım Basınçları (TS EN 1991-1-4)

    Hesap Parametreleri:
    • Pik Hız Basıncı (q_p) : {q_p:.3f} kN/m²
    • İç Basınç Katsayıları : c_pi(+) = {cpi_pos:+.2f}, c_pi(-) = {cpi_neg:+.2f}

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

# ================================================================
# PARAMETRE RAPORU
# ================================================================

def get_parameters_report(building) -> ReportDataFrame:
    summary = building.get_summary()
    h = summary["Geometri"]["h"]
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
# RAPOR
# ================================================================
W_LIST = {
    "x+": [1, 0, 0],
    "y+": [0, 1, 0],
    "x-": [-1, 0, 0],
    "y-": [0, -1, 0],
}

def get_report(
    building,
    image_bytes: Optional[bytes] = None,
    filename: str = "rapor.docx",
) -> None:
    if building is None:
        raise ValueError("building None olamaz.")
    if not getattr(building, "all_wind_zones", None):
        raise ValueError("building.all_wind_zones boş. Önce set_wind() çağırın.")

    parameters_report = get_parameters_report(building)
    cpe_report = create_cpe_summary_df(building)
    wind_force_report = create_wind_force_df(building)

    doc = myDocument()
    doc.apply_visual_settings()
    doc.add_heading_numbered("RÜZGAR ANALİZİ", level=1)

    parameters_report.save_to_docx(doc, level=2)

    # 3D görseli view'dan gelen byte'larla ekle
    if image_bytes:
        stream = io.BytesIO(image_bytes)
        doc.doc.add_picture(stream, Cm(15))

    cpe_report.save_to_docx(doc, level=2)
    wind_force_report.save_to_docx(doc, level=2)

    doc.doc.save(filename)
    print(f"[Report] Kaydedildi: {filename}")
