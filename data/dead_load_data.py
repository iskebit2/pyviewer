"""
Ölü Yük Verileri - TS 498 / TS EN 1991-1-1

Kaynak: TS 498 Yapı Elemanlarının Boyutlandırılmasında Alınacak Yüklerin Hesap Değerleri
"""

# ============================================================================
# 1. MALZEME BİRİM AĞIRLIKLARI (kN/m³)
# ============================================================================
# TS 498 Tablo 1 - Malzeme Birim Hacim Ağırlıkları

MATERIAL_WEIGHTS = {
    # AHŞAP MALZEMELER
    "ahşap_çam": 5.0,
    "ahşap_meşe": 6.0,
    "ahşap_kayın": 7.0,
    "ahşap_ladin": 4.5,
    "ahşap_kestane": 6.5,
    "ahşap_huş": 6.0,
    "ahşap_akçaağaç": 7.0,
    "ahşap_dişbudak": 7.0,
    "ahşap_ceviz": 6.0,
    "ahşap_karaağaç": 6.5,
    "ahşap_ıhlamur": 5.0,
    "ahşap_söğüt": 4.5,
    "ahşap_kavak": 4.0,
    "ahşap_okaliptüs": 8.0,
    "ahşap_maun": 6.5,
    "ahşap_abanoz": 11.0,
    "ahşap_gül": 8.0,
    "ahşap_palmiye": 7.0,
    "ahşap_bambu": 6.0,
    "ahşap_kontrplak": 6.0,
    "ahşap_sunta": 7.0,
    "ahşap_mdf": 7.0,
    "ahşap_osb": 6.5,
    "ahşap_lvl": 5.5,
    "ahşap_glulam": 5.0,
    "ahşap_clt": 5.0,
    
    # BETON MALZEMELER
    "betonarme": 25.0,
    "beton_hafif": 18.0,
    "beton_agir": 28.0,
    "beton_gaz": 6.0,
    "beton_ytong": 6.0,
    "beton_pomza": 12.0,
    "beton_hapsol": 10.0,
    "beton_selüloz": 8.0,
    "beton_perlit": 8.0,
    "beton_vermikülit": 6.0,
    "beton_köpük": 5.0,
    "beton_geopolimer": 24.0,
    "beton_uhpc": 28.0,
    "beton_fiber": 25.0,
    
    # ÇELİK MALZEMELER
    "çelik": 78.5,
    "çelik_paslanmaz": 79.0,
    "çelik_galvaniz": 78.5,
    "çelik_karbon": 78.5,
    "çelik_alasimli": 78.5,
    "çelik_boru": 78.5,
    "çelik_profil": 78.5,
    "çelik_sac": 78.5,
    "çelik_hasir": 78.5,
    "çelik_kablo": 78.5,
    "çelik_halat": 78.5,
    
    # DUVAR MALZEMELERİ
    "tuğla_dolu": 18.0,
    "tuğla_delikli": 14.0,
    "tuğla_hafif": 10.0,
    "tuğla_ısı": 8.0,
    "tuğla_yangın": 20.0,
    "bims": 10.0,
    "gazbeton": 6.0,
    "ytong": 6.0,
    "hafif_duvar": 5.0,
    "agir_duvar": 20.0,
    "taş_doğal": 25.0,
    "taş_yapay": 22.0,
    "mermer": 27.0,
    "granit": 28.0,
    "kireçtaşı": 22.0,
    "kumtaşı": 23.0,
    "bazalt": 29.0,
    "andezit": 26.0,
    "traverten": 24.0,
    "oniks": 27.0,
    "serpantin": 26.0,
    "kalker": 24.0,
    "dolomit": 27.0,
    "kuvarsit": 27.0,
    "şist": 26.0,
    "gnays": 27.0,
    "granodiyorit": 28.0,
    "siyenit": 27.0,
    "diyorit": 28.0,
    "gabro": 29.0,
    "peridotit": 30.0,
    "piroksenit": 31.0,
    
    # KAPLAMA MALZEMELERİ
    "seramik": 22.0,
    "porselen": 24.0,
    "cam": 25.0,
    "cam_yalıtım": 0.5,
    "cam_lif": 0.2,
    "cam_elyaf": 0.3,
    "alüminyum": 27.0,
    "alüminyum_kompozit": 5.0,
    "bakır": 89.0,
    "çinko": 71.0,
    "kurşun": 113.0,
    "çatı_kiremidi": 0.5,       # kN/m²
    "çatı_sac": 0.15,           # kN/m²
    "çatı_oluk": 0.1,           # kN/m²
    "çatı_mahya": 0.2,          # kN/m²
    "çatı_izolasyon": 0.1,      # kN/m² (5cm için)
    "çatı_su_yalıtımı": 0.05,   # kN/m²
    "çatı_buhar_kesici": 0.02,  # kN/m²
    "çatı_anti_kondans": 0.03,  # kN/m²
    "çatı_akustik": 0.04,       # kN/m²
    "çatı_havalandırma": 0.02,  # kN/m²
    "çatı_güneş_paneli": 0.15,  # kN/m²
    "çatı_kar_tutucu": 0.1,     # kN/m²
    "çatı_yürüme_yolu": 0.2,    # kN/m²
    "çatı_merdiven": 0.3,       # kN/m²
    
    # İZOLASYON MALZEMELERİ
    "izolasyon_cam": 0.2,
    "izolasyon_taş": 0.3,
    "izolasyon_poliüretan": 0.4,
    "izolasyon_polistiren": 0.3,
    "izolasyon_eps": 0.3,
    "izolasyon_xps": 0.4,
    "izolasyon_pere": 0.5,
    "izolasyon_selüloz": 0.6,
    "izolasyon_kauçuk": 0.8,
    "izolasyon_mantar": 0.5,
    "izolasyon_keçe": 0.2,
    "izolasyon_folyo": 0.1,
    "izolasyon_akustik": 0.4,
    "izolasyon_ısı": 0.3,
    "izolasyon_su": 0.1,
    "izolasyon_buhar": 0.05,
    "izolasyon_yangın": 0.6,
    
    # DÖŞEME MALZEMELERİ
    "parke": 7.0,
    "parke_laminat": 6.0,
    "parke_ahşap": 7.0,
    "parke_masif": 8.0,
    "halı": 0.15,               # kN/m²
    "halı_yün": 0.2,            # kN/m²
    "halı_sentetik": 0.1,       # kN/m²
    "linolyum": 0.1,            # kN/m²
    "vinil": 0.1,               # kN/m²
    "epoksi": 0.2,              # kN/m²
    "şap": 22.0,
    "şap_anhidrit": 20.0,
    "şap_hafif": 15.0,
    "şap_ısı": 12.0,
    "şap_akustik": 10.0,
    "şap_kendiliğinden": 20.0,
    "şap_epoksi": 18.0,
    "şap_poliüretan": 15.0,
    "şap_çimento": 22.0,
    "şap_kalsiyum": 20.0,
    
    # ASMA TAVAN MALZEMELERİ
    "asma_tavan": 0.3,          # kN/m²
    "asma_tavan_ahşap": 0.25,   # kN/m²
    "asma_tavan_alüminyum": 0.2, # kN/m²
    "asma_tavan_çelik": 0.35,   # kN/m²
    "asma_tavan_akustik": 0.3,  # kN/m²
    "asma_tavan_sıva": 0.4,     # kN/m²
    "asma_tavan_cam": 0.3,      # kN/m²
    "asma_tavan_plastik": 0.15, # kN/m²
    
    # SIVA MALZEMELERİ
    "sıva": 20.0,
    "sıva_kireç": 18.0,
    "sıva_çimento": 22.0,
    "sıva_alçı": 16.0,
    "sıva_akustik": 12.0,
    "sıva_ısı": 10.0,
    "sıva_dekoratif": 18.0,
    "sıva_mermer": 24.0,
    
    # BÖLME DUVAR MALZEMELERİ
    "hafif_bölme": 0.5,         # kN/m²
    "agir_bölme": 2.0,          # kN/m²
    "bölme_alçıpan": 0.3,       # kN/m²
    "bölme_cam": 0.5,           # kN/m²
    "bölme_ahşap": 0.4,         # kN/m²
    "bölme_çelik": 0.6,         # kN/m²
    "bölme_mobilya": 0.5,       # kN/m²
    "bölme_raflı": 0.7,         # kN/m²
    "bölme_depo": 1.0,          # kN/m²
    
    # DOLGU MALZEMELERİ
    "dolgu_hafif": 5.0,
    "dolgu_agir": 18.0,
    "dolgu_kum": 16.0,
    "dolgu_çakıl": 18.0,
    "dolgu_toprak": 18.0,
    "dolgu_kohezif": 20.0,
    "dolgu_granüler": 19.0,
    "dolgu_geri": 17.0,
    
    # EKİPMAN YÜKLERİ
    "ekipman_hafif": 0.5,       # kN/m²
    "ekipman_orta": 1.0,        # kN/m²
    "ekipman_agir": 2.0,        # kN/m²
    "ekipman_çok_agir": 3.0,    # kN/m²
    "mekanik_hafif": 0.3,       # kN/m²
    "mekanik_orta": 0.5,        # kN/m²
    "mekanik_agir": 1.0,        # kN/m²
    "elektrik_hafif": 0.1,      # kN/m²
    "elektrik_orta": 0.2,       # kN/m²
    "elektrik_agir": 0.3,       # kN/m²
    "sıhhi_tesisat": 0.2,       # kN/m²
    "havalandırma": 0.3,        # kN/m²
    "asansör_makinesi": 5.0,    # kN/m²
    "jeneratör": 10.0,          # kN/m²
    "trafo": 15.0,              # kN/m²
    "klima_santrali": 2.0,      # kN/m²
    "soğutma_kulesi": 3.0,      # kN/m²
    "depo_raf": 5.0,            # kN/m²
    "vinç": 10.0,               # kN/m²
    
    # SU YALITIMI
    "su_yalıtımı": 0.05,        # kN/m²
    "su_yalıtımı_sıvı": 0.03,   # kN/m²
    "su_yalıtımı_membran": 0.04, # kN/m²
    "su_yalıtımı_bitüm": 0.05,  # kN/m²
    "su_yalıtımı_epoksi": 0.06, # kN/m²
    "su_yalıtımı_poliüretan": 0.04, # kN/m²
    "su_yalıtımı_akrilik": 0.03, # kN/m²
    
    # KAR TUTUCU
    "kar_tutucu": 0.1,          # kN/m²
    "kar_tutucu_boru": 0.15,    # kN/m²
    "kar_tutucu_plaka": 0.12,   # kN/m²
    "kar_tutucu_file": 0.08,    # kN/m²
    "kar_tutucu_kafes": 0.2,    # kN/m²
    "kar_tutucu_ısıtmalı": 0.3, # kN/m²
    
    # DİĞER MALZEMELER
    "çatı_kaplama": 0.5,        # kN/m²
    "döşeme_kaplama": 1.0,      # kN/m²
    "duvar_kaplama": 0.5,       # kN/m²
    "cephe_kaplama": 0.6,       # kN/m²
    "cephe_cam": 0.8,           # kN/m²
    "cephe_kompozit": 0.4,      # kN/m²
    "cephe_ahşap": 0.3,         # kN/m²
    "cephe_metal": 0.5,         # kN/m²
    "cephe_taş": 1.2,           # kN/m²
    "cephe_tuğla": 0.8,         # kN/m²
    "cephe_sıva": 0.4,          # kN/m²
    "cephe_seramik": 0.6,       # kN/m²
    "cephe_mermer": 1.0,        # kN/m²
}

# ============================================================================
# 2. TS 498 YAPI TİPLERİNE GÖRE VARSAYILAN YÜKLER
# ============================================================================

DEFAULT_LOADS = {
    # AHŞAP YAPILAR
    "ahşap_konut": {
        "roof_covering": 0.5,
        "ceiling": 0.3,
        "floor_finish": 0.5,
        "plaster": 0.5,
        "partition": 0.5,
        "additional_dead": 0.0,
        "material": "ahşap_çam",
        "material_thickness": 0.0
    },
    "ahşap_villa": {
        "roof_covering": 0.6,
        "ceiling": 0.3,
        "floor_finish": 0.8,
        "plaster": 0.5,
        "partition": 0.5,
        "additional_dead": 0.2,
        "material": "ahşap_meşe",
        "material_thickness": 0.0
    },
    "ahşap_ofis": {
        "roof_covering": 0.5,
        "ceiling": 0.3,
        "floor_finish": 0.8,
        "plaster": 0.5,
        "partition": 0.8,
        "additional_dead": 0.3,
        "material": "ahşap_ladin",
        "material_thickness": 0.0
    },
    "ahşap_depo": {
        "roof_covering": 0.5,
        "ceiling": 0.0,
        "floor_finish": 1.0,
        "plaster": 0.3,
        "partition": 0.0,
        "additional_dead": 0.5,
        "material": "ahşap_kestane",
        "material_thickness": 0.0
    },
    "ahşap_çatı": {
        "roof_covering": 0.5,
        "ceiling": 0.3,
        "floor_finish": 0.3,
        "plaster": 0.0,
        "partition": 0.0,
        "additional_dead": 0.0,
        "material": "ahşap_çam",
        "material_thickness": 0.0
    },
    
    # BETONARME YAPILAR
    "betonarme_konut": {
        "roof_covering": 0.5,
        "ceiling": 0.3,
        "floor_finish": 1.0,
        "plaster": 0.5,
        "partition": 0.5,
        "additional_dead": 0.0,
        "material": "betonarme",
        "material_thickness": 0.15
    },
    "betonarme_villa": {
        "roof_covering": 0.6,
        "ceiling": 0.3,
        "floor_finish": 1.5,
        "plaster": 0.5,
        "partition": 0.5,
        "additional_dead": 0.2,
        "material": "betonarme",
        "material_thickness": 0.18
    },
    "betonarme_ofis": {
        "roof_covering": 0.5,
        "ceiling": 0.3,
        "floor_finish": 1.5,
        "plaster": 0.5,
        "partition": 1.0,
        "additional_dead": 0.5,
        "material": "betonarme",
        "material_thickness": 0.20
    },
    "betonarme_depo": {
        "roof_covering": 0.5,
        "ceiling": 0.0,
        "floor_finish": 2.0,
        "plaster": 0.3,
        "partition": 0.0,
        "additional_dead": 1.0,
        "material": "betonarme",
        "material_thickness": 0.25
    },
    "betonarme_endüstriyel": {
        "roof_covering": 0.3,
        "ceiling": 0.0,
        "floor_finish": 2.5,
        "plaster": 0.0,
        "partition": 0.0,
        "additional_dead": 2.0,
        "material": "betonarme",
        "material_thickness": 0.30
    },
    "betonarme_çatı_teras": {
        "roof_covering": 0.5,
        "ceiling": 0.3,
        "floor_finish": 2.0,
        "plaster": 0.3,
        "partition": 0.0,
        "additional_dead": 0.5,
        "material": "betonarme",
        "material_thickness": 0.20
    },
    
    # ÇELİK YAPILAR
    "çelik_konut": {
        "roof_covering": 0.4,
        "ceiling": 0.3,
        "floor_finish": 0.8,
        "plaster": 0.3,
        "partition": 0.5,
        "additional_dead": 0.0,
        "material": "çelik",
        "material_thickness": 0.0
    },
    "çelik_ofis": {
        "roof_covering": 0.4,
        "ceiling": 0.3,
        "floor_finish": 1.5,
        "plaster": 0.3,
        "partition": 1.0,
        "additional_dead": 0.5,
        "material": "çelik",
        "material_thickness": 0.0
    },
    "çelik_depo": {
        "roof_covering": 0.3,
        "ceiling": 0.0,
        "floor_finish": 2.0,
        "plaster": 0.0,
        "partition": 0.0,
        "additional_dead": 1.0,
        "material": "çelik",
        "material_thickness": 0.0
    },
    "çelik_endüstriyel": {
        "roof_covering": 0.2,
        "ceiling": 0.0,
        "floor_finish": 2.5,
        "plaster": 0.0,
        "partition": 0.0,
        "additional_dead": 2.0,
        "material": "çelik",
        "material_thickness": 0.0
    },
    
    # HAFİF YAPILAR
    "hafif_konut": {
        "roof_covering": 0.4,
        "ceiling": 0.3,
        "floor_finish": 0.5,
        "plaster": 0.3,
        "partition": 0.3,
        "additional_dead": 0.0,
        "material": "ahşap_çam",
        "material_thickness": 0.0
    },
    "hafif_ofis": {
        "roof_covering": 0.4,
        "ceiling": 0.3,
        "floor_finish": 0.8,
        "plaster": 0.3,
        "partition": 0.5,
        "additional_dead": 0.3,
        "material": "ahşap_ladin",
        "material_thickness": 0.0
    },
    "hafif_depo": {
        "roof_covering": 0.3,
        "ceiling": 0.0,
        "floor_finish": 1.0,
        "plaster": 0.0,
        "partition": 0.0,
        "additional_dead": 0.5,
        "material": "ahşap_kavak",
        "material_thickness": 0.0
    },
    
    # ÖZEL YAPILAR
    "çatı_teras": {
        "roof_covering": 0.5,
        "ceiling": 0.3,
        "floor_finish": 2.0,
        "plaster": 0.3,
        "partition": 0.0,
        "additional_dead": 0.5,
        "material": "betonarme",
        "material_thickness": 0.20
    },
    "çatı_yeşil": {
        "roof_covering": 0.5,
        "ceiling": 0.3,
        "floor_finish": 3.0,
        "plaster": 0.0,
        "partition": 0.0,
        "additional_dead": 1.0,
        "material": "betonarme",
        "material_thickness": 0.25
    },
    "çatı_güneş": {
        "roof_covering": 0.4,
        "ceiling": 0.3,
        "floor_finish": 0.5,
        "plaster": 0.0,
        "partition": 0.0,
        "additional_dead": 0.5,
        "material": "çelik",
        "material_thickness": 0.0
    }
}

# ============================================================================
# 3. YAPI TİPİ AÇIKLAMALARI
# ============================================================================

STRUCTURE_DESCRIPTIONS = {
    "ahşap_konut": "Ahşap taşıyıcı sistemli konut yapısı",
    "ahşap_villa": "Ahşap taşıyıcı sistemli villa",
    "ahşap_ofis": "Ahşap taşıyıcı sistemli ofis binası",
    "ahşap_depo": "Ahşap taşıyıcı sistemli depo",
    "ahşap_çatı": "Ahşap çatı konstrüksiyonu",
    "betonarme_konut": "Betonarme taşıyıcı sistemli konut",
    "betonarme_villa": "Betonarme taşıyıcı sistemli villa",
    "betonarme_ofis": "Betonarme taşıyıcı sistemli ofis",
    "betonarme_depo": "Betonarme taşıyıcı sistemli depo",
    "betonarme_endüstriyel": "Betonarme endüstriyel yapı",
    "betonarme_çatı_teras": "Betonarme teras çatı",
    "çelik_konut": "Çelik taşıyıcı sistemli konut",
    "çelik_ofis": "Çelik taşıyıcı sistemli ofis",
    "çelik_depo": "Çelik taşıyıcı sistemli depo",
    "çelik_endüstriyel": "Çelik endüstriyel yapı",
    "hafif_konut": "Hafif çelik veya ahşap konut",
    "hafif_ofis": "Hafif çelik veya ahşap ofis",
    "hafif_depo": "Hafif çelik veya ahşap depo",
    "çatı_teras": "Teras çatı",
    "çatı_yeşil": "Yeşil çatı (ekolojik)",
    "çatı_güneş": "Güneş paneli çatı"
}

# ============================================================================
# 4. YAPI KATEGORİLERİ
# ============================================================================

STRUCTURE_CATEGORIES = {
    "ahşap": ["ahşap_konut", "ahşap_villa", "ahşap_ofis", "ahşap_depo", "ahşap_çatı"],
    "betonarme": ["betonarme_konut", "betonarme_villa", "betonarme_ofis", 
                  "betonarme_depo", "betonarme_endüstriyel", "betonarme_çatı_teras"],
    "çelik": ["çelik_konut", "çelik_ofis", "çelik_depo", "çelik_endüstriyel"],
    "hafif": ["hafif_konut", "hafif_ofis", "hafif_depo"],
    "özel": ["çatı_teras", "çatı_yeşil", "çatı_güneş"]
}

# ============================================================================
# 5. YARDIMCI FONKSİYONLAR
# ============================================================================

def get_structure_types(category: str = None) -> list:
    """
    Yapı tiplerini döndürür
    
    Args:
        category: "ahşap", "betonarme", "çelik", "hafif", "özel" (opsiyonel)
    
    Returns:
        Yapı tipi listesi
    """
    if category and category in STRUCTURE_CATEGORIES:
        return STRUCTURE_CATEGORIES[category]
    return list(DEFAULT_LOADS.keys())

def get_material_weight(material_name: str) -> float:
    """
    Malzeme birim ağırlığını döndürür
    
    Args:
        material_name: Malzeme adı
    
    Returns:
        Birim ağırlık (kN/m³), bulunamazsa 0
    """
    return MATERIAL_WEIGHTS.get(material_name, 0.0)

def get_material_categories() -> dict:
    """
    Malzeme kategorilerini döndürür
    
    Returns:
        Kategori bazında malzeme sözlüğü
    """
    categories = {}
    for name in MATERIAL_WEIGHTS.keys():
        # İlk kelimeye göre kategorize et
        prefix = name.split('_')[0] if '_' in name else name
        if prefix not in categories:
            categories[prefix] = []
        categories[prefix].append(name)
    return categories