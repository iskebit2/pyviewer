
import math

from kivy.uix.widget import Widget
from kivy.graphics import (
    Color,
    Line,
    Rectangle,
)
from kivy.core.text import Label as CoreLabel
from kivy.core.window import Window


class SpectrumPlot(Widget):
    """
    TBDY 2018 tasarım spektrumları

    Kullanım:

        plot = SpectrumPlot()

        plot.set_spectrum(earthquake_analysis)

        plot.export_png("/sdcard/spectrum.png")
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._spectrum = None

        self.margin_left = 70
        self.margin_right = 25
        self.margin_top = 45
        self.margin_bottom = 60

        self.bind(
            size=self._redraw,
            pos=self._redraw
        )

    # =========================================================
    # ANA GİRİŞ
    # =========================================================

    def set_spectrum(self, spectrum):
        """
        EarthquakeLoad nesnesinden spektrum verilerini alır.
        """

        if spectrum.Sae_DD2 is None or spectrum.Sae_DD3 is None:
            raise ValueError(
                "Spektrum henüz hesaplanmamış."
            )

        self._spectrum = spectrum

        self._redraw()

    def clear(self):
        """
        Grafiği temizler.
        """

        self._spectrum = None
        self.canvas.clear()

    # =========================================================
    # ÇİZİM
    # =========================================================

    def _redraw(self, *args):

        self.canvas.clear()

        if self._spectrum is None:
            self._draw_empty()
            return

        self._draw_spectrum()

    # =========================================================
    # BOŞ GRAFİK
    # =========================================================

    def _draw_empty(self):

        self._draw_text(
            "Spektrum hesabı bekleniyor...",
            self.center_x,
            self.center_y,
            font_size=16,
            halign="center"
        )

    # =========================================================
    # ANA GRAFİK
    # =========================================================

    def _draw_spectrum(self):

        s = self._spectrum

        # -----------------------------------------------------
        # Grafik alanı
        # -----------------------------------------------------

        x0 = self.x + self.margin_left
        y0 = self.y + self.margin_bottom

        graph_width = (
            self.width
            - self.margin_left
            - self.margin_right
        )

        graph_height = (
            self.height
            - self.margin_bottom
            - self.margin_top
        )

        if graph_width <= 10 or graph_height <= 10:
            return

        # -----------------------------------------------------
        # Veriler
        # -----------------------------------------------------

        T_values = list(s.T_values)

        DD2 = list(s.Sae_DD2)
        DD3 = list(s.Sae_DD3)

        if not T_values:
            return

        T_max = float(s.T_MAX)

        if T_max <= 0:
            T_max = max(T_values)

        ymax = max(
            max(DD2),
            max(DD3)
        )

        ymax *= 1.15

        if ymax <= 0:
            ymax = 1.0

        # -----------------------------------------------------
        # Arka plan
        # -----------------------------------------------------

        with self.canvas:

            Color(
                0.98,
                0.98,
                0.98,
                1
            )

            Rectangle(
                pos=(x0, y0),
                size=(graph_width, graph_height)
            )

        # -----------------------------------------------------
        # Grid
        # -----------------------------------------------------

        self._draw_grid(
            x0,
            y0,
            graph_width,
            graph_height,
            T_max,
            ymax
        )

        # -----------------------------------------------------
        # Eksenler
        # -----------------------------------------------------

        with self.canvas:

            Color(
                0.25,
                0.25,
                0.25,
                1
            )

            Line(
                points=[
                    x0,
                    y0,
                    x0 + graph_width,
                    y0
                ],
                width=1.2
            )

            Line(
                points=[
                    x0,
                    y0,
                    x0,
                    y0 + graph_height
                ],
                width=1.2
            )

        # -----------------------------------------------------
        # DD-2
        # -----------------------------------------------------

        self._draw_curve(
            T_values,
            DD2,
            x0,
            y0,
            graph_width,
            graph_height,
            T_max,
            ymax,
            color=(0.12, 0.47, 0.71, 1),
            width=2.5
        )

        # -----------------------------------------------------
        # DD-3
        # -----------------------------------------------------

        self._draw_curve(
            T_values,
            DD3,
            x0,
            y0,
            graph_width,
            graph_height,
            T_max,
            ymax,
            color=(0.84, 0.15, 0.15, 1),
            width=2.5
        )

        # -----------------------------------------------------
        # TA / TB
        # -----------------------------------------------------

        self._draw_vline(
            s.TA_DD2,
            "TA (DD-2)",
            x0,
            y0,
            graph_width,
            graph_height,
            T_max,
            color=(0.12, 0.47, 0.71, 1),
            dash=True
        )

        self._draw_vline(
            s.TB_DD2,
            "TB (DD-2)",
            x0,
            y0,
            graph_width,
            graph_height,
            T_max,
            color=(0.12, 0.47, 0.71, 1),
            dash=False
        )

        self._draw_vline(
            s.TA_DD3,
            "TA (DD-3)",
            x0,
            y0,
            graph_width,
            graph_height,
            T_max,
            color=(0.84, 0.15, 0.15, 1),
            dash=True
        )

        self._draw_vline(
            s.TB_DD3,
            "TB (DD-3)",
            x0,
            y0,
            graph_width,
            graph_height,
            T_max,
            color=(0.84, 0.15, 0.15, 1),
            dash=False
        )

        # -----------------------------------------------------
        # T1
        # -----------------------------------------------------

        if s.T1 is not None and s.T1 > 0:

            self._draw_vline(
                s.T1,
                f"T1 = {s.T1:.3f} s",
                x0,
                y0,
                graph_width,
                graph_height,
                T_max,
                color=(0.17, 0.63, 0.17, 1),
                dash=True
            )

            self._draw_t1_points(
                s,
                x0,
                y0,
                graph_width,
                graph_height,
                T_max,
                ymax
            )

        # -----------------------------------------------------
        # Eksen yazıları
        # -----------------------------------------------------

        self._draw_axis_labels(
            x0,
            y0,
            graph_width,
            graph_height,
            T_max,
            ymax
        )

        # -----------------------------------------------------
        # Başlık
        # -----------------------------------------------------

        self._draw_text(
            "TBDY 2018 Tasarım Spektrumları",
            self.center_x,
            self.top - 8,
            font_size=18,
            bold=True,
            halign="center"
        )

        # -----------------------------------------------------
        # Legend
        # -----------------------------------------------------

        self._draw_legend()

    # =========================================================
    # EĞRİ
    # =========================================================

    def _draw_curve(
        self,
        x_values,
        y_values,
        x0,
        y0,
        width,
        height,
        x_max,
        y_max,
        color,
        width_line=2.5,
        **kwargs
    ):

        points = []

        for T, Sa in zip(x_values, y_values):

            x = x0 + (T / x_max) * width
            y = y0 + (Sa / y_max) * height

            points.extend([x, y])

        with self.canvas:

            Color(*color)

            Line(
                points=points,
                width=width_line,
                **kwargs
            )

    # =========================================================
    # GRID
    # =========================================================

    def _draw_grid(
        self,
        x0,
        y0,
        width,
        height,
        T_max,
        ymax
    ):

        with self.canvas:

            # Dikey major grid
            Color(
                0.75,
                0.75,
                0.75,
                0.45
            )

            t = 0.0

            while t <= T_max + 0.001:

                x = x0 + (t / T_max) * width

                Line(
                    points=[
                        x,
                        y0,
                        x,
                        y0 + height
                    ],
                    width=0.7
                )

                t += 0.5

            # Yatay major grid
            value = 0.0

            while value <= ymax + 0.001:

                y = y0 + (value / ymax) * height

                Line(
                    points=[
                        x0,
                        y,
                        x0 + width,
                        y
                    ],
                    width=0.7
                )

                value += 0.1

    # =========================================================
    # DÜŞEY ÇİZGİ
    # =========================================================

    def _draw_vline(
        self,
        value,
        label,
        x0,
        y0,
        width,
        height,
        x_max,
        color,
        dash=False
    ):

        if value is None or value <= 0:
            return

        if value > x_max:
            return

        x = x0 + (value / x_max) * width

        with self.canvas:

            Color(*color)

            if dash:

                # Kesikli çizgi
                y = y0

                while y < y0 + height:

                    Line(
                        points=[
                            x,
                            y,
                            x,
                            min(y + 6, y0 + height)
                        ],
                        width=1
                    )

                    y += 12

            else:

                Line(
                    points=[
                        x,
                        y0,
                        x,
                        y0 + height
                    ],
                    width=1.2
                )

        self._draw_text(
            label,
            x + 5,
            y0 + height - 10,
            font_size=10,
            color=color[:3],
            rotation=90
        )

    # =========================================================
    # T1 NOKTALARI
    # =========================================================

    def _draw_t1_points(
        self,
        s,
        x0,
        y0,
        width,
        height,
        x_max,
        y_max
    ):

        T = s.T1

        sae_dd2 = s.sae(
            T,
            s.dd2["Sds"],
            s.dd2["Sd1"],
            s.TA_DD2,
            s.TB_DD2,
            s.TL
        )

        sae_dd3 = s.sae(
            T,
            s.dd3["Sds"],
            s.dd3["Sd1"],
            s.TA_DD3,
            s.TB_DD3,
            s.TL
        )

        x = x0 + (T / x_max) * width

        # -----------------------------------------------------
        # DD2 noktası
        # -----------------------------------------------------

        y2 = y0 + (sae_dd2 / y_max) * height

        self._draw_point(
            x,
            y2,
            color=(0.12, 0.47, 0.71, 1)
        )

        self._draw_text(
            f"DD-2: {sae_dd2:.3f} g",
            x + 12,
            y2 + 10,
            font_size=10,
            color=(0.12, 0.47, 0.71),
            bold=True
        )

        # -----------------------------------------------------
        # DD3 noktası
        # -----------------------------------------------------

        y3 = y0 + (sae_dd3 / y_max) * height

        self._draw_point(
            x,
            y3,
            color=(0.84, 0.15, 0.15, 1)
        )

        self._draw_text(
            f"DD-3: {sae_dd3:.3f} g",
            x + 12,
            y3 - 25,
            font_size=10,
            color=(0.84, 0.15, 0.15),
            bold=True
        )

    # =========================================================
    # NOKTA
    # =========================================================

    def _draw_point(
        self,
        x,
        y,
        color
    ):

        with self.canvas:

            Color(
                1,
                1,
                1,
                1
            )

            # Beyaz dış halka
            from kivy.graphics import Ellipse

            Ellipse(
                pos=(x - 6, y - 6),
                size=(12, 12)
            )

            Color(*color)

            Ellipse(
                pos=(x - 4, y - 4),
                size=(8, 8)
            )

    # =========================================================
    # EKSENLER
    # =========================================================

    def _draw_axis_labels(
        self,
        x0,
        y0,
        width,
        height,
        T_max,
        ymax
    ):

        # X tickleri
        t = 0.0

        while t <= T_max + 0.001:

            x = x0 + (t / T_max) * width

            self._draw_text(
                f"{t:.1f}",
                x,
                y0 - 25,
                font_size=9,
                halign="center"
            )

            t += 0.5

        # Y tickleri
        value = 0.0

        while value <= ymax + 0.001:

            y = y0 + (value / ymax) * height

            self._draw_text(
                f"{value:.1f}",
                x0 - 12,
                y - 5,
                font_size=9,
                halign="right"
            )

            value += 0.1

        # X başlığı
        self._draw_text(
            "Periyot T (s)",
            x0 + width / 2,
            self.y + 12,
            font_size=12,
            bold=True,
            halign="center"
        )

        # Y başlığı
        self._draw_text(
            "Spektral İvme Sae (g)",
            self.x + 10,
            y0 + height / 2,
            font_size=12,
            bold=True,
            rotation=90,
            halign="center"
        )

    # =========================================================
    # LEGEND
    # =========================================================

    def _draw_legend(self):

        x = self.right - 145
        y = self.top - 55

        # DD2 çizgi
        with self.canvas:

            Color(
                0.12,
                0.47,
                0.71,
                1
            )

            Line(
                points=[
                    x,
                    y,
                    x + 25,
                    y
                ],
                width=2.5
            )

        self._draw_text(
            "DD-2",
            x + 32,
            y - 6,
            font_size=10
        )

        # DD3 çizgi
        y -= 20

        with self.canvas:

            Color(
                0.84,
                0.15,
                0.15,
                1
            )

            Line(
                points=[
                    x,
                    y,
                    x + 25,
                    y
                ],
                width=2.5
            )

        self._draw_text(
            "DD-3",
            x + 32,
            y - 6,
            font_size=10
        )

    # =========================================================
    # TEXT
    # =========================================================

    def _draw_text(
        self,
        text,
        x,
        y,
        font_size=12,
        color=(0.15, 0.15, 0.15),
        bold=False,
        rotation=0,
        halign="left"
    ):

        label = CoreLabel(
            text=text,
            font_size=font_size,
            bold=bold,
            color=(
                *color,
                1
            )
        )

        label.refresh()

        texture = label.texture

        tx = x
        ty = y

        if halign == "center":
            tx -= texture.width / 2

        elif halign == "right":
            tx -= texture.width

        with self.canvas:

            PushMatrix = __import__(
                "kivy.graphics",
                fromlist=["PushMatrix"]
            ).PushMatrix

            PopMatrix = __import__(
                "kivy.graphics",
                fromlist=["PopMatrix"]
            ).PopMatrix

            Rotate = __import__(
                "kivy.graphics",
                fromlist=["Rotate"]
            ).Rotate

            PushMatrix()

            if rotation:
                Rotate(
                    angle=rotation,
                    origin=(x, y)
                )

            Rectangle(
                texture=texture,
                pos=(tx, ty),
                size=texture.size
            )

            PopMatrix()