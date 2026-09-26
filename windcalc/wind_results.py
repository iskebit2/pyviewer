# main_wind.py
import json
from windcalc.analysis import analyze, ZoneBundle
from windcalc.visualize import draw_bundle_grid
from windcalc.report import build_full_report, print_console_summary
import matplotlib.pyplot as plt
from windcalc.report import build_full_report, print_console_summary

class WindResults:
    def __init__(self, points= {}, polygons= {}, wind_config= {}, file_path= "examples/complex_roof.json"):

        self.points = points
        self.polygons = polygons
        self.wind_config = wind_config
        self.file_path = file_path
        self.bundle = None
        if not points or not polygons:
            self.load_from_file()
        self.run_()


    def _load_from_file(self,file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except Exception as e:
            print(f"Dosya açılamadı: {e}")
            return {}

    def load_from_file(self):
        data = self._load_from_file(self.file_path)
        self.points = data["points"]
        self.polygons = data["polygons"]
        self.wind_config = data["wind_config"]


    def run_(self, export_doc= False):
        
        
        if not self.points or not self.polygons:
            return

        self.bundle = analyze(
                points=self.points,
                polygons=self.polygons,
                **self.wind_config
            )

    def show_plot(self) -> None:
        # Visualize the results
        print("\nDisplaying visualization...")
        fig = draw_bundle_grid(self.bundle, figsize=(12, 10))
        plt.show()

    def create_docx(self):
        # Generate DOCX report
    
        report_filename = "wind_analysis_report.docx"
        print(f"\nGenerating DOCX report: {report_filename}")
        build_full_report(self.bundle, filename=report_filename)
        print(f"Report saved to {report_filename}")

    def report(self) -> None:
        return print_console_summary(self.bundle)

if __name__ == "__main__":
    app= WindResults(file_path= "examples/monopitch_roof.json")
    rapor = app.report()
    print(rapor)
