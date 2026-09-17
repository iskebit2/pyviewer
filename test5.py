# ============================================================================
# 1. SABİTLER & VERİ
# ============================================================================

ARAZI_KATEGORILERI = {
    "Kategori 0": {
        "Arazi kategorisi": "Açık deniz etkisine maruz deniz veya kıyı alanı",
        "z0": 0.003,
        "zmin": 1.0
    },
    "Kategori I": {
        "Arazi kategorisi": "Göl, düz ve açık arazi: Göller veya ihmal edilebilecek seviyede bitki örtüsü olan ve engebeli olmayan düz ve yatay alan",
        "z0": 0.01,
        "zmin": 1.0
    },
    "Kategori II": {
        "Arazi kategorisi": "Bitki örtüsü ve/veya binalarla kaplı arazi: Çayır gibi az seviyede bitki örtüsü olan ve aralarında en az engel yüksekliğinin 20 katı kadar mesafe bulunan engellere (ağaçlar, binalar) sahip alan",
        "z0": 0.05,
        "zmin": 2.0
    },
    "Kategori III": {
        "Arazi kategorisi": "Orman, sanayi veya kentsel bölge: Düzgün yayılı şekilde bir bitki örtüsüne veya binalara veya aralarında en az engel yüksekliğinin 20 katı kadar mesafe bulunan engellere sahip alan (kasabalar, yörekent, ormanlık alan gibi",
        "z0": 0.3,
        "zmin": 5.0
    },
    "Kategori IV": {
        "Arazi kategorisi": "Yoğun şehir merkezi: Yüzeyinin en az % 15’i, yükseklik ortalaması 15 m’yi aşan binalarla kaplı alan",
        "z0": 1.0,
        "zmin": 10.0
    }
}

WALL_CPE_TABLE={
0: {
'cpe10':{
    5.0: {'A': -1.2, 'B': -0.8, 'C': -0.5, 'D': 0.8, 'E': -0.7},
    1.0: {'A': -1.2, 'B': -0.8, 'C': -0.5, 'D': 0.8, 'E': -0.5},
    0.25: {'A': -1.2, 'B': -0.8, 'C': -0.5, 'D': 0.7, 'E': -0.3}
        },
'cpe1': {
    5.0: {'A': -1.4, 'B': -1.1, 'C': -0.5, 'D': 1.0, 'E': -0.7},
    1.0: {'A': -1.4, 'B': -1.1, 'C': -0.5, 'D': 1.0, 'E': -0.5},
    0.25: {'A': -1.4, 'B': -1.1, 'C': -0.5, 'D': 1.0, 'E': -0.3}
}}}

MONOPITCH_CPE_DATA= {
0: {
'cpe10': {
5:  {'F': [-1.7, 0.0], 'G': [-1.2, 0.0], 'H': [-0.6, 0.0]},
10: {'F': [-0.9, 0.2], 'G': [-0.8, 0.2], 'H': [-0.3, 0.2]},
30: {'F': [-0.5, 0.7], 'G': [-0.5, 0.7], 'H': [-0.2, 0.4]},
45: {'F': [0.0, 0.7],  'G': [0.0, 0.7],  'H': [0.0, 0.6]},
60: {'F': [0.0, 0.7],  'G': [0.0, 0.7],  'H': [0.0, 0.7]},
75: {'F': [0.0, 0.8],  'G': [0.0, 0.8],  'H': [0.0, 0.8]}
},
'cpe1': {
5:  {'F': [-2.5, 0.0], 'G': [-2.0, 0.0], 'H': [-1.2, 0.0]},
10: {'F': [-2.0, 0.2], 'G': [-1.5, 0.2], 'H': [-0.3, 0.2]},
30: {'F': [-1.5, 0.7], 'G': [-1.5, 0.7], 'H': [-0.2, 0.4]},
45: {'F': [0.0, 0.7],  'G': [0.0, 0.7],  'H': [0.0, 0.6]},
60: {'F': [0.0, 0.7],  'G': [0.0, 0.7],  'H': [0.0, 0.7]},
75: {'F': [0.0, 0.8],  'G': [0.0, 0.8],  'H': [0.0, 0.8]}
}
},
180: {
'cpe10': {
5:  {'F': [-2.3, 0.0], 'G': [-1.3, 0.0], 'H': [-0.8, 0.0]},
10: {'F': [-2.5, 0.0], 'G': [-1.3, 0.0], 'H': [-0.9, 0.0]},
30: {'F': [-1.1, 0.0], 'G': [-0.8, 0.0], 'H': [-0.8, 0.0]},
45: {'F': [-0.6, 0.0], 'G': [-0.5, 0.0], 'H': [-0.7, 0.0]},
60: {'F': [-0.5, 0.0], 'G': [-0.5, 0.0], 'H': [-0.5, 0.0]},
75: {'F': [-0.5, 0.0], 'G': [-0.5, 0.0], 'H': [-0.5, 0.0]}
},
'cpe1': {
5:  {'F': [-2.5, 0.0], 'G': [-2.0, 0.0], 'H': [-1.2, 0.0]},
10: {'F': [-2.8, 0.0], 'G': [-2.0, 0.0], 'H': [-1.2, 0.0]},
30: {'F': [-2.3, 0.0], 'G': [-1.5, 0.0], 'H': [-0.8, 0.0]},
45: {'F': [-1.3, 0.0], 'G': [-0.5, 0.0], 'H': [-0.7, 0.0]},
60: {'F': [-1.0, 0.0], 'G': [-0.5, 0.0], 'H': [-0.5, 0.0]},
75: {'F': [-1.0, 0.0], 'G': [-0.5, 0.0], 'H': [-0.5, 0.0]}
}
},
90: {
'cpe10': {
5:  {'Fu': [-2.1, 0.0], 'Fl': [-2.1, 0.0], 'G': [-1.8, 0.0], 'H': [-0.6, 0.0], 'I': [-0.5, 0.0]},
15: {'Fu': [-2.4, 0.0], 'Fl': [-1.6, 0.0], 'G': [-1.9, 0.0], 'H': [-0.8, 0.0], 'I': [-0.7, 0.0]},
30: {'Fu': [-2.1, 0.0], 'Fl': [-1.3, 0.0], 'G': [-1.5, 0.0], 'H': [-1.0, 0.0], 'I': [-0.8, 0.0]},
45: {'Fu': [-1.5, 0.0], 'Fl': [-1.3, 0.0], 'G': [-1.4, 0.0], 'H': [-1.0, 0.0], 'I': [-0.9, 0.0]},
60: {'Fu': [-1.2, 0.0], 'Fl': [-1.2, 0.0], 'G': [-1.2, 0.0], 'H': [-1.0, 0.0], 'I': [-0.7, 0.0]},
75: {'Fu': [-1.2, 0.0], 'Fl': [-1.2, 0.0], 'G': [-1.2, 0.0], 'H': [-1.0, 0.0], 'I': [-0.5, 0.0]}
},
'cpe1': {
5:  {'Fu': [-2.6, 0.0], 'Fl': [-2.1, 0.0], 'G': [-2.0, 0.0], 'H': [-1.2, 0.0], 'I': [-0.5, 0.0]},
15: {'Fu': [-2.9, 0.0], 'Fl': [-1.6, 0.0], 'G': [-2.5, 0.0], 'H': [-1.2, 0.0], 'I': [-1.2, 0.0]},
30: {'Fu': [-2.9, 0.0], 'Fl': [-1.3, 0.0], 'G': [-2.0, 0.0], 'H': [-1.3, 0.0], 'I': [-1.2, 0.0]},
45: {'Fu': [-2.4, 0.0], 'Fl': [-1.3, 0.0], 'G': [-2.0, 0.0], 'H': [-1.3, 0.0], 'I': [-1.2, 0.0]},
60: {'Fu': [-2.0, 0.0], 'Fl': [-1.2, 0.0], 'G': [-2.0, 0.0], 'H': [-1.3, 0.0], 'I': [-1.2, 0.0]},
75: {'Fu': [-2.0, 0.0], 'Fl': [-1.2, 0.0], 'G': [-2.0, 0.0], 'H': [-1.3, 0.0], 'I': [-0.5, 0.0]}
}
}
}

DUOPITCH_CPE_DATA= {
0: {
'cpe10': {
-45: {'F': [-0.6, 0], 'G': [-0.6, 0], 'H': [-0.8, 0], 'I': [-0.7, 0], 'J': [-1.0, 0]},
-30: {'F': [-1.1, 0], 'G': [-0.8, 0], 'H': [-0.8, 0], 'I': [-0.6, 0], 'J': [-0.8, 0]},
-15: {'F': [-2.5, 0], 'G': [-1.3, 0], 'H': [-0.9, 0], 'I': [-0.5, 0], 'J': [-0.7, 0]},
-5: {'F': [-2.3, 0], 'G': [-1.2, 0], 'H': [-0.8, 0], 'I': [-0.6, 0.2], 'J': [-0.6, 0.2]},
5: {'F': [-1.7, 0.0], 'G': [-1.2, 0.0], 'H': [-0.6, 0.0], 'I': [-0.6, 0], 'J': [-0.6, 0.2]},
15: {'F': [-0.9, 0.2], 'G': [-0.8, 0.2], 'H': [-0.3, 0.2], 'I': [-0.4, 0.0], 'J': [-1.0, 0.0]},
30: {'F': [-0.5, 0.7], 'G': [-0.5, 0.7], 'H': [-0.2, 0.4], 'I': [-0.4, 0.0], 'J': [-0.5, 0.0]},
45: {'F': [-0.0, 0.7], 'G': [-0.0, 0.7], 'H': [-0.0, 0.6], 'I': [-0.2, 0.0], 'J': [-0.3, 0.0]},
60: {'F': [0, 0.7], 'G': [0, 0.7], 'H': [0, 0.7], 'I': [-0.2, 0], 'J': [-0.3, 0]},
75: {'F': [0, 0.8], 'G': [0, 0.8], 'H': [0, 0.8], 'I': [-0.2, 0], 'J': [-0.3, 0]}
},
'cpe1': {
-45: {'F': [-0.6, 0], 'G': [-0.6, 0], 'H': [-0.8, 0], 'I': [-0.7, 0], 'J': [-1.5, 0]},
-30: {'F': [-2.0, 0], 'G': [-1.5, 0], 'H': [-0.8, 0], 'I': [-0.6, 0], 'J': [-1.4, 0]},
-15: {'F': [-2.8, 0], 'G': [-2.0, 0], 'H': [-1.2, 0], 'I': [-0.5, 0], 'J': [-1.2, 0]},
-5: {'F': [-2.5, 0], 'G': [-2.0, 0], 'H': [-1.2, 0], 'I': [-0.6, 0.2], 'J': [-0.6, 0.2]},
5: {'F': [-2.5, 0.0], 'G': [-2.0, 0.0], 'H': [-1.2, 0.0], 'I': [-0.6, 0], 'J': [-0.6, 0.2]},
15: {'F': [-2.0, 0.2], 'G': [-1.5, 0.2], 'H': [-0.3, 0.2], 'I': [-0.4, 0.0], 'J': [-1.5, 0.0]},
30: {'F': [-1.5, 0.7], 'G': [-1.5, 0.7], 'H': [-0.2, 0.4], 'I': [-0.4, 0.0], 'J': [-0.5, 0.0]},
45: {'F': [0, 0.7], 'G': [0, 0.7], 'H': [0, 0.6], 'I': [-0.2, 0.0], 'J': [-0.3, 0.0]},
60: {'F': [0, 0.7], 'G': [0, 0.7], 'H': [0, 0.7], 'I': [-0.2, 0], 'J': [-0.3, 0]},
75: {'F': [0, 0.8], 'G': [0, 0.8], 'H': [0, 0.8], 'I': [-0.2, 0], 'J': [-0.3, 0]}
}
},
90: {
'cpe10': {
-45: {'F': [-1.4, 0], 'G': [-1.2, 0], 'H': [-1.0, 0], 'I': [-0.9, 0]},
-30: {'F': [-1.5, 0], 'G': [-1.2, 0], 'H': [-1.0, 0], 'I': [-0.9, 0]},
-15: {'F': [-1.9, 0], 'G': [-1.2, 0], 'H': [-0.8, 0], 'I': [-0.8, 0]},
-5: {'F': [-1.8, 0], 'G': [-1.2, 0], 'H': [-0.7, 0], 'I': [-0.6, 0]},
5: {'F': [-1.6, 0], 'G': [-1.3, 0], 'H': [-0.7, 0], 'I': [-0.6, 0]},
15: {'F': [-1.3, 0], 'G': [-1.3, 0], 'H': [-0.6, 0], 'I': [-0.5, 0]},
30: {'F': [-1.1, 0], 'G': [-1.4, 0], 'H': [-0.8, 0], 'I': [-0.5, 0]},
45: {'F': [-1.1, 0], 'G': [-1.4, 0], 'H': [-0.9, 0], 'I': [-0.5, 0]},
60: {'F': [-1.1, 0], 'G': [-1.2, 0], 'H': [-0.8, 0], 'I': [-0.5, 0]},
75: {'F': [-1.1, 0], 'G': [-1.2, 0], 'H': [-0.8, 0], 'I': [-0.5, 0]}
},
'cpe1': {
-45: {'F': [-2.0, 0], 'G': [-2.0, 0], 'H': [-1.3, 0], 'I': [-1.2, 0]},
-30: {'F': [-2.1, 0], 'G': [-2.0, 0], 'H': [-1.3, 0], 'I': [-1.2, 0]},
-15: {'F': [-2.5, 0], 'G': [-2.0, 0], 'H': [-1.2, 0], 'I': [-1.2, 0]},
-5: {'F': [-2.5, 0], 'G': [-2.0, 0], 'H': [-1.2, 0], 'I': [-1.2, 0]},
5: {'F': [-2.2, 0], 'G': [-2.0, 0], 'H': [-1.2, 0], 'I': [-0.6, 0]},
15: {'F': [-2.0, 0], 'G': [-2.0, 0], 'H': [-1.2, 0], 'I': [-0.5, 0]},
30: {'F': [-1.5, 0], 'G': [-2.0, 0], 'H': [-1.2, 0], 'I': [-0.5, 0]},
45: {'F': [-1.5, 0], 'G': [-2.0, 0], 'H': [-1.2, 0], 'I': [-0.5, 0]},
60: {'F': [-1.5, 0], 'G': [-2.0, 0], 'H': [-1.0, 0], 'I': [-0.5, 0]},
75: {'F': [-1.5, 0], 'G': [-2.0, 0], 'H': [-1.0, 0], 'I': [-0.5, 0]}
}
}
}

HIPPED_CPE_DATA= {
0: {
'cpe10': {
5: {'F': [-1.7, 0], 'G': [-1.2, 0], 'H': [-0.6, 0], 'I': [-0.3, 0], 'J': [-0.6, 0], 'K': [-0.6, 0], 'L': [-1.2, 0], 'M': [-0.6, 0], 'N': [-0.4, 0]},
15: {'F': [-0.9, 0.2], 'G': [-0.8, 0.2], 'H': [-0.3, 0.2], 'I': [-0.5, 0], 'J': [-1.0, 0], 'K': [-1.2, 0], 'L': [-1.4, 0], 'M': [-0.6, 0], 'N': [-0.3, 0]},
30: {'F': [-0.5, 0.5], 'G': [-0.5, 0.7], 'H': [-0.2, 0.4], 'I': [-0.4, 0], 'J': [-0.7, 0], 'K': [-0.5, 0], 'L': [-1.4, 0], 'M': [-0.8, 0], 'N': [-0.2, 0]},
45: {'F': [0, 0.7], 'G': [0, 0.7], 'H': [0, 0.6], 'I': [-0.3, 0], 'J': [-0.6, 0], 'K': [-0.3, 0], 'L': [-1.3, 0], 'M': [-0.8, 0], 'N': [-0.2, 0]},
60: {'F': [0, 0.7], 'G': [0, 0.7], 'H': [0, 0.7], 'I': [-0.3, 0], 'J': [-0.6, 0], 'K': [-0.3, 0], 'L': [-1.2, 0], 'M': [-0.4, 0], 'N': [-0.2, 0]},
75: {'F': [0, 0.8], 'G': [0, 0.8], 'H': [0, 0.8], 'I': [-0.3, 0], 'J': [-0.6, 0], 'K': [-0.3, 0], 'L': [-1.2, 0], 'M': [-0.4, 0], 'N': [-0.2, 0]}
},
'cpe1': {
5: {'F': [-2.5, 0], 'G': [-2.0, 0], 'H': [-1.2, 0], 'I': [-0.3, 0], 'J': [-0.6, 0], 'K': [-0.6, 0], 'L': [-2.0, 0], 'M': [-1.2, 0], 'N': [-0.4, 0]},
15: {'F': [-2.0, 0.2], 'G': [-1.5, 0.2], 'H': [-0.3, 0.2], 'I': [-0.5, 0], 'J': [-1.5, 0], 'K': [-2.0, 0], 'L': [-2.0, 0], 'M': [-1.2, 0], 'N': [-0.3, 0]},
30: {'F': [-1.5, 0.5], 'G': [-1.5, 0.7], 'H': [-0.2, 0.4], 'I': [-0.4, 0], 'J': [-1.2, 0], 'K': [-0.5, 0], 'L': [-2.0, 0], 'M': [-1.2, 0], 'N': [-0.2, 0]},
45: {'F': [0, 0.7], 'G': [0, 0.7], 'H': [0, 0.6], 'I': [-0.3, 0], 'J': [-0.6, 0], 'K': [-0.3, 0], 'L': [-2.0, 0], 'M': [-1.2, 0], 'N': [-0.2, 0]},
60: {'F': [0, 0.7], 'G': [0, 0.7], 'H': [0, 0.7], 'I': [-0.3, 0], 'J': [-0.6, 0], 'K': [-0.3, 0], 'L': [-2.0, 0], 'M': [-0.4, 0], 'N': [-0.2, 0]},
75: {'F': [0, 0.8], 'G': [0, 0.8], 'H': [0, 0.8], 'I': [-0.3, 0], 'J': [-0.6, 0], 'K': [-0.3, 0], 'L': [-2.0, 0], 'M': [-0.4, 0], 'N': [-0.2, 0]}
}
}
}

# İç Basınç Katsayıları
CPI_POSITIVE = 0.2
CPI_NEGATIVE = -0.3

# Sabitler
RHO = 1.25
K_I = 1.0
C0 = 1.0

# Muhtemel Duvar Bölgeleri
WALL_ZONES = ("A", "B", "C", "D", "E")
# Muhtemel Çatı Bölgeleri
ROOF_ZONES = ("F", "Fu", "Fl", "G", "H", "I", "J", "K", "L", "M", "N")

"""
table_type    WALL ise
wind_relation farketmez WINDWARD or PARALLEL or LEEWARD ise table_type_dir=0
yüzey bölgelere ayrıldığında Zone label muhtemel "A", "B", "C", "D", "E" olabilir
wind_relation WINDWARD ise  Zone label= "D"
              LEEWARD ise  Zone label= "E"
              PARALLEL ise
              e>= 5d ise Zone label= "A"
              e>= d ise Zone label= "A" ve "B"
              e<d ise Zone label= "A", "B", "C"
olabilir


table_type    MONOPITCH ise
wind_relation WINDWARD ise table_type_dir=0
                Zone label= "F", "G", "H"
              PARALLEL ise table_type_dir=90
                Zone label= "Fu", "Fl", "G", "H", "I"
              LEEWARD ise table_type_dir=180
                Zone label= "F", "G", "H"

table_type    DUOPITCH ise
wind_relation WINDWARD ise table_type_dir=0
                Zone label= "F", "G", "H"
              PARALLEL ise table_type_dir=90
                Zone label= "F", "G", "H", "I" (Tek F bölgesi var, düşük kotlu olanı F yap yüksek kotlu olanı da G yap)
              LEEWARD olamaz

table_type    HIPPED ise
wind_relation WINDWARD ise table_type_dir=0
                Zone label= "F", "G", "H"
              PARALLEL ise table_type_dir=0
                Zone label= "L", "M", "N"
              LEEWARD ise table_type_dir=0
                Zone label= "K", "J", "I"


"""

ARAZI_KATEGORILERI = {
    "Kategori 0": {
        "Arazi kategorisi": "Açık deniz etkisine maruz deniz veya kıyı alanı",
        "z0": 0.003,
        "zmin": 1.0
    },
    "Kategori I": {
        "Arazi kategorisi": "Göl, düz ve açık arazi: Göller veya ihmal edilebilecek seviyede bitki örtüsü olan ve engebeli olmayan düz ve yatay alan",
        "z0": 0.01,
        "zmin": 1.0
    },
    "Kategori II": {
        "Arazi kategorisi": "Bitki örtüsü ve/veya binalarla kaplı arazi: Çayır gibi az seviyede bitki örtüsü olan ve aralarında en az engel yüksekliğinin 20 katı kadar mesafe bulunan engellere (ağaçlar, binalar) sahip alan",
        "z0": 0.05,
        "zmin": 2.0
    },
    "Kategori III": {
        "Arazi kategorisi": "Orman, sanayi veya kentsel bölge: Düzgün yayılı şekilde bir bitki örtüsüne veya binalara veya aralarında en az engel yüksekliğinin 20 katı kadar mesafe bulunan engellere sahip alan (kasabalar, yörekent, ormanlık alan gibi",
        "z0": 0.3,
        "zmin": 5.0
    },
    "Kategori IV": {
        "Arazi kategorisi": "Yoğun şehir merkezi: Yüzeyinin en az % 15’i, yükseklik ortalaması 15 m’yi aşan binalarla kaplı alan",
        "z0": 1.0,
        "zmin": 10.0
    }
}

TOL = 1e-8
EPS = 1e-9


from dataclasses import dataclass, field
import numpy as np
from typing import List, Dict, Tuple, Optional, Any

CPE_DATA = {
    "WALL": WALL_CPE_TABLE,
    "MONOPITCH": MONOPITCH_CPE_DATA,
    "DUOPITCH": DUOPITCH_CPE_DATA,
    "HIPPED": HIPPED_CPE_DATA,
}

@dataclass
class Zone:

    label: str
    coords: np.ndarray

    table_type: str
    table_type_dir: float
    pitch: float

    # cpe_data: dict

    @property
    def cpe10(self):
        return self._interpolate("cpe10")

    @property
    def cpe1(self):
        return self._interpolate("cpe1")
    @staticmethod
    def interpolate(x, x1, x2, y1, y2):
        if x1 == x2:
            return y1
        return y1 + (x - x1) * (y2 - y1) / (x2 - x1)

    def interpolate_angle(self, data, angle):
        angles = sorted(data.keys())

        # h/d için sınırlama

        if self.table_type == "WALL":
            if angle > 5.0:
                angle = 5.0
            elif angle < 0.25:
                angle = 0.25

        if angle < angles[0]:
            angle = angles[0]
        elif angle > angles[-1]:
            angle = angles[-1]

        if angle in data:
            return data[angle]

        for i in range(len(angles) - 1):
            a1 = angles[i]
            a2 = angles[i + 1]

            if a1 <= angle <= a2:
                result = {}
                for zone in data[a1]:
                    y1 = data[a1][zone]
                    y2 = data[a2][zone]

                    if isinstance(y1, (list, tuple)) and isinstance(y2, (list, tuple)):
                        # Handle cases like MONOPITCH with [min_cpe, max_cpe]
                        result[zone] = (
                            self.interpolate(angle, a1, a2, y1[0], y2[0]),
                            self.interpolate(angle, a1, a2, y1[1], y2[1])
                        )
                    else:
                        # Handle cases like WALL with a single cpe value (float)
                        result[zone] = self.interpolate(angle, a1, a2, y1, y2)
                return result

        return data[angles[-1]]

    def _interpolate(self, cpe_type):
        data = CPE_DATA[self.table_type][self.table_type_dir][cpe_type]
        results= self.interpolate_angle(data, self.pitch)
        return results[self.label]

@dataclass
class Edge:
    """
    Saf geometrik kenar verisi. Rüzgar analizi EdgeAnalyzer tarafından yapılır.
    """
    index: int
    p1: np.ndarray
    p2: np.ndarray
    p1_2d: np.ndarray
    p2_2d: np.ndarray

    vector: np.ndarray
    length: float
    direction: np.ndarray

    vector_2d: np.ndarray
    length_2d: float
    direction_2d: Optional[np.ndarray]

    # EdgeAnalyzer tarafından doldurulur
    pos_front: Optional[float] = None
    pos_back: Optional[float] = None

    angle: Optional[float] = None
    exposed: bool = False
    leading: bool = False
    vertical: bool = False
    _global: bool = False

    shared: List[Dict[str, Any]] = field(default_factory=list)
    same_axis: List[Dict[str, Any]] = field(default_factory=list)
    log: str=""
    wind_to_2d: np.ndarray= None
    pos_front_pt: np.ndarray= None

    @classmethod
    def from_points(cls, i: int, plane) -> "Edge":
        p1 = plane.pts_3d[i]
        p2 = plane.pts_3d[(i + 1) % plane.n_pts]

        p1_2d = plane.pts_2d[i]
        p2_2d = plane.pts_2d[(i + 1) % plane.n_pts]

        vector = p2 - p1
        length = np.linalg.norm(vector)

        if length < 1e-12:
            direction = None
        else:
            direction = vector / length


        vector_2d = p2_2d - p1_2d
        length_2d = np.linalg.norm(vector_2d)

        if length_2d < 1e-12:
            direction_2d = None
        else:
            direction_2d = vector_2d / length_2d

        return cls(
            index=i,
            p1=p1, p2=p2,
            p1_2d=p1_2d, p2_2d=p2_2d,
            vector=vector,
            length=length,
            direction=direction,
            vector_2d=vector_2d,
            length_2d=length_2d,
            direction_2d=direction_2d,

        )

    # ------------------------------------------------------------------
    # Geometrik karşılaştırma (rüzgardan bağımsız)
    # ------------------------------------------------------------------

    def same_axis_2d(
        self,
        other: "Edge",
        angle_tol: float = 2.0,
        distance_tol: float = 1e-6,
    ) -> bool:
        d1, d2 = self.direction_2d, other.direction_2d
        if d1 is None or d2 is None:
            return False

        dot = float(np.clip(abs(np.dot(d1, d2)), -1.0, 1.0))
        if np.degrees(np.arccos(dot)) > angle_tol:
            return False

        normal = np.array([-d1[1], d1[0]])
        distance = abs(float(np.dot(other.p1[:2] - self.p1[:2], normal)))
        return distance <= distance_tol

    def is_same_edge(self, other: "Edge", tol: float = 1e-6) -> bool:
        return (
            np.allclose(self.p1, other.p1, atol=tol)
            and np.allclose(self.p2, other.p2, atol=tol)
        ) or (
            np.allclose(self.p1, other.p2, atol=tol)
            and np.allclose(self.p2, other.p1, atol=tol)
        )

    def reset_analysis(self) -> None:
        """Rüzgar analizine bağlı alanları sıfırla."""
        self.pos_front = None
        self.pos_back = None
        self.angle = None
        self.exposed = False
        self.leading = False
        self.vertical = (self.direction_2d is None)
        self.shared = []
        self.same_axis = []

class EdgeAnalyzer:
    """
    Tek bir yüzeyin kenarlarını rüzgar doğrultusuna göre analiz eder.

    Bu sınıf yalnızca LOKAL analiz yapar.

    Üretilen temel bilgiler:
        edge.exposed
        edge.leading
        edge.pos_front
        edge.pos_back
        edge.angle
        edge.vertical

    Başka yüzeylerle karşılaştırma yapılmaz.
    global_leading hesabı Building seviyesinde, bütün yüzeyler
    lokal olarak analiz edildikten sonra yapılmalıdır.
    """

    def __init__(
        self,
        edges: Dict[int, "Edge"],
        surface_normal: np.ndarray,
        is_ccw: bool,
        wind_relation= str,   # "WINDWARD" / "LEEWARD" / "PARALLEL"
        tol: float = 1e-6,
    ):
        self.edges = edges
        self.surface_normal = np.asarray(
            surface_normal,
            dtype=float
        )
        self.is_ccw = bool(is_ccw)
        self.wind_relation = wind_relation
        self.tol = float(tol)

        self._wind_to_2d: Optional[np.ndarray] = None

    # ------------------------------------------------------------------
    # PUBLIC
    # ------------------------------------------------------------------

    def analyze(self, wind_vector, building, current_surface_name):
        """
        Yüzeyin bütün kenarlarını lokal olarak analiz eder.

        wind_vector:
            Rüzgarın hareket yönü.
            Örneğin [1, 0, 0] -> +X
                     [0, 1, 0] -> +Y

        Döndürür:
            self.edges
        """

        wind_to = self._normalize_wind(wind_vector)

        if wind_to is None:
            return {}

        self._wind_to_2d = wind_to

        # Önce bütün kenarların mevcut analiz sonuçlarını temizle.
        for edge in self.edges.values():
            edge.reset_analysis()

        # 1. Her kenarın kendi geometrik özellikleri.
        for edge in self.edges.values():
            self._compute_edge_metrics(edge)

        # 2. Exposed kenarlar arasından lokal hücum kenarını bul.
        self._mark_leading()

        # --------------------------------------------------------------
        # 3) Diğer çatılarla karşılaştır
        # --------------------------------------------------------------

        if building is not None:
            self._find_shared_and_same_axis(
                building,
                current_surface_name,
            )

        return self.edges

    # ------------------------------------------------------------------
    # EDGE METRICS
    # ------------------------------------------------------------------

    def _compute_edge_metrics(self, edge):
        """
        Kenarın rüzgara göre temel geometrik özelliklerini hesaplar.
        """

        # XY doğrultusu olmayan kenar.
        if edge.direction_2d is None:
            pos1 = float(
                np.dot(edge.p1[:2], self._wind_to_2d)
            )

            edge.pos_front = pos1
            edge.pos_back = pos1
            edge.angle = 90.0
            edge.exposed = False
            edge.vertical = True

            return

        p1 = np.asarray(edge.p1[:2], dtype=float)
        p2 = np.asarray(edge.p2[:2], dtype=float)

        # Rüzgar doğrultusundaki konumlar.
        s1 = float(np.dot(p1, self._wind_to_2d))
        s2 = float(np.dot(p2, self._wind_to_2d))

        edge.pos_front_pt = edge.p1_2d if s1 <= s2 else edge.p2_2d
        edge.pos_front = min(s1, s2)
        edge.pos_back = max(s1, s2)

        # Kenar doğrultusu ile rüzgar doğrultusu arasındaki açı.
        direction = np.asarray(
            edge.direction_2d,
            dtype=float
        )

        cos_a = float(
            np.clip(
                abs(np.dot(direction, self._wind_to_2d)),
                -1.0,
                1.0,
            )
        )

        edge.angle = float(
            np.degrees(np.arccos(cos_a))
        )

        # Yüzey sınırının rüzgara bakan tarafı mı?
        edge.exposed = self._is_exposed(edge)

        edge.vertical = False

    # ------------------------------------------------------------------
    # EXPOSED
    # ------------------------------------------------------------------

    def _is_exposed(self, edge) -> bool:
        """
        Kenarın yüzeyin rüzgara bakan sınırında olup olmadığını belirler.

        wind_to:
            Rüzgarın hareket yönüdür.

        CCW polygon:
            dış normal yönü açısından
            cross(edge, wind_to) > 0

        CW polygon:
            cross(edge, wind_to) < 0
        """

        e = (
            np.asarray(edge.p2[:2], dtype=float)
            - np.asarray(edge.p1[:2], dtype=float)
        )

        w = self._wind_to_2d

        cross = (
            e[0] * w[1]
            - e[1] * w[0]
        )

        log_= f"edge log...: index: {edge.index} p1={edge.p1}, p1={edge.p2}\n"
        log_+= f"p1_2d={edge.p1_2d}, p1={edge.p2_2d}\n"
        log_+=f"wind_to_2d: {self._wind_to_2d}\n"
        log_+=f"is_ccw: {self.is_ccw}\n"
        log_+=f"cross: {cross}"


        edge.log= log_
        edge.wind_to_2d= self._wind_to_2d

        if self.is_ccw:
            return cross > self.tol

        return cross < -self.tol

    # ------------------------------------------------------------------
    # LEADING
    # ------------------------------------------------------------------

    def _mark_leading(self):
        exposed = [
            e for e in self.edges.values()
            if e.exposed
        ]

        if not exposed:
            return

        leading = min(
            exposed,
            key=lambda e: (
                e.pos_back,
                -e.angle
            )
        )

        for e in exposed:
            e.leading = (
                abs(e.pos_back - leading.pos_back) <= self.tol
                and abs(e.angle - leading.angle) <= self.tol
            )

    # ------------------------------------------------------------------
    # UTILITIES
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_wind(wind_vector):
        """
        3D rüzgar vektörünü XY düzleminde normalize eder.

        wind_vector rüzgarın hareket yönüdür.
        """

        if wind_vector is None:
            return None

        w = np.asarray(
            wind_vector,
            dtype=float,
        )

        if w.size < 2:
            return None

        w2 = w[:2]

        norm = np.linalg.norm(w2)

        if norm < 1e-12:
            return None

        return w2 / norm

    # ------------------------------------------------------------------
    # 4) SHARED / SAME_AXIS
    # ------------------------------------------------------------------

    def _find_shared_and_same_axis(
        self,
        building: Any,
        current_surface_name: str,
    ) -> None:
        """
        Diğer çatı yüzeyleriyle aynı eksen üzerindeki ve ortak olan
        kenarları belirler.
        """

        surfaces_items = getattr(
            building,
            "surfaces_items",
            {},
        ) or {}

        other_roofs: List[Tuple[str, Any]] = []

        for name, surface in surfaces_items.items():

            if name == current_surface_name:
                continue

            surface_type = getattr(
                surface.surface_type,
                "value",
                surface.surface_type,
            )

            if surface_type != "ROOF":
                continue

            other_roofs.append(
                (name, surface)
            )

        if not other_roofs:
            return

        # --------------------------------------------------------------
        # Her kenarı diğer çatılarla karşılaştır
        # --------------------------------------------------------------

        for edge in self.edges.values():

            if edge.direction_2d is None:
                continue

            for other_name, other_surface in other_roofs:

                for other_edge in other_surface.edges.values():

                    # Aynı fiziksel XY ekseninde değillerse geç
                    if not edge.same_axis_2d(other_edge):
                        continue

                    is_same = edge.is_same_edge(
                        other_edge,
                        tol=self.tol,
                    )

                    entry = {
                        "surface": other_name,
                        "surface_edge": other_edge.index,
                        "surface_angle": getattr(
                            other_surface,
                            "angle",
                            None,
                        ),
                        "direction_2d": other_edge.direction_2d,
                        "same_edge": is_same,
                    }

                    edge.same_axis.append(entry)

                    if is_same:
                        edge.shared.append(entry)

import math
import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Tuple, Optional, Union, Any

EPS = 1.0e-9


class SurfaceType(Enum):
    WALL = "WALL"
    ROOF = "ROOF"
    nodata = ""


class WindRelation(Enum):
    WINDWARD = "WINDWARD"
    LEEWARD = "LEEWARD"
    PARALLEL = "PARALLEL"
    nodata = ""

def polygon_centroid(polygon: np.ndarray) -> np.ndarray:
    """Poligonun merkezini hesaplar"""
    pts = np.asarray(polygon, dtype=float)

    if np.allclose(pts[0], pts[-1]):
        pts = pts[:-1]

    return np.mean(pts, axis=0)

def _make_local_sys(poly_coords, tol=1e-9):
    """
    Düzlemsel 3D bir poligon için sağ elli yerel koordinat sistemi oluşturur.

    Returns
    -------
    dict
        {
            "origin_3d": ...,
            "u_dir": ...,
            "v_dir": ...,
            "normal": ...
        }

    Koordinat sistemi:
        u_dir : poligon düzlemindeki ilk eksen
        v_dir : poligon düzlemindeki ikinci eksen
        normal: u_dir x v_dir
    """

    poly = np.asarray(poly_coords, dtype=float)

    if poly.ndim != 2 or poly.shape[1] != 3:
        raise ValueError("poly_coords (n, 3) şeklinde olmalıdır.")

    if len(poly) < 3:
        raise ValueError("En az üç nokta gerekli.")

    origin = poly[0]

    # ------------------------------------------------------------
    # 1. İlk anlamlı kenarı bul -> u_dir adayı
    # ------------------------------------------------------------

    u_dir = None

    for i in range(1, len(poly)):
        v = poly[i] - origin
        length = np.linalg.norm(v)

        if length > tol:
            u_dir = v / length
            break

    if u_dir is None:
        raise ValueError("Poligon dejenere: bütün noktalar aynı.")

    # ------------------------------------------------------------
    # 2. u_dir'e paralel olmayan bir vektör bul
    #    ve normal'i oluştur
    # ------------------------------------------------------------

    normal = None

    for i in range(1, len(poly)):
        v = poly[i] - origin

        cross = np.cross(u_dir, v)
        cross_len = np.linalg.norm(cross)

        if cross_len > tol:
            normal = cross / cross_len
            break

    if normal is None:
        raise ValueError(
            "Poligon dejenere: bütün noktalar aynı doğru üzerinde."
        )

    # ------------------------------------------------------------
    # 3. Gerçek v_dir'i normal ve u_dir'den üret
    #
    # u x v = normal olacak şekilde
    # ------------------------------------------------------------

    v_dir = np.cross(normal, u_dir)
    v_dir /= np.linalg.norm(v_dir)

    return {
        "origin_3d": origin.copy(),
        "u_dir": u_dir,
        "v_dir": v_dir,
        "normal": normal,
    }

def _project_3d_to_local_2d(poly_coords, local_sys):

    poly = np.asarray(poly_coords, dtype=float)

    origin = local_sys["origin_3d"]
    u_dir = local_sys["u_dir"]
    v_dir = local_sys["v_dir"]

    pts_2d = []

    for pt in poly:
        vec = pt - origin

        u = np.dot(vec, u_dir)
        v = np.dot(vec, v_dir)

        pts_2d.append([u, v])

    return np.asarray(pts_2d)

def _unproject_local_2d_to_3d(pts_2d, local_sys):

    pts_2d = np.asarray(pts_2d, dtype=float)

    origin = local_sys["origin_3d"]
    u_dir = local_sys["u_dir"]
    v_dir = local_sys["v_dir"]

    pts_3d = []

    for u, v in pts_2d:
        point = (
            origin
            + u * u_dir
            + v * v_dir
        )

        pts_3d.append(point)

    return np.asarray(pts_3d)

class WindPlane:
    def __init__(self, polygon: Union[List, np.ndarray], name: str = "Test"):
        """3B Düzlemsel Poligon Nesnesi"""

        pts = np.asarray(polygon, dtype=float)

        if len(pts) > 1 and np.allclose(
            pts[0], pts[-1], atol=1e-8
        ):
            pts = pts[:-1]

        if len(pts) < 3:
            raise ValueError("Poligon en az 3 nokta içermelidir.")

        self.polygon_name = name

        # Açık 3B koordinatlar
        self.coords = pts

        # Kapalı 3B polygon
        self.pts_3d: np.ndarray = self.close_polygon(pts)

        self.n_pts: int = len(pts)

        # Geometrik özellikler
        self.normal, self.normal_unit = self._compute_normal()
        self.centroid = polygon_centroid(self.pts_3d)
        self.pitch: float = self._compute_pitch()

        self.surface_type: SurfaceType = (
            SurfaceType.ROOF
            if self.pitch <= 75.0
            else SurfaceType.WALL
        )

        # En uygun projeksiyon düzlemi
        self.proj_info = _make_local_sys(self.pts_3d)

        # 2B projeksiyon
        self.pts_2d: np.ndarray = _project_3d_to_local_2d(self.pts_3d, self.proj_info)

        self.angle = self._compute_angle()
        self.is_ccw= None
        self.exposed_edge_list = []
        self.edges = self._build_edges()

        self.global_leading = False

        self.properties = {
            "name": self.polygon_name,
            "polygon": self.pts_3d,
            "surface_type": self.surface_type,
            "angle": self.angle,
            "pitch": self.pitch,
            "coords": self.coords,
            "pts_2d": self.pts_2d,
            "zmin": float(np.min(pts[:, 2])),
            "zmax": float(np.max(pts[:, 2])),
            "wind_vector": None,
            "wind_relation": WindRelation.nodata,
            "global_leading": None
        }

    @staticmethod
    def close_polygon(polygon: np.ndarray, tol: float = 1e-8) -> np.ndarray:
        """Poligonu kapatır"""
        polygon = np.asarray(polygon, dtype=float)
        if len(polygon) == 0:
            return polygon
        if not np.allclose(polygon[0], polygon[-1], atol=tol):
            polygon = np.vstack([polygon, polygon[0]])
        return polygon

    def _compute_normal(self) -> Tuple[np.ndarray, np.ndarray]:
        normal = np.zeros(3)
        for i in range(self.n_pts):
            p_curr, p_next = self.pts_3d[i], self.pts_3d[(i + 1) % self.n_pts]
            normal[0] += (p_curr[1] - p_next[1]) * (p_curr[2] + p_next[2])
            normal[1] += (p_curr[2] - p_next[2]) * (p_curr[0] + p_next[0])
            normal[2] += (p_curr[0] - p_next[0]) * (p_curr[1] + p_next[1])

        norm_len = np.linalg.norm(normal)
        if norm_len < 1e-12:
            raise ValueError(f"Geçersiz/Çökmüş poligon düzlemi: {self.pts_3d}")
        return normal, normal / norm_len

    def _compute_angle(self) -> float:
        if self.pitch < 1e-10:
            return 0.0
        nx, ny, nz = self.normal_unit
        if self.pitch >= 90.0 - 1e-10:
            return float(np.degrees(np.arctan2(ny, nx)))
        horiz_len = np.hypot(nx, ny)
        if horiz_len < 1e-12:
            return 0.0
        sign = np.sign(ny) if abs(ny) > abs(nx) else np.sign(nx)
        return float(sign * self.pitch)

    def _compute_pitch(self) -> float:
        nz_ratio = abs(self.normal_unit[2])
        nz_ratio = np.clip(nz_ratio, -1.0, 1.0)
        return float(np.degrees(np.arccos(nz_ratio)))

    def _get_best_projection_plane(self):
        abs_n = np.abs(self.normal_unit)
        max_idx = np.argmax(abs_n)
        if max_idx == 2:
            return 'XY', (0, 1), 2
        elif max_idx == 1:
            return 'XZ', (0, 2), 1
        else:
            return 'YZ', (1, 2), 0

    def polygon_direction_xy(self) -> str:
        """Poligonun XY düzlemindeki yönünü belirler."""

        polygon = np.asarray(self.pts_3d, dtype=float)

        if len(polygon) < 3:
            return "DEGENERATE"

        if np.allclose(polygon[0], polygon[-1]):
            polygon = polygon[:-1]

        if len(polygon) < 3:
            return "DEGENERATE"

        area2 = 0.0
        n = len(polygon)

        for i in range(n):
            x1, y1 = polygon[i][:2]
            x2, y2 = polygon[(i + 1) % n][:2]
            area2 += x1 * y2 - x2 * y1

        if area2 > EPS:
            return "CCW"
        elif area2 < -EPS:
            return "CW"
        else:
            return "DEGENERATE"

    def _build_edges(self) -> Dict[int, Edge]:
        edges = {}
        for i in range(self.n_pts):
            p1 = self.pts_3d[i]
            p2 = self.pts_3d[(i + 1) % self.n_pts]
            try:
                edges[i] = Edge.from_points(i, self)
            except ValueError:
                continue
        return edges

    def get_upslope_vector_xy(self) -> Optional[np.ndarray]:
        """
        Poligonun CCW/CW yapısından bağımsız olarak,
        Z yüksekliğinin arttığı (tırmanma) yönün XY projeksiyonunu döner.
        """
        nx, ny, nz = self.normal_unit

        # Tam dikey duvar veya dümdüz çatı
        if abs(nz) < 1e-4 or abs(nz) > 0.9999:
            return None

        # Z'nin artış gösterdiği XY gradyan yönü: (-nx/nz, -ny/nz)
        slope_xy = -np.array([nx / nz, ny / nz], dtype=float)
        norm = np.linalg.norm(slope_xy)

        return slope_xy / norm if norm > 1e-12 else None

    def analyze_wind_relation(self, w_vector: np.ndarray, angle_tol_deg: float = 5.0) -> WindRelation:
        # 1. Rüzgar yatay birim vektörü
        w_xy = np.array(w_vector[:2], dtype=float)
        w_norm = np.linalg.norm(w_xy)
        if w_norm < 1e-12:
            raise ValueError("Rüzgar vektörünün yatay bileşeni sıfır olamaz.")
        w_xy /= w_norm

        # 2. DUVAR HESABI
        if self.surface_type == SurfaceType.WALL:
            n_xy = np.array(self.normal_unit[:2], dtype=float)
            n_norm = np.linalg.norm(n_xy)
            if n_norm > 1e-12:
                n_xy /= n_norm
                # Dış normal ile rüzgar karşı karşıya geliyorsa (dot < 0) WINDWARD'dır
                dot = np.dot(n_xy, w_xy)
                tol_sin = np.sin(np.radians(angle_tol_deg))
                if dot < -tol_sin:
                    return WindRelation.WINDWARD
                elif dot > tol_sin:
                    return WindRelation.LEEWARD
            return WindRelation.PARALLEL

        # 3. ÇATI (ROOF) HESABI
        upslope_xy = self.get_upslope_vector_xy()

        if upslope_xy is None:
            return WindRelation.PARALLEL

        # Rüzgar yönü ile tırmanış yönünün iç çarpımı
        dot = np.dot(upslope_xy, w_xy)
        tol_cos = np.sin(np.radians(angle_tol_deg))

        # C2 Örneği Kontrolü:
        # Tırmanış yönü (upslope_xy) = [0, -1]  (Y=4'teki Z=5 yüksekliğine doğru)
        # Rüzgar (w_xy)             = [0, -1]  (Y ekseninde eksiye doğru esiyor)
        # dot = 1.0 (Rüzgar yüksek noktaya doğru esiyor -> Yüzeye vuruyor)

        if dot > tol_cos:
            return WindRelation.WINDWARD
        elif dot < -tol_cos:
            return WindRelation.LEEWARD
        else:
            return WindRelation.PARALLEL

    def _analyze_edges(self, w, building=None) -> Dict[int, Edge]:
        is_ccw = (self.polygon_direction_xy() == "CCW")
        self.is_ccw= is_ccw
        rel = self.analyze_wind_relation(w)

        analyzer = EdgeAnalyzer(
            edges=self.edges,
            surface_normal=self.normal_unit,
            is_ccw=is_ccw,
            wind_relation=rel.value,   # "WINDWARD" / "LEEWARD" / "PARALLEL"
            tol=1e-6,
        )
        return analyzer.analyze(
            wind_vector=w,
            building=building,
            current_surface_name=self.polygon_name,
        )

    def analysis_(self, w, building) -> None:
        rel_ = self.analyze_wind_relation(w)
        self.wind_relation = rel_

        self.edges = self._analyze_edges(w, building)

        self.properties["polygon_direction_xy"] = self.polygon_direction_xy()
        self.properties["wind_relation"] = rel_
        self.properties["wind_vector"] = w
        self.properties["any_shared"] = any(e.shared for e in self.edges.values())
        
class BuildingWindEngine:


    def __init__(
        self,
        points: Dict[str, Tuple[float, float, float]],
        polygons: Dict[str, List[str]],
        v_b0: float = 28.0,
        terrain: str = "Kategori III",
        w_dir: List[float] = [1.0, 0.0, 0.0],
        scale_factor: float = 1000.0,
        rho: float = 1.25,
        ct: float = 1.0,
        kI: float = 1.0
    ):
        self.raw_points = points
        self.polygons = polygons
        self.v_b0 = float(v_b0)
        self.terrain = terrain
        self.w_dir = np.array(w_dir, dtype=float)
        self.scale_factor = float(scale_factor)
        self.rho = rho
        self.ct = ct
        self.kI = kI
        self.e= None
        self.all_roof_polygons = {}

        if self.terrain not in ARAZI_KATEGORILERI:
            raise ValueError(f"Geçersiz arazi kategorisi: {self.terrain}")

        self.z0 = ARAZI_KATEGORILERI[self.terrain]["z0"]
        self.zmin = ARAZI_KATEGORILERI[self.terrain]["zmin"]

        # 1. Noktaları ölçekle
        self.scaled_points = self._scale_points()

        # 2. Yüzeyleri analiz et (Duvar/Çatı ayrımı ve kotlar)
        self.surfaces = self._analyze_surfaces()

        # 3. Yüzeylerden gelen verilerle bina geometrisini bağla (Artık çakışma yok)
        self.geometry = self._calculate_building_geometry()

        # 4. Rüzgar parametrelerini (q_b, q_p) hesapla
        self._calculate_wind_parameters()

    def _scale_points(self) -> Dict[str, np.ndarray]:
        return {
            name: np.array(pt, dtype=float) / self.scale_factor
            for name, pt in self.raw_points.items()
        }

    def _analyze_surfaces(self, w= None) -> Dict[str, Dict[str, Any]]:
        """Poligon bağımsız yüzey tipini ve kotlarını çıkarır."""
        if w is None:
            w = self.w_dir

        surfaces = {}
        self.surfaces_items= {}
        self.all_roof_polygons = {}
        for poly_name, pt_names in self.polygons.items():
            pts = np.array([self.scaled_points[pt] for pt in pt_names])
            surface_= WindPlane(pts, name=poly_name)
            self.surfaces_items[poly_name] = surface_
            if surface_.surface_type.value=="ROOF":
                self.all_roof_polygons[poly_name]= surface_.properties['coords']


            surfaces[poly_name] = {
                "type": surface_.properties['surface_type'],
                "pitch": surface_.properties['pitch'],
                "relation": surface_.analyze_wind_relation(self.w_dir),
                "zmin": surface_.properties['zmin'],
                "zmax": surface_.properties['zmax'],
                "coords": surface_.properties['coords']
            }
        return surfaces

    def _calculate_building_geometry(self) -> Dict[str, float]:
        """Hazır self.surfaces üzerinden saçak kotunu çekerek geometriyi tamamlar."""
        pts_matrix = np.array(list(self.scaled_points.values()))

        # Rüzgar eksenleri
        w_xy = self.w_dir[:2] / np.linalg.norm(self.w_dir[:2])
        v_vec = np.array([-w_xy[1], w_xy[0]])

        u_vals = [np.dot(pt[:2], w_xy) for pt in pts_matrix]
        v_vals = [np.dot(pt[:2], v_vec) for pt in pts_matrix]

        b = max(v_vals) - min(v_vals)
        d = max(u_vals) - min(u_vals)

        z_ground = float(min(pt[2] for pt in pts_matrix))
        z_ridge = float(max(pt[2] for pt in pts_matrix))

        # Saçak kotu tespiti (Duvarların maksimum z kotu)
        wall_z_maxs = [s["zmin"] for s in self.surfaces.values() if s["type"] == SurfaceType.ROOF]
        z_eaves = max(wall_z_maxs) if wall_z_maxs else z_ridge

        h_total = z_ridge - z_ground    # Mahya bazlı bina toplam yüksekliği
        h_eaves = z_eaves - z_ground    # Saçak yüksekliği
        e = min(b, 2.0 * h_total)
        self.e= e
        return {
            "b": b,
            "d": d,
            "h": h_total,
            "h_eaves": h_eaves,
            "z0_ground": z_ground,
            "z1_eaves": z_eaves,
            "z2_ridge": z_ridge,
            "e": e
        }

    def _calculate_wind_parameters(self):
        self.q_b = 0.5 * self.rho * (self.v_b0 ** 2) / 1000.0
        self.z_ref = max(self.geometry["z2_ridge"], self.zmin)

        self.kr = 0.19 * ((self.z0 / 0.05) ** 0.07)
        self.cr = self.kr * math.log(self.z_ref / self.z0)
        self.Iv = self.kI / math.log(self.z_ref / self.z0)

        self.ce = (self.cr * self.ct) ** 2 * (1.0 + 7.0 * self.Iv)
        self.q_p = self.ce * self.q_b

    def get_summary(self) -> Dict[str, Any]:
        """Tüm özet sonuçları temiz bir dict olarak döndürür."""
        return {
            "Geometri": self.geometry,
            "Rüzgar Parametreleri": {
                "q_b (kN/m²)": round(self.q_b, 3),
                "q_p (kN/m²)": round(self.q_p, 3),
                "c_e": round(self.ce, 3),
                "I_v": round(self.Iv, 3),
                "c_r": round(self.cr, 3),
                "k_r": round(self.kr, 3),
                "z_ref (m)": round(self.z_ref, 3),
            },
            "Arazi": {
                "Kategori": self.terrain,
                "z0 (m)": self.z0,
                "zmin (m)": self.zmin
            }
        }

    def get_polygon_coords(self, polygon_points, points, scale_=1000.0):
        """Poligon noktalarını koordinatlara dönüştürür ve ölçekler."""
        coords = []
        for pt_name in polygon_points:
            if pt_name in points:
                pt = points[pt_name]
                coords.append([pt[0] / scale_, pt[1] / scale_, pt[2] / scale_])
            else:
                raise ValueError(f"Nokta '{pt_name}' bulunamadı!")
        return np.array(coords)

    def analysis_all_roof_wind(self, w):
        w = np.asarray(w, dtype=float)

        w_len = np.linalg.norm(w)

        if w_len < 1e-12:
            return

        w_norm = w / w_len

        # ------------------------------------------------------------
        # 1. FAZ
        # Bütün yüzeylerin lokal analizini tamamla.
        # ------------------------------------------------------------

        self._analyze_surfaces(w)

        roof_surfaces = {}

        for surface_name, surface in self.surfaces_items.items():

            surface.analysis_(w, self)

            surface.global_leading = False
            surface.properties["global_leading"] = False

            if getattr(
                surface.surface_type,
                "value",
                surface.surface_type
            ) == "ROOF":

                roof_surfaces[surface_name] = surface

        if not roof_surfaces:
            return self.surfaces_items

        # ------------------------------------------------------------
        # 2. FAZ
        # Lokal leading kenarları artık bütün yüzeyler arasında
        # karşılaştır.
        # ------------------------------------------------------------

        self._global_analysis_all_roof_wind(self.surfaces_items,w)


        for surface_name, surface in roof_surfaces.items():
            edges= surface.edges
            surface.properties["global_leading"] = any([True for k in edges.values() if k._global])
            surface.global_leading = any([True for k in edges.values() if k._global])

        return self.surfaces_items

    def _global_analysis_all_roof_wind(self, all_surfaces, w, tol=1e-3):
      w = np.asarray(w, dtype=float)
      w_2d = w[:2]
      w_len = np.linalg.norm(w_2d)

      if w_len < 1e-12:
          return []

      # Rüzgarın gidiş yönü (normalize)
      w_norm = w_2d / w_len
      
      # Rüzgara dik dikdik doğrultu (perpendicular vector)
      w_perp = np.array([-w_norm[1], w_norm[0]])

      candidate_edges = []

      for surface in all_surfaces.values():
          surface_type = getattr(surface.surface_type, "value", surface.surface_type)
          if surface_type != "ROOF":
              continue

          for edge in surface.edges.values():
              p1_2d = np.asarray(edge.p1[:2], dtype=float)
              p2_2d = np.asarray(edge.p2[:2], dtype=float)

              # İki ucun rüzgar eksenindeki konumları
              pos1 = float(np.dot(p1_2d, w_norm))
              pos2 = float(np.dot(p2_2d, w_norm))

              # 1. En ön köşe konumu (Rüzgara en yakın uç)
              front_pos = min(pos1, pos2)
              
              # 2. Kenarın rüzgar eksenindeki ORTA noktası (Kenarı bütünsel temsil eder)
              mid_pos = (pos1 + pos2) / 2.0
              
              # 3. Kenarın rüzgara dik izdüşüm uzunluğu (Rüzgarı ne kadar göğüslüyor?)
              # Rüzgara dik olan kenarın bu değeri yüksek, rüzgara paralel giden kenarın 0 olur.
              proj_len = abs(float(np.dot(p2_2d - p1_2d, w_perp)))

              candidate_edges.append({
                  "surface": getattr(surface, "polygon_name", "ROOF"),
                  "edge": edge,
                  "front_pos": front_pos,
                  "mid_pos": mid_pos,
                  "proj_len": proj_len
              })

      if not candidate_edges:
          return []

      # ------------------------------------------------------------------
      # FİLTRELEME MANTIĞI:
      # ------------------------------------------------------------------
      
      # Adım 1: En öndeki köşeye sahip kenarları bul (Tolerans bandında)
      global_min_front = min(item["front_pos"] for item in candidate_edges)
      front_candidates = [
          item for item in candidate_edges
          if abs(item["front_pos"] - global_min_front) <= tol
      ]

      # Adım 2: Bu adaylar arasından "orta noktası" da en önde olanları (gerçek ön kenarları) seç
      min_mid_pos = min(item["mid_pos"] for item in front_candidates)
      mid_candidates = [
          item for item in front_candidates
          if abs(item["mid_pos"] - min_mid_pos) <= tol
      ]

      # Adım 3: Eğer hala eşitlik varsa, rüzgarı en çok göğüsleyen (izdüşümü en büyük) kenarı öne al
      max_proj = max(item["proj_len"] for item in mid_candidates)
      global_leading_edges = [
          item for item in mid_candidates
          if abs(item["proj_len"] - max_proj) <= tol
      ]

      # Kenarları işaretle
      for item in global_leading_edges:
          item["edge"].leading = True
          item["edge"]._global = True

      return global_leading_edges

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



def dict_tree(data, indent=""):
    lines = []

    items = list(data.items())

    for i, (key, value) in enumerate(items):
        last = i == len(items) - 1

        branch = "└── " if last else "├── "
        lines.append(f"{indent}{branch}{key}")

        if isinstance(value, dict):
            new_indent = indent + ("    " if last else "│   ")
            lines.append(dict_tree(value, new_indent))

        else:
            # Yukarıdaki key satırını value ile birleştir
            lines[-1] = f"{indent}{branch}{key} : {value}"

    return "\n".join(lines)
    
def close_polygon(polygon: np.ndarray, tol: float = TOL) -> np.ndarray:
    """Poligonu kapatır (ilk nokta = son nokta)."""
    polygon = np.asarray(polygon, dtype=float)
    if len(polygon) == 0:
        return polygon
    if not np.allclose(polygon[0], polygon[-1], atol=tol):
        polygon = np.vstack([polygon, polygon[0]])
    return polygon


def _open_polygon(polygon: np.ndarray, tol: float = TOL) -> np.ndarray:
    """Kapalı poligondan tekrar eden son noktayı kaldırır."""
    polygon = np.asarray(polygon, dtype=float)
    if len(polygon) > 1 and np.allclose(polygon[0], polygon[-1], atol=tol):
        return polygon[:-1]
    return polygon


def _area2(poly: np.ndarray) -> float:
    """İki katlı alan (işaretli)."""
    return float(np.sum(
        poly[:, 0] * np.roll(poly[:, 1], -1)
        - poly[:, 1] * np.roll(poly[:, 0], -1)
    ))


def _clean_vertices(pts: np.ndarray, tol: float = EPS) -> np.ndarray:
    """Ardışık mükerrer noktaları ve kapanış tekrarını temizler."""
    if len(pts) == 0:
        return pts
    cleaned = [pts[0]]
    for p in pts[1:]:
        if np.linalg.norm(p - cleaned[-1]) > tol:
            cleaned.append(p)
    if len(cleaned) > 1 and np.linalg.norm(cleaned[0] - cleaned[-1]) <= tol:
        cleaned.pop()
    return np.asarray(cleaned)


# ================================================================
# 2D BÖLME / KIRPMA
# ================================================================

def _split_by_line_2d(pts_2d, p1, p2, tol: float = EPS):
    """Poligonu p1->p2 doğrusu boyunca ikiye böler (Sutherland-Hodgman)."""
    poly = np.asarray(pts_2d, dtype=float)
    p1 = np.asarray(p1, dtype=float)
    p2 = np.asarray(p2, dtype=float)

    if len(poly) < 3:
        return np.empty((0, 2)), np.empty((0, 2))

    line = p2 - p1
    if np.linalg.norm(line) <= tol:
        raise ValueError("p1 ve p2 aynı nokta olamaz.")

    area2 = _area2(poly)
    if abs(area2) <= tol:
        raise ValueError("Poligon alanı sıfıra çok yakın.")
    ccw = area2 > 0

    # p1->p2 doğrusuna göre işaretli uzaklık
    def side(pt):
        v = pt - p1
        return line[0] * v[1] - line[1] * v[0]

    def clip(keep_left: bool) -> np.ndarray:
        result = []
        s = poly[-1]

        for e in poly:
            s_s = side(s)
            e_s = side(e)
            s_in = (s_s >= -tol) if keep_left else (s_s <= tol)
            e_in = (e_s >= -tol) if keep_left else (e_s <= tol)

            if e_in:
                if not s_in:
                    denom = s_s - e_s
                    t = s_s / denom if abs(denom) > tol else 0.0
                    result.append(s + t * (e - s))
                result.append(e.copy())
            elif s_in:
                denom = s_s - e_s
                t = s_s / denom if abs(denom) > tol else 0.0
                result.append(s + t * (e - s))

            s = e

        if not result:
            return np.empty((0, 2))

        cleaned = _clean_vertices(np.asarray(result), tol)
        if len(cleaned) < 3:
            return np.empty((0, 2))
        return cleaned

    left = clip(True)
    right = clip(False)

    def fix_orientation(p: np.ndarray) -> np.ndarray:
        if len(p) < 3:
            return p
        if (_area2(p) > 0) != ccw:
            return p[::-1].copy()
        return p

    return fix_orientation(left), fix_orientation(right)


def _clip_line_to_polygon_2d(line_p1, line_p2, polygon):
    """Sonsuz 2D çizginin poligon sınırıyla iki kesişimini döner."""
    p1 = np.asarray(line_p1, dtype=float)
    p2 = np.asarray(line_p2, dtype=float)
    direction = p2 - p1
    norm = np.linalg.norm(direction)
    if norm < TOL:
        return None
    direction /= norm

    pts = _open_polygon(polygon)
    n = len(pts)
    intersections = []

    for i in range(n):
        a = pts[i]
        b = pts[(i + 1) % n]
        edge = b - a

        cross = direction[0] * edge[1] - direction[1] * edge[0]
        if abs(cross) < 1e-10:
            continue

        q = a - p1
        t = (q[0] * edge[1] - q[1] * edge[0]) / cross
        u = (q[0] * direction[1] - q[1] * direction[0]) / cross

        if -TOL <= u <= 1 + TOL:
            pt = p1 + t * direction
            if not any(np.linalg.norm(pt - prev) < 1e-6 for prev in intersections):
                intersections.append(pt)

    if len(intersections) < 2:
        return None

    intersections.sort(key=lambda p: np.dot(p - p1, direction))
    return intersections[0], intersections[-1]


# ================================================================
# OFFSET / KENAR YARDIMCILARI
# ================================================================

def offset_edge_2d(polygon_2d, p1_2d, p2_2d, w_vector_2d, d_L):
    """Kenarı w yönünde offsetler."""
    p1 = np.asarray(p1_2d, dtype=float)
    p2 = np.asarray(p2_2d, dtype=float)
    w_2d = np.asarray(w_vector_2d, dtype=float)
    w_len = np.linalg.norm(w_2d)
    if w_len < TOL:
        return None
    offset = (w_2d / w_len) * d_L
    return _clip_line_to_polygon_2d(p1 + offset, p2 + offset, polygon_2d)


def create_edge_perp_2d(polygon_2d, p1_2d, p2_2d, w_vector_2d, d_L):
    """Kenara dik iki yardımcı çizgi üretir."""
    p1 = np.asarray(p1_2d, dtype=float)
    p2 = np.asarray(p2_2d, dtype=float)
    edge_vec = p2 - p1
    edge_len = np.linalg.norm(edge_vec)
    if edge_len < TOL:
        return None
    edge_dir = edge_vec / edge_len
    perp_dir = np.array([-edge_dir[1], edge_dir[0]])
    EXT = d_L * 2

    line_L_p1 = p1 + edge_dir * d_L
    line_R_p1 = p2 - edge_dir * d_L

    result_L = _clip_line_to_polygon_2d(line_L_p1, line_L_p1 + perp_dir * EXT, polygon_2d)
    result_R = _clip_line_to_polygon_2d(line_R_p1, line_R_p1 + perp_dir * EXT, polygon_2d)

    if result_L is None and result_R is None:
        return None
    return result_L, result_R


# ================================================================
# 3D <-> 2D
# ================================================================

def _unproject_local_2d_to_3d(pts_2d, local_sys):
    pts_2d = np.asarray(pts_2d, dtype=float)
    origin = local_sys["origin_3d"]
    u_dir = local_sys["u_dir"]
    v_dir = local_sys["v_dir"]
    return origin + pts_2d[:, 0:1] * u_dir + pts_2d[:, 1:2] * v_dir


def valid_polygon(poly) -> bool:
    return poly is not None and len(poly) >= 3


def split(poly, p1, p2):
    if not valid_polygon(poly):
        return None, None
    left, right = _split_by_line_2d(poly, p1, p2)
    return (
        left if valid_polygon(left) else None,
        right if valid_polygon(right) else None,
    )


def to_3d(poly, local_sys):
    if not valid_polygon(poly):
        return None
    return _unproject_local_2d_to_3d(poly, local_sys)

def _get_roof_zones(plane1, e: float, debug: bool = False) -> Dict[str, np.ndarray]:
    """
    Çatı yüzeyini rüzgar bölgelerine ayırır.

    Returns
    -------
    dict
        {zone_label: 3D coords (np.ndarray Nx3)}
        Örn: {"F": ..., "G": ..., "H": ...}
        veya {"Fu": ..., "Fl": ..., "G": ..., "H": ..., "I": ...}
    """
    edges = plane1.edges
    pts_2d = np.asarray(plane1.pts_2d, dtype=float)
    is_ccw = plane1.is_ccw

    exposed_edges = [k for k, ed in edges.items() if ed.exposed]
    leading_edges = [k for k, ed in edges.items() if ed.leading]
    target_edges = leading_edges + [k for k in exposed_edges if k not in leading_edges]

    print("debug",plane1.polygon_name, leading_edges)

    wind_3d = np.asarray(plane1.properties["wind_vector"], dtype=float)
    u_dir = np.asarray(plane1.proj_info["u_dir"], dtype=float)
    v_dir = np.asarray(plane1.proj_info["v_dir"], dtype=float)

    w_plane = np.array([np.dot(wind_3d, u_dir), np.dot(wind_3d, v_dir)])
    w_plane /= np.linalg.norm(w_plane)

    # -------- DICT TABANLI BÖLGE TOPLAYICI --------
    regions_2d: Dict[str, np.ndarray] = {}
    remain_ = pts_2d.copy()

    if debug:
        print(f"\n[_get_roof_zones] {plane1.polygon_name} | rel={plane1.wind_relation.value}")
        print(f"  leading={leading_edges} exposed={exposed_edges} ccw={is_ccw}")

    # ---------------- İç fonksiyonlar ----------------

    def split_FG(poly_FG, edge):
        """WINDWARD kenar için F1, F2, G bölgelerini üretir."""
        result_L, result_R = create_edge_perp_2d(
            pts_2d, edge.p1_2d, edge.p2_2d, edge.wind_to_2d, e / 4.0
        ) or (None, None)

        if result_L is None or result_R is None:
            return

        F_1, F_G = split(poly_FG, *result_L)
        if F_1 is None or F_G is None:
            return

        G_, F_2 = split(F_G, *result_R)
        if G_ is None or F_2 is None:
            return

        # Dict'e etiketli ekle
        regions_2d["F1"] = F_1
        regions_2d["F2"] = F_2
        regions_2d["G"] = G_

    def split_MN(poly_M):
        """PARALLEL kenar için M, N bölgelerini üretir."""
        edge = edges[leading_edges[0]]
        p0e = np.asarray(edge.pos_front_pt, dtype=float) + w_plane * (e / 2.0)
        w_perp = np.array([-w_plane[1], w_plane[0]])
        L = 10.0 * max(np.ptp(pts_2d[:, 0]), np.ptp(pts_2d[:, 1]))

        cut = _clip_line_to_polygon_2d(p0e - w_perp * L, p0e + w_perp * L, remain_)
        if cut is not None:
            M_, N_ = split(poly_M, *cut)
            if M_ is None or N_ is None:
                regions_2d["M"] = poly_M
                return
            regions_2d["M"] = M_
            regions_2d["N"] = N_
        else:
            regions_2d["M"] = poly_M

    # ---------------- Ana döngü ----------------
    sayac=0
    for idx_ in target_edges:
        edge = edges[idx_]
        p1 = np.asarray(edge.p1_2d, dtype=float)
        p2 = np.asarray(edge.p2_2d, dtype=float)

        edge_vec = p2 - p1
        edge_len = np.linalg.norm(edge_vec)
        if edge_len < 1e-10:
            continue

        edge_dir = edge_vec / edge_len
        left_normal = np.array([-edge_dir[1], edge_dir[0]])
        inward = left_normal if is_ccw else -left_normal
        offset = inward * (e / 10.0)

        clipped = _clip_line_to_polygon_2d(p1 + offset, p2 + offset, remain_)
        if clipped is None:
            continue

        H_, FG_ = split(remain_, *clipped)
        if H_ is None or FG_ is None:
            continue

        if edge._global:
            split_FG(FG_, edge)
        else:
            sayac+=1
            regions_2d[f"L{sayac}"] = FG_
            

        remain_ = H_

    # ---------------- Kalan bölge ----------------
    if plane1.wind_relation.value == "PARALLEL":
        split_MN(remain_)
    else:
        regions_2d["M"] = remain_

    # ---------------- F1 vs F2: Z eksenine göre Fu/Fl ata ----------------
    if "F1" in regions_2d and "F2" in regions_2d:
        f1_3d = to_3d(regions_2d["F1"], plane1.proj_info)
        f2_3d = to_3d(regions_2d["F2"], plane1.proj_info)

        if f1_3d is not None and f2_3d is not None:
            # Ortalama Z karşılaştırması
            z1 = float(np.mean(f1_3d[:, 2]))
            z2 = float(np.mean(f2_3d[:, 2]))

            if z1 >= z2:
                regions_2d["Fu"] = regions_2d.pop("F1")
                regions_2d["Fl"] = regions_2d.pop("F2")
            else:
                regions_2d["Fu"] = regions_2d.pop("F2")
                regions_2d["Fl"] = regions_2d.pop("F1")

            if debug:
                print(f"  [F1/F2 → Fu/Fl] z1={z1:.3f} z2={z2:.3f} "
                      f"→ Fu={'F1' if z1 >= z2 else 'F2'}")

    # ---------------- 2D → 3D dönüşümü ----------------
    result: Dict[str, np.ndarray] = {}
    for label, poly_2d in regions_2d.items():
        if not valid_polygon(poly_2d):
            continue
        poly_3d = to_3d(poly_2d, plane1.proj_info)
        if poly_3d is None:
            continue
        result[label] = close_polygon(poly_3d)

    if debug:
        print(f"  [_get_roof_zones] final zones={list(result.keys())}")

    return result



def _get_wall_zones(plane1, e: float, debug: bool = False) -> Dict[str, np.ndarray]:
  
  # --- Projeksiyon bilgisi (roof fonksiyonuyla aynı mantık) ---
  pts_2d = np.asarray(plane1.pts_2d, dtype=float)
  u_dir = np.asarray(plane1.proj_info["u_dir"], dtype=float)
  v_dir = np.asarray(plane1.proj_info["v_dir"], dtype=float)

  # Kapalı poligon
  pts_2d_closed = close_polygon(pts_2d)

  # --- Rüzgar yönünü 2D düzlemde hesapla ---
  wind_3d = np.asarray(plane1.properties["wind_vector"], dtype=float)
  w_plane = np.array([np.dot(wind_3d, u_dir), np.dot(wind_3d, v_dir)])
  w_norm = np.linalg.norm(w_plane)
  if w_norm < 1e-12:
      # Rüzgar duvar düzlemine dik → PARALLEL olamaz, tek bölge dön
      return {"A": close_polygon(plane1.pts_3d)}
  w_dir_2d = w_plane / w_norm

  # Rüzgara dik yön (duvar üzerinde)
  perp_2d = np.array([-w_dir_2d[1], w_dir_2d[0]])

  # --- Duvarın rüzgar yönü boyunca projeksiyon uzunluğu ---
  proj_vals = pts_2d_closed[:-1] @ w_dir_2d
  min_p, max_p = float(np.min(proj_vals)), float(np.max(proj_vals))
  d_len = max_p - min_p

  if d_len < 1e-6:
      return {"A": close_polygon(plane1.pts_3d)}

  # --- e değerini normalize et ---
  # Duvar için bölge uzunlukları e cinsinden ifade edilir.
  # e genelde min(b, h) olarak verilir; burada e/5, 4e/5 kullanılır.
  if e <= 0:
      e = d_len

  a_len = e / 5.0
  b_len = 4.0 * e / 5.0

  # Bölge sınırları (rüzgar yönü boyunca)
  # A: [min_p, min_p + a_len]
  # B: [min_p + a_len, min_p + a_len + b_len]
  # C: kalan
  splits = [a_len, a_len + b_len]
  zone_names = ["A", "B", "C"]

  # Eğer e >= d_len ise, C bölgesi oluşmaz (A+B yeterli)
  if a_len + b_len >= d_len - 1e-5:
      splits = [a_len] if a_len < d_len - 1e-5 else []
      zone_names = ["A", "B"]

  current_poly_2d = pts_2d_closed
  zones: Dict[str, np.ndarray] = {}

  # --- Bölme döngüsü ---
  for idx, offset in enumerate(splits):
      if offset >= d_len - 1e-5:
          break

      split_p = min_p + offset
      ref_pt = w_dir_2d * split_p
      # Rüzgara dik sonsuz çizgi
      p1 = ref_pt - perp_2d * 10000.0
      p2 = ref_pt + perp_2d * 10000.0

      res = _split_by_line_2d(current_poly_2d, p1, p2)
      if res is None:
          break

      part1_2d, part2_2d = res
      if len(part1_2d) < 3 or len(part2_2d) < 3:
          break

      center1 = np.mean(part1_2d[:-1], axis=0) @ w_dir_2d
      center2 = np.mean(part2_2d[:-1], axis=0) @ w_dir_2d

      if center1 < center2:
          zone_2d, current_poly_2d = part1_2d, close_polygon(part2_2d)
      else:
          zone_2d, current_poly_2d = part2_2d, close_polygon(part1_2d)

      # 2D → 3D
      zone_3d = _unproject_local_2d_to_3d(zone_2d, plane1.proj_info)
      zones[zone_names[idx]] = close_polygon(zone_3d)
      if debug:
        print("zone_names[idx]",close_polygon(zone_3d))


  # --- Kalan bölge (C veya B) ---
  remaining_name = zone_names[len(zones)] if len(zones) < len(zone_names) else "C"
  remaining_3d = _unproject_local_2d_to_3d(current_poly_2d, plane1.proj_info)
  zones[remaining_name] = close_polygon(remaining_3d)

  if debug:
      print(f"\n[_get_wall_parallel_zones] {plane1.polygon_name}")
      print(f"  w_dir_2d={w_dir_2d}, d_len={d_len:.3f}, e={e:.3f}")
      print(f"  splits={splits}, zones={list(zones.keys())}")

  return zones
  
  
def get_definition_regions(all_surfaces, regions):
    
    # 1. Determine if the overall roof structure is MONOPITCH
    surface_all_zones= {}
    table_type= None
    table_type_dir= 0
    roof_surfaces = {name: s for name, s in all_surfaces.items() if getattr(s.surface_type, "value", s.surface_type) == "ROOF"}
    roof_relations = [s.properties.get("wind_relation", None).value for s in roof_surfaces.values()]

    is_overall_monopitch = False
    if len(roof_relations) > 0 and all(x == roof_relations[0] for x in roof_relations):
    
        is_overall_monopitch = True

    # 2. Iterate through all surfaces for individual classification
    for sname, plane1 in all_surfaces.items():
        all_zones= []
        wind_relation = plane1.properties.get("wind_relation", None)
        if wind_relation is None:
            continue

        global_leading = plane1.properties.get("global_leading", False)
        surface_type = getattr(plane1.surface_type, "value", plane1.surface_type)

        if surface_type == "ROOF":
            if not is_overall_monopitch: # Apply DUOPITCH/HIPPED if the roof is not overall MONOPITCH
                if wind_relation.value == "PARALLEL" and global_leading:
                    print(f"DUOPITCH ROOF SURFACE: {sname}")
                    table_type = "DUOPITCH"
                    table_type_dir= 90
                else:
                    print(f"HIPPED ROOF SURFACE: {sname}")
                    table_type = "HIPPED"
                    table_type_dir= 0
            else:
                table_type= "MONOPITCH"
                if wind_relation.value == "WINDWARD":
                    table_type_dir= 0
                elif wind_relation.value == "LEEWARD":
                    table_type_dir= 180
                elif wind_relation.value == "PARALLEL":
                    table_type_dir= 90
          
        else: # It's a WALL surface
            table_type = "WALL"

          
        all_coords = np.vstack(list(plane1.pts_3d))
        x_range = all_coords[:, 0].max() - all_coords[:, 0].min()
        y_range = all_coords[:, 1].max() - all_coords[:, 1].min()
        z_range = all_coords[:, 2].max() - all_coords[:, 2].min()
        d= max(x_range, y_range)
        h=z_range

        if table_type == "WALL":
            if d>0:
                pitch= h/d
            else:
                continue
        else:
            pitch= plane1.pitch


        for reg_name,coords in regions[sname].items():
          
          
            if wind_relation.value == "WINDWARD":
                if table_type == "WALL":
                    label= "D"
                else:
                    label= reg_name[:1]
                    if label=="M":
                        label = "H"
            elif wind_relation.value == "LEEWARD":
                if table_type == "WALL":
                  label= "E"
                else:
                  label= reg_name[:1]
                  if label=="M":
                        label = "I"
                  elif label=="L":
                        label = "J"

            elif wind_relation.value == "PARALLEL":
                if table_type == "WALL":
                    label= reg_name
                elif table_type == "MONOPITCH":
                    if reg_name=="M":
                        label="H"
                    elif reg_name=="N":
                        label="I"
                    else:
                        label= reg_name

                elif table_type == "DUOPITCH":
                    if reg_name=="Fl":
                        label="F"
                    elif reg_name=="Fu":
                        label="G"
                    elif reg_name=="M":
                        label="H"
                    elif reg_name=="N":
                        label="I"
                    else:
                        label= reg_name
                else:
                    label= reg_name[:1]
            zone = Zone(
              label= label,
              coords=coords,
              table_type=table_type,
              table_type_dir=table_type_dir,
              pitch= pitch,
            )

            all_zones.append(zone)
        surface_all_zones[sname]= all_zones
    return surface_all_zones
      
def show_zones(building, all_wind_zones):
    import matplotlib.pyplot as plt
    import matplotlib
    from mpl_toolkits.mplot3d import Axes3D
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    import numpy as np

    # ================================================================
    # Data Source: all_wind_zones (List of Zone objects)
    # ================================================================

    # ---- Tüm koordinatları düzleştir ----
    all_polys = []
    for poly_zones in all_wind_zones.values():
        for zone_obj in poly_zones:
            all_polys.append(np.asarray(zone_obj.coords, dtype=float))

    if not all_polys:
        raise ValueError("all_wind_zones boş!")

    all_coords = np.vstack(all_polys)

    fig = plt.figure(figsize=(13, 10))
    ax = fig.add_subplot(111, projection='3d')

    # ---- Eksen aralıkları ----
    x_range = all_coords[:, 0].max() - all_coords[:, 0].min()
    y_range = all_coords[:, 1].max() - all_coords[:, 1].min()
    z_range = all_coords[:, 2].max() - all_coords[:, 2].min()
    max_range = max(x_range, y_range, z_range)

    mid_x = (all_coords[:, 0].max() + all_coords[:, 0].min()) / 2
    mid_y = (all_coords[:, 1].max() + all_coords[:, 1].min()) / 2
    mid_z = (all_coords[:, 2].max() + all_coords[:, 2].min()) / 2

    ax.set_xlim(mid_x - max_range / 2, mid_x + max_range / 2)
    ax.set_ylim(mid_y - max_range / 2, mid_y + max_range / 2)
    ax.set_zlim(mid_z - max_range / 2, mid_z + max_range / 2)
    ax.set_box_aspect([1, 1, 1])

    # ---- CPE10 değerlerini topla ve normalize et ----
    cpe10_values = []
    for poly_zones in all_wind_zones.values():
        for zone_obj in poly_zones:
            cpe = zone_obj.cpe10
            if isinstance(cpe, tuple):
                cpe10_values.append(cpe[0]) # Tuple ise ilk değeri al
            else:
                cpe10_values.append(cpe)

    # Negatif ve pozitif cpe10 değerlerini ayır
    neg_cpe = [v for v in cpe10_values if v < 0]
    pos_cpe = [v for v in cpe10_values if v >= 0]

    min_neg_abs = abs(min(neg_cpe)) if neg_cpe else 0
    max_pos = max(pos_cpe) if pos_cpe else 0

    # Renk haritaları
    # Negatif değerler için: LightBlue -> DarkBlue
    neg_cmap = matplotlib.colormaps.get_cmap('Blues')
    # Pozitif değerler için: LightRed -> DarkRed
    pos_cmap = matplotlib.colormaps.get_cmap('Reds')

    # ================================================================
    # HER POLİGONU ÇİZ + ETİKETİNİ YAZ
    # ================================================================
    for poly_zones in all_wind_zones.values():
        for zone_obj in poly_zones:
            coords = np.asarray(zone_obj.coords, dtype=float)
            zlabel = zone_obj.label

            cpe = zone_obj.cpe10
            if isinstance(cpe, tuple):
                current_cpe = cpe[0]
            else:
                current_cpe = cpe

            # CPE değerine göre renk ataması
            if current_cpe < 0:
                if min_neg_abs > 0:
                    # Negatif değerleri 0-1 aralığına normalize et (mutlak değer olarak)
                    norm_val = abs(current_cpe) / min_neg_abs
                    facecolor = neg_cmap(norm_val)
                else:
                    facecolor = neg_cmap(0.5) # Fallback if no negative values
            else:
                if max_pos > 0:
                    # Pozitif değerleri 0-1 aralığına normalize et
                    norm_val = current_cpe / max_pos
                    facecolor = pos_cmap(norm_val)
                else:
                    facecolor = pos_cmap(0.5) # Fallback if no positive values

            # Poligonu çiz
            col = Poly3DCollection(
                [coords],
                alpha=0.6, # Şeffaflığı biraz artır
                facecolor=facecolor,
                edgecolor='black',
                linewidths=1.0,
            )
            ax.add_collection3d(col)

            # ---- Etiket konumu: ağırlık merkezi ----
            pts = coords
            if len(pts) > 1 and np.allclose(pts[0], pts[-1], atol=1e-9):
                pts = pts[:-1]

            centroid = pts.mean(axis=0)

            # Etiket metni: "Bölge (CPE10)"
            text = f"{zlabel} ({current_cpe:.2f})"

            ax.text(
                centroid[0],
                centroid[1],
                centroid[2],
                text,
                fontsize=8,
                fontweight='bold',
                color='black',
                ha='center',
                va='center',
                bbox=dict(
                    boxstyle='round,pad=0.2',
                    facecolor='white',
                    edgecolor='gray',
                    alpha=0.7,
                    linewidth=0.5,
                ),
                zorder=10,
            )

    # ================================================================
    # RÜZGAR VEKTÖRÜ
    # ================================================================
    wind_vector = building.w_dir
    w_norm = np.linalg.norm(wind_vector)
    wind_dir_norm = wind_vector / w_norm if w_norm > 0 else np.array([1.0, 0.0, 0.0])

    arrow_start_x = mid_x - max_range / 2 - 2 * max_range / 10
    arrow_start_y = mid_y
    arrow_start_z = mid_z
    arrow_length = max_range / 5

    ax.quiver(
        arrow_start_x,
        arrow_start_y,
        arrow_start_z,
        wind_dir_norm[0] * arrow_length,
        wind_dir_norm[1] * arrow_length,
        wind_dir_norm[2] * arrow_length,
        color='red',
        arrow_length_ratio=0.3,
        label='Wind Vector',
        linewidth=2,
    )

    # ================================================================
    # EKSEN VE BAŞLIK
    # ================================================================
    ax.set_xlabel('X Coordinate')
    ax.set_ylabel('Y Coordinate')
    ax.set_zlabel('Z Coordinate')
    ax.set_title('3D Visualization of Wind Zones by CPE10')
    ax.grid(True)

    # Renk çubuklarını ekle (opsiyonel)
    # Negatif için
    if min_neg_abs > 0:
        cbar_neg_ax = fig.add_axes([0.02, 0.3, 0.02, 0.3]) # x, y, width, height
        norm_neg = matplotlib.colors.Normalize(vmin=-min_neg_abs, vmax=0)
        cbar_neg = matplotlib.colorbar.ColorbarBase(cbar_neg_ax, cmap=neg_cmap, norm=norm_neg, orientation='vertical')
        cbar_neg.set_label('Negative CPE10')

    # Pozitif için
    if max_pos > 0:
        cbar_pos_ax = fig.add_axes([0.06, 0.3, 0.02, 0.3]) # x, y, width, height
        norm_pos = matplotlib.colors.Normalize(vmin=0, vmax=max_pos)
        cbar_pos = matplotlib.colorbar.ColorbarBase(cbar_pos_ax, cmap=pos_cmap, norm=norm_pos, orientation='vertical')
        cbar_pos.set_label('Positive CPE10')

    plt.tight_layout(rect=[0.1, 0, 1, 1]) # Colorbar'lar için alanı ayarla
    plt.show()
    
if __name__ == "__main__":
    # ================================================================
    # TEST VERİLERİ
    # ================================================================

    points = {
        "P1": (0.0, 0.0, 0.0),
        "P2": (12000.0, 0.0, 0.0),
        "P3": (12000.0, 8000.0, 0.0),
        "P4": (0.0, 8000.0, 0.0),
        "P5": (0.0, 0.0, 4000.0),
        "P6": (12000.0, 0.0, 4000.0),
        "P7": (12000.0, 8000.0, 4000.0),
        "P8": (0.0, 8000.0, 4000.0),
        "P9": (3000.0, 4000.0, 5000.0),
        "P10": (12000.0, 4000.0, 5000.0),
    }

    polygons = {
        "D1": ["P1", "P2", "P6", "P5"],
        "D2": ["P1", "P5", "P8", "P4"],
        "D3": ["P2", "P3", "P7", "P10", "P6"],
        "D4": ["P3", "P4", "P8", "P7"],
        "C1": ["P5", "P6", "P10", "P9"],
        "C2": ["P8", "P9", "P10", "P7"],
        "C3": ["P8", "P5", "P9"],
    }

    W_LIST = {
        "x+": [1, 0, 0],
        "y+": [0, 1, 0],
        "x-": [-1, 0, 0],
        "y-": [0, -1, 0],
    }
    
    
    w= "x-"
    print(f"\n{'=' * 40}\nWIND: {w}\n{'=' * 40}")

    building = BuildingWindEngine(
        points=points,
        polygons=polygons,
        v_b0=28.0,
        terrain="Kategori III",
        w_dir=W_LIST[w],
        scale_factor=1000,
    )

    print("\nwind_parameters:\n", dict_tree(building.get_summary()))

    all_surfaces = building.analysis_all_roof_wind(W_LIST[w])


    render_lines = {}
    for name in polygons:
      print(name)
      if all_surfaces[name].surface_type.value=="WALL":
        render_lines[name]= {}
        zones= _get_wall_zones(all_surfaces[name], building.e, False)
        render_lines[name].update(zones)

      elif all_surfaces[name].surface_type.value=="ROOF":
        render_lines[name]= {}
        
        zones= _get_roof_zones(all_surfaces[name], building.e, False)
        
        render_lines[name].update(zones)
      print("global_leading:",all_surfaces[name].global_leading)

    all_wind_zones= get_definition_regions(all_surfaces, render_lines)
    # print(all_wind_zones)
    show_zones(building, all_wind_zones)


    


