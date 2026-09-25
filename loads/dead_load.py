"""
Ölü Yükler (Dead Load) - TS 498 / TS EN 1991-1-1

Sabit yükler:
- Malzeme birim ağırlıkları
- Kaplama, sıva, asma tavan
- Sabit ekipman yükleri
- Bölme duvarlar
"""

from typing import Dict, Any, Optional, List, Tuple, Union
from utils.report_dataframe import ReportDataFrame
from data.dead_load_data import (
    MATERIAL_WEIGHTS,
    DEFAULT_LOADS,
    STRUCTURE_DESCRIPTIONS,
    STRUCTURE_CATEGORIES,
    get_structure_types,
    get_material_weight,
    get_material_categories
)


class DeadLoad:
    """
    Ölü Yük Hesaplama Sınıfı - TS 498 uyumlu
    
    Kullanım:
        config = {
            "structure_type": "ahşap_konut",  # Varsayılan yapı tipi
            "roof_covering": 0.5,             # kN/m² (opsiyonel)
            "ceiling": 0.3,                   # kN/m² (opsiyonel)
            "floor_finish": 1.0,              # kN/m² (opsiyonel)
            "plaster": 0.5,                   # kN/m² (opsiyonel)
            "partition": 0.5,                 # kN/m² (opsiyonel)
            "additional_dead": 0.0,           # kN/m² (opsiyonel)
            "equipment": 0.0,                 # kN/m² (opsiyonel)
            "mechanical": 0.0,                # kN/m² (opsiyonel)
            "snow_guard": 0.0,                # kN/m² (opsiyonel)
            "material": "ahşap_çam",          # Malzeme adı
            "material_thickness": 0.0         # Kalınlık (m)
        }
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Args:
            config: Yük parametreleri sözlüğü
                   None verilirse varsayılan değerler kullanılır
        """
        self.config = config or {}
        self._load_defaults()
        self._parse_config()
        self._calculate()
    
    def _load_defaults(self):
        """TS 498'e göre varsayılan değerleri yükler"""
        structure_type = self.config.get("structure_type", "ahşap_konut")
        defaults = DEFAULT_LOADS.get(structure_type, DEFAULT_LOADS["ahşap_konut"])
        
        # Config'den gelen değerler, varsayılanları ezer
        for key, value in defaults.items():
            if key not in self.config:
                self.config[key] = value
        
        # Yapı tipi açıklamasını ekle
        self.structure_description = STRUCTURE_DESCRIPTIONS.get(
            structure_type, 
            "Belirtilmemiş yapı tipi"
        )
    
    def _parse_config(self):
        """Config'den değerleri alır"""
        # Sayısal değerler - float'a çevir
        self.roof_covering = self._get_float("roof_covering", 0.5)
        self.ceiling = self._get_float("ceiling", 0.3)
        self.snow_guard = self._get_float("snow_guard", 0.0)
        self.floor_finish = self._get_float("floor_finish", 1.0)
        self.plaster = self._get_float("plaster", 0.5)
        self.partition = self._get_float("partition", 0.5)
        self.additional_dead = self._get_float("additional_dead", 0.0)
        self.equipment = self._get_float("equipment", 0.0)
        self.mechanical = self._get_float("mechanical", 0.0)
        self.material_thickness = self._get_float("material_thickness", 0.0)
        
        # String değerler - olduğu gibi al
        self.material = self.config.get("material", "ahşap_çam")
        self.structure_type = self.config.get("structure_type", "ahşap_konut")
    
    def _get_float(self, key: str, default: float) -> float:
        """Config'den float değer alır, yoksa default döner"""
        value = self.config.get(key, default)
        if value is None:
            return float(default)
        try:
            return float(value)
        except (ValueError, TypeError):
            return float(default)
    
    def _calculate(self):
        """Ölü yükleri hesaplar"""
        # Çatı ölü yükü
        self.roof_dead = (
            self.roof_covering +
            self.ceiling +
            self.snow_guard +
            self.additional_dead +
            self.mechanical
        )
        
        # Kat ölü yükü
        self.floor_dead = (
            self.floor_finish +
            self.plaster +
            self.partition +
            self.additional_dead +
            self.equipment +
            self.mechanical
        )
        
        # Malzeme ağırlığı (opsiyonel)
        self.material_weight = self._calculate_material_weight()
        
        # Toplam ölü yük
        self.total_dead = max(self.roof_dead, self.floor_dead)
    
    def _calculate_material_weight(self) -> float:
        """
        Malzeme ağırlığını hesaplar (opsiyonel)
        
        Returns:
            Malzeme ağırlığı (kN/m²)
        """
        if self.material_thickness <= 0:
            return 0.0
        
        weight = get_material_weight(self.material)
        return weight * self.material_thickness
    
    def get_load_patterns(self) -> Dict[str, float]:
        """
        SAP2000 yük kalıplarını döndürür
        
        Returns:
            {"DEAD_ROOF": float, "DEAD_FLOOR": float, ...}
        """
        patterns = {
            "DEAD_ROOF": round(self.roof_dead, 3),
            "DEAD_FLOOR": round(self.floor_dead, 3),
            "DEAD_TOTAL": round(self.total_dead, 3)
        }
        
        if self.material_weight > 0:
            patterns["DEAD_MATERIAL"] = round(self.material_weight, 3)
        
        return patterns
    
    def get_section_loads(self, section_type: str = "roof") -> float:
        """
        Belirli bir bölüm için ölü yükü döndürür
        
        Args:
            section_type: "roof" veya "floor"
        
        Returns:
            Ölü yük (kN/m²)
        """
        if section_type.lower() == "roof":
            return self.roof_dead
        else:
            return self.floor_dead
    
    def add_custom_material(self, name: str, weight: float):
        """
        Özel malzeme ekler veya günceller
        
        Args:
            name: Malzeme adı
            weight: Birim ağırlık (kN/m³)
        """
        from data.dead_load_data import MATERIAL_WEIGHTS as global_weights
        global_weights[name] = weight
    
    def get_material_info(self) -> Dict[str, Any]:
        """
        Malzeme bilgilerini döndürür
        
        Returns:
            {"name": str, "weight": float, "thickness": float}
        """
        return {
            "name": self.material,
            "weight": get_material_weight(self.material),
            "thickness": self.material_thickness,
            "weight_per_area": self.material_weight
        }
    
    @classmethod
    def get_available_structure_types(cls, category: str = None) -> List[str]:
        """
        Mevcut yapı tiplerini döndürür
        
        Args:
            category: "ahşap", "betonarme", "çelik", "hafif", "özel"
        
        Returns:
            Yapı tipi listesi
        """
        return get_structure_types(category)
    
    @classmethod
    def get_material_categories(cls) -> Dict[str, List[str]]:
        """
        Malzeme kategorilerini döndürür
        
        Returns:
            Kategori bazında malzeme sözlüğü
        """
        return get_material_categories()
    
    def report(self) -> ReportDataFrame:
        """
        Ölü yük raporunu döndürür
        
        Returns:
            ReportDataFrame
        """
        # TS 498 referans bilgisi
        ts498_ref = """
        TS 498 - Yapı Elemanlarının Boyutlandırılmasında Alınacak Yüklerin Hesap Değerleri
        """
        
        # Malzeme bilgileri
        material_info = self.get_material_info()
        
        # Veri hazırlama
        parametreler = [
            "Yapı Tipi",
            "Yapı Açıklaması",
            "Çatı Kaplama",
            "Asma Tavan",
            "Kar Tutucu",
            "Döşeme Kaplama",
            "Sıva",
            "Hafif Bölme Duvar",
            "Ekipman Yükü",
            "Mekanik Tesisat",
            "Ek Ölü Yük",
            "Malzeme",
            "Malzeme Kalınlığı",
            "Malzeme Birim Ağırlığı",
        ]
        
        degerler = [
            self.structure_type,
            self.structure_description,
            self.roof_covering,
            self.ceiling,
            self.snow_guard,
            self.floor_finish,
            self.plaster,
            self.partition,
            self.equipment,
            self.mechanical,
            self.additional_dead,
            self.material,
            self.material_thickness,
            material_info["weight"],
        ]
        
        birimler = [
            "-",
            "-",
            "kN/m²",
            "kN/m²",
            "kN/m²",
            "kN/m²",
            "kN/m²",
            "kN/m²",
            "kN/m²",
            "kN/m²",
            "kN/m²",
            "-",
            "m",
            "kN/m³",
        ]
        
        # Malzeme ağırlığı varsa ekle
        if self.material_weight > 0:
            parametreler.append("Malzeme Ağırlığı")
            degerler.append(self.material_weight)
            birimler.append("kN/m²")
        
        # Toplam yükleri ekle
        parametreler.extend(["Toplam Çatı Ölü Yükü", "Toplam Kat Ölü Yükü"])
        degerler.extend([round(self.roof_dead, 3), round(self.floor_dead, 3)])
        birimler.extend(["kN/m²", "kN/m²"])
        
        data = {
            "Parametre": parametreler,
            "Değer": degerler,
            "Birim": birimler
        }
        
        # Açıklama oluştur
        desc = f"""
        {ts498_ref}
        
        Yapı Tipi: {self.structure_type}
        {self.structure_description}
        
        Çatı Ölü Yükü: {self.roof_dead:.3f} kN/m²
        Kat Ölü Yükü: {self.floor_dead:.3f} kN/m²
        
        Malzeme Bilgisi:
        • Malzeme: {self.material}
        • Kalınlık: {self.material_thickness:.3f} m
        • Birim Ağırlık: {material_info['weight']:.1f} kN/m³
        • Ağırlık: {self.material_weight:.3f} kN/m²
        
        Hesaplama Formülleri:
        • q_roof = roof_covering + ceiling + snow_guard + additional + mechanical
        • q_floor = floor_finish + plaster + partition + additional + equipment + mechanical
        • q_material = material_weight × thickness
        
        Standart: TS 498 Yapı Elemanlarının Boyutlandırılmasında Alınacak Yüklerin Hesap Değerleri
        """
        
        return ReportDataFrame(
            data,
            custom_title="Ölü Yük Analizi (Dead Load) - TS 498",
            custom_desc=desc
        )
    
    def to_dict(self) -> Dict[str, float]:
        """
        Tüm yükleri dictionary olarak döndürür
        
        Returns:
            {"roof_dead": float, "floor_dead": float, ...}
        """
        return {
            "roof_covering": self.roof_covering,
            "ceiling": self.ceiling,
            "snow_guard": self.snow_guard,
            "floor_finish": self.floor_finish,
            "plaster": self.plaster,
            "partition": self.partition,
            "equipment": self.equipment,
            "mechanical": self.mechanical,
            "additional_dead": self.additional_dead,
            "roof_dead": self.roof_dead,
            "floor_dead": self.floor_dead,
            "total_dead": self.total_dead,
            "material_weight": self.material_weight
        }


# Yardımcı fonksiyonlar
def create_dead_load(structure_type: str = "ahşap_konut", 
                     custom_loads: Optional[Dict[str, Any]] = None) -> DeadLoad:
    """
    Kolay başlangıç için yardımcı fonksiyon
    
    Args:
        structure_type: Yapı tipi
        custom_loads: Özel yük değerleri (opsiyonel)
    
    Returns:
        DeadLoad nesnesi
    """
    config = {"structure_type": structure_type}
    if custom_loads:
        config.update(custom_loads)
    return DeadLoad(config)


def list_structure_types(category: str = None) -> List[str]:
    """
    Mevcut yapı tiplerini listeler
    
    Args:
        category: "ahşap", "betonarme", "çelik", "hafif", "özel"
    
    Returns:
        Yapı tipi listesi
    """
    return DeadLoad.get_available_structure_types(category)


def get_material_info(material_name: str) -> Dict[str, Any]:
    """
    Malzeme bilgilerini döndürür
    
    Args:
        material_name: Malzeme adı
    
    Returns:
        {"name": str, "weight": float, "category": str}
    """
    weight = get_material_weight(material_name)
    category = "Bilinmiyor"
    
    for cat, materials in get_material_categories().items():
        if material_name in materials:
            category = cat
            break
    
    return {
        "name": material_name,
        "weight": weight,
        "category": category,
        "unit": "kN/m³"
    }


if __name__ == "__main__":
    # 1. Mevcut yapı tiplerini listele
    print("=" * 60)
    print("MEVCUT YAPI TİPLERİ")
    print("=" * 60)
    print("Tüm tipler:", list_structure_types())
    print("Ahşap:", list_structure_types("ahşap"))
    print("Betonarme:", list_structure_types("betonarme"))
    print("Çelik:", list_structure_types("çelik"))
    
    print("\n" + "=" * 60)
    print("ÖRNEK KULLANIMLAR")
    print("=" * 60)
    
    # 2. Betonarme ofis
    dead = create_dead_load("betonarme_ofis")
    print("\nBetonarme Ofis:")
    print(f"   Çatı: {dead.roof_dead:.3f} kN/m²")
    print(f"   Kat: {dead.floor_dead:.3f} kN/m²")
    print(f"   Yük Kalıpları: {dead.get_load_patterns()}")
    
    # 3. Özel konfigürasyon
    config = {
        "structure_type": "ahşap_konut",
        "roof_covering": 0.6,
        "floor_finish": 3.0,
        "equipment": 0.5,
        "material": "çelik",
        "material_thickness": 0.015
    }
    dead2 = DeadLoad(config)
    print("\nÇelik Endüstriyel:")
    print(f"   Çatı: {dead2.roof_dead:.3f} kN/m²")
    print(f"   Kat: {dead2.floor_dead:.3f} kN/m²")
    print(f"   Yük Kalıpları: {dead2.get_load_patterns()}")
    
    # 4. Rapor göster
    print("\n" + "=" * 60)
    print("RAPOR ÖRNEĞİ")
    print("=" * 60)
    report = dead.report()
    print(report)