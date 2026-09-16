# edge.py

from dataclasses import dataclass, field
import numpy as np
from typing import List, Dict, Tuple, Optional, Any


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

    shared: List[Dict[str, Any]] = field(default_factory=list)
    same_axis: List[Dict[str, Any]] = field(default_factory=list)
    log: str=""

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