from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, 
                               QPushButton, QToolButton, QSizePolicy)
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QIcon, QFont, QColor, QPalette

class ButtonBar(QWidget):
    """Modern buton çubuğu"""
    
    # Buton tıklama sinyali (buton metni ile birlikte)
    button_clicked = Signal(str)
    
    def __init__(self, parent=None, buttons=None, orientation=Qt.Horizontal, 
                 button_height=32, spacing=4, style="modern"):
        """
        Args:
            parent: Parent widget
            buttons: Dict veya list of dicts - buton tanımları
            orientation: Qt.Horizontal veya Qt.Vertical
            button_height: Buton yüksekliği
            spacing: Butonlar arası boşluk
            style: "modern", "compact", "outline"
        """
        super().__init__(parent)
        
        self.button_height = button_height
        self.spacing = spacing
        self.style_type = style
        self.buttons = {}  # Buton referanslarını sakla
        
        # Layout oluştur
        if orientation == Qt.Horizontal:
            self.main_layout = QHBoxLayout(self)
        else:
            self.main_layout = QVBoxLayout(self)
        
        self.main_layout.setContentsMargins(4, 4, 4, 4)
        self.main_layout.setSpacing(spacing)
        
        # Stilleri uygula
        self._apply_styles()
        
        # Butonları ekle
        if buttons:
            self.add_buttons(buttons)
    
    def _apply_styles(self):
        """Modern stilleri uygula"""
        style_sheets = {
            "modern": """
                QPushButton {
                    background-color: #f0f0f0;
                    border: 1px solid #d0d0d0;
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-weight: 500;
                    font-size: 11px;
                    color: #333333;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                    border-color: #b0b0b0;
                }
                QPushButton:pressed {
                    background-color: #d0d0d0;
                    border-color: #909090;
                }
                QPushButton:checked {
                    background-color: #4a90d9;
                    border-color: #357abd;
                    color: white;
                }
                QPushButton:disabled {
                    background-color: #f5f5f5;
                    color: #999999;
                    border-color: #e0e0e0;
                }
                QToolButton {
                    background-color: transparent;
                    border: 1px solid transparent;
                    border-radius: 6px;
                    padding: 6px 10px;
                    font-size: 11px;
                    color: #333333;
                }
                QToolButton:hover {
                    background-color: #f0f0f0;
                    border-color: #d0d0d0;
                }
                QToolButton:pressed {
                    background-color: #e0e0e0;
                }
            """,
            "outline": """
                QPushButton {
                    background-color: transparent;
                    border: 2px solid #4a90d9;
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-weight: 500;
                    font-size: 11px;
                    color: #4a90d9;
                }
                QPushButton:hover {
                    background-color: #4a90d9;
                    color: white;
                }
                QPushButton:pressed {
                    background-color: #357abd;
                    border-color: #357abd;
                    color: white;
                }
                QPushButton:checked {
                    background-color: #4a90d9;
                    color: white;
                }
                QPushButton:disabled {
                    border-color: #cccccc;
                    color: #999999;
                }
                QToolButton {
                    background-color: transparent;
                    border: 1px solid #4a90d9;
                    border-radius: 6px;
                    padding: 6px 10px;
                    font-size: 11px;
                    color: #4a90d9;
                }
                QToolButton:hover {
                    background-color: #4a90d9;
                    color: white;
                }
                QToolButton:pressed {
                    background-color: #357abd;
                    color: white;
                }
            """,
            "dark": """
                QPushButton {
                    background-color: #2d2d2d;
                    border: 1px solid #3d3d3d;
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-weight: 500;
                    font-size: 11px;
                    color: #e0e0e0;
                }
                QPushButton:hover {
                    background-color: #3d3d3d;
                    border-color: #4d4d4d;
                }
                QPushButton:pressed {
                    background-color: #1d1d1d;
                }
                QPushButton:checked {
                    background-color: #4a90d9;
                    border-color: #357abd;
                    color: white;
                }
                QPushButton:disabled {
                    background-color: #222222;
                    color: #666666;
                    border-color: #333333;
                }
                QToolButton {
                    background-color: transparent;
                    border: 1px solid transparent;
                    border-radius: 6px;
                    padding: 6px 10px;
                    font-size: 11px;
                    color: #e0e0e0;
                }
                QToolButton:hover {
                    background-color: #3d3d3d;
                    border-color: #4d4d4d;
                }
            """,
            "material": """
                QPushButton {
                    background-color: #6200ee;
                    border: none;
                    border-radius: 8px;
                    padding: 8px 16px;
                    font-weight: 500;
                    font-size: 12px;
                    color: white;
                    text-transform: uppercase;
                }
                QPushButton:hover {
                    background-color: #7c3af8;
                }
                QPushButton:pressed {
                    background-color: #5000d0;
                }
                QPushButton:checked {
                    background-color: #5000d0;
                }
                QPushButton:disabled {
                    background-color: #9e9e9e;
                    color: #e0e0e0;
                }
                QToolButton {
                    background-color: transparent;
                    border: none;
                    border-radius: 8px;
                    padding: 8px 14px;
                    font-weight: 500;
                    font-size: 12px;
                    color: #6200ee;
                    text-transform: uppercase;
                }
                QToolButton:hover {
                    background-color: rgba(98, 0, 238, 0.1);
                }
                QToolButton:pressed {
                    background-color: rgba(98, 0, 238, 0.2);
                }
            """
        }
        
        self.setStyleSheet(style_sheets.get(self.style_type, style_sheets["modern"]))
    
    def add_button(self, text, callback=None, icon=None, tooltip=None, 
                   checkable=False, checked=False, shortcut=None, 
                   button_type="push", enabled=True):
        """
        Tek bir buton ekle
        
        Args:
            text: Buton metni veya icon için (icon varsa metin gizlenir)
            callback: Tıklama callback'i
            icon: QIcon veya icon yolu string
            tooltip: Tooltip metni
            checkable: Checkable yap
            checked: Başlangıç checked durumu
            shortcut: Kısayol tuşu
            button_type: "push" veya "tool"
            enabled: Başlangıç enabled durumu
        """
        if button_type == "tool":
            button = QToolButton()
            button.setText(text)
        else:
            button = QPushButton()
            button.setText(text)
        
        # Boyut ayarları
        button.setFixedHeight(self.button_height)
        button.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        
        # Icon
        if icon:
            if isinstance(icon, str):
                from PySide6.QtGui import QIcon
                icon = QIcon(icon)
            button.setIcon(icon)
            button.setIconSize(QSize(16, 16))
            # Icon varsa metni gizle
            if text and text.strip():
                button.setText(text)
        
        # Tooltip
        if tooltip:
            button.setToolTip(tooltip)
        
        # Checkable
        if checkable:
            button.setCheckable(True)
            if checked:
                button.setChecked(True)
        
        # Shortcut
        if shortcut:
            button.setShortcut(shortcut)
        
        # Enabled
        button.setEnabled(enabled)
        
        # Callback
        if callback:
            button.clicked.connect(callback)
        
        # Genel sinyal
        button.clicked.connect(lambda: self.button_clicked.emit(text))
        
        # Layout'a ekle
        self.main_layout.addWidget(button)
        
        # Referansı sakla
        self.buttons[text] = button
        
        return button
    
    def add_buttons(self, buttons, button_type="push"):
        """
        Birden fazla buton ekle
        
        Args:
            buttons: 
                - Dict: {"Buton1": callback1, "Buton2": callback2}
                - List of dict: [{"text": "Buton1", "callback": func1, ...}, ...]
                - List of tuple: [("Buton1", callback1), ("Buton2", callback2)]
            button_type: "push" veya "tool"
        """
        if isinstance(buttons, dict):
            # Dict format: {"text": callback}
            for text, callback in buttons.items():
                self.add_button(text, callback, button_type=button_type)
                
        elif isinstance(buttons, list):
            for item in buttons:
                if isinstance(item, dict):
                    # Dict format with options
                    text = item.get("text", "")
                    callback = item.get("callback", None)
                    icon = item.get("icon", None)
                    tooltip = item.get("tooltip", None)
                    checkable = item.get("checkable", False)
                    checked = item.get("checked", False)
                    shortcut = item.get("shortcut", None)
                    enabled = item.get("enabled", True)
                    btn_type = item.get("button_type", button_type)
                    
                    self.add_button(
                        text=text,
                        callback=callback,
                        icon=icon,
                        tooltip=tooltip,
                        checkable=checkable,
                        checked=checked,
                        shortcut=shortcut,
                        button_type=btn_type,
                        enabled=enabled
                    )
                elif isinstance(item, (list, tuple)) and len(item) >= 2:
                    # Tuple format: (text, callback)
                    self.add_button(item[0], item[1], button_type=button_type)
                elif isinstance(item, str):
                    # Sadece metin, callback yok
                    self.add_button(item, None, button_type=button_type)
    
    def add_separator(self):
        """Ara çizgi ekle"""
        from PySide6.QtWidgets import QFrame
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setFixedHeight(self.button_height)
        self.main_layout.addWidget(separator)
        return separator
    
    def add_widget(self, widget):
        """Özel widget ekle"""
        self.main_layout.addWidget(widget)
        return widget
    
    def add_stretch(self):
        """Esnek boşluk ekle"""
        self.main_layout.addStretch()
    
    def get_button(self, text):
        """Buton referansını getir"""
        return self.buttons.get(text)
    
    def set_button_enabled(self, text, enabled):
        """Buton enabled durumunu değiştir"""
        button = self.get_button(text)
        if button:
            button.setEnabled(enabled)
    
    def set_button_checked(self, text, checked):
        """Buton checked durumunu değiştir"""
        button = self.get_button(text)
        if button and button.isCheckable():
            button.setChecked(checked)
    
    def clear(self):
        """Tüm butonları temizle"""
        for i in reversed(range(self.main_layout.count())):
            item = self.main_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
        self.buttons.clear()
    
    def set_button_style(self, style_type):
        """Buton stilini değiştir"""
        self.style_type = style_type
        self._apply_styles()
    
    def count(self):
        """Buton sayısı"""
        return len(self.buttons)
    
    def set_button_height(self, height):
        """Tüm butonların yüksekliğini değiştir"""
        self.button_height = height
        for button in self.buttons.values():
            button.setFixedHeight(height)

    def set_enabled(self, text, enabled):
        """Buton enabled durumunu değiştir"""
        if btn := self.get_button(text):
            btn.setEnabled(enabled)