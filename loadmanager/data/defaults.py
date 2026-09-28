from data.material_data import MATERIAL_LIBRARY


proje_data = {
"proje_bilgileri": {
"proje_adi": "Endüstriyel Depo Yapısı",
"ada_parsel": "102 / 14",
"muhendis": "Engineer",
"tarih": "",
"revizyon": "R0",
},

"saha_ve_deprem": {
"zemin_sinifi": "ZD",
"ks_yatak_katsayisi_kN_m3": 15000,
},
"points": {"P1": [0.0, 0.0, 0.0], "P2": [12.0, 0.0, 0.0], "P3": [12.0, 8.0, 0.0], "P4": [0.0, 8.0, 0.0], "P5": [0.0, 0.0, 4.0], "P6": [12.0, 0.0, 4.0], "P7": [12.0, 8.0, 5.0], "P8": [0.0, 8.0, 5.0]},
"polygons": {"D1": ["P1", "P2", "P6", "P5"], "D2": ["P1", "P5", "P8", "P4"], "D3": ["P2", "P3", "P7", "P6"], "D4": ["P3", "P4", "P8", "P7"], "C1": ["P5", "P6", "P7", "P8"]},
"wind_config": {
"v_b0": 28.0,
"terrain": "Kategori II",
"rho": 1.25,
"ct": 1.0,
"kI": 1.0
},
"snow_config": {
"slope": 15.0,
"snow_region": 2,
"altitude": 50,
"Ce": 1.0,
"Ct": 1.0
},
"earthquake_config": {
"R": 2.5,
"D": 2.5,
"I": 1.2,
"kappa": 0.5,
"Hn": 10.1,
"gamma_E": 0.9,
"n": 0.3,
"e": "±0.05",
"ee": "Dbi= (η_bi/1.2)², Ek dış merkezlik= %5 + Dbi",
"zemin_sinifi": "ZC",
"limit_raw": 0.008,
"has_irregularity": True,
"dd2": {
"Ss": 0.329,
"S1": 0.128,
"PGA": 0.143,
"PGV": 10.653,
"Fs": 1.3,
"F1": 1.5,
"Sds": 0.428,
"Sd1": 0.192
},
"dd3": {
"Ss": 0.13,
"S1": 0.054,
"PGA": 0.058,
"PGV": 4.54,
"Fs": 1.3,
"F1": 1.5,
"Sds": 0.169,
"Sd1": 0.081
}
},

"malzemeler": {
"beton": "C30/37",
"donati": "B420C",
"yapisal_celik": "S355",
"ahsap": "C24",
"panel": "OSB/3",
},

"yukler": {
"olu_yukler_G": {
"cati_kaplamasi": {
"toplam_yuk": 0.45,
"birim": "kN/m²",
"details": [
{
"ad": "Kiremit Kaplama",
"malzeme_ref": MATERIAL_LIBRARY.get("kiremit"),
"thickness_m": 0.02,
"hesaplanan_yuk_kN_m2": 0.38,
},
{
"ad": "Isı Yalıtımı (Taşyünü)",
"malzeme_ref": MATERIAL_LIBRARY.get("tasyunu"),
"thickness_m": 0.10,
"hesaplanan_yuk_kN_m2": 0.05,
},
{
"ad": "OSB Alt Kaplama",
"malzeme_ref": MATERIAL_LIBRARY.get("osb_3"),
"thickness_m": 0.018,
"hesaplanan_yuk_kN_m2": 0.117,
},
],
},
"tesisat_ve_asma_tavan": {
"toplam_yuk": 0.15,
"birim": "kN/m²",
"details": [
{"ad": "Aydınlatma ve Kanal Tesisatı", "hesaplanan_yuk_kN_m2": 0.10},
{"ad": "Asma Tavan Profilleri", "hesaplanan_yuk_kN_m2": 0.05},
],
}
},

"hareketli_yukler_Q": {
"cati_bakim": {
"qk": 0.75,
"birim": "kN/m²",
"psi_2_katilim_katsayisi": 0.3,
"description": "TS EN 1991-1-1 Ulaşılamayan çatı yükü (Kategori H)",
}
},



"load_cases":{
"dead_load_cases": [],
"dead_load_combs": [],
"live_load_cases": [],
"live_load_combs": [],
"wind_load_cases": [],
"wind_load_combs": [],
"snow_load_cases": [],
"snow_load_combs": [],

"seismic_load_cases": [
"EQX",
"EQY",
"QUAKEX",
"QUAKEY"
],
"drift_combo_names": [
"EXP",
"EXM",
"EYP",
"EYM"
]
               
}
}
}
