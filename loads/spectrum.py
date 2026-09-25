#spectrum.py
"""
TBDY 2018 Deprem Hesapları
"""

import numpy as np


class EarthquakeLoad:
    """
    TBDY 2018 deprem hesapları.

    DataPanel'den gelen earthquake_config verisi ile çalışır.

    Şimdilik T1, TBDY ampirik periyot bağıntısından hesaplanır.
    İleride SAP2000 modal periyodu dışarıdan verilebilir.
    """

    TL = 6.0
    T_MIN = 0.01
    T_MAX = 4.0
    N_POINTS = 200

    # Şimdilik geçici değer.
    # Taşıyıcı sistem belli olduğunda config'e alınabilir.
    DEFAULT_CT = 0.10

    def __init__(
        self,
        R,
        D,
        I,
        kappa,
        Hn,
        gamma_E,
        n,
        e,
        ee,
        zemin_sinifi,
        limit_raw,
        load_cases,
        drift_combo_names,
        has_irregularity,
        dd2,
        dd3,
    ):
        # -------------------------------------------------
        # Genel deprem parametreleri
        # -------------------------------------------------

        self.R = R
        self.D = D
        self.I = I
        self.kappa = kappa
        self.Hn = Hn
        self.gamma_E = gamma_E
        self.n = n
        self.e = e
        self.ee = ee
        self.zemin_sinifi = zemin_sinifi
        self.limit_raw = limit_raw
        self.load_cases = load_cases
        self.drift_combo_names = drift_combo_names
        self.has_irregularity = has_irregularity

        # -------------------------------------------------
        # DD-2 / DD-3
        # -------------------------------------------------

        self.dd2 = dd2
        self.dd3 = dd3

        # -------------------------------------------------
        # Spektrum
        # -------------------------------------------------

        self.T_values = np.linspace(
            self.T_MIN,
            self.T_MAX,
            self.N_POINTS,
        )

        self.TA_DD2 = None
        self.TB_DD2 = None

        self.TA_DD3 = None
        self.TB_DD3 = None

        self.TpA = None
        self.T1 = None

        self.Sae_DD2 = None
        self.Sae_DD3 = None

        self.lambda_val = None

        # -------------------------------------------------
        # Hesap
        # -------------------------------------------------

        self._calculate_period_params()

        # Şimdilik SAP2000 yerine ampirik T1
        self.calculate()

    # =====================================================
    # SPEKTRUM PARAMETRELERİ
    # =====================================================

    def _calculate_period_params(self):
        """DD-2 ve DD-3 için TA ve TB değerlerini hesaplar."""

        self.TA_DD2 = (
            0.2 *
            self.dd2["Sd1"] /
            self.dd2["Sds"]
        )

        self.TB_DD2 = (
            self.dd2["Sd1"] /
            self.dd2["Sds"]
        )

        self.TA_DD3 = (
            0.2 *
            self.dd3["Sd1"] /
            self.dd3["Sds"]
        )

        self.TB_DD3 = (
            self.dd3["Sd1"] /
            self.dd3["Sds"]
        )

    # =====================================================
    # AMPİRİK HAKİM PERİYOT
    # =====================================================

    def calculate_tpA(self, Ct=None):
        """
        Ampirik hakim doğal titreşim periyodu.

        TpA = Ct * Hn ** 0.75

        Şimdilik geçici T1 üretiminde kullanılıyor.
        """

        if Ct is None:
            Ct = self.DEFAULT_CT

        self.TpA = Ct * self.Hn ** 0.75

        return self.TpA

    # =====================================================
    # SPEKTRAL İVME
    # =====================================================

    @staticmethod
    def sae(
        T,
        Sds,
        Sd1,
        TA,
        TB,
        TL=6.0,
    ):
        """
        Elastik tasarım spektrumu Sae(T).
        """

        if T <= TA:

            return (
                0.4 +
                0.6 * T / TA
            ) * Sds

        elif T <= TB:

            return Sds

        elif T <= TL:

            return Sd1 / T

        else:

            return Sd1 * TL / T**2

    # =====================================================
    # SPEKTRUM HESABI
    # =====================================================

    def _calculate_spectrum(self):
        """DD-2 ve DD-3 spektrumlarını hesaplar."""

        self.Sae_DD2 = np.array([
            self.sae(
                T,
                self.dd2["Sds"],
                self.dd2["Sd1"],
                self.TA_DD2,
                self.TB_DD2,
                self.TL,
            )
            for T in self.T_values
        ])

        self.Sae_DD3 = np.array([
            self.sae(
                T,
                self.dd3["Sds"],
                self.dd3["Sd1"],
                self.TA_DD3,
                self.TB_DD3,
                self.TL,
            )
            for T in self.T_values
        ])

    # =====================================================
    # LAMBDA
    # =====================================================

    def _calculate_lambda(self):
        """
        DD-3 / DD-2 spektral ivme oranı.

        Lambda, T1 periyodundaki spektral ivmeler
        üzerinden hesaplanır.
        """

        if self.T1 is None or self.T1 <= 0:
            self.lambda_val = None
            return None

        sae_dd2 = self.sae(
            self.T1,
            self.dd2["Sds"],
            self.dd2["Sd1"],
            self.TA_DD2,
            self.TB_DD2,
            self.TL,
        )

        sae_dd3 = self.sae(
            self.T1,
            self.dd3["Sds"],
            self.dd3["Sd1"],
            self.TA_DD3,
            self.TB_DD3,
            self.TL,
        )

        if sae_dd2 == 0:
            self.lambda_val = None
        else:
            self.lambda_val = sae_dd3 / sae_dd2

        return self.lambda_val

    # =====================================================
    # ANA HESAP
    # =====================================================

    def calculate(self, T1=None):
        """
        Deprem hesabını çalıştırır.

        T1 verilirse SAP2000 vb. dış kaynaktan gelen
        hakim periyot kullanılır.

        T1 verilmezse şimdilik TpA kullanılır.
        """

        # ---------------------------------------------
        # T1
        # ---------------------------------------------

        if T1 is None:
            self.T1 = self.calculate_tpA()
        else:
            self.T1 = float(T1)

        # ---------------------------------------------
        # Spektrum
        # ---------------------------------------------

        self._calculate_spectrum()

        # ---------------------------------------------
        # Lambda
        # ---------------------------------------------

        self._calculate_lambda()

        return self

    # =====================================================
    # DIŞARIDAN T1 VERME
    # =====================================================

    def set_period(self, T1):
        """
        SAP2000'den alınan gerçek T1 değerini kullanır.
        """

        return self.calculate(T1=T1)

    # =====================================================
    # RAPOR
    # =====================================================

    def report(self):
        """
        DataPanel/MainWindow tarafından kullanılacak
        hesap sonuçlarını döndürür.
        """

        return {
            "Deprem Parametreleri": {
                "R": self.R,
                "D": self.D,
                "I": self.I,
                "kappa": self.kappa,
                "Hn (m)": self.Hn,
                "gamma_E": self.gamma_E,
                "n": self.n,
                "Zemin Sınıfı": self.zemin_sinifi,
                "Düzensizlik": self.has_irregularity,
            },

            "DD-2": {
                "Ss": self.dd2["Ss"],
                "S1": self.dd2["S1"],
                "PGA": self.dd2["PGA"],
                "PGV": self.dd2["PGV"],
                "Fs": self.dd2["Fs"],
                "F1": self.dd2["F1"],
                "Sds": self.dd2["Sds"],
                "Sd1": self.dd2["Sd1"],
                "TA (s)": self.TA_DD2,
                "TB (s)": self.TB_DD2,
            },

            "DD-3": {
                "Ss": self.dd3["Ss"],
                "S1": self.dd3["S1"],
                "PGA": self.dd3["PGA"],
                "PGV": self.dd3["PGV"],
                "Fs": self.dd3["Fs"],
                "F1": self.dd3["F1"],
                "Sds": self.dd3["Sds"],
                "Sd1": self.dd3["Sd1"],
                "TA (s)": self.TA_DD3,
                "TB (s)": self.TB_DD3,
            },

            "Spektrum": {
                "TpA (s)": self.TpA,
                "T1 (s)": self.T1,
                "Lambda": self.lambda_val,
            },

            "Yük Durumları": {
                "load_cases": self.load_cases,
                "drift_combinations": self.drift_combo_names,
            },

            "Öteleme": {
                "limit_raw": self.limit_raw,
            },
        }