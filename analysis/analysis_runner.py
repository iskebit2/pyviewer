# analysis/analysis_runner.py
"""
Analiz Modülleri Sarmalayıcı

Kendi modüllerinizi (SnowLoad, WindResults, EarthquakeLoad) burada
tek noktadan çağırır. Hata durumunda GUI'ye anlamlı mesaj döner.
"""

import traceback
from typing import Any


class AnalysisResult:
    """Analiz çıktısını GUI'ye taşımak için basit taşıyıcı."""

    def __init__(
        self,
        key: str,
        title: str,
        report: Any = None,
        error: str | None = None,
        extra: dict | None = None,
    ):
        self.key = key
        self.title = title
        self.report = report
        self.error = error
        self.extra = extra or {}

    @property
    def success(self) -> bool:
        return self.error is None

    def as_text(self) -> str:
        if not self.success:
            return f"❌ {self.title} analizi başarısız:\n{self.error}"
        return str(self.report)


# ----------------------------------------------------------------------
# Rüzgâr
# ----------------------------------------------------------------------

def run_wind(config: dict, data: dict) -> AnalysisResult:
    try:
        from windcalc.wind_results import WindResults

        result = WindResults(
            points=config.get("points", []),
            polygons=config.get("polygons", []),
            wind_config=data,
        )
        report = result.report()
        return AnalysisResult(
            key="wind",
            title="Rüzgâr",
            report=report,
            extra={"analysis": result},
        )
    except Exception as e:
        traceback.print_exc()
        return AnalysisResult(
            key="wind",
            title="Rüzgâr",
            error=f"{type(e).__name__}: {e}",
        )


# ----------------------------------------------------------------------
# Kar
# ----------------------------------------------------------------------

def run_snow(config: dict, data: dict) -> AnalysisResult:
    try:
        from loads.snow_load import SnowLoad

        snow = SnowLoad(data)
        report = snow.report()
        return AnalysisResult(
            key="snow",
            title="Kar",
            report=report,
            extra={"analysis": snow},
        )
    except Exception as e:
        traceback.print_exc()
        return AnalysisResult(
            key="snow",
            title="Kar",
            error=f"{type(e).__name__}: {e}",
        )


# ----------------------------------------------------------------------
# Deprem
# ----------------------------------------------------------------------

def run_earthquake(config: dict, data: dict) -> AnalysisResult:
    try:
        from loads.spectrum import EarthquakeLoad

        eq = EarthquakeLoad(**data)
        report = eq.report()
        return AnalysisResult(
            key="earthquake",
            title="Deprem",
            report=report,
            extra={"analysis": eq},
        )
    except Exception as e:
        traceback.print_exc()
        return AnalysisResult(
            key="earthquake",
            title="Deprem",
            error=f"{type(e).__name__}: {e}",
        )


# ----------------------------------------------------------------------
# Spektrum Grafiği
# ----------------------------------------------------------------------

def show_spectrum_plot(earthquake_analysis) -> dict:
    """
    Spektrum grafiğini oluşturur ve gösterir.

    Returns
    -------
    dict: {"ok": bool, "save_path": str | None, "error": str | None}
    """
    try:
        from loads.spectrum_matplotlib import SpectrumPlot

        plot = SpectrumPlot()
        plot.set_spectrum(earthquake_analysis)
        plot.show()

        save_path = None
        if hasattr(plot, "get_default_save_path"):
            save_path = plot.get_default_save_path()
        elif hasattr(plot, "_get_default_save_path"):
            save_path = plot._get_default_save_path()

        return {"ok": True, "save_path": save_path, "error": None}

    except Exception as e:
        traceback.print_exc()
        return {"ok": False, "save_path": None, "error": f"{type(e).__name__}: {e}"}