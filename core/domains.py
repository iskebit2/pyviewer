# domains.py

import math
from dataclasses import dataclass
import numpy as np
import logging

from PySide6.QtCore import Qt, QPointF, Signal, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QPolygonF, QFont, QPainterPath, QPainterPathStroker
from PySide6.QtWidgets import (QVBoxLayout, QTableWidget, QTableWidgetItem, QLabel, 
    QGraphicsTextItem, QGraphicsObject, QGraphicsItem, QDialog, QDialogButtonBox, QCheckBox, 
    QTreeWidget, QHeaderView, QHBoxLayout, QPushButton, QTreeWidgetItem, QWidget, QMessageBox)

@dataclass
class Vec3:
    x: float
    y: float
    z: float


class Camera3D:
    def __init__(self):
        self.yaw = math.radians(-55)
        self.pitch = math.radians(30)
        self.zoom = 1.0

    def rotate(self, dx, dy):
        self.yaw += math.radians(dx * 0.5)
        self.pitch += math.radians(dy * 0.5)
        self.pitch = max(math.radians(-89), min(math.radians(89), self.pitch))

    def project(self, p: Vec3):
        cy, sy = math.cos(self.yaw), math.sin(self.yaw)
        x1 = p.x * sy + p.y * cy
        y1 = -p.x * cy + p.y * sy

        cp, sp = math.cos(self.pitch), math.sin(self.pitch)
        x2 = -x1
        y2 = p.z * cp - y1 * sp
        z2 = p.z * sp + y1 * cp
        return x2, y2, z2


class ClickableGraphicsItem(QGraphicsObject):
    """Temel tıklanabilir grafik öğesi - QGraphicsObject tabanlı"""
    clicked = Signal(object)
    context_menu_requested = Signal(object)
    visibility_changed = Signal(object, bool)
    
    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.name = name
        self._is_deleted = False
        self._is_visible = True

        self._label_item = None            # QGraphicsTextItem
        self._label_visible = True         # kullanıcı tercihi (global toggle)
        self._label_offset = QPointF(0, 0) # alt sınıflar override eder
        
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setVisible(True)

        self._colors = {
            "normal":   QColor("#2196f3"),   # normal durum
            "hover":    QColor("#00bcd4"),   # hover
            "selected": QColor("#e91e63"),   # seçili
            "hidden":   QColor("#9e9e9e"),   # gizli
            "border":   QColor("#0d47a1"),   # kenar çizgisi
        }

        self._color_override = None

    def _ensure_label(self, text=None, color=None):
        if self._label_item is None:
            self._label_item = QGraphicsTextItem(text or self.name, self)
            self._label_item.setDefaultTextColor(color or QColor("#111111"))
            self._label_item.setFont(QFont("Arial", 8, QFont.Weight.Bold))
            self._label_item.setZValue(self.zValue() + 1)
        return self._label_item

    def set_label_visible(self, visible):
        self._label_visible = visible
        if self._label_item:
            self._label_item.setVisible(visible)

    def is_label_visible(self):
        return self._label_visible

    def update_label_position(self):
        """Alt sınıflar override eder."""
        pass

    def set_color(self, color):
        """Ana rengi override et. QColor, hex string veya tuple kabul eder."""
        self._color_override = QColor(color)
        self.update()

    def set_default_colors(self, normal=None, hover=None, selected=None,
                           hidden=None, border=None):
        """Alt sınıflar kendi varsayılan paletlerini buradan atar."""
        if normal   is not None: self._colors["normal"]   = QColor(normal)
        if hover    is not None: self._colors["hover"]    = QColor(hover)
        if selected is not None: self._colors["selected"] = QColor(selected)
        if hidden   is not None: self._colors["hidden"]   = QColor(hidden)
        if border   is not None: self._colors["border"]   = QColor(border)
        self.update()

    def color(self):
        """Aktif ana rengi döndür (override varsa onu)."""
        return self._color_override or self._colors["normal"]

    def clear_color_override(self):
        self._color_override = None
        self.update()

    def get_active_color(self, hovered=False, selected=False):
        """Duruma göre aktif rengi döndür (override öncelikli)."""
        if not self._is_visible:
            return self._colors["hidden"]
        if self._color_override is not None:
            return self._color_override
        if selected:
            return self._colors["selected"]
        if hovered:
            return self._colors["hover"]
        return self._colors["normal"]
    
    def set_visible(self, visible):
        """Görünürlüğü ayarla"""
        if self._is_visible != visible:
            self._is_visible = visible
            self.setVisible(visible)
            self.visibility_changed.emit(self.name, visible)
            
    def is_visible(self):
        """Görünürlük durumunu döndür"""
        return self._is_visible
        
    def toggle_visibility(self):
        """Görünürlüğü değiştir"""
        self.set_visible(not self._is_visible)
        
    def boundingRect(self):
        return QRectF(-10, -10, 20, 20)
    
    def paint(self, painter, option, widget):
        pass
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.name)
        elif event.button() == Qt.MouseButton.RightButton:
            self.context_menu_requested.emit(self.name)
        super().mousePressEvent(event)

    def safe_ungrab(self):
        """Qt grab'ı removeItem sırasında otomatik bırakır."""
        pass

    def safe_remove(self):
        if self._is_deleted:
            return
        self._is_deleted = True
        if self.scene():
            self.scene().removeItem(self)
            
class AxisItem(QGraphicsObject):
    """3D eksenleri gösteren grafik öğesi - Sabit boyut, 3D rotasyonlu"""
    
    def __init__(self, view3d, length=60, parent=None):
        super().__init__(parent)
        self.view3d = view3d
        self._length = length  # Sabit piksel uzunluğu
        self.setZValue(9999)
        self.setAcceptHoverEvents(False)
        self.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self.setFlag(QGraphicsItem.ItemIsMovable, False)
        
    def boundingRect(self):
        r = self._length * 1.0
        return QRectF(-r, -r, r * 2, r * 2)
    
    def paint(self, painter, option, widget=None):
        if not self.view3d:
            return
        
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Sabit uzunluk
        l = self._length
        
        # 3D noktaları projekte et (zoom'suz)
        origin = self._project(Vec3(0, 0, 0))
        x_end = self._project(Vec3(1, 0, 0))
        y_end = self._project(Vec3(0, 1, 0))
        z_end = self._project(Vec3(0, 0, 1))
        
        # Vektörleri normalize et ve l uzunluğuna ölçekle
        def scale_vector(vec):
            dx = vec.x() - origin.x()
            dy = vec.y() - origin.y()
            length = (dx * dx + dy * dy) ** 0.5
            if length < 0.001:
                return origin
            scale = l / length
            return QPointF(origin.x() + dx * scale, origin.y() + dy * scale)
        
        x_tip = scale_vector(x_end)
        y_tip = scale_vector(y_end)
        z_tip = scale_vector(z_end)
        
        # X ekseni - Kırmızı
        painter.setPen(QPen(QColor("#ff1744"), 2.5))
        painter.drawLine(origin, x_tip)
        # self._draw_arrow(painter, origin, x_tip, QColor("#ff1744"))
        # painter.drawText(x_tip + QPointF(8, -8), "X")
        
        # Y ekseni - Yeşil
        painter.setPen(QPen(QColor("#00e676"), 2.5))
        painter.drawLine(origin, y_tip)
        # self._draw_arrow(painter, origin, y_tip, QColor("#00e676"))
        # painter.drawText(y_tip + QPointF(-15, -8), "Y")
        
        # Z ekseni - Cyan
        painter.setPen(QPen(QColor("#00e5ff"), 2.5))
        painter.drawLine(origin, z_tip)
        # self._draw_arrow(painter, origin, z_tip, QColor("#00e5ff"))
        # painter.drawText(z_tip + QPointF(8, 8), "Z")
        
        # Orijin
        # painter.setBrush(QBrush(QColor("#ffffff")))
        # painter.setPen(QPen(QColor("#666666"), 1.5))
        # painter.drawEllipse(origin, 4, 4)
        # painter.drawText(origin + QPointF(-15, 15), "O")
    
    def _project(self, p3d: Vec3):
        """3D noktayı zoom'suz projekte et"""
        if not self.view3d:
            return QPointF(0, 0)
        x, y, _ = self.view3d.camera.project(p3d)
        # Zoom faktörünü 1.0 al
        scale = 40 * 1.0
        return QPointF(x * scale + self.view3d.center_x, 
                      -y * scale + self.view3d.center_y)
    
    def _draw_arrow(self, painter, origin, tip, color):
        """Ok başı çizer"""
        try:
            size = 10
            dx = tip.x() - origin.x()
            dy = tip.y() - origin.y()
            length = (dx * dx + dy * dy) ** 0.5
            
            if length < 0.01:
                return
                
            dx /= length
            dy /= length
            
            nx = -dy
            ny = dx
            
            p1 = QPointF(tip.x() - size * dx + size * 0.4 * nx,
                         tip.y() - size * dy + size * 0.4 * ny)
            p2 = QPointF(tip.x() - size * dx - size * 0.4 * nx,
                         tip.y() - size * dy - size * 0.4 * ny)
            
            painter.setBrush(color)
            painter.setPen(QPen(color, 1))
            path = QPainterPath()
            path.moveTo(tip)
            path.lineTo(p1)
            path.lineTo(p2)
            path.closeSubpath()
            painter.drawPath(path)
        except:
            pass

class PointItem(ClickableGraphicsItem):
    def __init__(self, name, radius=6, parent=None):
        super().__init__(name, parent)
        self.radius = radius
        self._is_selected = False
        self._is_hovered = False

        self.setZValue(200)

        # Varsayılan palet
        self.set_default_colors(
            normal="#2196f3", hover="#00bcd4",
            selected="#e91e63", hidden="#9e9e9e", border="#0d47a1"
        )
        
        self._ensure_label()
        self._label_item.setPos(radius + 3, -radius - 3)
        self.update_label_position()

    def set_selected_state(self, selected: bool):
        self._is_selected = selected
        self.update()

    def hoverEnterEvent(self, event):
        self._is_hovered = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._is_hovered = False
        self.update()
        super().hoverLeaveEvent(event)

    def boundingRect(self):
        r = self.radius + 6
        return QRectF(-r, -r, r * 2, r * 2)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        brush_color = self.get_active_color(self._is_hovered, self._is_selected)
        # border = self._colors["border"] if self._color_override is None else brush_color.darker(150)

        painter.setBrush(QBrush(brush_color))
        # painter.setPen(QPen(border, 3 if (self._is_selected or self._is_hovered) else 2))
        painter.drawEllipse(QRectF(-self.radius, -self.radius,
                                   self.radius * 2, self.radius * 2))



class EdgeItem(ClickableGraphicsItem):
    clicked = Signal(object, object)  # (edge_key, parent_polygons)
    context_menu_requested = Signal(object)

    def __init__(self, edge_key, p1_name, p2_name, parent_polygons, parent=None):
        super().__init__(edge_key, parent)
        self.edge_key = edge_key
        self.p1_name = p1_name
        self.p2_name = p2_name
        self.parent_polygons = parent_polygons  # Bu bir liste: [poly1, poly2, ...]
        self.p1_pos = QPointF()
        self.p2_pos = QPointF()
        self._is_selected = False
        self._is_hovered = False
        self.display_name = None
        self.setAcceptHoverEvents(True)
        self.setZValue(150)

        self.set_default_colors(
            normal="#ff9800", hover="#ffc107",
            selected="#e91e63", hidden="#9e9e9e"
        )

        self._ensure_label()
        self._label_item.setDefaultTextColor(QColor("#b71c1c"))  # koyu kırmızı

    def set_line(self, p1: QPointF, p2: QPointF):
        self.prepareGeometryChange()
        self.p1_pos = p1
        self.p2_pos = p2
        self.update()
        self.update_label_position()

    def set_display_name(self, name: str):
        """Edge'in görüntülenecek ismini ayarla (örn: POLY1.0)"""
        self.display_name = name
        if hasattr(self, "_label_item") and self._label_item:
            self._label_item.setPlainText(name)

    def update_label_position(self):
        if self._label_item is None:
            return
        mid = QPointF((self.p1_pos.x() + self.p2_pos.x()) / 2,
                      (self.p1_pos.y() + self.p2_pos.y()) / 2)
        dx = self.p2_pos.x() - self.p1_pos.x()
        dy = self.p2_pos.y() - self.p1_pos.y()
        length = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / length, dx / length

        offset = 10
        rect = self._label_item.boundingRect()
        self._label_item.setPos(mid.x() + nx * offset - rect.width() / 2,
                                mid.y() + ny * offset - rect.height() / 2)

    def set_selected_state(self, selected: bool):
        self._is_selected = selected
        self.update()

    def hoverEnterEvent(self, event):
        self._is_hovered = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._is_hovered = False
        self.update()
        super().hoverLeaveEvent(event)

    def boundingRect(self):
        return QRectF(self.p1_pos, self.p2_pos).normalized().adjusted(-6, -6, 6, 6)

    def shape(self):
        path = QPainterPath()
        path.moveTo(self.p1_pos)
        path.lineTo(self.p2_pos)
        stroker = QPainterPathStroker()
        stroker.setWidth(10)
        return stroker.createStroke(path)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        col = self.get_active_color(self._is_hovered, self._is_selected)

        # Override yoksa paylaşılan kenar rengini kullan
        if self._color_override is None and len(self.parent_polygons) > 1 \
                and not self._is_selected and not self._is_hovered:
            col = QColor("#9c27b0")

        painter.setPen(QPen(col, 3))
        painter.drawLine(self.p1_pos, self.p2_pos)
        
        # Paylaşılan kenar olduğunu belirten küçük gösterge
        if len(self.parent_polygons) > 1:
            mid_x = (self.p1_pos.x() + self.p2_pos.x()) / 2
            mid_y = (self.p1_pos.y() + self.p2_pos.y()) / 2
            painter.setPen(QPen(QColor("#9c27b0"), 1))
            painter.setBrush(QBrush(QColor("#9c27b0")))
            painter.drawEllipse(QPointF(mid_x, mid_y), 4, 4)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # parent_polygons bilgisini gönder
            self.clicked.emit(self.edge_key, self.parent_polygons)
            event.accept()
            return
        elif event.button() == Qt.MouseButton.RightButton:
            self.context_menu_requested.emit(self.edge_key)
            event.accept()
            return
        super().mousePressEvent(event)


class PolygonItem(ClickableGraphicsItem):
    def __init__(self, name, polygon_points, parent=None):
        super().__init__(name, parent)
        self.polygon_points = polygon_points
        self.screen_polygon = QPolygonF()
        self._is_selected = False
        self._is_hovered = False
        self.depth = 0

        # Poligon için dolgu renkleri alpha ile
        self._fill_normal   = QColor(123, 31, 162, 40)
        self._fill_hover    = QColor(171, 71, 188, 70)
        self._fill_selected = QColor(233, 30, 99, 100)

        self._ensure_label()
        self._label_item.setDefaultTextColor(QColor("#4a148c"))  # koyu mor

        self.set_default_colors(
            normal="#7b1fa2", hover="#ab47bc",
            selected="#e91e63", hidden="#9e9e9e", border="#7b1fa2"
        )

    def set_color(self, color):
        """Dolgu rengini override et (alpha korunur)."""
        c = QColor(color)
        c.setAlpha(self._fill_normal.alpha())
        self._color_override = c
        self.update()

    def set_border_color(self, color):
        self._colors["border"] = QColor(color)
        self.update()

    def get_fill_color(self):
        if not self._is_visible:
            return QColor(158, 158, 158, 40)
        if self._color_override is not None:
            return self._color_override
        if self._is_selected:
            return self._fill_selected
        if self._is_hovered:
            return self._fill_hover
        return self._fill_normal
    
    def set_polygon(self, qpolygon: QPolygonF, depth: float):
        self.prepareGeometryChange()
        self.screen_polygon = qpolygon
        self.depth = depth
        self.setZValue(50 + depth)
        self.update_label_position()

    def update_label_position(self):
        if self._label_item is None or self.screen_polygon.isEmpty():
            return
        # Centroid — ağırlık merkezi
        pts = self.screen_polygon
        n = pts.count()
        if n == 0:
            return
        cx = sum(pts.at(i).x() for i in range(n)) / n
        cy = sum(pts.at(i).y() for i in range(n)) / n

        # Label'ı ortala
        rect = self._label_item.boundingRect()
        self._label_item.setPos(cx - rect.width() / 2,
                                cy - rect.height() / 2)


    def set_selected_state(self, selected: bool):
        self._is_selected = selected
        self.update()

    def hoverEnterEvent(self, event):
        self._is_hovered = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._is_hovered = False
        self.update()
        super().hoverLeaveEvent(event)

    def boundingRect(self):
        return self.screen_polygon.boundingRect().adjusted(-5, -5, 5, 5)

    def shape(self):
        path = QPainterPath()
        path.addPolygon(self.screen_polygon)
        return path

    def paint(self, painter, option, widget=None):
        if self.screen_polygon.isEmpty():
            return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        fill = self.get_fill_color()
        border = self.get_active_color(self._is_hovered, self._is_selected)

        painter.setPen(QPen(border, 2))
        painter.setBrush(QBrush(fill))
        painter.drawPolygon(self.screen_polygon)


class FrameItem(ClickableGraphicsItem):
    def __init__(self, name, p1_name, p2_name, parent=None):
        super().__init__(name, parent)
        self.p1_name = p1_name
        self.p2_name = p2_name
        self.p1_pos = QPointF()
        self.p2_pos = QPointF()
        self._is_selected = False
        self._is_hovered = False
        self.setZValue(175)

        self.set_default_colors(
            normal="#1565c0", hover="#4fc3f7",
            selected="#e91e63", hidden="#9e9e9e"
        )

        self._ensure_label()
        self._label_item.setDefaultTextColor(QColor("#0d47a1"))  # koyu mavi

    def set_line(self, p1: QPointF, p2: QPointF):
        self.prepareGeometryChange()
        self.p1_pos = p1
        self.p2_pos = p2
        self.update()
        self.update_label_position()

    def update_label_position(self):
        if self._label_item is None:
            return
        mid = QPointF((self.p1_pos.x() + self.p2_pos.x()) / 2,
                      (self.p1_pos.y() + self.p2_pos.y()) / 2)

        # Çizgiye dik normal — label'ı çizginin dışına kaydır
        dx = self.p2_pos.x() - self.p1_pos.x()
        dy = self.p2_pos.y() - self.p1_pos.y()
        length = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / length, dx / length   # dik normal

        offset = 12   # piksel — label çizgiden 12px dışarı
        rect = self._label_item.boundingRect()
        self._label_item.setPos(mid.x() + nx * offset - rect.width() / 2,
                                mid.y() + ny * offset - rect.height() / 2)

    def set_selected_state(self, selected: bool):
        self._is_selected = selected
        self.update()

    def hoverEnterEvent(self, event):
        self._is_hovered = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._is_hovered = False
        self.update()
        super().hoverLeaveEvent(event)

    def boundingRect(self):
        return QRectF(self.p1_pos, self.p2_pos).normalized().adjusted(-8, -8, 8, 8)

    def shape(self):
        path = QPainterPath()
        path.moveTo(self.p1_pos)
        path.lineTo(self.p2_pos)
        stroker = QPainterPathStroker()
        stroker.setWidth(12)
        return stroker.createStroke(path)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        col = self.get_active_color(self._is_hovered, self._is_selected)
        pen = QPen(col, 4 if (self._is_selected or self._is_hovered) else 3)
        painter.setPen(pen)
        painter.drawLine(self.p1_pos, self.p2_pos)


class LineItem(ClickableGraphicsItem):
    def __init__(self, name, points_3d, parent=None):
        super().__init__(name, parent)
        self.points_3d = points_3d
        self.screen_points = []
        self._is_selected = False
        self._is_hovered = False
        self.setZValue(125)

    def set_line(self, screen_points):
        self.prepareGeometryChange()
        self.screen_points = screen_points
        self.update()

    def set_selected_state(self, selected: bool):
        self._is_selected = selected
        self.update()

    def hoverEnterEvent(self, event):
        self._is_hovered = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._is_hovered = False
        self.update()
        super().hoverLeaveEvent(event)

    def boundingRect(self):
        if not self.screen_points:
            return QRectF()
        min_x = min(p.x() for p in self.screen_points)
        max_x = max(p.x() for p in self.screen_points)
        min_y = min(p.y() for p in self.screen_points)
        max_y = max(p.y() for p in self.screen_points)
        return QRectF(min_x - 8, min_y - 8, max_x - min_x + 16, max_y - min_y + 16)

    def shape(self):
        path = QPainterPath()
        if not self.screen_points:
            return path
        path.moveTo(self.screen_points[0])
        for p in self.screen_points[1:]:
            path.lineTo(p)
        stroker = QPainterPathStroker()
        stroker.setWidth(10)
        return stroker.createStroke(path)

    def paint(self, painter, option, widget=None):
        if len(self.screen_points) < 2:
            return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        if self._is_selected:
            pen = QPen(QColor("#e91e63"), 3)
        elif self._is_hovered:
            pen = QPen(QColor("#66bb6a"), 3)
        else:
            pen = QPen(QColor("#2e7d32"), 2)

        painter.setPen(pen)
        path = QPainterPath()
        path.moveTo(self.screen_points[0])
        for p in self.screen_points[1:]:
            path.lineTo(p)
        painter.drawPath(path)

class ZoneItem(ClickableGraphicsItem):
    """
    Zone nesnelerini çizen grafik öğesi.
    PointItem'lara bağımlı değildir; koordinatları doğrudan 3D dünya
    koordinatı olarak alır ve View3D üzerinden projekte eder.
    """

    def __init__(self, name, zone, view3d, parent=None):
        super().__init__(name, parent)
        self.zone = zone                    # Zone nesnesi
        self.view3d = view3d                # projeksiyon için
        self.coords_3d = np.asarray(zone.coords, dtype=float)  # (N,3)
        self.screen_points = []             # QPointF listesi
        self.depth = 0.0
        self._is_selected = False
        self._is_hovered = False

        self.setZValue(60)

        # Zone için varsayılan palet (poligondan farklı ton)
        self._fill_normal   = QColor(0, 150, 136, 45)     # teal
        self._fill_hover    = QColor(0, 188, 212, 80)     # cyan
        self._fill_selected = QColor(233, 30, 99, 110)    # pink

        self.set_default_colors(
            normal="#090089", hover="#00bcd4",
            selected="#e91e63", hidden="#9e9e9e", border="#004d40"
        )
        
        self._ensure_label()
        self._label_item.setDefaultTextColor(QColor("#004d40"))

        # Zone etiketi: label + surface + table_type
        label_text = f"{zone.label}"
        self._label_item.setPlainText(label_text)

    # ------------------------------------------------------------- geometry
    def update_screen_points(self):
        """3D coords -> ekran koordinatları (View3D.screen_position ile)."""
        self.prepareGeometryChange()
        old_rect = self.boundingRect()  # eski bbox'ı al

        self.screen_points = []
        depths = []
        for p in self.coords_3d:
            pos, depth = self.view3d.screen_position(Vec3(float(p[0]), float(p[1]), float(p[2])))
            self.screen_points.append(pos)
            depths.append(depth)
        self.depth = sum(depths) / len(depths) if depths else 0.0
        self.setZValue(50 + self.depth)

        if self.scene():
            self.scene().invalidate(old_rect.adjusted(-2, -2, 2, 2))
            self.scene().invalidate(self.boundingRect().adjusted(-2, -2, 2, 2))
        self.update_label_position()
        self.update()

    def get_polygon(self) -> QPolygonF:
        poly = QPolygonF()
        for p in self.screen_points:
            poly.append(p)
        return poly

    # ---------------------------------------------------------------- label
    def update_label_position(self):
        if self._label_item is None or not self.screen_points:
            return
        n = len(self.screen_points)
        cx = sum(p.x() for p in self.screen_points) / n
        cy = sum(p.y() for p in self.screen_points) / n
        rect = self._label_item.boundingRect()
        self._label_item.setPos(cx - rect.width() / 2, cy - rect.height() / 2)

    # -------------------------------------------------------------- states
    def set_selected_state(self, selected: bool):
        self._is_selected = selected
        self.update()

    def hoverEnterEvent(self, event):
        self._is_hovered = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._is_hovered = False
        self.update()
        super().hoverLeaveEvent(event)

    # --------------------------------------------------------------- paint
    def get_fill_color(self):
        if not self._is_visible:
            return QColor(158, 158, 158, 40)
        if self._color_override is not None:
            return self._color_override
        if self._is_selected:
            return self._fill_selected
        if self._is_hovered:
            return self._fill_hover
        return self._fill_normal

    def boundingRect(self):
        if not self.screen_points:
            return QRectF()
        min_x = min(p.x() for p in self.screen_points)
        max_x = max(p.x() for p in self.screen_points)
        min_y = min(p.y() for p in self.screen_points)
        max_y = max(p.y() for p in self.screen_points)
        return QRectF(min_x - 5, min_y - 5,
                      max_x - min_x + 10, max_y - min_y + 10)

    def shape(self):
        path = QPainterPath()
        path.addPolygon(self.get_polygon())
        return path

    def paint(self, painter, option, widget=None):
        if len(self.screen_points) < 2:
            return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        fill = self.get_fill_color()
        border = self.get_active_color(self._is_hovered, self._is_selected)

        pen = QPen(border, 2)
        if self.zone.table_type == "ROOF":
            pen.setStyle(Qt.PenStyle.SolidLine)
        elif self.zone.table_type == "WALL":
            pen.setStyle(Qt.PenStyle.DashLine)
        elif self.zone.table_type == "CEILING":
            pen.setStyle(Qt.PenStyle.DotLine)
        painter.setPen(pen)
        painter.setBrush(QBrush(fill))

        # Zone bir polyline (genelde kapalı); polygon olarak çiz
        painter.drawPolygon(self.get_polygon())

    def set_color(self, color):
    #     """Dolgu rengini override et; alpha'yı korur."""
        c = QColor(color)
    #     if c.alpha() == 255:
    #         c.setAlpha(self._fill_normal.alpha())
    #     self._color_override = c
    #     # Kenar rengini de biraz koyulaştır
        self._colors["border"] = c.darker(150)
        self.update()

# ElementPropertiesDialog - Düzeltilmiş versiyon
class ElementPropertiesDialog(QDialog):
    def __init__(self, elem_type, elem_id, properties, view3d, parent=None):
        super().__init__(parent)
        self.elem_type = elem_type
        self.elem_id = elem_id
        self.properties = properties
        self.view3d = view3d
        self.setWindowTitle(f"Özellikler - {elem_type}: {elem_id}")
        self.setModal(True)
        self.resize(500, 400)
        self.setup_ui()
        self._load_properties()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        title_label = QLabel(f"<h2>{self.elem_type}: {self.elem_id}</h2>")
        layout.addWidget(title_label)
        
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Özellik", "Değer"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked | 
                                   QTableWidget.EditTrigger.EditKeyPressed)
        layout.addWidget(self.table)
        
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | 
                                      QDialogButtonBox.StandardButton.Cancel |
                                      QDialogButtonBox.StandardButton.Apply)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.apply_changes)
        layout.addWidget(button_box)

    def _load_properties(self):
        self.table.setRowCount(len(self.properties))
        
        for row, (key, value) in enumerate(self.properties.items()):
            key_item = QTableWidgetItem(str(key))
            key_item.setFlags(key_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, key_item)
            
            value_item = QTableWidgetItem(str(value))
            self.table.setItem(row, 1, value_item)

    def _get_updated_properties(self):
        updated = {}
        for row in range(self.table.rowCount()):
            key_item = self.table.item(row, 0)
            value_item = self.table.item(row, 1)
            
            if key_item and value_item:
                key = key_item.text()
                value_str = value_item.text()
                original_value = self.properties.get(key)
                updated[key] = self._parse_value(value_str, original_value)
        
        return updated

    def _parse_value(self, value_str, original_value):
        if isinstance(original_value, list):
            if ',' in value_str:
                items = [item.strip() for item in value_str.split(',')]
                try:
                    return [float(item) if item.replace('.', '').replace('-', '').isdigit() else item for item in items]
                except:
                    return items
            else:
                return [value_str.strip()]
        
        elif isinstance(original_value, tuple):
            if ',' in value_str:
                items = [item.strip() for item in value_str.split(',')]
                try:
                    return tuple(float(item) if item.replace('.', '').replace('-', '').isdigit() else item for item in items)
                except:
                    return tuple(items)
            else:
                return (value_str.strip(),)
        
        elif isinstance(original_value, (int, float)):
            try:
                return float(value_str) if '.' in value_str else int(value_str)
            except ValueError:
                return value_str
        
        elif isinstance(original_value, bool):
            return value_str.lower() in ('true', 'yes', '1', 'evet')
        
        else:
            return value_str

    def apply_changes(self):
        updated_properties = self._get_updated_properties()
        self._update_data(updated_properties)
        logging.info(f"Properties applied for {self.elem_type}:{self.elem_id}")

    def _update_data(self, updated_properties):
        if self.elem_type == "POINT" and self.elem_id in self.view3d.points:
            try:
                x = float(updated_properties.get("X", 0))
                y = float(updated_properties.get("Y", 0))
                z = float(updated_properties.get("Z", 0))
                self.view3d.points[self.elem_id] = (x, y, z)
                self.view3d.draw_scene()
                self.view3d.data_changed.emit("POINT", self.elem_id, (x, y, z))
            except ValueError as e:
                QMessageBox.warning(self, "Hata", f"Geçersiz koordinat değeri: {e}")
                
        elif self.elem_type == "POLYGON" and self.elem_id in self.view3d.polygons:
            points_str = updated_properties.get("Noktalar", "")
            if isinstance(points_str, str):
                points = [p.strip() for p in points_str.split(',') if p.strip()]
                if points:
                    self.view3d.polygons[self.elem_id] = points
                    self.view3d.draw_scene()
            elif isinstance(points_str, list):
                self.view3d.polygons[self.elem_id] = points_str
                self.view3d.draw_scene()
                    
        elif self.elem_type == "FRAME" and self.elem_id in self.view3d.frames:
            start = updated_properties.get("Başlangıç", "")
            end = updated_properties.get("Bitiş", "")
            if start and end:
                self.view3d.frames[self.elem_id] = (start, end)
                self.view3d.draw_scene()
        

    def accept(self):
        self.apply_changes()
        super().accept()


class ShowObjectsDialog(QDialog):
    visibility_changed = Signal(str, str, bool)

    def __init__(self, view3d, parent=None):
        super().__init__(parent)
        self.view3d = view3d
        self.setWindowTitle("Show Objects")
        self.setModal(False)
        self.resize(400, 500)
        self.setMinimumSize(300, 400)

        self.setup_ui()
        self.load_data()

    # ------------------------------------------------------------------ UI
    def setup_ui(self):
        layout = QVBoxLayout(self)

        title_label = QLabel("<h3>Görünürlük Kontrolleri</h3>")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Öğe Tipi", "ID", "Görünür"])
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.setIndentation(20)
        layout.addWidget(self.tree)

        button_layout = QHBoxLayout()

        show_all_btn = QPushButton("Tümünü Göster")
        show_all_btn.clicked.connect(self.show_all)
        button_layout.addWidget(show_all_btn)

        hide_all_btn = QPushButton("Tümünü Gizle")
        hide_all_btn.clicked.connect(self.hide_all)
        button_layout.addWidget(hide_all_btn)

        layout.addLayout(button_layout)

        type_layout = QHBoxLayout()
        types = ["POINT", "POLYGON", "EDGE", "FRAME", "LINE"]
        type_labels = {
            "POINT": "🔵 Noktalar",
            "POLYGON": "🟢 Poligonlar",
            "EDGE": "🔴 Kenarlar",
            "FRAME": "🟠 Frame'ler",
            "LINE": "🟣 Line'lar"
        }

        for elem_type in types:
            btn = QPushButton(type_labels.get(elem_type, elem_type))
            btn.setProperty("type", elem_type)
            btn.clicked.connect(lambda checked, t=elem_type: self.toggle_type_visibility(t))
            btn.setMaximumWidth(100)
            type_layout.addWidget(btn)

        layout.addLayout(type_layout)

        close_btn = QPushButton("Kapat")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    # ------------------------------------------------------------- helpers
    def _get_type_items(self, elem_type):
        """
        (item_id, item_or_None) çiftlerinin listesini döndürür.
        LINE için item her zaman None'dır (tıklanamaz graphics item).
        """
        if elem_type == "POINT":
            return list(self.view3d.point_items.items())
        if elem_type == "POLYGON":
            return list(self.view3d.polygon_items.items())
        if elem_type == "ZONE":
            return [(zid, item) for zid, item in self.view3d.zone_items.items()]
        if elem_type == "FRAME":
            return list(self.view3d.frame_items.items())
        if elem_type == "EDGE":
            return list(self.view3d.edge_items.items())
        if elem_type == "LINE":
            # self.view3d.lines bir liste; her eleman bir polyline
            return [(f"line_{i}", None) for i in range(len(self.view3d.lines))]
        return []

    def _item_is_visible(self, elem_type, item_id):
        """Tek merkezden görünürlük okuma."""
        if elem_type == "LINE":
            return self.view3d.get_visibility("LINE", item_id)
        # Diğerleri için graphics item varsa ondan, yoksa state'ten
        item = None
        if elem_type == "POINT":
            item = self.view3d.point_items.get(item_id)
        elif elem_type == "POLYGON":
            item = self.view3d.polygon_items.get(item_id)
        elif elem_type == "ZONE":
            item = self.view3d.zone_items.get(item_id)
        elif elem_type == "FRAME":
            item = self.view3d.frame_items.get(item_id)
        elif elem_type == "EDGE":
            item = self.view3d.edge_items.get(item_id)
        if item is not None and hasattr(item, "is_visible"):
            return item.is_visible()
        return self.view3d.get_visibility(elem_type, item_id)

    def _apply_visibility(self, elem_type, item_id, visible):
        """
        Görünürlüğü uygula. LINE için sadece state'i günceller ve sahneyi yeniden çizer.
        Diğerleri için hem graphics item'a hem state'e uygular.
        """
        if elem_type == "LINE":
            self.view3d.set_visibility("LINE", item_id, visible)
            self.view3d.draw_scene()
            return

        # POINT / POLYGON / FRAME / EDGE
        item_dict = {
            "POINT": self.view3d.point_items,
            "POLYGON": self.view3d.polygon_items,
            "ZONE": self.view3d.zone_items,
            "FRAME": self.view3d.frame_items,
            "EDGE": self.view3d.edge_items,
        }[elem_type]

        item = item_dict.get(item_id)
        if item is not None and hasattr(item, "set_visible"):
            item.set_visible(visible)   # item kendi state'ini + görünürlüğünü ayarlar
        else:
            # Graphics item yoksa state'i yine de güncelle
            self.view3d.set_visibility(elem_type, item_id, visible)

    # ------------------------------------------------------------ load data
    def load_data(self):
        """Mevcut verileri ağaca yükle"""
        self.tree.clear()

        categories = [
            ("POINT",   "Noktalar"),
            ("POLYGON", "Poligonlar"),
            ("ZONE", "Zone'lar"),
            ("FRAME",   "Frame'ler"),
            ("EDGE",    "Kenarlar"),
            ("LINE",    "Line'lar"),
        ]

        for elem_type, label in categories:
            items = self._get_type_items(elem_type)
            if not items:
                continue

            category_item = QTreeWidgetItem(self.tree)
            category_item.setText(0, label)
            category_item.setText(1, f"({len(items)} öğe)")
            category_item.setText(2, "")

            font = category_item.font(0)
            font.setBold(True)
            category_item.setFont(0, font)

            for item_id, _item in items:
                child = QTreeWidgetItem(category_item)
                child.setText(0, "")
                child.setText(1, item_id)

                check_widget = QWidget()
                check_layout = QHBoxLayout(check_widget)
                check_layout.setContentsMargins(0, 0, 0, 0)
                check_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

                checkbox = QCheckBox()
                is_visible = self._item_is_visible(elem_type, item_id)
                checkbox.setChecked(is_visible)
                checkbox.stateChanged.connect(
                    lambda state, t=elem_type, i=item_id: self.on_visibility_changed(t, i, state)
                )
                check_layout.addWidget(checkbox)

                self.tree.setItemWidget(child, 2, check_widget)
                child.setData(0, Qt.ItemDataRole.UserRole, (elem_type, item_id))

            category_item.setExpanded(True)

    # --------------------------------------------------------- visibility
    def on_visibility_changed(self, elem_type, item_id, state):
        is_visible = state == Qt.CheckState.Checked.value
        self.visibility_changed.emit(elem_type, item_id, is_visible)
        self._apply_visibility(elem_type, item_id, is_visible)

    def toggle_type_visibility(self, elem_type):
        items = self._get_type_items(elem_type)
        if not items:
            return

        # Tümü görünürse -> hepsini gizle, aksi halde hepsini göster
        all_visible = all(self._item_is_visible(elem_type, item_id) for item_id, _ in items)
        new_state = not all_visible

        for item_id, _ in items:
            self._apply_visibility(elem_type, item_id, new_state)
            self.visibility_changed.emit(elem_type, item_id, new_state)

        self.update_tree()

    def show_all(self):
        self._set_all_visibility(True)

    def hide_all(self):
        self._set_all_visibility(False)

    def _set_all_visibility(self, visible):
        for elem_type in ["POINT", "POLYGON", "FRAME", "EDGE", "LINE"]:
            for item_id, _ in self._get_type_items(elem_type):
                self._apply_visibility(elem_type, item_id, visible)
                self.visibility_changed.emit(elem_type, item_id, visible)

        self.update_tree()

    # -------------------------------------------------------------- refresh
    def update_tree(self):
        for i in range(self.tree.topLevelItemCount()):
            category = self.tree.topLevelItem(i)
            for j in range(category.childCount()):
                child = category.child(j)
                widget = self.tree.itemWidget(child, 2)
                if not widget:
                    continue
                checkbox = widget.findChild(QCheckBox)
                if not checkbox:
                    continue
                data = child.data(0, Qt.ItemDataRole.UserRole)
                if not data:
                    continue
                elem_type, item_id = data
                checkbox.blockSignals(True)
                checkbox.setChecked(self._item_is_visible(elem_type, item_id))
                checkbox.blockSignals(False)