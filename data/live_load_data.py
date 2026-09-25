"""
Hareketli Yük Verileri - TS 498 / TS EN 1991-1-1

Kaynak: TS 498 Yapı Elemanlarının Boyutlandırılmasında Alınacak Yüklerin Hesap Değerleri
TS EN 1991-1-1 Yapılar Üzerindeki Etkiler - Bölüm 1-1: Genel Etkiler
"""

from typing import Dict, List

# ============================================================================
# 1. TS 498'E GÖRE HAREKETLİ YÜKLER (kN/m²)
# ============================================================================

LIVE_LOADS = {
    # KONUT VE BENZERİ
    "konut": 2.0,
    "apartman": 2.0,
    "villa": 2.0,
    "yazlik": 2.0,
    "öğrenci_yurdu_oda": 2.0,
    "öğrenci_yurdu_koridor": 3.0,
    "huzurevi": 2.0,
    "çocuk_yuvası": 2.0,
    "kres": 2.0,
    
    # OFIS VE İŞ YERLERİ
    "ofis_genel": 3.0,
    "ofis_özel": 3.0,
    "ofis_bölüm": 3.0,
    "ofis_arşiv": 4.0,
    "banka": 4.0,
    "sigorta": 3.0,
    "danışmanlık": 3.0,
    "muhasebe": 3.0,
    "avukat": 3.0,
    "mimarlık": 3.0,
    "mühendislik": 3.0,
    
    # OKULLAR
    "okul_sınıf": 3.0,
    "okul_koridor": 4.0,
    "okul_merdiven": 5.0,
    "okul_konferans": 4.0,
    "okul_kütüphane": 3.0,
    "okul_yemekhane": 4.0,
    "okul_spor": 4.0,
    "okul_laboratuvar": 4.0,
    "okul_atölye": 5.0,
    "okul_bahçe": 4.0,
    "üniversite_sınıf": 3.0,
    "üniversite_amfi": 4.0,
    "üniversite_koridor": 5.0,
    "üniversite_kütüphane": 4.0,
    "üniversite_laboratuvar": 5.0,
    "üniversite_atölye": 5.0,
    
    # TİCARET
    "mağaza": 5.0,
    "butik": 4.0,
    "market": 5.0,
    "süpermarket": 7.0,
    "hipermarket": 7.0,
    "alışveriş_merkezi": 5.0,
    "avm_koridor": 4.0,
    "avm_restoran": 5.0,
    "avm_sinema": 5.0,
    "avm_oyun": 5.0,
    "avm_eczane": 4.0,
    "avm_kuaför": 4.0,
    "avm_terzi": 4.0,
    "avm_kuru_temizleme": 5.0,
    "avm_oto_yıkama": 5.0,
    
    # RESTORAN VE KAFE
    "restoran": 5.0,
    "kafe": 5.0,
    "bar": 5.0,
    "gece_kulübü": 5.0,
    "fast_food": 5.0,
    "pastane": 5.0,
    "fırın": 5.0,
    "lokanta": 5.0,
    "kebapçı": 5.0,
    "pizza": 5.0,
    
    # OTELLER
    "otel_oda": 2.0,
    "otel_koridor": 3.0,
    "otel_restoran": 5.0,
    "otel_toplu": 5.0,
    "otel_konferans": 5.0,
    "otel_spor": 4.0,
    "otel_yüzme": 4.0,
    "otel_sauna": 4.0,
    "otel_cilt": 4.0,
    "otel_kapalı_otopark": 3.0,
    
    # SAĞLIK
    "hastane_oda": 2.0,
    "hastane_koridor": 4.0,
    "hastane_amfi": 4.0,
    "hastane_laboratuvar": 4.0,
    "hastane_ameliyat": 4.0,
    "hastane_muayene": 3.0,
    "hastane_acil": 4.0,
    "hastane_yoğun": 4.0,
    "hastane_doğum": 3.0,
    "hastane_çocuk": 3.0,
    "poliklinik_muayene": 3.0,
    "poliklinik_bekleme": 4.0,
    "poliklinik_koridor": 4.0,
    "diş_kliniği": 3.0,
    "fizik_tedavi": 4.0,
    "rehabilitasyon": 3.0,
    
    # SPOR VE KÜLTÜR
    "spor_salonu": 5.0,
    "spor_vestiyer": 4.0,
    "spor_tribün": 5.0,
    "spor_kapalı": 5.0,
    "spor_açık": 4.0,
    "spor_basketbol": 5.0,
    "spor_voleybol": 5.0,
    "spor_tenis": 5.0,
    "spor_yüzme": 4.0,
    "spor_fitness": 5.0,
    "spor_yoga": 4.0,
    "spor_pilates": 4.0,
    "spor_boks": 5.0,
    "spor_karate": 5.0,
    "tiyatro": 5.0,
    "sinema": 5.0,
    "konser": 5.0,
    "konferans": 5.0,
    "sergi": 5.0,
    "kongre": 5.0,
    "toplantı": 5.0,
    "nikah": 5.0,
    "düğün": 5.0,
    "kongre_merkezi": 5.0,
    "fuay": 5.0,
    
    # DEPO VE ENDÜSTRİ
    "depo_hafif": 5.0,
    "depo_orta": 7.0,
    "depo_agir": 10.0,
    "depo_raf": 7.0,
    "depo_otomasyon": 7.0,
    "depo_soğuk": 7.0,
    "depo_yeraltı": 7.0,
    "depo_tehlike": 7.0,
    "endüstriyel_hafif": 5.0,
    "endüstriyel_orta": 7.0,
    "endüstriyel_agir": 10.0,
    "endüstriyel_çok_agir": 15.0,
    "fabrika": 7.0,
    "atölye": 5.0,
    "imalat": 7.0,
    "montaj": 7.0,
    "boyahane": 5.0,
    "kaynak": 7.0,
    "makin": 7.0,
    
    # OTOPARK
    "otopark_hafif": 3.0,
    "otopark_orta": 4.0,
    "otopark_agir": 5.0,
    "otopark_yeraltı": 4.0,
    "otopark_açık": 3.0,
    "otopark_kapalı": 4.0,
    "otopark_katlı": 4.0,
    "otopark_otomobil": 3.0,
    "otopark_kamyonet": 5.0,
    "otopark_kamyon": 7.0,
    "otopark_otobüs": 7.0,
    
    # KORİDOR VE MERDİVEN
    "koridor": 4.0,
    "merdiven": 5.0,
    "giriş_hol": 4.0,
    "fuaye": 5.0,
    "bekleme": 4.0,
    "geçit": 5.0,
    "tünel": 5.0,
    "köprü": 5.0,
    "geçiş": 5.0,
    "yürüme_yolu": 4.0,
    "rampa": 5.0,
    
    # ÇATILAR
    "çatı_erişilemez": 0.75,
    "çatı_erişilebilir": 2.0,
    "çatı_teras": 2.0,
    "çatı_bahçe": 3.0,
    "çatı_restoran": 5.0,
    "çatı_kafe": 5.0,
    "çatı_havuz": 4.0,
    "çatı_spor": 5.0,
    "çatı_güneş": 1.0,
    "çatı_ekipman": 2.0,
    "çatı_bakım": 0.75,
    
    # ÖZEL YAPILAR
    "tribün_ayakta": 4.0,
    "tribün_oturan": 3.0,
    "tribün_kapalı": 5.0,
    "tribün_açık": 4.0,
    "ibadet": 4.0,
    "cami": 4.0,
    "kilise": 4.0,
    "havra": 4.0,
    "müze": 4.0,
    "kütüphane": 4.0,
    "arşiv": 5.0,
    "laboratuvar": 5.0,
    "bilgisayar_oda": 4.0,
    "sunucu_oda": 5.0,
    "kontrol_oda": 4.0,
    "güvenlik": 3.0,
}

# ============================================================================
# 2. YAPI KATEGORİLERİNE GÖRE YÜKLER
# ============================================================================

STRUCTURE_CATEGORIES = {
    "konut": ["konut", "apartman", "villa", "yazlik", "öğrenci_yurdu_oda"],
    "ofis": ["ofis_genel", "ofis_özel", "ofis_bölüm", "ofis_arşiv", "banka", 
             "sigorta", "danışmanlık", "muhasebe", "avukat", "mimarlık", "mühendislik"],
    "okul": ["okul_sınıf", "okul_koridor", "okul_merdiven", "okul_konferans", 
             "okul_kütüphane", "okul_yemekhane", "okul_spor", "okul_laboratuvar", 
             "okul_atölye", "okul_bahçe", "üniversite_sınıf", "üniversite_amfi", 
             "üniversite_koridor", "üniversite_kütüphane", "üniversite_laboratuvar", 
             "üniversite_atölye"],
    "ticaret": ["mağaza", "butik", "market", "süpermarket", "hipermarket", 
                "alışveriş_merkezi", "avm_koridor", "avm_restoran", "avm_sinema", 
                "avm_oyun", "avm_eczane", "avm_kuaför", "avm_terzi", 
                "avm_kuru_temizleme", "avm_oto_yıkama"],
    "restoran": ["restoran", "kafe", "bar", "gece_kulübü", "fast_food", 
                 "pastane", "fırın", "lokanta", "kebapçı", "pizza"],
    "otel": ["otel_oda", "otel_koridor", "otel_restoran", "otel_toplu", 
             "otel_konferans", "otel_spor", "otel_yüzme", "otel_sauna", 
             "otel_cilt", "otel_kapalı_otopark"],
    "saglik": ["hastane_oda", "hastane_koridor", "hastane_amfi", "hastane_laboratuvar", 
               "hastane_ameliyat", "hastane_muayene", "hastane_acil", "hastane_yoğun", 
               "hastane_doğum", "hastane_çocuk", "poliklinik_muayene", 
               "poliklinik_bekleme", "poliklinik_koridor", "diş_kliniği", 
               "fizik_tedavi", "rehabilitasyon"],
    "spor_kultur": ["spor_salonu", "spor_vestiyer", "spor_tribün", "spor_kapalı", 
                    "spor_açık", "spor_basketbol", "spor_voleybol", "spor_tenis", 
                    "spor_yüzme", "spor_fitness", "spor_yoga", "spor_pilates", 
                    "spor_boks", "spor_karate", "tiyatro", "sinema", "konser", 
                    "konferans", "sergi", "kongre", "toplantı", "nikah", "düğün", 
                    "kongre_merkezi", "fuay"],
    "depo_endustri": ["depo_hafif", "depo_orta", "depo_agir", "depo_raf", 
                      "depo_otomasyon", "depo_soğuk", "depo_yeraltı", "depo_tehlike", 
                      "endüstriyel_hafif", "endüstriyel_orta", "endüstriyel_agir", 
                      "endüstriyel_çok_agir", "fabrika", "atölye", "imalat", 
                      "montaj", "boyahane", "kaynak", "makin"],
    "otopark": ["otopark_hafif", "otopark_orta", "otopark_agir", "otopark_yeraltı", 
                "otopark_açık", "otopark_kapalı", "otopark_katlı", "otopark_otomobil", 
                "otopark_kamyonet", "otopark_kamyon", "otopark_otobüs"],
    "koridor_merdiven": ["koridor", "merdiven", "giriş_hol", "fuaye", "bekleme", 
                         "geçit", "tünel", "köprü", "geçiş", "yürüme_yolu", "rampa"],
    "cati": ["çatı_erişilemez", "çatı_erişilebilir", "çatı_teras", "çatı_bahçe", 
             "çatı_restoran", "çatı_kafe", "çatı_havuz", "çatı_spor", "çatı_güneş", 
             "çatı_ekipman", "çatı_bakım"],
    "ozel": ["tribün_ayakta", "tribün_oturan", "tribün_kapalı", "tribün_açık", 
             "ibadet", "cami", "kilise", "havra", "müze", "kütüphane", "arşiv", 
             "laboratuvar", "bilgisayar_oda", "sunucu_oda", "kontrol_oda", "güvenlik"]
}

# ============================================================================
# 3. YAPI TİPİ AÇIKLAMALARI
# ============================================================================

STRUCTURE_DESCRIPTIONS = {
    "konut": "Konut ve apartman daireleri",
    "apartman": "Apartman daireleri",
    "villa": "Villa tipi konut",
    "yazlik": "Yazlık konut",
    "öğrenci_yurdu_oda": "Öğrenci yurdu odaları",
    "öğrenci_yurdu_koridor": "Öğrenci yurdu koridorları",
    "huzurevi": "Huzurevi odaları",
    "çocuk_yuvası": "Çocuk yuvası",
    "kres": "Kreş",
    "ofis_genel": "Genel ofis alanları",
    "ofis_özel": "Özel ofis odaları",
    "ofis_bölüm": "Bölüm ofisleri",
    "ofis_arşiv": "Ofis arşiv odaları",
    "banka": "Banka şubeleri",
    "sigorta": "Sigorta ofisleri",
    "danışmanlık": "Danışmanlık ofisleri",
    "muhasebe": "Muhasebe ofisleri",
    "avukat": "Avukat ofisleri",
    "mimarlık": "Mimarlık ofisleri",
    "mühendislik": "Mühendislik ofisleri",
    "okul_sınıf": "Okul sınıfları",
    "okul_koridor": "Okul koridorları",
    "okul_merdiven": "Okul merdivenleri",
    "okul_konferans": "Okul konferans salonları",
    "okul_kütüphane": "Okul kütüphaneleri",
    "okul_yemekhane": "Okul yemekhaneleri",
    "okul_spor": "Okul spor salonları",
    "okul_laboratuvar": "Okul laboratuvarları",
    "okul_atölye": "Okul atölyeleri",
    "okul_bahçe": "Okul bahçeleri",
    "üniversite_sınıf": "Üniversite sınıfları",
    "üniversite_amfi": "Üniversite amfi salonları",
    "üniversite_koridor": "Üniversite koridorları",
    "üniversite_kütüphane": "Üniversite kütüphaneleri",
    "üniversite_laboratuvar": "Üniversite laboratuvarları",
    "üniversite_atölye": "Üniversite atölyeleri",
    "mağaza": "Mağazalar",
    "butik": "Butik mağazalar",
    "market": "Marketler",
    "süpermarket": "Süpermarketler",
    "hipermarket": "Hipermarketler",
    "alışveriş_merkezi": "Alışveriş merkezleri",
    "avm_koridor": "AVM koridorları",
    "avm_restoran": "AVM restoranları",
    "avm_sinema": "AVM sinema salonları",
    "avm_oyun": "AVM oyun alanları",
    "avm_eczane": "AVM eczaneleri",
    "avm_kuaför": "AVM kuaförleri",
    "avm_terzi": "AVM terzileri",
    "avm_kuru_temizleme": "AVM kuru temizlemeleri",
    "avm_oto_yıkama": "AVM oto yıkamaları",
    "restoran": "Restoranlar",
    "kafe": "Kafeler",
    "bar": "Barlar",
    "gece_kulübü": "Gece kulüpleri",
    "fast_food": "Fast food restoranları",
    "pastane": "Pastaneler",
    "fırın": "Fırınlar",
    "lokanta": "Lokantalar",
    "kebapçı": "Kebapçılar",
    "pizza": "Pizza restoranları",
    "otel_oda": "Otel odaları",
    "otel_koridor": "Otel koridorları",
    "otel_restoran": "Otel restoranları",
    "otel_toplu": "Otel toplantı salonları",
    "otel_konferans": "Otel konferans salonları",
    "otel_spor": "Otel spor salonları",
    "otel_yüzme": "Otel yüzme havuzları",
    "otel_sauna": "Otel saunaları",
    "otel_cilt": "Otel cilt bakım merkezleri",
    "otel_kapalı_otopark": "Otel kapalı otoparkları",
    "hastane_oda": "Hastane odaları",
    "hastane_koridor": "Hastane koridorları",
    "hastane_amfi": "Hastane amfi salonları",
    "hastane_laboratuvar": "Hastane laboratuvarları",
    "hastane_ameliyat": "Hastane ameliyathaneleri",
    "hastane_muayene": "Hastane muayene odaları",
    "hastane_acil": "Hastane acil servisleri",
    "hastane_yoğun": "Hastane yoğun bakımları",
    "hastane_doğum": "Hastane doğum salonları",
    "hastane_çocuk": "Hastane çocuk servisleri",
    "poliklinik_muayene": "Poliklinik muayene odaları",
    "poliklinik_bekleme": "Poliklinik bekleme salonları",
    "poliklinik_koridor": "Poliklinik koridorları",
    "diş_kliniği": "Diş klinikleri",
    "fizik_tedavi": "Fizik tedavi merkezleri",
    "rehabilitasyon": "Rehabilitasyon merkezleri",
    "spor_salonu": "Spor salonları",
    "spor_vestiyer": "Spor vestiyerleri",
    "spor_tribün": "Spor tribünleri",
    "spor_kapalı": "Kapalı spor alanları",
    "spor_açık": "Açık spor alanları",
    "spor_basketbol": "Basketbol sahaları",
    "spor_voleybol": "Voleybol sahaları",
    "spor_tenis": "Tenis kortları",
    "spor_yüzme": "Yüzme havuzları",
    "spor_fitness": "Fitness salonları",
    "spor_yoga": "Yoga stüdyoları",
    "spor_pilates": "Pilates stüdyoları",
    "spor_boks": "Boks salonları",
    "spor_karate": "Karate salonları",
    "tiyatro": "Tiyatro salonları",
    "sinema": "Sinema salonları",
    "konser": "Konser salonları",
    "konferans": "Konferans salonları",
    "sergi": "Sergi salonları",
    "kongre": "Kongre merkezleri",
    "toplantı": "Toplantı salonları",
    "nikah": "Nikah salonları",
    "düğün": "Düğün salonları",
    "kongre_merkezi": "Kongre merkezleri",
    "fuay": "Fuaye alanları",
    "depo_hafif": "Hafif depo alanları",
    "depo_orta": "Orta depo alanları",
    "depo_agir": "Ağır depo alanları",
    "depo_raf": "Raflı depo alanları",
    "depo_otomasyon": "Otomasyon depo alanları",
    "depo_soğuk": "Soğuk hava depoları",
    "depo_yeraltı": "Yeraltı depoları",
    "depo_tehlike": "Tehlikeli madde depoları",
    "endüstriyel_hafif": "Hafif endüstriyel alanlar",
    "endüstriyel_orta": "Orta endüstriyel alanlar",
    "endüstriyel_agir": "Ağır endüstriyel alanlar",
    "endüstriyel_çok_agir": "Çok ağır endüstriyel alanlar",
    "fabrika": "Fabrika alanları",
    "atölye": "Atölye alanları",
    "imalat": "İmalat alanları",
    "montaj": "Montaj alanları",
    "boyahane": "Boyahane alanları",
    "kaynak": "Kaynak atölyeleri",
    "makin": "Makine daireleri",
    "otopark_hafif": "Hafif araç otoparkları",
    "otopark_orta": "Orta araç otoparkları",
    "otopark_agir": "Ağır araç otoparkları",
    "otopark_yeraltı": "Yeraltı otoparkları",
    "otopark_açık": "Açık otoparklar",
    "otopark_kapalı": "Kapalı otoparklar",
    "otopark_katlı": "Katlı otoparklar",
    "otopark_otomobil": "Otomobil otoparkları",
    "otopark_kamyonet": "Kamyonet otoparkları",
    "otopark_kamyon": "Kamyon otoparkları",
    "otopark_otobüs": "Otobüs otoparkları",
    "koridor": "Koridorlar",
    "merdiven": "Merdivenler",
    "giriş_hol": "Giriş hol ve lobiler",
    "fuaye": "Fuayeler",
    "bekleme": "Bekleme salonları",
    "geçit": "Geçit ve köprüler",
    "tünel": "Tüneller",
    "köprü": "Köprüler",
    "geçiş": "Geçiş yolları",
    "yürüme_yolu": "Yürüme yolları",
    "rampa": "Rampalar",
    "çatı_erişilemez": "Erişilemeyen çatılar",
    "çatı_erişilebilir": "Erişilebilir çatılar",
    "çatı_teras": "Teras çatılar",
    "çatı_bahçe": "Yeşil çatılar",
    "çatı_restoran": "Restoran çatılar",
    "çatı_kafe": "Kafe çatılar",
    "çatı_havuz": "Havuz çatılar",
    "çatı_spor": "Spor çatılar",
    "çatı_güneş": "Güneş paneli çatılar",
    "çatı_ekipman": "Ekipman çatılar",
    "çatı_bakım": "Bakım çatıları",
    "tribün_ayakta": "Ayakta tribünler",
    "tribün_oturan": "Oturan tribünler",
    "tribün_kapalı": "Kapalı tribünler",
    "tribün_açık": "Açık tribünler",
    "ibadet": "İbadet yerleri",
    "cami": "Camiler",
    "kilise": "Kiliseler",
    "havra": "Havralar",
    "müze": "Müzeler",
    "kütüphane": "Kütüphaneler",
    "arşiv": "Arşivler",
    "laboratuvar": "Laboratuvarlar",
    "bilgisayar_oda": "Bilgisayar odaları",
    "sunucu_oda": "Sunucu odaları",
    "kontrol_oda": "Kontrol odaları",
    "güvenlik": "Güvenlik odaları"
}

# ============================================================================
# 4. ÖZEL YÜK DURUMLARI (Azaltma Faktörleri vb.)
# ============================================================================

# TS 498 Madde 7.2 - Hareketli Yük Azaltma Faktörleri
REDUCTION_FACTORS = {
    "konut": 0.5,
    "apartman": 0.5,
    "villa": 0.5,
    "yazlik": 0.5,
    "ofis": 0.6,
    "okul_sınıf": 0.6,
    "okul_koridor": 0.7,
    "mağaza": 0.7,
    "market": 0.7,
    "depo": 0.8,
    "endüstriyel": 0.8,
    "otopark": 0.8,
    "cati": 0.7
}

# ============================================================================
# 5. YARDIMCI FONKSİYONLAR
# ============================================================================

def get_live_load(usage_type: str) -> float:
    """
    Kullanım tipine göre hareketli yükü döndürür
    
    Args:
        usage_type: Kullanım tipi
    
    Returns:
        Hareketli yük (kN/m²)
    """
    return LIVE_LOADS.get(usage_type, 2.0)

def get_reduction_factor(usage_type: str) -> float:
    """
    Kullanım tipine göre azaltma faktörünü döndürür
    
    Args:
        usage_type: Kullanım tipi
    
    Returns:
        Azaltma faktörü
    """
    for key, factor in REDUCTION_FACTORS.items():
        if key in usage_type:
            return factor
    return 0.5  # Varsayılan

def get_structure_categories() -> Dict[str, List[str]]:
    """
    Yapı kategorilerini döndürür
    
    Returns:
        Kategori bazında yapı tipleri sözlüğü
    """
    return STRUCTURE_CATEGORIES

def get_category_description(category: str) -> str:
    """
    Kategori açıklamasını döndürür
    
    Args:
        category: Kategori adı
    
    Returns:
        Kategori açıklaması
    """
    descriptions = {
        "konut": "Konut ve apartman daireleri",
        "ofis": "Ofis ve iş yerleri",
        "okul": "Okul ve üniversiteler",
        "ticaret": "Ticari alanlar",
        "restoran": "Restoran ve kafeler",
        "otel": "Oteller",
        "saglik": "Sağlık tesisleri",
        "spor_kultur": "Spor ve kültür merkezleri",
        "depo_endustri": "Depo ve endüstriyel alanlar",
        "otopark": "Otoparklar",
        "koridor_merdiven": "Koridor ve merdivenler",
        "cati": "Çatılar",
        "ozel": "Özel yapılar"
    }
    return descriptions.get(category, "Belirtilmemiş kategori")