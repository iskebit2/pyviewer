# edge_analyzer.py

import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from edge import Edge

class EdgeAnalyzer:
    """
    Bir yüzeyin Edge koleksiyonunu, verilen rüzgar yönü için XY izdüşümünde
    analiz eder. Dönme kuralı ile exposed tespiti yapar.
    """

    def __init__(
        self,
        edges: Dict[int, "Edge"],
        surface_normal: np.ndarray,
        is_ccw: bool,
        wind_relation: str = "",        # "WINDWARD" | "LEEWARD" | "PARALLEL" | ""
        tol: float = 1e-6,
    ):
        self.edges = edges
        self.surface_normal = np.asarray(surface_normal, dtype=float)
        self.is_ccw = bool(is_ccw)
        self.wind_relation = wind_relation
        self.tol = float(tol)

        self._wind_from_2d: Optional[np.ndarray] = None
        self._wind_to_2d: Optional[np.ndarray] = None

    # ------------------------------------------------------------------
    # PUBLIC
    # ------------------------------------------------------------------

    def analyze(
        self,
        wind_vector: np.ndarray,
        building: Any = None,
        current_surface_name: str = "",
    ) -> Dict[int, "Edge"]:
        w_to = self._normalize_wind(wind_vector)
        if w_to is None:
            return {}

        self._wind_to_2d = w_to
        self._wind_from_2d = -w_to

        # 1) Her kenarı sıfırla ve 2D metrikleri hesapla
        for edge in self.edges.values():
            edge.reset_analysis()
            self._compute_edge_metrics(edge)

        # 2) Leading
        self._mark_leading()

        # 3) Diğer çatılarla karşılaştırma
        if building is not None:
            self._find_shared_and_same_axis(building, current_surface_name)

        return self.edges

    # ------------------------------------------------------------------
    # 1) KENAR BAŞINA METRİKLER
    # ------------------------------------------------------------------

    def _compute_edge_metrics(self, edge: "Edge") -> None:
        # Düşey kenar (XY'de sıfır uzunluk)
        if edge.direction_xy is None:
            pos = float(np.dot(edge.p1[:2], self._wind_from_2d))
            edge.pos_front = pos
            edge.pos_back = pos
            edge.angle = 90.0
            edge.exposed = False
            edge.vertical = True
            return

        # Ön/arka pozisyonlar (wind_from → küçük = ön)
        s1 = float(np.dot(edge.p1[:2], self._wind_from_2d))
        s2 = float(np.dot(edge.p2[:2], self._wind_from_2d))
        edge.pos_front, edge.pos_back = (s1, s2) if s1 <= s2 else (s2, s1)

        # Açı (2D)
        cos_a = float(np.clip(abs(np.dot(edge.direction_xy, self._wind_from_2d)), -1.0, 1.0))
        edge.angle = float(np.degrees(np.arccos(cos_a)))

        # Exposed — dönme kuralı
        edge.exposed = self._is_exposed(edge)
        edge.vertical = False

    def _is_exposed(self, edge: "Edge") -> bool:
        """
        Dönme kuralı ile exposed tespiti.

        PARALLEL yüzeylerde hiçbir kenar rüzgarı karşılamaz → exposed yok.
        (İsteğe bağlı: bu davranışı değiştirmek istersen kaldır.)
        """
        if self.wind_relation == "PARALLEL":
            return False

        e = edge.p2[:2] - edge.p1[:2]
        w = self._wind_to_2d
        cross = e[0] * w[1] - e[1] * w[0]

        if self.is_ccw:
            return cross < -self.tol
        else:
            return cross > self.tol

    # ------------------------------------------------------------------
    # 2) LEADING
    # ------------------------------------------------------------------

    def _mark_leading(self) -> None:
        """
        Leading sadece WINDWARD yüzeylerde olur.
        Exposed kenarlar arasında EN ÖN pozisyona (min pos_front) sahip
        olan(lar) leading olur.
        """
        if self.wind_relation != "WINDWARD":
            return

        exposed = [e for e in self.edges.values() if e.exposed]
        if not exposed:
            return

        global_front = min(e.pos_front for e in exposed)

        for e in exposed:
            if abs(e.pos_front - global_front) <= self.tol:
                if e.length_xy > 1e-3:
                    e.leading = True

    # ------------------------------------------------------------------
    # 3) SHARED / SAME_AXIS
    # ------------------------------------------------------------------

    def _find_shared_and_same_axis(
        self,
        building: Any,
        current_surface_name: str,
    ) -> None:
        surfaces_items = getattr(building, "surfaces_items", {}) or {}

        other_roofs: List[Tuple[str, Any]] = []
        for name, surf in surfaces_items.items():
            if name == current_surface_name:
                continue
            if getattr(surf.surface_type, "value", surf.surface_type) != "ROOF":
                continue
            other_roofs.append((name, surf))

        if not other_roofs:
            return

        for edge in self.edges.values():
            if edge.direction_xy is None:
                continue

            for other_name, other_surf in other_roofs:
                for other_edge in other_surf.edges.values():
                    if not edge.same_axis_xy(other_edge):
                        continue

                    is_same = edge.is_same_edge(other_edge, tol=self.tol)
                    entry = {
                        "surface": other_name,
                        "surface_edge": other_edge.index,
                        "surface_angle": getattr(other_surf, "angle", None),
                        "direction_xy": other_edge.direction_xy,
                        "same_edge": is_same,
                    }
                    edge.same_axis.append(entry)
                    if is_same:
                        edge.shared.append(entry)

    # ------------------------------------------------------------------
    # YARDIMCI
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_wind(wind_vector: np.ndarray) -> Optional[np.ndarray]:
        w = np.asarray(wind_vector, dtype=float)
        w2 = w[:2]
        n = np.linalg.norm(w2)
        return None if n < 1e-12 else w2 / n