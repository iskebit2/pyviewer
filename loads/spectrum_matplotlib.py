"""
TBDY 2018 Deprem Spektrum Grafiği
matplotlib tabanlı - PC ve Pydroid uyumlu
"""

import os
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator


class SpectrumPlot:
    """
    matplotlib tabanlı spektrum çizici.

    Kullanım:
        plot = SpectrumPlot()
        plot.set_spectrum(earthquake_analysis)
        plot.show()
    """

    def __init__(self, parent=None):
        self._spectrum = None
        self.fig = None
        self.ax = None
        self._parent = parent

    # =====================================================
    # ANA GİRİŞ
    # =====================================================

    def set_spectrum(self, spectrum):
        """EarthquakeLoad nesnesinden spektrum verilerini alır."""
        if spectrum.Sae_DD2 is None or spectrum.Sae_DD3 is None:
            raise ValueError("Spektrum henüz hesaplanmamış.")

        self._spectrum = spectrum
        self._draw()

    def show(self, save_path=None):
        """
        Grafiği gösterir.

        Args:
            save_path: Verilirse PNG olarak kaydeder.
                       None ise varsayılan yola kaydeder.
        """
        if self.fig is None:
            print("[SpectrumPlot] Önce set_spectrum() çağırın.")
            return

        # PNG kaydetme (Pydroid fallback)
        if save_path is None:
            save_path = self._get_default_save_path()

        try:
            self.fig.savefig(save_path, dpi=110, bbox_inches="tight")
            print(f"[SpectrumPlot] PNG kaydedildi: {save_path}")
        except Exception as e:
            print(f"[SpectrumPlot] PNG kaydetme hatası: {e}")

        # Ekranda göster
        try:
            plt.show()
        except Exception as e:
            print(f"[SpectrumPlot] plt.show() hatası: {e}")
            print(f"[SpectrumPlot] Grafik dosyaya kaydedildi: {save_path}")

    def clear(self):
        """Figürü kapatır."""
        self._spectrum = None
        if self.fig is not None:
            plt.close(self.fig)
            self.fig = None
            self.ax = None

    def save(self, path):
        """Grafiği belirtilen yola kaydeder."""
        if self.fig is None:
            raise ValueError("Önce set_spectrum() çağırın.")
        self.fig.savefig(path, dpi=110, bbox_inches="tight")
        return path

    # =====================================================
    # YARDIMCI
    # =====================================================

    def _get_default_save_path(self):
        """Platform'a göre varsayılan kayıt yolu."""
        # Android
        if os.path.exists("/storage/emulated/0"):
            return "/storage/emulated/0/spectrum.png"
        # PC (Windows/Linux/Mac)
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        if os.path.exists(desktop):
            return os.path.join(desktop, "spectrum.png")
        return "spectrum.png"

    # =====================================================
    # ÇİZİM
    # =====================================================

    def _draw(self):
        s = self._spectrum

        # Eski figürü kapat
        if self.fig is not None:
            plt.close(self.fig)

        # Yeni figür
        self.fig, self.ax = plt.subplots(figsize=(10, 6), dpi=100)

        # ---- Ana eğriler ----
        self.ax.plot(
            s.T_values, s.Sae_DD2,
            color="#1f77b4", linewidth=2.5,
            label="DD-2", zorder=3
        )
        self.ax.plot(
            s.T_values, s.Sae_DD3,
            color="#d62728", linewidth=2.5,
            label="DD-3", zorder=3
        )

        # ---- Karakteristik periyotlar ----
        self._add_vline(s.TA_DD2, "TA (DD-2)", "#1f77b4", ":")
        self._add_vline(s.TB_DD2, "TB (DD-2)", "#1f77b4", "--")
        self._add_vline(s.TA_DD3, "TA (DD-3)", "#d62728", ":")
        self._add_vline(s.TB_DD3, "TB (DD-3)", "#d62728", "--")

        # ---- T1 (hakim periyot) ----
        if s.T1 is not None and s.T1 > 0:
            self._add_vline(
                s.T1,
                f"T₁ = {s.T1:.3f} s",
                "#2ca02c",
                "-.",
                linewidth=2.0
            )
            self._add_t1_points(s)

        # ---- Eksenler ----
        self.ax.set_xlabel("Periyot T (s)", fontsize=12, fontweight="bold")
        self.ax.set_ylabel("Spektral İvme Sae (g)", fontsize=12, fontweight="bold")
        self.ax.set_title(
            "TBDY 2018 Tasarım Spektrumları",
            fontsize=14, fontweight="bold", pad=15
        )

        # ---- Grid ----
        self.ax.grid(True, which="major", alpha=0.35, linestyle="-")
        self.ax.grid(True, which="minor", alpha=0.15, linestyle=":")

        # ---- Legend ----
        self.ax.legend(
            loc="upper right",
            fontsize=10,
            framealpha=0.95,
            edgecolor="#888"
        )

        # ---- Sınırlar ----
        self.ax.set_xlim(0, s.T_MAX)

        ymax = max(np.max(s.Sae_DD2), np.max(s.Sae_DD3))
        self.ax.set_ylim(0, ymax * 1.15)

        # ---- Tick'ler ----
        self.ax.xaxis.set_major_locator(MultipleLocator(0.5))
        self.ax.xaxis.set_minor_locator(MultipleLocator(0.1))
        self.ax.yaxis.set_major_locator(MultipleLocator(0.1))
        self.ax.yaxis.set_minor_locator(MultipleLocator(0.02))

        # ---- İnce ayar ----
        for spine in self.ax.spines.values():
            spine.set_linewidth(1.1)
            spine.set_color("#555")

        self.fig.tight_layout()

    # =====================================================
    # DÜŞEY ÇİZGİLER
    # =====================================================

    def _add_vline(self, x, label, color, style, linewidth=1.2):
        """Belirtilen x için düşey çizgi ekler."""
        if x is None or x <= 0:
            return

        self.ax.axvline(
            x=x,
            color=color,
            linestyle=style,
            linewidth=linewidth,
            alpha=0.75,
            zorder=2
        )

        # Etiket (üst kısma)
        ymax = self.ax.get_ylim()[1]
        self.ax.text(
            x, ymax * 0.95,
            f" {label}",
            rotation=90,
            fontsize=8,
            color=color,
            ha="left",
            va="top",
            fontweight="bold"
        )

    # =====================================================
    # T1 NOKTALARI
    # =====================================================

    def _add_t1_points(self, s):
        """T1 periyodundaki spektral ivme noktalarını işaretler."""
        T = s.T1
        if T <= 0:
            return

        # Spektral ivmeler
        sae_dd2 = s.sae(T, s.dd2["Sds"], s.dd2["Sd1"],
                        s.TA_DD2, s.TB_DD2, s.TL)
        sae_dd3 = s.sae(T, s.dd3["Sds"], s.dd3["Sd1"],
                        s.TA_DD3, s.TB_DD3, s.TL)

        # Noktalar
        self.ax.plot(
            T, sae_dd2, "o",
            color="#1f77b4", markersize=10,
            markeredgecolor="white",
            markeredgewidth=1.5,
            zorder=5
        )
        self.ax.plot(
            T, sae_dd3, "o",
            color="#d62728", markersize=10,
            markeredgecolor="white",
            markeredgewidth=1.5,
            zorder=5
        )

        # Değer etiketleri
        self.ax.annotate(
            f"DD-2: {sae_dd2:.3f} g",
            xy=(T, sae_dd2),
            xytext=(12, 10),
            textcoords="offset points",
            fontsize=10,
            color="#1f77b4",
            fontweight="bold",
            bbox=dict(
                boxstyle="round,pad=0.3",
                facecolor="white",
                edgecolor="#1f77b4",
                alpha=0.9
            ),
            arrowprops=dict(
                arrowstyle="->",
                color="#1f77b4",
                lw=1.2
            ),
            zorder=6
        )
        self.ax.annotate(
            f"DD-3: {sae_dd3:.3f} g",
            xy=(T, sae_dd3),
            xytext=(12, -25),
            textcoords="offset points",
            fontsize=10,
            color="#d62728",
            fontweight="bold",
            bbox=dict(
                boxstyle="round,pad=0.3",
                facecolor="white",
                edgecolor="#d62728",
                alpha=0.9
            ),
            arrowprops=dict(
                arrowstyle="->",
                color="#d62728",
                lw=1.2
            ),
            zorder=6
        )
        
