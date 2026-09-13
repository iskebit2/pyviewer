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

    vector: np.ndarray
    length: float
    unit_vector: np.ndarray

    vector_xy: np.ndarray
    length_xy: float
    direction_xy: Optional[np.ndarray]

    # EdgeAnalyzer tarafından doldurulur
    pos_front: Optional[float] = None
    pos_back: Optional[float] = None
    angle: Optional[float] = None
    exposed: bool = False
    leading: bool = False
    vertical: bool = False

    shared: List[Dict[str, Any]] = field(default_factory=list)
    same_axis: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_points(cls, index: int, p1, p2) -> "Edge":
        p1 = np.asarray(p1, dtype=float).copy()
        p2 = np.asarray(p2, dtype=float).copy()

        vector = p2 - p1
        length = float(np.linalg.norm(vector))
        if length < 1e-12:
            raise ValueError(f"Çökmüş kenar: {index}")

        unit_vector = vector / length

        vector_xy = vector[:2].copy()
        length_xy = float(np.linalg.norm(vector_xy))

        direction_xy = None if length_xy < 1e-12 else vector_xy / length_xy

        return cls(
            index=index,
            p1=p1, p2=p2,
            vector=vector,
            length=length,
            unit_vector=unit_vector,
            vector_xy=vector_xy,
            length_xy=length_xy,
            direction_xy=direction_xy,
        )

    # ------------------------------------------------------------------
    # Geometrik karşılaştırma (rüzgardan bağımsız)
    # ------------------------------------------------------------------

    def same_axis_xy(
        self,
        other: "Edge",
        angle_tol: float = 2.0,
        distance_tol: float = 1e-6,
    ) -> bool:
        d1, d2 = self.direction_xy, other.direction_xy
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
        self.vertical = (self.direction_xy is None)
        self.shared = []
        self.same_axis = []