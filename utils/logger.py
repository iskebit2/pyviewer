from datetime import datetime
import tkinter as tk
from typing import Optional, Callable, Any
import traceback

class EnhancedLogger:
    def __init__(self, text_widget: Optional[tk.Text] = None):
        self.text_widget = text_widget
        self.logs = []
        self.logs_details = []
        self._action_counter = 0
        self._is_destroyed = False

        self.colors = {
            "INFO": "#2980b9",
            "SUCCESS": "#27ae60",
            "WARNING": "#d35400",
            "ERROR": "#c0392b",
            "PRINT": "#2c3e50",
        }

        if self.text_widget:
            self._setup_tags()

    def _validate_widget(self) -> bool:
        """Widget'in hala geçerli olup olmadığını kontrol et"""
        if not self.text_widget:
            return False
        try:
            # Widget hala var mı kontrol et
            self.text_widget.winfo_exists()
            return True
        except (tk.TclError, AttributeError):
            self._is_destroyed = True
            self.text_widget = None
            return False

    def _setup_tags(self):
        if not self._validate_widget():
            return

        try:
            for level, color in self.colors.items():
                weight = "bold" if level in ("WARNING", "ERROR", "SUCCESS") else "normal"
                self.text_widget.tag_config(
                    level,
                    foreground=color,
                    font=("Consolas", 8, weight)
                )
        except tk.TclError as e:
            print(f"Tag setup failed: {e}")

    def log(self, message: str, level: str = "PRINT", action: Optional[Callable] = None):
        """Log mesajı ekle"""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_details_entry = f"[{timestamp}] {level}: {message}\n"
            log_entry = f"{message}\n"
            self.logs_details.append(log_details_entry)
            self.logs.append(log_entry)

            if not self._validate_widget():
                return

            # Level kontrolü
            if level not in self.colors:
                level = "PRINT"

            start_index = self.text_widget.index("end-1c")
            
            try:
                self.text_widget.insert("end", log_entry, level)
            except tk.TclError:
                # Widget artık mevcut değilse
                self.text_widget = None
                return

            if action:
                self._add_action_link(start_index, action)

            self._scroll_to_end()

        except Exception as e:
            print(f"Log error: {e}")
            traceback.print_exc()

    def _add_action_link(self, start_index: str, action: Callable):
        """Aksiyon linki ekle"""
        try:
            self._action_counter += 1
            tag = f"ACTION_{self._action_counter}"

            self.text_widget.tag_config(tag, underline=True, foreground="#3498db")
            self.text_widget.tag_add(tag, start_index, "end-1c")

            # Lambda'lar için closure sorununu önle
            def make_action_wrapper(fn):
                return lambda e: self._safe_execute(fn)

            self.text_widget.tag_bind(
                tag, "<Button-1>",
                make_action_wrapper(action)
            )
            
            self.text_widget.tag_bind(
                tag, "<Enter>",
                lambda e, t=self.text_widget: t.config(cursor="hand2") if t else None
            )
            self.text_widget.tag_bind(
                tag, "<Leave>",
                lambda e, t=self.text_widget: t.config(cursor="") if t else None
            )

        except Exception as e:
            print(f"Action link error: {e}")

    def _safe_execute(self, action: Callable):
        """Güvenli fonksiyon çalıştırma"""
        try:
            action()
        except Exception as e:
            self.log(f"Action failed: {e}", "ERROR")

    def _scroll_to_end(self):
        """Son satıra scroll et"""
        if self._validate_widget():
            try:
                self.text_widget.see("end")
            except tk.TclError:
                pass

    def write(self, string: str):
        """Print fonksiyonları için"""
        if string.strip():  # Boş satırları filtrele
            self.log(string.strip(), "PRINT")

    def flush(self):
        pass

    def clear(self, keep_logs: bool = False):
        """Log ekranını temizle
        
        Args:
            keep_logs: True ise self.logs listesini korur
        """
        if not self._validate_widget():
            return

        try:
            self.text_widget.delete("1.0", "end")
            
            # Tüm action tag'larini temizle
            for tag in self.text_widget.tag_names():
                if tag.startswith("ACTION_"):
                    self.text_widget.tag_delete(tag)
            
            self._action_counter = 0
            
            if not keep_logs:
                self.logs.clear()
                
        except tk.TclError as e:
            print(f"Clear error: {e}")

    def get_logs_as_text(self) -> str:
        """Log'ları metin olarak al"""
        return "".join(self.logs)

    def save_logs(self, filename: str):
        """Log'ları dosyaya kaydet"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.get_logs_as_text())
            self.log(f"Logs saved to {filename}", "SUCCESS")
        except Exception as e:
            self.log(f"Save failed: {e}", "ERROR")

    def set_text_widget(self, text_widget: tk.Text):
        """Runtime'da text widget'ını değiştir"""
        self.text_widget = text_widget
        self._is_destroyed = False
        self._setup_tags()