# gui/panels.py
"""
Yük Atama GUI - Kivy
Seçilen döşeme/kirişe kütüphaneden ölü ve hareketli yük atar.
"""

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.togglebutton import ToggleButton
from kivy.properties import StringProperty, NumericProperty, ListProperty
from kivy.metrics import dp

from data.material_data import MATERIAL_WEIGHTS, LIVE_LOADS
from data.preset_loader import PresetLibrary



from loads.load_definition import LoadDefinition, LoadComponent
from loads.load_manager import LoadManager


# ============================================================
# GLOBAL LOAD MANAGER
# ============================================================

load_manager = LoadManager(material_weights=MATERIAL_WEIGHTS)
preset_library = PresetLibrary()

def set_globals(manager: LoadManager, library: PresetLibrary):
    global load_manager, preset_library
    load_manager = manager
    preset_library = library
# ============================================================
# YARDIMCI FONKSİYONLAR
# ============================================================

def malzeme_listesi_getir():
    """MATERIAL_WEIGHTS sözlüğünden malzeme listesi döner."""
    return sorted(MATERIAL_WEIGHTS.keys())


def canli_yuk_listesi_getir():
    """LIVE_LOADS sözlüğünden Q yük listesi döner."""
    return [
        (k, v["name"], v["value"])
        for k, v in LIVE_LOADS.items()
    ]


def benzersiz_id_uret(prefix: str) -> str:
    """Verilen prefix ile benzersiz bir ID üretir (G01, G02... / Q01, Q02...)."""
    mevcut = [
        d.id for d in load_manager.definitions.values()
        if d.id.startswith(prefix)
    ]
    sayi = 1
    while f"{prefix}{sayi:02d}" in mevcut:
        sayi += 1
    return f"{prefix}{sayi:02d}"


# ============================================================
# YÜK BİLEŞEN SATIRI (G yükleri için)
# ============================================================

class BilesenSatiri(BoxLayout):
    """Bir G yükü bileşenini temsil eden satır: Ad + Tip + Değer/Malzeme + Kalınlık"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.height = dp(40)
        self.spacing = dp(4)
        self.padding = dp(2)

        # Bileşen adı
        self.ad_input = TextInput(
            hint_text="Bileşen adı",
            size_hint_x=0.30,
            multiline=False
        )
        self.add_widget(self.ad_input)

        # Tip seçimi
        self.tip_spinner = Spinner(
            text="Malzeme",
            values=["Malzeme", "Sabit Değer"],
            size_hint_x=0.20
        )
        self.tip_spinner.bind(text=self.tip_degisti)
        self.add_widget(self.tip_spinner)

        # Malzeme spinner
        self.malzeme_spinner = Spinner(
            text="seramik",
            values=malzeme_listesi_getir(),
            size_hint_x=0.25
        )
        self.add_widget(self.malzeme_spinner)

        # Değer input (sabit değer için)
        self.deger_input = TextInput(
            hint_text="Değer (kN/m²)",
            size_hint_x=0.15,
            multiline=False,
            input_filter="float"
        )
        self.add_widget(self.deger_input)

        # Kalınlık input
        self.kalinlik_input = TextInput(
            hint_text="Kalınlık (m)",
            size_hint_x=0.10,
            multiline=False,
            input_filter="float"
        )
        self.add_widget(self.kalinlik_input)

        # Kaldır butonu
        self.kaldir_btn = Button(
            text="X",
            size_hint_x=0.05,
            background_color=(0.8, 0.2, 0.2, 1)
        )
        self.kaldir_btn.bind(on_press=self.kaldir)
        self.add_widget(self.kaldir_btn)

    def tip_degisti(self, spinner, text):
        """Malzeme/Sabit Değer seçimine göre alanları aktif/pasif yapar."""
        if text == "Malzeme":
            self.malzeme_spinner.disabled = False
            self.kalinlik_input.disabled = False
            self.deger_input.disabled = True
            self.deger_input.text = ""
        else:
            self.malzeme_spinner.disabled = True
            self.kalinlik_input.disabled = True
            self.kalinlik_input.text = ""
            self.deger_input.disabled = False

    def kaldir(self, instance):
        """Bu bileşen satırını ebeveyninden kaldırır."""
        if self.parent:
            self.parent.remove_widget(self)

    def load_component_olustur(self) -> LoadComponent | None:
        """Girilen verilerden LoadComponent oluşturur."""
        ad = self.ad_input.text.strip() or "Bileşen"
        tip = self.tip_spinner.text

        if tip == "Malzeme":
            malzeme = self.malzeme_spinner.text
            try:
                kalinlik = float(self.kalinlik_input.text)
            except (ValueError, TypeError):
                return None
            if kalinlik <= 0:
                return None
            return LoadComponent(
                name=ad,
                material=malzeme,
                thickness=kalinlik
            )
        else:
            try:
                deger = float(self.deger_input.text)
            except (ValueError, TypeError):
                return None
            return LoadComponent(
                name=ad,
                value=deger
            )

# ============================================================
# HAZIR YÜK PANELİ (JSON Kütüphanesi)
# ============================================================

class HazirYukPaneli(BoxLayout):
    """
    data/load_maps.json içindeki hazır yükleri listeler.
    Çift tıklama ile seçili yük LoadManager'a eklenir.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.spacing = dp(6)
        self.padding = dp(6)

        # --- Kategori seçimi ---
        ust = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(6))
        ust.add_widget(Label(text="Kategori:", size_hint_x=0.15))

        kategoriler = preset_library.kategori_listesi()
        self.kategori_map = {
            label: kid for kid, label, _ in kategoriler
        }
        self.kategori_spinner = Spinner(
            text=kategoriler[0][1] if kategoriler else "",
            values=[label for _, label, _ in kategoriler],
            size_hint_x=0.55
        )
        self.kategori_spinner.bind(text=self.kategori_degisti)
        ust.add_widget(self.kategori_spinner)

        self.tip_label = Label(
            text="",
            size_hint_x=0.30,
            color=(0.2, 0.4, 0.8, 1),
            bold=True
        )
        ust.add_widget(self.tip_label)
        self.add_widget(ust)

        # --- Kaynak / dönüşüm bilgisi ---
        meta = preset_library.meta.get("conversion", {})
        self.add_widget(Label(
            text=(
                f"Kaynak: {preset_library.meta.get('source', '')}  |  "
                f"Dönüşüm: {meta.get('from','')} → {meta.get('to','')} "
                f"(x{meta.get('factor','')}, {meta.get('rounding','')} hane)"
            ),
            size_hint_y=None,
            height=dp(24),
            color=(0.4, 0.4, 0.4, 1),
            font_size=dp(11)
        ))

        # --- Başlık ---
        baslik = BoxLayout(size_hint_y=None, height=dp(28))
        baslik.add_widget(Label(text="Yük Adı",      size_hint_x=0.60, bold=True))
        baslik.add_widget(Label(text="kgf/m²",       size_hint_x=0.15, bold=True))
        baslik.add_widget(Label(text="kN/m²",        size_hint_x=0.15, bold=True))
        baslik.add_widget(Label(text="",             size_hint_x=0.10))
        self.add_widget(baslik)

        # --- Yük listesi (scrollable) ---
        self.scroll = ScrollView()
        self.liste_layout = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=dp(2)
        )
        self.liste_layout.bind(minimum_height=self.liste_layout.setter("height"))
        self.scroll.add_widget(self.liste_layout)
        self.add_widget(self.scroll)

        # --- Alt bilgi ---
        self.bilgi_label = Label(
            text="Bir yüke tıklayarak seçin, çift tıklayarak LoadManager'a ekleyin.",
            size_hint_y=None,
            height=dp(30),
            color=(0.3, 0.3, 0.3, 1)
        )
        self.add_widget(self.bilgi_label)

        # İlk kategoriyi yükle
        if kategoriler:
            self.kategori_degisti(
                self.kategori_spinner,
                kategoriler[0][1]
            )

    # ------------------------------------------------------------------
    def kategori_degisti(self, spinner, label):
        kid = self.kategori_map.get(label)
        if not kid:
            return
        cat = preset_library.categories[kid]
        self.tip_label.text = f"Tip: {cat.get('load_type','G')}"
        self.liste_yenile(kid)

    # ------------------------------------------------------------------

    def liste_yenile(self, kategori_id):
        self.liste_layout.clear_widgets()
        yukler = preset_library.kategori_yukleri(kategori_id)

        # Sütun başlıkları kiriş senaryosunda farklı
        is_kiris = (kategori_id == "hazir_kiris_senaryolari")
        birim = "kN/m" if is_kiris else "kN/m²"

        for idx, y in enumerate(yukler):
            satir = BoxLayout(
                size_hint_y=None,
                height=dp(36),
                spacing=dp(2)
            )

            # Yük adı
            isim_btn = Button(
                text=y["name"],
                size_hint_x=0.60,
                halign="left",
                valign="middle",
                background_color=(0.9, 0.9, 0.9, 1),
                color=(0, 0, 0, 1)
            )
            isim_btn.bind(
                on_press=lambda inst, k=kategori_id, i=idx: self.satir_sec(k, i)
            )
            isim_btn.bind(
                on_release=lambda inst, k=kategori_id, i=idx: self.satir_ekle(k, i)
            )
            satir.add_widget(isim_btn)

            # kgf sütunu (kiriş senaryosunda '-')
            kgf_text = f"{y['kgf']:.2f}" if y.get("kgf") is not None else "-"
            satir.add_widget(Label(text=kgf_text, size_hint_x=0.15))

            # kN sütunu
            satir.add_widget(Label(
                text=f"{y['kn']:.2f}",
                size_hint_x=0.15,
                color=(0.1, 0.5, 0.2, 1),
                bold=True
            ))

            # Ekle butonu
            ekle_btn = Button(text="+", size_hint_x=0.10)
            ekle_btn.bind(
                on_press=lambda inst, k=kategori_id, i=idx: self.satir_ekle(k, i)
            )
            satir.add_widget(ekle_btn)

            self.liste_layout.add_widget(satir)

    # satir_sec'i de kiriş için uyarla:
    def satir_sec(self, kategori_id, item_index):
        yukler = preset_library.kategori_yukleri(kategori_id)
        y = yukler[item_index]
        if kategori_id == "hazir_kiris_senaryolari":
            self.bilgi_label.text = (
                f"Seçildi: {y['name']}  |  "
                f"Net yük. {y['net_height_m']:.2f} m  |  "
                f"Yüzey {y['area_load_kn_m2']} kN/m²  →  "
                f"Çizgisel {y['kn']} kN/m"
            )
        else:
            self.bilgi_label.text = (
                f"Seçildi: {y['name']}  |  {y['kgf']:.2f} kgf/m²  "
                f"→  {y['kn']:.2f} kN/m²"
            )

    # ------------------------------------------------------------------
    def satir_ekle(self, kategori_id, item_index):
        """Seçilen yükü LoadManager'a ekler."""
        try:
            load_type = preset_library.categories[kategori_id].get("load_type", "G")
            prefix = "G" if load_type == "G" else "Q"
            yeni_id = benzersiz_id_uret(prefix)

            definition = preset_library.load_definition_olustur(
                kategori_id=kategori_id,
                item_index=item_index,
                load_id=yeni_id,
                load_type=load_type,
            )
            load_manager.add_definition(definition)

            self.bilgi_label.text = (
                f"Eklendi: [{yeni_id}] {definition.name}  "
                f"= {definition.value:.2f} kN/m²"
            )
        except Exception as e:
            self.bilgi_label.text = f"Hata: {e}"

# ============================================================
# YÜK TANIMLAMA PANELİ
# ============================================================

class YukTanimlamaPaneli(BoxLayout):
    """G ve Q yüklerini tanımlama paneli."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.spacing = dp(6)
        self.padding = dp(6)

        
        # ---- Sekmeli yapı: G ve Q ----
        self.tabs = TabbedPanel(do_default_tab=False)
        self.tabs.tab_width = dp(120)

        # ---- G YÜKÜ SEKMESİ ----
        g_tab = TabbedPanelItem(text="Ölü Yük (G)")
        self.g_panel = self._g_paneli_olustur()
        g_tab.add_widget(self.g_panel)
        self.tabs.add_widget(g_tab)

        # ---- Q YÜKÜ SEKMESİ ----
        q_tab = TabbedPanelItem(text="Hareketli Yük (Q)")
        self.q_panel = self._q_paneli_olustur()
        q_tab.add_widget(self.q_panel)
        self.tabs.add_widget(q_tab)

        self.add_widget(self.tabs)

    # --------------------------------------------------------
    # G PANELİ
    # --------------------------------------------------------
    def _g_paneli_olustur(self):
        layout = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(4))

        # ID ve Ad
        ust = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(4))
        ust.add_widget(Label(text="ID:", size_hint_x=0.1))
        self.g_id_input = TextInput(
            text=benzersiz_id_uret("G"),
            size_hint_x=0.2,
            multiline=False
        )
        ust.add_widget(self.g_id_input)

        ust.add_widget(Label(text="Ad:", size_hint_x=0.1))
        self.g_ad_input = TextInput(
            hint_text="Örn: Konut Döşemesi",
            size_hint_x=0.6,
            multiline=False
        )
        ust.add_widget(self.g_ad_input)
        layout.add_widget(ust)

        # Bileşen başlıkları
        baslik = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(4))
        baslik.add_widget(Label(text="Ad", size_hint_x=0.30, bold=True))
        baslik.add_widget(Label(text="Tip", size_hint_x=0.20, bold=True))
        baslik.add_widget(Label(text="Malzeme", size_hint_x=0.25, bold=True))
        baslik.add_widget(Label(text="Değer", size_hint_x=0.15, bold=True))
        baslik.add_widget(Label(text="Kalınlık", size_hint_x=0.10, bold=True))
        layout.add_widget(baslik)

        # Bileşen listesi (scrollable)
        self.g_bilesen_scroll = ScrollView()
        self.g_bilesen_layout = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=dp(2)
        )
        self.g_bilesen_layout.bind(
            minimum_height=self.g_bilesen_layout.setter("height")
        )
        self.g_bilesen_scroll.add_widget(self.g_bilesen_layout)
        layout.add_widget(self.g_bilesen_scroll)

        # Butonlar
        btn_layout = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(6))
        ekle_btn = Button(text="+ Bileşen Ekle")
        ekle_btn.bind(on_press=self.bilesen_ekle)
        btn_layout.add_widget(ekle_btn)

        kaydet_btn = Button(
            text="G Yükünü Kaydet",
            background_color=(0.2, 0.6, 0.3, 1)
        )
        kaydet_btn.bind(on_press=self.g_yuku_kaydet)
        btn_layout.add_widget(kaydet_btn)
        layout.add_widget(btn_layout)

        # Başlangıçta bir bileşen ekle
        self.bilesen_ekle(None)

        return layout

    def bilesen_ekle(self, instance):
        satir = BilesenSatiri()
        self.g_bilesen_layout.add_widget(satir)

    def g_yuku_kaydet(self, instance):
        g_id = self.g_id_input.text.strip()
        g_ad = self.g_ad_input.text.strip()

        if not g_id or not g_ad:
            self._popup_goster("Hata", "ID ve Ad alanları zorunludur.")
            return

        if g_id in load_manager.definitions:
            self._popup_goster("Hata", f"'{g_id}' ID'si zaten mevcut.")
            return

        bilesenler = []
        for child in self.g_bilesen_layout.children:
            if isinstance(child, BilesenSatiri):
                comp = child.load_component_olustur()
                if comp is None:
                    self._popup_goster(
                        "Hata",
                        "Bileşen değerleri geçersiz. "
                        "Malzeme için kalınlık, sabit değer için sayı giriniz."
                    )
                    return
                bilesenler.append(comp)

        if not bilesenler:
            self._popup_goster("Hata", "En az bir bileşen eklemelisiniz.")
            return

        definition = LoadDefinition(
            id=g_id,
            name=g_ad,
            load_type="G",
            components=bilesenler,
            source="user"
        )

        try:
            load_manager.add_definition(definition)
            toplam = definition.calculate(MATERIAL_WEIGHTS)
            self._popup_goster(
                "Başarılı",
                f"{g_id} kaydedildi.\nToplam: {toplam:.3f} kN/m²"
            )
            # Formu sıfırla
            self.g_id_input.text = benzersiz_id_uret("G")
            self.g_ad_input.text = ""
            for child in list(self.g_bilesen_layout.children):
                self.g_bilesen_layout.remove_widget(child)
            self.bilesen_ekle(None)
        except Exception as e:
            self._popup_goster("Hata", str(e))

    # --------------------------------------------------------
    # Q PANELİ
    # --------------------------------------------------------
    def _q_paneli_olustur(self):
        layout = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(4))

        # ID
        ust = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(4))
        ust.add_widget(Label(text="ID:", size_hint_x=0.1))
        self.q_id_input = TextInput(
            text=benzersiz_id_uret("Q"),
            size_hint_x=0.2,
            multiline=False
        )
        ust.add_widget(self.q_id_input)

        ust.add_widget(Label(text="Kullanım:", size_hint_x=0.15))
        self.q_kullanim_spinner = Spinner(
            text="konut",
            values=[k for k, _, _ in canli_yuk_listesi_getir()],
            size_hint_x=0.55
        )
        self.q_kullanim_spinner.bind(text=self.q_kullanim_degisti)
        ust.add_widget(self.q_kullanim_spinner)
        layout.add_widget(ust)

        # Seçilen yük bilgisi
        self.q_bilgi_label = Label(
            text="",
            size_hint_y=None,
            height=dp(30),
            color=(0.2, 0.4, 0.8, 1)
        )
        layout.add_widget(self.q_bilgi_label)

        # Değer
        deger_layout = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(4))
        deger_layout.add_widget(Label(text="Değer (kN/m²):", size_hint_x=0.3))
        self.q_deger_input = TextInput(
            text="",
            size_hint_x=0.4,
            multiline=False,
            input_filter="float"
        )
        deger_layout.add_widget(self.q_deger_input)
        deger_layout.add_widget(Label(text="", size_hint_x=0.3))
        layout.add_widget(deger_layout)

        # Kaydet
        kaydet_btn = Button(
            text="Q Yükünü Kaydet",
            size_hint_y=None,
            height=dp(45),
            background_color=(0.2, 0.6, 0.3, 1)
        )
        kaydet_btn.bind(on_press=self.q_yuku_kaydet)
        layout.add_widget(kaydet_btn)

        # Başlangıç bilgisi
        self.q_kullanim_degisti(self.q_kullanim_spinner, "konut")

        return layout

    def q_kullanim_degisti(self, spinner, text):
        for key, name, value in canli_yuk_listesi_getir():
            if key == text:
                self.q_bilgi_label.text = f"{name}  →  {value} kN/m²"
                self.q_deger_input.text = str(value)
                break

    def q_yuku_kaydet(self, instance):
        q_id = self.q_id_input.text.strip()
        kullanim = self.q_kullanim_spinner.text

        if not q_id:
            self._popup_goster("Hata", "ID alanı zorunludur.")
            return

        if q_id in load_manager.definitions:
            self._popup_goster("Hata", f"'{q_id}' ID'si zaten mevcut.")
            return

        try:
            deger = float(self.q_deger_input.text)
        except (ValueError, TypeError):
            self._popup_goster("Hata", "Geçerli bir sayı giriniz.")
            return

        # Kullanım adını bul
        ad = kullanim
        for key, name, _ in canli_yuk_listesi_getir():
            if key == kullanim:
                ad = name
                break

        definition = LoadDefinition(
            id=q_id,
            name=ad,
            load_type="Q",
            value=deger,
            source="TS 498"
        )

        try:
            load_manager.add_definition(definition)
            self._popup_goster("Başarılı", f"{q_id} kaydedildi: {deger} kN/m²")
            self.q_id_input.text = benzersiz_id_uret("Q")
        except Exception as e:
            self._popup_goster("Hata", str(e))

    # --------------------------------------------------------
    def _popup_goster(self, baslik, mesaj):
        popup = Popup(
            title=baslik,
            content=Label(text=mesaj),
            size_hint=(0.6, 0.3)
        )
        popup.open()


# ============================================================
# ELEMAN ATAMA PANELİ
# ============================================================

class ElemanAtamaPaneli(BoxLayout):
    """Seçili elemana G ve Q yükü atama paneli."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.spacing = dp(6)
        self.padding = dp(6)

        self.secili_eleman = None

        # Eleman seçimi
        eleman_layout = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(6))
        eleman_layout.add_widget(Label(text="Eleman ID:", size_hint_x=0.2))
        self.eleman_input = TextInput(
            hint_text="Örn: 101, K-12",
            size_hint_x=0.5,
            multiline=False
        )
        eleman_layout.add_widget(self.eleman_input)

        sec_btn = Button(text="Elemanı Seç", size_hint_x=0.3)
        sec_btn.bind(on_press=self.eleman_sec)
        eleman_layout.add_widget(sec_btn)
        self.add_widget(eleman_layout)

        # Seçili eleman bilgisi
        self.eleman_bilgi = Label(
            text="Henüz eleman seçilmedi.",
            size_hint_y=None,
            height=dp(30),
            color=(0.2, 0.4, 0.8, 1)
        )
        self.add_widget(self.eleman_bilgi)

        # Yük listeleri (G ve Q)
        listeler = BoxLayout(spacing=dp(8))

        # G yükleri
        g_box = BoxLayout(orientation="vertical", spacing=dp(4))
        g_box.add_widget(Label(
            text="Ölü Yükler (G)",
            size_hint_y=None,
            height=dp(30),
            bold=True
        ))
        self.g_scroll = ScrollView()
        self.g_liste = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=dp(2)
        )
        self.g_liste.bind(minimum_height=self.g_liste.setter("height"))
        self.g_scroll.add_widget(self.g_liste)
        g_box.add_widget(self.g_scroll)
        listeler.add_widget(g_box)

        # Q yükleri
        q_box = BoxLayout(orientation="vertical", spacing=dp(4))
        q_box.add_widget(Label(
            text="Hareketli Yükler (Q)",
            size_hint_y=None,
            height=dp(30),
            bold=True
        ))
        self.q_scroll = ScrollView()
        self.q_liste = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=dp(2)
        )
        self.q_liste.bind(minimum_height=self.q_liste.setter("height"))
        self.q_scroll.add_widget(self.q_liste)
        q_box.add_widget(self.q_scroll)
        listeler.add_widget(q_box)

        self.add_widget(listeler)

        # Toplam bilgisi
        self.toplam_label = Label(
            text="",
            size_hint_y=None,
            height=dp(60),
            color=(0.8, 0.2, 0.2, 1),
            bold=True
        )
        self.add_widget(self.toplam_label)

        # Atama butonu
        atama_btn = Button(
            text="Seçili Yükleri Elemana Ata",
            size_hint_y=None,
            height=dp(45),
            background_color=(0.2, 0.5, 0.8, 1)
        )
        atama_btn.bind(on_press=self.atama_yap)
        self.add_widget(atama_btn)

        # Yük listesini yenile
        self.liste_yenile()

    def liste_yenile(self):
        """Tanımlı yükleri G ve Q listelerine doldurur."""
        # G listesi
        self.g_liste.clear_widgets()
        for d in sorted(load_manager.definitions.values(), key=lambda x: x.id):
            if d.load_type != "G":
                continue
            try:
                deger = d.calculate(MATERIAL_WEIGHTS)
            except Exception:
                deger = 0.0
            tb = ToggleButton(
                text=f"[{d.id}] {d.name}  ({deger:.3f} kN/m²)",
                size_hint_y=None,
                height=dp(38)
            )
            tb.load_id = d.id
            self.g_liste.add_widget(tb)

        # Q listesi
        self.q_liste.clear_widgets()
        for d in sorted(load_manager.definitions.values(), key=lambda x: x.id):
            if d.load_type != "Q":
                continue
            try:
                deger = d.calculate(MATERIAL_WEIGHTS)
            except Exception:
                deger = 0.0
            tb = ToggleButton(
                text=f"[{d.id}] {d.name}  ({deger:.3f} kN/m²)",
                size_hint_y=None,
                height=dp(38)
            )
            tb.load_id = d.id
            self.q_liste.add_widget(tb)

    def eleman_sec(self, instance):
        elem = self.eleman_input.text.strip()
        if not elem:
            self._popup_goster("Hata", "Eleman ID boş olamaz.")
            return
        self.secili_eleman = elem
        self.eleman_bilgi.text = f"Seçili eleman: {elem}"
        self.toplam_guncelle()

    def _secili_yukleri_al(self, liste_layout):
        """ToggleButton'lardan seçili olanların load_id listesini döner."""
        secili = []
        for child in liste_layout.children:
            if isinstance(child, ToggleButton) and child.state == "down":
                secili.append(child.load_id)
        return secili

    def atama_yap(self, instance):
        if self.secili_eleman is None:
            self._popup_goster("Hata", "Önce bir eleman seçin.")
            return

        secili_g = self._secili_yukleri_al(self.g_liste)
        secili_q = self._secili_yukleri_al(self.q_liste)

        if not secili_g and not secili_q:
            self._popup_goster("Hata", "En az bir yük seçin.")
            return

        for load_id in secili_g + secili_q:
            try:
                load_manager.assign(self.secili_eleman, load_id)
            except Exception as e:
                self._popup_goster("Hata", str(e))
                return

        self.toplam_guncelle()
        self._popup_goster(
            "Başarılı",
            f"{self.secili_eleman} elemanına "
            f"{len(secili_g)} G ve {len(secili_q)} Q yükü atandı."
        )

    def toplam_guncelle(self):
        if self.secili_eleman is None:
            return
        try:
            g_top = load_manager.get_element_total(self.secili_eleman, "G")
            q_top = load_manager.get_element_total(self.secili_eleman, "Q")
            self.toplam_label.text = (
                f"Toplam Ölü Yük (G): {g_top:.3f} kN/m²\n"
                f"Toplam Hareketli Yük (Q): {q_top:.3f} kN/m²"
            )
        except Exception as e:
            self.toplam_label.text = f"Hata: {e}"

    def _popup_goster(self, baslik, mesaj):
        popup = Popup(
            title=baslik,
            content=Label(text=mesaj),
            size_hint=(0.6, 0.3)
        )
        popup.open()


# ============================================================
# RAPOR PANELİ
# ============================================================

class RaporPaneli(BoxLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.spacing = dp(6)
        self.padding = dp(6)

        btn_layout = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(6))
        yenile_btn = Button(text="Raporu Yenile")
        yenile_btn.bind(on_press=self.rapor_yenile)
        btn_layout.add_widget(yenile_btn)
        self.add_widget(btn_layout)

        self.scroll = ScrollView()
        self.rapor_layout = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=dp(4)
        )
        self.rapor_layout.bind(minimum_height=self.rapor_layout.setter("height"))
        self.scroll.add_widget(self.rapor_layout)
        self.add_widget(self.scroll)

    def rapor_yenile(self, instance=None):
        self.rapor_layout.clear_widgets()

        # Yük tanımları
        self.rapor_layout.add_widget(Label(
            text="=== TANIMLI YÜKLER ===",
            size_hint_y=None,
            height=dp(30),
            bold=True,
            color=(0.2, 0.4, 0.8, 1)
        ))

        for d in sorted(load_manager.definitions.values(), key=lambda x: x.id):
            try:
                deger = d.calculate(MATERIAL_WEIGHTS)
            except Exception:
                deger = 0.0
            self.rapor_layout.add_widget(Label(
                text=f"[{d.id}] {d.name} ({d.load_type}) = {deger:.3f} kN/m²",
                size_hint_y=None,
                height=dp(25)
            ))

        # Eleman atamaları
        self.rapor_layout.add_widget(Label(
            text="\n=== ELEMAN ATAMALARI ===",
            size_hint_y=None,
            height=dp(30),
            bold=True,
            color=(0.2, 0.4, 0.8, 1)
        ))

        for elem_id, assignment in load_manager.assignments.items():
            g_ids = assignment.get("G", [])
            q_ids = assignment.get("Q", [])
            if not g_ids and not q_ids:
                continue
            try:
                g_top = load_manager.get_element_total(elem_id, "G")
                q_top = load_manager.get_element_total(elem_id, "Q")
            except Exception:
                g_top = q_top = 0.0
            self.rapor_layout.add_widget(Label(
                text=(
                    f"Eleman {elem_id}: "
                    f"G={g_top:.3f} ({', '.join(g_ids)}) | "
                    f"Q={q_top:.3f} ({', '.join(q_ids)})"
                ),
                size_hint_y=None,
                height=dp(25)
            ))

# ============================================================
# DEAD / LIVE CONFIG EXPORT
# ============================================================

def export_dead_config() -> dict:
    """LoadManager'daki G yüklerini ve atamalarını JSON sözlüğüne çevirir."""
    definitions = []
    for d in load_manager.definitions.values():
        if d.load_type != "G":
            continue
        try:
            value = d.calculate(MATERIAL_WEIGHTS)
        except Exception:
            value = 0.0
        definitions.append({
            "id": d.id,
            "name": d.name,
            "load_type": d.load_type,
            "value": round(value, 4),
            "unit": getattr(d, "unit", "kN/m²"),
            "source": d.source,
            "description": d.description,
        })

    assignments = {}
    for elem_id, kinds in load_manager.assignments.items():
        g_ids = list(kinds.get("G", []))
        if g_ids:
            assignments[str(elem_id)] = {"G": g_ids}

    return {
        "definitions": definitions,
        "assignments": assignments,
    }


def export_live_config() -> dict:
    """LoadManager'daki Q yüklerini ve atamalarını JSON sözlüğüne çevirir."""
    definitions = []
    for d in load_manager.definitions.values():
        if d.load_type != "Q":
            continue
        try:
            value = d.calculate(MATERIAL_WEIGHTS)
        except Exception:
            value = 0.0
        definitions.append({
            "id": d.id,
            "name": d.name,
            "load_type": d.load_type,
            "value": round(value, 4),
            "unit": getattr(d, "unit", "kN/m²"),
            "source": d.source,
            "description": d.description,
        })

    assignments = {}
    for elem_id, kinds in load_manager.assignments.items():
        q_ids = list(kinds.get("Q", []))
        if q_ids:
            assignments[str(elem_id)] = {"Q": q_ids}

    return {
        "definitions": definitions,
        "assignments": assignments,
    }


# ============================================================
# ANA UYGULAMA
# ============================================================

class YukAtamaApp(App):

    def build(self):
        self.title = "Yük Atama Sistemi - TS 498"

        root = BoxLayout(orientation="vertical")
        tabs = TabbedPanel(do_default_tab=False)
        tabs.tab_width = dp(150)

        # 1) Manuel Tanımlama (mevcut)
        tanim_tab = TabbedPanelItem(text="1. Yük Tanımla")
        tanim_tab.add_widget(YukTanimlamaPaneli())
        tabs.add_widget(tanim_tab)

        # 2) YENİ: Hazır Yükler
        hazir_tab = TabbedPanelItem(text="2. Hazır Yükler")
        self.hazir_panel = HazirYukPaneli()
        hazir_tab.add_widget(self.hazir_panel)
        tabs.add_widget(hazir_tab)

        # 3) Elemana Ata (mevcut → numara kaydı)
        atama_tab = TabbedPanelItem(text="3. Elemana Ata")
        self.atama_panel = ElemanAtamaPaneli()
        atama_tab.add_widget(self.atama_panel)
        tabs.add_widget(atama_tab)

        # 4) Rapor (mevcut → numara kaydı)
        rapor_tab = TabbedPanelItem(text="4. Rapor")
        self.rapor_panel = RaporPaneli()
        rapor_tab.add_widget(self.rapor_panel)
        tabs.add_widget(rapor_tab)

        tabs.bind(current_tab=self.sekme_degisti)
        root.add_widget(tabs)
        return root

    def sekme_degisti(self, instance, value):
        if hasattr(self, "atama_panel"):
            self.atama_panel.liste_yenile()
        if hasattr(self, "rapor_panel"):
            self.rapor_panel.rapor_yenile()


if __name__ == "__main__":
    YukAtamaApp().run()