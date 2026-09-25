"""
Hareketli Yükler (Live Load) - TS 498 / TS EN 1991-1-1

Kullanım yükleri:
- Konut, ofis, okul, ticaret, depo vb. yapılar
- Çatı bakım yükleri
- Özel kullanım yükleri
"""

from typing import Dict, Any, Optional, List, Union
from utils.report_dataframe import ReportDataFrame
from data.live_load_data import (
    LIVE_LOADS,
    STRUCTURE_CATEGORIES,
    STRUCTURE_DESCRIPTIONS,
    get_live_load,
    get_reduction_factor,
    get_structure_categories,
    get_category_description
)


class LiveLoad:
    """
    Hareketli Yük Hesaplama Sınıfı - TS 498 uyumlu
    
    Kullanım:
        config = {
            "usage_type": "konut",           # Kullanım tipi
            "roof_accessible": False,        # Çatı erişilebilir mi?
            "roof_maintenance_load": 0.75,   # Çatı bakım yükü (kN/m²)
            "reduction_factor": 0.5,         # Azaltma faktörü (opsiyonel)
            "additional_live": 0.0,          # Ek hareketli yük (kN/m²)
            "category": "konut"              # Kategori (opsiyonel)
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
        # Kullanım tipine göre varsayılan değerler
        usage_type = self.config.get("usage_type", "konut")
        
        # Kullanım tipi açıklaması
        self.usage_description = STRUCTURE_DESCRIPTIONS.get(
            usage_type,
            "Belirtilmemiş kullanım tipi"
        )
        
        # Kategori
        if "category" not in self.config:
            for cat, types in STRUCTURE_CATEGORIES.items():
                if usage_type in types:
                    self.config["category"] = cat
                    break
            if "category" not in self.config:
                self.config["category"] = "konut"
    
    def _parse_config(self):
        """Config'den değerleri alır"""
        # String değerler
        self.usage_type = self.config.get("usage_type", "konut")
        self.category = self.config.get("category", "konut")
        
        # Boolean değerler
        self.roof_accessible = self.config.get("roof_accessible", False)
        
        # Sayısal değerler
        self.roof_maintenance_load = self._get_float("roof_maintenance_load", 0.75)
        self.additional_live = self._get_float("additional_live", 0.0)
        
        # Azaltma faktörü (kullanıcı tanımlı veya otomatik)
        self.reduction_factor = self.config.get("reduction_factor")
        if self.reduction_factor is None:
            self.reduction_factor = get_reduction_factor(self.usage_type)
        else:
            self.reduction_factor = self._get_float("reduction_factor", 0.5)
    
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
        """Hareketli yükleri hesaplar"""
        # 1. Temel hareketli yük
        self.base_load = get_live_load(self.usage_type)
        
        # 2. Çatı hareketli yükü
        if self.roof_accessible:
            # Erişilebilir çatı - min 2.0 kN/m²
            self.roof_live = max(self.roof_maintenance_load, 2.0)
            self.roof_note = "Erişilebilir çatı → min 2.0 kN/m²"
        else:
            # Erişilemeyen çatı - bakım yükü
            self.roof_live = self.roof_maintenance_load
            self.roof_note = "Standart bakım yükü (Kategori H)"
        
        # 3. Azaltılmış kat yükü
        self.floor_live = self.base_load * self.reduction_factor
        
        # 4. Ek yüklerle birlikte
        self.total_floor_live = self.floor_live + self.additional_live
        self.total_roof_live = self.roof_live + self.additional_live
        
        # 5. Maksimum hareketli yük
        self.max_live = max(self.total_floor_live, self.total_roof_live)
        
        # 6. Kategori açıklaması
        self.category_description = get_category_description(self.category)
    
    def get_load_patterns(self) -> Dict[str, float]:
        """
        SAP2000 yük kalıplarını döndürür
        
        Returns:
            {"LIVE_FLOOR": float, "LIVE_ROOF": float, ...}
        """
        patterns = {
            "LIVE_FLOOR": round(self.total_floor_live, 3),
            "LIVE_ROOF": round(self.total_roof_live, 3),
            "LIVE_TOTAL": round(self.max_live, 3),
            "LIVE_BASE": round(self.base_load, 3)
        }
        
        if self.reduction_factor < 1.0:
            patterns["LIVE_REDUCED"] = round(self.floor_live, 3)
        
        return patterns
    
    def get_section_loads(self, section_type: str = "floor") -> float:
        """
        Belirli bir bölüm için hareketli yükü döndürür
        
        Args:
            section_type: "floor" veya "roof"
        
        Returns:
            Hareketli yük (kN/m²)
        """
        if section_type.lower() == "roof":
            return self.total_roof_live
        else:
            return self.total_floor_live
    
    def get_reduced_load(self, floor_count: int = 1) -> float:
        """
        Kat sayısına göre azaltılmış yükü hesaplar
        
        TS 498 Madde 7.2'ye göre:
        - 1-2 kat: %100
        - 3-5 kat: %80
        - 6-10 kat: %60
        - 10+ kat: %50
        
        Args:
            floor_count: Kat sayısı
        
        Returns:
            Azaltılmış yük (kN/m²)
        """
        if floor_count <= 2:
            reduction = 1.0
        elif floor_count <= 5:
            reduction = 0.8
        elif floor_count <= 10:
            reduction = 0.6
        else:
            reduction = 0.5
        
        return self.base_load * reduction
    
    def is_accessible_roof(self) -> bool:
        """
        Çatının erişilebilir olup olmadığını döndürür
        
        Returns:
            bool
        """
        return self.roof_accessible
    
    def get_category_info(self) -> Dict[str, str]:
        """
        Kategori bilgilerini döndürür
        
        Returns:
            {"category": str, "description": str}
        """
        return {
            "category": self.category,
            "description": self.category_description
        }
    
    @classmethod
    def get_available_usage_types(cls, category: str = None) -> List[str]:
        """
        Mevcut kullanım tiplerini döndürür
        
        Args:
            category: Kategori (opsiyonel)
        
        Returns:
            Kullanım tipi listesi
        """
        if category:
            return STRUCTURE_CATEGORIES.get(category, [])
        return list(LIVE_LOADS.keys())
    
    @classmethod
    def get_categories(cls) -> Dict[str, str]:
        """
        Tüm kategorileri ve açıklamalarını döndürür
        
        Returns:
            {"category": "description", ...}
        """
        return {
            cat: get_category_description(cat) 
            for cat in STRUCTURE_CATEGORIES.keys()
        }
    
    @classmethod
    def get_load_value(cls, usage_type: str) -> float:
        """
        Belirli bir kullanım tipi için yük değerini döndürür
        
        Args:
            usage_type: Kullanım tipi
        
        Returns:
            Hareketli yük (kN/m²)
        """
        return get_live_load(usage_type)
    
    def report(self) -> ReportDataFrame:
        """
        Hareketli yük raporunu döndürür
        
        Returns:
            ReportDataFrame
        """
        # TS 498 referans bilgisi
        ts498_ref = """
        TS 498 - Yapı Elemanlarının Boyutlandırılmasında Alınacak Yüklerin Hesap Değerleri
        TS EN 1991-1-1 - Yapılar Üzerindeki Etkiler - Genel Etkiler
        """
        
        # Veri hazırlama
        parametreler = [
            "Kullanım Tipi",
            "Kategori",
            "Kategori Açıklaması",
            "Temel Hareketli Yük",
            "Azaltma Faktörü",
            "Azaltılmış Kat Yükü",
            "Çatı Erişilebilirliği",
            "Çatı Bakım Yükü",
            "Çatı Hareketli Yükü",
            "Ek Hareketli Yük",
            "Toplam Kat Hareketli Yükü",
            "Toplam Çatı Hareketli Yükü"
        ]
        
        degerler = [
            self.usage_type,
            self.category,
            self.category_description,
            self.base_load,
            self.reduction_factor,
            round(self.floor_live, 3),
            "Erişilebilir" if self.roof_accessible else "Erişilemez",
            self.roof_maintenance_load,
            round(self.roof_live, 3),
            self.additional_live,
            round(self.total_floor_live, 3),
            round(self.total_roof_live, 3)
        ]
        
        birimler = [
            "-",
            "-",
            "-",
            "kN/m²",
            "-",
            "kN/m²",
            "-",
            "kN/m²",
            "kN/m²",
            "kN/m²",
            "kN/m²",
            "kN/m²"
        ]
        
        data = {
            "Parametre": parametreler,
            "Değer": degerler,
            "Birim": birimler
        }
        
        # Açıklama oluştur
        desc = f"""
        {ts498_ref}
        
        Kullanım Tipi: {self.usage_type}
        {self.usage_description}
        
        Kategori: {self.category}
        {self.category_description}
        
        Temel Yük: {self.base_load:.3f} kN/m²
        Kat Yükü: {self.total_floor_live:.3f} kN/m²
        Çatı Yükü: {self.total_roof_live:.3f} kN/m²
        
        Çatı Bilgisi:
        • Erişilebilir: {"Evet" if self.roof_accessible else "Hayır"}
        • Bakım Yükü: {self.roof_maintenance_load:.3f} kN/m²
        • {self.roof_note}
        
        Azaltma Bilgisi:
        • Faktör: {self.reduction_factor:.2f}
        • Azaltılmış Yük: {self.floor_live:.3f} kN/m²
        
        TS 498 Madde 7.2 - Hareketli Yük Azaltma Faktörleri:
        • 1-2 kat: %100
        • 3-5 kat: %80
        • 6-10 kat: %60
        • 10+ kat: %50
        """
        
        return ReportDataFrame(
            data,
            custom_title="Hareketli Yük Analizi (Live Load) - TS 498",
            custom_desc=desc
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Tüm yükleri dictionary olarak döndürür
        
        Returns:
            {"base_load": float, "floor_live": float, ...}
        """
        return {
            "usage_type": self.usage_type,
            "category": self.category,
            "category_description": self.category_description,
            "base_load": self.base_load,
            "reduction_factor": self.reduction_factor,
            "floor_live": self.floor_live,
            "roof_live": self.roof_live,
            "additional_live": self.additional_live,
            "total_floor_live": self.total_floor_live,
            "total_roof_live": self.total_roof_live,
            "max_live": self.max_live,
            "roof_accessible": self.roof_accessible,
            "roof_maintenance_load": self.roof_maintenance_load,
            "roof_note": self.roof_note
        }


# Yardımcı fonksiyonlar
def create_live_load(usage_type: str = "konut", 
                     roof_accessible: bool = False,
                     roof_maintenance_load: float = 0.75,
                     reduction_factor: Optional[float] = None,
                     additional_live: float = 0.0,
                     category: Optional[str] = None,
                     **kwargs) -> LiveLoad:
    """
    Kolay başlangıç için yardımcı fonksiyon
    
    Args:
        usage_type: Kullanım tipi
        roof_accessible: Çatı erişilebilir mi?
        roof_maintenance_load: Çatı bakım yükü (kN/m²)
        reduction_factor: Azaltma faktörü (opsiyonel)
        additional_live: Ek hareketli yük (kN/m²)
        category: Kategori (opsiyonel)
        **kwargs: Diğer parametreler
    
    Returns:
        LiveLoad nesnesi
    """
    config = {
        "usage_type": usage_type,
        "roof_accessible": roof_accessible,
        "roof_maintenance_load": roof_maintenance_load,
        "additional_live": additional_live
    }
    
    if reduction_factor is not None:
        config["reduction_factor"] = reduction_factor
    
    if category is not None:
        config["category"] = category
    
    # Ek parametreleri ekle
    config.update(kwargs)
    
    return LiveLoad(config)


def list_usage_types(category: str = None) -> List[str]:
    """
    Mevcut kullanım tiplerini listeler
    
    Args:
        category: Kategori (opsiyonel)
    
    Returns:
        Kullanım tipi listesi
    """
    return LiveLoad.get_available_usage_types(category)


def list_categories() -> Dict[str, str]:
    """
    Tüm kategorileri listeler
    
    Returns:
        {"category": "description", ...}
    """
    return LiveLoad.get_categories()


if __name__ == "__main__":
    # 1. Mevcut kullanım tiplerini listele
    print("=" * 60)
    print("MEVCUT KULLANIM TİPLERİ")
    print("=" * 60)
    print("Tüm tipler:", list_usage_types())
    print("\nKategoriler:", list_categories())
    print("\nKonut tipleri:", list_usage_types("konut"))
    print("Ofis tipleri:", list_usage_types("ofis"))
    print("Okul tipleri:", list_usage_types("okul"))
    print("Çatı tipleri:", list_usage_types("cati"))
    
    print("\n" + "=" * 60)
    print("ÖRNEK KULLANIMLAR")
    print("=" * 60)
    
    # 2. Varsayılan konut
    live1 = create_live_load("konut")
    print("\n1. Konut:")
    print(f"   Kat: {live1.total_floor_live:.3f} kN/m²")
    print(f"   Çatı: {live1.total_roof_live:.3f} kN/m²")
    print(f"   Yük Kalıpları: {live1.get_load_patterns()}")
    
    # 3. Ofis
    live2 = create_live_load("ofis_genel")
    print("\n2. Ofis:")
    print(f"   Kat: {live2.total_floor_live:.3f} kN/m²")
    print(f"   Çatı: {live2.total_roof_live:.3f} kN/m²")
    print(f"   Yük Kalıpları: {live2.get_load_patterns()}")
    
    # 4. Erişilebilir çatılı mağaza
    live3 = create_live_load(
        usage_type="mağaza",
        roof_accessible=True,
        roof_maintenance_load=1.5,
        additional_live=0.5
    )
    print("\n3. Mağaza (Erişilebilir Çatı):")
    print(f"   Kat: {live3.total_floor_live:.3f} kN/m²")
    print(f"   Çatı: {live3.total_roof_live:.3f} kN/m²")
    print(f"   Çatı Notu: {live3.roof_note}")
    print(f"   Yük Kalıpları: {live3.get_load_patterns()}")
    
    # 5. Depo
    live4 = create_live_load("depo_agir")
    print("\n4. Ağır Depo:")
    print(f"   Kat: {live4.total_floor_live:.3f} kN/m²")
    print(f"   Yük Kalıpları: {live4.get_load_patterns()}")
    
    # 6. Azaltma faktörü ile
    print("\n5. Kat Sayısına Göre Azaltma:")
    for floor_count in [2, 4, 8, 12]:
        reduced = live1.get_reduced_load(floor_count)
        print(f"   {floor_count} kat: {reduced:.3f} kN/m²")
    
    # 7. Rapor göster
    print("\n" + "=" * 60)
    print("RAPOR ÖRNEĞİ")
    print("=" * 60)
    report = live1.report()
    print(report)