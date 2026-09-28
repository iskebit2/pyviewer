# data/material_data.py
"""
Ölü Yük Verileri - TS 498 / TS EN 1991-1-1

REFACTORED:
- MATERIAL_LIBRARY: Her malzeme için weight + unit ('volumetric' | 'area') + name
- MATERIAL_WEIGHTS: Eski API ile uyumluluk için otomatik türetilir.
                    ('volumetric' → kN/m³ ağırlık, 'area' → kN/m² alan yükü)
"""

# ============================================================================
# 1. MALZEME KÜTÜPHANESİ (Birim bilgili)
# ============================================================================
# 'volumetric' -> kN/m³ (Kalınlıkla çarpılacak)
# 'area'       -> kN/m² (Doğrudan eklenecek)

MATERIAL_LIBRARY = {
    # --- AHŞAP MALZEMELER (Hacimsel: kN/m³) ---
    "ahşap_çam":        {"weight": 5.0,  "unit": "volumetric", "name": "Çam Ahşap"},
    "ahşap_meşe":       {"weight": 6.0,  "unit": "volumetric", "name": "Meşe Ahşap"},
    "ahşap_kayın":      {"weight": 7.0,  "unit": "volumetric", "name": "Kayın Ahşap"},
    "ahşap_ladin":      {"weight": 4.5,  "unit": "volumetric", "name": "Ladin Ahşap"},
    "ahşap_kestane":    {"weight": 6.5,  "unit": "volumetric", "name": "Kestane Ahşap"},
    "ahşap_osb":        {"weight": 6.5,  "unit": "volumetric", "name": "OSB Levha"},
    "ahşap_clt":        {"weight": 5.0,  "unit": "volumetric", "name": "CLT Panel"},
    "ahşap_kontrplak":  {"weight": 6.0,  "unit": "volumetric", "name": "Kontrplak"},
    "ahşap_glulam":     {"weight": 5.0,  "unit": "volumetric", "name": "Glulam"},
    "ahşap_mdf":        {"weight": 7.0,  "unit": "volumetric", "name": "MDF Levha"},
    "ahşap_sunta":      {"weight": 7.0,  "unit": "volumetric", "name": "Sunta"},
    "ahşap_lvl":        {"weight": 5.5,  "unit": "volumetric", "name": "LVL"},

    # --- BETON & DUVAR (Hacimsel: kN/m³) ---
    "betonarme":        {"weight": 25.0, "unit": "volumetric", "name": "Betonarme"},
    "beton_hafif":      {"weight": 18.0, "unit": "volumetric", "name": "Hafif Beton"},
    "gazbeton":         {"weight": 6.0,  "unit": "volumetric", "name": "Gazbeton / Ytong"},
    "ytong":            {"weight": 6.0,  "unit": "volumetric", "name": "Ytong"},
    "bims":             {"weight": 10.0, "unit": "volumetric", "name": "Bims"},
    "tuğla_dolu":       {"weight": 18.0, "unit": "volumetric", "name": "Dolu Harman Tuğlası"},
    "tuğla_delikli":    {"weight": 14.0, "unit": "volumetric", "name": "Düşey Delikli Tuğla"},
    "tuğla_hafif":      {"weight": 10.0, "unit": "volumetric", "name": "Hafif Tuğla"},
    "taş_doğal":        {"weight": 25.0, "unit": "volumetric", "name": "Doğal Taş (Genel)"},
    "kireçtaşı":        {"weight": 22.0, "unit": "volumetric", "name": "Kireçtaşı / Kalker"},
    "kalker":           {"weight": 24.0, "unit": "volumetric", "name": "Kalker"},
    "bazalt":           {"weight": 29.0, "unit": "volumetric", "name": "Bazalt"},
    "granit":           {"weight": 28.0, "unit": "volumetric", "name": "Granit"},
    "mermer":           {"weight": 27.0, "unit": "volumetric", "name": "Mermer"},
    "traverten":        {"weight": 24.0, "unit": "volumetric", "name": "Traverten"},
    "kumtaşı":          {"weight": 23.0, "unit": "volumetric", "name": "Kumtaşı"},
    "şap":              {"weight": 22.0, "unit": "volumetric", "name": "Şap"},
    "şap_anhidrit":     {"weight": 20.0, "unit": "volumetric", "name": "Anhidrit Şap"},
    "seramik":          {"weight": 22.0, "unit": "volumetric", "name": "Seramik"},
    "porselen":         {"weight": 24.0, "unit": "volumetric", "name": "Porselen"},
    "cam":              {"weight": 25.0, "unit": "volumetric", "name": "Cam"},
    "sıva":             {"weight": 20.0, "unit": "volumetric", "name": "Sıva (Genel)"},
    "sıva_kireç":       {"weight": 18.0, "unit": "volumetric", "name": "Kireç Harçlı Sıva"},
    "sıva_çimento":     {"weight": 22.0, "unit": "volumetric", "name": "Çimento Harçlı Sıva"},
    "sıva_alçı":        {"weight": 16.0, "unit": "volumetric", "name": "Alçı Sıva"},
    "dolgu_kum":        {"weight": 16.0, "unit": "volumetric", "name": "Kum Dolgu"},
    "dolgu_çakıl":      {"weight": 18.0, "unit": "volumetric", "name": "Çakıl Dolgu"},
    "parke_masif":      {"weight": 8.0,  "unit": "volumetric", "name": "Masif Parke"},
    "parke_laminat":    {"weight": 6.0,  "unit": "volumetric", "name": "Laminat Parke"},

    # --- KAPLAMA & YÜZEY YÜKLERİ (Alansal: kN/m²) ---
    "çatı_kiremidi":        {"weight": 0.5,  "unit": "area", "name": "Kiremit Çatı Kaplaması"},
    "çatı_sac":             {"weight": 0.15, "unit": "area", "name": "Trapez Sac Kaplama"},
    "çatı_izolasyon":       {"weight": 0.1,  "unit": "area", "name": "Çatı Isı Yalıtımı"},
    "çatı_su_yalıtımı":     {"weight": 0.05, "unit": "area", "name": "Çatı Su Yalıtımı"},
    "çatı_güneş_paneli":    {"weight": 0.15, "unit": "area", "name": "Güneş Paneli"},
    "asma_tavan":           {"weight": 0.3,  "unit": "area", "name": "Standart Asma Tavan"},
    "asma_tavan_ahşap":     {"weight": 0.25, "unit": "area", "name": "Ahşap Asma Tavan"},
    "asma_tavan_alüminyum": {"weight": 0.2,  "unit": "area", "name": "Alüminyum Asma Tavan"},
    "halı":                 {"weight": 0.15, "unit": "area", "name": "Halı Kaplama"},
    "halı_yün":             {"weight": 0.2,  "unit": "area", "name": "Yün Halı"},
    "linolyum":             {"weight": 0.1,  "unit": "area", "name": "Linolyum"},
    "vinil":                {"weight": 0.1,  "unit": "area", "name": "Vinil Kaplama"},
    "hafif_bölme":          {"weight": 0.5,  "unit": "area", "name": "Hafif Bölme Duvar"},
    "agir_bölme":           {"weight": 2.0,  "unit": "area", "name": "Ağır Bölme Duvar"},
    "bölme_alçıpan":        {"weight": 0.3,  "unit": "area", "name": "Alçıpan Bölme"},
    "bölme_cam":            {"weight": 0.5,  "unit": "area", "name": "Cam Bölme"},
    "kar_tutucu":           {"weight": 0.1,  "unit": "area", "name": "Kar Tutucu Sistem"},
    "su_yalıtımı_membran":  {"weight": 0.04, "unit": "area", "name": "Bitümlü Membran"},
    "su_yalıtımı":          {"weight": 0.05, "unit": "area", "name": "Su Yalıtımı"},
    "izolasyon_eps":        {"weight": 0.3,  "unit": "area", "name": "EPS Isı Yalıtımı"},
    "izolasyon_xps":        {"weight": 0.4,  "unit": "area", "name": "XPS Isı Yalıtımı"},
    "izolasyon_taş":        {"weight": 0.3,  "unit": "area", "name": "Taş Yünü Yalıtım"},
    "cephe_taş":            {"weight": 1.2,  "unit": "area", "name": "Mekanik Askılı Taş Cephe"},
    "cephe_mermer":         {"weight": 1.0,  "unit": "area", "name": "Mermer Cephe"},
    "cephe_kompozit":       {"weight": 0.4,  "unit": "area", "name": "Alüminyum Kompozit Cephe"},
    "cephe_cam":            {"weight": 0.8,  "unit": "area", "name": "Giydirme Cam Cephe"},
    "cephe_ahşap":          {"weight": 0.3,  "unit": "area", "name": "Ahşap Cephe"},
    "cephe_metal":          {"weight": 0.5,  "unit": "area", "name": "Metal Cephe"},
    "cephe_tuğla":          {"weight": 0.8,  "unit": "area", "name": "Tuğla Cephe"},
    "cephe_sıva":           {"weight": 0.4,  "unit": "area", "name": "Sıvalı Cephe"},
    "cephe_seramik":        {"weight": 0.6,  "unit": "area", "name": "Seramik Cephe"},
}


# ============================================================================
# 2. GERİYE UYUMLULUK: MATERIAL_WEIGHTS
# ============================================================================
# Eski kodlar `MATERIAL_WEIGHTS[malzeme]` çağırıyordu; ağırlık döner.
# Otomatik türetiyoruz, böylece LoadComponent.calculate() bozulmaz.

MATERIAL_WEIGHTS = {
    key: mat["weight"]
    for key, mat in MATERIAL_LIBRARY.items()
}


# ============================================================================
# 3. YARDIMCI FONKSİYONLAR (Yeni API)
# ============================================================================

def get_material_info(key: str) -> dict:
    """Malzemenin tam bilgisini döner."""
    if key not in MATERIAL_LIBRARY:
        raise KeyError(f"Tanımsız malzeme: {key}")
    return MATERIAL_LIBRARY[key]


def get_material_unit(key: str) -> str:
    """'volumetric' veya 'area'."""
    return get_material_info(key)["unit"]


def get_material_display_name(key: str) -> str:
    """Kullanıcıya gösterilecek isim."""
    return get_material_info(key)["name"]


def is_volumetric(key: str) -> bool:
    return get_material_unit(key) == "volumetric"


def is_area_load(key: str) -> bool:
    return get_material_unit(key) == "area"


# ============================================================================
# 4. HAREKETLİ YÜKLER (TS 498) - DEĞİŞMEDİ
# ============================================================================

LIVE_LOADS = {
    "kullanici_tanimli": {"name": "Kullanıcı Tanımlı", "value": 1.961},
    "konut": {"name": "Konut, teras, oda ve koridorlar", "value": 1.961},
    "konut_dukkan": {"name": "Konutlarda 50 m²'ye kadar dükkanlar / hastane odaları", "value": 1.961},
    "hastane": {"name": "Hastane mutfakları, muayene ve poliklinik odaları", "value": 3.432},
    "sinif": {"name": "Sınıflar, amfiler, yatakhaneler", "value": 3.432},
    "konut_merdiveni": {"name": "Konut merdivenleri", "value": 3.432},
    "cami": {"name": "Camiler", "value": 4.903},
    "tiyatro_sinema": {"name": "Tiyatrolar ve sinemalar", "value": 4.903},
    "magaza": {"name": "Mağazalar", "value": 4.903},
    "toplanti": {"name": "Toplantı ve bekleme salonları", "value": 4.903},
    "spor_sergi": {"name": "Spor, dans ve sergi salonları", "value": 4.903},
    "tribun_sabit": {"name": "Tribünler, sabit oturma", "value": 4.903},
    "lokanta": {"name": "Lokantalar", "value": 4.903},
    "kutuphane": {"name": "Kütüphaneler", "value": 4.903},
    "arsiv": {"name": "Arşivler", "value": 4.903},
    "hafif_atolye": {"name": "Hafif ağırlıklı atölyeler", "value": 4.903},
    "buyuk_mutfak": {"name": "Büyük mutfaklar, kantinler", "value": 4.903},
    "merdiven_umumi": {"name": "Umumi yapılarda merdivenler", "value": 4.903},
    "tribun_hareketli": {"name": "Tribünler, sabit olmayan oturma", "value": 7.355},
    "garaj": {"name": "Garajlar, toplam ağırlığı 2.5 tona kadar araçlar", "value": 4.903},
}