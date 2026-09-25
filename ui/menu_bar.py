from argparse import Action
import json
import logging

from PySide6.QtWidgets import QFileDialog, QMenuBar, QMessageBox
from PySide6.QtCore import QFileInfo

class MenuBar(QMenuBar):

    def __init__(self, main_window):
        super().__init__(main_window)

        self.main_window = main_window

        self.setup_menu()

    def setup_menu(self):
        """Menü çubuğunu oluştur"""
        
        
        # ==================== FILE MENÜSÜ ====================
        file_menu = self.addMenu("&File")
        
        # New
        new_action = file_menu.addAction("&New")
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_file)
        
        file_menu.addSeparator()
        
        # Open
        open_action = file_menu.addAction("&Open...")
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_file)
        
        # Save
        save_action = file_menu.addAction("&Save")
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_file)
        
        # Save As
        save_as_action = file_menu.addAction("Save &As...")
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.save_as_file)
        
        file_menu.addSeparator()
        
        # Import
        import_menu = file_menu.addMenu("&Import")
        
        import_json_action = import_menu.addAction("Import from JSON...")
        import_json_action.triggered.connect(self.import_json)
        
        import_csv_action = import_menu.addAction("Import from CSV...")
        import_csv_action.triggered.connect(self.import_csv)
        
        import_obj_action = import_menu.addAction("Import from OBJ...")
        import_obj_action.triggered.connect(self.import_obj)
        
        file_menu.addSeparator()
        
        # Export
        export_menu = file_menu.addMenu("&Export")
        
        export_json_action = export_menu.addAction("Export to JSON...")
        export_json_action.triggered.connect(self.export_json)
        
        export_obj_action = export_menu.addAction("Export to OBJ...")
        export_obj_action.triggered.connect(self.export_obj)
        
        export_png_action = export_menu.addAction("Export as PNG...")
        export_png_action.triggered.connect(self.export_png)
        
        file_menu.addSeparator()
        
        # Wind Analysis
        wind_menu = self.addMenu("&Wind Analysis")
        
        analyze_action = wind_menu.addAction("&Analyze Selected")
        analyze_action.setShortcut("Ctrl+A")
        analyze_action.triggered.connect(self.main_window.building_wind_calc)
        
        wind_menu.addSeparator()
        
        set_wind_action = wind_menu.addAction("&Set Wind Parameters...")
        set_wind_action.triggered.connect(self.main_window.set_wind_parameters)
        
        set_e_action = wind_menu.addAction("&Set Building Size (e)...")
        set_e_action.triggered.connect(self.main_window.set_building_size)
        
        file_menu.addSeparator()
        
        # Test
        test_action = file_menu.addAction("&Test Data")
        test_action.setShortcut("Ctrl+T")
        test_action.triggered.connect(self.main_window.create_sample_data)
        
        file_menu.addSeparator()
        
        # Exit
        exit_action = file_menu.addAction("E&xit")
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.main_window.close)

        logging.info("menu connected")
    # ==================== FILE MENÜSÜ FONKSİYONLARI ====================
    
    def new_file(self):
        """Yeni dosya oluştur"""
        if self._confirm_discard_changes():
            self.main_window.view3d.points.clear()
            self.main_window.view3d.polygons.clear()
            self.main_window.view3d.lines.clear()
            self.main_window.view3d.frames.clear()
            self.main_window.view3d.rebuild()
            self.main_window.current_file_path = None
            self.setWindowTitle("3D Viewer - Yeni Dosya")
            logging.info("Yeni Dosya", "Yeni dosya oluşturuldu!")

    def open_file(self):
        """Dosya aç"""
        if not self._confirm_discard_changes():
            return
            
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Dosya Aç", 
            "", 
            "JSON Dosyaları (*.json);;Tüm Dosyalar (*.*)"
        )
        
        if file_path:
            self._load_from_file(file_path)
    
    def save_file(self):
        """Dosyayı kaydet"""
        if self.main_window.current_file_path:
            self._save_to_file(self.main_window.current_file_path)
        else:
            self.save_as_file()
    
    def save_as_file(self):
        """Farklı kaydet"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "Farklı Kaydet", 
            "", 
            "JSON Dosyaları (*.json);;Tüm Dosyalar (*.*)"
        )
        
        if file_path:
            if not file_path.lower().endswith('.json'):
                file_path += '.json'
            self._save_to_file(file_path)
    
    def import_json(self):
        """JSON dosyasından içe aktar"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "JSON İçe Aktar", 
            "", 
            "JSON Dosyaları (*.json);;Tüm Dosyalar (*.*)"
        )
        
        if file_path:
            self._import_from_json(file_path)
    
    def import_csv(self):
        """CSV dosyasından içe aktar"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "CSV İçe Aktar", 
            "", 
            "CSV Dosyaları (*.csv);;Tüm Dosyalar (*.*)"
        )
        
        if file_path:
            self._import_from_csv(file_path)
    
    def import_obj(self):
        """OBJ dosyasından içe aktar"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "OBJ İçe Aktar", 
            "", 
            "OBJ Dosyaları (*.obj);;Tüm Dosyalar (*.*)"
        )
        
        if file_path:
            self._import_from_obj(file_path)
    
    def export_json(self):
        """JSON olarak dışa aktar"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "JSON Olarak Dışa Aktar", 
            "", 
            "JSON Dosyaları (*.json);;Tüm Dosyalar (*.*)"
        )
        
        if file_path:
            if not file_path.lower().endswith('.json'):
                file_path += '.json'
            self._export_to_json(file_path)
    
    def export_obj(self):
        """OBJ olarak dışa aktar"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "OBJ Olarak Dışa Aktar", 
            "", 
            "OBJ Dosyaları (*.obj);;Tüm Dosyalar (*.*)"
        )
        
        if file_path:
            if not file_path.lower().endswith('.obj'):
                file_path += '.obj'
            self._export_to_obj(file_path)
    
    def export_png(self):
        """PNG olarak dışa aktar"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "PNG Olarak Dışa Aktar", 
            "", 
            "PNG Dosyaları (*.png);;Tüm Dosyalar (*.*)"
        )
        
        if file_path:
            if not file_path.lower().endswith('.png'):
                file_path += '.png'
            self._export_to_png(file_path)

    # ==================== DOSYA İŞLEM FONKSİYONLARI ====================
    
    def _confirm_discard_changes(self):
        """Değişiklikleri kaydetmeyi onayla"""
        if self.main_window.view3d.points or self.main_window.view3d.polygons or self.main_window.view3d.lines or self.main_window.view3d.frames:
            reply = QMessageBox.question(
                self, 
                "Değişiklikler", 
                "Mevcut veriler kaydedilmeyecek. Devam etmek istediğinize emin misiniz?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            return reply == QMessageBox.StandardButton.Yes
        return True
    
    def _load_from_file(self, file_path):
        """Dosyadan veri yükle"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.main_window.maindata = data
            self.main_window.view3d.set_data(
                data.get('points', {}),
                data.get('polygons', {}),
                data.get('lines', {}),
                data.get('frames', {})
            )

            self.main_window.current_file_path = file_path
            self.setWindowTitle(
                f"3D Viewer - {QFileInfo(file_path).fileName()}"
            )
            self.main_window.view3d.zoom_extents()

            logging.info(f"Dosya başarıyla açıldı: {file_path}")

        except Exception as e:
            logging.error(f"Dosya açılamadı: {e}")
    
    def _save_to_file(self, file_path):
        """Veriyi dosyaya kaydet"""
        try:
            data = {
                'points': self.main_window.view3d.points,
                'polygons': self.main_window.view3d.polygons,
                'lines': self.main_window.view3d.lines,
                'frames': self.main_window.view3d.frames
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self.main_window.current_file_path = file_path
            self.setWindowTitle(f"3D Viewer - {QFileInfo(file_path).fileName()}")
            
            logging.info("Başarılı", f"Dosya başarıyla kaydedildi: {file_path}")
            
        except Exception as e:
            logging.error(f"Error saving file: {e}")
            logging.info("Hata", f"Dosya kaydedilemedi: {str(e)}")
    
    def _import_from_json(self, file_path):
        """JSON'dan içe aktar"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.main_window.view3d.points.update(data.get('points', {}))
            self.main_window.view3d.polygons.update(data.get('polygons', {}))
            self.main_window.view3d.lines.update(data.get('lines', {}))
            self.main_window.view3d.frames.update(data.get('frames', {}))
            self.main_window.view3d.rebuild()
            self.main_window.view3d.zoom_extents()
            
            logging.info("Başarılı", f"JSON dosyası içe aktarıldı: {file_path}")
            
        except Exception as e:
            logging.error(f"Error importing JSON: {e}")
            logging.info("Hata", f"JSON içe aktarılamadı: {str(e)}")
    
    def _import_from_csv(self, file_path):
        """CSV'den içe aktar"""
        try:
            import csv
            points = {}
            
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 4:
                        name = row[0].strip()
                        try:
                            x = float(row[1])
                            y = float(row[2])
                            z = float(row[3])
                            points[name] = (x, y, z)
                        except ValueError:
                            continue
            
            if points:
                self.main_window.view3d.points.update(points)
                self.main_window.view3d.rebuild()
                self.main_window.view3d.zoom_extents()
                logging.info("Başarılı", f"{len(points)} nokta içe aktarıldı!")
            else:
                logging.info("Uyarı", "Hiçbir nokta içe aktarılamadı!")
            
        except Exception as e:
            logging.error(f"Error importing CSV: {e}")
            logging.info("Hata", f"CSV içe aktarılamadı: {str(e)}")
    
    def _import_from_obj(self, file_path):
        """OBJ'den içe aktar"""
        try:
            points = {}
            polygons = []
            vertices = []
            
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    parts = line.split()
                    if not parts:
                        continue
                    
                    if parts[0] == 'v':
                        if len(parts) >= 4:
                            try:
                                x = float(parts[1])
                                y = float(parts[2])
                                z = float(parts[3])
                                vertices.append((x, y, z))
                            except ValueError:
                                continue
                    
                    elif parts[0] == 'f':
                        face_indices = []
                        for part in parts[1:]:
                            idx = part.split('/')[0]
                            if idx:
                                try:
                                    face_indices.append(int(idx) - 1)
                                except ValueError:
                                    continue
                        if face_indices:
                            polygons.append(face_indices)
            
            for i, (x, y, z) in enumerate(vertices):
                points[f"V{i+1}"] = (x, y, z)
            
            for i, indices in enumerate(polygons):
                poly_points = [f"V{idx+1}" for idx in indices if idx < len(vertices)]
                if len(poly_points) >= 3:
                    self.main_window.view3d.polygons[f"Poly{i+1}"] = poly_points
            
            self.main_window.view3d.points.update(points)
            self.main_window.view3d.rebuild()
            self.main_window.view3d.zoom_extents()
            
            logging.info("Başarılı", f"OBJ içe aktarıldı!\n{len(points)} nokta, {len(polygons)} poligon")
            
        except Exception as e:
            logging.error(f"Error importing OBJ: {e}")
            logging.info("Hata", f"OBJ içe aktarılamadı: {str(e)}")
    
    def _export_to_json(self, file_path):
        """JSON'a dışa aktar"""
        try:
            data = {
                'points': self.main_window.view3d.points,
                'polygons': self.main_window.view3d.polygons,
                'lines': self.main_window.view3d.lines,
                'frames': self.main_window.view3d.frames
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logging.info("Başarılı", f"JSON'a dışa aktarıldı: {file_path}")
            
        except Exception as e:
            logging.error(f"Error exporting JSON: {e}")
            logging.info("Hata", f"JSON dışa aktarılamadı: {str(e)}")
    
    def _export_to_obj(self, file_path):
        """OBJ'ye dışa aktar"""
        try:
            vertex_map = {}
            vertices = []
            
            for name, coords in self.main_window.view3d.points.items():
                vertex_map[name] = len(vertices)
                vertices.append(coords)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("# Exported from 3D Viewer\n")
                
                for x, y, z in vertices:
                    f.write(f"v {x:.6f} {y:.6f} {z:.6f}\n")
                
                f.write("\n")
                
                for poly_name, poly_points in self.main_window.view3d.polygons.items():
                    indices = []
                    for p_name in poly_points:
                        if p_name in vertex_map:
                            indices.append(vertex_map[p_name] + 1)
                    if len(indices) >= 3:
                        f.write(f"f {' '.join(str(idx) for idx in indices)}\n")
            
            logging.info("Başarılı", f"OBJ'ye dışa aktarıldı: {file_path}")
            
        except Exception as e:
            logging.error(f"Error exporting OBJ: {e}")
            logging.info("Hata", f"OBJ dışa aktarılamadı: {str(e)}")
    
    def _export_to_png(self, file_path):
        """PNG olarak dışa aktar"""
        try:
            from PySide6.QtGui import QPixmap
            
            pixmap = self.main_window.view3d.grab()
            pixmap.save(file_path, "PNG")
            
            logging.info("Başarılı", f"PNG olarak kaydedildi: {file_path}")
            
        except Exception as e:
            logging.error(f"Error exporting PNG: {e}")
            logging.info("Hata", f"PNG kaydedilemedi: {str(e)}")

    def _build_view_menu(self):
        view_menu = self.menuBar().addMenu("&View")

        toggle_data_panel = Action("Data Panel", self)
        toggle_data_panel.setShortcut("Ctrl+D")
        toggle_data_panel.setCheckable(True)
        toggle_data_panel.setChecked(self.data_dock.isVisible())
        toggle_data_panel.triggered.connect(self.data_dock.setVisible)

        # Dock görünürlüğü değişince menü check güncellensin
        self.data_dock.visibilityChanged.connect(toggle_data_panel.setChecked)

        view_menu.addAction(toggle_data_panel)