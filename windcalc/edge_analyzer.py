# edge_analyzer.py


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
            surface_normal, dtype=float
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