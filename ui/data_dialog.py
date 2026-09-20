# ui/data_dialog.py

import logging
from dataclasses import fields, is_dataclass
from typing import Any

import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import (
    QDialog,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QDialogButtonBox,
    QHeaderView,
    QToolBar,
)


class DataDialog(QDialog):

    element_selected = Signal(str, str)   # (elem_type, elem_id)

    # =========================================================
    # INIT
    # =========================================================

    def __init__(self, view3d, parent=None, polygon_name: str = None):
        super().__init__(parent)
        self.view3d = view3d
        self.polygon_name = polygon_name

        # İç durum
        self._planes: dict[str, Any] = {}       # {surface_name: plane}
        self._single_plane = None               # tek plane verildiyse
        self._mode = "multi"                    # "multi" | "single"
        self._single_mode = "edges"             # single iken "edges"|"properties"|"zones"

        # Eşlemeler
        self._edge_items_map: dict[str, QTreeWidgetItem] = {}
        self._zone_items_map: dict[str, QTreeWidgetItem] = {}
        self._surface_items_map: dict[str, QTreeWidgetItem] = {}   # surface_name → dal
        self._item_meta: dict[int, tuple[str, str]] = {}
        self._suppress_signals = False

        # Pencere
        self.setWindowTitle("Data")
        self.setModal(False)
        self.resize(560, 750)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        # ---------- Toolbar ----------
        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)

        self.act_edges = self.toolbar.addAction("📐 Edges")
        self.act_edges.triggered.connect(self._on_show_edges)

        self.act_props = self.toolbar.addAction("📊 Properties")
        self.act_props.triggered.connect(self._on_show_props)

        self.act_zones = self.toolbar.addAction("🏠 Zones")
        self.act_zones.triggered.connect(self._on_show_zones)

        self.toolbar.addSeparator()

        self.act_expand = self.toolbar.addAction("⏬ Expand All")
        self.act_expand.triggered.connect(lambda: self.tree.expandAll())

        self.act_collapse = self.toolbar.addAction("⏫ Collapse All")
        self.act_collapse.triggered.connect(lambda: self.tree.collapseAll())

        # ---------- Ağaç ----------
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Parameter", "Value"])
        self.tree.setColumnWidth(0, 300)
        self.tree.header().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.tree.setAlternatingRowColors(True)
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self.tree.setEditTriggers(QTreeWidget.EditTrigger.NoEditTriggers)
        self.tree.setUniformRowHeights(True)
        self.tree.setAnimated(True)
        self.tree.setExpandsOnDoubleClick(True)

        self.tree.itemSelectionChanged.connect(self._on_tree_selection_changed)
        self.tree.itemClicked.connect(self._on_tree_item_clicked)

        # ---------- Butonlar ----------
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)

        # ---------- Layout ----------
        layout = QVBoxLayout(self)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.tree)
        layout.addWidget(buttons)

        # ---------- View3D sinyalini dinle ----------
        try:
            self.view3d.element_selected.connect(self.on_element_selected)
        except Exception as e:
            logging.warning(f"DataDialog: view3d.element_selected bağlanamadı - {e}")

    # =========================================================
    # PUBLIC API
    # =========================================================

    def set_data(self, data: Any, title: str = "Data", polygon_name: str = None):
        """
        Veri setini ağaca yükle.

        Kabul edilen tipler:
        - dict[str, WindPlane]   → çoklu surface modu
        - WindPlane benzeri      → tek surface modu
        - dict[int|str, Edge]    → sadece edge modu
        - Diğer dataclass/dict/list → generic görüntüleme
        """
        if polygon_name is not None:
            self.polygon_name = polygon_name

        self.setWindowTitle(title)

        # ---------- dict[str, WindPlane] ----------
        if isinstance(data, dict) and self._is_multi_plane_dict(data):
            self._planes = dict(data)
            self._single_plane = None
            self._mode = "multi"
            self._show_multi_surfaces(title)
            return

        # ---------- tek WindPlane ----------
        if self._is_plane_object(data):
            self._single_plane = data
            self._planes = {}
            self._mode = "single"

            # mod önceliği: properties > edges > zones > generic
            props = getattr(data, "properties", None)
            edges = getattr(data, "edges", None)
            zones = getattr(data, "zones", None)

            if props is not None:
                self._single_mode = "properties"
                self._show_single_plane(data, "properties", title)
            elif isinstance(edges, dict) and edges:
                self._single_mode = "edges"
                self._show_single_plane(data, "edges", title)
            elif isinstance(zones, (list, tuple)) and zones:
                self._single_mode = "zones"
                self._show_single_plane(data, "zones", title)
            else:
                self._show_generic(data, title)
            return

        # ---------- dict[int|str, Edge] ----------
        if isinstance(data, dict) and any(
            self._is_edge_object(v) for v in data.values()
        ):
            self._planes = {}
            self._single_plane = None
            self._mode = "single"
            self._single_mode = "edges"
            self._show_all_edges(data, title)
            return

        # ---------- bilinmeyen ----------
        self._planes = {}
        self._single_plane = None
        self._show_generic(data, title)

    def show_element(self, elem_type: str, elem_id: str):
        """View3D'de başka bir nesne seçildiğinde ağacı günceller."""
        try:
            if elem_type == "EDGE":
                self._show_edge(elem_id)
            elif elem_type == "POLYGON":
                self._show_polygon(elem_id)
            elif elem_type == "POINT":
                self._show_point(elem_id)
            elif elem_type == "FRAME":
                self._show_frame(elem_id)
            elif elem_type == "ZONE":
                self._show_zone(elem_id)
        except Exception as e:
            logging.error(f"DataDialog.show_element hatası: {e}")

    def select_element(self, elem_type: str, elem_id: str):
        """View3D'den gelen seçimi ağaçta vurgula."""
        if elem_type != "EDGE":
            return

        item = self._edge_items_map.get(elem_id)
        if item is None:
            return

        self._select_and_scroll(item)

    def clear_selection(self):
        self._suppress_signals = True
        try:
            self.tree.clearSelection()
            self._clear_highlights()
        finally:
            self._suppress_signals = False

    def clear(self):
        self._suppress_signals = True
        try:
            self.tree.clear()
            self._edge_items_map.clear()
            self._zone_items_map.clear()
            self._surface_items_map.clear()
            self._item_meta.clear()
        finally:
            self._suppress_signals = False

    # =========================================================
    # VIEW3D → DIALOG
    # =========================================================

    def on_element_selected(self, elem_type, elem_id, data=None):
        if elem_type is None:
            self.clear_selection()
            return
        self.show_element(elem_type, elem_id)

    # =========================================================
    # DIALOG → VIEW3D
    # =========================================================

    def _on_tree_selection_changed(self):
        if self._suppress_signals:
            return
        items = self.tree.selectedItems()
        if not items:
            if getattr(self.view3d, "selected_type", None) == "EDGE":
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
        if meta is None:
            return

        elem_type, elem_id = meta
        logging.info(f"DataDialog → View3D: {elem_type} '{elem_id}'")

        if elem_type == "EDGE":
            if elem_id not in self.view3d.edge_items:
                self.view3d.edge_selection_mode = True
                self.view3d.draw_scene()

        elif elem_type == "ZONE":
            if elem_id not in self.view3d.zone_items:
                candidates = [
                    k for k in self.view3d.zone_items
                    if k.startswith(elem_id) or elem_id.startswith(k)
                ]
                if candidates:
                    elem_id = candidates[0]
                else:
                    logging.warning(f"DataDialog: ZONE '{elem_id}' View3D'de yok")
                    return

        self.view3d.select_element(elem_type, elem_id)
        self.view3d._update_selection_states()
        self.view3d.draw_scene()

        self.element_selected.emit(elem_type, elem_id)

    # =========================================================
    # ÇOKLU SURFACE MODU (multi)
    # =========================================================

    def _show_multi_surfaces(self, title: str = "Surfaces"):
        """Tüm surface'leri ağaçta göster."""
        self._mode = "multi"
        self.setWindowTitle(title)
        self.clear()

        root = self.tree.invisibleRootItem()

        root_item = QTreeWidgetItem(root)
        root_item.setText(0, "🏢 Surfaces")
        f = root_item.font(0)
        f.setBold(True)
        root_item.setFont(0, f)
        root_item.setForeground(0, QBrush(QColor("#0d47a1")))

        for surface_name, plane in self._planes.items():
            surface_branch = self._make_surface_branch(root_item, surface_name)

            # Properties
            props = getattr(plane, "properties", None)
            if props is not None:
                p_branch = QTreeWidgetItem(surface_branch)
                p_branch.setText(0, "📊 Properties")
                f = p_branch.font(0)
                f.setBold(True)
                p_branch.setFont(0, f)
                p_branch.setForeground(0, QBrush(QColor("#6a1b9a")))
                self._flatten(props, p_branch)
                p_branch.setExpanded(False)

            # Edges
            edges = getattr(plane, "edges", None)
            if isinstance(edges, dict) and edges:
                e_branch = QTreeWidgetItem(surface_branch)
                e_branch.setText(0, "📐 Edges")
                f = e_branch.font(0)
                f.setBold(True)
                e_branch.setFont(0, f)
                e_branch.setForeground(0, QBrush(QColor("#1565c0")))

                for k, edge in edges.items():
                    if not self._is_edge_object(edge):
                        continue
                    edge_id = self._make_edge_id(
                        edge, k, surface_name=surface_name
                    )
                    edge_branch = self._make_edge_branch(e_branch, edge_id)
                    self._flatten(edge, edge_branch)
                e_branch.setExpanded(False)

            # Zones
            zones = getattr(plane, "zones", None)
            if isinstance(zones, (list, tuple)) and zones:
                z_branch = QTreeWidgetItem(surface_branch)
                z_branch.setText(0, "🏠 Zones")
                f = z_branch.font(0)
                f.setBold(True)
                z_branch.setFont(0, f)
                z_branch.setForeground(0, QBrush(QColor("#6a1b9a")))

                for idx, zone in enumerate(zones):
                    zone_id = self._make_zone_id(
                        zone, idx, surface_name=surface_name
                    )
                    zone_branch = self._make_zone_branch(z_branch, zone_id)
                    self._flatten(zone, zone_branch)
                z_branch.setExpanded(False)

            surface_branch.setExpanded(False)

        root_item.setExpanded(True)

    def _make_surface_branch(self, parent, surface_name: str) -> QTreeWidgetItem:
        """'📐 D1' başlıklı kalın yeşil dal."""
        item = QTreeWidgetItem(parent)
        item.setText(0, f"📐 {surface_name}")
        f = item.font(0)
        f.setBold(True)
        item.setFont(0, f)
        item.setForeground(0, QBrush(QColor("#2e7d32")))
        item.setForeground(1, QBrush(QColor("#2e7d32")))

        # Surface item'ını meta olarak kaydet → tıklanınca polygon seçilsin
        self._item_meta[id(item)] = ("POLYGON", surface_name)
        self._surface_items_map[surface_name] = item
        return item

    # =========================================================
    # TEK PLANE MODU (single)
    # =========================================================

    def _show_single_plane(self, plane, mode: str, title: str):
        """Tek plane için Edges / Properties / Zones göster."""
        self._mode = "single"
        self._single_mode = mode
        self.setWindowTitle(title)
        self.clear()

        if mode == "properties":
            self._show_properties(getattr(plane, "properties", None), title)
        elif mode == "edges":
            self._show_all_edges(getattr(plane, "edges", {}), title)
        elif mode == "zones":
            self._show_all_zones(getattr(plane, "zones", []), title)

    def _on_show_edges(self):
        if self._mode == "multi":
            # Çoklu modda toolbar sadece 'expand/collapse' amacıyla kullanılır;
            # tek surface odaklı geçiş için self.polygon_name tercih edilir.
            if self.polygon_name and self.polygon_name in self._planes:
                plane = self._planes[self.polygon_name]
                self._show_single_plane(plane, "edges", "Edge Parameters")
            else:
                self._show_multi_surfaces("Surfaces")
            return

        if self._single_plane is not None:
            self._show_single_plane(self._single_plane, "edges", "Edge Parameters")

    def _on_show_props(self):
        if self._mode == "multi":
            if self.polygon_name and self.polygon_name in self._planes:
                plane = self._planes[self.polygon_name]
                self._show_single_plane(plane, "properties", "Surface Parameters")
            else:
                self._show_multi_surfaces("Surfaces")
            return

        if self._single_plane is not None:
            self._show_single_plane(
                self._single_plane, "properties", "Surface Parameters"
            )

    def _on_show_zones(self):
        if self._mode == "multi":
            if self.polygon_name and self.polygon_name in self._planes:
                plane = self._planes[self.polygon_name]
                self._show_single_plane(plane, "zones", "Zones")
            else:
                self._show_multi_surfaces("Surfaces")
            return

        if self._single_plane is not None:
            self._show_single_plane(self._single_plane, "zones", "Zones")

    # =========================================================
    # PROPERTY / EDGE / ZONE MODLARI
    # =========================================================

    def _show_properties(self, props, title: str = "Surface Parameters"):
        if props is None:
            return

        self.setWindowTitle(title)
        self.clear()

        root = self.tree.invisibleRootItem()
        root_item = QTreeWidgetItem(root)
        root_item.setText(0, "Properties")
        f = root_item.font(0)
        f.setBold(True)
        root_item.setFont(0, f)
        root_item.setForeground(0, QBrush(QColor("#6a1b9a")))

        self._flatten(props, root_item)
        root_item.setExpanded(True)

    def _show_all_edges(self, edges: dict, title: str = "Edge Parameters"):
        self.setWindowTitle(title)
        self.clear()

        root = self.tree.invisibleRootItem()
        root_item = QTreeWidgetItem(root)
        root_item.setText(0, "Edges")
        f = root_item.font(0)
        f.setBold(True)
        root_item.setFont(0, f)

        for k, edge in edges.items():
            if not self._is_edge_object(edge):
                continue
            edge_id = self._make_edge_id(edge, k)
            edge_branch = self._make_edge_branch(root_item, edge_id)
            self._flatten(edge, edge_branch)

        root_item.setExpanded(True)

    def _show_all_zones(self, zones: list, title: str = "Zones"):
        self.setWindowTitle(title)
        self.clear()

        root = self.tree.invisibleRootItem()
        root_item = QTreeWidgetItem(root)
        root_item.setText(0, "Zones")
        f = root_item.font(0)
        f.setBold(True)
        root_item.setFont(0, f)

        for idx, zone in enumerate(zones):
            zone_id = self._make_zone_id(zone, idx)
            zone_branch = self._make_zone_branch(root_item, zone_id)
            self._flatten(zone, zone_branch)

        root_item.setExpanded(True)

    # =========================================================
    # KİMLİK ÜRETİCİLERİ
    # =========================================================

    def _make_edge_id(self, edge_obj, key, surface_name: str = None) -> str:
        """
        View3D ile uyumlu edge id:
        - surface_name = 'D1', index = 0 → 'D1.0'
        - surface_name yoksa → polygon_name kullan
        - o da yoksa → 'edge_{key}'
        """
        idx = getattr(edge_obj, "index", key)
        prefix = surface_name or self.polygon_name
        if prefix:
            return f"{prefix}.{idx}"
        return f"edge_{idx}"

    def _make_zone_id(self, zone_obj, fallback_idx: int,
                      surface_name: str = None) -> str:
        """Zone için kimlik üret."""
        for attr in ("name", "label", "id", "index"):
            val = getattr(zone_obj, attr, None)
            if val is not None:
                return str(val)
        return f"zone_{fallback_idx}"

    # =========================================================
    # AĞAÇ DALI ÜRETİCİLERİ
    # =========================================================

    def _make_edge_branch(self, parent, edge_id: str) -> QTreeWidgetItem:
        item = QTreeWidgetItem(parent)
        item.setText(0, f"🔷 {edge_id}")
        f = item.font(0)
        f.setBold(True)
        item.setFont(0, f)
        item.setForeground(0, QBrush(QColor("#1565c0")))
        item.setForeground(1, QBrush(QColor("#1565c0")))
        item.setToolTip(0, f"Edge: {edge_id}  (tıkla ve grafikte gör)")

        self._item_meta[id(item)] = ("EDGE", edge_id)
        self._edge_items_map[edge_id] = item
        return item

    def _make_zone_branch(self, parent, zone_id: str) -> QTreeWidgetItem:
        item = QTreeWidgetItem(parent)
        item.setText(0, f"🏠 {zone_id}")
        f = item.font(0)
        f.setBold(True)
        item.setFont(0, f)
        item.setForeground(0, QBrush(QColor("#6a1b9a")))
        item.setForeground(1, QBrush(QColor("#6a1b9a")))
        item.setToolTip(0, f"Zone: {zone_id}  (tıkla ve grafikte gör)")

        self._item_meta[id(item)] = ("ZONE", zone_id)
        self._zone_items_map[zone_id] = item
        return item

    # =========================================================
    # FLATTEN (RECURSIVE)
    # =========================================================

    def _flatten(self, data, parent_item: QTreeWidgetItem):
        """
        Veriyi ağaca dönüştürür.
        - dict[int, Edge] → her Edge için '🔷 D1.0' dalı
        - dict[str, Edge] key 'D1.0' formatındaysa edge dalı olur
        - dataclass/dict/list/numpy → alt dallara iner
        - leaf → parent_item'ın Value kolonuna yaz
        """

        # ---------- DICT ----------
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(k, int) and self._is_edge_object(v):
                    edge_id = self._make_edge_id(v, k)
                    edge_branch = self._make_edge_branch(parent_item, edge_id)
                    self._flatten(v, edge_branch)
                    continue

                sub_item = QTreeWidgetItem(parent_item)
                sub_item.setText(0, str(k))

                if self._looks_like_edge_id(k):
                    self._register_as_edge(sub_item, k)

                self._flatten(v, sub_item)
            return

        # ---------- Dataclass ----------
        if is_dataclass(data) and not isinstance(data, type):
            for f in fields(data):
                key = f.name
                val = getattr(data, key)
                sub_item = QTreeWidgetItem(parent_item)
                sub_item.setText(0, key)
                self._flatten(val, sub_item)
            return

        # ---------- List / Tuple ----------
        if isinstance(data, (list, tuple)):
            for i, v in enumerate(data):
                sub_item = QTreeWidgetItem(parent_item)
                sub_item.setText(0, f"[{i}]")
                self._flatten(v, sub_item)
            return

        # ---------- Numpy array ----------
        if isinstance(data, np.ndarray):
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
            return

        # ---------- Leaf ----------
        parent_item.setText(1, self._fmt(data))

    # =========================================================
    # DİĞER ELEMANLAR (context-aware)
    # =========================================================

    def _show_edge(self, edge_id: str):
        item = self._edge_items_map.get(edge_id)
        if item is None:
            return
        self._select_and_scroll(item)

    def _show_polygon(self, poly_id: str):
        """Poligon seçildiğinde: eğer çoklu moddaysa o surface'e odaklan,
        değilse vertex listesini göster."""
        # Çoklu surface modunda ve surface mevcutsa oraya odaklan
        if self._mode == "multi" and poly_id in self._surface_items_map:
            self.polygon_name = poly_id
            item = self._surface_items_map[poly_id]
            self._select_and_scroll(item)
            return

        p = self.view3d.polygons.get(poly_id)
        if p is None:
            return

        self.setWindowTitle(f"Polygon: {poly_id}")
        self.clear()

        root = self.tree.invisibleRootItem()
        root_item = QTreeWidgetItem(root)
        root_item.setText(0, f"📐 {poly_id}")
        f = root_item.font(0)
        f.setBold(True)
        root_item.setFont(0, f)
        root_item.setForeground(0, QBrush(QColor("#2e7d32")))

        verts_branch = QTreeWidgetItem(root_item)
        verts_branch.setText(0, "Vertices")

        for i, name in enumerate(p):
            item = QTreeWidgetItem(verts_branch)
            item.setText(0, f"[{i}] {name}")
            coords = self.view3d.points.get(name)
            if coords is not None:
                item.setText(1, self._fmt(np.asarray(coords)))

        verts_branch.setExpanded(True)
        root_item.setExpanded(True)

        self._item_meta[id(root_item)] = ("POLYGON", poly_id)

    def _show_point(self, pt_id: str):
        coords = self.view3d.points.get(pt_id)
        if coords is None:
            return

        self.setWindowTitle(f"Point: {pt_id}")
        self.clear()

        root = self.tree.invisibleRootItem()
        root_item = QTreeWidgetItem(root)
        root_item.setText(0, f"📍 {pt_id}")
        f = root_item.font(0)
        f.setBold(True)
        root_item.setFont(0, f)
        root_item.setForeground(0, QBrush(QColor("#c62828")))

        for i, c in enumerate(coords):
            leaf = QTreeWidgetItem(root_item)
            leaf.setText(0, ["X", "Y", "Z"][i] if i < 3 else f"[{i}]")
            leaf.setText(1, self._fmt(c))

        root_item.setExpanded(True)
        self._item_meta[id(root_item)] = ("POINT", pt_id)

    def _show_frame(self, frame_id: str):
        fr = self.view3d.frames.get(frame_id)
        if fr is None:
            return
        p1, p2 = fr

        self.setWindowTitle(f"Frame: {frame_id}")
        self.clear()

        root = self.tree.invisibleRootItem()
        root_item = QTreeWidgetItem(root)
        root_item.setText(0, f"🔗 {frame_id}")
        f = root_item.font(0)
        f.setBold(True)
        root_item.setFont(0, f)
        root_item.setForeground(0, QBrush(QColor("#ef6c00")))

        for label, pt_name in (("Start (p1)", p1), ("End (p2)", p2)):
            leaf = QTreeWidgetItem(root_item)
            leaf.setText(0, label)
            coords = self.view3d.points.get(pt_name)
            if coords is not None:
                leaf.setText(1, f"{pt_name}  {self._fmt(np.asarray(coords))}")
            else:
                leaf.setText(1, pt_name)

        root_item.setExpanded(True)
        self._item_meta[id(root_item)] = ("FRAME", frame_id)

    def _show_zone(self, zone_id: str):
        item = self._zone_items_map.get(zone_id)
        if item is not None:
            # üst ataları aç ve seç
            parent = item.parent()
            while parent is not None:
                parent.setExpanded(True)
                parent = parent.parent()
            self._select_and_scroll(item)
            return

        # Bulunamazsa fallback: tekil gösterim
        zi = self.view3d.zone_items.get(zone_id)
        if zi is None:
            return
        z = zi.zone
        self.setWindowTitle(f"Zone: {zone_id}")
        self.clear()
        root = self.tree.invisibleRootItem()
        root_item = QTreeWidgetItem(root)
        root_item.setText(0, f"🏠 {getattr(z, 'label', zone_id)}")
        f = root_item.font(0)
        f.setBold(True)
        root_item.setFont(0, f)
        root_item.setForeground(0, QBrush(QColor("#6a1b9a")))
        self._flatten(z, root_item)
        root_item.setExpanded(True)
        self._item_meta[id(root_item)] = ("ZONE", zone_id)

    def _show_generic(self, data, title="Data"):
        self.setWindowTitle(title)
        self.clear()

        root = self.tree.invisibleRootItem()
        root_item = QTreeWidgetItem(root)
        root_item.setText(0, "Data")
        f = root_item.font(0)
        f.setBold(True)
        root_item.setFont(0, f)

        self._flatten(data, root_item)
        root_item.setExpanded(True)

    # =========================================================
    # HELPERS
    # =========================================================

    def _select_and_scroll(self, item: QTreeWidgetItem):
        self._suppress_signals = True
        try:
            self._clear_highlights()

            parent = item.parent()
            while parent is not None:
                parent.setExpanded(True)
                parent = parent.parent()

            self.tree.setCurrentItem(item)
            item.setSelected(True)
            self.tree.scrollToItem(item, QTreeWidget.ScrollHint.PositionAtCenter)
            self._highlight_item(item)
        finally:
            self._suppress_signals = False

    def _is_plane_object(self, obj) -> bool:
        if obj is None:
            return False
        return (
            hasattr(obj, "edges")
            or hasattr(obj, "properties")
            or hasattr(obj, "zones")
        )

    def _is_multi_plane_dict(self, obj) -> bool:
        """dict[str, WindPlane] mi? (en az bir value plane olmalı)"""
        if not isinstance(obj, dict) or not obj:
            return False
        # Edge dict'i değil, plane dict'i
        if any(self._is_edge_object(v) for v in obj.values()):
            return False
        # En az bir value plane olmalı
        return any(self._is_plane_object(v) for v in obj.values())

    def _is_edge_object(self, obj) -> bool:
        if not is_dataclass(obj) or isinstance(obj, type):
            return False
        field_names = {f.name for f in fields(obj)}
        return {"index", "p1", "p2"}.issubset(field_names)

    @staticmethod
    def _looks_like_edge_id(name) -> bool:
        if not isinstance(name, str):
            return False
        if "." not in name:
            return False
        head, _, tail = name.rpartition(".")
        return bool(head) and tail.isdigit()

    def _register_as_edge(self, item: QTreeWidgetItem, edge_id: str):
        f = item.font(0)
        f.setBold(True)
        item.setFont(0, f)
        item.setForeground(0, QBrush(QColor("#1565c0")))
        item.setForeground(1, QBrush(QColor("#1565c0")))
        item.setToolTip(0, f"Edge: {edge_id}")
        self._item_meta[id(item)] = ("EDGE", edge_id)
        self._edge_items_map[edge_id] = item

    def _highlight_item(self, item: QTreeWidgetItem):
        for col in (0, 1):
            item.setBackground(col, QBrush(QColor("#fff3cd")))

    def _clear_highlights(self):
        for item in self._edge_items_map.values():
            self._reset_item_bg(item)
        for item in self._zone_items_map.values():
            self._reset_item_bg(item)
        for item in self._surface_items_map.values():
            self._reset_item_bg(item)

    @staticmethod
    def _reset_item_bg(item: QTreeWidgetItem):
        for col in (0, 1):
            item.setBackground(col, QBrush(Qt.transparent))
        for i in range(item.childCount()):
            child = item.child(i)
            for col in (0, 1):
                child.setBackground(col, QBrush(Qt.transparent))

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
# CONVENIENCE
# =============================================================

def show_data(data, view3d=None, title="Data", parent=None, polygon_name=None):
    dlg = DataDialog(view3d, parent=parent, polygon_name=polygon_name)
    dlg.set_data(data, title=title, polygon_name=polygon_name)
    dlg.show()
    return dlg