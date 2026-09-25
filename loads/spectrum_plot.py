import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtGui import QPen, QFont
from PySide6.QtWidgets import QWidget, QVBoxLayout


class SpectrumPlot(QWidget):
    """TBDY 2018 deprem spektrumlarını gösteren Qt grafiği."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self._spectrum = None

        self._create_plot()

    # =====================================================
    # GRAFİK OLUŞTURMA
    # =====================================================

    def _create_plot(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.plot = pg.PlotWidget()
        layout.addWidget(self.plot)

        # -------------------------------------------------
        # Eksenler
        # -------------------------------------------------

        self.plot.setLabel(
            "bottom",
            "Periyot",
            units="s",
        )

        self.plot.setLabel(
            "left",
            "Spektral İvme",
            units="g",
        )

        self.plot.setTitle(
            "TBDY 2018 Tasarım Spektrumları"
        )

        # -------------------------------------------------
        # Grid
        # -------------------------------------------------

        self.plot.showGrid(
            x=True,
            y=True,
            alpha=0.25,
        )

        # -------------------------------------------------
        # Legend
        # -------------------------------------------------

        self.plot.addLegend()

        # -------------------------------------------------
        # Mouse
        # -------------------------------------------------

        self.plot.setMouseEnabled(
            x=True,
            y=True,
        )

        self.plot.setMenuEnabled(True)

        # -------------------------------------------------
        # Arka plan
        # -------------------------------------------------

        self.plot.setBackground(None)

    # =====================================================
    # SPEKTRUMU GÖSTER
    # =====================================================

    def set_spectrum(self, spectrum):
        """
        EarthquakeLoad nesnesinden spektrum verilerini alır.
        """

        if spectrum.Sae_DD2 is None:
            raise ValueError(
                "Spektrum henüz hesaplanmamış."
            )

        if spectrum.Sae_DD3 is None:
            raise ValueError(
                "Spektrum henüz hesaplanmamış."
            )

        self._spectrum = spectrum

        self._clear_plot()
        self._draw_spectra()
        self._draw_period_lines()
        self._draw_t1_point()

        self._set_range()

    # =====================================================
    # TEMİZLE
    # =====================================================

    def clear(self):
        """Grafiği temizler."""

        self._spectrum = None
        self._clear_plot()

    def _clear_plot(self):
        """PlotWidget içeriğini temizler."""

        self.plot.clear()

        # clear() legend'ı da kaldırdığı için
        # tekrar oluşturuyoruz.
        self.plot.addLegend()

    # =====================================================
    # SPEKTRUM EĞRİLERİ
    # =====================================================

    def _draw_spectra(self):

        spectrum = self._spectrum

        self.plot.plot(
            spectrum.T_values,
            spectrum.Sae_DD2,
            pen=pg.mkPen(
                width=2.5
            ),
            name="DD-2",
        )

        self.plot.plot(
            spectrum.T_values,
            spectrum.Sae_DD3,
            pen=pg.mkPen(
                width=2.5
            ),
            name="DD-3",
        )

    # =====================================================
    # TA / TB / T1 ÇİZGİLERİ
    # =====================================================

    def _draw_period_lines(self):

        spectrum = self._spectrum

        # -------------------------------------------------
        # DD-2
        # -------------------------------------------------

        self._add_period_line(
            spectrum.TA_DD2,
            "DD-2 TA",
            Qt.PenStyle.DashLine,
        )

        self._add_period_line(
            spectrum.TB_DD2,
            "DD-2 TB",
            Qt.PenStyle.DotLine,
        )

        # -------------------------------------------------
        # DD-3
        # -------------------------------------------------

        self._add_period_line(
            spectrum.TA_DD3,
            "DD-3 TA",
            Qt.PenStyle.DashLine,
        )

        self._add_period_line(
            spectrum.TB_DD3,
            "DD-3 TB",
            Qt.PenStyle.DotLine,
        )

        # -------------------------------------------------
        # T1
        # -------------------------------------------------

        if spectrum.T1 is not None:

            self._add_period_line(
                spectrum.T1,
                f"T₁ = {spectrum.T1:.3f} s",
                Qt.PenStyle.DashDotLine,
            )

    def _add_period_line(
        self,
        value,
        label,
        style,
    ):
        """Düşey periyot çizgisi ekler."""

        if value is None:
            return

        line = pg.InfiniteLine(
            pos=value,
            angle=90,
            movable=False,
            pen=pg.mkPen(
                style=style,
                width=1.2,
            ),
            label=label,
            labelOpts={
                "position": 0.85,
                "fill": None,
            },
        )

        self.plot.addItem(line)

    # =====================================================
    # T1 NOKTASI
    # =====================================================

    def _draw_t1_point(self):

        spectrum = self._spectrum

        if spectrum.T1 is None:
            return

        if spectrum.T1 <= 0:
            return

        # DD-2
        sae_dd2 = spectrum.sae(
            spectrum.T1,
            spectrum.dd2["Sds"],
            spectrum.dd2["Sd1"],
            spectrum.TA_DD2,
            spectrum.TB_DD2,
            spectrum.TL,
        )

        # DD-3
        sae_dd3 = spectrum.sae(
            spectrum.T1,
            spectrum.dd3["Sds"],
            spectrum.dd3["Sd1"],
            spectrum.TA_DD3,
            spectrum.TB_DD3,
            spectrum.TL,
        )

        # DD-2 noktası
        self._add_t1_point(
            spectrum.T1,
            sae_dd2,
            "DD-2",
        )

        # DD-3 noktası
        self._add_t1_point(
            spectrum.T1,
            sae_dd3,
            "DD-3",
        )

    def _add_t1_point(
        self,
        T,
        Sae,
        label,
    ):
        """T1 üzerindeki spektral ivme noktasını gösterir."""

        scatter = pg.ScatterPlotItem(
            [T],
            [Sae],
            size=10,
            pen=pg.mkPen(width=1.5),
            brush=pg.mkBrush("blue"),
        )

        self.plot.addItem(scatter)

        text = pg.TextItem(
            text=f"{label}: {Sae:.3f} g",
            anchor=(0, 1),
        )

        text.setPos(T, Sae)

        self.plot.addItem(text)

    # =====================================================
    # EKSEN ARALIĞI
    # =====================================================

    def _set_range(self):

        spectrum = self._spectrum

        self.plot.setXRange(
            0,
            spectrum.T_MAX,
            padding=0.02,
        )

        ymax = max(
            np.max(spectrum.Sae_DD2),
            np.max(spectrum.Sae_DD3),
        )

        self.plot.setYRange(
            0,
            ymax * 1.15,
            padding=0,
        )