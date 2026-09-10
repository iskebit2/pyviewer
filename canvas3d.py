#canvas3d.py

from dataclasses import dataclass
import math
import traceback
import numpy as np
import logging
from PySide6.QtCore import QPoint, Qt, QPointF, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF, QPainterPath, QKeySequence, QShortcut, QAction
from PySide6.QtWidgets import (QGraphicsView, QGraphicsScene, QGraphicsPathItem, QMenu, QMessageBox)

from domains import AxisItem, Camera3D, ElementPropertiesDialog, PointItem, Vec3, PolygonItem, FrameItem, LineItem, EdgeItem, ShowObjectsDialog

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s - %(message)s"
)


class View3D(QGraphicsView):
    element_selected = Signal(str, str, object)
    multi_selection_changed = Signal(list)
    delete_requested = Signal()
    polygon_created = Signal(list)
    point_selected_for_operation = Signal(str)
    context_menu_action = Signal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        logging.debug("View3D: Initializing...")
        self.debug_active = False

        self.shortcut = QShortcut(QKeySequence("Ctrl+L"), self)
        self.shortcut.activated.connect(self.toggle_debug)

        self.scene = QGraphicsScene()
        self.setScene(self.scene)

        self.camera = Camera3D()
        self.points = {}
        self.polygons = {}
        self.lines = {}
        self.frames = {}
        
        self.point_items = {}
        self.polygon_items = {}
        self.edge_items = {}
        self.frame_items = {}
        self.line_items = {}
        self.graphics_line_items = []

        # Görünürlük durumları - TÜM ÖĞELER İÇİN
        self._visibility_states = {}

        self.multi_selection_mode = False
        self.selected_items = {
            "POINT": [],
            "POLYGON": [],
            "EDGE": [],
            "FRAME": [],
            "LINE": []
        }
        self.selected_type = None
        self.selected_id = None

        self.edge_selection_mode = False
        self.draw_mode = False
        self.creation_sequence = []
        self.point_selection_mode = False
        self.selected_points_for_operation = []

        self.preview_path_item = QGraphicsPathItem()
        pen = QPen(QColor("#4caf50"), 2, Qt.PenStyle.DashLine)
        self.preview_path_item.setPen(pen)
        self.preview_path_item.setZValue(300)
        self.scene.addItem(self.preview_path_item)

        self.center_x = 0
        self.center_y = 0
        self.middle_pan = False
        self.right_orbit = False
        self.last_viewport_pos = None

        # Eksenler
        self.axis_item = None
        self.axis_length = 60  # Sabit piksel
        self.show_axes = True
        
        self.axis_shortcut = QShortcut(QKeySequence("Ctrl+Shift+A"), self)
        self.axis_shortcut.activated.connect(self.toggle_axes)

        self.context_menu_pos = QPointF()
        self.context_menu_item_type = None
        self.context_menu_item_id = None

        self.show_objects_dialog = None

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setBackgroundBrush(QColor("#f7f8fa"))
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.NoAnchor)

        self.context_menu_action.connect(self.on_context_menu_action)
        self.delete_requested.connect(self.delete_selected_elements)
        logging.debug("View3D: Initialization complete")

    def toggle_debug(self):
        """Debug loglarını açıp kapatan fonksiyon"""
        self.debug_active = not self.debug_active
        if self.debug_active:
            logging.getLogger().setLevel(logging.DEBUG)
            print("🐛 Debug Logları: AÇIK")
            logging.debug("--- DEBUG MODU AKTİF EDİLDİ ---")
        else:
            logging.debug("--- DEBUG MODU KAPATILIYOR ---")
            logging.getLogger().setLevel(logging.INFO)
            print("🐛 Debug Logları: KAPALI")

    def set_data(self, points, polygons=None, lines=None, frames=None):
        logging.info(f"View3D: set_data called - Points: {len(points) if points else 0}, "
                     f"Polygons: {len(polygons) if polygons else 0}, "
                     f"Lines: {len(lines) if lines else 0}, "
                     f"Frames: {len(frames) if frames else 0}")
        
        self.points = points if points is not None else {}
        self.polygons = polygons if polygons is not None else {}
        self.lines = lines if lines is not None else {}
        self.frames = frames if frames is not None else {}
        
        # Görünürlük durumlarını temizle
        self._visibility_states.clear()
        
        self.rebuild()

    def rebuild(self):
        logging.debug("View3D: Rebuilding scene...")
        
        self._clear_all_items()
        
        for name in self.points:
            item = PointItem(name)
            item.clicked.connect(lambda n=name: self.on_point_clicked(n))
            item.context_menu_requested.connect(lambda n=name: self.show_context_menu("POINT", n))
            # Görünürlük sinyalini bağla
            item.visibility_changed.connect(lambda n, v: self._on_visibility_changed("POINT", n, v))
            self.point_items[name] = item
            self.scene.addItem(item)

        if self.preview_path_item:
            self.scene.removeItem(self.preview_path_item)
        self.preview_path_item = QGraphicsPathItem()
        pen = QPen(QColor("#4caf50"), 2, Qt.PenStyle.DashLine)
        self.preview_path_item.setPen(pen)
        self.preview_path_item.setZValue(300)
        self.scene.addItem(self.preview_path_item)

        self.draw_scene()
        logging.debug(f"View3D: Rebuild complete - Points: {len(self.point_items)}, "
                      f"Polygons: {len(self.polygon_items)}, "
                      f"Lines: {len(self.line_items)}, "
                      f"Frames: {len(self.frame_items)}")

    def _clear_all_items(self):
        """Tüm grafik öğelerini temizler"""
        for item in list(self.point_items.values()) + list(self.polygon_items.values()) + \
                    list(self.edge_items.values()) + list(self.frame_items.values()) + \
                    list(self.line_items.values()) + self.graphics_line_items:
            try:
                if item and item.scene():
                    self.scene.removeItem(item)
            except RuntimeError:
                pass
        
        self.point_items.clear()
        self.polygon_items.clear()
        self.edge_items.clear()
        self.frame_items.clear()
        self.line_items.clear()
        self.graphics_line_items.clear()

    def _get_visibility_key(self, elem_type, item_id):
        """Görünürlük anahtarını oluştur"""
        return f"{elem_type}:{item_id}"

    def _get_visibility(self, elem_type, item_id):
        """Bir öğenin görünürlük durumunu döndür (varsayılan True)"""
        key = self._get_visibility_key(elem_type, item_id)
        return self._visibility_states.get(key, True)

    def _set_visibility(self, elem_type, item_id, visible):
        """Bir öğenin görünürlük durumunu ayarla ve kaydet"""
        key = self._get_visibility_key(elem_type, item_id)
        self._visibility_states[key] = visible
        logging.debug(f"View3D: _set_visibility - {key} = {visible}")
        
        # Öğeyi güncelle
        self._apply_visibility_to_item(elem_type, item_id, visible)

    def _apply_visibility_to_item(self, elem_type, item_id, visible):
        """Görünürlüğü doğrudan öğeye uygula"""
        if elem_type == "POINT" and item_id in self.point_items:
            self.point_items[item_id].setVisible(visible)
            self.point_items[item_id]._is_visible = visible
        elif elem_type == "POLYGON" and item_id in self.polygon_items:
            self.polygon_items[item_id].setVisible(visible)
            self.polygon_items[item_id]._is_visible = visible
        elif elem_type == "FRAME" and item_id in self.frame_items:
            self.frame_items[item_id].setVisible(visible)
            self.frame_items[item_id]._is_visible = visible
        elif elem_type == "LINE" and item_id in self.line_items:
            self.line_items[item_id].setVisible(visible)
            self.line_items[item_id]._is_visible = visible
        elif elem_type == "EDGE" and item_id in self.edge_items:
            self.edge_items[item_id].setVisible(visible)
            self.edge_items[item_id]._is_visible = visible

    def _on_visibility_changed(self, elem_type, item_id, visible):
        """Öğeden gelen görünürlük değişikliğini yakala"""
        key = self._get_visibility_key(elem_type, item_id)
        self._visibility_states[key] = visible
        logging.debug(f"View3D: _on_visibility_changed - {key} = {visible}")

    def screen_position(self, p: Vec3):
        x, y, depth = self.camera.project(p)
        scale = 40 * self.camera.zoom
        return QPointF(x * scale + self.center_x, -y * scale + self.center_y), depth

    def extract_edges(self):
        """Poligonlardan kenarları çıkarır"""
        edges = {}
        for poly_name, pts in self.polygons.items():
            n = len(pts)
            for i in range(n):
                p1, p2 = pts[i], pts[(i + 1) % n]
                # Sıralı anahtar oluştur
                edge_key = tuple(sorted([p1, p2]))
                if edge_key not in edges:
                    edges[edge_key] = []
                # Poligon adını ekle (tekrar etmesin)
                if poly_name not in edges[edge_key]:
                    edges[edge_key].append(poly_name)
        return edges

    def update_preview_path(self):
        if not self.creation_sequence:
            self.preview_path_item.setPath(QPainterPath())
            return

        path = QPainterPath()
        first_pt = self.creation_sequence[0]
        if first_pt in self.point_items:
            path.moveTo(self.point_items[first_pt].pos())

        for pt_name in self.creation_sequence[1:]:
            if pt_name in self.point_items:
                path.lineTo(self.point_items[pt_name].pos())

        self.preview_path_item.setPath(path)

    def draw_scene(self):
        logging.debug("View3D: Drawing scene...")
        
        # Mevcut öğeleri temizle (axis_item hariç)
        for item in list(self.polygon_items.values()) + list(self.edge_items.values()) + \
                    list(self.frame_items.values()) + list(self.line_items.values()):
            try:
                if item and item.scene():
                    self.scene.removeItem(item)
            except RuntimeError:
                pass
        
        self.polygon_items.clear()
        self.edge_items.clear()
        self.frame_items.clear()
        self.line_items.clear()

        # Noktaları güncelle
        self._update_point_positions()

        # Poligonları çiz
        self._draw_polygons()

        # Frame'leri çiz
        self._draw_frames()

        # Line'ları çiz
        self._draw_lines()

        # Edge'leri çiz
        if self.edge_selection_mode:
            self._draw_edges()

        # Eksenleri en son çiz - 0,0,0'da
        self._draw_axis()

        self.update_preview_path()
        self.viewport().update()
        logging.debug("View3D: Scene drawing complete")

    def _draw_axis(self):
        """Eksenleri 0,0,0 konumunda çiz"""
        # Eski ekseni temizle
        if self.axis_item:
            try:
                self.scene.removeItem(self.axis_item)
            except:
                pass
            self.axis_item = None
        
        # Eksenleri gösteriliyorsa oluştur
        if self.show_axes:
            self.axis_item = AxisItem(self, self.axis_length)
            # 0,0,0'a yerleştir
            self.axis_item.setPos(0, 0)
            self.scene.addItem(self.axis_item)

    def _update_point_positions(self):
        """Noktaların pozisyonlarını günceller"""
        for name, coords in self.points.items():
            if name in self.point_items:
                pos, depth = self.screen_position(Vec3(*coords))
                self.point_items[name].setPos(pos)
                self.point_items[name].setZValue(200 + depth)
                
                # Görünürlüğü uygula
                visible = self._get_visibility("POINT", name)
                self.point_items[name].setVisible(visible)
                self.point_items[name]._is_visible = visible

    def _draw_polygons(self):
        """Poligonları çizer"""
        for poly_name, pts in self.polygons.items():
            poly = QPolygonF()
            total_depth = 0
            valid = True
            
            for p_name in pts:
                if p_name in self.points:
                    pos, depth = self.screen_position(Vec3(*self.points[p_name]))
                    poly.append(pos)
                    total_depth += depth
                else:
                    valid = False
                    break

            if valid and len(poly) >= 3:
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

                # Görünürlüğü uygula
                visible = self._get_visibility("POLYGON", poly_name)
                poly_item.setVisible(visible)
                poly_item._is_visible = visible

                self.polygon_items[poly_name] = poly_item
                self.scene.addItem(poly_item)

    def _draw_frames(self):
        """Frame'leri çizer"""
        for frame_name, (p1_name, p2_name) in self.frames.items():
            if p1_name in self.points and p2_name in self.points:
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

                # Görünürlüğü uygula
                visible = self._get_visibility("FRAME", frame_name)
                frame_item.setVisible(visible)
                frame_item._is_visible = visible

                self.frame_items[frame_name] = frame_item
                self.scene.addItem(frame_item)

    def _draw_lines(self):
        """Line'ları çizer"""
        for line_name, point_list in self.lines.items():
            screen_points = []
            depths = []
        
            for p in point_list:
                coords = None
                if isinstance(p, str):
                    if p in self.points:
                        coords = self.points[p]
                else:
                    coords = p
        
                if coords is not None:
                    flat_coords = np.asarray(coords, dtype=float).ravel()
                    x = float(flat_coords[0])
                    y = float(flat_coords[1])
                    z = float(flat_coords[2])
                
                    pos, depth = self.screen_position(Vec3(x, y, z))
                    screen_points.append(pos)
                    depths.append(depth)
        
            if len(screen_points) >= 2:
                line_item = LineItem(line_name, point_list)
                line_item.set_line(screen_points)
                line_item.clicked.connect(lambda n=line_name: self.on_line_clicked(n))
                line_item.context_menu_requested.connect(
                    lambda n=line_name: self.show_context_menu("LINE", n)
                )
                line_item.visibility_changed.connect(
                    lambda n, v: self._on_visibility_changed("LINE", n, v)
                )

                avg_depth = sum(depths) / len(depths) if depths else 0
                line_item.setZValue(125 + avg_depth)
        
                if self._is_item_selected("LINE", line_name):
                    line_item.set_selected_state(True)

                # Görünürlüğü uygula
                visible = self._get_visibility("LINE", line_name)
                line_item.setVisible(visible)
                line_item._is_visible = visible
        
                self.line_items[line_name] = line_item
                self.scene.addItem(line_item)

    def _draw_edges(self):
        """Edge'leri çizer"""
        edges = self.extract_edges()
        for (p1_n, p2_n), parent_polys in edges.items():
            if p1_n in self.points and p2_n in self.points:
                pos1, _ = self.screen_position(Vec3(*self.points[p1_n]))
                pos2, _ = self.screen_position(Vec3(*self.points[p2_n]))
                edge_key = f"{p1_n}-{p2_n}"

                # parent_polys bilgisini doğru şekilde aktar
                edge_item = EdgeItem(edge_key, p1_n, p2_n, parent_polys)
                edge_item.set_line(pos1, pos2)
                edge_item.clicked.connect(lambda e=edge_key, pp=parent_polys: self.on_edge_clicked(e, pp))
                edge_item.context_menu_requested.connect(
                    lambda n=edge_key: self.show_context_menu("EDGE", n)
                )
                edge_item.visibility_changed.connect(
                    lambda n, v: self._on_visibility_changed("EDGE", n, v)
                )

                if self._is_item_selected("EDGE", edge_key):
                    edge_item.set_selected_state(True)

                # Görünürlüğü uygula
                visible = self._get_visibility("EDGE", edge_key)
                edge_item.setVisible(visible)
                edge_item._is_visible = visible

                self.edge_items[edge_key] = edge_item
                self.scene.addItem(edge_item)

    def _is_item_selected(self, item_type, item_id):
        if self.selected_type == item_type and self.selected_id == item_id:
            return True
        if self.multi_selection_mode and item_id in self.selected_items.get(item_type, []):
            return True
        return False

    # ==================== GÖRÜNÜRLÜK METOTLARI ====================
    
    def toggle_visibility(self, elem_type, item_id):
        """Bir öğenin görünürlüğünü değiştir"""
        logging.debug(f"View3D: toggle_visibility - Type: {elem_type}, ID: {item_id}")
        
        current = self._get_visibility(elem_type, item_id)
        new_state = not current
        self._set_visibility(elem_type, item_id, new_state)
        
        # Dialog'u güncelle (eğer açıksa)
        if self.show_objects_dialog and self.show_objects_dialog.isVisible():
            self.show_objects_dialog.update_tree()
    
    def set_visibility(self, elem_type, item_id, visible):
        """Bir öğenin görünürlüğünü ayarla"""
        logging.debug(f"View3D: set_visibility - Type: {elem_type}, ID: {item_id}, Visible: {visible}")
        self._set_visibility(elem_type, item_id, visible)
        
        # Dialog'u güncelle (eğer açıksa)
        if self.show_objects_dialog and self.show_objects_dialog.isVisible():
            self.show_objects_dialog.update_tree()
    
    def get_visibility(self, elem_type, item_id):
        """Bir öğenin görünürlük durumunu döndür"""
        return self._get_visibility(elem_type, item_id)
    
    def clear_visibility_states(self):
        """Tüm görünürlük durumlarını temizle"""
        self._visibility_states.clear()

    # ==================== DİĞER METOTLAR ====================
    
    def _get_modifiers(self):
        from PySide6.QtWidgets import QApplication
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
        logging.debug(
            f"View3D: toggle_multi_selection - Type: {elem_type}, ID: {elem_id}"
        )

        if not self.multi_selection_mode:
            logging.debug("View3D: Starting multi-selection mode")
            self.multi_selection_mode = True

            if self.selected_type and self.selected_id:
                self.selected_items[self.selected_type].append(
                    self.selected_id
                )
                self.selected_type = None
                self.selected_id = None

        if elem_type in self.selected_items:
            items = self.selected_items[elem_type]

            if elem_id in items:
                items.remove(elem_id)
                logging.info(f"View3D: Removed {elem_id} from selection")
            else:
                items.append(elem_id)
                logging.info(f"View3D: Added {elem_id} to selection")

            self._update_selection_states()
            self._emit_multi_selection()

    def _update_selection_states(self):
        logging.debug("View3D: Updating selection states")
        
        for item_dict, item_type in [
            (self.point_items, "POINT"),
            (self.polygon_items, "POLYGON"),
            (self.edge_items, "EDGE"),
            (self.frame_items, "FRAME"),
            (self.line_items, "LINE")
        ]:
            for item_id, item in item_dict.items():
                is_selected = self._is_item_selected(item_type, item_id)
                item.set_selected_state(is_selected)

    def _emit_multi_selection(self):
        all_selected = []
        for elem_type, ids in self.selected_items.items():
            for elem_id in ids:
                all_selected.append((elem_type, elem_id))
        logging.info(f"View3D: Emitting multi_selection_changed with {len(all_selected)} items")
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
        
        for item_dict in [self.point_items, self.polygon_items, 
                          self.edge_items, self.frame_items, self.line_items]:
            for item in item_dict.values():
                item.set_selected_state(False)
        self.multi_selection_changed.emit([])
        self.element_selected.emit(None, None, None)

    def on_point_clicked(self, name):
        logging.debug(f"View3D: Point clicked - {name}")
        
        if self.point_selection_mode:
            if name not in self.selected_points_for_operation:
                self.selected_points_for_operation.append(name)
                self.point_selected_for_operation.emit(name)
                if name in self.point_items:
                    self.point_items[name].set_selected_state(True)
            return
        
        if self.draw_mode:
            if len(self.creation_sequence) >= 3 and name == self.creation_sequence[0]:
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
        logging.debug(f"View3D: Polygon clicked - {name}")
        
        if not self.edge_selection_mode and not self.draw_mode:
            if self._has_modifier(Qt.KeyboardModifier.ControlModifier):
                self.toggle_multi_selection("POLYGON", name)
            else:
                self.select_element("POLYGON", name)
                self.element_selected.emit("POLYGON", name, None)

    def _show_edge_polygon_selection(self, edge_key, parent_polygons):
        """Kenarın ait olduğu poligonları seçmek için dialog gösterir"""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QPushButton, QLabel, QHBoxLayout, QDialogButtonBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Kenar Hangi Poligona Ait? - {edge_key}")
        dialog.setModal(True)
        dialog.resize(350, 250)
        
        layout = QVBoxLayout(dialog)
        
        # Bilgi
        info_label = QLabel(
            f"<b>{edge_key}</b> kenarı {len(parent_polygons)} poligona ait.<br>"
            "Hangi poligonun kenarını seçmek istiyorsunuz?"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Poligon listesi
        list_widget = QListWidget()
        for poly_name in parent_polygons:
            list_widget.addItem(poly_name)
        
        # Varsayılan olarak ilk öğeyi seç
        if list_widget.count() > 0:
            list_widget.setCurrentRow(0)
        
        layout.addWidget(list_widget)
        
        # Bilgi: poligonun kaç kenarı olduğunu göster
        info_label2 = QLabel("Seçtiğiniz poligonun kenarı olarak işaretlenecektir.")
        info_label2.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(info_label2)
        
        # Butonlar
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(lambda: self._confirm_edge_polygon(dialog, list_widget, edge_key))
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        dialog.exec()

    def _confirm_edge_polygon(self, dialog, list_widget, edge_key):
        """Seçilen poligonu onayla"""
        current_item = list_widget.currentItem()
        if current_item:
            poly_name = current_item.text()
            # Kenarı seç ve hangi poligona ait olduğunu belirt
            self.select_element("EDGE", edge_key)
            self.element_selected.emit("EDGE", edge_key, {
                "selected_polygon": poly_name,
                "all_polygons": [list_widget.item(i).text() for i in range(list_widget.count())]
            })
            dialog.accept()

    def on_edge_clicked(self, edge_key, parent_polygons):
        """Edge tıklandığında çağrılır"""
        logging.info(f"View3D: Edge clicked - {edge_key}, Parent polygons: {parent_polygons}")
        
        if self.draw_mode:
            return
        
        # Edge'i seç
        self.select_element("EDGE", edge_key)
        self.element_selected.emit("EDGE", edge_key, parent_polygons)
        
        # Eğer kenar birden fazla poligona aitse, kullanıcıya hangi poligonu seçmek istediğini sor
        if parent_polygons and len(parent_polygons) > 1:
            self._show_edge_polygon_selection(edge_key, parent_polygons)
        elif parent_polygons and len(parent_polygons) == 1:
            # Tek poligon varsa, o poligonun kenarı olarak işaretle
            self._select_edge_with_polygon_context(edge_key, parent_polygons[0])

    def _select_edge_with_polygon_context(self, edge_key, poly_name):
        """Kenarı belirli bir poligon bağlamında seçer"""
        logging.info(f"View3D: Edge {edge_key} selected in context of polygon {poly_name}")
        
        # Edge zaten seçili, sadece context bilgisini ekle
        # Bu bilgiyi element_selected sinyali ile gönderebiliriz
        self.element_selected.emit("EDGE", edge_key, {"polygon": poly_name, "type": "edge_in_polygon"})

    def _show_edge_polygon_choice(self, edge_key, parent_polygons):
        """Kenarın ait olduğu poligonları seçmek için dialog gösterir"""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QPushButton, QLabel, QHBoxLayout
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Kenar Poligonları - {edge_key}")
        dialog.setModal(True)
        dialog.resize(300, 250)
        
        layout = QVBoxLayout(dialog)
        
        # Bilgi
        info_label = QLabel(f"Bu kenar {len(parent_polygons)} poligona ait:")
        layout.addWidget(info_label)
        
        # Poligon listesi
        list_widget = QListWidget()
        for poly_name in parent_polygons:
            list_widget.addItem(poly_name)
        layout.addWidget(list_widget)
        
        # Butonlar
        button_layout = QHBoxLayout()
        
        select_btn = QPushButton("Seç")
        select_btn.clicked.connect(lambda: self._select_edge_polygon(dialog, list_widget))
        button_layout.addWidget(select_btn)
        
        select_all_btn = QPushButton("Tümünü Seç")
        select_all_btn.clicked.connect(lambda: self._select_all_edge_polygons(dialog, parent_polygons))
        button_layout.addWidget(select_all_btn)
        
        cancel_btn = QPushButton("İptal")
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        dialog.exec()

    def _select_edge_polygon(self, dialog, list_widget):
        """Listeden seçilen poligonu seçer"""
        current_item = list_widget.currentItem()
        if current_item:
            poly_name = current_item.text()
            if poly_name in self.polygon_items:
                self.clear_selection()
                self.select_element("POLYGON", poly_name)
                self.element_selected.emit("POLYGON", poly_name, None)
                dialog.accept()

    def _select_all_edge_polygons(self, dialog, parent_polygons):
        """Kenarın tüm poligonlarını seçer"""
        self.clear_selection()
        
        for poly_name in parent_polygons:
            if poly_name in self.polygon_items:
                self.selected_items["POLYGON"].add(poly_name)
        
        self.multi_selection_mode = True
        self._update_selection_states()
        self._emit_multi_selection()
        
        logging.info(f"View3D: Selected {len(parent_polygons)} polygons sharing edge")
        dialog.accept()

    def on_frame_clicked(self, name):
        logging.debug(f"View3D: Frame clicked - {name}")
        
        if not self.draw_mode and not self.edge_selection_mode:
            if self._has_modifier(Qt.KeyboardModifier.ControlModifier):
                self.toggle_multi_selection("FRAME", name)
            else:
                self.select_element("FRAME", name)
                self.element_selected.emit("FRAME", name, None)

    def on_line_clicked(self, name):
        logging.debug(f"View3D: Line clicked - {name}")
        
        if not self.draw_mode and not self.edge_selection_mode:
            if self._has_modifier(Qt.KeyboardModifier.ControlModifier):
                self.toggle_multi_selection("LINE", name)
            else:
                self.select_element("LINE", name)
                self.element_selected.emit("LINE", name, None)

    def get_multi_selected(self):
        result = {}
        for elem_type, ids in self.selected_items.items():
            if ids:
                result[elem_type] = list(ids)
        return result

    def get_selected_count(self):
        return sum(len(ids) for ids in self.selected_items.values())

    def select_all(self):
        logging.debug("View3D: Selecting all items")
        self.multi_selection_mode = True
        self.selected_type = None
        self.selected_id = None
        
        for item_dict, item_type in [
            (self.point_items, "POINT"),
            (self.polygon_items, "POLYGON"),
            (self.edge_items, "EDGE"),
            (self.frame_items, "FRAME"),
            (self.line_items, "LINE")
        ]:
            for name in item_dict.keys():
                self.selected_items[item_type].add(name)
            
        self._update_selection_states()
        self._emit_multi_selection()

    def start_point_selection(self):
        logging.debug("View3D: Starting point selection mode")
        self.point_selection_mode = True
        self.selected_points_for_operation = []
        for item in self.point_items.values():
            item.set_selected_state(False)
            
    def stop_point_selection(self):
        logging.debug("View3D: Stopping point selection mode")
        self.point_selection_mode = False
        self.selected_points_for_operation = []
        for item in self.point_items.values():
            item.set_selected_state(False)
            
    def get_selected_points(self):
        return self.selected_points_for_operation.copy()

    def zoom_extents(self):
        logging.debug("View3D: Zoom to extents")
        
        all_points = {}
        
        for k, p in self.points.items():
            flat = np.asarray(p, dtype=float).ravel()
            if len(flat) >= 3:
                all_points[k] = (float(flat[0]), float(flat[1]), float(flat[2]))
    
        for line_name, point_list in self.lines.items():
            for i, p in enumerate(point_list):
                if not isinstance(p, str):
                    flat = np.asarray(p, dtype=float).ravel()
                    if len(flat) >= 3:
                        all_points[f"{line_name}_{i}"] = (float(flat[0]), float(flat[1]), float(flat[2]))
    
        if not all_points:
            logging.debug("View3D: No points found for zoom extents")
            return
    
        pts_array = np.array(list(all_points.values()), dtype=float)
        xs, ys, zs = pts_array[:, 0], pts_array[:, 1], pts_array[:, 2]
    
        center_3d = Vec3(
            float((xs.min() + xs.max()) / 2.0),
            float((ys.min() + ys.max()) / 2.0),
            float((zs.min() + zs.max()) / 2.0)
        )
    
        proj_x, proj_y = [], []
        for p in all_points.values():
            x, y, _ = self.camera.project(Vec3(*p))
            proj_x.append(x)
            proj_y.append(y)
    
        dx = max(max(proj_x) - min(proj_x), 1.0)
        dy = max(max(proj_y) - min(proj_y), 1.0)
        vw, vh = self.viewport().width() * 0.7, self.viewport().height() * 0.7
    
        self.camera.zoom = max(0.00001, min(1000.0, min(vw / (dx * 40), vh / (dy * 40))))
        cx_proj, cy_proj, _ = self.camera.project(center_3d)
        self.center_x = (self.viewport().width() / 2.0) - (cx_proj * 40 * self.camera.zoom)
        self.center_y = (self.viewport().height() / 2.0) + (cy_proj * 40 * self.camera.zoom)
        
        self.draw_scene()
        

    def mousePressEvent(self, event):
        pos = event.position().toPoint()
        logging.debug(f"View3D: mousePressEvent - Button: {event.button()}, Position: ({pos.x()}, {pos.y()})")
        
        modifiers = event.modifiers()
        self._log_modifiers(modifiers)
        
        # Eksenlere tıklandıysa işlemi engelle
        item = self.itemAt(pos)
        if item == self.axis_item:
            logging.debug("View3D: Clicked on axis - ignoring")
            return
        
        if event.button() == Qt.MouseButton.RightButton:
            self.context_menu_pos = QPointF(pos)
            
            if item is None:
                logging.debug("View3D: Right click on empty area - Showing empty context menu")
                self.show_empty_context_menu()
                return
            else:
                super().mousePressEvent(event)
                return
        
        if event.button() == Qt.MouseButton.MiddleButton and (modifiers & Qt.KeyboardModifier.ShiftModifier):
            logging.debug("View3D: Shift+Middle button pressed - Starting orbit")
            self.right_orbit = True
            self.last_viewport_pos = pos
            super().mousePressEvent(event)
            return
        
        elif event.button() == Qt.MouseButton.MiddleButton:
            logging.debug("View3D: Middle button pressed - Starting pan")
            self.middle_pan = True
            self.last_viewport_pos = pos
            super().mousePressEvent(event)
            return
        
        elif event.button() == Qt.MouseButton.LeftButton and item is None:
            logging.debug("View3D: Left button pressed on empty area - Clearing selection")
            if not self.point_selection_mode:
                self.clear_selection()
            super().mousePressEvent(event)
            return
        
        super().mousePressEvent(event)

    def _log_modifiers(self, modifiers):
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            logging.debug("View3D: Ctrl key is pressed")
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            logging.debug("View3D: Shift key is pressed")
        if modifiers & Qt.KeyboardModifier.AltModifier:
            logging.debug("View3D: Alt key is pressed")

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
        logging.debug(f"View3D: mouseReleaseEvent - Button: {event.button()}")
        self.middle_pan = False
        self.right_orbit = False
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        factor = 1.15 if delta > 0 else 1 / 1.15
        old_zoom = self.camera.zoom
        self.camera.zoom = max(0.000001, min(10000, self.camera.zoom * factor))
        logging.debug(f"View3D: Wheel event - Zoom: {old_zoom:.4f} -> {self.camera.zoom:.4f}")
        self.draw_scene()

    def keyPressEvent(self, event):
        logging.debug(f"View3D: keyPressEvent - Key: {event.key()}")
        self._log_modifiers(event.modifiers())
        
        key = event.key()
        modifiers = event.modifiers()
        
        if key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.delete_requested.emit()
        elif key == Qt.Key.Key_Home:
            self.zoom_extents()
        elif key == Qt.Key.Key_Escape:
            self.clear_selection()
        elif key == Qt.Key.Key_A and (modifiers & Qt.KeyboardModifier.ControlModifier):
            self.select_all()
        elif key == Qt.Key.Key_D and (modifiers & Qt.KeyboardModifier.ControlModifier):
            self.draw_mode = not self.draw_mode
            logging.debug(f"View3D: Draw mode is now {self.draw_mode}")
            if not self.draw_mode:
                self.creation_sequence.clear()
                self.update_preview_path()
        elif key == Qt.Key.Key_E and (modifiers & Qt.KeyboardModifier.ControlModifier):
            self.edge_selection_mode = not self.edge_selection_mode
            logging.debug(f"View3D: Edge selection mode is now {self.edge_selection_mode}")
            self.draw_scene()
        elif key == Qt.Key.Key_O and (modifiers & Qt.KeyboardModifier.ControlModifier):
            self.show_objects_dialog()

    def show_context_menu(self, item_type, item_id):
        logging.debug(f"View3D: show_context_menu - Type: {item_type}, ID: {item_id}")
        
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
        logging.debug("View3D: Showing empty context menu")
        
        menu = QMenu(self)
        
        new_point_action = QAction("New Point", menu)
        new_point_action.triggered.connect(
            lambda: self.context_menu_action.emit("NEW_POINT", {"pos": self.context_menu_pos})
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
        
        self._show_menu(menu)

    def _add_general_menu_items(self, menu, item_type, item_id):
        select_action = QAction("Select", menu)
        select_action.triggered.connect(
            lambda: self.context_menu_action.emit("SELECT", {"type": item_type, "id": item_id})
        )
        menu.addAction(select_action)
        
        if self.multi_selection_mode:
            toggle_action = QAction("Toggle Selection", menu)
            toggle_action.triggered.connect(
                lambda: self.context_menu_action.emit("TOGGLE", {"type": item_type, "id": item_id})
            )
            menu.addAction(toggle_action)

        menu.addSeparator()
    
        visibility_action = QAction("Toggle Visibility", menu)
        visibility_action.triggered.connect(
            lambda: self.context_menu_action.emit("TOGGLE_VISIBILITY", {"type": item_type, "id": item_id})
        )
        menu.addAction(visibility_action)

    def _add_type_specific_menu_items(self, menu, item_type, item_id):
        handlers = {
            "POINT": self._add_point_menu_items,
            "POLYGON": self._add_polygon_menu_items,
            "EDGE": self._add_edge_menu_items,
            "FRAME": self._add_frame_menu_items,
            "LINE": self._add_line_menu_items
        }
        
        handler = handlers.get(item_type)
        if handler:
            handler(menu, item_id)

    def _add_action_menu_items(self, menu, item_type, item_id):
        delete_action = QAction("Delete", menu)
        delete_action.triggered.connect(
            lambda: self.context_menu_action.emit("DELETE", {"type": item_type, "id": item_id})
        )
        menu.addAction(delete_action)
        
        properties_action = QAction("Properties...", menu)
        properties_action.triggered.connect(
            lambda: self.context_menu_action.emit("PROPERTIES", {"type": item_type, "id": item_id})
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

    def _show_menu(self, menu):
        if self.context_menu_pos is not None:
            viewport_pos = self.mapFromGlobal(self.cursor().pos())
            global_pos = self.mapToGlobal(viewport_pos)
            menu.exec(global_pos)
        else:
            menu.exec(self.cursor().pos())

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
                menu
            )
            info_action.setEnabled(False)
            menu.addAction(info_action)
    
    def _add_polygon_menu_items(self, menu, polygon_id):
        if polygon_id in self.polygons:
            points = self.polygons[polygon_id]
            
            edit_action = QAction("Edit Points", menu)
            edit_action.triggered.connect(
                lambda: self.context_menu_action.emit("EDIT_POLYGON", {"id": polygon_id})
            )
            menu.addAction(edit_action)
            
            info_action = QAction(f"Vertices: {len(points)}", menu)
            info_action.setEnabled(False)
            menu.addAction(info_action)
    
    def _add_edge_menu_items(self, menu, edge_id):
        """Kenar için özel menü öğeleri"""
        if edge_id in self.edge_items:
            edge_item = self.edge_items[edge_id]
            parent_polys = edge_item.parent_polygons
            
            # Kenar bilgisi
            info_action = QAction(f"🔗 Kenar: {edge_id}", menu)
            info_action.setEnabled(False)
            menu.addAction(info_action)
            
            # Poligon bilgisi
            if parent_polys:
                if len(parent_polys) == 1:
                    poly_info = QAction(f"📍 Ait Olduğu Poligon: {parent_polys[0]}", menu)
                    poly_info.setEnabled(False)
                    menu.addAction(poly_info)
                else:
                    poly_info = QAction(f"📍 {len(parent_polys)} Poligona Ait", menu)
                    poly_info.setEnabled(False)
                    menu.addAction(poly_info)
                    
                    menu.addSeparator()
                    
                    # Poligon listesi
                    submenu = QMenu("Poligonları Göster", menu)
                    for poly in parent_polys:
                        poly_action = QAction(f"📐 {poly}", submenu)
                        poly_action.triggered.connect(
                            lambda p=poly: self.context_menu_action.emit("SELECT_EDGE_IN_POLYGON", {
                                "edge_id": edge_id, 
                                "polygon": p
                            })
                        )
                        submenu.addAction(poly_action)
                    menu.addMenu(submenu)
    
    def _add_frame_menu_items(self, menu, frame_id):
        if frame_id in self.frames:
            p1, p2 = self.frames[frame_id]
            info_action = QAction(f"Between: {p1} ↔ {p2}", menu)
            info_action.setEnabled(False)
            menu.addAction(info_action)
    
    def _add_line_menu_items(self, menu, line_id):
        if line_id in self.lines:
            points = self.lines[line_id]
            info_action = QAction(f"Points: {len(points)}", menu)
            info_action.setEnabled(False)
            menu.addAction(info_action)

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
            self.show_objects_dialog.visibility_changed.connect(self._on_dialog_visibility_changed)
            self.show_objects_dialog.finished.connect(self._on_objects_dialog_closed)
            self.show_objects_dialog.show()
            logging.debug("View3D: Show Objects dialog opened")
            
        except ImportError as e:
            logging.error(f"View3D: Could not import ShowObjectsDialog - {e}")
            QMessageBox.warning(self, "Hata", "Show Objects dialog yüklenemedi!")
        except Exception as e:
            logging.error(f"View3D: Error opening Show Objects dialog - {e}")
            QMessageBox.warning(self, "Hata", f"Show Objects dialog açılamadı: {str(e)}")
    
    def _on_dialog_visibility_changed(self, elem_type, item_id, is_visible):
        """Dialog'dan gelen görünürlük değişikliği"""
        logging.debug(f"View3D: _on_dialog_visibility_changed - {elem_type}:{item_id} -> {is_visible}")
        self.set_visibility(elem_type, item_id, is_visible)
    
    def _on_objects_dialog_closed(self):
        logging.debug("View3D: Show Objects dialog closed")
        self.show_objects_dialog = None


    def _clear_items_safely(self):
        """Öğeleri güvenli bir şekilde temizler"""
        
        def safe_remove(item_dict):
            for item_id, item in list(item_dict.items()):
                try:
                    if item:
                        # Mouse grab'ı kontrol et
                        if hasattr(item, 'grabber'):
                            try:
                                if item.grabber():
                                    item.ungrabMouse()
                            except RuntimeError:
                                pass
                        
                        if item.scene():
                            item.scene().removeItem(item)
                except RuntimeError as e:
                    if "wrapped C/C++ object has been deleted" in str(e):
                        pass
                    else:
                        logging.warning(f"Error removing item: {e}")
            
            item_dict.clear()
        
        # Tüm öğeleri güvenli şekilde temizle
        safe_remove(self.point_items)
        safe_remove(self.polygon_items)
        safe_remove(self.edge_items)
        safe_remove(self.frame_items)
        safe_remove(self.line_items)
        
        # Graphics line items
        for item in list(self.graphics_line_items):
            try:
                if item and item.scene():
                    item.scene().removeItem(item)
            except RuntimeError:
                pass
        self.graphics_line_items.clear()
        
    def reset_view(self):
        """Kamerayı sıfırla"""
        self.camera.yaw = math.radians(-55)
        self.camera.pitch = math.radians(30)
        self.camera.zoom = 1.0
        self.center_x = 0
        self.center_y = 0
        self.draw_scene()

    def show_objects_dialog(self):
            """Show Objects dialog'u göster"""
            if hasattr(self, 'view3d') and self:
                self.show_objects_dialog()
            else:
                QMessageBox.warning(self, "Hata", "3D görünümü bulunamadı!")
    
    def on_context_menu_action(self, action_name, data):
        """Context menu aksiyonlarını işler"""
        logging.debug(f"Context menu action: {action_name}, Data: {data}")
        
        try:
            if action_name == "DELETE":
                self._handle_delete_action(data)
                
            elif action_name == "TOGGLE_VISIBILITY":
                elem_type = data.get("type")
                elem_id = data.get("id")
                if elem_type and elem_id:
                    self.toggle_visibility(elem_type, elem_id)
                    
            elif action_name == "SHOW_OBJECTS":
                self.show_objects_dialog()

            elif action_name == "PROPERTIES":
                self.show_properties()

            elif action_name == "SELECT":
                elem_type = data.get("type")
                elem_id = data.get("id")
                if elem_type and elem_id:
                    self.select_element(elem_type, elem_id)
                    
            elif action_name == "TOGGLE":
                elem_type = data.get("type")
                elem_id = data.get("id")
                if elem_type and elem_id:
                    self.toggle_multi_selection(elem_type, elem_id)

            elif action_name == "SELECT_EDGE_IN_POLYGON":
                edge_id = data.get("edge_id")
                polygon = data.get("polygon")
                if edge_id and polygon:
                    # Kenarı seç ve hangi poligona ait olduğunu belirt
                    self.select_element("EDGE", edge_id)
                    self.element_selected.emit("EDGE", edge_id, {
                        "selected_polygon": polygon,
                        "all_polygons": [polygon]
                    })
                    
            elif action_name == "SELECT_POLYGON":
                poly_id = data.get("id")
                if poly_id:
                    self.select_element("POLYGON", poly_id)
                    self.element_selected.emit("POLYGON", poly_id, None)
                    
            elif action_name == "SELECT_ALL_POLYGONS":
                edge_id = data.get("edge_id")
                polygons = data.get("polygons", [])
                if polygons:
                    self.clear_selection()
                    for poly_name in polygons:
                        if poly_name in self.polygon_items:
                            self.selected_items["POLYGON"].append(poly_name)
                    self.multi_selection_mode = True
                    self._update_selection_states()
                    self._emit_multi_selection()
                    
            elif action_name == "NEW_POINT":
                pos = data.get("pos")
                logging.info(f"New point at position: {pos}")
                # Yeni nokta oluşturma işlemi
                
            elif action_name == "NEW_POLYGON":
                logging.info("New polygon creation requested")
                
            elif action_name == "RESET_VIEW":
                self.camera.yaw = math.radians(-55)
                self.camera.pitch = math.radians(30)
                self.camera.zoom = 1.0
                self.center_x = 0
                self.center_y = 0
                self.draw_scene()
                
            elif action_name == "TOGGLE_DRAW_MODE":
                self.draw_mode = not self.draw_mode
                logging.info(f"Draw mode: {self.draw_mode}")
                if not self.draw_mode:
                    self.creation_sequence.clear()
                    self.update_preview_path()
                    
            elif action_name == "TOGGLE_EDGE_MODE":
                self.edge_selection_mode = not self.edge_selection_mode
                logging.info(f"Edge mode: {self.edge_selection_mode}")
                self.draw_scene()
                
            elif action_name == "SCENE_INFO":
                self._show_scene_info()
                
            elif action_name == "EDIT_POINT":
                point_id = data.get("id")
                if point_id:
                    self.show_properties()
                    
            elif action_name == "SELECT_POLYGON":
                poly_id = data.get("id")
                if poly_id:
                    self.select_element("POLYGON", poly_id)
                    
        except Exception as e:
            logging.error(f"Error in context menu action: {e}")
            logging.error(traceback.format_exc())
            QMessageBox.warning(self, "Hata", f"İşlem sırasında hata oluştu: {str(e)}")

    def _handle_delete_action(self, data):
        """Delete aksiyonunu işler"""
        if self.multi_selection_mode:
            self.delete_selected_elements()
        else:
            elem_type = data.get("type")
            elem_id = data.get("id")
            if elem_type and elem_id:
                reply = QMessageBox.question(
                    self, 
                    "Öğeyi Sil", 
                    f"{elem_type}: {elem_id} öğesini silmek istediğinize emin misiniz?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self._delete_single_element(elem_type, elem_id)

    def _show_scene_info(self):
        """Sahne bilgilerini gösterir"""
        points_count = len(self.points)
        polygons_count = len(self.polygons)
        lines_count = len(self.lines)
        frames_count = len(self.frames)
        edges_count = len(self.edge_items)
        
        info = (
            f"📊 Sahne Bilgileri\n"
            f"{'='*30}\n"
            f"📍 Noktalar: {points_count}\n"
            f"🟦 Poligonlar: {polygons_count}\n"
            f"📏 Line'lar: {lines_count}\n"
            f"🟧 Frame'ler: {frames_count}\n"
            f"🔴 Kenarlar: {edges_count}\n"
            f"{'='*30}\n"
            f"Toplam Öğe: {points_count + polygons_count + lines_count + frames_count + edges_count}"
        )
        
        QMessageBox.information(self, "Sahne Bilgileri", info)

    def show_properties(self):
        """Seçili öğenin özelliklerini gösterir ve düzenlemeye izin verir"""
        if not self.selected_type or not self.selected_id:
            QMessageBox.information(self, "Özellikler", "Özelliklerini görmek için bir öğe seçin!")
            return
            
        elem_type = self.selected_type
        elem_id = self.selected_id
        properties = self._get_properties(elem_type, elem_id)
            
        if properties:
            dialog = ElementPropertiesDialog(elem_type, elem_id, properties, self, self)
            dialog.exec()
            self.draw_scene()

    def _get_properties(self, elem_type, elem_id):
        """Öğe tipine göre özellikleri döndürür"""
        properties = {}
        
        if elem_type == "POINT" and elem_id in self.points:
            coords = self.points[elem_id]
            properties = {
                "Tür": "Nokta",
                "ID": elem_id,
                "X": coords[0],
                "Y": coords[1],
                "Z": coords[2],
            }
                
        elif elem_type == "POLYGON" and elem_id in self.polygons:
            points = self.polygons[elem_id]
            properties = {
                "Tür": "Poligon",
                "ID": elem_id,
                "Nokta Sayısı": len(points),
                "Noktalar": ", ".join(points) if points else "",
            }
                
        elif elem_type == "FRAME" and elem_id in self.frames:
            p1, p2 = self.frames[elem_id]
            properties = {
                "Tür": "Frame",
                "ID": elem_id,
                "Başlangıç": p1,
                "Bitiş": p2,
            }
                
        elif elem_type == "EDGE" and elem_id in self.edge_items:
            edge_item = self.edge_items[elem_id]
            properties = {
                "Tür": "Kenar",
                "ID": elem_id,
                "Nokta1": edge_item.p1_name,
                "Nokta2": edge_item.p2_name,
                "Bağlı Poligonlar": ", ".join(edge_item.parent_polygons) if edge_item.parent_polygons else "Yok",
            }
                
        elif elem_type == "LINE" and elem_id in self.lines:
            points = self.lines[elem_id]
            properties = {
                "Tür": "Line",
                "ID": elem_id,
                "Nokta Sayısı": len(points),
                "Noktalar": ", ".join([str(p) for p in points]) if points else "",
            }
        
        return properties

    def delete_selected_elements(self):
        """Seçili öğeleri siler (tek veya çoklu)"""
        try:
            if self.multi_selection_mode:
                selected_items = self.get_multi_selected()
                total_count = sum(len(items) for items in selected_items.values())
                
                if total_count == 0:
                    QMessageBox.information(self, "Sil", "Silinecek öğe yok!")
                    return
                    
                reply = QMessageBox.question(
                    self, 
                    "Öğeleri Sil", 
                    f"{total_count} öğeyi silmek istediğinize emin misiniz?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    self._delete_multi_selected(selected_items)
                    
            else:
                if not self.selected_type or not self.selected_id:
                    QMessageBox.information(self, "Sil", "Silmek için bir öğe seçin!")
                    return
                    
                elem_type = self.selected_type
                elem_id = self.selected_id
                
                reply = QMessageBox.question(
                    self, 
                    "Öğeyi Sil", 
                    f"{elem_type}: {elem_id} öğesini silmek istediğinize emin misiniz?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    self._delete_single_element(elem_type, elem_id)
                    
        except Exception as e:
            logging.error(f"Error in delete_selected_elements: {e}")
            logging.error(traceback.format_exc())
            QMessageBox.critical(self, "Hata", f"Silme işlemi sırasında hata oluştu: {str(e)}")

    def _delete_single_element(self, elem_type, elem_id):
        """Tek bir öğeyi siler"""
        logging.info(f"Deleting {elem_type}: {elem_id}")
        
        try:
            if elem_type == "POINT":
                self._delete_point(elem_id)
            elif elem_type == "POLYGON":
                self._delete_polygon(elem_id)
            elif elem_type == "FRAME":
                self._delete_frame(elem_id)
            elif elem_type == "EDGE":
                self._delete_edge(elem_id)
            elif elem_type == "LINE":
                self._delete_line(elem_id)
            else:
                logging.warning(f"Unknown element type: {elem_type}")
                return
                
            self.clear_selection()
            self.draw_scene()
            
            QMessageBox.information(self, "Başarılı", f"{elem_type}: {elem_id} başarıyla silindi!")
            
        except Exception as e:
            logging.error(f"Error deleting {elem_type}: {elem_id} - {e}")
            logging.error(traceback.format_exc())
            QMessageBox.critical(self, "Hata", f"Silme işlemi başarısız: {str(e)}")

    def _delete_multi_selected(self, selected_items):
        """Çoklu seçimdeki öğeleri siler"""
        deleted_count = 0
        errors = []
        
        for elem_type, ids in selected_items.items():
            for elem_id in ids:
                try:
                    if elem_type == "POINT":
                        self._delete_point(elem_id)
                    elif elem_type == "POLYGON":
                        self._delete_polygon(elem_id)
                    elif elem_type == "FRAME":
                        self._delete_frame(elem_id)
                    elif elem_type == "EDGE":
                        self._delete_edge(elem_id)
                    elif elem_type == "LINE":
                        self._delete_line(elem_id)
                    else:
                        continue
                    deleted_count += 1
                except Exception as e:
                    errors.append(f"{elem_type}: {elem_id} - {str(e)}")
        
        self.clear_selection()
        self.draw_scene()
        
        if errors:
            QMessageBox.warning(
                self, 
                "Uyarı", 
                f"{deleted_count} öğe silindi.\n"
                f"{len(errors)} öğe silinemedi:\n" + "\n".join(errors[:5])
            )
        else:
            QMessageBox.information(self, "Başarılı", f"{deleted_count} öğe başarıyla silindi!")

    def _safe_remove_item(self, item, item_dict, item_id):
        """Bir öğeyi güvenli şekilde sahneden kaldırır"""
        if not item:
            return
        
        try:
            if hasattr(item, 'setSelected'):
                item.setSelected(False)
            
            if hasattr(item, 'grabber') and item.grabber():
                try:
                    item.ungrabMouse()
                except RuntimeError:
                    pass
            
            if item.scene():
                item.scene().removeItem(item)
            
            if item_id in item_dict:
                del item_dict[item_id]
                
        except RuntimeError as e:
            if "wrapped C/C++ object has been deleted" in str(e):
                if item_id in item_dict:
                    del item_dict[item_id]
            else:
                logging.warning(f"Error removing item {item_id}: {e}")

    def _delete_polygon(self, polygon_id):
        """Poligon siler - Güvenli silme"""
        if polygon_id not in self.polygons:
            return
        
        try:
            if polygon_id in self.polygon_items:
                item = self.polygon_items[polygon_id]
                self._safe_remove_item(item, self.polygon_items, polygon_id)
            
            if polygon_id in self.polygons:
                del self.polygons[polygon_id]
            
            if self.edge_selection_mode:
                self.draw_scene()
            
            logging.info(f"Polygon {polygon_id} deleted successfully")
            
        except RuntimeError as e:
            if "wrapped C/C++ object has been deleted" in str(e):
                logging.warning(f"Polygon {polygon_id} already deleted")
            else:
                raise e

    def _delete_point(self, point_id):
        """Nokta siler - Güvenli silme"""
        if point_id not in self.points:
            return
        
        try:
            self._delete_dependent_elements(point_id)
            
            if point_id in self.point_items:
                item = self.point_items[point_id]
                
                try:
                    if hasattr(item, 'grabber') and item.grabber():
                        item.ungrabMouse()
                except RuntimeError:
                    pass
                
                if item.scene():
                    item.scene().removeItem(item)
                
                if point_id in self.point_items:
                    del self.point_items[point_id]
            
            if point_id in self.points:
                del self.points[point_id]
            
            logging.info(f"Point {point_id} deleted successfully")
            
        except RuntimeError as e:
            if "wrapped C/C++ object has been deleted" in str(e):
                logging.warning(f"Point {point_id} already deleted")
            else:
                raise e

    def _delete_dependent_elements(self, point_id):
        """Bir noktaya bağlı tüm öğeleri siler"""
        polygons_to_delete = []
        for poly_name, poly_points in self.polygons.items():
            if point_id in poly_points:
                polygons_to_delete.append(poly_name)
        
        for poly_name in polygons_to_delete:
            self._delete_polygon(poly_name)
        
        frames_to_delete = []
        for frame_name, (p1, p2) in self.frames.items():
            if point_id == p1 or point_id == p2:
                frames_to_delete.append(frame_name)
        
        for frame_name in frames_to_delete:
            self._delete_frame(frame_name)
        
        lines_to_delete = []
        for line_name, line_points in self.lines.items():
            if all(isinstance(p, str) for p in line_points):
                if point_id in line_points:
                    lines_to_delete.append(line_name)
        
        for line_name in lines_to_delete:
            self._delete_line(line_name)

    def _delete_frame(self, frame_id):
        """Frame siler - Güvenli silme"""
        if frame_id not in self.frames:
            return
        
        try:
            if frame_id in self.frame_items:
                item = self.frame_items[frame_id]
                
                try:
                    if hasattr(item, 'grabber') and item.grabber():
                        item.ungrabMouse()
                except RuntimeError:
                    pass
                
                if item.scene():
                    item.scene().removeItem(item)
                
                if frame_id in self.frame_items:
                    del self.frame_items[frame_id]
            
            if frame_id in self.frames:
                del self.frames[frame_id]
            
            logging.info(f"Frame {frame_id} deleted successfully")
            
        except RuntimeError as e:
            if "wrapped C/C++ object has been deleted" in str(e):
                logging.warning(f"Frame {frame_id} already deleted")
            else:
                raise e

    def _delete_line(self, line_id):
        """Line siler - Güvenli silme"""
        if line_id not in self.lines:
            return
        
        try:
            if line_id in self.line_items:
                item = self.line_items[line_id]
                
                try:
                    if hasattr(item, 'grabber') and item.grabber():
                        item.ungrabMouse()
                except RuntimeError:
                    pass
                
                if item.scene():
                    item.scene().removeItem(item)
                
                if line_id in self.line_items:
                    del self.line_items[line_id]
            
            if line_id in self.lines:
                del self.lines[line_id]
            
            logging.info(f"Line {line_id} deleted successfully")
            
        except RuntimeError as e:
            if "wrapped C/C++ object has been deleted" in str(e):
                logging.warning(f"Line {line_id} already deleted")
            else:
                raise e

    def _delete_edge(self, edge_id):
        """Edge siler - Güvenli silme"""
        if edge_id not in self.edge_items:
            return
        
        try:
            if edge_id in self.edge_items:
                item = self.edge_items[edge_id]
                
                try:
                    if hasattr(item, 'grabber') and item.grabber():
                        item.ungrabMouse()
                except RuntimeError:
                    pass
                
                if item.scene():
                    item.scene().removeItem(item)
                
                if edge_id in self.edge_items:
                    del self.edge_items[edge_id]
            
            logging.info(f"Edge {edge_id} deleted successfully")
            
        except RuntimeError as e:
            if "wrapped C/C++ object has been deleted" in str(e):
                logging.warning(f"Edge {edge_id} already deleted")
            else:
                raise e
    
    def resizeEvent(self, event):
        """Pencere boyutu değiştiğinde eksenleri güncelle"""
        super().resizeEvent(event)
        self.draw_scene()

    def toggle_axes(self):
        """Eksenleri göster/gizle"""
        self.show_axes = not self.show_axes
        logging.info(f"View3D: Axes visibility: {self.show_axes}")
        self.draw_scene()