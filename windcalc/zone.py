#zone.py
from data.wind_data import WALL_CPE_TABLE, MONOPITCH_CPE_DATA, DUOPITCH_CPE_DATA, HIPPED_CPE_DATA

from dataclasses import dataclass
from typing import Optional
import numpy as np

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

    roof_type: str
    roof_type_dir: float
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
        
        if self.roof_type == "WALL":
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
                    result[zone] = (
                        self.interpolate(angle, a1, a2, y1[0], y2[0]),
                        self.interpolate(angle, a1, a2, y1[1], y2[1])
                    )
                return result
        
        return data[angles[-1]]
        
    def _interpolate(self, cpe_type):
        data = CPE_DATA[self.roof_type][self.roof_type_dir][cpe_type]
        results= self.interpolate_angle(data, self.pitch)
        return results[self.label]
        
if __name__ == "__main__":
    zone = Zone(
        label="A",
        coords=right,
        roof_type="WALL",
        roof_type_dir=0,
        pitch=15,
    )
    
    print(zone)
    print(zone.cpe10)