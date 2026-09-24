# ui/data_dialog.py
"""
DataPanel — View3D seçimlerini ağaç görünümünde sunan bağımsız panel.

QDockWidget ile birlikte kullanılır (bkz. ui/data_dock.py).
Bir QWidget'tir, QDialog değildir: modal değil, kendi başına pencere açmaz.

Görevleri:
- ElementInfo alır, akıllı bir ağaç görünümü oluşturur.
- Ağaçta bir elemana tıklanınca View3D'ye `element_selected` sinyali yayar.
- View3D'den gelen seçimlerde ilgili satırı vurgular.
"""

import logging
from dataclasses import fields, is_dataclass
from typing import Any, Optional

import numpy as np

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QHeaderView,
    QToolBar,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)


# =============================================================
# STİL SABİTLERİ
# =============================================================

_COLOR_SURFACE   = QColor("#2e7d32")   # Yeşil
_COLOR_EDGE      = QColor("#1565c0")   # Mavi
_COLOR_ZONE      = QColor("#6a1b9a")   # Mor
_COLOR_POINT     = QColor("#c62828")   # Kırmızı
_COLOR_FRAME     = QColor("#ef6c00")   # Turuncu
_COLOR_ROOT      = QColor("#0d47a1")   # Koyu Mavi
_COLOR_MUTED     = QColor("#757575")   # Gri
_COLOR_HIGHLIGHT = QColor("#fff3cd")   # Açık Sarı


# =============================================================
# DATAPANEL
# =============================================================

class DataPanel(QWidget):
    """
    View3D ile senkronize ağaç tabanlı veri görüntüleyici.

    Public API:
    - set_element_info(info)   →  ElementInfo göster
    - set_data(obj, title)     →  Ham veri göster
    - show_element(type, id)   →  Ağaçta elemanı vurgula
    - clear()                  →  Temizle
    - clear_selection()        →  Seçimi temizle
    """

    element_selected = Signal(str, str)   # (elem_type, elem_id)
    close_requested  = Signal()           # panel kapatma isteği

    # =========================================================
    # INIT
    # =========================================================

    def __init__(self, view3d=None, parent=None,
                 polygon_name: Optional[str] = None,
                 surface_provider=None):
        super().__init__(parent)
        logging.debug("DataPanel: Initializing...")

        self.view3d = view3d
        self.polygon_name = polygon_name
        self._surface_provider = surface_provider

        # --- Eşlemeler ---
        self._edge_items_map: dict[str, QTreeWidgetItem] = {}
        self._zone_items_map: dict[str, QTreeWidgetItem] = {}
        self._surface_items_map: dict[str, QTreeWidgetItem] = {}
        self._item_meta: dict[int, tuple[str, str]] = {}

        # --- Sinyal bastırma ---
        self._suppress_signals = False

        # --- UI ---
        self._build_toolbar()
        self._build_tree()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.tree)

        self.setMinimumWidth(320)

        # --- View3D sinyali ---
        self._connect_view3d()

    # =========================================================
    # UI KURULUM
    # =========================================================

    def _build_toolbar(self):
        """Sadece ağaç kontrolleri — mod butonu yok."""
        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)

        self.act_expand = self.toolbar.addAction("⏬ Expand All")
        self.act_collapse = self.toolbar.addAction("⏫ Collapse All")

    def _build_tree(self):
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Parameter", "Value"])
        self.tree.setColumnWidth(0, 260)
        self.tree.header().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.tree.setAlternatingRowColors(True)
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self.tree.setEditTriggers(QTreeWidget.EditTrigger.NoEditTriggers)
        self.tree.setUniformRowHeights(True)
        self.tree.setAnimated(False)
        self.tree.setExpandsOnDoubleClick(True)

        self.tree.itemSelectionChanged.connect(self._on_tree_selection_changed)
        self.tree.itemClicked.connect(self._on_tree_item_clicked)

        # Toolbar aksiyonları ağaç oluştuktan sonra bağlanır
        self.act_expand.triggered.connect(self.tree.expandAll)
        self.act_collapse.triggered.connect(self.tree.collapseAll)

    def _connect_view3d(self):
        if self.view3d is None:
            return
        try:
            self.view3d.element_selected.connect(self.on_element_selected)
        except Exception as e:
            logging.warning(f"DataPanel: element_selected bağlanamadı - {e}")

    # =========================================================
    # PUBLIC API
    # =========================================================

    def set_element_info(self, info: Any):
        """
        ElementDataService çıktısını göster.

        `info.preferred_data()` ne dönerse otomatik olarak tanınır:
        - WindPlane          → Properties + Edges + Zones (hepsi bir arada)
        - dict[str, plane]   → çoklu surface
        - dict[int|str, Edge]→ edge listesi
        - Edge / Zone        → düz ağaç
        - diğer / None       → generic / empty
        """
        if info is None:
            self._render_empty_state("Data")
            return

        # Başlık
        title = (info.title() if hasattr(info, "title")
                 else f"{getattr(info, 'elem_type', 'Data')}: "
                      f"{getattr(info, 'elem_id', '')}")
        self.setWindowTitle(title)

        # Tercih edilen veri
        data = info.preferred_data() if hasattr(info, "preferred_data") else info
        if data is None:
            self._render_empty_state(title)
            return

        # Polygon_name ipucu (edge id üretimi için)
        elem_type = getattr(info, "elem_type", None)
        elem_id = getattr(info, "elem_id", None)
        polygon_name = self.polygon_name
        if elem_type == "POLYGON" and elem_id:
            polygon_name = elem_id
        elif elem_type == "EDGE" and elem_id and "." in elem_id:
            polygon_name = elem_id.rsplit(".", 1)[0]
        self.polygon_name = polygon_name

        # Render
        self.set_data(data, title=title, polygon_name=polygon_name)

        # Ağaçta varsa vurgula
        if elem_type and elem_id:
            self.show_element(elem_type, elem_id)

    def set_data(self, data: Any, title: str = "Data",
                 polygon_name: Optional[str] = None):
        """
        Veri setini ağaca yükle. Tip otomatik algılanır.
        """
        if polygon_name is not None:
            self.polygon_name = polygon_name

        if data is None:
            self._render_empty_state(title)
            return

        self.setWindowTitle(title)
        self.clear()

        # 1) dict[str, WindPlane] — çoklu surface
        if isinstance(data, dict) and self._is_multi_plane_dict(data):
            self._render_multi_surfaces(data, title)
            return

        # 2) Tek WindPlane — Properties + Edges + Zones
        if self._is_plane_object(data):
            self._render_plane_full(data, title)
            return

        # 3) dict[int|str, Edge] — edge listesi
        if isinstance(data, dict) and self._is_edge_dict(data):
            self._render_edge_dict(data, title)
            return

        # 4) Edge dataclass
        if self._is_edge_object(data):
            self._render_edge_dataclass(data, title)
            return

        # 5) Zone dataclass
        if self._is_zone_object(data):
            self._render_zone_dataclass(data, title)
            return

        # 6) Diğer → generic
        self._render_generic(data, title)

    def show_element(self, elem_type: str, elem_id: str):
        """View3D'den gelen seçimi ağaçta vurgula (varsa)."""
        if not elem_type or not elem_id:
            return

        item = None
        if elem_type == "EDGE":
            item = self._edge_items_map.get(elem_id)
        elif elem_type == "ZONE":
            item = self._zone_items_map.get(elem_id)
        elif elem_type == "POLYGON":
            item = self._surface_items_map.get(elem_id)

        if item is not None:
            self._select_and_scroll(item)

    def clear_selection(self):
        """Seçimi ve vurguları temizle."""
        self._with_suppressed_signals(
            lambda: (self.tree.clearSelection(), self._clear_highlights())
        )

    def clear(self):
        """Ağacı ve tüm eşlemeleri temizle."""
        def _do():
            self.tree.clear()
            self._edge_items_map.clear()
            self._zone_items_map.clear()
            self._surface_items_map.clear()
            self._item_meta.clear()

        self._with_suppressed_signals(_do)

    # =========================================================
    # VIEW3D → PANEL
    # =========================================================

    def on_element_selected(self, elem_type, elem_id, data=None):
        if elem_type is None:
            self.clear_selection()
            return
        self.show_element(elem_type, elem_id)

    # =========================================================
    # PANEL → VIEW3D
    # =========================================================

    def _on_tree_selection_changed(self):
        if self._suppress_signals:
            return

        items = self.tree.selectedItems()
        if not items:
            if (self.view3d is not None
                    and getattr(self.view3d, "selected_type", None) == "EDGE"):
                self.view3d.clear_selection()
                self.view3d.draw_scene()
            return

        self._emit_view3d_selection(items[0])

    def _on_tree_item_clicked(self, item: QTreeWidgetItem, column: int):
        if self._suppress_signals:
            return
        self._emit_view3d_selection(item)

    def _emit_view3d_selection(self, item: QTreeWidgetItem):
        meta = self._item_meta.get(id(item))
        if meta is None or self.view3d is None:
            return

        elem_type, elem_id = meta

        # Edge: View3D'de yoksa edge modunu aç
        if (elem_type == "EDGE"
                and elem_id not in getattr(self.view3d, "edge_items", {})):
            self.view3d.edge_selection_mode = True
            self.view3d.draw_scene()

        # Zone: yakın eşleşme ara
        elif (elem_type == "ZONE"
              and elem_id not in getattr(self.view3d, "zone_items", {})):
            elem_id = self._resolve_zone_id(elem_id)
            if elem_id is None:
                return

        if hasattr(self.view3d, "select_element"):
            self.view3d.select_element(elem_type, elem_id)
            if hasattr(self.view3d, "_update_selection_states"):
                self.view3d._update_selection_states()
            if hasattr(self.view3d, "draw_scene"):
                self.view3d.draw_scene()

        self.element_selected.emit(elem_type, elem_id)

    def _resolve_zone_id(self, zone_id: str) -> Optional[str]:
        zone_items = getattr(self.view3d, "zone_items", {})
        for k in zone_items:
            if k.startswith(zone_id) or zone_id.startswith(k):
                return k
        logging.warning(f"DataPanel: ZONE '{zone_id}' View3D'de bulunamadı.")
        return None

    # =========================================================
    # RENDER — ÇOKLU SURFACE
    # =========================================================

    def _render_multi_surfaces(self, planes: dict, title: str):
        self.setWindowTitle(title)

        root_item = self._add_root_branch("🏢 Surfaces", _COLOR_ROOT)

        for surface_name, plane in planes.items():
            surface_branch = self._make_surface_branch(root_item, surface_name)
            self._populate_plane_children(surface_branch, plane, surface_name)
            surface_branch.setExpanded(False)

        root_item.setExpanded(True)

    # =========================================================
    # RENDER — TEK PLANE
    # =========================================================

    def _render_plane_full(self, plane, title: str):
        """
        Bir plane'i TÜM dallarıyla göster:
        📊 Properties + 📐 Edges + 🏠 Zones
        """
        self.setWindowTitle(title)

        surface_name = self.polygon_name or "Surface"

        root_item = self._add_root_branch(f"📐 {surface_name}", _COLOR_SURFACE)
        self._item_meta[id(root_item)] = ("POLYGON", surface_name)
        self._surface_items_map[surface_name] = root_item

        self._populate_plane_children(root_item, plane, surface_name)
        root_item.setExpanded(True)

    def _populate_plane_children(self, parent, plane, surface_name):
        """Properties + Edges + Zones dallarını parent'a ekle."""
        self._add_branch_properties(parent, plane)
        self._add_branch_edges(parent, plane, surface_name)
        self._add_branch_zones(parent, plane)

    # =========================================================
    # RENDER — EDGE / ZONE / GENERIC / EMPTY
    # =========================================================

    def _render_edge_dict(self, edges: dict, title: str):
        self.setWindowTitle(title)

        root_item = self._add_root_branch("📐 Edges", _COLOR_EDGE)
        self._populate_edges(root_item, edges, self.polygon_name)
        root_item.setExpanded(True)

    def _render_edge_dataclass(self, edge, title: str):
        self.setWindowTitle(title)

        edge_id = self._make_edge_id(edge, getattr(edge, "index", 0))
        root_item = self._add_root_branch(f"🔷 {edge_id}", _COLOR_EDGE)

        self._item_meta[id(root_item)] = ("EDGE", edge_id)
        self._edge_items_map[edge_id] = root_item

        self._flatten(edge, root_item)
        root_item.setExpanded(True)

    def _render_zone_dataclass(self, zone, title: str):
        self.setWindowTitle(title)

        zone_id = self._make_zone_id(zone, 0)
        root_item = self._add_root_branch(
            f"🏠 {getattr(zone, 'label', zone_id)}", _COLOR_ZONE
        )
        self._item_meta[id(root_item)] = ("ZONE", zone_id)
        self._zone_items_map[zone_id] = root_item

        self._flatten(zone, root_item)
        root_item.setExpanded(True)

    def _render_generic(self, data, title: str):
        self.setWindowTitle(title)

        root_item = self._add_root_branch("Data")
        self._flatten(data, root_item)
        root_item.setExpanded(True)

    def _render_empty_state(self, title: str = "Data"):
        self.clear()
        self.setWindowTitle(title)

        root = self.tree.invisibleRootItem()
        item = QTreeWidgetItem(root)
        item.setText(0, "ℹ️  View3D'de bir eleman seçin")
        f = item.font(0)
        f.setItalic(True)
        item.setFont(0, f)
        item.setForeground(0, QBrush(_COLOR_MUTED))
        item.setExpanded(True)

    # =========================================================
    # DAL OLUŞTURUCULAR
    # =========================================================

    def _add_branch_properties(self, parent, plane):
        props = getattr(plane, "properties", None)
        if props is None:
            return

        branch = QTreeWidgetItem(parent)
        branch.setText(0, "📊 Properties")
        self._set_branch_style(branch, _COLOR_ZONE)
        self._flatten(props, branch)
        branch.setExpanded(False)

    def _add_branch_edges(self, parent, plane, surface_name):
        edges = getattr(plane, "edges", None)
        if not isinstance(edges, dict) or not edges:
            return

        branch = QTreeWidgetItem(parent)
        branch.setText(0, "📐 Edges")
        self._set_branch_style(branch, _COLOR_EDGE)
        self._populate_edges(branch, edges, surface_name)
        branch.setExpanded(False)

    def _populate_edges(self, parent, edges: dict, surface_name):
        for key, edge in edges.items():
            if not self._is_edge_object(edge):
                continue

            edge_id = self._make_edge_id(edge, key, surface_name=surface_name)

            edge_item = QTreeWidgetItem(parent)
            edge_item.setText(0, f"🔷 {edge_id}")
            self._set_branch_style(edge_item, _COLOR_EDGE)
            edge_item.setForeground(1, QBrush(_COLOR_EDGE))
            edge_item.setToolTip(0, f"Edge: {edge_id}")

            self._item_meta[id(edge_item)] = ("EDGE", edge_id)
            self._edge_items_map[edge_id] = edge_item

            self._flatten(edge, edge_item)
            edge_item.setExpanded(False)

    def _add_branch_zones(self, parent, plane):
        zones = getattr(plane, "zones", None)
        if not isinstance(zones, (list, tuple)) or not zones:
            return

        branch = QTreeWidgetItem(parent)
        branch.setText(0, "🏠 Zones")
        self._set_branch_style(branch, _COLOR_ZONE)

        for idx, zone in enumerate(zones):
            zone_id = self._make_zone_id(zone, idx)

            zone_item = QTreeWidgetItem(branch)
            zone_item.setText(0, f"🏠 {zone_id}")
            self._set_branch_style(zone_item, _COLOR_ZONE)
            zone_item.setForeground(1, QBrush(_COLOR_ZONE))
            zone_item.setToolTip(0, f"Zone: {zone_id}")

            self._item_meta[id(zone_item)] = ("ZONE", zone_id)
            self._zone_items_map[zone_id] = zone_item

            self._flatten(zone, zone_item)
            zone_item.setExpanded(False)

        branch.setExpanded(False)

    def _make_surface_branch(self, parent, surface_name: str) -> QTreeWidgetItem:
        item = QTreeWidgetItem(parent)
        item.setText(0, f"📐 {surface_name}")
        self._set_branch_style(item, _COLOR_SURFACE)
        item.setForeground(1, QBrush(_COLOR_SURFACE))

        self._item_meta[id(item)] = ("POLYGON", surface_name)
        self._surface_items_map[surface_name] = item
        return item

    # =========================================================
    # FLATTEN (RECURSIVE)
    # =========================================================

    def _flatten(self, data, parent_item: QTreeWidgetItem):
        """
        Veriyi ağaca dönüştür:
        - dict[int|str, Edge] → edge dalları
        - dict[str, any]      → key-value çocukları
        - dataclass           → alan çocukları
        - list / tuple        → [i] indeksli çocuklar
        - np.ndarray          → bileşenler veya shape özeti
        - leaf                → Value kolonuna yaz
        """
        # DICT
        if isinstance(data, dict):
            for k, v in data.items():
                # int key + Edge value → edge dalı
                if isinstance(k, int) and self._is_edge_object(v):
                    edge_id = self._make_edge_id(
                        v, k, surface_name=self.polygon_name
                    )
                    edge_branch = QTreeWidgetItem(parent_item)
                    edge_branch.setText(0, f"🔷 {edge_id}")
                    self._set_branch_style(edge_branch, _COLOR_EDGE)
                    edge_branch.setForeground(1, QBrush(_COLOR_EDGE))
                    self._item_meta[id(edge_branch)] = ("EDGE", edge_id)
                    self._edge_items_map[edge_id] = edge_branch
                    self._flatten(v, edge_branch)
                    continue

                sub_item = QTreeWidgetItem(parent_item)
                sub_item.setText(0, str(k))

                # str key "D1.0" ise edge olarak kaydet
                if self._looks_like_edge_id(k):
                    self._set_branch_style(sub_item, _COLOR_EDGE)
                    sub_item.setForeground(1, QBrush(_COLOR_EDGE))
                    self._item_meta[id(sub_item)] = ("EDGE", k)
                    self._edge_items_map[k] = sub_item

                self._flatten(v, sub_item)
            return

        # DATACLASS
        if is_dataclass(data) and not isinstance(data, type):
            for f in fields(data):
                sub_item = QTreeWidgetItem(parent_item)
                sub_item.setText(0, f.name)
                self._flatten(getattr(data, f.name), sub_item)
            return

        # LIST / TUPLE
        if isinstance(data, (list, tuple)):
            for i, v in enumerate(data):
                sub_item = QTreeWidgetItem(parent_item)
                sub_item.setText(0, f"[{i}]")
                self._flatten(v, sub_item)
            return

        # NUMPY
        if isinstance(data, np.ndarray):
            self._flatten_ndarray(data, parent_item)
            return

        # LEAF
        parent_item.setText(1, self._fmt(data))

    def _flatten_ndarray(self, data: np.ndarray, parent_item: QTreeWidgetItem):
        flat = data.ravel()
        if flat.size == 0:
            parent_item.setText(1, "empty")
        elif flat.size == 1:
            parent_item.setText(1, self._fmt(flat[0]))
        elif flat.size <= 12:
            for i, v in enumerate(flat):
                sub_item = QTreeWidgetItem(parent_item)
                sub_item.setText(0, f"[{i}]")
                sub_item.setText(1, self._fmt(v))
        else:
            parent_item.setText(1, f"ndarray {data.shape}")

    # =========================================================
    # YARDIMCILAR
    # =========================================================

    def _with_suppressed_signals(self, fn):
        self._suppress_signals = True
        try:
            fn()
        finally:
            self._suppress_signals = False

    def _select_and_scroll(self, item: QTreeWidgetItem):
        def _do():
            self._clear_highlights()

            parent = item.parent()
            while parent is not None:
                parent.setExpanded(True)
                parent = parent.parent()

            self.tree.setCurrentItem(item)
            item.setSelected(True)
            self.tree.scrollToItem(
                item, QTreeWidget.ScrollHint.PositionAtCenter
            )
            self._highlight(item)

        self._with_suppressed_signals(_do)

    def _set_branch_style(self, item: QTreeWidgetItem, color: QColor):
        f = item.font(0)
        f.setBold(True)
        item.setFont(0, f)
        item.setForeground(0, QBrush(color))

    def _highlight(self, item: QTreeWidgetItem):
        for col in (0, 1):
            item.setBackground(col, QBrush(_COLOR_HIGHLIGHT))

    def _clear_highlights(self):
        for store in (self._edge_items_map,
                      self._zone_items_map,
                      self._surface_items_map):
            for item in store.values():
                self._reset_bg(item)

    @staticmethod
    def _reset_bg(item: QTreeWidgetItem):
        for col in (0, 1):
            item.setBackground(col, QBrush(Qt.BrushStyle.NoBrush))
        for i in range(item.childCount()):
            child = item.child(i)
            for col in (0, 1):
                child.setBackground(col, QBrush(Qt.BrushStyle.NoBrush))

    def _add_root_branch(self, text: str, color: QColor = None,
                         bold: bool = True) -> QTreeWidgetItem:
        root = self.tree.invisibleRootItem()
        item = QTreeWidgetItem(root)
        item.setText(0, text)
        if bold:
            f = item.font(0)
            f.setBold(True)
            item.setFont(0, f)
        if color is not None:
            item.setForeground(0, QBrush(color))
        return item

    def _lookup_surface(self, polygon_id: str):
        """surface_provider üzerinden plane ara."""
        if self._surface_provider is None:
            return None
        try:
            plane = self._surface_provider(polygon_id)
        except Exception as e:
            logging.warning(f"surface_provider({polygon_id}) hatası: {e}")
            return None
        if plane is None or not self._is_plane_object(plane):
            return None
        return plane

    # ---- Kimlik üreticileri ----

    def _make_edge_id(self, edge_obj, key, surface_name=None) -> str:
        idx = getattr(edge_obj, "index", key)
        prefix = surface_name or self.polygon_name
        return f"{prefix}.{idx}" if prefix else f"edge_{idx}"

    def _make_zone_id(self, zone_obj, fallback_idx: int) -> str:
        for attr in ("name", "label", "id", "index"):
            val = getattr(zone_obj, attr, None)
            if val is not None:
                return str(val)
        return f"zone_{fallback_idx}"

    # ---- Tip kontrol yardımcıları ----

    def _is_plane_object(self, obj) -> bool:
        """WindPlane benzeri mi? (edges, properties veya zones alanı olan)"""
        if obj is None:
            return False
        return (hasattr(obj, "edges")
                or hasattr(obj, "properties")
                or hasattr(obj, "zones"))

    def _is_multi_plane_dict(self, obj) -> bool:
        """dict[str, WindPlane] mi?"""
        if not isinstance(obj, dict) or not obj:
            return False
        if any(self._is_edge_object(v) for v in obj.values()):
            return False
        return any(self._is_plane_object(v) for v in obj.values())

    def _is_edge_dict(self, obj) -> bool:
        """dict[int|str, Edge] mi?"""
        if not isinstance(obj, dict) or not obj:
            return False
        return any(self._is_edge_object(v) for v in obj.values())

    def _is_edge_object(self, obj) -> bool:
        """index, p1, p2 alanları olan bir dataclass mı?"""
        if not is_dataclass(obj) or isinstance(obj, type):
            return False
        names = {f.name for f in fields(obj)}
        return {"index", "p1", "p2"}.issubset(names)

    def _is_zone_object(self, obj) -> bool:
        """Zone benzeri mi? (label/surface/cpe10 gibi alanlar)"""
        if is_dataclass(obj) and not isinstance(obj, type):
            names = {f.name for f in fields(obj)}
            return bool({"label", "surface", "cpe10"} & names)
        return False

    @staticmethod
    def _looks_like_edge_id(name) -> bool:
        """'D1.0' formatını tanır."""
        if not isinstance(name, str) or "." not in name:
            return False
        head, _, tail = name.rpartition(".")
        return bool(head) and tail.isdigit()

    @staticmethod
    def _fmt(v):
        if v is None:
            return "None"
        if isinstance(v, bool):
            return "True" if v else "False"
        if isinstance(v, float):
            return f"{v:g}"
        if isinstance(v, np.ndarray):
            return np.array2string(v, precision=4, separator=", ")
        return str(v)


# =============================================================
# GERİYE DÖNÜK UYUMLULUK
# =============================================================

# Eski `DataDialog` adıyla kullanılan yerler için
DataDialog = DataPanel


def show_data(data, view3d=None, title="Data", parent=None,
              polygon_name=None, surface_provider=None):
    """Bir DataPanel oluştur, veriyi yükle ve göster."""
    panel = DataPanel(
        view3d=view3d,
        parent=parent,
        polygon_name=polygon_name,
        surface_provider=surface_provider,
    )
    panel.set_data(data, title=title, polygon_name=polygon_name)
    panel.show()
    return panel