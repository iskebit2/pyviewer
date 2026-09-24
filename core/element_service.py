# core/element_service.py

import logging
from dataclasses import dataclass, field
from typing import Any, Optional


# =============================================================
# ELEMENT INFO — çözümleme sonucu
# =============================================================

@dataclass
class ElementInfo:
    """Bir seçimin tam tanımı: View3D karşılığı + domain karşılığı."""

    elem_type: str
    elem_id: str

    view_object: Any = None        # View3D'deki geometrik nesne
    domain_object: Any = None      # building'deki zengin nesne (plane, edge, zone, ...)
    geometry: Any = None           # fallback olarak hazırlanmış dict/obj

    # Başlık için ipucu
    display_title: Optional[str] = None

    @property
    def has_domain(self) -> bool:
        return self.domain_object is not None

    @property
    def has_geometry(self) -> bool:
        return self.geometry is not None

    @property
    def source(self) -> str:
        if self.has_domain:
            return "domain"
        if self.has_geometry:
            return "geometry"
        return "empty"

    def preferred_data(self):
        """
        DataDialog'a gösterilecek asıl veriyi seç.
        Domain varsa domain, yoksa geometry.
        """
        if self.has_domain:
            return self.domain_object
        if self.has_geometry:
            return self.geometry
        return None

    def title(self) -> str:
        if self.display_title:
            return self.display_title

        label = {
            "POLYGON": "Polygon",
            "POINT":   "Point",
            "EDGE":    "Edge",
            "FRAME":   "Frame",
            "ZONE":    "Zone",
            "LINE":    "Line",
        }.get(self.elem_type, self.elem_type or "Element")

        if self.has_domain:
            return f"{label}: {self.elem_id}  [domain]"
        return f"{label}: {self.elem_id}"


# =============================================================
# ELEMENT DATA SERVICE
# =============================================================

class ElementDataService:
    """
    View3D seçimlerini zenginleştirir.

    - `view3d`  : geometrik nesneleri sağlar (points, polygons, frames, ...)
    - `building`: domain nesnelerini sağlar (wind_planes, edges, zones, ...)

    İki taraf arasında eşleştirme yapar ve `ElementInfo` döner.
    """

    def __init__(self, view3d=None, building=None):
        logging.debug("ElementDataService: Initializing...")
        self.view3d = view3d
        self.building = building

    # ---------------------------------------------------------
    # PUBLIC
    # ---------------------------------------------------------

    def resolve(self, elem_type: str, elem_id: str) -> ElementInfo:
        """
        Bir seçimi çözümle. View3D nesnesi, domain nesnesi ve
        gerekli fallback geometrisini toplar.
        """
        logging.debug(f"ElementDataService , resolve, elem_type: {elem_type} elem_id: {elem_id}")

        info = ElementInfo(elem_type=elem_type, elem_id=elem_id)

        # 1) View3D tarafı
        info.view_object = self._find_view_object(elem_type, elem_id)
        logging.debug(f"info.view_object: {info.view_object}")
        # 2) Domain tarafı
        info.domain_object = self._find_domain_object(elem_type, elem_id)
        logging.debug(f"info.view_object: {info.domain_object}")
        # 3) Geometry fallback (domain yoksa veya eksikse)
        info.geometry = self._build_geometry(elem_type, elem_id,
                                              info.view_object)
        logging.debug(f"info.geometry: {info.geometry}")

        # 4) Başlık
        info.display_title = self._build_title(info)
        
        
        return info

    def set_building(self, building):
        self.building = building

    def set_view3d(self, view3d):
        self.view3d = view3d

    # ---------------------------------------------------------
    # 1) VIEW3D TARAFI
    # ---------------------------------------------------------

    def _find_view_object(self, elem_type: str, elem_id: str):
        """View3D'deki geometrik nesneyi bul."""
        if self.view3d is None:
            return None

        # View3D'nin kendi API'si
        if hasattr(self.view3d, "get_element"):
            try:
                obj = self.view3d.get_element(elem_type, elem_id)
                if obj is not None:
                    return obj
            except Exception as e:
                logging.warning(f"ElementDataService: get_element hatası - {e}")

        # Alternatif: map'lerden çek
        return self._view_lookup_fallback(elem_type, elem_id)

    def _view_lookup_fallback(self, elem_type: str, elem_id: str):
        """View3D kendi get_element'i yoksa, map'lere doğrudan bak."""
        v = self.view3d
        if v is None:
            return None

        if elem_type == "POINT":
            return getattr(v, "points", {}).get(elem_id)
        if elem_type == "POLYGON":
            return getattr(v, "polygons", {}).get(elem_id)
        if elem_type == "FRAME":
            return getattr(v, "frames", {}).get(elem_id)
        if elem_type == "EDGE":
            return getattr(v, "edge_items", {}).get(elem_id)
        if elem_type == "ZONE":
            zi = getattr(v, "zone_items", {}).get(elem_id)
            return zi.zone if zi is not None else None
        if elem_type == "LINE":
            # line_3 → lines[3]
            idx = self._parse_line_id(elem_id)
            lines = getattr(v, "lines", [])
            if idx is not None and 0 <= idx < len(lines):
                return lines[idx]
        return None

    @staticmethod
    def _parse_line_id(line_id) -> Optional[int]:
        if isinstance(line_id, int):
            return line_id
        if isinstance(line_id, str) and line_id.startswith("line_"):
            try:
                return int(line_id.split("_", 1)[1])
            except ValueError:
                return None
        return None

    # ---------------------------------------------------------
    # 2) DOMAIN TARAFI
    # ---------------------------------------------------------

    def _find_domain_object(self, elem_type: str, elem_id: str):
        """Building içindeki zengin nesneyi bul."""
        if self.building is None:
            return None

        # --- POLYGON → WindPlane ---
        if elem_type == "POLYGON":
            plane = self._lookup_wind_plane(elem_id)
            if plane is not None:
                return plane

            # Fallback: surfaces_items dict'te fuzzy
            return None

        # --- EDGE → Edge dataclass ---
        if elem_type == "EDGE":
            return self._lookup_edge_object(elem_id)

        # --- POINT → içinde bulunduğu plane (sahibi) ---
        if elem_type == "POINT":
            owner = self._lookup_point_owner(elem_id)
            if owner is not None:
                return owner  # plane
            return None

        # --- FRAME → iki noktasını da içeren plane ---
        if elem_type == "FRAME":
            fr = self._view_frames(elem_id)
            if fr is not None:
                owner = self._lookup_frame_owner(elem_id, fr)
                if owner is not None:
                    return owner
            return None

        # --- ZONE → Zone dataclass ---
        if elem_type == "ZONE":
            return self._lookup_zone_object(elem_id)

        return None

    # ---- Domain lookup yardımcıları ----

    def _wind_planes_dict(self):
        """Building'deki tüm WindPlane'leri döndür."""
        if self.building is None:
            return {}
        # Yeni isim
        planes = getattr(self.building, "wind_planes", None)
        if isinstance(planes, dict):
            return planes
        # Eski isim
        planes = getattr(self.building, "surfaces_items", None)
        if isinstance(planes, dict):
            return planes
        return {}

    def _lookup_wind_plane(self, polygon_id: str):
        planes = self._wind_planes_dict()
        plane = planes.get(polygon_id)
        if plane is not None:
            return plane
        # Fuzzy
        for k, v in planes.items():
            if polygon_id in k or k in polygon_id:
                return v
        return None

    def _lookup_edge_object(self, edge_id: str):
        """
        'D1.0' → D1 plane'inin 0 numaralı edge'i
        """
        if "." not in edge_id:
            return None
        surface_name, _, idx_str = edge_id.rpartition(".")
        try:
            idx = int(idx_str)
        except ValueError:
            return None

        plane = self._lookup_wind_plane(surface_name)
        if plane is None:
            return None

        edges = getattr(plane, "edges", None)
        if not isinstance(edges, dict):
            return None

        # Direkt key
        edge = edges.get(idx)
        if self._is_edge_like(edge):
            return edge

        # Edge.index üzerinden
        for e in edges.values():
            if getattr(e, "index", None) == idx and self._is_edge_like(e):
                return e
        return None

    def _lookup_zone_object(self, zone_id: str):
        for plane in self._wind_planes_dict().values():
            zones = getattr(plane, "zones", None)
            if not isinstance(zones, (list, tuple)):
                continue
            for z in zones:
                for attr in ("name", "label", "id", "index"):
                    val = getattr(z, attr, None)
                    if val is not None and str(val) == zone_id:
                        return z
        return None

    def _lookup_point_owner(self, point_id: str):
        """Noktanın bulunduğu poligon → onun plane'i."""
        if self.view3d is None:
            return None
        polygons = getattr(self.view3d, "polygons", {})
        for poly_name, pts in polygons.items():
            if point_id in pts:
                plane = self._lookup_wind_plane(poly_name)
                if plane is not None:
                    return plane
        return None

    def _lookup_frame_owner(self, frame_id: str, frame_pts):
        """Frame'in iki noktasını da içeren poligon → onun plane'i."""
        if self.view3d is None or frame_pts is None:
            return None
        try:
            p1, p2 = frame_pts
        except (TypeError, ValueError):
            return None

        polygons = getattr(self.view3d, "polygons", {})
        for poly_name, pts in polygons.items():
            if p1 in pts and p2 in pts:
                plane = self._lookup_wind_plane(poly_name)
                if plane is not None:
                    return plane
        return None

    def _view_frames(self, frame_id):
        if self.view3d is None:
            return None
        return getattr(self.view3d, "frames", {}).get(frame_id)

    @staticmethod
    def _is_edge_like(obj) -> bool:
        """index, p1, p2 alanları olan bir dataclass mı?"""
        if obj is None:
            return False
        return all(hasattr(obj, a) for a in ("index", "p1", "p2"))

    # ---------------------------------------------------------
    # 3) GEOMETRY FALLBACK
    # ---------------------------------------------------------

    def _build_geometry(self, elem_type: str, elem_id: str, view_object):
        """
        Domain yoksa veya eksikse gösterilecek geometrik veri.
        Sadece View3D'ye ait bilgiler.
        """
        v = self.view3d
        if v is None:
            return None

        if elem_type == "POINT":
            coords = v.points.get(elem_id)
            if coords is None:
                return None
            return {
                "id": elem_id,
                "x": float(coords[0]),
                "y": float(coords[1]),
                "z": float(coords[2]),
            }

        if elem_type == "POLYGON":
            pts = v.polygons.get(elem_id)
            if pts is None:
                return None
            return {
                "id": elem_id,
                "vertex_count": len(pts),
                "vertices": list(pts),
                "coordinates": {
                    name: tuple(v.points.get(name, ())) for name in pts
                },
            }

        if elem_type == "FRAME":
            fr = v.frames.get(elem_id)
            if fr is None:
                return None
            p1, p2 = fr
            return {
                "id": elem_id,
                "start": p1,
                "end": p2,
                "start_coords": tuple(v.points.get(p1, ())),
                "end_coords": tuple(v.points.get(p2, ())),
            }

        if elem_type == "EDGE":
            edge_item = v.edge_items.get(elem_id)
            if edge_item is None:
                return None
            return {
                "id": elem_id,
                "p1": getattr(edge_item, "p1_name", None),
                "p2": getattr(edge_item, "p2_name", None),
                "p1_coords": tuple(v.points.get(
                    getattr(edge_item, "p1_name", None), ())),
                "p2_coords": tuple(v.points.get(
                    getattr(edge_item, "p2_name", None), ())),
                "parent_polygons": list(
                    getattr(edge_item, "parent_polygons", []) or []
                ),
            }

        if elem_type == "ZONE":
            zi = v.zone_items.get(elem_id)
            if zi is not None:
                return zi.zone
            return None

        if elem_type == "LINE":
            idx = self._parse_line_id(elem_id)
            lines = getattr(v, "lines", [])
            if idx is None or not (0 <= idx < len(lines)):
                return None
            pts = lines[idx]
            return {
                "id": elem_id,
                "point_count": len(pts),
                "points": list(pts),
            }

        return None

    # ---------------------------------------------------------
    # 4) TITLE
    # ---------------------------------------------------------

    def _build_title(self, info: ElementInfo) -> str:
        label = {
            "POLYGON": "Surface",
            "POINT":   "Point",
            "EDGE":    "Edge",
            "FRAME":   "Frame",
            "ZONE":    "Zone",
            "LINE":    "Line",
        }.get(info.elem_type, info.elem_type or "Element")

        if info.has_domain:
            return f"{label}: {info.elem_id}"
        return f"{label}: {info.elem_id}  (geometry)"