# data/analysis_config.py
"""
Analiz Modülleri için Konfigürasyon Yükleyici

Kullanıcı, tek bir JSON dosyasında tüm analiz konfigürasyonunu
(wind_config, snow_config, earthquake_config) tanımlayabilir.

Örnek JSON:
{
  "wind_config":       { ... },
  "snow_config":       { ... },
  "earthquake_config": { ... },
  "points":            [ {...}, {...} ],
  "polygons":          [ {...} ]
}
"""

import json
import os
from typing import Any


DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__),
    "analysis_defaults.json"
)


# ----------------------------------------------------------------------
# Varsayılan değerler (yeni başlayanlar için)
# ----------------------------------------------------------------------

DEFAULT_WIND = {
    "wind_speed": 28.0,           # m/s
    "terrain_category": "II",
    "altitude": 0.0,
    "exposure_factor": 1.0,
    "direction": 0.0,
}

DEFAULT_SNOW = {
    "region": "II",
    "altitude": 500.0,
    "roof_type": "duz",
    "slope_angle": 0.0,
    "exposure": "normal",
    "thermal": "normal",
}

DEFAULT_EARTHQUAKE = {
    "a0": 0.30,                   # yer ivmesi (g)
    "S": 1.20,                    # zemin katsayısı
    "I": 1.00,                    # bina önem katsayısı
    "R": 4.00,                    # davranış katsayısı
    "T": 0.50,                    # hakim periyot (s)
    "soil_class": "ZC",
    "spectrum_points": [],
}


def get_default_config() -> dict:
    """Analiz sekmeleri için başlangıç konfigürasyonu."""
    return {
        "wind_config":       dict(DEFAULT_WIND),
        "snow_config":       dict(DEFAULT_SNOW),
        "earthquake_config": dict(DEFAULT_EARTHQUAKE),
        "points":            [],
        "polygons":          [],
    }


def load_config(path: str | None) -> dict:
    """JSON dosyasından config yükler. Eksik anahtarları varsayılanla doldurur."""
    base = get_default_config()
    if not path:
        return base

    with open(path, "r", encoding="utf-8") as f:
        user = json.load(f)

    for key in ("wind_config", "snow_config", "earthquake_config"):
        if key in user and isinstance(user[key], dict):
            base[key].update(user[key])

    for key in ("points", "polygons"):
        if key in user:
            base[key] = user[key]

    return base


def save_config(config: dict, path: str):
    """Config'i JSON'a yazar."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)