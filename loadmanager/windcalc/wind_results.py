import numpy as np

from docx.shared import Cm
from data.material_data import MATERIAL_LIBRARY
from utils.my_document import myDocument
from windcalc.report import create_cpe_summary_df, create_wind_force_df, get_parameters_report, show_zones
from windcalc.wind_analyzer import WindAnalyzer
from windcalc.windengine import WindEngine
from data.defaults import proje_data


class WindReport:

    W_LIST = {
        "x+": np.array([1.0, 0.0, 0.0]),
        "y+": np.array([0.0, 1.0, 0.0]),
        "x-": np.array([-1.0, 0.0, 0.0]),
        "y-": np.array([0.0, -1.0, 0.0]),
    }

    def __init__(self, proje_data):

        self.proje_data = proje_data

        self.proje_bilgileri = proje_data["proje_bilgileri"]
        self.points = proje_data["points"]
        self.polygons = proje_data["polygons"]
        self.wind_config = proje_data["wind_config"]

        self.base_engine = None
        self.parameters = None
        self.results = {}

    def analyze(self):

        # Genel rüzgar parametreleri
        self.base_engine = WindEngine(
            points=self.points,
            polygons=self.polygons,
            **self.wind_config,
        )

        self.base_engine.update_geometry()

        self.parameters = get_parameters_report(
            self.base_engine
        )

        self.results.clear()

        # Her rüzgar yönü
        for w_key, w_dir in self.W_LIST.items():

            analyzer = WindAnalyzer(
                self.points,
                self.polygons,
                w_dir,
                **self.wind_config,
            )

            engine = analyzer.engine
            engine.update_geometry()

            zones = analyzer.analyze()

            self.results[w_key] = {
                "w_dir": w_dir,
                "engine": engine,
                "zones": zones,
            }

        return self.results

    def report(self):

        if not self.results:
            self.analyze()

        report = {
            "parameters": self.parameters,
        }

        for w_key, result in self.results.items():

            zones = result["zones"]
            engine = result["engine"]

            report[w_key] = {
                "cpe": create_cpe_summary_df(zones),
                "wind_force": create_wind_force_df(
                    zones,
                    engine,
                ),
            }

        return report


if __name__ == "__main__":
    wind_report = WindReport(proje_data)
    wind_report.analyze()
    print(wind_report.report())