"""
Rüzgar Yükü Motoru - TS EN 1991-1-4
"""

from typing import Dict, Any, List, Tuple, Union, Optional
import math
import pandas as pd
import numpy as np
from utils.report_dataframe import ReportDataFrame
from data.wind_data import (
    ARAZI_KATEGORILERI, CPE_DATA, CPI_POSITIVE, CPI_NEGATIVE, RHO, K_I, C0
)
from utils.math_utils import (
    calculate_wind_velocity_pressure,
    calculate_roughness_coefficient,
    calculate_exposure_coefficient,
    calculate_turbulence_intensity
)


class WindLoad:
    """
    Rüzgar Yükü Hesaplama Sınıfı
    TS EN 1991-1-4 ve Türkiye Ulusal Eki
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Args:
            config: {
                "b": 8.21,               # Rüzgar yönüne dik genişlik (m)
                "d": 4.56,               # Rüzgar yönüne paralel derinlik (m)
                "z0": 0.0,               # Zemin kotu (m)
                "z1": 10.45,             # Saçak kotu (m)
                "z2": 11.344,            # Mahya kotu (m)
                "v_b0": 28.0,            # Temel rüzgar hızı (m/s)
                "egim": 21.43,           # Çatı eğimi (derece)
                "roof_type": "Beşik",    # Çatı tipi (Duvar, Tek Eğimli, Beşik, Çift Eğimli)
                "mahya_paralel": "b",    # Mahya paralelliği ("b" veya "d")
                "terrain": "Kategori III"
            }
        """
        self.config = config
        
        # Geometri parametreleri
        self.b = float(config.get("b", 8.21))
        self.d = float(config.get("d", 4.56))
        self.z0_ground = float(config.get("z0", 0.0))
        self.z1 = float(config.get("z1", 10.45))
        self.z2 = float(config.get("z2", 11.344))
        self.h = self.z1 - self.z0_ground
        
        # Rüzgar parametreleri
        self.alpha = float(config.get("egim", 21.43))
        self.v_b0 = float(config.get("v_b0", 28.0))
        self.rho = float(config.get("ro", RHO))
        self.ct = float(config.get("ct", C0))
        
        # Çatı tipi ve mahya yönü
        self.roof_type = config.get("roof_type", "Beşik")
        self.mahya_paralel = config.get("mahya_paralel", "b")
        self.terrain = config.get("terrain", "Kategori III")
        
        # Arazi parametreleri
        self.terrain_params = ARAZI_KATEGORILERI.get(self.terrain)
        if not self.terrain_params:
            raise ValueError(f"Geçersiz arazi kategorisi: {self.terrain}")
        
        self.z0 = float(self.terrain_params.get("z0", 0.3))
        self.zmin = float(self.terrain_params.get("zmin", 5.0))
        
        # İç basınç katsayıları
        self.cpi_pos = float(CPI_POSITIVE)
        self.cpi_neg = float(CPI_NEGATIVE)
        self.kI = K_I
        self.c0 = C0
        
        # Hesaplamalar
        self._calculate()
    
    def _calculate(self):
        """Tüm rüzgar yükü hesaplamalarını yapar"""
        # 1. Temel hız basıncı
        self.q_b = calculate_wind_velocity_pressure(self.v_b0, self.rho)
        
        # 2. Referans yükseklik - mahya seviyesi
        z_ref = max(self.z2, self.zmin)
        
        # 3. Pürüzlülük katsayıları
        self.kr, self.cr = calculate_roughness_coefficient(self.z0, z_ref, self.zmin)
        
        # 4. Türbülans şiddeti
        self.Iv = calculate_turbulence_intensity(self.z0, z_ref, self.zmin, self.kI)
        
        # 5. Maruziyet katsayısı
        ce_base = calculate_exposure_coefficient(self.cr, self.ct)
        self.ce = ce_base * (1 + 7 * self.Iv)
        
        # 6. Pik hız basıncı
        self.q_p = self.ce * self.q_b
        
        # 7. Her iki yön için hesaplama
        self.results_0 = self._calculate_direction(0)
        self.results_90 = self._calculate_direction(90)
        
        # 8. Rapor tabloları
        self.report_tables = []
        if self.results_0:
            self.report_tables.append(self.results_0["report"])
        if self.results_90:
            self.report_tables.append(self.results_90["report"])
    
    def _interp_angle(self, value: float, angle_dict: Dict) -> Tuple[float, float]:
        """
        Açı değerine göre interpolasyon için alt ve üst açıları bulur
        """
        angles = np.array(sorted(angle_dict.keys()))
        if value <= angles.min():
            return angles.min(), angles.min()
        if value >= angles.max():
            return angles.max(), angles.max()
        return angles[angles <= value].max(), angles[angles >= value].min()
    
    def _build_cpe(self, wind_data: Dict, value: float) -> pd.DataFrame:
        """
        CPE_DATA'dan veriyi alarak DataFrame oluşturur
        """
        zones = wind_data["zones"]
        df = pd.DataFrame(index=zones)
        
        for cpe_type in ["cpe10", "cpe1"]:
            angle_dict = wind_data["data"][cpe_type]
            a1, a2 = self._interp_angle(value, angle_dict)
            
            for z in zones:
                n1, p1 = angle_dict[a1][z]
                n2, p2 = angle_dict[a2][z]
                t = 0 if a1 == a2 else (value - a1) / (a2 - a1)
                df.loc[z, f"{cpe_type} -"] = n1 + t * (n2 - n1)
                df.loc[z, f"{cpe_type} +"] = p1 + t * (p2 - p1)
        
        return df
    
    def _calculate_direction(self, wind_dir: int) -> Dict[str, Any]:
        """
        Belirli bir rüzgar yönü için hesaplama yapar
        """
        # Mahya paralelliğine göre roof_key belirle
        is_parallel_d = (self.mahya_paralel == "d")
        roof_key = 0 if (wind_dir == 0) ^ is_parallel_d else 90
        
        b_eff = self.b if wind_dir == 0 else self.d
        d_eff = self.d if wind_dir == 0 else self.b
        h_d = self.h / d_eff if d_eff else 0
        
        # Duvar CPE hesapları (h/d oranına göre)
        duvar_data = CPE_DATA["Duvar"][0]
        duvar = self._build_cpe(duvar_data, h_d)
        
        # Çatı CPE hesapları (eğim açısına göre)
        cati_data = CPE_DATA[self.roof_type][roof_key]
        cati = self._build_cpe(cati_data, self.alpha)
        
        # Duvar ve çatı verilerini birleştir
        res = pd.concat([duvar, cati])
        
        # --- DOĞRULANMIŞ TS EN 1991-1-4 KRİTİK YÜK KOMBİNASYONLARI ---
        # cpe_neg (Emme) ve cpe_pos (Basınç) durumları için en elverişsiz w_net hesabı:
        # 1. Dış Emme + İç Basınç (Açmaya çalışan maks. çekme/vakum)
        res["W_net_pull_max"] = self.q_p * (res["cpe10 -"] - self.cpi_pos)
        
        # 2. Dış Emme + İç Vakum
        res["W_net_pull_min"] = self.q_p * (res["cpe10 -"] - self.cpi_neg)

        # 3. Dış Basınç + İç Vakum (Baskılayan maks. içe doğru basınç)
        res["W_net_push_max"] = self.q_p * (res["cpe10 +"] - self.cpi_neg)
        
        # 4. Dış Basınç + İç Basınç
        res["W_net_push_min"] = self.q_p * (res["cpe10 +"] - self.cpi_pos)
        
        # Rapor oluştur
        e = min(b_eff, 2 * self.h)
        pattern = "WindX" if wind_dir == 0 else "WindY"
        desc = (
            f"Yük Deseni: {pattern}\n"
            f"Etkin Boyutlar: b={b_eff:.2f}m, d={d_eff:.2f}m, h={self.h:.2f}m\n"
            f"Kritik Uzunluk e: {e:.2f}m\n"
            f"h/d Oranı: {h_d:.3f}\n"
            f"İç Basınç Katsayıları: c_pi(+)={self.cpi_pos}, c_pi(-)={self.cpi_neg}\n"
            f"q_p = {self.q_p:.3f} kN/m²\n"
            f"Çatı Tipi: {self.roof_type}"
        )
        
        report = ReportDataFrame(
            res.round(3).reset_index(),
            custom_title=f"RÜZGAR YÖNÜ {wind_dir}° - {pattern}",
            custom_desc=desc,
            column_units={
                "cpe10 -": "-",
                "cpe10 +": "-",
                "cpe1 -": "-",
                "cpe1 +": "-",
                "W_P_+cpi": "kN/m²",
                "W_P_-cpi": "kN/m²",
                "W_E_+cpi": "kN/m²",
                "W_E_-cpi": "kN/m²"
            }
        )
        
        return {
            "wind_dir": wind_dir,
            "pattern": pattern,
            "b_eff": b_eff,
            "d_eff": d_eff,
            "h_d": h_d,
            "roof_key": roof_key,
            "dataframe": res,
            "report": report,
            "W_net_pull_max": res["W_net_pull_max"].tolist(),
            "W_net_pull_min": res["W_net_pull_min"].tolist(),
            "W_net_push_max": res["W_net_push_max"].tolist(),
            "W_net_push_min": res["W_net_push_min"].tolist()
        }
    
    def get_parameters_report(self) -> ReportDataFrame:
        """Rüzgar parametreleri raporu"""
        z_ref = max(self.z2, self.zmin)
        
        data = {
            "Parametre": [
                "Çatı Tipi",
                "Bina Yüksekliği (h)",
                "Çatı Eğimi (α)",
                "Arazi Kategorisi",
                "Pürüzlülük Uzunluğu (z₀)",
                "Minimum Yükseklik (z_min)",
                "Referans Yükseklik (z_ref)",
                "Temel Rüzgar Hızı (v_b0)",
                "Hava Yoğunluğu (ρ)",
                "Temel Hız Basıncı (q_b)",
                "Pürüzlülük Katsayısı (k_r)",
                "Arazi Faktörü (c_r)",
                "Türbülans Şiddeti (I_v)",
                "Maruziyet Katsayısı (c_e)",
                "Pik Hız Basıncı (q_p)",
                "İç Basınç (+)",
                "İç Basınç (-)"
            ],
            "Değer": [
                self.roof_type,
                f"{self.h:.2f} m",
                f"{self.alpha:.2f}°",
                self.terrain,
                f"{self.z0:.3f} m",
                f"{self.zmin:.1f} m",
                f"{z_ref:.3f} m",
                f"{self.v_b0:.1f} m/s",
                f"{self.rho:.2f} kg/m³",
                f"{self.q_b:.3f} kN/m²",
                f"{self.kr:.3f}",
                f"{self.cr:.3f}",
                f"{self.Iv:.3f}",
                f"{self.ce:.3f}",
                f"{self.q_p:.3f} kN/m²",
                f"{self.cpi_pos:.2f}",
                f"{self.cpi_neg:.2f}"
            ]
        }
        
        desc = f"""
        Rüzgar Yükü Analizi - TS EN 1991-1-4
        
        Çatı Tipi: {self.roof_type}
        Arazi Kategorisi: {self.terrain}
        
        Hesaplama Formülleri:
        q_b = 0.5 × ρ × v_b0² = {self.q_b:.3f} kN/m²
        k_r = 0.19 × (z₀/0.05)^0.07 = {self.kr:.3f}
        c_r = k_r × ln(z/z₀) = {self.cr:.3f}
        I_v = k_I / ln(z/z₀) = {self.Iv:.3f}
        c_e = c_r² × (1 + 7·I_v) = {self.ce:.3f}
        q_p = c_e × q_b = {self.q_p:.3f} kN/m²
        
        Not: Referans yükseklik olarak mahya seviyesi (z₂) kullanılmıştır.
        """
        
        return ReportDataFrame(
            data,
            custom_title="Rüzgar Yükü Parametreleri",
            custom_desc=desc
        )
    
    def get_load_patterns(self) -> Dict[str, float]:
        """SAP2000 için yük kalıpları"""
        patterns = {}
        
        for result in [self.results_0, self.results_90]:
            if result:
                pattern_name = result["pattern"]
                all_loads = (
                    result["w_p_plus_cpi"] +
                    result["w_p_minus_cpi"] +
                    result["w_e_plus_cpi"] +
                    result["w_e_minus_cpi"]
                )
                if all_loads:
                    max_load = max(abs(v) for v in all_loads)
                    patterns[pattern_name] = round(max_load, 3)
        
        return patterns
    
    def get_all_reports(self) -> List[ReportDataFrame]:
        """Tüm rapor tablolarını döndürür"""
        reports = [self.get_parameters_report()]
        reports.extend(self.report_tables)
        return reports
    
    @property
    def w_net(self) -> Dict[str, Dict[str, float]]:
        """Eski formatla uyumluluk için w_net property'si"""
        result = {}
        
        if self.results_0:
            df = self.results_0["dataframe"]
            for idx, row in df.iterrows():
                result[idx] = {
                    "W_P_+cpi": row.get("W_P_+cpi", 0.0),
                    "W_P_-cpi": row.get("W_P_-cpi", 0.0),
                    "W_E_+cpi": row.get("W_E_+cpi", 0.0),
                    "W_E_-cpi": row.get("W_E_-cpi", 0.0)
                }
        
        return result
    
    def to_dict(self) -> Dict[str, Any]:
        """Tüm verileri dictionary olarak döndürür"""
        return {
            "config": self.config,
            "q_b": self.q_b,
            "q_p": self.q_p,
            "kr": self.kr,
            "cr": self.cr,
            "Iv": self.Iv,
            "ce": self.ce,
            "cpi_pos": self.cpi_pos,
            "cpi_neg": self.cpi_neg,
            "results_0": self.results_0,
            "results_90": self.results_90
        }



    

class WindLoadCalculator:
    """
    3D Uzay Geometrisi ve TS EN 1991-1-4 Rüzgar Yükü Köprüsü.
    View3D'den bağımsız çalışır; ham nokta verilerini alır, OBB geometrisini, 
    e=min(B, 2H) değerlerini türetir ve çizim pritiflerini oluşturur.
    """

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

    @classmethod
    def build_wind_config(
        cls, 
        geom: Dict[str, Any], 
        user_overrides: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Geometrik motordan elde edilen b, d, h değerlerini senin mevcut 
        WindLoad konfigürasyon sözlüğüne dönüştürür.
        """
        config = {
            "b": round(geom["b"], 3),
            "d": round(geom["d"], 3),
            "z0": round(geom["z0_ground"], 3),
            "z1": round(geom["z_max"], 3),
            "z2": round(geom["z_max"], 3),  # Mahya varsayılan olarak saçakla aynı veya üzeri
            "v_b0": 28.0,
            "egim": 0.0,
            "roof_type": "Beşik",
            "mahya_paralel": "b",
            "terrain": "Kategori III"
        }

        if user_overrides:
            config.update(user_overrides)

        return config


# =============================================================================
# BAĞIMSIZ TEST BLOĞU (STANDALONE TEST)
# =============================================================================
if __name__ == "__main__":
    import sys
    import tkinter as tk
    from utils.my_document import myDocument
    from utils.logger import EnhancedLogger
    from utils.datapanel import dataPanel

    print("=" * 60)
    print(" WindLoadCalculator Geometri & Çizim Motoru Testi")
    print("=" * 60)

    # 1. Örnek Bir 3D Yapı Düğüm Noktaları (Örn: 10x6m Tabanlı, 4m Yüksekliğinde Bir Depo)
    sample_points = {
        "N1": [0.0, 0.0, 0.0],
        "N2": [10.0, 0.0, 0.0],
        "N3": [10.0, 6.0, 0.0],
        "N4": [0.0, 6.0, 0.0],
        "N5": [0.0, 0.0, 4.0],
        "N6": [10.0, 0.0, 4.0],
        "N7": [10.0, 6.0, 4.0],
        "N8": [0.0, 6.0, 4.0],
        "N9_Roof": [5.0, 3.0, 5.5]  # Mahya Noktası
    }

    # 2. Kullanıcının Ekranda Diyagonal İki Nokta Seçtiğini Varsayalım (Açılı Rüzgar)
    p1_selected = sample_points["N1"]
    p2_selected = sample_points["N7"]  # Çapraz hat

    print(f"\n[1] Seçilen Referans Noktalar : N1{p1_selected} -> N7{p2_selected}")

    # 3. Geometri ve OBB Hesabı
    geom_results = WindLoadCalculator.calculate_obb_and_geometry(
        p1_selected, p2_selected, sample_points
    )

    if geom_results:
        print("\n[2] Türetilen Geometrik Mühendislik Parametreleri:")
        print(f"    - Dik Genişlik (b)    : {geom_results['b']:.2f} m")
        print(f"    - Paralel Derinlik (d): {geom_results['d']:.2f} m")
        print(f"    - Bina Yüksekliği (h) : {geom_results['h']:.2f} m")
        print(f"    - Kritik Boyut (e)    : {geom_results['e']:.2f} m  [min(b, 2h)]")
        print(f"    - Etkime Noktası (Z=0): {[round(c, 2) for c in geom_results['impact_point']]}")

        # 4. View3D'ye Gönderilecek Çizim Primitifleri
        render_lines = WindLoadCalculator.generate_render_lines(geom_results)
        print(f"\n[3] View3D Rendering Testi:")
        print(f"    - Üretilen Toplam Çizgi Segmenti Sayısı: {len(render_lines)}")
        print(f"    - İlk Çizgi (OBB Kenarı 1)               : {render_lines[0]}")
        print(f"    - Son Çizgi ('W' Harfi Segmenti)         : {render_lines[-1]}")

        
        wind_config = WindLoadCalculator.build_wind_config(
            geom_results, 
            user_overrides={"egim": 15.0, "roof_type": "Beşik"}
        )
        print("\n[4] Oluşturulan WindLoad Config Sözlüğü:")
        for k, v in wind_config.items():
            print(f"    - {k:<15}: {v}")

        print("\n Test Başarıyla Tamamlandı! Kasıntısız, Temiz Matematik Output'u Hazır.")
    else:
        print("\n HATA: Geçersiz noktalar veya çakışan koordinatlar!")


    root = tk.Tk()
    dataPanel(
        root,
        wind_config,
        title="Rüzgar Parametreleri"
    ).pack()
    
    text = tk.Text(root, width=80, height=25)
    text.pack(fill="both", expand=True)

    logger = EnhancedLogger(text)

    sys.stdout = logger
    
    doc = myDocument()
    doc.apply_visual_settings()
    doc.add_heading_numbered("RÜZGAR ANALİZİ", level=1)
    
    
    doc = None

    def run_():
        global doc

        doc = myDocument()
        doc.apply_visual_settings()
        doc.add_heading_numbered(
            "RÜZGAR ANALİZİ",
            level=1
        )

        wind = WindLoad(wind_config)

        for report in wind.get_all_reports():

            report.save_to_docx(
                doc,
                level=2
            )

            print(f"\n{report.custom_title}")
            print("-" * 50)
            print(f"\n{report.custom_desc}")
            print(report)


    def prev_():

        if doc is None:
            return

        doc.preview(root)
        
        
    tk.Button(root, text="Run", command=run_).pack(side=tk.LEFT, padx=2)
    tk.Button(root, text="Preview", command=prev_).pack(side=tk.LEFT, padx=2)
    
    root.mainloop()