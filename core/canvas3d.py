# canvas3d.py

import faulthandler
faulthandler.enable()

import math
import traceback

import numpy as np

from PySide6.QtCore import (
    QBuffer, QByteArray, QIODevice, QRectF, Qt, QPointF, Signal,
)
from PySide6.QtGui import (
    QAction, QColor, QImage, QKeySequence, QPainter, QPainterPath,
    QPen, QPixmap, QPolygonF, QShortcut,
)
from PySide6.QtWidgets import (
    QApplication, QGraphicsPathItem, QGraphicsScene, QGraphicsView,
    QMenu, QMessageBox,
)

from core.domains import (
    AxisItem, Camera3D, EdgeItem, FrameItem, PointItem, PolygonItem,
    ShowObjectsDialog, Vec3, ZoneItem,
)
from ui.data_dock import DataDock


import logging



# =============================================================
# RENK YARDIMCILARI
# =============================================================

def _lerp_color(c1: QColor, c2: QColor, t: float) -> QColor:
    """t=0 → c1, t=1 → c2."""
    t = max(0.0, min(1.0, t))
    return QColor(
        int(c1.red()   + (c2.red()   - c1.red())   * t),
        int(c1.green() + (c2.green() - c1.green()) * t),
        int(c1.blue()  + (c2.blue()  - c1.blue())  * t),
    )


_BLUES_STOPS = [
    (0.00, QColor("#f7fbff")),
    (0.25, QColor("#c6dbef")),
    (0.50, QColor("#6baed6")),
    (0.75, QColor("#2171b5")),
    (1.00, QColor("#08306b")),
]

_REDS_STOPS = [
    (0.00, QColor("#fff5f0")),
    (0.25, QColor("#fcbba1")),
    (0.50, QColor("#fb6a4a")),
    (0.75, QColor("#cb181d")),
    (1.00, QColor("#67000d")),
]


def _colormap_lookup(stops, t: float) -> QColor:
    t = max(0.0, min(1.0, t))
    for i in range(len(stops) - 1):
        p0, c0 = stops[i]
        p1, c1 = stops[i + 1]
        if p0 <= t <= p1:
            local_t = 0.0 if p1 == p0 else (t - p0) / (p1 - p0)
            return _lerp_color(c0, c1, local_t)
    return stops[-1][1]


# =============================================================
# VIEW3D
# =============================================================

class View3D(QGraphicsView):

    # --- Sinyaller ---
    element_selected         = Signal(str, str, object)
    multi_selection_changed  = Signal(list)
    delete_requested         = Signal()
    polygon_created          = Signal(list)
    point_selected_for_operation = Signal(str)
    context_menu_action      = Signal(str, object)
    properties_requested     = Signal(str, str)

    # =========================================================
    # INIT
    # =========================================================

    def __init__(self, parent=None):
        super().__init__(parent)
        logging.debug("View3D: Initializing...")

        self.debug_active = False

        # --- Kısayollar ---
        self.shortcut = QShortcut(QKeySequence("Ctrl+L"), self)
        self.shortcut.activated.connect(self.toggle_debug)

        self.axis_shortcut = QShortcut(QKeySequence("Ctrl+Shift+A"), self)
        self.axis_shortcut.activated.connect(self.toggle_axes)

        self.label_shortcut = QShortcut(QKeySequence("Ctrl+Shift+L"), self)
        self.label_shortcut.activated.connect(self.toggle_labels)

        # --- Sahne ---
        self.scene = QGraphicsScene()
        self.setScene(self.scene)

        self.camera = Camera3D()
        
        # --- Veri modeli ---
        self.points   = {}
        self.polygons = {}
        self.lines    = []
        self.frames   = {}
        self.zones    = {}

        # --- Görsel öğeler ---
        self.point_items        = {}
        self.polygon_items      = {}
        self.edge_items         = {}
        self.frame_items        = {}
        self.zone_items         = {}
        self.graphics_line_items = []

        # Poligon kenarları (edge modu için)
        self.polygon_edge_items = {}

        # --- Durum ---
        self.show_labels = True
        self._visibility_states = {}
        self._color_overrides   = {}

        # Çoklu seçim
        self.multi_selection_mode = False
        self.selected_items = {
            "POINT": [], "POLYGON": [], "EDGE": [], "FRAME": [], "LINE": [],
        }
        self.selected_type = None
        self.selected_id   = None

        # Modlar
        self.edge_selection_mode = False
        self.draw_mode           = False
        self.point_selection_mode = False

        self.creation_sequence = []
        self.selected_points_for_operation = []

        # Kamera kontrolü
        self.center_x = 0
        self.center_y = 0
        self.middle_pan      = False
        self.right_orbit     = False
        self.last_viewport_pos = None

        # Eksen
        self.axis_item = None
        self.axis_length = 40
        self.show_axes = True

        # Context menu durumu
        self.context_menu_pos = QPointF()
        self.context_menu_item_type = None
        self.context_menu_item_id   = None

        # Objects dialog
        self.show_objects_dialog = None

        # --- Önizleme yolu (draw mode) ---
        self.preview_path_item = QGraphicsPathItem()
        pen = QPen(QColor("#4caf50"), 2, Qt.PenStyle.DashLine)
        self.preview_path_item.setPen(pen)
        self.preview_path_item.setZValue(300)
        self.scene.addItem(self.preview_path_item)

        # --- Görsel ayarlar ---
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setBackgroundBrush(QColor("#f7f8fa"))
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.NoAnchor)

        # --- İç sinyal bağlantıları ---
        self.context_menu_action.connect(self.on_context_menu_action)
        self.delete_requested.connect(self.delete_selected_elements)
        self.polygon_created.connect(self._on_polygon_created)

        logging.debug("View3D: Initialization complete")

    # =========================================================
    # GENEL GÖRÜNÜM AYARLARI
    # =========================================================

    def toggle_labels(self):
        """Tüm öğe etiketlerini aç/kapat."""
        self.show_labels = not self.show_labels
        logging.info(f"View3D: Labels visibility: {self.show_labels}")

        for store in (self.point_items, self.polygon_items, self.zone_items,
                      self.frame_items, self.edge_items):
            for item in store.values():
                if hasattr(item, "set_label_visible"):
                    item.set_label_visible(self.show_labels)

    def toggle_debug(self):
        """Debug loglarını aç/kapat."""
        self.debug_active = not self.debug_active
        if self.debug_active:
            logging.getLogger().setLevel(logging.DEBUG)
            print("🐛 Debug Logları: AÇIK")
        else:
            logging.getLogger().setLevel(logging.INFO)
            print("🐛 Debug Logları: KAPALI")

    def toggle_axes(self):
        """Eksenleri aç/kapat."""
        self.show_axes = not self.show_axes
        logging.info(f"View3D: Axes visibility: {self.show_axes}")
        self.draw_scene()

    # =========================================================
    # VERİ YÜKLEME
    # =========================================================

    def set_data(self, points, polygons=None, lines=None,
                 frames=None, zones=None):
        logging.info(
            f"View3D: set_data — Points: {len(points) if points else 0}, "
            f"Polygons: {len(polygons) if polygons else 0}, "
            f"Lines: {len(lines) if lines else 0}, "
            f"Frames: {len(frames) if frames else 0}, "
            f"Zones: {len(zones) if zones else 0}"
        )

        self.points   = points   if points   is not None else {}
        self.polygons = polygons if polygons is not None else {}
        self.lines    = lines    if lines    is not None else []
        self.frames   = frames   if frames   is not None else {}
        self.zones    = zones    if zones    is not None else {}

        self._visibility_states.clear()
        self.rebuild()

    def rebuild(self):
        """Sahneyi sıfırdan kur."""
        logging.debug("View3D: Rebuilding scene...")

        self._clear_all_items()

        for name in self.points:
            item = PointItem(name)
            item.clicked.connect(lambda n=name: self.on_point_clicked(n))
            item.context_menu_requested.connect(
                lambda n=name: self.show_context_menu("POINT", n)
            )
            item.visibility_changed.connect(
                lambda n, v: self._on_visibility_changed("POINT", n, v)
            )
            self.point_items[name] = item
            self.scene.addItem(item)

        # Önizleme yolu yenile
        self._reset_preview_path()

        self.draw_scene()
        logging.debug(
            f"View3D: Rebuild complete — Points: {len(self.point_items)}, "
            f"Polygons: {len(self.polygon_items)}, "
            f"Lines: {len(self.graphics_line_items)}, "
            f"Frames: {len(self.frame_items)}"
        )

    def _clear_all_items(self):
        """Tüm grafik öğelerini sahneden ve sözlüklerden temizle."""
        all_items = (
            list(self.point_items.values())
            + list(self.polygon_items.values())
            + list(self.edge_items.values())
            + list(self.frame_items.values())
            + list(self.zone_items.values())
            + self.graphics_line_items
        )
        for item in all_items:
            try:
                if item and item.scene():
                    self.scene.removeItem(item)
            except RuntimeError:
                pass

        self.point_items.clear()
        self.polygon_items.clear()
        self.edge_items.clear()
        self.frame_items.clear()
        self.zone_items.clear()
        self.graphics_line_items.clear()

    def _reset_preview_path(self):
        """Önizleme yolunu yeniden oluştur."""
        if self.preview_path_item and self.preview_path_item.scene():
            self.scene.removeItem(self.preview_path_item)

        self.preview_path_item = QGraphicsPathItem()
        pen = QPen(QColor("#4caf50"), 2, Qt.PenStyle.DashLine)
        self.preview_path_item.setPen(pen)
        self.preview_path_item.setZValue(300)
        self.scene.addItem(self.preview_path_item)

    # =========================================================
    # GÖRÜNÜRLÜK
    # =========================================================

    def _get_visibility_key(self, elem_type, item_id):
        return f"{elem_type}:{item_id}"

    def _get_visibility(self, elem_type, item_id):
        key = self._get_visibility_key(elem_type, item_id)
        return self._visibility_states.get(key, True)

    def _set_visibility(self, elem_type, item_id, visible):
        key = self._get_visibility_key(elem_type, item_id)
        self._visibility_states[key] = visible
        self._apply_visibility_to_item(elem_type, item_id, visible)

    def _apply_visibility_to_item(self, elem_type, item_id, visible):
        store = {
            "POINT":   self.point_items,
            "POLYGON": self.polygon_items,
            "FRAME":   self.frame_items,
            "ZONE":    self.zone_items,
            "EDGE":    self.edge_items,
        }.get(elem_type)
        if store and item_id in store:
            store[item_id].setVisible(visible)
            store[item_id]._is_visible = visible

    def _on_visibility_changed(self, elem_type, item_id, visible):
        key = self._get_visibility_key(elem_type, item_id)
        self._visibility_states[key] = visible

    def toggle_visibility(self, elem_type, item_id):
        current = self._get_visibility(elem_type, item_id)
        self._set_visibility(elem_type, item_id, not current)
        if self.show_objects_dialog and self.show_objects_dialog.isVisible():
            self.show_objects_dialog.update_tree()

    def set_visibility(self, elem_type, item_id, visible):
        self._set_visibility(elem_type, item_id, visible)
        if self.show_objects_dialog and self.show_objects_dialog.isVisible():
            self.show_objects_dialog.update_tree()

    def get_visibility(self, elem_type, item_id):
        return self._get_visibility(elem_type, item_id)

    def clear_visibility_states(self):
        self._visibility_states.clear()

    # =========================================================
    # RENK
    # =========================================================

    def _color_key(self, elem_type, elem_id):
        return f"{elem_type}:{elem_id}"

    def set_element_color(self, elem_type, elem_id, color):
        c = QColor(color)
        self._color_overrides[self._color_key(elem_type, elem_id)] = c
        self._apply_color_to_item(elem_type, elem_id, c)
        if self.show_objects_dialog and self.show_objects_dialog.isVisible():
            self.show_objects_dialog.update_tree()

    def get_element_color(self, elem_type, elem_id):
        return self._color_overrides.get(self._color_key(elem_type, elem_id))

    def clear_element_color(self, elem_type, elem_id):
        self._color_overrides.pop(self._color_key(elem_type, elem_id), None)
        self.draw_scene()

    def _apply_color_to_item(self, elem_type, elem_id, color):
        store = {
            "POINT":   self.point_items,
            "POLYGON": self.polygon_items,
            "FRAME":   self.frame_items,
            "EDGE":    self.edge_items,
        }.get(elem_type)
        if store and elem_id in store:
            store[elem_id].set_color(color)
        # LINE: bir sonraki draw_scene'de pen rengine uygulanır

    def set_selected_items_color(self, color):
        if self.multi_selection_mode:
            for elem_type, ids in self.get_multi_selected().items():
                for elem_id in ids:
                    self.set_element_color(elem_type, elem_id, color)
        elif self.selected_type and self.selected_id:
            self.set_element_color(self.selected_type, self.selected_id, color)

    # =========================================================
    # PROJEKSİYON
    # =========================================================

    def screen_position(self, p: Vec3):
        x, y, depth = self.camera.project(p)
        scale = 40 * self.camera.zoom
        return (
            QPointF(x * scale + self.center_x, -y * scale + self.center_y),
            depth,
        )

    def _inverse_project(self, x2, y2, z=0.0):
        """Kamera projeksiyonunun tersini al (z düzleminde)."""
        yaw   = self.camera.yaw
        pitch = self.camera.pitch

        x1 = -x2
        sp = math.sin(pitch)
        cp = math.cos(pitch)
        y1 = 0.0 if abs(sp) < 1e-6 else (z * cp - y2) / sp

        sy  = math.sin(yaw)
        cy_ = math.cos(yaw)

        px = x1 * sy - y1 * cy_
        py = x1 * cy_ + y1 * sy
        return Vec3(px, py, z)

    # =========================================================
    # ÖNİZLEME (draw mode)
    # =========================================================

    def update_preview_path(self):
        if not self.creation_sequence:
            self.preview_path_item.setPath(QPainterPath())
            return

        path = QPainterPath()
        first = self.creation_sequence[0]
        if first in self.point_items:
            path.moveTo(self.point_items[first].pos())

        for pt_name in self.creation_sequence[1:]:
            if pt_name in self.point_items:
                path.lineTo(self.point_items[pt_name].pos())

        self.preview_path_item.setPath(path)

    # =========================================================
    # ANA ÇİZİM
    # =========================================================

    def draw_scene(self):
        logging.debug("View3D: Drawing scene...")
        try:
            # Sahneden mevcut öğeleri kaldır (noktalar hariç — onlar kalıcı)
            for item in (
                list(self.polygon_items.values())
                + list(self.zone_items.values())
                + list(self.edge_items.values())
                + list(self.frame_items.values())
                + self.graphics_line_items
            ):
                try:
                    if item and item.scene():
                        self.scene.removeItem(item)
                except RuntimeError:
                    pass

            self.polygon_items.clear()
            self.edge_items.clear()
            self.frame_items.clear()
            self.zone_items.clear()
            self.graphics_line_items.clear()

            # Sırayla çiz
            self._update_point_positions()
            self._draw_polygons()
            self._draw_zones()
            self._compute_zone_colors_by_cpe10()
            self._draw_frames()
            self._draw_lines()

            if self.edge_selection_mode:
                self._draw_edges()

            self._draw_axis()
            self.update_preview_path()

            self.scene.invalidate()
            self.viewport().update()
            logging.debug("View3D: Scene drawing complete")
        except Exception as e:
            logging.error(f"draw_scene error: {e}")
            logging.error(traceback.format_exc())

    def _update_point_positions(self):
        for name, coords in self.points.items():
            if name not in self.point_items:
                continue
            item = self.point_items[name]
            pos, depth = self.screen_position(Vec3(*coords))
            item.setPos(pos)
            item.setZValue(200 + depth)

            visible = self._get_visibility("POINT", name)
            item.setVisible(visible)
            item._is_visible = visible

            override = self._color_overrides.get(self._color_key("POINT", name))
            if override:
                item.set_color(override)

            if hasattr(item, "set_label_visible"):
                item.set_label_visible(self.show_labels)
                item._label_item.setZValue(200 + depth + 0.5)

    def _draw_polygons(self):
        for poly_name, pts in self.polygons.items():
            poly = QPolygonF()
            total_depth = 0
            valid = True

            for p_name in pts:
                if p_name not in self.points:
                    valid = False
                    break
                pos, depth = self.screen_position(Vec3(*self.points[p_name]))
                poly.append(pos)
                total_depth += depth

            if not (valid and len(poly) >= 3):
                continue

            poly_item = PolygonItem(poly_name, pts)
            poly_item.set_polygon(poly, total_depth / len(pts))
            poly_item.clicked.connect(self.on_polygon_clicked)
            poly_item.context_menu_requested.connect(
                lambda n=poly_name: self.show_context_menu("POLYGON", n)
            )
            poly_item.visibility_changed.connect(
                lambda n, v: self._on_visibility_changed("POLYGON", n, v)
            )

            if self._is_item_selected("POLYGON", poly_name):
                poly_item.set_selected_state(True)

            visible = self._get_visibility("POLYGON", poly_name)
            poly_item.setVisible(visible)
            poly_item._is_visible = visible

            override = self._color_overrides.get(
                self._color_key("POLYGON", poly_name)
            )
            if override:
                poly_item.set_color(override)

            if hasattr(poly_item, "set_label_visible"):
                poly_item.set_label_visible(self.show_labels)
                poly_item._label_item.setZValue(200 + depth + 0.5)

            self.polygon_items[poly_name] = poly_item
            self.scene.addItem(poly_item)

    def _draw_zones(self):
        for item in list(self.zone_items.values()):
            try:
                if item and item.scene():
                    self.scene.removeItem(item)
            except RuntimeError:
                pass
        self.zone_items.clear()
        self.scene.invalidate()

        for zone_key, zone_list in self.zones.items():
            if not isinstance(zone_list, (list, tuple)):
                zone_list = [zone_list]

            for idx, zone in enumerate(zone_list):
                item_key = (
                    f"{zone_key}[{idx}]" if len(zone_list) > 1 else zone_key
                )

                try:
                    coords = np.asarray(zone.coords, dtype=float)
                    if coords.ndim != 2 or coords.shape[1] < 3 or len(coords) < 2:
                        logging.warning(
                            f"Zone {item_key}: geçersiz coords {coords.shape}"
                        )
                        continue
                except Exception as e:
                    logging.warning(f"Zone {item_key}: coords okunamadı - {e}")
                    continue

                zone_item = ZoneItem(item_key, zone, self)
                zone_item.update_screen_points()

                zone_item.clicked.connect(self.on_zone_clicked)
                zone_item.context_menu_requested.connect(
                    lambda n=item_key: self.show_context_menu("ZONE", n)
                )
                zone_item.visibility_changed.connect(
                    lambda n, v: self._on_visibility_changed("ZONE", n, v)
                )

                if self._is_item_selected("ZONE", item_key):
                    zone_item.set_selected_state(True)

                visible = self._get_visibility("ZONE", item_key)
                zone_item.setVisible(visible)
                zone_item._is_visible = visible

                override = self._color_overrides.get(
                    self._color_key("ZONE", item_key)
                )
                if override:
                    zone_item.set_color(override)

                if hasattr(zone_item, "set_label_visible"):
                    zone_item.set_label_visible(self.show_labels)
                    zone_item._label_item.setZValue(200 + zone_item.depth + 0.5)

                self.zone_items[item_key] = zone_item
                self.scene.addItem(zone_item)

    def _draw_axis(self):
        if self.axis_item:
            try:
                self.scene.removeItem(self.axis_item)
            except Exception:
                logging.error(traceback.format_exc())
            self.axis_item = None

        if self.show_axes:
            self.axis_item = AxisItem(self, self.axis_length)
            self.axis_item.setPos(0, 0)
            self.scene.addItem(self.axis_item)

    def _draw_frames(self):
        for frame_name, (p1_name, p2_name) in self.frames.items():
            if p1_name not in self.points or p2_name not in self.points:
                continue

            pos1, depth1 = self.screen_position(Vec3(*self.points[p1_name]))
            pos2, depth2 = self.screen_position(Vec3(*self.points[p2_name]))

            frame_item = FrameItem(frame_name, p1_name, p2_name)
            frame_item.set_line(pos1, pos2)
            frame_item.clicked.connect(self.on_frame_clicked)
            frame_item.context_menu_requested.connect(
                lambda n=frame_name: self.show_context_menu("FRAME", n)
            )
            frame_item.visibility_changed.connect(
                lambda n, v: self._on_visibility_changed("FRAME", n, v)
            )

            avg_depth = (depth1 + depth2) / 2.0
            frame_item.setZValue(175 + avg_depth)

            if self._is_item_selected("FRAME", frame_name):
                frame_item.set_selected_state(True)

            visible = self._get_visibility("FRAME", frame_name)
            frame_item.setVisible(visible)
            frame_item._is_visible = visible

            override = self._color_overrides.get(
                self._color_key("FRAME", frame_name)
            )
            if override:
                frame_item.set_color(override)

            if hasattr(frame_item, "set_label_visible"):
                frame_item.set_label_visible(self.show_labels)
                depth = max(depth1, depth2)
                frame_item._label_item.setZValue(200 + depth + 0.5)

            self.frame_items[frame_name] = frame_item
            self.scene.addItem(frame_item)

    def _draw_lines(self):
        for i_, point_list in enumerate(self.lines):
            line_name = f"line_{i_}"

            if not self._get_visibility("LINE", line_name):
                continue

            screen_points = []
            depths = []

            for p in point_list:
                coords = self.points.get(p) if isinstance(p, str) else p
                if coords is None:
                    continue
                try:
                    flat = np.asarray(coords, dtype=float).ravel()
                    if flat.size < 3:
                        continue
                    x, y, z = float(flat[0]), float(flat[1]), float(flat[2])
                except (ValueError, TypeError):
                    continue

                pos, depth = self.screen_position(Vec3(x, y, z))
                screen_points.append(pos)
                depths.append(depth)

            if len(screen_points) < 2:
                continue

            override = self._color_overrides.get(
                self._color_key("LINE", line_name)
            )
            pen = QPen(override if override else QColor("#2c3e50"), 1.5)
            pen.setCosmetic(True)

            path = QPainterPath()
            path.moveTo(screen_points[0])
            for pt in screen_points[1:]:
                path.lineTo(pt)

            graphics_item = QGraphicsPathItem(path)
            graphics_item.setPen(pen)
            graphics_item.setBrush(Qt.BrushStyle.NoBrush)

            avg_depth = sum(depths) / len(depths) if depths else 0
            graphics_item.setZValue(125 + avg_depth)

            graphics_item.setFlag(
                QGraphicsPathItem.GraphicsItemFlag.ItemIsSelectable, False
            )
            graphics_item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            graphics_item.setEnabled(False)

            self.graphics_line_items.append(graphics_item)
            self.scene.addItem(graphics_item)

    def _draw_edges(self):
        edges = self._get_visible_polygon_edges()

        for edge_key, edge_info in edges.items():
            p1_n         = edge_info["p1"]
            p2_n         = edge_info["p2"]
            display_name = edge_info["display_name"]
            parent_polys = edge_info["polygons"]
            edge_index   = edge_info.get("edge_index")

            if p1_n not in self.points or p2_n not in self.points:
                continue

            pos1, _ = self.screen_position(Vec3(*self.points[p1_n]))
            pos2, _ = self.screen_position(Vec3(*self.points[p2_n]))

            if edge_index is not None:
                edge_id = f"{parent_polys[0]}.{edge_index}"
            elif isinstance(edge_key, tuple):
                edge_id = f"{edge_key[0]}-{edge_key[1]}"
            else:
                edge_id = str(edge_key)

            edge_item = EdgeItem(edge_id, p1_n, p2_n, parent_polys)
            edge_item.set_line(pos1, pos2)
            edge_item.clicked.connect(
                lambda e=edge_id, pp=parent_polys: self.on_edge_clicked(e, pp)
            )
            edge_item.context_menu_requested.connect(
                lambda n=edge_id: self.show_context_menu("EDGE", n)
            )
            edge_item.visibility_changed.connect(
                lambda n, v: self._on_visibility_changed("EDGE", n, v)
            )

            if hasattr(edge_item, "set_display_name"):
                edge_item.set_display_name(display_name)

            if self._is_item_selected("EDGE", edge_id):
                edge_item.set_selected_state(True)

            visible = self._get_visibility("EDGE", edge_id)
            edge_item.setVisible(visible)
            edge_item._is_visible = visible

            if hasattr(edge_item, "set_label_visible"):
                edge_item.set_label_visible(self.show_labels)

            self.edge_items[edge_id] = edge_item
            self.scene.addItem(edge_item)

    def _compute_zone_colors_by_cpe10(self):
        """Zone'ları cpe10 değerine göre renklendir."""
        if not self.zones:
            return

        entries = []
        for zone_key, zone_list in self.zones.items():
            if not isinstance(zone_list, (list, tuple)):
                zone_list = [zone_list]
            for idx, zone in enumerate(zone_list):
                item_key = (
                    f"{zone_key}[{idx}]" if len(zone_list) > 1 else zone_key
                )
                cpe = getattr(zone, "cpe10", None)
                if cpe is None:
                    continue
                if isinstance(cpe, tuple):
                    cpe = cpe[0]
                try:
                    cpe = float(cpe)
                except (TypeError, ValueError):
                    continue
                entries.append((item_key, cpe))

        if not entries:
            return

        negs = [v for _, v in entries if v < 0]
        poss = [v for _, v in entries if v >= 0]

        min_neg_abs = abs(min(negs)) if negs else 0.0
        max_pos     = max(poss) if poss else 0.0

        for item_key, cpe in entries:
            if cpe < 0:
                t = abs(cpe) / min_neg_abs if min_neg_abs > 0 else 0.0
                color = _colormap_lookup(_BLUES_STOPS, t)
            else:
                t = cpe / max_pos if max_pos > 0 else 0.0
                color = _colormap_lookup(_REDS_STOPS, t)

            fill = QColor(color)
            fill.setAlpha(220)

            item = self.zone_items.get(item_key)
            if item is not None:
                item.set_color(fill)

    # =========================================================
    # SEÇİM YARDIMCILARI
    # =========================================================

    def _is_item_selected(self, item_type, item_id):
        if self.selected_type == item_type and self.selected_id == item_id:
            return True
        if (self.multi_selection_mode
                and item_id in self.selected_items.get(item_type, [])):
            return True
        return False

    def _get_modifiers(self):
        return QApplication.queryKeyboardModifiers()

    def _has_modifier(self, modifier):
        return bool(self._get_modifiers() & modifier)

    def select_element(self, elem_type, elem_id):
        logging.info(f"View3D: select_element - Type: {elem_type}, ID: {elem_id}")
        self.selected_type = elem_type
        self.selected_id = elem_id
        self.multi_selection_mode = False
        self._update_selection_states()

    def toggle_multi_selection(self, elem_type, elem_id):
        if not self.multi_selection_mode:
            self.multi_selection_mode = True
            if self.selected_type and self.selected_id:
                self.selected_items[self.selected_type].append(self.selected_id)
                self.selected_type = None
                self.selected_id = None

        if elem_type in self.selected_items:
            items = self.selected_items[elem_type]
            if elem_id in items:
                items.remove(elem_id)
            else:
                items.append(elem_id)
            self._update_selection_states()
            self._emit_multi_selection()

    def _update_selection_states(self):
        for item_dict, item_type in (
            (self.point_items,   "POINT"),
            (self.polygon_items, "POLYGON"),
            (self.zone_items,    "ZONE"),
            (self.edge_items,    "EDGE"),
            (self.frame_items,   "FRAME"),
        ):
            for item_id, item in item_dict.items():
                try:
                    is_selected = self._is_item_selected(item_type, item_id)
                    if hasattr(item, "set_selected_state"):
                        item.set_selected_state(is_selected)
                except RuntimeError:
                    continue

    def _emit_multi_selection(self):
        all_selected = []
        for elem_type, ids in self.selected_items.items():
            for elem_id in ids:
                all_selected.append((elem_type, elem_id))
        self.multi_selection_changed.emit(all_selected)

    def clear_selection(self):
        logging.debug("View3D: Clearing selection")
        self.selected_type = None
        self.selected_id = None
        self.multi_selection_mode = False

        for key in self.selected_items:
            self.selected_items[key].clear()

        self.creation_sequence.clear()
        self.update_preview_path()

        for item_dict in (self.point_items, self.polygon_items, self.zone_items,
                          self.edge_items, self.frame_items):
            for item in item_dict.values():
                item.set_selected_state(False)

        self.multi_selection_changed.emit([])
        self.element_selected.emit(None, None, None)

    def cancel_modes(self):
        logging.debug("View3D: Cancelling active modes")
        self.edge_selection_mode = False
        self.point_selection_mode = False
        self.multi_selection_mode = False
        self.creation_sequence.clear()
        self.polygon_edge_items.clear()
        self.update_preview_path()
        self.draw_scene()

    def get_multi_selected(self):
        return {
            elem_type: list(ids)
            for elem_type, ids in self.selected_items.items() if ids
        }

    def get_selected_count(self):
        return sum(len(ids) for ids in self.selected_items.values())

    def has_selection(self):
        return (
            self.selected_type is not None
            or self.selected_id is not None
            or any(self.selected_items.values())
        )

    def select_all(self):
        self.multi_selection_mode = True
        self.selected_type = None
        self.selected_id = None

        for item_dict, item_type in (
            (self.point_items,   "POINT"),
            (self.polygon_items, "POLYGON"),
            (self.zone_items,    "ZONE"),
            (self.edge_items,    "EDGE"),
            (self.frame_items,   "FRAME"),
        ):
            for name in item_dict.keys():
                if name not in self.selected_items[item_type]:
                    self.selected_items[item_type].append(name)

        self._update_selection_states()
        self._emit_multi_selection()

    # =========================================================
    # TIKLAMA HANDLER'LARI
    # =========================================================

    def on_point_clicked(self, name):
        if self.point_selection_mode:
            if name not in self.selected_points_for_operation:
                self.selected_points_for_operation.append(name)
                self.point_selected_for_operation.emit(name)
                if name in self.point_items:
                    self.point_items[name].set_selected_state(True)
            return

        if self.draw_mode:
            if (len(self.creation_sequence) >= 3
                    and name == self.creation_sequence[0]):
                self.polygon_created.emit(list(self.creation_sequence))
                self.creation_sequence.clear()
                self.update_preview_path()
                return

            if name not in self.creation_sequence:
                self.creation_sequence.append(name)
                self.update_preview_path()

            self.element_selected.emit("DRAWING", name, self.creation_sequence)
            return

        if self._has_modifier(Qt.KeyboardModifier.ControlModifier):
            self.toggle_multi_selection("POINT", name)
        else:
            self.select_element("POINT", name)
            self.element_selected.emit("POINT", name, None)

    def on_polygon_clicked(self, name):
        if self.edge_selection_mode or self.draw_mode:
            return

        if self._has_modifier(Qt.KeyboardModifier.ControlModifier):
            self.toggle_multi_selection("POLYGON", name)
        else:
            self.select_element("POLYGON", name)
            self.element_selected.emit("POLYGON", name, None)
            self._show_polygon_edges(name)

    def on_zone_clicked(self, name):
        if self.draw_mode or self.edge_selection_mode:
            return

        if self._has_modifier(Qt.KeyboardModifier.ControlModifier):
            self.toggle_multi_selection("ZONE", name)
        else:
            self.select_element("ZONE", name)
            zone_item = self.zone_items.get(name)
            payload = zone_item.zone if zone_item else None
            self.element_selected.emit("ZONE", name, payload)

    def on_frame_clicked(self, name):
        if self.draw_mode or self.edge_selection_mode:
            return

        if self._has_modifier(Qt.KeyboardModifier.ControlModifier):
            self.toggle_multi_selection("FRAME", name)
        else:
            self.select_element("FRAME", name)
            self.element_selected.emit("FRAME", name, None)

    def on_edge_clicked(self, edge_key, parent_polygons):
        if self.draw_mode:
            return

        self.select_element("EDGE", edge_key)
        self.element_selected.emit("EDGE", edge_key, parent_polygons)

        if parent_polygons and len(parent_polygons) > 1:
            self._show_edge_polygon_selection(edge_key, parent_polygons)
        elif parent_polygons and len(parent_polygons) == 1:
            self.element_selected.emit("EDGE", edge_key, {
                "polygon": parent_polygons[0],
                "type": "edge_in_polygon",
            })

    # =========================================================
    # POLİGON KENARLARI
    # =========================================================

    def _show_polygon_edges(self, polygon_id):
        if polygon_id not in self.polygons:
            logging.warning(f"_show_polygon_edges: {polygon_id} bulunamadı")
            return

        self.edge_selection_mode = True
        self.polygon_edge_items = self._get_visible_polygon_edges()

        logging.info(
            f"View3D: Polygon {polygon_id} kenarları gösteriliyor: "
            f"{list(self.polygon_edge_items.keys())}"
        )
        self.draw_scene()

    def _get_polygon_edges_with_indices(self, polygon_id):
        """
        Bir poligonun kenarlarını index'li olarak döndür.
        Dönüş: {"0": (p1, p2), "1": (p2, p3), ...}
        """
        edges = {}
        if polygon_id not in self.polygons:
            return edges

        pts = self.polygons[polygon_id]
        n = len(pts)
        for i in range(n):
            p1 = pts[i]
            p2 = pts[(i + 1) % n]
            edges[str(i)] = (p1, p2)
        return edges

    def _get_visible_polygon_edges(self):
        """
        Sadece seçili poligonun kenarlarını numaralı olarak döndür.
        Seçili poligon yoksa boş dict.
        """
        active_poly = None
        if self.selected_type == "POLYGON" and self.selected_id:
            active_poly = self.selected_id
        elif self.multi_selection_mode and "POLYGON" in self.selected_items:
            polys = self.selected_items["POLYGON"]
            if len(polys) == 1:
                active_poly = polys[0]

        if not active_poly or active_poly not in self.polygons:
            return {}

        result = {}
        for idx_str, (p1, p2) in self._get_polygon_edges_with_indices(active_poly).items():
            edge_key = tuple(sorted([p1, p2]))
            if edge_key not in result:
                result[edge_key] = {
                    "p1": p1,
                    "p2": p2,
                    "display_name": f"{active_poly}.{idx_str}",
                    "polygons": [active_poly],
                    "edge_index": idx_str,
                }

        self.polygon_edge_items = result
        return result

    def _show_edge_polygon_selection(self, edge_key, parent_polygons):
        """Kenarın ait olduğu poligonları seçmek için dialog gösterir."""
        from PySide6.QtWidgets import (
            QDialog, QDialogButtonBox, QLabel, QListWidget, QVBoxLayout,
        )

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Kenar Hangi Poligona Ait? - {edge_key}")
        dialog.setModal(True)
        dialog.resize(350, 250)

        layout = QVBoxLayout(dialog)

        info_label = QLabel(
            f"<b>{edge_key}</b> kenarı {len(parent_polygons)} poligona ait.<br>"
            "Hangi poligonun kenarını seçmek istiyorsunuz?"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        list_widget = QListWidget()
        for poly_name in parent_polygons:
            list_widget.addItem(poly_name)
        if list_widget.count() > 0:
            list_widget.setCurrentRow(0)
        layout.addWidget(list_widget)

        info_label2 = QLabel("Seçtiğiniz poligonun kenarı olarak işaretlenecektir.")
        info_label2.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(info_label2)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(
            lambda: self._confirm_edge_polygon(dialog, list_widget, edge_key)
        )
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        dialog.exec()

    def _confirm_edge_polygon(self, dialog, list_widget, edge_key):
        current_item = list_widget.currentItem()
        if current_item:
            poly_name = current_item.text()
            self.select_element("EDGE", edge_key)
            self.element_selected.emit("EDGE", edge_key, {
                "selected_polygon": poly_name,
                "all_polygons": [
                    list_widget.item(i).text()
                    for i in range(list_widget.count())
                ],
            })
            dialog.accept()

    # =========================================================
    # NOKTA SEÇİM MODU (işlem için)
    # =========================================================

    def start_point_selection(self):
        self.point_selection_mode = True
        self.selected_points_for_operation = []
        for item in self.point_items.values():
            item.set_selected_state(False)

    def stop_point_selection(self):
        self.point_selection_mode = False
        self.selected_points_for_operation = []
        for item in self.point_items.values():
            item.set_selected_state(False)

    def get_selected_points(self):
        return self.selected_points_for_operation.copy()

    # =========================================================
    # KAMERA
    # =========================================================

    def zoom_extents(self):
        logging.debug("View3D: Zoom to extents")

        all_points = {}

        for k, p in self.points.items():
            flat = np.asarray(p, dtype=float).ravel()
            if len(flat) >= 3:
                all_points[k] = (float(flat[0]), float(flat[1]), float(flat[2]))

        for i_, point_list in enumerate(self.lines):
            line_name = f"line_{i_}"
            for i, p in enumerate(point_list):
                if not isinstance(p, str):
                    flat = np.asarray(p, dtype=float).ravel()
                    if len(flat) >= 3:
                        all_points[f"{line_name}_{i}"] = (
                            float(flat[0]), float(flat[1]), float(flat[2])
                        )

        if not all_points:
            return

        pts_array = np.array(list(all_points.values()), dtype=float)
        xs, ys, zs = pts_array[:, 0], pts_array[:, 1], pts_array[:, 2]

        center_3d = Vec3(
            float((xs.min() + xs.max()) / 2.0),
            float((ys.min() + ys.max()) / 2.0),
            float((zs.min() + zs.max()) / 2.0),
        )

        proj_x, proj_y = [], []
        for p in all_points.values():
            x, y, _ = self.camera.project(Vec3(*p))
            proj_x.append(x)
            proj_y.append(y)

        dx = max(max(proj_x) - min(proj_x), 1.0)
        dy = max(max(proj_y) - min(proj_y), 1.0)
        vw = self.viewport().width() * 0.7
        vh = self.viewport().height() * 0.7

        self.camera.zoom = max(
            0.00001, min(1000.0, min(vw / (dx * 40), vh / (dy * 40)))
        )

        cx_proj, cy_proj, _ = self.camera.project(center_3d)
        self.center_x = (self.viewport().width() / 2.0) - (
            cx_proj * 40 * self.camera.zoom
        )
        self.center_y = (self.viewport().height() / 2.0) + (
            cy_proj * 40 * self.camera.zoom
        )

        self.draw_scene()

    def reset_view(self):
        self.camera.yaw   = math.radians(-55)
        self.camera.pitch = math.radians(30)
        self.camera.zoom  = 1.0
        self.center_x = 0
        self.center_y = 0
        self.draw_scene()

    # =========================================================
    # MOUSE OLAYLARI
    # =========================================================

    def mousePressEvent(self, event):
        pos = event.position().toPoint()
        modifiers = event.modifiers()

        item = self.itemAt(pos)
        if item == self.axis_item:
            return

        if event.button() == Qt.MouseButton.RightButton:
            self.context_menu_pos = QPointF(pos)
            if item is None:
                self.show_empty_context_menu()
                return
            super().mousePressEvent(event)
            return

        if (event.button() == Qt.MouseButton.MiddleButton
                and (modifiers & Qt.KeyboardModifier.ShiftModifier)):
            self.right_orbit = True
            self.last_viewport_pos = pos
            super().mousePressEvent(event)
            return

        if event.button() == Qt.MouseButton.MiddleButton:
            self.middle_pan = True
            self.last_viewport_pos = pos
            super().mousePressEvent(event)
            return

        if event.button() == Qt.MouseButton.LeftButton and item is None:
            if not self.point_selection_mode:
                self.clear_selection()
            super().mousePressEvent(event)
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()

        if self.right_orbit and self.last_viewport_pos:
            delta = pos - self.last_viewport_pos
            self.camera.rotate(delta.x(), delta.y())
            self.draw_scene()
            self.last_viewport_pos = pos
            super().mouseMoveEvent(event)
            return

        if self.middle_pan and self.last_viewport_pos:
            delta = pos - self.last_viewport_pos
            self.center_x += delta.x()
            self.center_y += delta.y()
            self.draw_scene()
            self.last_viewport_pos = pos
            super().mouseMoveEvent(event)
            return

        self.last_viewport_pos = pos
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.middle_pan = False
        self.right_orbit = False
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        factor = 1.15 if delta > 0 else 1 / 1.15
        self.camera.zoom = max(0.000001, min(10000, self.camera.zoom * factor))
        self.draw_scene()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.draw_scene()

    def keyPressEvent(self, event):
        key = event.key()
        modifiers = event.modifiers()

        if key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.delete_requested.emit()
        elif key == Qt.Key.Key_Home:
            self.zoom_extents()
        elif key == Qt.Key.Key_Escape:
            if self.has_selection():
                self.clear_selection()
            else:
                logging.debug("ikinci kez Esc basıldı")
                self.cancel_modes()
        elif key == Qt.Key.Key_A and (modifiers & Qt.KeyboardModifier.ControlModifier):
            self.select_all()
        elif key == Qt.Key.Key_D and (modifiers & Qt.KeyboardModifier.ControlModifier):
            self.draw_mode = not self.draw_mode
            if not self.draw_mode:
                self.creation_sequence.clear()
                self.update_preview_path()
        elif key == Qt.Key.Key_E and (modifiers & Qt.KeyboardModifier.ControlModifier):
            self.edge_selection_mode = not self.edge_selection_mode
            self.draw_scene()
        elif key == Qt.Key.Key_O and (modifiers & Qt.KeyboardModifier.ControlModifier):
            self.show_objects_dialog()
        elif key == Qt.Key.Key_P and (modifiers & Qt.KeyboardModifier.ControlModifier):
            print(self.polygon_items)
            print(self.polygons)

    # =========================================================
    # CONTEXT MENU
    # =========================================================

    def show_context_menu(self, item_type, item_id):
        self.context_menu_item_type = item_type
        self.context_menu_item_id = item_id

        menu = QMenu(self)
        self._add_general_menu_items(menu, item_type, item_id)
        menu.addSeparator()
        self._add_type_specific_menu_items(menu, item_type, item_id)
        menu.addSeparator()
        self._add_action_menu_items(menu, item_type, item_id)
        self._show_menu(menu)

    def show_empty_context_menu(self):
        menu = QMenu(self)

        new_point_action = QAction("New Point", menu)
        new_point_action.triggered.connect(
            lambda: self.context_menu_action.emit(
                "NEW_POINT", {"pos": self.context_menu_pos}
            )
        )
        menu.addAction(new_point_action)

        new_polygon_action = QAction("New Polygon", menu)
        new_polygon_action.triggered.connect(
            lambda: self.context_menu_action.emit("NEW_POLYGON", {})
        )
        menu.addAction(new_polygon_action)

        menu.addSeparator()

        view_menu = menu.addMenu("View")
        zoom_extents_action = QAction("Zoom Extents", view_menu)
        zoom_extents_action.triggered.connect(self.zoom_extents)
        view_menu.addAction(zoom_extents_action)

        reset_view_action = QAction("Reset View", view_menu)
        reset_view_action.triggered.connect(
            lambda: self.context_menu_action.emit("RESET_VIEW", {})
        )
        view_menu.addAction(reset_view_action)

        menu.addSeparator()
        self._add_mode_toggle_items(menu)
        menu.addSeparator()

        info_action = QAction("Scene Info", menu)
        info_action.triggered.connect(
            lambda: self.context_menu_action.emit("SCENE_INFO", {})
        )
        menu.addAction(info_action)

        show_objects_action = QAction("Show Objects Panel", menu)
        show_objects_action.triggered.connect(self._show_objects_dialog)
        menu.addAction(show_objects_action)

        labels_action = QAction("Toggle Labels", menu)
        labels_action.setCheckable(True)
        labels_action.setChecked(self.show_labels)
        labels_action.triggered.connect(self.toggle_labels)
        menu.addAction(labels_action)

        self._show_menu(menu)

    def _add_general_menu_items(self, menu, item_type, item_id):
        select_action = QAction("Select", menu)
        select_action.triggered.connect(
            lambda: self.context_menu_action.emit(
                "SELECT", {"type": item_type, "id": item_id}
            )
        )
        menu.addAction(select_action)

        if self.multi_selection_mode:
            toggle_action = QAction("Toggle Selection", menu)
            toggle_action.triggered.connect(
                lambda: self.context_menu_action.emit(
                    "TOGGLE", {"type": item_type, "id": item_id}
                )
            )
            menu.addAction(toggle_action)

        menu.addSeparator()

        visibility_action = QAction("Toggle Visibility", menu)
        visibility_action.triggered.connect(
            lambda: self.context_menu_action.emit(
                "TOGGLE_VISIBILITY", {"type": item_type, "id": item_id}
            )
        )
        menu.addAction(visibility_action)

    def _add_type_specific_menu_items(self, menu, item_type, item_id):
        handlers = {
            "POINT":   self._add_point_menu_items,
            "POLYGON": self._add_polygon_menu_items,
            "ZONE":    self._add_zone_menu_items,
            "EDGE":    self._add_edge_menu_items,
            "FRAME":   self._add_frame_menu_items,
        }
        handler = handlers.get(item_type)
        if handler:
            handler(menu, item_id)

    def _add_action_menu_items(self, menu, item_type, item_id):
        color_action = QAction("Renk Değiştir...", menu)
        color_action.triggered.connect(
            lambda: self.context_menu_action.emit(
                "CHANGE_COLOR", {"type": item_type, "id": item_id}
            )
        )
        menu.addAction(color_action)

        delete_action = QAction("Delete", menu)
        delete_action.triggered.connect(
            lambda: self.context_menu_action.emit(
                "DELETE", {"type": item_type, "id": item_id}
            )
        )
        menu.addAction(delete_action)

        properties_action = QAction("Properties...", menu)
        properties_action.triggered.connect(
            lambda: self.context_menu_action.emit(
                "PROPERTIES", {"type": item_type, "id": item_id}
            )
        )
        menu.addAction(properties_action)

    def _add_mode_toggle_items(self, menu):
        draw_mode_action = QAction("Toggle Draw Mode", menu)
        draw_mode_action.setCheckable(True)
        draw_mode_action.setChecked(self.draw_mode)
        draw_mode_action.triggered.connect(
            lambda: self.context_menu_action.emit("TOGGLE_DRAW_MODE", {})
        )
        menu.addAction(draw_mode_action)

        edge_mode_action = QAction("Toggle Edge Mode", menu)
        edge_mode_action.setCheckable(True)
        edge_mode_action.setChecked(self.edge_selection_mode)
        edge_mode_action.triggered.connect(
            lambda: self.context_menu_action.emit("TOGGLE_EDGE_MODE", {})
        )
        menu.addAction(edge_mode_action)

    def _add_point_menu_items(self, menu, point_id):
        edit_action = QAction("Edit Coordinates", menu)
        edit_action.triggered.connect(
            lambda: self.context_menu_action.emit("EDIT_POINT", {"id": point_id})
        )
        menu.addAction(edit_action)

        if point_id in self.points:
            coords = self.points[point_id]
            info_action = QAction(
                f"Position: ({coords[0]:.2f}, {coords[1]:.2f}, {coords[2]:.2f})",
                menu,
            )
            info_action.setEnabled(False)
            menu.addAction(info_action)

    def _add_zone_menu_items(self, menu, zone_id):
        zone_item = self.zone_items.get(zone_id)
        if not zone_item:
            return
        z = zone_item.zone

        info = QAction(
            f"🏠 {z.label} | surface={z.surface} | "
            f"{z.table_type} | pitch={z.pitch:.3f}",
            menu,
        )
        info.setEnabled(False)
        menu.addAction(info)

        info2 = QAction(f"Köşe sayısı: {len(zone_item.coords_3d)}", menu)
        info2.setEnabled(False)
        menu.addAction(info2)

    def _add_polygon_menu_items(self, menu, polygon_id):
        if polygon_id not in self.polygons:
            return

        points = self.polygons[polygon_id]

        edit_action = QAction("Edit Points", menu)
        edit_action.triggered.connect(
            lambda: self.context_menu_action.emit(
                "EDIT_POLYGON", {"id": polygon_id}
            )
        )
        menu.addAction(edit_action)

        info_action = QAction(f"Vertices: {len(points)}", menu)
        info_action.setEnabled(False)
        menu.addAction(info_action)

    def _add_edge_menu_items(self, menu, edge_id):
        if edge_id not in self.edge_items:
            return

        edge_item = self.edge_items[edge_id]
        parent_polys = edge_item.parent_polygons

        info_action = QAction(f"🔗 Kenar: {edge_id}", menu)
        info_action.setEnabled(False)
        menu.addAction(info_action)

        if not parent_polys:
            return

        if len(parent_polys) == 1:
            poly_info = QAction(
                f"📍 Ait Olduğu Poligon: {parent_polys[0]}", menu
            )
            poly_info.setEnabled(False)
            menu.addAction(poly_info)
            return

        poly_info = QAction(f"📍 {len(parent_polys)} Poligona Ait", menu)
        poly_info.setEnabled(False)
        menu.addAction(poly_info)

        menu.addSeparator()

        submenu = QMenu("Poligonları Göster", menu)
        for poly in parent_polys:
            poly_action = QAction(f"📐 {poly}", submenu)
            poly_action.triggered.connect(
                lambda _=False, p=poly: self.context_menu_action.emit(
                    "SELECT_EDGE_IN_POLYGON",
                    {"edge_id": edge_id, "polygon": p},
                )
            )
            submenu.addAction(poly_action)
        menu.addMenu(submenu)

    def _add_frame_menu_items(self, menu, frame_id):
        if frame_id not in self.frames:
            return
        p1, p2 = self.frames[frame_id]
        info_action = QAction(f"Between: {p1} ↔ {p2}", menu)
        info_action.setEnabled(False)
        menu.addAction(info_action)

    def _show_menu(self, menu):
        if self.context_menu_pos is not None:
            viewport_pos = self.mapFromGlobal(self.cursor().pos())
            global_pos = self.mapToGlobal(viewport_pos)
            menu.exec(global_pos)
        else:
            menu.exec(self.cursor().pos())

    # =========================================================
    # CONTEXT MENU ACTION HANDLER
    # =========================================================

    def on_context_menu_action(self, action_name, data):
        """Context menü aksiyonlarını işler."""
        logging.debug(f"View3D: Unhandled context action '{action_name}'")
        try:
            handler = getattr(self, f"_ctx_{action_name.lower()}", None)
            if handler is not None:
                handler(data)
            else:
                logging.debug(f"View3D: Unhandled context action '{action_name}'")
        except Exception as e:
            logging.error(f"Error in context menu action: {e}")
            logging.error(traceback.format_exc())
            QMessageBox.warning(
                self, "Hata", f"İşlem sırasında hata oluştu: {str(e)}"
            )

    # --- Aksiyon işleyicileri ---

    def _ctx_delete(self, data):
        if self.multi_selection_mode:
            self.delete_selected_elements()
            return

        elem_type = data.get("type")
        elem_id = data.get("id")
        if not (elem_type and elem_id):
            return

        reply = QMessageBox.question(
            self, "Öğeyi Sil",
            f"{elem_type}: {elem_id} öğesini silmek istediğinize emin misiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._delete_single_element(elem_type, elem_id)

    def _ctx_change_color(self, data):
        elem_type = data.get("type")
        elem_id = data.get("id")
        if not (elem_type and elem_id):
            return

        from PySide6.QtWidgets import QColorDialog
        current = self.get_element_color(elem_type, elem_id) or QColor("#1976d2")
        color = QColorDialog.getColor(
            current, self, f"{elem_type}: {elem_id} Rengi"
        )
        if color.isValid():
            self.set_element_color(elem_type, elem_id, color)

    def _ctx_toggle_visibility(self, data):
        elem_type = data.get("type")
        elem_id = data.get("id")
        if elem_type and elem_id:
            self.toggle_visibility(elem_type, elem_id)

    def _ctx_show_objects(self, _data):
        self._show_objects_dialog()

    def _ctx_properties(self, _data):
        self.show_properties()

    def _ctx_select(self, data):
        elem_type = data.get("type")
        elem_id = data.get("id")
        if elem_type and elem_id:
            self.select_element(elem_type, elem_id)

    def _ctx_toggle(self, data):
        elem_type = data.get("type")
        elem_id = data.get("id")
        if elem_type and elem_id:
            self.toggle_multi_selection(elem_type, elem_id)

    def _ctx_select_edge_in_polygon(self, data):
        edge_id = data.get("edge_id")
        polygon = data.get("polygon")
        if edge_id and polygon:
            self.select_element("EDGE", edge_id)
            self.element_selected.emit("EDGE", edge_id, {
                "selected_polygon": polygon,
                "all_polygons": [polygon],
            })

    def _ctx_select_polygon(self, data):
        poly_id = data.get("id")
        if poly_id:
            self.select_element("POLYGON", poly_id)
            self.element_selected.emit("POLYGON", poly_id, None)

    def _ctx_select_all_polygons(self, data):
        polygons = data.get("polygons", [])
        if not polygons:
            return
        self.clear_selection()
        for poly_name in polygons:
            if poly_name in self.polygon_items:
                self.selected_items["POLYGON"].append(poly_name)
        self.multi_selection_mode = True
        self._update_selection_states()
        self._emit_multi_selection()

    def _ctx_new_point(self, data):
        pos = data.get("pos")
        if pos is not None:
            self._create_point_at_screen_pos(pos)

    def _ctx_new_polygon(self, _data):
        self.draw_mode = True
        self.creation_sequence.clear()
        self.update_preview_path()

    def _ctx_reset_view(self, _data):
        self.reset_view()

    def _ctx_toggle_draw_mode(self, _data):
        self.draw_mode = not self.draw_mode
        if not self.draw_mode:
            self.creation_sequence.clear()
            self.update_preview_path()

    def _ctx_toggle_edge_mode(self, _data):
        self.edge_selection_mode = not self.edge_selection_mode
        self.draw_scene()

    def _ctx_scene_info(self, _data):
        self._show_scene_info()

    def _ctx_edit_point(self, _data):
        self.show_properties()

    def _ctx_edit_polygon(self, _data):
        self.show_properties()

    # =========================================================
    # ÖZELLİKLER (PROPERTIES)
    # =========================================================

    def show_properties(self):
        """
        Seçili elemanın özelliklerini göstermek için sinyal yayar.
        Kim dinlerse ona iletir. View3D, MainWindow'u tanımaz.
        """
        if not self.selected_type or not self.selected_id:
            QMessageBox.information(
                self, "Özellikler",
                "Özelliklerini görmek için bir öğe seçin!"
            )
            return

        # Sadece sinyal yay — kim dinliyorsa işlesin
        self.properties_requested.emit(self.selected_type, self.selected_id)

    def _get_properties_data(self, elem_type, elem_id):
        """DataDialog için eleman verisini hazırla."""
        if elem_type == "POINT":
            coords = self.points.get(elem_id)
            if coords is None:
                return None
            return {
                "id": elem_id,
                "x": float(coords[0]),
                "y": float(coords[1]),
                "z": float(coords[2]),
            }

        if elem_type == "POLYGON":
            pts = self.polygons.get(elem_id)
            if pts is None:
                return None
            return {
                "id": elem_id,
                "vertex_count": len(pts),
                "vertices": list(pts),
                "coordinates": {
                    name: tuple(self.points.get(name, ())) for name in pts
                },
            }

        if elem_type == "FRAME":
            fr = self.frames.get(elem_id)
            if fr is None:
                return None
            p1, p2 = fr
            return {
                "id": elem_id,
                "start": p1,
                "end": p2,
                "start_coords": tuple(self.points.get(p1, ())),
                "end_coords": tuple(self.points.get(p2, ())),
            }

        if elem_type == "EDGE":
            edge_item = self.edge_items.get(elem_id)
            if edge_item is None:
                return None
            return {
                "id": elem_id,
                "p1": edge_item.p1_name,
                "p2": edge_item.p2_name,
                "p1_coords": tuple(self.points.get(edge_item.p1_name, ())),
                "p2_coords": tuple(self.points.get(edge_item.p2_name, ())),
                "parent_polygons": list(edge_item.parent_polygons or []),
            }

        if elem_type == "ZONE":
            zi = self.zone_items.get(elem_id)
            if zi is None:
                return None
            return zi.zone

        if elem_type == "LINE":
            idx = None
            if isinstance(elem_id, str) and elem_id.startswith("line_"):
                try:
                    idx = int(elem_id.split("_", 1)[1])
                except ValueError:
                    idx = None
            if idx is None or idx < 0 or idx >= len(self.lines):
                return None
            pts = self.lines[idx]
            return {
                "id": elem_id,
                "point_count": len(pts),
                "points": list(pts),
            }

        return None

    # =========================================================
    # SİLME
    # =========================================================

    def delete_selected_elements(self):
        try:
            if self.multi_selection_mode:
                selected_items = self.get_multi_selected()
                total_count = sum(len(items) for items in selected_items.values())
                if total_count == 0:
                    QMessageBox.information(self, "Sil", "Silinecek öğe yok!")
                    return

                reply = QMessageBox.question(
                    self, "Öğeleri Sil",
                    f"{total_count} öğeyi silmek istediğinize emin misiniz?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self._delete_multi_selected(selected_items)
                return

            if not self.selected_type or not self.selected_id:
                QMessageBox.information(self, "Sil", "Silmek için bir öğe seçin!")
                return

            elem_type = self.selected_type
            elem_id = self.selected_id

            reply = QMessageBox.question(
                self, "Öğeyi Sil",
                f"{elem_type}: {elem_id} öğesini silmek istediğinize emin misiniz?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._delete_single_element(elem_type, elem_id)

        except Exception as e:
            logging.error(f"Error in delete_selected_elements: {e}")
            logging.error(traceback.format_exc())
            QMessageBox.critical(
                self, "Hata", f"Silme işlemi sırasında hata: {str(e)}"
            )

    def _delete_single_element(self, elem_type, elem_id):
        logging.info(f"Deleting {elem_type}: {elem_id}")
        try:
            handler = {
                "POINT":   self._delete_point,
                "POLYGON": self._delete_polygon,
                "FRAME":   self._delete_frame,
                "EDGE":    self._delete_edge,
                "LINE":    self._delete_line,
            }.get(elem_type)

            if handler is None:
                logging.warning(f"Unknown element type: {elem_type}")
                return

            handler(elem_id)
            self.clear_selection()
            self.draw_scene()
            QMessageBox.information(
                self, "Başarılı", f"{elem_type}: {elem_id} başarıyla silindi!"
            )
        except Exception as e:
            logging.error(f"Error deleting {elem_type}: {elem_id} - {e}")
            logging.error(traceback.format_exc())
            QMessageBox.critical(
                self, "Hata", f"Silme işlemi başarısız: {str(e)}"
            )

    def _delete_multi_selected(self, selected_items):
        deleted_count = 0
        errors = []

        for elem_type, ids in selected_items.items():
            for elem_id in ids:
                try:
                    handler = {
                        "POINT":   self._delete_point,
                        "POLYGON": self._delete_polygon,
                        "FRAME":   self._delete_frame,
                        "EDGE":    self._delete_edge,
                        "LINE":    self._delete_line,
                    }.get(elem_type)
                    if handler is None:
                        continue
                    handler(elem_id)
                    deleted_count += 1
                except Exception as e:
                    errors.append(f"{elem_type}: {elem_id} - {str(e)}")

        self.clear_selection()
        self.draw_scene()

        if errors:
            QMessageBox.warning(
                self, "Uyarı",
                f"{deleted_count} öğe silindi.\n"
                f"{len(errors)} öğe silinemedi:\n" + "\n".join(errors[:5]),
            )
        else:
            QMessageBox.information(
                self, "Başarılı", f"{deleted_count} öğe başarıyla silindi!"
            )

    def _delete_polygon(self, polygon_id):
        if polygon_id not in self.polygons:
            return
        try:
            if self.selected_id == polygon_id:
                self.selected_id = None
                self.selected_type = None
            if polygon_id in self.selected_items.get("POLYGON", []):
                self.selected_items["POLYGON"].remove(polygon_id)

            item = self.polygon_items.pop(polygon_id, None)
            if item:
                try:
                    if item.scene():
                        item.scene().removeItem(item)
                except RuntimeError:
                    pass

            self.polygons.pop(polygon_id, None)
            self._color_overrides.pop(self._color_key("POLYGON", polygon_id), None)
            self._visibility_states.pop(
                self._get_visibility_key("POLYGON", polygon_id), None
            )
        except Exception as e:
            logging.error(f"_delete_polygon error: {e}")
            logging.error(traceback.format_exc())

    def _delete_point(self, point_id):
        if point_id not in self.points:
            return
        try:
            self._delete_dependent_elements(point_id)

            item = self.point_items.pop(point_id, None)
            if item:
                try:
                    if item.scene():
                        item.scene().removeItem(item)
                except RuntimeError:
                    pass

            self.points.pop(point_id, None)
            self._color_overrides.pop(self._color_key("POINT", point_id), None)
        except RuntimeError as e:
            if "wrapped C/C++ object has been deleted" not in str(e):
                raise

    def _delete_dependent_elements(self, point_id):
        polygons_to_delete = [
            name for name, pts in self.polygons.items() if point_id in pts
        ]
        for name in polygons_to_delete:
            self._delete_polygon(name)

        frames_to_delete = [
            name for name, (p1, p2) in self.frames.items()
            if point_id in (p1, p2)
        ]
        for name in frames_to_delete:
            self._delete_frame(name)

        lines_to_delete = []
        for idx, line_points in enumerate(self.lines):
            if all(isinstance(p, str) for p in line_points) and point_id in line_points:
                lines_to_delete.append(idx)
        for idx in sorted(lines_to_delete, reverse=True):
            self._delete_line(f"line_{idx}")

    def _delete_frame(self, frame_id):
        if frame_id not in self.frames:
            return
        try:
            item = self.frame_items.pop(frame_id, None)
            if item:
                try:
                    if item.scene():
                        item.scene().removeItem(item)
                except RuntimeError:
                    pass

            self.frames.pop(frame_id, None)
            self._color_overrides.pop(self._color_key("FRAME", frame_id), None)
        except RuntimeError as e:
            if "wrapped C/C++ object has been deleted" not in str(e):
                raise

    def _delete_line(self, line_id):
        try:
            idx = None
            if isinstance(line_id, str) and line_id.startswith("line_"):
                idx = int(line_id.split("_", 1)[1])
            elif isinstance(line_id, int):
                idx = line_id

            if idx is None or idx < 0 or idx >= len(self.lines):
                return

            del self.lines[idx]
            self._visibility_states.pop(
                self._get_visibility_key("LINE", f"line_{idx}"), None
            )
            self._color_overrides.pop(
                self._color_key("LINE", f"line_{idx}"), None
            )
        except Exception as e:
            logging.warning(f"Error deleting line {line_id}: {e}")

    def _delete_edge(self, edge_id):
        if edge_id not in self.edge_items:
            return
        try:
            item = self.edge_items.pop(edge_id, None)
            if item:
                try:
                    if item.scene():
                        item.scene().removeItem(item)
                except RuntimeError:
                    pass

            self._color_overrides.pop(self._color_key("EDGE", edge_id), None)
        except RuntimeError as e:
            if "wrapped C/C++ object has been deleted" not in str(e):
                raise

    # =========================================================
    # SHOW OBJECTS DIALOG
    # =========================================================

    def _show_objects_dialog(self):
        logging.debug("View3D: show_objects_dialog called")
        try:
            if self.show_objects_dialog is not None:
                try:
                    if self.show_objects_dialog.isVisible():
                        self.show_objects_dialog.raise_()
                        self.show_objects_dialog.activateWindow()
                        return
                except RuntimeError:
                    self.show_objects_dialog = None

            self.show_objects_dialog = ShowObjectsDialog(self, self.parent())
            self.show_objects_dialog.visibility_changed.connect(
                self._on_dialog_visibility_changed
            )
            self.show_objects_dialog.finished.connect(
                self._on_objects_dialog_closed
            )
            self.show_objects_dialog.show()
        except Exception as e:
            logging.error(f"View3D: Error opening Show Objects dialog - {e}")
            QMessageBox.warning(
                self, "Hata", f"Show Objects dialog açılamadı: {str(e)}"
            )

    def _on_dialog_visibility_changed(self, elem_type, item_id, is_visible):
        self.set_visibility(elem_type, item_id, is_visible)

    def _on_objects_dialog_closed(self):
        self.show_objects_dialog = None

    # =========================================================
    # YARDIMCILAR
    # =========================================================

    def _show_scene_info(self):
        counts = {
            "📍 Noktalar": len(self.points),
            "🟦 Poligonlar": len(self.polygons),
            "📏 Line'lar": len(self.lines),
            "🟧 Frame'ler": len(self.frames),
            "🔴 Kenarlar": len(self.edge_items),
        }
        total = sum(counts.values())

        lines = [f"{k}: {v}" for k, v in counts.items()]
        info = (
            "📊 Sahne Bilgileri\n"
            + "=" * 30 + "\n"
            + "\n".join(lines) + "\n"
            + "=" * 30 + "\n"
            + f"Toplam Öğe: {total}"
        )
        QMessageBox.information(self, "Sahne Bilgileri", info)

    def _create_point_at_screen_pos(self, screen_pos: QPointF):
        """Ekran koordinatından yeni nokta oluştur (z=0 düzleminde)."""
        idx = 1
        while f"P{idx}" in self.points:
            idx += 1
        name = f"P{idx}"

        scale = 40 * self.camera.zoom
        cx = (screen_pos.x() - self.center_x) / scale
        cy = -(screen_pos.y() - self.center_y) / scale
        p = self._inverse_project(cx, cy, 0.0)

        self.points[name] = (p.x, p.y, p.z)

        item = PointItem(name)
        item.clicked.connect(lambda n=name: self.on_point_clicked(n))
        item.context_menu_requested.connect(
            lambda n=name: self.show_context_menu("POINT", n)
        )
        item.visibility_changed.connect(
            lambda n, v: self._on_visibility_changed("POINT", n, v)
        )
        self.point_items[name] = item
        self.scene.addItem(item)

        self.draw_scene()
        logging.info(f"Created point {name} at {self.points[name]}")

    def _on_polygon_created(self, point_names):
        idx = 1
        while f"POLY{idx}" in self.polygons:
            idx += 1
        name = f"POLY{idx}"
        self.polygons[name] = list(point_names)
        self.draw_scene()
        logging.info(f"Polygon {name} created from {point_names}")

    def get_element_data(self, elem_type, elem_id):
        """Seçili öğenin verisini dict olarak döndürür."""
        return self._get_properties_data(elem_type, elem_id)

    def get_all_data(self):
        return {
            "points":   self.points,
            "polygons": self.polygons,
            "lines":    self.lines,
            "frames":   self.frames,
            "zones":    self.zones,
        }

    # =========================================================
    # RENDER / EXPORT
    # =========================================================

    def render_to_pixmap(self, scale: float = 2.0,
                         transparent: bool = False) -> QPixmap:
        """Sahneyi yüksek çözünürlüklü QPixmap olarak döndür."""
        if self.scene is None:
            raise RuntimeError("QGraphicsScene atanmamış!")

        rect = self.scene.itemsBoundingRect()
        if rect.isEmpty():
            rect = self.sceneRect()

        w = int(rect.width() * scale)
        h = int(rect.height() * scale)

        image = QImage(w, h, QImage.Format_ARGB32)
        image.fill(Qt.transparent if transparent else Qt.white)

        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        self.scene.render(painter, target=QRectF(0, 0, w, h), source=rect)
        painter.end()

        return QPixmap.fromImage(image)

    def render_to_png_bytes(self, scale: float = 2.0,
                            transparent: bool = False) -> bytes:
        """Sahneyi PNG byte olarak döndür."""
        pixmap = self.render_to_pixmap(scale=scale, transparent=transparent)

        ba = QByteArray()
        buf = QBuffer(ba)
        buf.open(QIODevice.WriteOnly)
        pixmap.save(buf, "PNG")
        buf.close()

        return bytes(ba)

    def copy_to_clipboard(self, scale: float = 2.0,
                          transparent: bool = False):
        """Sahneyi panoya resim olarak kopyala."""
        pixmap = self.render_to_pixmap(scale=scale, transparent=transparent)
        QApplication.clipboard().setPixmap(pixmap)

    def get_element(self, elem_type, elem_id):
        """
        Belirtilen tipteki elemanın geometrik nesnesini döndür.
        ElementDataService tarafından kullanılır.
        """
        if elem_type == "POINT":
            return self.points.get(elem_id)

        if elem_type == "POLYGON":
            return self.polygons.get(elem_id)

        if elem_type == "FRAME":
            return self.frames.get(elem_id)

        if elem_type == "EDGE":
            item = self.edge_items.get(elem_id)
            if item is not None:
                return item
            # Ağaçta olmasa da geometri olabilir
            return None

        if elem_type == "ZONE":
            zi = self.zone_items.get(elem_id)
            return zi.zone if zi is not None else None

        if elem_type == "LINE":
            if isinstance(elem_id, int):
                idx = elem_id
            elif isinstance(elem_id, str) and elem_id.startswith("line_"):
                try:
                    idx = int(elem_id.split("_", 1)[1])
                except ValueError:
                    return None
            else:
                return None
            if 0 <= idx < len(self.lines):
                return self.lines[idx]

        return None


# =============================================================
# BAĞIMSIZ ÇALIŞTIRMA TESTİ
# =============================================================

if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)

    points = {
        "P1": (2000, 2000, 0),
        "P2": (2500, 5000, 0),
        "P3": (0, 0, 0),
    }
    
    polygons = {
        "POLY1": ["P1", "P2", "P3"],
    }

    frames = {
        "F1": ["P1", "P2"],
        "F2": ["P3", "P1"],
    }

    render_lines = [
        [[0.0, 0.0, 0.0], [12000.0, 0.0, 0.0]],
        [[12000.0, 0.0, 0.0], [12000.0, 8000.0, 0.0]],
        [[12000.0, 8000.0, 0.0], [0.0, 8000.0, 0.0]],
        [[0.0, 8000.0, 0.0], [0.0, 0.0, 0.0]],
    ]

    view = View3D()
    
    raw_points = {'P1b': [0.0, 0.0, 0],
 'P2b': [5.0, 0.0, 0],
 'P3b': [5.0, -2.0, 0],
 'P4b': [8.0, -2.0, 0],
 'P5b': [8.0, 0.0, 0],
 'P6b': [12.0, 0.0, 0],
 'P7b': [12.0, 4.0, 0],
 'P8b': [13.0, 4.0, 0],
 'P9b': [13.0, 7.0, 0],
 'P10b': [11.0, 7.0, 0],
 'P11b': [11.0, 10.0, 0],
 'P12b': [9.0, 10.0, 0],
 'P13b': [9.0, 9.0, 0],
 'P14b': [2.0, 9.0, 0],
 'P15b': [2.0, 8.0, 0],
 'P16b': [0.0, 8.0, 0],
 'P1': [0.0, 0.0, 4],
 'P2': [5.0, 0.0, 4],
 'P3': [5.0, -2.0, 4],
 'P4': [8.0, -2.0, 4],
 'P5': [8.0, 0.0, 4],
 'P6': [12.0, 0.0, 4],
 'P7': [12.0, 4.0, 4],
 'P8': [13.0, 4.0, 4],
 'P9': [13.0, 7.0, 4],
 'P10': [11.0, 7.0, 4],
 'P11': [11.0, 10.0, 4],
 'P12': [9.0, 10.0, 4],
 'P13': [9.0, 9.0, 4],
 'P14': [2.0, 9.0, 4],
 'P15': [2.0, 8.0, 4],
 'P16': [0.0, 8.0, 4],
 'PP0': [6.5, -0.5, 4.3],
 'PP1': [10.0, 9.0, 4.2],
 'PP2': [10.0, 8.0, 4.2],
 'PP3': [11.5, 5.5, 4.3],
 'PP4': [10.5, 5.5, 4.3],
 'PP5': [8.5, 3.5, 4.7],
 'PP6': [7.5, 3.5, 4.7],
 'PP7': [6.5, 4.5, 4.9],
 'PP8': [6.0, 4.0, 4.8],
 'PP9': [4.0, 4.0, 4.8],
 'PP10': [6.5, 1.5, 4.3]}
    polygons_= {'POLY1': ['P1', 'PP9', 'P16'], 'POLY2': ['P7', 'P8', 'PP3', 'PP4'], 'POLY3': ['P8', 'P9', 'PP3'], 'POLY5': ['P11', 'P12', 'PP1'], 'POLY6': ['P12', 'P13', 'PP2', 'PP1'], 'POLY7': ['P15', 'P16', 'PP9', 'PP8'], 'POLY8': ['P14', 'P15', 'PP8', 'PP7'], 'POLY9': ['P1', 'P2', 'PP10', 'P5', 'P6', 'PP5', 'PP6', 'PP7', 'PP8', 'PP9'], 'POLY10': ['P6', 'P7', 'PP4', 'PP5'], 'POLY11': ['P13', 'P14', 'PP7', 'PP2'], 'POLY4': ['P9', 'P10', 'PP6', 'PP5', 'PP4', 'PP3'], 'POLY12': ['P10', 'P11', 'PP1', 'PP2', 'PP7', 'PP6'], 'POLY13': ['P3', 'P4', 'PP0'], 'POLY14': ['P2', 'P3', 'PP0', 'PP10'], 'POLY15': ['P4', 'P5', 'PP10', 'PP0'], 'POLY16': ['P1b', 'P2b', 'P2', 'P1'], 'POLY17': ['P2b', 'P3b', 'P3', 'P2'], 'POLY18': ['P3b', 'P4b', 'P4', 'P3'], 'POLY19': ['P4b', 'P5b', 'P5', 'P4'], 'POLY20': ['P5b', 'P6b', 'P6', 'P5'], 'POLY21': ['P6b', 'P7b', 'P7', 'P6'], 'POLY22': ['P7b', 'P8b', 'P8', 'P7'], 'POLY23': ['P8b', 'P9b', 'P9', 'P8'], 'POLY24': ['P9b', 'P10b', 'P10', 'P9'], 'POLY25': ['P10b', 'P11b', 'P11', 'P10'], 'POLY26': ['P11b', 'P12b', 'P12', 'P11'], 'POLY28': ['P13b', 'P14b', 'P14', 'P13'], 'POLY29': ['P14b', 'P15b', 'P15', 'P14'], 'POLY30': ['P15b', 'P16b', 'P16', 'P15'], 'POLY31': ['P16b', 'P1b', 'P1', 'P16'], 'POLY27': ['P12b', 'P13b', 'P13', 'P12']}
    view.set_data(points=raw_points, polygons= polygons_)
    # view.set_data(points=ppts, polygons=polygons,
                  # lines=render_lines, frames=frames)
    view.resize(1000, 700)
    view.show()
    view.zoom_extents()

    sys.exit(app.exec())