# ui/data_dock.py
"""
DataDock — DataPanel'i MainWindow'a dock/float edilebilir şekilde yerleştirir.

Kullanım:
    dock = DataDock(view3d=self.view3d, parent=self)
    self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)

Public API (DataPanel'e delege):
    - set_element_info(info)
    - set_data(data, title, polygon_name)
    - show_element(elem_type, elem_id)
    - clear_selection()
    - clear()
"""

import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDockWidget

from ui.data_dialog import DataPanel


class DataDock(QDockWidget):
    """
    DataPanel'i dock/float edilebilir kılıf.

    Özellikler:
    - Başlığından sürükleyerek ayrılabilir / yeniden dock edilebilir.
    - X butonu paneli gizler; tekrar görünür yapılabilir.
    - Kapatıldığında panel state'i korunur (yeniden açınca aynı içerik).
    """

    # Panel sinyallerini dışarı yönlendir
    element_selected = Signal(str, str)

    def __init__(self, view3d=None, parent=None,
                 polygon_name=None, surface_provider=None,
                 title: str = "Data"):
        super().__init__(title, parent)

        # saveState/restoreState için
        self.setObjectName("DataDock")

        # İzin verilen konumlar
        self.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea
            | Qt.DockWidgetArea.RightDockWidgetArea
            | Qt.DockWidgetArea.BottomDockWidgetArea
        )

        # Özellikler: taşınabilir, ayrılabilir, kapatılabilir
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable
        )

        # Panel
        self.panel = DataPanel(
            view3d=view3d,
            parent=self,
            polygon_name=polygon_name,
            surface_provider=surface_provider,
        )
        self.setWidget(self.panel)

        # Panel sinyallerini dışa aktar
        self.panel.element_selected.connect(self.element_selected.emit)

        # Minimum boyut
        self.setMinimumWidth(320)
        self.setMinimumHeight(200)

        logging.debug("DataDock: Initialized")

    # =========================================================
    # DELEGE METOTLAR (DataPanel API'sini birebir yansıtır)
    # =========================================================

    def set_element_info(self, info):
        self.panel.set_element_info(info)

    def set_data(self, data, title="Data", polygon_name=None):
        self.panel.set_data(data, title=title, polygon_name=polygon_name)

    def show_element(self, elem_type, elem_id):
        self.panel.show_element(elem_type, elem_id)

    def clear_selection(self):
        self.panel.clear_selection()

    def clear(self):
        self.panel.clear()

    def set_polygon_name(self, name):
        self.panel.polygon_name = name

    def set_surface_provider(self, provider):
        self.panel._surface_provider = provider

    def get_panel(self) -> DataPanel:
        """Alt panel'e doğrudan erişim."""
        return self.panel