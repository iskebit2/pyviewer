#edge.py

from dataclasses import dataclass, field
import numpy as np
from typing import List, Dict, Tuple, Optional, Union, Any

@dataclass
class Edge:
    index: int
    p1: np.ndarray
    p2: np.ndarray

    vector: np.ndarray
    length: float
    unit_vector: np.ndarray

    vector_xy: np.ndarray
    length_xy: float
    direction_xy: Optional[np.ndarray]

    front_positions: Optional[Tuple[float, float]] = None
    angle: Optional[float] = None
    exposed: bool = False
    leading: bool = False

    shared: List[Dict[str, Any]] = field(default_factory=list)
    same_axis: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_points(cls, index: int, p1, p2):
        p1 = np.asarray(p1, dtype=float).copy()
        p2 = np.asarray(p2, dtype=float).copy()

        vector = p2 - p1
        length = np.linalg.norm(vector)

        if length < 1e-12:
            raise ValueError(f"Çökmüş kenar: {index}")

        unit_vector = vector / length

        vector_xy = vector[:2].copy()
        length_xy = np.linalg.norm(vector_xy)

        if length_xy < 1e-12:
            direction_xy = None
        else:
            direction_xy = vector_xy / length_xy

        return cls(
            index=index,
            p1=p1,
            p2=p2,
            vector=vector,
            length=float(length),
            unit_vector=unit_vector,
            vector_xy=vector_xy,
            length_xy=float(length_xy),
            direction_xy=direction_xy,
        )
    
    def analyze_wind(
        self,
        wind_from: np.ndarray,
        surface_normal: np.ndarray,
        tol: float = 1e-6,
    ):
        p1_pos = np.dot(self.p1, wind_from)
        p2_pos = np.dot(self.p2, wind_from)

        self.front_positions = (
            max(p1_pos, p2_pos),
            min(p1_pos, p2_pos),
        )

        outward_normal = np.cross(
            self.unit_vector,
            surface_normal
        )

        norm = np.linalg.norm(outward_normal)

        if norm < 1e-12:
            self.exposed = False
            return

        outward_normal /= norm

        exposure = np.dot(outward_normal, wind_from)

        self.exposed = exposure > tol

        cos_angle = np.clip(
            abs(np.dot(self.unit_vector, wind_from)),
            -1.0,
            1.0
        )

        self.angle = float(
            np.degrees(np.arccos(cos_angle))
        )
        
    def check_leading(
        self,
        best_positions: Tuple[float, float],
        tol: float = 1e-6,
    ) -> bool:

        if not self.exposed:
            self.leading = False
            return False

        if self.front_positions is None:
            self.leading = False
            return False

        self.leading = (
            abs(self.front_positions[0] - best_positions[0]) <= tol
            and
            abs(self.front_positions[1] - best_positions[1]) <= tol
        )

        return self.leading
    
    def same_axis_xy(
        self,
        other: "Edge",
        angle_tol: float = 2.0,
        distance_tol: float = 1e-6,
    ) -> bool:

        d1 = self.direction_xy
        d2 = other.direction_xy

        if d1 is None or d2 is None:
            return False

        dot = np.clip(abs(np.dot(d1, d2)), -1.0, 1.0)
        angle = np.degrees(np.arccos(dot))

        if angle > angle_tol:
            return False

        normal = np.array([-d1[1], d1[0]])

        distance = abs(
            np.dot(other.p1[:2] - self.p1[:2], normal)
        )

        return distance <= distance_tol
    
    def is_same_edge(
        self,
        other: "Edge",
        tol: float = 1e-6,
    ) -> bool:

        return (
            np.allclose(self.p1, other.p1, atol=tol)
            and
            np.allclose(self.p2, other.p2, atol=tol)
        ) or (
            np.allclose(self.p1, other.p2, atol=tol)
            and
            np.allclose(self.p2, other.p1, atol=tol)
        )
    
    def _analyze_edges(self, w, building=None):

        w_3d = np.asarray(w, dtype=float)
        w_norm = np.linalg.norm(w_3d)

        if w_norm < 1e-12:
            return

        wind_from = -(w_3d / w_norm)

        surface_normal = self.normal_unit
        tol = 1e-6

        self_position = np.dot(
            self.centroid,
            wind_from
        )

        # 1. Her kenarın kendi rüzgâr analizini yap
        for edge in self.edges.values():
            edge.analyze_wind(
                wind_from,
                surface_normal,
                tol=tol
            )

        # 2. Leading kenarları bul
        valid_edges = [
            edge for edge in self.edges.values()
            if edge.front_positions is not None
        ]

        if not valid_edges:
            return

        best_positions = max(
            edge.front_positions
            for edge in valid_edges
        )

        for edge in valid_edges:
            edge.check_leading(
                best_positions,
                tol=tol
            )

        # 3. Diğer yüzeylerle ilişkileri bul
        if building is not None:

            for polygon_name, surface in building.surfaces_items.items():

                if polygon_name == self.polygon_name:
                    continue

                if surface.surface_type != SurfaceType.ROOF:
                    continue

                other_position = np.dot(
                    surface.centroid,
                    wind_from
                )

                for edge in self.edges.values():

                    for other_edge in surface.edges.values():

                        if not edge.same_axis_xy(other_edge):
                            continue

                        edge.same_axis.append({
                            "surface": polygon_name,
                            "surface_edge": other_edge.index,
                            "surface_angle": surface.angle,
                            "direction_xy": other_edge.direction_xy,
                            "same_edge": edge.is_same_edge(
                                other_edge,
                                tol=tol
                            ),
                        })

                        if edge.is_same_edge(
                            other_edge,
                            tol=tol
                        ):
                            edge.shared.append({
                                "surface": polygon_name,
                                "surface_edge": other_edge.index,
                                "surface_angle": surface.angle,
                                "upstream": (
                                    other_position >
                                    self_position + tol
                                ),
                            })
i= 0    
p1= np.array([0,0,0])
p2= np.array([12,0,0])
Edge.from_points(i, p1, p2)
