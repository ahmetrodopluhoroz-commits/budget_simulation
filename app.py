import streamlit as st
import pandas as pd
import numpy as np
import io
import json
import os
import hashlib
import inspect
import re
import urllib.error
import urllib.request
from datetime import date, datetime

# ============================================================
# 💾 YEREL ÖNBELLEK (CACHE) DOSYA YOLLARI (F5 KORUMASI)
# ============================================================
CACHE_DATA_MASTER = "cache_data_master.parquet"
CACHE_2026_B = "cache_2026_buyume.parquet"
CACHE_2026_GERCEK_B = "cache_2026_buyume_gercek.parquet"

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

# Data_New için lisans gerektirmeyen AG Grid Community özellikleri kullanılır.
# Paket bulunmazsa uygulama mevcut Streamlit editörüne güvenli biçimde döner.
try:
    from st_aggrid import AgGrid, DataReturnMode, GridOptionsBuilder, JsCode
    ST_AGGRID_AVAILABLE = True
except ImportError:
    ST_AGGRID_AVAILABLE = False

# ============================================================
# STREAMLIT SAYFA AYARLARI
# ============================================================
st.set_page_config(
    page_title="Gelişmiş Bütçe Simülatörü",
    layout="wide"
)

# ============================================================
# 🎨 UYGULAMA GENELİ AÇIK / KOYU TEMA
# ============================================================
if "arayuz_koyu_tema" not in st.session_state:
    st.session_state.arayuz_koyu_tema = False

st.sidebar.caption("🎨 Görünüm")
st.sidebar.toggle(
    "🌙 Koyu tema",
    key="arayuz_koyu_tema",
    help="Tüm uygulamanın açık ve koyu görünümü arasında geçiş yapar."
)

if st.session_state.arayuz_koyu_tema:
    TEMA = {
        "bg": "#0d1117",
        "surface": "#161b22",
        "surface_2": "#21262d",
        "surface_3": "#292f37",
        "text": "#e6edf3",
        "muted": "#9da7b3",
        "border": "#30363d",
        "primary": "#ff4b4b",
        "shadow": "rgba(0, 0, 0, 0.35)",
        "editable": "#4a3b12",
        "editable_text": "#fff1b8",
        "scheme": "dark"
    }
else:
    TEMA = {
        "bg": "#f7f9fc",
        "surface": "#ffffff",
        "surface_2": "#f1f5f9",
        "surface_3": "#e8eef5",
        "text": "#172033",
        "muted": "#64748b",
        "border": "#dbe3ee",
        "primary": "#ff4b4b",
        "shadow": "rgba(15, 23, 42, 0.08)",
        "editable": "#fff3cd",
        "editable_text": "#3d3100",
        "scheme": "light"
    }

st.markdown(
    f"""
    <style>
    :root {{
        color-scheme: {TEMA['scheme']};
        --app-bg: {TEMA['bg']};
        --app-surface: {TEMA['surface']};
        --app-surface-2: {TEMA['surface_2']};
        --app-surface-3: {TEMA['surface_3']};
        --app-text: {TEMA['text']};
        --app-muted: {TEMA['muted']};
        --app-border: {TEMA['border']};
        --app-primary: {TEMA['primary']};
    }}

    html, body, .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"] {{
        background: var(--app-bg) !important;
        color: var(--app-text) !important;
    }}

    [data-testid="stHeader"] {{
        background: var(--app-bg) !important;
        border-bottom: 1px solid var(--app-border) !important;
    }}

    [data-testid="stSidebar"],
    [data-testid="stSidebar"] > div:first-child {{
        background: var(--app-surface) !important;
        color: var(--app-text) !important;
        border-right: 1px solid var(--app-border) !important;
    }}

    .stApp h1, .stApp h2, .stApp h3, .stApp h4,
    .stApp h5, .stApp h6, .stApp p, .stApp label,
    .stApp [data-testid="stMarkdownContainer"],
    .stApp [data-testid="stCaptionContainer"],
    .stApp [data-testid="stMetricLabel"],
    .stApp [data-testid="stMetricValue"] {{
        color: var(--app-text) !important;
    }}

    .stApp [data-testid="stCaptionContainer"],
    .stApp small {{
        color: var(--app-muted) !important;
    }}

    .stApp hr {{
        border-color: var(--app-border) !important;
    }}

    .stApp [data-testid="stMetric"],
    .stApp [data-testid="stFileUploaderDropzone"],
    .stApp details,
    .stApp [data-testid="stExpander"],
    .stApp [data-testid="stForm"] {{
        background: var(--app-surface) !important;
        color: var(--app-text) !important;
        border-color: var(--app-border) !important;
        border-radius: 10px !important;
        box-shadow: 0 2px 10px {TEMA['shadow']} !important;
    }}

    .stApp input, .stApp textarea,
    .stApp [data-baseweb="input"] > div,
    .stApp [data-baseweb="select"] > div,
    .stApp [data-baseweb="base-input"] {{
        background: var(--app-surface-2) !important;
        color: var(--app-text) !important;
        border-color: var(--app-border) !important;
        caret-color: var(--app-text) !important;
    }}

    .stApp input::placeholder, .stApp textarea::placeholder {{
        color: var(--app-muted) !important;
        opacity: 0.9 !important;
    }}

    [data-baseweb="popover"], [role="listbox"],
    [data-baseweb="menu"] {{
        background: var(--app-surface) !important;
        color: var(--app-text) !important;
        border-color: var(--app-border) !important;
    }}

    [role="option"] {{
        background: var(--app-surface) !important;
        color: var(--app-text) !important;
    }}

    [role="option"]:hover {{
        background: var(--app-surface-2) !important;
    }}

    .stApp .stButton > button:not([kind="primary"]),
    .stApp .stDownloadButton > button,
    .stApp [data-testid="stFileUploader"] button {{
        background: var(--app-surface) !important;
        color: var(--app-text) !important;
        border-color: var(--app-border) !important;
    }}

    .stApp .stButton > button:not([kind="primary"]):hover,
    .stApp .stDownloadButton > button:hover {{
        background: var(--app-surface-2) !important;
        border-color: var(--app-primary) !important;
        color: var(--app-primary) !important;
    }}

    .stApp .stButton > button[kind="primary"] {{
        background: var(--app-primary) !important;
        color: #ffffff !important;
        border-color: var(--app-primary) !important;
    }}

    .stApp [data-baseweb="tab-list"] {{
        background: var(--app-surface) !important;
        border-bottom: 1px solid var(--app-border) !important;
    }}

    .stApp button[data-baseweb="tab"] {{
        background: transparent !important;
        color: var(--app-muted) !important;
        border-color: transparent !important;
    }}

    .stApp button[data-baseweb="tab"][aria-selected="true"] {{
        color: var(--app-primary) !important;
        border-bottom-color: var(--app-primary) !important;
        background: var(--app-surface-2) !important;
    }}

    .stApp [data-testid="stDataFrame"],
    .stApp [data-testid="stDataEditor"] {{
        background: var(--app-surface) !important;
        color: var(--app-text) !important;
        border: 1px solid var(--app-border) !important;
        border-radius: 8px !important;
    }}

    .stApp [data-testid="stAlert"] {{
        color: var(--app-text) !important;
        border: 1px solid var(--app-border) !important;
        box-shadow: none !important;
    }}

    .stApp [data-testid="stWidgetLabel"] {{
        color: var(--app-text) !important;
    }}

    .stApp svg {{
        color: currentColor;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# AG Grid iframe'ı ana sayfa CSS'inden etkilenmediği için renkler ayrıca verilir.
DATA_NEW_GRID_CSS = {
    ".ag-root-wrapper": {
        "background-color": TEMA["surface"],
        "color": TEMA["text"],
        "border-color": TEMA["border"]
    },
    ".ag-header, .ag-floating-filter": {
        "background-color": TEMA["surface_2"],
        "color": TEMA["text"],
        "border-color": TEMA["border"]
    },
    ".ag-header-cell, .ag-header-cell-text": {
        "color": TEMA["text"]
    },
    ".ag-row": {
        "background-color": TEMA["surface"],
        "color": TEMA["text"],
        "border-color": TEMA["border"]
    },
    ".ag-row-even": {
        "background-color": TEMA["surface_2"]
    },
    ".ag-row-hover": {
        "background-color": TEMA["surface_3"] + " !important"
    },
    ".ag-cell": {
        "color": TEMA["text"],
        "border-color": TEMA["border"]
    },
    ".ag-floating-filter input, .ag-input-field-input": {
        "background-color": TEMA["surface"],
        "color": TEMA["text"],
        "border-color": TEMA["border"]
    },
    ".ag-paging-panel": {
        "background-color": TEMA["surface_2"],
        "color": TEMA["text"],
        "border-color": TEMA["border"]
    }
}

# ============================================================
# 🔒 KULLANICI GİRİŞ (LOGIN) SİSTEMİ
# ============================================================
if "oturum_acik" not in st.session_state:
    st.session_state.oturum_acik = False
if "oturum_kullanici" not in st.session_state:
    st.session_state.oturum_kullanici = ""

if not st.session_state.oturum_acik:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col2:
        st.title("🔒 Bütçe Sistemine Giriş")
        st.markdown("Lütfen devam etmek için yetkili bilgilerinizi girin.")
        
        kullanici_adi = st.text_input("Kullanıcı Adı")
        sifre = st.text_input("Şifre", type="password")
        
        if st.button("Giriş Yap", use_container_width=True, type="primary"):
            if kullanici_adi == "rasg" and sifre == "Hrz1234":
                st.session_state.oturum_acik = True
                st.session_state.oturum_kullanici = kullanici_adi.strip()
                st.success("Giriş Başarılı! Sistem Yükleniyor...")
                st.rerun()
            else:
                st.error("Hatalı kullanıcı adı veya şifre girdiniz!")
                
    st.stop()

AKTIF_KULLANICI = (
    st.session_state.get("oturum_kullanici", "").strip() or "rasg"
)

# ============================================================
# SÜTUN VE VERİ TİPİ TANIMLARI
# ============================================================
aylar = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
ilk_9_ay = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül"]

ana_kolonlar = [
    "Uniq ID", "Yıl", "Teslimat Tipi", "Atf Tipi", "Çıkış İl Adı", "Çıkış Şube Adı", "Varış İl Adı", "Varış Şube Adı",
    "İlk Okutma Şubesi", "Müşteri Kodu", "Müşteri Adı", "Müşteri Temsilcisi", "Sap Kodu", "Durum", "Kayıt Tarihi", "Müşteri Grubu"
]
parametre_kolonlari = [
    "Yakıt Değişim Yüzdesi (%)", "Yakıt Anlık Değişim Oranı (%)", "Yakıt Değişim Periyodu (Ay)",
    "Enf. Değişim Yüzdesi (%)", "Enf. Değişim Periyodu (Ay)", "Esk. Baz Yakıt Fiyatı", "Esk. Yakıt Başlangıç Tarihi", "Esk. Enf. Başlangıç Tarihi"
]

kolonlar_25_Kg = [f"2025 {ay} Kg" for ay in aylar]
kolonlar_25_tutar = [f"2025 {ay} Tutar" for ay in aylar]
kolonlar_25_fiyat = [f"2025 {ay} Fiyat" for ay in aylar]

kolonlar_26_buyume = [f"2026 {ay} Büyüme" for ay in aylar]
kolonlar_26_esk = [f"2026 {ay} Esk." for ay in aylar]
kolonlar_26_Kg = [f"2026 {ay} Kg" for ay in aylar]
kolonlar_26_tutar = [f"2026 {ay} Tutar" for ay in aylar]
kolonlar_26_fiyat = [f"2026 {ay} Fiyat" for ay in aylar]

tum_kolonlar = (ana_kolonlar + parametre_kolonlari + kolonlar_25_Kg + kolonlar_25_tutar + kolonlar_25_fiyat +
                kolonlar_26_buyume + kolonlar_26_esk + kolonlar_26_Kg + kolonlar_26_tutar + kolonlar_26_fiyat)

BIGINT_KOLONLAR = ["Uniq ID", "Yıl", "Yakıt Değişim Periyodu (Ay)", "Enf. Değişim Periyodu (Ay)"]
NUMERIC_KOLONLAR = (["Yakıt Değişim Yüzdesi (%)", "Yakıt Anlık Değişim Oranı (%)", "Enf. Değişim Yüzdesi (%)", "Esk. Baz Yakıt Fiyatı"] +
                    kolonlar_25_Kg + kolonlar_25_tutar + kolonlar_25_fiyat + kolonlar_26_buyume + kolonlar_26_esk +
                    kolonlar_26_Kg + kolonlar_26_tutar + kolonlar_26_fiyat)

data_ekran_sutunlari = [
    "Uniq ID", "Yıl", "Teslimat Tipi", "Atf Tipi", "Çıkış İl Adı", "Çıkış Şube Adı", "Varış İl Adı", "Varış Şube Adı",
    "İlk Okutma Şubesi", "Müşteri Kodu", "Müşteri Adı", "Müşteri Temsilcisi", "Sap Kodu", "Durum", "Kayıt Tarihi", "Müşteri Grubu",
    "Yakıt Değişim Yüzdesi (%)", "Yakıt Anlık Değişim Oranı (%)", "Yakıt Değişim Periyodu (Ay)", "Enf. Değişim Yüzdesi (%)",
    "Enf. Değişim Periyodu (Ay)", "Esk. Baz Yakıt Fiyatı", "Esk. Yakıt Başlangıç Tarihi", "Esk. Enf. Başlangıç Tarihi"
]
deg_anah_sutunlari = ["Müşteri Kodu", "Sap No", "Ünvan", "Müşteri Temsilcisi 1", "Müşteri Temsilcisi 2", "Değişim Anahtarı", "KDV Durumu", "Baz Yakıt Fiyatı"]
baz_yakit_sutunlari = [
    "Müşteri Kodu", "Müşteri Adı", "Müşteri Temsilcisi", "Durum",
    "KDV Durumu", "Baz Yakıt Fiyatı (Girilen)",
    "Esk. Baz Yakıt Fiyatı (KDV Hariç)"
]
master_data_kimlik_sutunlari = [
    "Müşteri Kodu", "Müşteri Adı", "Müşteri Temsilcisi", "Sap Kodu",
    "Durum", "Kayıt Tarihi", "Müşteri Grubu"
]
master_data_kaynak_sutunlari = [
    "Değişim Anahtarı", "KDV Durumu", "Baz Yakıt Fiyatı (Girilen)"
]
master_data_manuel_sutunlari = [
    "Yakıt Değişim Yüzdesi (%)", "Yakıt Anlık Değişim Oranı (%)",
    "Yakıt Değişim Periyodu (Ay)", "Enf. Değişim Yüzdesi (%)",
    "Enf. Değişim Periyodu (Ay)",
    "Esk. Baz Yakıt Fiyatı (KDV Hariç)",
    "Esk. Yakıt Başlangıç Tarihi", "Esk. Enf. Başlangıç Tarihi"
]
master_data_mazot_sutunlari = [f"Mazot {ay} (%)" for ay in aylar]
MASTER_MAZOT_MANUEL_ALANLAR_DB = "Mazot Manuel Alanlar"
master_data_enflasyon_sutunlari = [f"Enflasyon {ay} (%)" for ay in aylar]
MASTER_ENFLASYON_MANUEL_ALANLAR_DB = "Enflasyon Manuel Alanlar"
master_data_eskalasyon_sutunlari = [f"Eskalasyon {ay} (%)" for ay in aylar]
master_data_sutunlari = (
    master_data_kimlik_sutunlari
    + master_data_kaynak_sutunlari
    + master_data_manuel_sutunlari
    + master_data_mazot_sutunlari
    + master_data_enflasyon_sutunlari
    + master_data_eskalasyon_sutunlari
)
baz_birim_fiyat_sutunlari = [
    "uniq", "Müşteri Kodu", "Müşteri Adı", "Müşteri Grubu",
    "Müşteri Temsilcisi", "Durum", "Atf Tipi", "TL/desi", "Açıklama"
]
data_new_kimlik_sutunlari = ana_kolonlar.copy()
data_new_parametre_sutunlari = parametre_kolonlari.copy()
data_new_2025_desi_sutunlari = [f"2025 {ay} Desi" for ay in aylar]
data_new_2025_tutar_sutunlari = [f"2025 {ay} Tutar" for ay in aylar]
data_new_2025_fiyat_sutunlari = [f"2025 {ay} Fiyat" for ay in aylar]
data_new_2026_buyume_sutunlari = [f"2026 {ay} Büyüme" for ay in aylar]
data_new_2026_esk_sutunlari = [f"2026 {ay} Esk." for ay in aylar]
data_new_2026_desi_sutunlari = [f"2026 {ay} Desi" for ay in aylar]
data_new_2026_tutar_sutunlari = [f"2026 {ay} Tutar" for ay in aylar]
data_new_2026_fiyat_sutunlari = [f"2026 {ay} Fiyat" for ay in aylar]
DATA_NEW_MANUEL_BUYUME_DB = "Manuel Büyüme Ayarları"
data_new_tum_sutunlar = (
    data_new_kimlik_sutunlari
    + data_new_parametre_sutunlari
    + data_new_2025_desi_sutunlari
    + data_new_2025_tutar_sutunlari
    + data_new_2025_fiyat_sutunlari
    + data_new_2026_buyume_sutunlari
    + data_new_2026_esk_sutunlari
    + data_new_2026_desi_sutunlari
    + data_new_2026_tutar_sutunlari
    + data_new_2026_fiyat_sutunlari
)
mazot_giriş_sutunlari = ["Baz Motorin"] + aylar
buyume_ekran_sutunlari = [
    "Müşteri Kodu", "Müşteri Adı", "Müşteri Temsilcisi", "Sap Kodu", "Durum", "Kayıt Tarihi", "Müşteri Grubu"
] + aylar + [
    "2024 ilk 9 ay desi", "2025 ilk 9 ay desi", "2025 % desi pay", "Y To Y Desi",
    "25 kullanılan büyüme", "KULLANICAK BÜYÜME", "Gelen Özet Bilgi", "Müşteriden Gelen Büyüme"
]
BUYUME_AYLIK_ORANLAR_DB = "Aylık Büyüme Oranları"
KG_MUSTERI_DB_TABLOSU = "kg_musteri_tablosu"
YIL_KAPANIS_DB_TABLOSU = "yil_kapanis_tablosu"
YIL_KAPANIS_DETAY_DB_TABLOSU = "yil_kapanis_detay_tablosu"
kg_musteri_sutunlari = [
    "Yıl", "Müşteri Kodu", "Müşteri Grubu"
] + [f"{ay} Kg" for ay in aylar]
yil_kapanis_sonuc_sutunlari = [
    "Müşteri Grubu"
] + [f"{ay} (%)" for ay in aylar] + ["Gerçekleşen Dönem Payı (%)"]
yil_kapanis_detay_kimlik_sutunlari = [
    "Uniq ID", "Yıl", "Teslimat Tipi", "Atf Tipi", "Çıkış İl Adı",
    "Çıkış Şube Adı", "Varış İl Adı", "Varış Şube Adı",
    "İlk Okutma Şubesi", "Müşteri Kodu", "Müşteri Adı",
    "Müşteri Temsilcisi", "Sap Kodu", "Durum", "Kayıt Tarihi",
    "Müşteri Grubu", "Esk. Yakıt Başlangıç Tarihi",
    "Esk. Enf. Başlangıç Tarihi"
]
yil_kapanis_detay_ay_sutunlari = [f"{ay} Desi" for ay in aylar]
yil_kapanis_detay_sutunlari = (
    yil_kapanis_detay_kimlik_sutunlari
    + yil_kapanis_detay_ay_sutunlari
    + ["Gerçekleşen Toplam Desi", "Tahmini Yıl Sonu Toplam Desi"]
)

# ============================================================
# SESSION STATE (OTOMATİK YÜKLEME DAHİL)
# ============================================================
if "data_sayfası_df" not in st.session_state: 
    if os.path.exists(CACHE_DATA_MASTER):
        st.session_state.data_sayfası_df = pd.read_parquet(CACHE_DATA_MASTER)
    else:
        st.session_state.data_sayfası_df = pd.DataFrame(columns=data_ekran_sutunlari)

if "df_2026_buyume_9" not in st.session_state:
    if os.path.exists(CACHE_2026_B):
        st.session_state.df_2026_buyume_9 = pd.read_parquet(CACHE_2026_B)
    else:
        st.session_state.df_2026_buyume_9 = pd.DataFrame()

if "df_2026_gercek_9" not in st.session_state:
    if os.path.exists(CACHE_2026_GERCEK_B):
        st.session_state.df_2026_gercek_9 = pd.read_parquet(CACHE_2026_GERCEK_B)
    else:
        # Eski önbellekle uyumluluk: yeni bir dosya yüklenene kadar mevcut 2026
        # verisi gerçekleşen kaynak olarak kabul edilir.
        st.session_state.df_2026_gercek_9 = (
            st.session_state.df_2026_buyume_9.copy()
        )

if "son_gerceklesen_ay_2026_9" not in st.session_state:
    st.session_state.son_gerceklesen_ay_2026_9 = "Ağustos"
if "upload_2026_imza_9" not in st.session_state:
    st.session_state.upload_2026_imza_9 = None
if "tahmin_uygulama_imza_9" not in st.session_state:
    st.session_state.tahmin_uygulama_imza_9 = None
if "eksik_2026_kolonlari_9" not in st.session_state:
    st.session_state.eksik_2026_kolonlari_9 = []

if "ana_veri" not in st.session_state: st.session_state.ana_veri = pd.DataFrame(columns=tum_kolonlar)
if "editor_key" not in st.session_state: st.session_state.editor_key = 0
if "musteri_ayarlari" not in st.session_state: st.session_state.musteri_ayarlari = {}
if "deg_anah_veri" not in st.session_state: st.session_state.deg_anah_veri = pd.DataFrame(columns=deg_anah_sutunlari)
if "parametre_editor_nonce" not in st.session_state:
    st.session_state.parametre_editor_nonce = 0
if "parametre_upload_imzasi" not in st.session_state:
    st.session_state.parametre_upload_imzasi = None
if "parametre_bulut_mesaji" not in st.session_state:
    st.session_state.parametre_bulut_mesaji = None
if "baz_yakit_veri" not in st.session_state: st.session_state.baz_yakit_veri = pd.DataFrame(columns=baz_yakit_sutunlari)
if "master_data_df" not in st.session_state: st.session_state.master_data_df = pd.DataFrame(columns=master_data_sutunlari)
if "master_data_ayarlari" not in st.session_state: st.session_state.master_data_ayarlari = {}
if "master_mazot_ayarlari" not in st.session_state: st.session_state.master_mazot_ayarlari = {}
if "master_enflasyon_ayarlari" not in st.session_state: st.session_state.master_enflasyon_ayarlari = {}
if "master_editor_nonce" not in st.session_state: st.session_state.master_editor_nonce = 0
if "master_son_islenen_surucu_imzasi" not in st.session_state:
    st.session_state.master_son_islenen_surucu_imzasi = None
if "master_bulut_yuklenen_revizyon" not in st.session_state:
    st.session_state.master_bulut_yuklenen_revizyon = None
if "master_bulut_kaynak_df" not in st.session_state:
    st.session_state.master_bulut_kaynak_df = pd.DataFrame(
        columns=master_data_sutunlari
    )
# Eski sürüm otomatik değerleri manuel sanabiliyordu. Yeni izleme modeline ilk
# geçişte yalnızca bir kez eski oturum işaretlerini temizle.
if st.session_state.get("master_mazot_izleme_surumu") != 2:
    st.session_state.master_mazot_ayarlari = {}
    st.session_state.master_mazot_izleme_surumu = 2
if st.session_state.get("master_enflasyon_izleme_surumu") != 1:
    st.session_state.master_enflasyon_ayarlari = {}
    st.session_state.master_enflasyon_izleme_surumu = 1
if "musteri_ekran_df" not in st.session_state: st.session_state.musteri_ekran_df = pd.DataFrame()
if "buyume_ayarlari" not in st.session_state: st.session_state.buyume_ayarlari = {}
if "buyume_ekran_df" not in st.session_state: st.session_state.buyume_ekran_df = pd.DataFrame()
if "buyume_tarihsel_upload_imzalari" not in st.session_state:
    st.session_state.buyume_tarihsel_upload_imzalari = {}
if "yil_kapanis_kg_df" not in st.session_state:
    st.session_state.yil_kapanis_kg_df = pd.DataFrame(
        columns=kg_musteri_sutunlari
    )
if "yil_kapanis_upload_imzasi" not in st.session_state:
    st.session_state.yil_kapanis_upload_imzasi = None
if "yil_kapanis_kayitli_sonuc_df" not in st.session_state:
    st.session_state.yil_kapanis_kayitli_sonuc_df = pd.DataFrame(
        columns=yil_kapanis_sonuc_sutunlari
    )
if "yil_kapanis_bulut_ayarlari" not in st.session_state:
    st.session_state.yil_kapanis_bulut_ayarlari = {}
if "yil_kapanis_detay_upload_df" not in st.session_state:
    st.session_state.yil_kapanis_detay_upload_df = pd.DataFrame(
        columns=yil_kapanis_detay_sutunlari
    )
if "yil_kapanis_detay_bulut_df" not in st.session_state:
    st.session_state.yil_kapanis_detay_bulut_df = pd.DataFrame(
        columns=yil_kapanis_detay_sutunlari
    )
if "yil_kapanis_data_new_bulut_df" not in st.session_state:
    st.session_state.yil_kapanis_data_new_bulut_df = pd.DataFrame()
if "yil_kapanis_data_new_bulut_revizyon" not in st.session_state:
    st.session_state.yil_kapanis_data_new_bulut_revizyon = None
if "yil_kapanis_detay_manuel_ayarlari" not in st.session_state:
    st.session_state.yil_kapanis_detay_manuel_ayarlari = {}
if "baz_birim_fiyat_df" not in st.session_state:
    st.session_state.baz_birim_fiyat_df = pd.DataFrame(
        columns=baz_birim_fiyat_sutunlari
    )
if "baz_birim_upload_imzasi" not in st.session_state:
    st.session_state.baz_birim_upload_imzasi = None
if "data_new_girdi_df" not in st.session_state:
    st.session_state.data_new_girdi_df = pd.DataFrame()
if "data_new_sonuc_df" not in st.session_state:
    st.session_state.data_new_sonuc_df = pd.DataFrame(
        columns=data_new_tum_sutunlar
    )
if "data_new_kaynak_df" not in st.session_state:
    st.session_state.data_new_kaynak_df = pd.DataFrame(
        columns=data_new_tum_sutunlar
    )
if "data_new_upload_imzasi" not in st.session_state:
    st.session_state.data_new_upload_imzasi = None
if "data_new_kontrol_bilgisi" not in st.session_state:
    st.session_state.data_new_kontrol_bilgisi = {}
if "data_new_buyume_ayarlari" not in st.session_state:
    st.session_state.data_new_buyume_ayarlari = {}
if "data_new_liste_filtreleri" not in st.session_state:
    st.session_state.data_new_liste_filtreleri = {}
if "data_new_filtre_nonce" not in st.session_state:
    st.session_state.data_new_filtre_nonce = 0
if "aktif_revizyon_id" not in st.session_state:
    st.session_state.aktif_revizyon_id = None
if "aktif_revizyon_adi" not in st.session_state:
    st.session_state.aktif_revizyon_adi = ""

if "mazot_giriş_veri" not in st.session_state:
    st.session_state.mazot_giriş_veri = pd.DataFrame([{
        "Baz Motorin": 45.8416, "Ocak": 45.99, "Şubat": 46.82, "Mart": 47.66, "Nisan": 48.76,
        "Mayıs": 49.81, "Haziran": 50.52, "Temmuz": 50.99, "Ağustos": 51.51, "Eylül": 52.09,
        "Ekim": 52.92, "Kasım": 53.76, "Aralık": 54.60
    }])

# ============================================================
# BULUT BAĞLANTISI, EVDS VE REVİZYONLARI ÇEKME (TEK SEFER)
# ============================================================
def gizli_ayar_getir(ayar_adi, varsayilan=""):
    """Streamlit Secrets, ardından ortam değişkeninden güvenli ayar okur."""
    deger = None
    try:
        deger = st.secrets.get(ayar_adi)
    except Exception:
        deger = None
    if deger is None or str(deger).strip() == "":
        deger = os.getenv(ayar_adi, varsayilan)
    return str(deger).strip() if deger is not None else ""


GIZLI_SUPABASE_URL = gizli_ayar_getir("SUPABASE_URL")
GIZLI_SUPABASE_KEY = gizli_ayar_getir("SUPABASE_KEY")
EVDS_API_KEY = gizli_ayar_getir("EVDS_API_KEY")

@st.cache_resource(show_spinner=False)
def get_supabase_client():
    if not SUPABASE_AVAILABLE or not GIZLI_SUPABASE_URL or not GIZLI_SUPABASE_KEY:
        return None
    try: return create_client(GIZLI_SUPABASE_URL, GIZLI_SUPABASE_KEY)
    except: return None

@st.cache_data(ttl=60, show_spinner=False)
def revizyon_loglarini_getir():
    bulut_client = get_supabase_client()
    if not bulut_client:
        return []
    sonuc = bulut_client.table("revizyon_log").select("*").execute()
    return sonuc.data or []

client = get_supabase_client()
rev_secenekleri = {}
revizyon_kayitlari = []
revizyon_id_haritasi = {}

if client:
    try:
        log_verileri = revizyon_loglarini_getir()

        if log_verileri:
            def revizyon_zamani(record):
                return str(
                    record.get("degistirilme_tarihi")
                    or record.get("olusturulma_tarihi")
                    or record.get("kayit_zamani")
                    or record.get("created_at")
                    or ""
                )

            sirali_data = sorted(
                log_verileri, key=revizyon_zamani, reverse=True
            )
            for r in sirali_data:
                rev_id = str(r.get("revizyon_id", "")).strip()
                if not rev_id:
                    continue
                rev_adi = str(
                    r.get("revizyon_adi")
                    or r.get("revizyon_notu")
                    or rev_id
                ).strip()
                kisi = str(r.get("olusturan_kisi") or "Bilinmiyor")
                tarih = revizyon_zamani(r)[:16].replace("T", " ")
                etiket = f"{rev_adi} | {kisi} | {tarih or 'Tarih Yok'}"
                rev_secenekleri[etiket] = rev_id
                revizyon_kayitlari.append(r)
                revizyon_id_haritasi[rev_id] = r

            aktif_id = st.session_state.get("aktif_revizyon_id")
            if aktif_id not in revizyon_id_haritasi and sirali_data:
                aktif_id = str(sirali_data[0].get("revizyon_id"))
                st.session_state.aktif_revizyon_id = aktif_id
            if aktif_id in revizyon_id_haritasi:
                aktif_kayit = revizyon_id_haritasi[aktif_id]
                st.session_state.aktif_revizyon_adi = str(
                    aktif_kayit.get("revizyon_adi")
                    or aktif_kayit.get("revizyon_notu")
                    or aktif_id
                )
    except Exception as e:
        st.error(f"☁️ Bulut (Supabase) geçmişi çekilirken bir hata oluştu: {e}")


def aktif_revizyon_id_getir():
    rev_id = st.session_state.get("aktif_revizyon_id")
    return rev_id if rev_id in revizyon_id_haritasi else None


def revizyonu_degistirildi_isaretle(revizyon_id):
    """Başarılı bulut kaydından sonra revizyonun son değişiklik bilgisini yeniler."""
    if not client or not revizyon_id:
        return
    try:
        client.table("revizyon_log").update({
            "son_degistiren": AKTIF_KULLANICI,
            "degistirilme_tarihi": datetime.now().astimezone().isoformat()
        }).eq("revizyon_id", revizyon_id).execute()
        revizyon_loglarini_getir.clear()
    except Exception:
        # Yeni metadata SQL'i çalıştırılmadan eski kayıt düğmeleri bozulmasın.
        pass


def aktif_revizyon_bilgisi_goster():
    rev_id = aktif_revizyon_id_getir()
    if rev_id:
        st.info(
            "Aktif Revizyon: "
            f"{st.session_state.get('aktif_revizyon_adi', rev_id)} "
            f"| Kullanıcı: {AKTIF_KULLANICI}"
        )
    else:
        st.warning(
            "Aktif revizyon yok. Bulut Revizyon Geçmişi sayfasından bir "
            "revizyon oluşturun veya mevcut bir revizyonu aktif edin."
        )
    return rev_id


def sayfa_aktif_revizyonunu_getir(container=None):
    """Sayfadaki kayıt/getir işlemlerini tek global aktif revizyona bağlar."""
    rev_id = aktif_revizyon_id_getir()
    hedef = container if container is not None else st
    if rev_id:
        hedef.caption(
            "Aktif revizyon: "
            f"{st.session_state.get('aktif_revizyon_adi', rev_id)}"
        )
    else:
        hedef.warning(
            "Önce Bulut Revizyon Geçmişi sayfasından bir revizyonu aktif edin."
        )
    return rev_id


def revizyon_oturumunu_temizle():
    """Revizyon değişirken önceki revizyona ait ekrandaki verileri ayırır."""
    st.session_state.data_sayfası_df = pd.DataFrame(
        columns=data_ekran_sutunlari
    )
    st.session_state.ana_veri = pd.DataFrame(columns=tum_kolonlar)
    st.session_state.musteri_ayarlari = {}
    st.session_state.musteri_ekran_df = pd.DataFrame()
    st.session_state.deg_anah_veri = pd.DataFrame(columns=deg_anah_sutunlari)
    st.session_state.parametre_upload_imzasi = None
    st.session_state.parametre_editor_nonce += 1
    st.session_state.baz_yakit_veri = pd.DataFrame(columns=baz_yakit_sutunlari)
    st.session_state.master_data_df = pd.DataFrame(columns=master_data_sutunlari)
    st.session_state.master_data_ayarlari = {}
    st.session_state.master_mazot_ayarlari = {}
    st.session_state.master_enflasyon_ayarlari = {}
    st.session_state.master_bulut_yuklenen_revizyon = None
    st.session_state.master_bulut_kaynak_df = pd.DataFrame(
        columns=master_data_sutunlari
    )
    st.session_state.master_editor_nonce += 1
    st.session_state.buyume_ayarlari = {}
    st.session_state.buyume_ekran_df = pd.DataFrame()
    st.session_state.buyume_tarihsel_upload_imzalari = {}
    st.session_state.yil_kapanis_kg_df = pd.DataFrame(
        columns=kg_musteri_sutunlari
    )
    st.session_state.yil_kapanis_upload_imzasi = None
    st.session_state.yil_kapanis_kayitli_sonuc_df = pd.DataFrame(
        columns=yil_kapanis_sonuc_sutunlari
    )
    st.session_state.yil_kapanis_bulut_ayarlari = {}
    st.session_state.yil_kapanis_detay_upload_df = pd.DataFrame(
        columns=yil_kapanis_detay_sutunlari
    )
    st.session_state.yil_kapanis_detay_bulut_df = pd.DataFrame(
        columns=yil_kapanis_detay_sutunlari
    )
    st.session_state.yil_kapanis_data_new_bulut_df = pd.DataFrame()
    st.session_state.yil_kapanis_data_new_bulut_revizyon = None
    st.session_state.yil_kapanis_detay_manuel_ayarlari = {}
    st.session_state.baz_birim_fiyat_df = pd.DataFrame(
        columns=baz_birim_fiyat_sutunlari
    )
    st.session_state.baz_birim_upload_imzasi = None
    st.session_state.data_new_girdi_df = pd.DataFrame()
    st.session_state.data_new_sonuc_df = pd.DataFrame(
        columns=data_new_tum_sutunlar
    )
    st.session_state.data_new_kaynak_df = pd.DataFrame(
        columns=data_new_tum_sutunlar
    )
    st.session_state.data_new_buyume_ayarlari = {}
    st.session_state.data_new_kontrol_bilgisi = {}
    st.session_state.data_new_upload_imzasi = None
    st.session_state.mazot_giriş_veri = pd.DataFrame([{
        "Baz Motorin": 45.8416, "Ocak": 45.99, "Şubat": 46.82,
        "Mart": 47.66, "Nisan": 48.76, "Mayıs": 49.81,
        "Haziran": 50.52, "Temmuz": 50.99, "Ağustos": 51.51,
        "Eylül": 52.09, "Ekim": 52.92, "Kasım": 53.76,
        "Aralık": 54.60
    }])
    st.session_state.pop("takvim_verisi_yillar", None)
    st.session_state.pop("takvim_yuklenen_revizyon", None)

# ============================================================
# VERİ TEMİZLEME MOTORU
# ============================================================
def sutun_adlarini_standartlastir(dataframe):
    """Excel başlıklarındaki gizli/fazla boşlukları tek biçime getirir."""
    df = dataframe.copy()
    df.columns = [
        re.sub(r"\s+", " ", str(col).replace("\xa0", " ")).strip()
        for col in df.columns
    ]
    return df

def guvenli_sayi(value):
    if value is None: return 0.0
    try:
        if pd.isna(value): return 0.0
    except: pass
    if isinstance(value, (int, float, np.integer, np.floating)):
        try:
            val = float(value)
            return val if np.isfinite(val) else 0.0
        except: return 0.0
    value = str(value).strip()
    if value.lower() in {"", "-", "nan", "none", "null", "nat"}: return 0.0
    value = (
        value.replace("₺", "")
        .replace("%", "")
        .replace("\xa0", "")
        .replace(" ", "")
    )

    # 85.0 ve 85,0 değerlerini 85 olarak korur.
    # Türkçe ve İngilizce binlik/ondalık biçimlerini güvenli okur.
    if "," in value and "." in value:
        if value.rfind(",") > value.rfind("."):
            value = value.replace(".", "").replace(",", ".")
        else:
            value = value.replace(",", "")
    elif "," in value:
        if value.count(",") == 1:
            value = value.replace(",", ".")
        else:
            value = value.replace(",", "")
    elif value.count(".") > 1:
        value = value.replace(".", "")
    elif value.count(".") == 1:
        sol_taraf, sag_taraf = value.split(".", 1)
        # Türkçe biçimde 2.325 binlik gösterimdir; 85.0 ise ondalık değerdir.
        if (
            sol_taraf.lstrip("-").isdigit()
            and sag_taraf.isdigit()
            and len(sag_taraf) == 3
        ):
            value = sol_taraf + sag_taraf
    try:
        val = float(value)
        return val if np.isfinite(val) else 0.0
    except: return 0.0

def guvenli_tamsayi(value, nullable=True):
    val = guvenli_sayi(value)
    return int(round(val)) if val != 0.0 or str(value).strip() == "0" else (None if nullable else 0)

def guvenli_metin_kodu(value):
    if pd.isna(value): return ""
    val_str = str(value).strip()
    try:
        val_float = float(val_str)
        if val_float.is_integer(): return str(int(val_float))
        return str(val_float)
    except: return val_str

def json_uyumlu_deger(value):
    if value is None or pd.isna(value): return None
    if isinstance(value, (pd.Timestamp, datetime, date)): return value.strftime("%Y-%m-%d")
    if isinstance(value, np.integer): return int(value)
    if isinstance(value, np.floating): return float(value) if np.isfinite(float(value)) else None
    if isinstance(value, np.bool_): return bool(value)
    return value


# ============================================================
# TCMB EVDS - AYLIK ÜFE / TÜFE GERÇEKLEŞEN VERİLERİ
# ============================================================
# TÜFE: 2025=100 Genel Endeks
# Yİ-ÜFE: Yurt İçi Üretici Fiyat Endeksi Genel
EVDS_TUFE_SERI_KODU = "TP.TUKFIY2025.GENEL"
EVDS_UFE_SERI_KODU = "TP.TUFE1YI.T1"
EVDS_SERVIS_KOKU = "https://evds3.tcmb.gov.tr/igmevdsms-dis"
ENFLASYON_DB_TABLOSU = "enflasyon_aylik_verileri"
ENFLASYON_REVIZYON_DB_TABLOSU = "enflasyon_revizyon_tablosu"
TAKVIM_REVIZYON_DB_TABLOSU = "takvim_revizyon_tablosu"


def nullable_sayi(value):
    """Boş ekonomik veriyi 0'a çevirmeden, varsa sayıya dönüştürür."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, (int, float, np.integer, np.floating)):
        sayi = float(value)
        return sayi if np.isfinite(sayi) else None
    metin = (
        str(value).strip().replace("%", "").replace("\xa0", "").replace(" ", "")
    )
    if metin.lower() in {"", "-", "nan", "none", "null", "nat", "nd"}:
        return None
    if "," in metin and "." in metin:
        if metin.rfind(",") > metin.rfind("."):
            metin = metin.replace(".", "").replace(",", ".")
        else:
            metin = metin.replace(",", "")
    elif "," in metin:
        metin = metin.replace(",", ".")
    try:
        sayi = float(metin)
        return sayi if np.isfinite(sayi) else None
    except (TypeError, ValueError):
        return None


def desi_kg_tam_sayiya_yuvarla(value):
    """Desi/Kg değerini Excel YUVARLA mantığıyla tam sayıya çevirir."""
    sayi = nullable_sayi(value)
    if sayi is None:
        return 0.0
    return float(
        np.floor(sayi + 0.5) if sayi >= 0 else np.ceil(sayi - 0.5)
    )


def desi_kg_serisini_yuvarla(seri):
    """Bir Desi/Kg serisini ondalıksız, sayısal değerler halinde döndürür."""
    return seri.apply(desi_kg_tam_sayiya_yuvarla).astype(float)


def temiz_metin(value, varsayilan=""):
    """Gizli boşlukları temizleyip gerçek boş değerleri korur."""
    if value is None:
        return varsayilan
    try:
        if pd.isna(value):
            return varsayilan
    except (TypeError, ValueError):
        pass
    metin = re.sub(r"\s+", " ", str(value).replace("\xa0", " ")).strip()
    return varsayilan if metin.lower() in {"", "nan", "none", "null", "nat"} else metin


def atf_tipini_standartlastir(value):
    return temiz_metin(value).upper()


def baz_birim_uniq_olustur(musteri_kodu, atf_tipi):
    return f"{guvenli_metin_kodu(musteri_kodu)}{atf_tipini_standartlastir(atf_tipi)}"


def yuklenen_tabloyu_oku(uploaded_file):
    """Excel/CSV yüklemelerini aynı başlık ve kodlama kurallarıyla okur."""
    dosya_adi = uploaded_file.name.lower()
    ham = uploaded_file.getvalue()
    buffer = io.BytesIO(ham)
    if dosya_adi.endswith(".csv"):
        for encoding in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                buffer.seek(0)
                df = pd.read_csv(
                    buffer, sep=None, engine="python", encoding=encoding
                )
                break
            except UnicodeDecodeError:
                continue
        else:
            raise ValueError("CSV dosyasının karakter kodlaması okunamadı.")
    else:
        df = pd.read_excel(buffer)
    return sutun_adlarini_standartlastir(df)


def yuklenen_dosya_imzasi(uploaded_file):
    return hashlib.sha256(uploaded_file.getvalue()).hexdigest()


def baz_birim_fiyat_tablosunu_hazirla(df_raw):
    df = sutun_adlarini_standartlastir(df_raw)
    for col in baz_birim_fiyat_sutunlari:
        if col not in df.columns:
            df[col] = np.nan if col == "TL/desi" else ""

    for col in [
        "Müşteri Adı", "Müşteri Grubu", "Müşteri Temsilcisi",
        "Durum", "Atf Tipi", "Açıklama"
    ]:
        df[col] = df[col].apply(temiz_metin)
    df["Müşteri Kodu"] = df["Müşteri Kodu"].apply(guvenli_metin_kodu)
    df["Atf Tipi"] = df["Atf Tipi"].apply(atf_tipini_standartlastir)
    df["TL/desi"] = df["TL/desi"].apply(nullable_sayi).astype(float)
    df["uniq"] = [
        baz_birim_uniq_olustur(mk, atf)
        for mk, atf in zip(df["Müşteri Kodu"], df["Atf Tipi"])
    ]
    df = df[(df["Müşteri Kodu"] != "") & (df["Atf Tipi"] != "")]
    return df[baz_birim_fiyat_sutunlari].reset_index(drop=True)


def dosya_oranini_yuzde_puanina_cevir(value):
    """Excel'in 0,40 biçimindeki yüzde değerini uygulamadaki 40'a çevirir."""
    sayi = nullable_sayi(value)
    if sayi is None:
        return np.nan
    return sayi * 100.0 if abs(sayi) <= 1.0 else sayi


def data_new_girdisini_hazirla(df_raw):
    """2025 operasyon dosyasını Data_New hesaplama şemasına dönüştürür."""
    df = sutun_adlarini_standartlastir(df_raw)
    kimlik_girdi = [c for c in ana_kolonlar if c != "Uniq ID"]
    for col in kimlik_girdi + parametre_kolonlari:
        if col not in df.columns:
            df[col] = np.nan

    metin_kolonlari = [
        "Teslimat Tipi", "Atf Tipi", "Çıkış İl Adı", "Çıkış Şube Adı",
        "Varış İl Adı", "Varış Şube Adı", "İlk Okutma Şubesi",
        "Müşteri Adı", "Müşteri Temsilcisi", "Sap Kodu", "Durum",
        "Müşteri Grubu"
    ]
    for col in metin_kolonlari:
        df[col] = df[col].apply(temiz_metin)
    df["Atf Tipi"] = df["Atf Tipi"].apply(atf_tipini_standartlastir)
    df["Müşteri Kodu"] = df["Müşteri Kodu"].apply(guvenli_metin_kodu)
    df["Yıl"] = df["Yıl"].apply(
        lambda v: guvenli_tamsayi(v, nullable=False)
    )

    for col in ["Kayıt Tarihi", "Esk. Yakıt Başlangıç Tarihi", "Esk. Enf. Başlangıç Tarihi"]:
        df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)

    oran_kolonlari = [
        "Yakıt Değişim Yüzdesi (%)", "Yakıt Anlık Değişim Oranı (%)",
        "Enf. Değişim Yüzdesi (%)"
    ]
    for col in oran_kolonlari:
        df[col] = df[col].apply(dosya_oranini_yuzde_puanina_cevir)
    for col in [
        "Yakıt Değişim Periyodu (Ay)", "Enf. Değişim Periyodu (Ay)",
        "Esk. Baz Yakıt Fiyatı"
    ]:
        df[col] = df[col].apply(nullable_sayi).astype(float)

    for ay in aylar:
        desi_kaynagi = next(
            (
                c for c in [f"{ay} Desi", f"{ay} Kg", f"2025 {ay} Desi", f"2025 {ay} Kg"]
                if c in df.columns
            ),
            None
        )
        tutar_kaynagi = next(
            (c for c in [f"{ay} Tutar", f"2025 {ay} Tutar"] if c in df.columns),
            None
        )
        df[f"2025 {ay} Desi"] = (
            desi_kg_serisini_yuvarla(df[desi_kaynagi])
            if desi_kaynagi else 0.0
        )
        df[f"2025 {ay} Tutar"] = (
            df[tutar_kaynagi].apply(guvenli_sayi).astype(float)
            if tutar_kaynagi else 0.0
        )

    uniq_parcalari = [
        "Yıl", "Teslimat Tipi", "Atf Tipi", "Çıkış İl Adı",
        "Çıkış Şube Adı", "Varış İl Adı", "Varış Şube Adı",
        "İlk Okutma Şubesi", "Müşteri Kodu"
    ]
    uniq_df = df[uniq_parcalari].copy()
    uniq_df["Yıl"] = uniq_df["Yıl"].apply(lambda v: str(int(v)))
    for col in uniq_parcalari[1:]:
        uniq_df[col] = uniq_df[col].apply(temiz_metin)
    df["Uniq ID"] = uniq_df.astype(str).agg("".join, axis=1)
    df = df[df["Müşteri Kodu"] != ""].reset_index(drop=True)
    baslangic_sutunlari = (
        data_new_kimlik_sutunlari
        + data_new_parametre_sutunlari
        + data_new_2025_desi_sutunlari
        + data_new_2025_tutar_sutunlari
    )
    return df.reindex(columns=baslangic_sutunlari)


def buyume_ayarlari_dataframe_olustur(ayarlar):
    rows = []
    for mkod, ayar in (ayarlar or {}).items():
        kullanilacak = nullable_sayi(ayar.get("KULLANICAK BÜYÜME"))
        row = {
            "Müşteri Kodu": guvenli_metin_kodu(mkod),
            "KULLANICAK BÜYÜME": kullanilacak
        }
        # Müşteri Büyüme Matrisi aylık değerleri varsa ay bazında kullanılır;
        # eski kayıtlarda aylık alan yoksa KULLANICAK BÜYÜME 12 aya uygulanır.
        for ay in aylar:
            aylik = nullable_sayi(ayar.get(ay))
            row[ay] = kullanilacak if aylik is None else aylik
        rows.append(row)
    return pd.DataFrame(rows)


def data_new_buyume_kaynaklarini_uygula(
    dataframe, buyume_df, hesaplari_yenile=False
):
    """Büyüme Matrisi Ocak-Aralık değerlerini müşteri koduyla Data_New'a taşır."""
    df = dataframe.copy()
    buyume = (
        sutun_adlarini_standartlastir(buyume_df)
        if buyume_df is not None else pd.DataFrame()
    )
    eslesme = pd.Series(False, index=df.index)
    if df.empty:
        return df, eslesme

    if not buyume.empty and "Müşteri Kodu" in buyume.columns:
        buyume["Müşteri Kodu"] = buyume["Müşteri Kodu"].apply(
            guvenli_metin_kodu
        )
        if BUYUME_AYLIK_ORANLAR_DB in buyume.columns:
            for idx, ham_ayar in buyume[BUYUME_AYLIK_ORANLAR_DB].items():
                if isinstance(ham_ayar, str):
                    try:
                        ham_ayar = json.loads(ham_ayar)
                    except (TypeError, ValueError, json.JSONDecodeError):
                        ham_ayar = {}
                if not isinstance(ham_ayar, dict):
                    continue
                for ay in aylar:
                    if ay in ham_ayar:
                        buyume.at[idx, ay] = nullable_sayi(ham_ayar.get(ay))
        buyume = buyume.drop_duplicates("Müşteri Kodu", keep="last")
        musteri_kodlari = df["Müşteri Kodu"].apply(guvenli_metin_kodu)
        if "KULLANICAK BÜYÜME" in buyume.columns:
            kullanilacak_map = (
                buyume.set_index("Müşteri Kodu")["KULLANICAK BÜYÜME"]
                .apply(nullable_sayi)
            )
            kullanilacak_seri = musteri_kodlari.map(kullanilacak_map)
        else:
            kullanilacak_seri = pd.Series(np.nan, index=df.index)
        for ay in aylar:
            if ay in buyume.columns:
                aylik_map = (
                    buyume.set_index("Müşteri Kodu")[ay]
                    .apply(nullable_sayi)
                )
                aylik_seri = musteri_kodlari.map(aylik_map)
                aylik_seri = aylik_seri.where(
                    aylik_seri.notna(), kullanilacak_seri
                )
            else:
                aylik_seri = kullanilacak_seri.copy()
            eslesme = eslesme | aylik_seri.notna()
            df[f"2026 {ay} Büyüme"] = pd.to_numeric(
                aylik_seri, errors="coerce"
            ).fillna(0.0)
    else:
        for ay in aylar:
            df[f"2026 {ay} Büyüme"] = 0.0

    if hesaplari_yenile:
        for ay in aylar:
            desi_25 = pd.to_numeric(
                df.get(f"2025 {ay} Desi", 0.0), errors="coerce"
            ).fillna(0.0)
            buyume_26 = pd.to_numeric(
                df[f"2026 {ay} Büyüme"], errors="coerce"
            ).fillna(0.0)
            desi_26 = desi_kg_serisini_yuvarla(
                desi_25 * (1.0 + buyume_26 / 100.0)
            )
            df[f"2026 {ay} Desi"] = desi_26
            fiyat_26 = pd.to_numeric(
                df.get(f"2026 {ay} Fiyat", np.nan), errors="coerce"
            )
            df[f"2026 {ay} Tutar"] = desi_26 * fiyat_26
    return df, eslesme


def supabase_revizyon_kayitlarini_getir(
    tablo_adi, revizyon_id, paket_boyutu=1000
):
    """PostgREST satır sınırına takılmadan bir revizyonun tamamını getirir."""
    if not client or not revizyon_id:
        return []
    tum_kayitlar = []
    baslangic = 0
    while True:
        sonuc = (
            client.table(tablo_adi)
            .select("*")
            .eq("revizyon_id", revizyon_id)
            .range(baslangic, baslangic + paket_boyutu - 1)
            .execute()
        )
        paket = sonuc.data or []
        tum_kayitlar.extend(paket)
        if len(paket) < paket_boyutu:
            break
        baslangic += paket_boyutu
    return tum_kayitlar


def master_bulut_kaydini_oturuma_yukle(revizyon_id, zorla=False):
    """Master Data manuel alanlarını seçili revizyondan oturuma geri yükler."""
    if not client or not revizyon_id:
        return 0
    if (
        not zorla
        and st.session_state.get("master_bulut_yuklenen_revizyon")
        == revizyon_id
    ):
        return 0

    kayitlar = supabase_revizyon_kayitlarini_getir(
        "master_data_tablosu", revizyon_id
    )
    if not kayitlar:
        st.session_state.master_bulut_kaynak_df = pd.DataFrame(
            columns=master_data_sutunlari
        )
        st.session_state.master_bulut_yuklenen_revizyon = revizyon_id
        return 0

    st.session_state.master_bulut_kaynak_df = pd.DataFrame(kayitlar).drop(
        columns=["id", "revizyon_id", "created_at", "updated_at"],
        errors="ignore"
    )

    st.session_state.master_data_ayarlari = {}
    st.session_state.master_mazot_ayarlari = {}
    st.session_state.master_enflasyon_ayarlari = {}

    for row in kayitlar:
        mkod = guvenli_metin_kodu(row.get("Müşteri Kodu"))
        if not mkod:
            continue
        st.session_state.master_data_ayarlari[mkod] = {
            col: row.get(col) for col in master_data_manuel_sutunlari
        }

        manuel_mazot_alanlari = row.get(
            MASTER_MAZOT_MANUEL_ALANLAR_DB, []
        )
        if isinstance(manuel_mazot_alanlari, str):
            try:
                manuel_mazot_alanlari = json.loads(manuel_mazot_alanlari)
            except (TypeError, ValueError, json.JSONDecodeError):
                manuel_mazot_alanlari = []
        if not isinstance(manuel_mazot_alanlari, list):
            manuel_mazot_alanlari = []
        st.session_state.master_mazot_ayarlari[mkod] = {
            col: row.get(col)
            for col in manuel_mazot_alanlari
            if col in master_data_mazot_sutunlari
        }

        manuel_enflasyon_alanlari = row.get(
            MASTER_ENFLASYON_MANUEL_ALANLAR_DB, []
        )
        if isinstance(manuel_enflasyon_alanlari, str):
            try:
                manuel_enflasyon_alanlari = json.loads(
                    manuel_enflasyon_alanlari
                )
            except (TypeError, ValueError, json.JSONDecodeError):
                manuel_enflasyon_alanlari = []
        if not isinstance(manuel_enflasyon_alanlari, list):
            manuel_enflasyon_alanlari = []
        st.session_state.master_enflasyon_ayarlari[mkod] = {
            col: row.get(col)
            for col in manuel_enflasyon_alanlari
            if col in master_data_enflasyon_sutunlari
        }

    st.session_state.master_bulut_yuklenen_revizyon = revizyon_id
    return len(kayitlar)


def yil_kapanis_grup_adi(value):
    grup = temiz_metin(value, "DİĞER").upper()
    return grup if grup in {"MP", "HOROZ CÜZDAN"} else "DİĞER"


def kg_musteri_verisini_hazirla(dataframe, varsayilan_yil=None):
    """Uzun veya yıl önekli müşteri-Kg kaynağını ortak şemaya dönüştürür."""
    if dataframe is None or dataframe.empty:
        return pd.DataFrame(columns=kg_musteri_sutunlari)
    df = sutun_adlarini_standartlastir(dataframe)
    if "Müşteri Kodu" not in df.columns:
        return pd.DataFrame(columns=kg_musteri_sutunlari)
    df["Müşteri Kodu"] = df["Müşteri Kodu"].apply(guvenli_metin_kodu)
    df = df[df["Müşteri Kodu"] != ""].copy()
    if df.empty:
        return pd.DataFrame(columns=kg_musteri_sutunlari)
    if "Müşteri Grubu" not in df.columns:
        df["Müşteri Grubu"] = "DİĞER"
    df["Müşteri Grubu"] = df["Müşteri Grubu"].apply(yil_kapanis_grup_adi)

    yillik_kolon_yillari = sorted({
        int(eslesme.group(1))
        for col in df.columns
        for eslesme in [re.match(r"^(20\d{2})\s+", str(col).strip())]
        if eslesme
    })
    parcalar = []

    def yil_parcasini_olustur(kaynak, yil, yillik_onek=False):
        parca = kaynak[["Müşteri Kodu", "Müşteri Grubu"]].copy()
        parca["Yıl"] = int(yil)
        for ay in aylar:
            adaylar = (
                [f"{yil} {ay} Kg", f"{yil} {ay} Desi"]
                if yillik_onek else
                [f"{ay} Kg", f"{ay} Desi", ay]
            )
            kaynak_col = next((c for c in adaylar if c in kaynak.columns), None)
            parca[f"{ay} Kg"] = (
                kaynak[kaynak_col].apply(guvenli_sayi).astype(float)
                if kaynak_col else 0.0
            )
        return parca

    if yillik_kolon_yillari:
        for yil in yillik_kolon_yillari:
            parcalar.append(yil_parcasini_olustur(df, yil, True))
    else:
        if "Yıl" in df.columns:
            yil_serisi = df["Yıl"].apply(
                lambda value: guvenli_tamsayi(value, nullable=True)
            )
        else:
            yil_serisi = pd.Series(varsayilan_yil, index=df.index)
        gecici = df.copy()
        gecici["__YIL"] = yil_serisi
        for yil in sorted({
            int(v) for v in gecici["__YIL"].dropna().tolist()
        }):
            yil_df = gecici[gecici["__YIL"] == yil].copy()
            parcalar.append(yil_parcasini_olustur(yil_df, yil, False))

    if not parcalar:
        return pd.DataFrame(columns=kg_musteri_sutunlari)
    birlesik = pd.concat(parcalar, ignore_index=True)
    ayliklar = [f"{ay} Kg" for ay in aylar]
    grup_haritasi = (
        birlesik.drop_duplicates(["Yıl", "Müşteri Kodu"], keep="last")
        .set_index(["Yıl", "Müşteri Kodu"])["Müşteri Grubu"]
        .to_dict()
    )
    sonuc = birlesik.groupby(
        ["Yıl", "Müşteri Kodu"], as_index=False
    )[ayliklar].sum()
    for col in ayliklar:
        sonuc[col] = desi_kg_serisini_yuvarla(sonuc[col])
    sonuc["Müşteri Grubu"] = [
        yil_kapanis_grup_adi(grup_haritasi.get((yil, kod), "DİĞER"))
        for yil, kod in zip(sonuc["Yıl"], sonuc["Müşteri Kodu"])
    ]
    return sonuc.reindex(columns=kg_musteri_sutunlari).reset_index(drop=True)


def kg_musteri_kaynaklarini_birlestir(*kaynaklar):
    """Sonraki kaynak öncelikli olacak şekilde müşteri-yıl kayıtlarını birleştirir."""
    hazirlar = [
        kaynak.copy() for kaynak in kaynaklar
        if kaynak is not None and not kaynak.empty
    ]
    if not hazirlar:
        return pd.DataFrame(columns=kg_musteri_sutunlari)
    sonuc = pd.concat(hazirlar, ignore_index=True)
    sonuc["Yıl"] = sonuc["Yıl"].apply(
        lambda value: guvenli_tamsayi(value, nullable=False)
    )
    sonuc["Müşteri Kodu"] = sonuc["Müşteri Kodu"].apply(guvenli_metin_kodu)
    sonuc = sonuc.drop_duplicates(
        ["Yıl", "Müşteri Kodu"], keep="last"
    )
    return sonuc.reindex(columns=kg_musteri_sutunlari).reset_index(drop=True)


def yil_kapanis_yuzde_matrisi(kg_musteri_df, yil):
    """Seçilen yılda her grubun aylık Kg paylarını yüzde puanı olarak üretir."""
    grup_sirasi = ["MP", "HOROZ CÜZDAN", "DİĞER"]
    kaynak = kg_musteri_df[
        pd.to_numeric(kg_musteri_df["Yıl"], errors="coerce") == int(yil)
    ].copy()
    ayliklar = [f"{ay} Kg" for ay in aylar]
    for col in ayliklar:
        kaynak[col] = pd.to_numeric(kaynak[col], errors="coerce").fillna(0.0)
    kaynak["Müşteri Grubu"] = kaynak["Müşteri Grubu"].apply(
        yil_kapanis_grup_adi
    )
    grup_toplamlari = (
        kaynak.groupby("Müşteri Grubu")[ayliklar].sum()
        .reindex(grup_sirasi, fill_value=0.0)
    )
    satirlar = []
    for grup in grup_sirasi:
        aylik_degerler = grup_toplamlari.loc[grup].to_numpy(dtype=float)
        yillik_toplam = float(aylik_degerler.sum())
        yuzdeler = (
            aylik_degerler / yillik_toplam * 100.0
            if yillik_toplam > 0 else np.zeros(len(aylar), dtype=float)
        )
        satirlar.append({
            "Müşteri Grubu": grup,
            **{ay: float(yuzdeler[i]) for i, ay in enumerate(aylar)}
        })
    return pd.DataFrame(satirlar)


def yil_kapanis_ortalamasini_hesapla(
    kg_musteri_df, yil_1, yil_2, son_gerceklesen_ay
):
    """İki yılın grup/ay yüzdelerinin aritmetik ortalamasını hesaplar."""
    matris_1 = yil_kapanis_yuzde_matrisi(kg_musteri_df, yil_1)
    matris_2 = yil_kapanis_yuzde_matrisi(kg_musteri_df, yil_2)
    harita_1 = matris_1.set_index("Müşteri Grubu")
    harita_2 = matris_2.set_index("Müşteri Grubu")
    son_ay_index = aylar.index(son_gerceklesen_ay)
    sonuc = []
    for grup in ["DİĞER", "HOROZ CÜZDAN", "MP"]:
        aylik_ortalamalar = {
            ay: (
                guvenli_sayi(harita_1.at[grup, ay])
                + guvenli_sayi(harita_2.at[grup, ay])
            ) / 2.0
            for ay in aylar
        }
        sonuc.append({
            "Müşteri Grubu": grup,
            **{f"{ay} (%)": aylik_ortalamalar[ay] for ay in aylar},
            "Gerçekleşen Dönem Payı (%)": sum(
                aylik_ortalamalar[ay] for ay in aylar[:son_ay_index + 1]
            )
        })
    return matris_1, matris_2, pd.DataFrame(sonuc)


def yil_kapanis_detayini_hazirla(dataframe, varsayilan_yil=None):
    """Operasyon detayını yıl kapanışının sabit 32 kolonlu şemasına çevirir."""
    if dataframe is None or dataframe.empty:
        return pd.DataFrame(columns=yil_kapanis_detay_sutunlari)
    kaynak = sutun_adlarini_standartlastir(dataframe)
    if "Müşteri Kodu" not in kaynak.columns:
        return pd.DataFrame(columns=yil_kapanis_detay_sutunlari)

    sonuc = pd.DataFrame(index=kaynak.index)
    for col in yil_kapanis_detay_kimlik_sutunlari:
        if col in kaynak.columns:
            sonuc[col] = kaynak[col]
        else:
            sonuc[col] = np.nan if col == "Yıl" else ""

    if "Yıl" in kaynak.columns:
        sonuc["Yıl"] = kaynak["Yıl"].apply(
            lambda value: guvenli_tamsayi(value, nullable=True)
        )
    else:
        sonuc["Yıl"] = varsayilan_yil
    if varsayilan_yil is not None:
        sonuc["Yıl"] = sonuc["Yıl"].fillna(int(varsayilan_yil))
    sonuc = sonuc[sonuc["Yıl"].notna()].copy()
    if sonuc.empty:
        return pd.DataFrame(columns=yil_kapanis_detay_sutunlari)
    sonuc["Yıl"] = sonuc["Yıl"].astype(int)

    sonuc["Müşteri Kodu"] = sonuc["Müşteri Kodu"].apply(
        guvenli_metin_kodu
    )
    sonuc = sonuc[sonuc["Müşteri Kodu"] != ""].copy()
    sonuc["Müşteri Grubu"] = sonuc["Müşteri Grubu"].apply(
        yil_kapanis_grup_adi
    )
    for col in [
        "Teslimat Tipi", "Atf Tipi", "Çıkış İl Adı", "Çıkış Şube Adı",
        "Varış İl Adı", "Varış Şube Adı", "İlk Okutma Şubesi",
        "Müşteri Adı", "Müşteri Temsilcisi", "Sap Kodu", "Durum"
    ]:
        sonuc[col] = sonuc[col].apply(temiz_metin)
    for col in [
        "Kayıt Tarihi", "Esk. Yakıt Başlangıç Tarihi",
        "Esk. Enf. Başlangıç Tarihi"
    ]:
        sonuc[col] = pd.to_datetime(
            sonuc[col], errors="coerce", dayfirst=True
        )

    for ay in aylar:
        hedef = pd.Series(0.0, index=sonuc.index, dtype=float)
        for yil in sonuc["Yıl"].dropna().astype(int).unique():
            yil_maskesi = sonuc["Yıl"] == yil
            adaylar = [
                f"{yil} {ay} Desi", f"{yil} {ay} Kg",
                f"{ay} Desi", f"{ay} Kg", ay
            ]
            kaynak_col = next(
                (col for col in adaylar if col in kaynak.columns), None
            )
            if kaynak_col:
                hedef.loc[yil_maskesi] = (
                    kaynak.loc[yil_maskesi, kaynak_col]
                    .apply(guvenli_sayi).astype(float)
                )
        sonuc[f"{ay} Desi"] = desi_kg_serisini_yuvarla(hedef)

    uniq_ham = sonuc["Uniq ID"].apply(temiz_metin)
    uniq_parcalari = [
        "Yıl", "Teslimat Tipi", "Atf Tipi", "Çıkış İl Adı",
        "Çıkış Şube Adı", "Varış İl Adı", "Varış Şube Adı",
        "İlk Okutma Şubesi", "Müşteri Kodu"
    ]
    olusturulan_uniq = sonuc[uniq_parcalari].fillna("").astype(str).agg(
        "".join, axis=1
    )
    sonuc["Uniq ID"] = uniq_ham.where(uniq_ham != "", olusturulan_uniq)
    sonuc = sonuc.drop_duplicates("Uniq ID", keep="last")
    sonuc["Gerçekleşen Toplam Desi"] = sonuc[
        yil_kapanis_detay_ay_sutunlari
    ].sum(axis=1)
    sonuc["Tahmini Yıl Sonu Toplam Desi"] = sonuc[
        "Gerçekleşen Toplam Desi"
    ]
    return sonuc.reindex(columns=yil_kapanis_detay_sutunlari).reset_index(
        drop=True
    )


def yil_kapanis_calisma_gunu_oranlari(takvim_df, kapanis_yili):
    """Kapanan yıl için önceki yıldan gelen aylık çalışma günü katsayıları."""
    oran_etiketi = (
        f"{str(int(kapanis_yili) - 1)[-2:]}to"
        f"{str(int(kapanis_yili))[-2:]}"
    )
    varsayilan = {ay: 1.0 for ay in aylar}
    if takvim_df is None or takvim_df.empty or "YIL" not in takvim_df.columns:
        return varsayilan, oran_etiketi, False

    takvim = takvim_df.copy()
    yil_serisi = takvim["YIL"].astype(str).str.strip()
    onceki = takvim[yil_serisi == str(int(kapanis_yili) - 1)]
    guncel = takvim[yil_serisi == str(int(kapanis_yili))]
    if not onceki.empty and not guncel.empty:
        oranlar = {}
        for ay in aylar:
            onceki_gun = guvenli_sayi(onceki.iloc[0].get(ay, 0.0))
            guncel_gun = guvenli_sayi(guncel.iloc[0].get(ay, 0.0))
            oranlar[ay] = (
                guncel_gun / onceki_gun if onceki_gun > 0 else 0.0
            )
        return oranlar, oran_etiketi, True

    hazir_oran = takvim[yil_serisi.str.lower() == oran_etiketi.lower()]
    if not hazir_oran.empty:
        return (
            {ay: guvenli_sayi(hazir_oran.iloc[0].get(ay, 1.0)) for ay in aylar},
            oran_etiketi,
            True
        )
    return varsayilan, oran_etiketi, False


def yil_kapanis_detay_tahminini_hesapla(
    detay_df, ortalama_sonuc, son_gerceklesen_ay, calisma_gunu_oranlari
):
    """Eksik ayları sabit gerçekleşen toplam ve sezon paylarıyla tamamlar."""
    if detay_df is None or detay_df.empty:
        return pd.DataFrame(columns=yil_kapanis_detay_sutunlari)
    sonuc = yil_kapanis_detayini_hazirla(detay_df)
    if sonuc.empty:
        return sonuc
    son_ay_index = aylar.index(son_gerceklesen_ay)
    gercek_sutunlar = [
        f"{ay} Desi" for ay in aylar[:son_ay_index + 1]
    ]
    gercek_toplam = sonuc[gercek_sutunlar].sum(axis=1).to_numpy(float)
    sonuc["Gerçekleşen Toplam Desi"] = gercek_toplam

    oran_haritasi = ortalama_sonuc.set_index("Müşteri Grubu")
    satir_gruplari = sonuc["Müşteri Grubu"].apply(yil_kapanis_grup_adi)
    grup_paydalari = {
        grup: sum(
            guvenli_sayi(oran_haritasi.at[grup, f"{ay} (%)"])
            for ay in aylar[:son_ay_index + 1]
        )
        for grup in oran_haritasi.index
    }
    payda = satir_gruplari.map(grup_paydalari).fillna(0.0).to_numpy(float)
    yillik_baz = np.divide(
        gercek_toplam,
        payda,
        out=np.zeros_like(gercek_toplam, dtype=float),
        where=payda > 0
    )

    for hedef_index in range(son_ay_index + 1, len(aylar)):
        hedef_ay = aylar[hedef_index]
        onceki_uc_sutun = [
            f"{ay} Desi"
            for ay in aylar[max(0, hedef_index - 3):hedef_index]
        ]
        onceki_uc_toplam = sonuc[onceki_uc_sutun].sum(
            axis=1
        ).to_numpy(float)
        hedef_pay_haritasi = {
            grup: guvenli_sayi(oran_haritasi.at[grup, f"{hedef_ay} (%)"])
            for grup in oran_haritasi.index
        }
        hedef_pay = satir_gruplari.map(hedef_pay_haritasi).fillna(
            0.0
        ).to_numpy(float)
        gun_orani = guvenli_sayi(
            calisma_gunu_oranlari.get(hedef_ay, 1.0)
        )
        tahmin = yillik_baz * hedef_pay * gun_orani
        sonuc[f"{hedef_ay} Desi"] = np.where(
            np.isclose(onceki_uc_toplam, 0.0),
            0.0,
            np.where(
                tahmin >= 0,
                np.floor(tahmin + 0.5),
                np.ceil(tahmin - 0.5)
            )
        )

    for col in yil_kapanis_detay_ay_sutunlari:
        sonuc[col] = desi_kg_serisini_yuvarla(sonuc[col])

    sonuc["Tahmini Yıl Sonu Toplam Desi"] = sonuc[
        yil_kapanis_detay_ay_sutunlari
    ].sum(axis=1)
    return sonuc.reindex(columns=yil_kapanis_detay_sutunlari)


def yil_kapanis_detay_toplamlarini_yenile(
    detay_df, son_gerceklesen_ay
):
    """Manuel Desi değişikliklerinden sonra dönem ve yıl toplamlarını yeniler."""
    if detay_df is None or detay_df.empty:
        return pd.DataFrame(columns=yil_kapanis_detay_sutunlari)
    sonuc = detay_df.copy()
    for col in yil_kapanis_detay_ay_sutunlari:
        if col not in sonuc.columns:
            sonuc[col] = 0.0
        sonuc[col] = desi_kg_serisini_yuvarla(sonuc[col])
    son_ay_index = aylar.index(son_gerceklesen_ay)
    gercek_sutunlar = [
        f"{ay} Desi" for ay in aylar[:son_ay_index + 1]
    ]
    sonuc["Gerçekleşen Toplam Desi"] = sonuc[gercek_sutunlar].sum(axis=1)
    sonuc["Tahmini Yıl Sonu Toplam Desi"] = sonuc[
        yil_kapanis_detay_ay_sutunlari
    ].sum(axis=1)
    return sonuc.reindex(columns=yil_kapanis_detay_sutunlari)


def yil_kapanis_manuel_baglami(
    revizyon_id, kapanis_yili, yil_1, yil_2, son_gerceklesen_ay
):
    """Yıl kapanışındaki manuel hücreleri doğru senaryodan ayırır."""
    return "|".join([
        temiz_metin(revizyon_id, "yerel"), str(int(kapanis_yili)),
        str(int(yil_1)), str(int(yil_2)), son_gerceklesen_ay
    ])


def yil_kapanis_manuel_degerlerini_uygula(detay_df, baglam):
    """Oturumdaki manuel Desi/tarih değerlerini hesaplanan tabloya uygular."""
    if detay_df is None or detay_df.empty:
        return detay_df
    sonuc = detay_df.copy()
    ayarlar = st.session_state.yil_kapanis_detay_manuel_ayarlari.get(
        baglam, {}
    )
    if not ayarlar:
        return sonuc
    index_haritasi = {
        temiz_metin(value): idx
        for idx, value in sonuc["Uniq ID"].items()
    }
    tarih_sutunlari = {
        "Kayıt Tarihi", "Esk. Yakıt Başlangıç Tarihi",
        "Esk. Enf. Başlangıç Tarihi"
    }
    for uniq_id, degisiklikler in ayarlar.items():
        idx = index_haritasi.get(temiz_metin(uniq_id))
        if idx is None:
            continue
        for col, value in degisiklikler.items():
            if col in yil_kapanis_detay_ay_sutunlari:
                sonuc.at[idx, col] = desi_kg_tam_sayiya_yuvarla(value)
            elif col in tarih_sutunlari:
                sonuc.at[idx, col] = pd.to_datetime(
                    value, errors="coerce", dayfirst=True
                )
    return sonuc


def yil_kapanis_manuel_degisikliklerini_kaydet(
    onceki_df, duzenlenen_df, baglam
):
    """Gridde gerçekten değiştirilen Desi/tarih hücrelerini oturumda saklar."""
    if (
        onceki_df is None or onceki_df.empty
        or duzenlenen_df is None or duzenlenen_df.empty
        or "Uniq ID" not in duzenlenen_df.columns
    ):
        return False
    onceki = onceki_df.copy()
    onceki["Uniq ID"] = onceki["Uniq ID"].apply(temiz_metin)
    onceki = onceki.drop_duplicates("Uniq ID", keep="last").set_index(
        "Uniq ID"
    )
    ayarlar = st.session_state.yil_kapanis_detay_manuel_ayarlari.setdefault(
        baglam, {}
    )
    tarih_sutunlari = [
        "Kayıt Tarihi", "Esk. Yakıt Başlangıç Tarihi",
        "Esk. Enf. Başlangıç Tarihi"
    ]
    degisti = False
    for _, row in duzenlenen_df.iterrows():
        uniq_id = temiz_metin(row.get("Uniq ID"))
        if not uniq_id or uniq_id not in onceki.index:
            continue
        satir_ayarlari = ayarlar.setdefault(uniq_id, {})
        for col in yil_kapanis_detay_ay_sutunlari:
            yeni = desi_kg_tam_sayiya_yuvarla(row.get(col))
            eski = desi_kg_tam_sayiya_yuvarla(onceki.at[uniq_id, col])
            if not np.isclose(yeni, eski):
                satir_ayarlari[col] = yeni
                degisti = True
        for col in tarih_sutunlari:
            yeni = pd.to_datetime(row.get(col), errors="coerce", dayfirst=True)
            eski = pd.to_datetime(
                onceki.at[uniq_id, col], errors="coerce", dayfirst=True
            )
            ayni = (pd.isna(yeni) and pd.isna(eski)) or (
                not pd.isna(yeni) and not pd.isna(eski)
                and yeni.normalize() == eski.normalize()
            )
            if not ayni:
                satir_ayarlari[col] = (
                    None if pd.isna(yeni) else yeni.date().isoformat()
                )
                degisti = True
        if not satir_ayarlari:
            ayarlar.pop(uniq_id, None)
    return degisti


def yil_kapanis_detay_toplam_satiri(detay_df, kapanis_yili=None):
    """Detay tablosunun aylık ve dönemsel genel toplam satırını oluşturur."""
    toplam = {col: "" for col in yil_kapanis_detay_sutunlari}
    toplam["Uniq ID"] = "🔥 GENEL TOPLAM"
    toplam["Müşteri Adı"] = "🔥 GENEL TOPLAM"
    toplam["Yıl"] = int(kapanis_yili) if kapanis_yili is not None else ""
    sayisal_sutunlar = (
        yil_kapanis_detay_ay_sutunlari
        + ["Gerçekleşen Toplam Desi", "Tahmini Yıl Sonu Toplam Desi"]
    )
    for col in sayisal_sutunlar:
        toplam[col] = float(
            pd.to_numeric(detay_df[col], errors="coerce").fillna(0.0).sum()
        )
    return toplam


def data_new_tablosunu_hesapla(girdi_df, master_df, buyume_df, baz_birim_df):
    """Data_New'un bütün 2025/2026 alanlarını toplu olarak hesaplar."""
    sonuc = girdi_df.copy().reset_index(drop=True)
    sonuc["Müşteri Kodu"] = sonuc["Müşteri Kodu"].apply(guvenli_metin_kodu)

    master = sutun_adlarini_standartlastir(master_df) if master_df is not None else pd.DataFrame()
    master_parametre_eslesmesi = pd.Series(False, index=sonuc.index)
    if not master.empty and "Müşteri Kodu" in master.columns:
        master["Müşteri Kodu"] = master["Müşteri Kodu"].apply(guvenli_metin_kodu)
        master = master.drop_duplicates("Müşteri Kodu", keep="last")
        kaynak_esleme = {
            "Yakıt Değişim Yüzdesi (%)": "Yakıt Değişim Yüzdesi (%)",
            "Yakıt Anlık Değişim Oranı (%)": "Yakıt Anlık Değişim Oranı (%)",
            "Yakıt Değişim Periyodu (Ay)": "Yakıt Değişim Periyodu (Ay)",
            "Enf. Değişim Yüzdesi (%)": "Enf. Değişim Yüzdesi (%)",
            "Enf. Değişim Periyodu (Ay)": "Enf. Değişim Periyodu (Ay)",
            "Esk. Baz Yakıt Fiyatı": "Esk. Baz Yakıt Fiyatı (KDV Hariç)",
            "Esk. Yakıt Başlangıç Tarihi": "Esk. Yakıt Başlangıç Tarihi",
            "Esk. Enf. Başlangıç Tarihi": "Esk. Enf. Başlangıç Tarihi"
        }
        alinacak = ["Müşteri Kodu"] + [
            c for c in kaynak_esleme.values() if c in master.columns
        ] + [
            c for c in master_data_eskalasyon_sutunlari if c in master.columns
        ]
        alinacak = list(dict.fromkeys(alinacak))
        master_join = master[alinacak].copy()
        master_join["__master_eslesti"] = True
        master_join = master_join.rename(
            columns={c: f"__master__{c}" for c in alinacak if c != "Müşteri Kodu"}
        )
        sonuc = sonuc.merge(master_join, on="Müşteri Kodu", how="left")
        master_parametre_eslesmesi = sonuc["__master_eslesti"].fillna(False)

        for hedef, kaynak in kaynak_esleme.items():
            kaynak_col = f"__master__{kaynak}"
            if kaynak_col not in sonuc.columns:
                continue
            master_degeri = sonuc[kaynak_col]
            sonuc[hedef] = master_degeri.where(master_degeri.notna(), sonuc[hedef])

        for ay in aylar:
            kaynak_col = f"__master__Eskalasyon {ay} (%)"
            sonuc[f"2026 {ay} Esk."] = (
                pd.to_numeric(sonuc[kaynak_col], errors="coerce").fillna(0.0)
                if kaynak_col in sonuc.columns else 0.0
            )
    else:
        for ay in aylar:
            sonuc[f"2026 {ay} Esk."] = 0.0

    sonuc, buyume_eslesmesi = data_new_buyume_kaynaklarini_uygula(
        sonuc, buyume_df, hesaplari_yenile=False
    )

    baz = baz_birim_fiyat_tablosunu_hazirla(baz_birim_df) if baz_birim_df is not None else pd.DataFrame()
    if not baz.empty:
        baz_map = baz.drop_duplicates("uniq", keep="last").set_index("uniq")["TL/desi"]
        baz_anahtari = [
            baz_birim_uniq_olustur(mk, atf)
            for mk, atf in zip(sonuc["Müşteri Kodu"], sonuc["Atf Tipi"])
        ]
        aralik_baz_fiyati = pd.Series(baz_anahtari, index=sonuc.index).map(baz_map)
    else:
        aralik_baz_fiyati = pd.Series(np.nan, index=sonuc.index)
    baz_eslesmesi = aralik_baz_fiyati.notna()

    for ay in aylar:
        desi = pd.to_numeric(sonuc[f"2025 {ay} Desi"], errors="coerce").fillna(0.0)
        tutar = pd.to_numeric(sonuc[f"2025 {ay} Tutar"], errors="coerce").fillna(0.0)
        sonuc[f"2025 {ay} Fiyat"] = np.where(desi != 0.0, tutar / desi, np.nan)
    # Kullanıcı kararı: dosyadaki gerçekleşenden bağımsız olarak Aralık fiyatı
    # her zaman Baz Birim Fiyatlar sayfasından gelir.
    sonuc["2025 Aralık Fiyat"] = pd.to_numeric(aralik_baz_fiyati, errors="coerce")

    onceki_fiyat = sonuc["2025 Aralık Fiyat"].copy()
    for ay in aylar:
        buyume_col = f"2026 {ay} Büyüme"
        esk_col = f"2026 {ay} Esk."
        desi_25 = pd.to_numeric(sonuc[f"2025 {ay} Desi"], errors="coerce").fillna(0.0)
        sonuc[f"2026 {ay} Desi"] = desi_kg_serisini_yuvarla(
            desi_25 * (
                1.0
                + pd.to_numeric(
                    sonuc[buyume_col], errors="coerce"
                ).fillna(0.0) / 100.0
            )
        )
        yeni_fiyat = onceki_fiyat * (
            1.0 + pd.to_numeric(sonuc[esk_col], errors="coerce").fillna(0.0) / 100.0
        )
        sonuc[f"2026 {ay} Fiyat"] = yeni_fiyat
        sonuc[f"2026 {ay} Tutar"] = sonuc[f"2026 {ay} Desi"] * yeni_fiyat
        onceki_fiyat = yeni_fiyat

    yardimci_kolonlar = [
        c for c in sonuc.columns if c.startswith("__master")
    ]
    sonuc = sonuc.drop(columns=yardimci_kolonlar, errors="ignore")
    for col in ["Kayıt Tarihi", "Esk. Yakıt Başlangıç Tarihi", "Esk. Enf. Başlangıç Tarihi"]:
        sonuc[col] = pd.to_datetime(sonuc[col], errors="coerce", dayfirst=True).dt.date

    kontrol = {
        "satir_sayisi": int(len(sonuc)),
        "tekrarlanan_uniq": int(sonuc["Uniq ID"].duplicated(keep=False).sum()),
        "master_eslesmeyen": int((~master_parametre_eslesmesi).sum()),
        "buyume_eslesmeyen": int((~buyume_eslesmesi).sum()),
        "baz_fiyat_eslesmeyen": int((~baz_eslesmesi).sum())
    }
    return sonuc.reindex(columns=data_new_tum_sutunlar), kontrol


def data_new_manuel_buyumeleri_uygula(dataframe, manuel_ayarlar):
    """Satır/ay bazlı büyüme düzeltmelerini Desi ve Tutar'a yansıtır."""
    df = dataframe.copy()
    if df.empty or not manuel_ayarlar or "Uniq ID" not in df.columns:
        return df
    uniq_index = pd.Series(df.index, index=df["Uniq ID"].astype(str)).to_dict()
    for uniq_id, ayarlar in manuel_ayarlar.items():
        idx = uniq_index.get(str(uniq_id))
        if idx is None or not isinstance(ayarlar, dict):
            continue
        for buyume_col, value in ayarlar.items():
            if buyume_col not in data_new_2026_buyume_sutunlari:
                continue
            ay = buyume_col.removeprefix("2026 ").removesuffix(" Büyüme")
            buyume = guvenli_sayi(value)
            desi_25 = guvenli_sayi(df.at[idx, f"2025 {ay} Desi"])
            fiyat_26 = nullable_sayi(df.at[idx, f"2026 {ay} Fiyat"])
            desi_26 = desi_kg_tam_sayiya_yuvarla(
                desi_25 * (1.0 + buyume / 100.0)
            )
            df.at[idx, buyume_col] = buyume
            df.at[idx, f"2026 {ay} Desi"] = desi_26
            df.at[idx, f"2026 {ay} Tutar"] = (
                np.nan if fiyat_26 is None else desi_26 * fiyat_26
            )
    return df


def data_new_tarihlerini_gosterime_hazirla(dataframe):
    """AG Grid'e tarih nesnesi yerine GG.AA.YYYY metni gönderir."""
    df = dataframe.copy()
    tarih_sutunlari = [
        "Kayıt Tarihi",
        "Esk. Yakıt Başlangıç Tarihi",
        "Esk. Enf. Başlangıç Tarihi"
    ]

    def tarih_metni(value):
        if value is None:
            return ""
        try:
            if pd.isna(value):
                return ""
        except (TypeError, ValueError):
            pass
        if isinstance(value, dict):
            if {"year", "month", "day"}.issubset(value):
                try:
                    return date(
                        int(value["year"]),
                        int(value["month"]),
                        int(value["day"])
                    ).strftime("%d.%m.%Y")
                except (TypeError, ValueError):
                    return ""
            value = value.get("value", value.get("date", ""))
        metin = str(value).strip()
        if re.match(r"^\d{4}-\d{1,2}-\d{1,2}", metin):
            tarih = pd.to_datetime(
                metin[:10], errors="coerce", format="%Y-%m-%d"
            )
        else:
            tarih = pd.to_datetime(value, errors="coerce", dayfirst=True)
        if pd.isna(tarih):
            return ""
        return pd.Timestamp(tarih).strftime("%d.%m.%Y")

    for col in tarih_sutunlari:
        if col in df.columns:
            df[col] = df[col].apply(tarih_metni)
    return df


def evds_alan_adi_normallestir(value):
    """EVDS JSON alanlarını seri koduyla güvenli eşleştirmek için sadeleştirir."""
    return re.sub(r"[^A-Z0-9]+", "_", str(value).upper()).strip("_")


def evds_tarih_degerini_oku(value):
    if value is None:
        return None
    metin = str(value).strip()
    if not metin:
        return None
    for dayfirst in (True, False):
        tarih = pd.to_datetime(metin, errors="coerce", dayfirst=dayfirst)
        if not pd.isna(tarih):
            return pd.Timestamp(tarih).normalize()
    return None


@st.cache_data(ttl=3600, show_spinner=False)
def evds_aylik_enflasyon_getir(baslangic_yili, bitis_yili, api_key):
    """EVDS'den aylık ÜFE/TÜFE yüzde değişimlerini tek çağrıda getirir."""
    if not api_key:
        raise ValueError("EVDS_API_KEY Streamlit Secrets içinde bulunamadı.")

    baslangic_yili = int(baslangic_yili)
    bitis_yili = int(bitis_yili)
    if bitis_yili < baslangic_yili:
        raise ValueError("Bitiş yılı başlangıç yılından küçük olamaz.")

    # Ocak değişiminin hesaplanabilmesi için bir önceki Aralık da istenir.
    servis_baslangici = pd.Timestamp(
        year=baslangic_yili - 1, month=12, day=1
    )
    servis_bitisi = pd.Timestamp(year=bitis_yili, month=12, day=31)
    seri_parametresi = f"{EVDS_TUFE_SERI_KODU}-{EVDS_UFE_SERI_KODU}"
    url = (
        f"{EVDS_SERVIS_KOKU}/series={seri_parametresi}"
        f"&startDate={servis_baslangici.strftime('%d-%m-%Y')}"
        f"&endDate={servis_bitisi.strftime('%d-%m-%Y')}"
        "&type=json&formulas=1-1&frequency=5"
    )
    istek = urllib.request.Request(
        url,
        headers={
            "key": api_key,
            "Accept": "application/json",
            "User-Agent": "Budget-Simulation-Streamlit/1.0"
        },
        method="GET"
    )
    try:
        with urllib.request.urlopen(istek, timeout=60) as yanit:
            ham_metin = yanit.read().decode("utf-8-sig")
    except urllib.error.HTTPError as hata:
        if hata.code == 403:
            raise RuntimeError(
                "EVDS erişimi reddedildi (403). EVDS_API_KEY değerini kontrol edin."
            ) from hata
        raise RuntimeError(f"EVDS HTTP hatası: {hata.code}") from hata
    except urllib.error.URLError as hata:
        neden = getattr(hata, "reason", hata)
        raise RuntimeError(f"EVDS bağlantısı kurulamadı: {neden}") from hata

    try:
        govde = json.loads(ham_metin)
    except json.JSONDecodeError as hata:
        raise RuntimeError("EVDS geçerli JSON döndürmedi.") from hata

    if isinstance(govde, dict):
        satirlar = govde.get("items") or govde.get("data") or govde.get("results") or []
    elif isinstance(govde, list):
        satirlar = govde
    else:
        satirlar = []
    if not satirlar:
        raise RuntimeError("EVDS seçilen yıllar için veri döndürmedi.")

    ilk_satir = next((s for s in satirlar if isinstance(s, dict)), {})
    tarih_adaylari = [
        k for k in ilk_satir
        if evds_alan_adi_normallestir(k) in {
            "TARIH", "DATE", "DONEM", "PERIOD", "OBSERVATION_DATE"
        }
    ]
    if not tarih_adaylari:
        tarih_adaylari = [
            k for k in ilk_satir
            if "TARIH" in evds_alan_adi_normallestir(k)
            or "DATE" in evds_alan_adi_normallestir(k)
        ]
    if not tarih_adaylari:
        raise RuntimeError("EVDS yanıtındaki tarih alanı bulunamadı.")
    tarih_alani = tarih_adaylari[0]

    def seri_alanini_bul(seri_kodu):
        hedef = evds_alan_adi_normallestir(seri_kodu)
        adaylar = []
        for alan in ilk_satir:
            norm = evds_alan_adi_normallestir(alan)
            if alan == tarih_alani or norm in {"UNIXTIME", "FREQUENCY"}:
                continue
            if norm == hedef:
                return alan
            if norm.startswith(hedef) or hedef.startswith(norm):
                adaylar.append(alan)
        return adaylar[0] if adaylar else None

    tufe_alani = seri_alanini_bul(EVDS_TUFE_SERI_KODU)
    ufe_alani = seri_alanini_bul(EVDS_UFE_SERI_KODU)
    if not tufe_alani or not ufe_alani:
        veri_alanlari = [
            k for k in ilk_satir
            if k != tarih_alani
            and evds_alan_adi_normallestir(k) not in {"UNIXTIME", "FREQUENCY"}
        ]
        if len(veri_alanlari) >= 2:
            tufe_alani = tufe_alani or veri_alanlari[0]
            ufe_alani = ufe_alani or veri_alanlari[1]
    if not tufe_alani or not ufe_alani:
        raise RuntimeError("EVDS yanıtındaki ÜFE/TÜFE seri alanları eşleştirilemedi.")

    sonuclar = []
    guncelleme_zamani = datetime.now().astimezone().isoformat()
    for satir in satirlar:
        if not isinstance(satir, dict):
            continue
        donem = evds_tarih_degerini_oku(satir.get(tarih_alani))
        if donem is None or not (baslangic_yili <= donem.year <= bitis_yili):
            continue
        tufe = nullable_sayi(satir.get(tufe_alani))
        ufe = nullable_sayi(satir.get(ufe_alani))
        # Henüz açıklanmayan aylar Supabase'e boş kayıt olarak gönderilmez.
        if tufe is None and ufe is None:
            continue
        sonuclar.append({
            "yil": int(donem.year),
            "ay": int(donem.month),
            "donem": donem.strftime("%Y-%m-01"),
            "ufe_gerceklesen_oran": ufe,
            "tufe_gerceklesen_oran": tufe,
            "evds_ufe_seri_kodu": EVDS_UFE_SERI_KODU,
            "evds_tufe_seri_kodu": EVDS_TUFE_SERI_KODU,
            "kaynak": "TCMB EVDS / TÜİK",
            "kaynak_url": "https://evds3.tcmb.gov.tr/",
            "kaynak_guncelleme_zamani": guncelleme_zamani
        })

    if not sonuclar:
        raise RuntimeError("EVDS yanıtında kullanılabilir aylık oran bulunamadı.")
    return sonuclar


def enflasyon_bulut_verilerini_getir(
    baslangic_yili, bitis_yili, revizyon_id=None
):
    if not client:
        return pd.DataFrame()
    yanit = (
        client.table(ENFLASYON_DB_TABLOSU)
        .select("*")
        .gte("yil", int(baslangic_yili))
        .lte("yil", int(bitis_yili))
        .order("yil")
        .order("ay")
        .execute()
    )
    ortak_df = pd.DataFrame(yanit.data or [])
    if not revizyon_id:
        return ortak_df

    try:
        rev_yanit = (
            client.table(ENFLASYON_REVIZYON_DB_TABLOSU)
            .select("*")
            .eq("revizyon_id", revizyon_id)
            .gte("yil", int(baslangic_yili))
            .lte("yil", int(bitis_yili))
            .order("yil")
            .order("ay")
            .execute()
        )
        rev_df = pd.DataFrame(rev_yanit.data or [])
    except Exception:
        # Yeni revizyon tablosu kurulmadan ortak veriler çalışmaya devam eder.
        return ortak_df
    if rev_df.empty:
        return ortak_df

    birlesik = ortak_df.copy()
    if birlesik.empty:
        birlesik = pd.DataFrame(columns=["yil", "ay"])
    for df in [birlesik, rev_df]:
        df["yil"] = pd.to_numeric(df.get("yil"), errors="coerce").astype("Int64")
        df["ay"] = pd.to_numeric(df.get("ay"), errors="coerce").astype("Int64")
    birlesik = birlesik.set_index(["yil", "ay"], drop=False)
    rev_df = rev_df.set_index(["yil", "ay"], drop=False)
    rev_alanlari = [
        "donem", "ufe_tahmin_oran", "tufe_tahmin_oran",
        "ufe_manuel_oran", "tufe_manuel_oran"
    ]
    for anahtar, row in rev_df.iterrows():
        if anahtar not in birlesik.index:
            birlesik.loc[anahtar, "yil"] = int(anahtar[0])
            birlesik.loc[anahtar, "ay"] = int(anahtar[1])
        for alan in rev_alanlari:
            if alan in row.index and pd.notna(row.get(alan)):
                birlesik.loc[anahtar, alan] = row.get(alan)
    return birlesik.reset_index(drop=True)


def enflasyon_editor_tablosu_olustur(baslangic_yili, bitis_yili, bulut_df):
    satirlar = []
    for yil in range(int(baslangic_yili), int(bitis_yili) + 1):
        for ay_no, ay_adi in enumerate(aylar, start=1):
            satirlar.append({
                "yil": yil,
                "ay": ay_no,
                "Ay": ay_adi,
                "donem": date(yil, ay_no, 1)
            })
    temel = pd.DataFrame(satirlar)
    if bulut_df is not None and not bulut_df.empty:
        kullanilacak = bulut_df.drop(
            columns=[c for c in ["id", "created_at"] if c in bulut_df.columns],
            errors="ignore"
        ).copy()
        kullanilacak["yil"] = pd.to_numeric(
            kullanilacak["yil"], errors="coerce"
        ).astype("Int64")
        kullanilacak["ay"] = pd.to_numeric(
            kullanilacak["ay"], errors="coerce"
        ).astype("Int64")
        kullanilacak = kullanilacak.drop(columns=["donem"], errors="ignore")
        temel = temel.merge(kullanilacak, on=["yil", "ay"], how="left")

    oran_kolonlari = [
        "ufe_gerceklesen_oran", "tufe_gerceklesen_oran",
        "ufe_tahmin_oran", "tufe_tahmin_oran",
        "ufe_manuel_oran", "tufe_manuel_oran"
    ]
    for kolon in oran_kolonlari:
        if kolon not in temel.columns:
            temel[kolon] = np.nan
        temel[kolon] = pd.to_numeric(temel[kolon], errors="coerce")

    temel["ufe_kullanilan_oran"] = temel["ufe_manuel_oran"].combine_first(
        temel["ufe_gerceklesen_oran"]
    ).combine_first(temel["ufe_tahmin_oran"])
    temel["tufe_kullanilan_oran"] = temel["tufe_manuel_oran"].combine_first(
        temel["tufe_gerceklesen_oran"]
    ).combine_first(temel["tufe_tahmin_oran"])

    def kaynak_durumu(row):
        if pd.notna(row["ufe_manuel_oran"]) or pd.notna(row["tufe_manuel_oran"]):
            return "Manuel düzeltme"
        if pd.notna(row["ufe_gerceklesen_oran"]) or pd.notna(row["tufe_gerceklesen_oran"]):
            return "Gerçekleşen"
        if pd.notna(row["ufe_tahmin_oran"]) or pd.notna(row["tufe_tahmin_oran"]):
            return "Tahmin"
        return "Boş"

    temel["Veri Durumu"] = temel.apply(kaynak_durumu, axis=1)
    yeniden_adlandir = {
        "yil": "Yıl",
        "donem": "Dönem",
        "ufe_gerceklesen_oran": "ÜFE Gerçekleşen (%)",
        "tufe_gerceklesen_oran": "TÜFE Gerçekleşen (%)",
        "ufe_tahmin_oran": "ÜFE Tahmin (%)",
        "tufe_tahmin_oran": "TÜFE Tahmin (%)",
        "ufe_manuel_oran": "ÜFE Manuel (%)",
        "tufe_manuel_oran": "TÜFE Manuel (%)",
        "ufe_kullanilan_oran": "ÜFE Kullanılan (%)",
        "tufe_kullanilan_oran": "TÜFE Kullanılan (%)"
    }
    temel = temel.rename(columns=yeniden_adlandir)
    return temel[[
        "Yıl", "Ay", "Dönem",
        "ÜFE Gerçekleşen (%)", "TÜFE Gerçekleşen (%)",
        "ÜFE Tahmin (%)", "TÜFE Tahmin (%)",
        "ÜFE Manuel (%)", "TÜFE Manuel (%)",
        "ÜFE Kullanılan (%)", "TÜFE Kullanılan (%)", "Veri Durumu"
    ]]


@st.cache_data(ttl=60, show_spinner=False)
def master_enflasyon_kaynaklarini_getir(revizyon_id=None):
    """Master Data hesapları için ekonomik verileri Supabase'den tek kez okur."""
    bulut_client = get_supabase_client()
    if not bulut_client:
        return [], []
    enflasyon_kayitlari = (
        bulut_client.table(ENFLASYON_DB_TABLOSU)
        .select("*")
        .order("yil")
        .order("ay")
        .execute()
    ).data or []
    if revizyon_id:
        try:
            rev_kayitlari = (
                bulut_client.table(ENFLASYON_REVIZYON_DB_TABLOSU)
                .select("*")
                .eq("revizyon_id", revizyon_id)
                .order("yil")
                .order("ay")
                .execute()
            ).data or []
            kayit_haritasi = {
                (int(k["yil"]), int(k["ay"])): dict(k)
                for k in enflasyon_kayitlari
                if k.get("yil") is not None and k.get("ay") is not None
            }
            for rev_kayit in rev_kayitlari:
                anahtar = (int(rev_kayit["yil"]), int(rev_kayit["ay"]))
                hedef = kayit_haritasi.setdefault(
                    anahtar,
                    {"yil": anahtar[0], "ay": anahtar[1]}
                )
                for alan in [
                    "donem", "ufe_tahmin_oran", "tufe_tahmin_oran",
                    "ufe_manuel_oran", "tufe_manuel_oran"
                ]:
                    if rev_kayit.get(alan) is not None:
                        hedef[alan] = rev_kayit.get(alan)
            enflasyon_kayitlari = list(kayit_haritasi.values())
        except Exception:
            pass
    try:
        asgari_kayitlari = (
            bulut_client.table("asgari_ucret_hesaplanan")
            .select("*")
            .order("donem_baslangic")
            .execute()
        ).data or []
    except Exception:
        # Asgari ücret tablosu boş/erişilemez olsa da ÜFE+TÜFE hesabı çalışır.
        asgari_kayitlari = []
    return enflasyon_kayitlari, asgari_kayitlari


def degisim_anahtarini_normallestir(value):
    return (
        str(value or "").strip().upper()
        .replace("İ", "I").replace("Ş", "S").replace("Ğ", "G")
        .replace("Ü", "U").replace("Ö", "O").replace("Ç", "C")
    )


def aylik_oranlari_bilesik_hesapla(oranlar):
    """Yüzde puan listesini bileşik dönemsel yüzde değişime dönüştürür."""
    if not oranlar:
        return None
    carpim = 1.0
    for oran in oranlar:
        sayi = nullable_sayi(oran)
        if sayi is None:
            return None
        carpim *= 1.0 + (sayi / 100.0)
    return (carpim - 1.0) * 100.0


def sabit_enflasyon_uygulama_tarihleri(
    periyot, baslangic_tarihi, hedef_yil=2026
):
    """Başlangıca bağlı ve yıl içinde değişmeyen enflasyon uygulama takvimidir."""
    periyot_sayisi = guvenli_tamsayi(periyot, nullable=True)
    baslangic = yakit_baslangic_tarihini_hazirla(baslangic_tarihi)
    if periyot_sayisi is None or periyot_sayisi <= 0 or baslangic is None:
        return []

    baslangic = pd.Timestamp(
        year=baslangic.year, month=baslangic.month, day=1
    )
    yil_basi = pd.Timestamp(year=hedef_yil, month=1, day=1)
    yil_sonu = pd.Timestamp(year=hedef_yil, month=12, day=1)
    uygulama = baslangic + pd.DateOffset(months=periyot_sayisi)
    guvenlik = 0
    while uygulama < yil_basi and guvenlik < 240:
        uygulama += pd.DateOffset(months=periyot_sayisi)
        guvenlik += 1

    tarihler = []
    while uygulama <= yil_sonu and guvenlik < 480:
        tarihler.append(pd.Timestamp(uygulama).normalize())
        uygulama += pd.DateOffset(months=periyot_sayisi)
        guvenlik += 1
    return tarihler


def enflasyon_kaynak_haritasi_olustur(enflasyon_kayitlari):
    """DB satırlarını (yıl, ay) -> (kullanılan ÜFE, kullanılan TÜFE) yapar."""
    harita = {}
    for row in enflasyon_kayitlari or []:
        try:
            yil = int(row.get("yil"))
            ay_no = int(row.get("ay"))
        except (TypeError, ValueError):
            continue
        ufe = nullable_sayi(row.get("ufe_kullanilan_oran"))
        if ufe is None:
            ufe = next((
                nullable_sayi(row.get(c))
                for c in [
                    "ufe_manuel_oran", "ufe_gerceklesen_oran", "ufe_tahmin_oran"
                ]
                if nullable_sayi(row.get(c)) is not None
            ), None)
        tufe = nullable_sayi(row.get("tufe_kullanilan_oran"))
        if tufe is None:
            tufe = next((
                nullable_sayi(row.get(c))
                for c in [
                    "tufe_manuel_oran", "tufe_gerceklesen_oran", "tufe_tahmin_oran"
                ]
                if nullable_sayi(row.get(c)) is not None
            ), None)
        harita[(yil, ay_no)] = (ufe, tufe)
    return harita


def donemdeki_asgari_ucret_artisini_bul(
    asgari_kayitlari, onceki_uygulama_tarihi, uygulama_tarihi
):
    """İki eskalasyon tarihi arasında yürürlüğe giren en yüksek artışı bulur."""
    bulunan = []
    for row in asgari_kayitlari or []:
        tarih = yakit_baslangic_tarihini_hazirla(row.get("donem_baslangic"))
        oran = nullable_sayi(row.get("artis_orani_yuzde"))
        if tarih is None or oran is None:
            continue
        if onceki_uygulama_tarihi < tarih <= uygulama_tarihi:
            bulunan.append(oran)
    return max(bulunan) if bulunan else None


def musteri_enflasyon_oranlarini_getir(
    degisim_anahtari,
    periyot,
    baslangic_tarihi,
    enflasyon_kaynak_haritasi,
    asgari_kayitlari=None,
    hedef_yil=2026
):
    """Sabit periyotlarla müşterinin 12 aylık enflasyon eskalasyonunu üretir."""
    sonuc = {f"Enflasyon {ay} (%)": np.nan for ay in aylar}
    anahtar = degisim_anahtarini_normallestir(degisim_anahtari)
    if "GECERSIZ" in anahtar or not ("UFE" in anahtar and "TUFE" in anahtar):
        return sonuc

    periyot_sayisi = guvenli_tamsayi(periyot, nullable=True)
    if periyot_sayisi is None or periyot_sayisi <= 0:
        return sonuc
    uygulama_tarihleri = sabit_enflasyon_uygulama_tarihleri(
        periyot_sayisi, baslangic_tarihi, hedef_yil
    )

    asgari_karsilastirmasi = "ASGARI" in anahtar
    for uygulama_tarihi in uygulama_tarihleri:
        onceki_uygulama = uygulama_tarihi - pd.DateOffset(
            months=periyot_sayisi
        )
        donem_aylari = pd.date_range(
            start=onceki_uygulama,
            periods=periyot_sayisi,
            freq="MS"
        )
        ufe_oranlari = []
        tufe_oranlari = []
        veri_tamam = True
        for donem in donem_aylari:
            ufe, tufe = enflasyon_kaynak_haritasi.get(
                (int(donem.year), int(donem.month)), (None, None)
            )
            if ufe is None or tufe is None:
                veri_tamam = False
                break
            ufe_oranlari.append(ufe)
            tufe_oranlari.append(tufe)
        if not veri_tamam:
            continue

        ufe_bilesik = aylik_oranlari_bilesik_hesapla(ufe_oranlari)
        tufe_bilesik = aylik_oranlari_bilesik_hesapla(tufe_oranlari)
        if ufe_bilesik is None or tufe_bilesik is None:
            continue
        uygulanacak_oran = (ufe_bilesik + tufe_bilesik) / 2.0

        if asgari_karsilastirmasi:
            asgari_artisi = donemdeki_asgari_ucret_artisini_bul(
                asgari_kayitlari or [], onceki_uygulama, uygulama_tarihi
            )
            if asgari_artisi is not None:
                uygulanacak_oran = max(uygulanacak_oran, asgari_artisi)

        hedef_ay = aylar[int(uygulama_tarihi.month) - 1]
        sonuc[f"Enflasyon {hedef_ay} (%)"] = uygulanacak_oran
    return sonuc


def musteri_eskalasyon_oranlarini_getir(
    row, durum_gecersiz=False, anahtar_gecersiz=False
):
    """Aylık mazot ve enflasyon oranlarını müşteri ağırlıklarıyla birleştirir."""
    sonuc = {f"Eskalasyon {ay} (%)": 0.0 for ay in aylar}
    if durum_gecersiz or anahtar_gecersiz:
        return sonuc

    yakit_agirligi = nullable_sayi(row.get("Yakıt Değişim Yüzdesi (%)"))
    enflasyon_agirligi = nullable_sayi(row.get("Enf. Değişim Yüzdesi (%)"))
    yakit_agirligi = 0.0 if yakit_agirligi is None else yakit_agirligi / 100.0
    enflasyon_agirligi = (
        0.0 if enflasyon_agirligi is None else enflasyon_agirligi / 100.0
    )

    for ay in aylar:
        mazot_orani = nullable_sayi(row.get(f"Mazot {ay} (%)"))
        enflasyon_orani = nullable_sayi(row.get(f"Enflasyon {ay} (%)"))
        mazot_orani = 0.0 if mazot_orani is None else mazot_orani
        enflasyon_orani = 0.0 if enflasyon_orani is None else enflasyon_orani
        sonuc[f"Eskalasyon {ay} (%)"] = (
            mazot_orani * yakit_agirligi
            + enflasyon_orani * enflasyon_agirligi
        )
    return sonuc


def manuel_enflasyon_hucrelerini_kaydet(edited_rows, edited_master):
    """Değiştirilen enflasyon hücrelerini saklar ve hesap yenilemesini bildirir."""
    if not isinstance(edited_rows, dict) or edited_master is None:
        return False
    enflasyon_surucu_sutunlari = {
        "Enf. Değişim Yüzdesi (%)",
        "Enf. Değişim Periyodu (Ay)",
        "Esk. Enf. Başlangıç Tarihi"
    }
    hesap_yenilenecek = False
    for satir_no, degisiklikler in edited_rows.items():
        try:
            satir_index = int(satir_no)
        except (TypeError, ValueError):
            continue
        if satir_index < 0 or satir_index >= len(edited_master):
            continue
        if not isinstance(degisiklikler, dict):
            continue
        mkod = guvenli_metin_kodu(
            edited_master.iloc[satir_index]["Müşteri Kodu"]
        )
        manuel_oranlar = st.session_state.master_enflasyon_ayarlari.setdefault(
            mkod, {}
        )
        for col, deger in degisiklikler.items():
            if col in enflasyon_surucu_sutunlari:
                hesap_yenilenecek = True
            if col in master_data_enflasyon_sutunlari:
                hesap_yenilenecek = True
                try:
                    deger_bos = deger is None or bool(pd.isna(deger))
                except (TypeError, ValueError):
                    deger_bos = deger is None
                manuel_oranlar[col] = (
                    None if deger_bos else guvenli_sayi(deger)
                )
    return hesap_yenilenecek

def uniq_id_hazirla(df):
    if "Uniq ID" not in df.columns: return df
    mevcut_idler = [guvenli_tamsayi(x) for x in df["Uniq ID"] if guvenli_tamsayi(x) is not None]
    sonraki_id = max(mevcut_idler, default=0) + 1
    kullanilan_idler = set()
    sonuc_idler = []
    for val in df["Uniq ID"]:
        temiz_val = guvenli_tamsayi(val)
        if temiz_val is None or temiz_val in kullanilan_idler:
            while sonraki_id in kullanilan_idler: sonraki_id += 1
            temiz_val = sonraki_id
            sonraki_id += 1
        kullanilan_idler.add(temiz_val)
        sonuc_idler.append(temiz_val)
    df["Uniq ID"] = sonuc_idler
    return df

def supabase_verisini_hazirla(dataframe):
    df = dataframe.copy()
    df.columns = [str(c).strip() for c in df.columns]
    df = df.reindex(columns=tum_kolonlar).dropna(how="all").reset_index(drop=True)
    df = uniq_id_hazirla(df)
    for c in BIGINT_KOLONLAR: df[c] = df[c].apply(lambda v: guvenli_tamsayi(v, nullable=True))
    for c in NUMERIC_KOLONLAR: df[c] = df[c].apply(lambda v: float(guvenli_sayi(v)))
    return df, [{c: json_uyumlu_deger(v) for c, v in row.items()} for _, row in df.iterrows()]

def otomatik_baz_yakit_tablosu_olustur():
    """Yeni-Bütçe kimlikleri ile değ.anah. KDV/fiyatlarını müşteri kodunda birleştirir."""
    musteri_df = st.session_state.get("musteri_ekran_df", pd.DataFrame()).copy()
    if musteri_df.empty or "Müşteri Kodu" not in musteri_df.columns:
        return pd.DataFrame(columns=baz_yakit_sutunlari)

    kimlikler = sutun_adlarini_standartlastir(musteri_df)
    kimlikler["Müşteri Kodu"] = kimlikler["Müşteri Kodu"].apply(guvenli_metin_kodu)
    for col in ["Müşteri Adı", "Müşteri Temsilcisi", "Durum"]:
        if col not in kimlikler.columns:
            kimlikler[col] = ""
    kimlikler = (
        kimlikler[kimlikler["Müşteri Kodu"] != ""]
        .drop_duplicates(subset=["Müşteri Kodu"], keep="first")
        [["Müşteri Kodu", "Müşteri Adı", "Müşteri Temsilcisi", "Durum"]]
    )

    parametreler = sutun_adlarini_standartlastir(
        st.session_state.get("deg_anah_veri", pd.DataFrame())
    )
    if not parametreler.empty and "Müşteri Kodu" in parametreler.columns:
        parametreler["Müşteri Kodu"] = parametreler["Müşteri Kodu"].apply(guvenli_metin_kodu)
        for col in ["KDV Durumu", "Baz Yakıt Fiyatı"]:
            if col not in parametreler.columns:
                parametreler[col] = np.nan
        parametreler = (
            parametreler.drop_duplicates(subset=["Müşteri Kodu"], keep="first")
            [["Müşteri Kodu", "KDV Durumu", "Baz Yakıt Fiyatı"]]
        )
        sonuc = pd.merge(kimlikler, parametreler, on="Müşteri Kodu", how="left")
    else:
        sonuc = kimlikler.copy()
        sonuc["KDV Durumu"] = np.nan
        sonuc["Baz Yakıt Fiyatı"] = np.nan

    sonuc["KDV Durumu"] = sonuc["KDV Durumu"].apply(
        lambda v: "" if pd.isna(v) else str(v).strip()
    )

    def fiyat_ve_kdv_hazirla(row):
        ham = row.get("Baz Yakıt Fiyatı")
        ham_bos = ham is None or (isinstance(ham, str) and ham.strip() in {"", "-"})
        try:
            ham_bos = ham_bos or pd.isna(ham)
        except Exception:
            pass
        if ham_bos:
            return pd.Series([np.nan, np.nan])
        girilen = guvenli_sayi(ham)
        kdv = (
            str(row.get("KDV Durumu", ""))
            .strip()
            .upper()
            .replace("İ", "I")
            .replace("’", "'")
        )
        if kdv == "KDV'LI":
            net = girilen / 1.20
        elif kdv in {"KDV'SIZ", "MUAF"}:
            net = girilen
        else:
            # KDV durumu bilinmiyorsa hatalı bir net fiyat üretme.
            net = np.nan
        return pd.Series([girilen, net])

    sonuc[["Baz Yakıt Fiyatı (Girilen)", "Esk. Baz Yakıt Fiyatı (KDV Hariç)"]] = (
        sonuc.apply(fiyat_ve_kdv_hazirla, axis=1)
    )
    return sonuc.reindex(columns=baz_yakit_sutunlari)

def mazot_degisim_matrisi_olustur(mazot_verisi=None):
    """Baz motorin ve aylık fiyatlardan 1-6 aylık değişim matrisini üretir."""
    kaynak = (
        st.session_state.get("mazot_giriş_veri", pd.DataFrame())
        if mazot_verisi is None else mazot_verisi
    )
    if kaynak is None or kaynak.empty:
        return pd.DataFrame(columns=["Periyot"] + aylar)

    mz_base = kaynak.iloc[0]
    matris_rows = []
    for periyot in range(1, 7):
        row_data = {"Periyot": f"{periyot} ay"}
        for ay_index, ay in enumerate(aylar):
            guncel_fiyat = guvenli_sayi(mz_base.get(ay, 0.0))
            onceki_index = ay_index - periyot
            if onceki_index == -1:
                onceki_fiyat = guvenli_sayi(mz_base.get("Baz Motorin", 0.0))
            elif onceki_index < -1:
                onceki_fiyat = 0.0
            else:
                onceki_fiyat = guvenli_sayi(mz_base.get(aylar[onceki_index], 0.0))
            row_data[ay] = (
                (guncel_fiyat / onceki_fiyat) - 1
                if onceki_fiyat > 0 and guncel_fiyat > 0 else np.nan
            )
        matris_rows.append(row_data)
    return pd.DataFrame(matris_rows)

def yakit_baslangic_tarihini_hazirla(value):
    """Türkçe/ISO tarihleri gün-ay-yıl önceliğiyle güvenli okur."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return pd.Timestamp(value).normalize()
    metin = str(value).strip()
    if not metin:
        return None
    tarih = pd.to_datetime(metin, errors="coerce", dayfirst=True)
    return None if pd.isna(tarih) else pd.Timestamp(tarih).normalize()

def sabit_yakit_eskalasyon_aylari(periyot, baslangic_tarihi, hedef_yil=2026):
    """Başlangıç tarihine bağlı, erken artıştan etkilenmeyen sabit ayları verir."""
    periyot_sayisi = guvenli_tamsayi(periyot, nullable=True)
    baslangic = yakit_baslangic_tarihini_hazirla(baslangic_tarihi)
    if periyot_sayisi is None or periyot_sayisi <= 0 or baslangic is None:
        return set()

    yil_basi = pd.Timestamp(year=hedef_yil, month=1, day=1)
    yil_sonu = pd.Timestamp(year=hedef_yil, month=12, day=31)
    tarih = baslangic
    guvenlik = 0
    while tarih < yil_basi and guvenlik < 240:
        tarih = tarih + pd.DateOffset(months=periyot_sayisi)
        guvenlik += 1

    sabit_aylar = set()
    while tarih <= yil_sonu and guvenlik < 480:
        if tarih.year == hedef_yil:
            sabit_aylar.add(int(tarih.month))
        tarih = tarih + pd.DateOffset(months=periyot_sayisi)
        guvenlik += 1
    return sabit_aylar

def musteri_mazot_oranlarini_getir(
    periyot, anlik_degisim_esigi, baslangic_tarihi, hedef_yil=2026
):
    """Sabit takvim ve +/- eşik kuralıyla müşterinin aylık mazot oranlarını hesaplar."""
    sonuc = {f"Mazot {ay} (%)": np.nan for ay in aylar}
    sonuc["Mazot Ocak (%)"] = 0.0
    sabit_aylar = sabit_yakit_eskalasyon_aylari(
        periyot, baslangic_tarihi, hedef_yil
    )
    esik = abs(guvenli_sayi(anlik_degisim_esigi))
    fiyat_kaynagi = st.session_state.get("mazot_giriş_veri", pd.DataFrame())
    if fiyat_kaynagi is None or fiyat_kaynagi.empty:
        return sonuc

    fiyatlar = fiyat_kaynagi.iloc[0]
    ocak_fiyati = guvenli_sayi(fiyatlar.get("Ocak", 0.0))
    if ocak_fiyati <= 0:
        return sonuc

    # 2026 bütçe başlangıcı Ocak'tır. İlk referans fiyat Ocak fiyatıdır.
    son_uygulanan_fiyat = ocak_fiyati
    for ay_index, ay in enumerate(aylar[1:], start=2):
        guncel_fiyat = guvenli_sayi(fiyatlar.get(ay, 0.0))
        if guncel_fiyat <= 0 or son_uygulanan_fiyat <= 0:
            continue
        degisim_yuzdesi = (
            (guncel_fiyat / son_uygulanan_fiyat) - 1.0
        ) * 100.0
        sabit_uygulama = ay_index in sabit_aylar
        erken_uygulama = esik > 0 and abs(degisim_yuzdesi) >= esik
        if sabit_uygulama or erken_uygulama:
            sonuc[f"Mazot {ay} (%)"] = degisim_yuzdesi
            son_uygulanan_fiyat = guncel_fiyat
    return sonuc

def manuel_mazot_hucrelerini_kaydet(edited_rows, edited_master):
    """Değiştirilen Mazot hücrelerini saklar ve hesap yenilemesini bildirir."""
    if not isinstance(edited_rows, dict) or edited_master is None:
        return False
    mazot_surucu_sutunlari = {
        "Yakıt Değişim Yüzdesi (%)",
        "Yakıt Anlık Değişim Oranı (%)",
        "Yakıt Değişim Periyodu (Ay)",
        "Esk. Yakıt Başlangıç Tarihi"
    }
    hesap_yenilenecek = False
    for satir_no, degisiklikler in edited_rows.items():
        try:
            satir_index = int(satir_no)
        except (TypeError, ValueError):
            continue
        if satir_index < 0 or satir_index >= len(edited_master):
            continue
        if not isinstance(degisiklikler, dict):
            continue
        mkod = guvenli_metin_kodu(
            edited_master.iloc[satir_index]["Müşteri Kodu"]
        )
        manuel_mazotlar = st.session_state.master_mazot_ayarlari.setdefault(
            mkod, {}
        )
        for col, deger in degisiklikler.items():
            if col in mazot_surucu_sutunlari:
                hesap_yenilenecek = True
            if col in master_data_mazot_sutunlari:
                hesap_yenilenecek = True
                try:
                    deger_bos = deger is None or bool(pd.isna(deger))
                except (TypeError, ValueError):
                    deger_bos = deger is None
                manuel_mazotlar[col] = (
                    None if deger_bos else guvenli_sayi(deger)
                )
    return hesap_yenilenecek

def takvim_verisini_hazirla():
    """Çalışma günü tablosunu bütün sekmeler için tek kez hazırlar."""
    aktif_rev_id = aktif_revizyon_id_getir()
    yukleme_anahtari = aktif_rev_id or "__ORTAK__"
    if (
        "takvim_verisi_yillar" in st.session_state
        and st.session_state.get("takvim_yuklenen_revizyon") == yukleme_anahtari
    ):
        return

    takvim_df = pd.DataFrame()
    if client:
        if aktif_rev_id:
            try:
                tk_rev_res = (
                    client.table(TAKVIM_REVIZYON_DB_TABLOSU)
                    .select("*")
                    .eq("revizyon_id", aktif_rev_id)
                    .execute()
                )
                if tk_rev_res.data:
                    takvim_df = pd.DataFrame(tk_rev_res.data)
                    takvim_df = takvim_df.drop(
                        columns=["id", "revizyon_id", "created_at"],
                        errors="ignore"
                    )
            except Exception:
                takvim_df = pd.DataFrame()
        try:
            if takvim_df.empty:
                tk_res = client.table("takvim_tablosu").select("*").execute()
                if tk_res.data:
                    takvim_df = pd.DataFrame(tk_res.data)
                    takvim_df = takvim_df.drop(
                        columns=["id", "created_at"], errors="ignore"
                    )
        except Exception:
            takvim_df = pd.DataFrame()

    if takvim_df.empty:
        takvim_df = pd.DataFrame([
            {"YIL": "2024", "Ocak": 26, "Şubat": 25, "Mart": 26, "Nisan": 23, "Mayıs": 26, "Haziran": 22, "Temmuz": 27, "Ağustos": 27, "Eylül": 25, "Ekim": 27, "Kasım": 26, "Aralık": 26},
            {"YIL": "2025", "Ocak": 26, "Şubat": 24, "Mart": 25, "Nisan": 25, "Mayıs": 26, "Haziran": 22, "Temmuz": 26, "Ağustos": 26, "Eylül": 26, "Ekim": 26, "Kasım": 25, "Aralık": 27},
            {"YIL": "2026", "Ocak": 26, "Şubat": 24, "Mart": 23, "Nisan": 26, "Mayıs": 21, "Haziran": 26, "Temmuz": 26, "Ağustos": 26, "Eylül": 26, "Ekim": 26, "Kasım": 25, "Aralık": 27},
            {"YIL": "2027", "Ocak": 26, "Şubat": 24, "Mart": 23, "Nisan": 26, "Mayıs": 21, "Haziran": 26, "Temmuz": 26, "Ağustos": 26, "Eylül": 26, "Ekim": 26, "Kasım": 25, "Aralık": 27}
        ])

    for kolon in ["YIL"] + aylar:
        if kolon not in takvim_df.columns:
            takvim_df[kolon] = "" if kolon == "YIL" else 0.0
    takvim_df["YIL"] = takvim_df["YIL"].astype(str).str.strip()
    for ay in aylar:
        takvim_df[ay] = takvim_df[ay].apply(guvenli_sayi).astype(float)
    st.session_state.takvim_verisi_yillar = (
        takvim_df[["YIL"] + aylar].reset_index(drop=True)
    )
    st.session_state.takvim_yuklenen_revizyon = yukleme_anahtari

takvim_verisini_hazirla()

# ============================================================
# ARAYÜZ SEKMELERİ (YALNIZCA AÇIK SEKMEYİ HESAPLAYAN HIZLI YAPI)
# ============================================================
sekme_etiketleri = [
    "📅 Çalışma Günleri Takvimi", "☁️ Bulut Revizyon Yönetimi",
    "👤 Yeni-Bütçe Müşteri", "⚙️ değ.anah.-yakıt-kdv", "⛽ Baz Yakıt Fiyatları",
    "🧾 Eskalasyon & Master Data", "📊 2026 Mazot Analizi", "📈 Müşteri Büyüme Oranları",
    "🏁 Yıl Kapanış", "📉 ÜFE-TÜFE Yönetimi", "💳 Baz Birim Fiyatlar", "🆕 Data_New",
    "🔮 Desi Tahminleme"
]

# Başlıklar tema kontrolüyle aynı sol menüde yer alır. Yalnızca seçili sayfa
# çalıştırıldığı için ağır tablolar arasında geçiş de daha hızlıdır.
st.sidebar.markdown("---")
st.sidebar.caption("📚 SAYFALAR")
aktif_sekme_etiketi = st.sidebar.radio(
    "Sayfa",
    sekme_etiketleri,
    label_visibility="collapsed",
    key="ana_uygulama_sayfasi_v5"
)
sekmeler = [st.container() for _ in sekme_etiketleri]
sekme_acik_mi = [
    etiket == aktif_sekme_etiketi for etiket in sekme_etiketleri
]

# ------------------------------------------------------------
# 1. SEKME: ÇALIŞMA GÜNLERİ (KAYIT VE EXCEL DESTEKLİ DİNAMİK MATRİS 📅)
# ------------------------------------------------------------
if sekme_acik_mi[0]:
    with sekmeler[0]:
        st.title("📅 Operasyonel Çalışma Günleri Takvimi")
        st.markdown("Aşağıdaki matristen çalışma günlerini düzenleyebilirsiniz. Yapılan değişiklikleri **Buluta Kaydet** butonu ile kalıcı hale getirebilir veya **Excel** olarak indirebilirsiniz.")

        @st.fragment
        def takvim_modulunu_calistir():
            if "takvim_verisi_yillar" not in st.session_state:
                takvim_yuklendi_mi = False
                if client:
                    try:
                        tk_res = client.table("takvim_tablosu").select("*").execute()
                        if tk_res.data:
                            df_cloud_tk = pd.DataFrame(tk_res.data)
                            if "id" in df_cloud_tk.columns: 
                                df_cloud_tk = df_cloud_tk.drop(columns=["id"])
                            takvim_sirasi = ["YIL"] + aylar
                            st.session_state.takvim_verisi_yillar = df_cloud_tk[takvim_sirasi]
                            takvim_yuklendi_mi = True
                    except:
                        pass
            
                if not takvim_yuklendi_mi:
                    st.session_state.takvim_verisi_yillar = pd.DataFrame([
                        {"YIL": "2024", "Ocak": 26, "Şubat": 25, "Mart": 26, "Nisan": 23, "Mayıs": 26, "Haziran": 22, "Temmuz": 27, "Ağustos": 27, "Eylül": 25, "Ekim": 27, "Kasım": 26, "Aralık": 26},
                        {"YIL": "2025", "Ocak": 26, "Şubat": 24, "Mart": 25, "Nisan": 25, "Mayıs": 26, "Haziran": 22, "Temmuz": 26, "Ağustos": 26, "Eylül": 26, "Ekim": 26, "Kasım": 25, "Aralık": 27},
                        {"YIL": "2026", "Ocak": 26, "Şubat": 24, "Mart": 23, "Nisan": 26, "Mayıs": 21, "Haziran": 26, "Temmuz": 26, "Ağustos": 26, "Eylül": 26, "Ekim": 26, "Kasım": 25, "Aralık": 27},
                        {"YIL": "2027", "Ocak": 0, "Şubat": 0, "Mart": 0, "Nisan": 0, "Mayıs": 0, "Haziran": 0, "Temmuz": 0, "Ağustos": 0, "Eylül": 0, "Ekim": 0, "Kasım": 0, "Aralık": 0}
                    ])

            df_yillar = st.session_state.takvim_verisi_yillar.copy()
            for m in aylar:
                df_yillar[m] = pd.to_numeric(df_yillar[m].apply(guvenli_sayi), errors='coerce').fillna(0.0)
            
            df_yillar["Toplam"] = df_yillar[aylar].sum(axis=1)

            def yil_satiri_getir(yr_str):
                match = df_yillar[df_yillar["YIL"] == yr_str]
                return match.iloc[0] if not match.empty else None

            ratio_rows = []
            oran_kurgulari = [
                ("2026", "2027", "26to27"),
                ("2025", "2026", "25to26"),
                ("2024", "2025", "24to25")
            ]

            for prev_y, curr_y, label in oran_kurgulari:
                r_prev = yil_satiri_getir(prev_y)
                r_curr = yil_satiri_getir(curr_y)
            
                r_dict = {"YIL": label}
                for m in aylar:
                    v_prev = r_prev[m] if r_prev is not None else 0.0
                    v_curr = r_curr[m] if r_curr is not None else 0.0
                    r_dict[m] = (v_curr / v_prev) if v_prev > 0 else 0.0
                
                r_dict["Toplam"] = np.nan
                ratio_rows.append(r_dict)

            df_ratios = pd.DataFrame(ratio_rows)
            combined_calendar_df = pd.concat([df_yillar, df_ratios], ignore_index=True)

            edited_calendar = st.data_editor(
                combined_calendar_df,
                use_container_width=True,
                hide_index=True,
                disabled=["YIL", "Toplam"], 
                column_config={
                    "YIL": st.column_config.TextColumn("YIL"),
                    "Toplam": st.column_config.NumberColumn("Toplam", format="%d"),
                    **{m: st.column_config.NumberColumn(m, format="%.2f") for m in aylar}
                },
                key="dynamic_operational_calendar_editor"
            )

            satir_sayisi = len(st.session_state.takvim_verisi_yillar)
            just_real_years = edited_calendar.iloc[:satir_sayisi].copy()
        
            degisim_var = False
            for i in range(satir_sayisi):
                for m in aylar:
                    eski = float(guvenli_sayi(st.session_state.takvim_verisi_yillar.iloc[i][m]))
                    yeni = float(guvenli_sayi(just_real_years.iloc[i][m]))
                
                    if abs(eski - yeni) > 0.0001:
                        degisim_var = True
                        st.session_state.takvim_verisi_yillar = just_real_years
                        st.session_state.takvim_verisi_yillar.at[i, m] = yeni
                    
            if degisim_var:
                try: st.rerun(scope="fragment")
                except: st.rerun()

            st.markdown("<br>", unsafe_allow_html=True)
            c_tk1, c_tk2, c_tk3 = st.columns([2, 2, 1])
        
            with c_tk1:
                output_tk_excel = io.BytesIO()
                with pd.ExcelWriter(output_tk_excel, engine="openpyxl") as writer:
                    combined_calendar_df.to_excel(writer, index=False, sheet_name="Çalışma Günleri")
                st.download_button(
                    label="📥 Tüm Tabloyu Excel Olarak İndir",
                    data=output_tk_excel.getvalue(),
                    file_name="operasyonel_calisma_gunleri_matrisi.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key="btn_tk_excel_download"
                )
            
            with c_tk2:
                aktif_takvim_rev_id = sayfa_aktif_revizyonunu_getir(c_tk2)
                if client:
                    if st.button(
                        "💾 Takvimi Aktif Revizyona Kaydet",
                        type="primary",
                        use_container_width=True,
                        key="btn_tk_cloud_save",
                        disabled=not aktif_takvim_rev_id
                    ):
                        clean_save_df = st.session_state.takvim_verisi_yillar.copy()
                        tk_records = [
                            {
                                **{
                                    c: json_uyumlu_deger(v)
                                    for c, v in row.items()
                                },
                                "revizyon_id": aktif_takvim_rev_id
                            }
                            for _, row in clean_save_df.iterrows()
                        ]
                    
                        with st.spinner("Takvim bulut ambarına mühürleniyor..."):
                            try:
                                client.table(TAKVIM_REVIZYON_DB_TABLOSU).delete().eq(
                                    "revizyon_id", aktif_takvim_rev_id
                                ).execute()
                                client.table(TAKVIM_REVIZYON_DB_TABLOSU).insert(
                                    tk_records
                                ).execute()
                                revizyonu_degistirildi_isaretle(
                                    aktif_takvim_rev_id
                                )
                                st.success(
                                    "🎉 Çalışma günleri aktif revizyona kaydedildi."
                                )
                            except Exception as e:
                                st.error(f"Kayıt esnasında bulut hatası oluştu: {e}")
                else:
                    st.info("Bulut bağlantısı aktif olmadığı için kalıcı kayıt devre dışı, verileriniz tarayıcı açık kaldığı sürece korunacaktır.")

            with c_tk3:
                if st.button(
                    "↩️ Ortak Varsayılana Dön",
                    use_container_width=True,
                    key="btn_tk_override_sil",
                    disabled=(not client or not aktif_takvim_rev_id)
                ):
                    try:
                        client.table(TAKVIM_REVIZYON_DB_TABLOSU).delete().eq(
                            "revizyon_id", aktif_takvim_rev_id
                        ).execute()
                        st.session_state.pop("takvim_verisi_yillar", None)
                        st.session_state.pop("takvim_yuklenen_revizyon", None)
                        revizyonu_degistirildi_isaretle(aktif_takvim_rev_id)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Ortak takvime dönülemedi: {e}")

        takvim_modulunu_calistir()

# ------------------------------------------------------------
# 2. SEKME: BULUT REVİZYON YÖNETİMİ
# ------------------------------------------------------------
if sekme_acik_mi[1]:
    with sekmeler[1]:
        st.title("☁️ Bulut Revizyon Geçmişi")
        st.caption(
            "Revizyonu burada oluşturun ve aktif edin. Diğer bütün bütçe "
            "sayfalarının bulut kayıtları seçili aktif revizyona yazılır."
        )

        def revizyon_tarihini_goster(record, degisiklik=False):
            alanlar = (
                ["degistirilme_tarihi", "olusturulma_tarihi", "kayit_zamani", "created_at"]
                if degisiklik else
                ["olusturulma_tarihi", "kayit_zamani", "created_at"]
            )
            ham = next((record.get(a) for a in alanlar if record.get(a)), None)
            if not ham:
                return ""
            tarih = pd.to_datetime(ham, errors="coerce", utc=True)
            if pd.isna(tarih):
                return str(ham)
            try:
                tarih = tarih.tz_convert("Europe/Istanbul")
            except (TypeError, ValueError):
                pass
            return tarih.strftime("%d.%m.%Y %H:%M")

        def revizyon_tablosunu_kopyala(tablo_adi, kaynak_id, hedef_id):
            kayitlar = supabase_revizyon_kayitlarini_getir(
                tablo_adi, kaynak_id
            )
            if not kayitlar:
                return 0
            yeni_kayitlar = []
            for kayit in kayitlar:
                yeni = {
                    key: value for key, value in kayit.items()
                    if key not in {"id", "created_at", "updated_at"}
                }
                yeni["revizyon_id"] = hedef_id
                yeni_kayitlar.append(yeni)
            for baslangic in range(0, len(yeni_kayitlar), 500):
                client.table(tablo_adi).insert(
                    yeni_kayitlar[baslangic:baslangic + 500]
                ).execute()
            return len(yeni_kayitlar)

        with st.expander("➕ Yeni Revizyon Oluştur", expanded=not revizyon_kayitlari):
            yeni_rev_adi = st.text_input(
                "Revizyon Adı",
                placeholder="2026.08.14_tarihli_butce_V1",
                key="yeni_revizyon_adi"
            )
            yeni_rev_notu = st.text_input(
                "Açıklama",
                placeholder="2026 bütçe ilk çalışma",
                key="yeni_revizyon_aciklama"
            )
            olusturma_tipi = st.radio(
                "Başlangıç",
                ["Boş Revizyon Oluştur", "Mevcut Revizyondan Kopyala"],
                horizontal=True,
                key="yeni_revizyon_tipi"
            )
            kopya_kaynak_id = None
            if olusturma_tipi == "Mevcut Revizyondan Kopyala":
                if rev_secenekleri:
                    kopya_etiket = st.selectbox(
                        "Kopyalanacak Revizyon",
                        list(rev_secenekleri.keys()),
                        key="yeni_revizyon_kopya_kaynak"
                    )
                    kopya_kaynak_id = rev_secenekleri[kopya_etiket]
                else:
                    st.warning("Kopyalanabilecek mevcut revizyon bulunmuyor.")

            if st.button(
                "☁️ Revizyonu Oluştur ve Aktif Et",
                type="primary",
                use_container_width=True,
                disabled=not client,
                key="btn_yeni_revizyon_olustur"
            ):
                temiz_ad = re.sub(r"\s+", " ", yeni_rev_adi).strip()
                mevcut_adlar = {
                    str(r.get("revizyon_adi") or "").strip().casefold()
                    for r in revizyon_kayitlari
                }
                if not temiz_ad:
                    st.error("Revizyon adı boş olamaz.")
                elif temiz_ad.casefold() in mevcut_adlar:
                    st.error("Bu revizyon adı daha önce kullanılmış.")
                elif (
                    olusturma_tipi == "Mevcut Revizyondan Kopyala"
                    and not kopya_kaynak_id
                ):
                    st.error("Kopyalanacak revizyonu seçin.")
                else:
                    yeni_rev_id = (
                        "REV-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f")
                    )
                    try:
                        simdi = datetime.now().astimezone().isoformat()
                        client.table("revizyon_log").insert({
                            "revizyon_id": yeni_rev_id,
                            "revizyon_adi": temiz_ad,
                            "olusturan_kisi": AKTIF_KULLANICI,
                            "olusturulma_tarihi": simdi,
                            "son_degistiren": AKTIF_KULLANICI,
                            "degistirilme_tarihi": simdi,
                            "revizyon_notu": yeni_rev_notu.strip()
                        }).execute()

                        if kopya_kaynak_id:
                            kopyalanacak_tablolar = [
                                "butce_tablosu", "data_tablosu",
                                "musteri_detay_tablosu", "deg_anah_tablosu",
                                "baz_yakit_tablosu", "master_data_tablosu",
                                "mazot_tablosu", "buyume_tablosu",
                                "baz_birim_fiyat_tablosu", "data_new_tablosu",
                                "kg_musteri_tablosu", "yil_kapanis_tablosu",
                                "yil_kapanis_detay_tablosu",
                                "takvim_revizyon_tablosu",
                                "enflasyon_revizyon_tablosu"
                            ]
                            for tablo in kopyalanacak_tablolar:
                                try:
                                    revizyon_tablosunu_kopyala(
                                        tablo, kopya_kaynak_id, yeni_rev_id
                                    )
                                except Exception:
                                    # Henüz oluşturulmamış opsiyonel tablo,
                                    # diğer revizyon verilerinin kopyalanmasını durdurmaz.
                                    continue

                        revizyon_oturumunu_temizle()
                        st.session_state.aktif_revizyon_id = yeni_rev_id
                        st.session_state.aktif_revizyon_adi = temiz_ad
                        revizyon_loglarini_getir.clear()
                        st.success(f"Revizyon oluşturuldu: {temiz_ad}")
                        st.rerun()
                    except Exception as hata:
                        st.error(
                            "Revizyon oluşturulamadı. Önce yeni Supabase "
                            f"revizyon SQL'ini çalıştırın. Ayrıntı: {hata}"
                        )

        if revizyon_kayitlari:
            tarihce_satirlari = []
            aktif_id = aktif_revizyon_id_getir()
            for kayit in revizyon_kayitlari:
                rev_id = str(kayit.get("revizyon_id"))
                tarihce_satirlari.append({
                    "Aktif": "✅" if rev_id == aktif_id else "",
                    "Revizyon Adı": kayit.get("revizyon_adi")
                    or kayit.get("revizyon_notu") or rev_id,
                    "Açan Kişi": kayit.get("olusturan_kisi") or "",
                    "Oluşturulma Tarihi": revizyon_tarihini_goster(kayit),
                    "Son Değiştiren": kayit.get("son_degistiren")
                    or kayit.get("olusturan_kisi") or "",
                    "Son Değiştirilme Tarihi": revizyon_tarihini_goster(
                        kayit, degisiklik=True
                    ),
                    "Açıklama": kayit.get("revizyon_notu") or "",
                    "Teknik ID": rev_id
                })
            st.dataframe(
                pd.DataFrame(tarihce_satirlari),
                use_container_width=True,
                hide_index=True,
                height=min(500, 38 * len(tarihce_satirlari) + 42)
            )

            secim_etiketi = st.selectbox(
                "İşlem Yapılacak Revizyon",
                list(rev_secenekleri.keys()),
                index=(
                    list(rev_secenekleri.values()).index(aktif_id)
                    if aktif_id in rev_secenekleri.values() else 0
                ),
                key="revizyon_yonetim_secimi"
            )
            secili_rev = rev_secenekleri[secim_etiketi]
            r1, r2 = st.columns(2)
            if r1.button(
                "✅ Seçili Revizyonu Aktif Et",
                type="primary",
                use_container_width=True,
                key="btn_revizyon_aktif_et"
            ):
                kayit = revizyon_id_haritasi.get(secili_rev, {})
                revizyon_oturumunu_temizle()
                st.session_state.aktif_revizyon_id = secili_rev
                st.session_state.aktif_revizyon_adi = str(
                    kayit.get("revizyon_adi")
                    or kayit.get("revizyon_notu") or secili_rev
                )
                st.success("Aktif revizyon değiştirildi.")
                st.rerun()

            silme_onayi = r2.checkbox(
                "Silme işlemini onaylıyorum",
                key="revizyon_silme_onayi"
            )
            if r2.button(
                "🗑️ Seçili Revizyonu Kalıcı Sil",
                use_container_width=True,
                disabled=not silme_onayi,
                key="delete_selected_rev_btn"
            ):
                silinecek_tablolar = [
                    "butce_tablosu", "data_tablosu",
                    "deg_anah_tablosu", "baz_yakit_tablosu",
                    "musteri_detay_tablosu", "master_data_tablosu",
                    "mazot_tablosu", "buyume_tablosu",
                    "baz_birim_fiyat_tablosu", "data_new_tablosu",
                    "kg_musteri_tablosu", "yil_kapanis_tablosu",
                    "yil_kapanis_detay_tablosu",
                    "takvim_revizyon_tablosu",
                    "enflasyon_revizyon_tablosu"
                ]
                for tablo in silinecek_tablolar:
                    try:
                        client.table(tablo).delete().eq(
                            "revizyon_id", secili_rev
                        ).execute()
                    except Exception:
                        continue
                client.table("revizyon_log").delete().eq(
                    "revizyon_id", secili_rev
                ).execute()
                if st.session_state.aktif_revizyon_id == secili_rev:
                    revizyon_oturumunu_temizle()
                    st.session_state.aktif_revizyon_id = None
                    st.session_state.aktif_revizyon_adi = ""
                revizyon_loglarini_getir.clear()
                st.success("Revizyon ve bağlı kayıtları silindi.")
                st.rerun()
        else:
            st.info("Bulut tabanlı bir kayıt bulunmuyor.")

# ------------------------------------------------------------
# 3. SEKME: YENİ-BÜTÇE MÜŞTERİ
# ------------------------------------------------------------
if sekme_acik_mi[2]:
    with sekmeler[2]:
        st.title("👤 Yeni-Bütçe Müşteri Detay Yönetimi")

        MUSTERI_GERCEKLESEN_AYLAR = aylar[:10]
        MUSTERI_AYLIK_KG_KOLONLARI = [f"{ay} Kg" for ay in MUSTERI_GERCEKLESEN_AYLAR]
        MUSTERI_TOPLAM_KOLONU = "Gerçekleşen Aylar Toplam Desi"
        MUSTERI_DETAY_KOLONLARI = [
            "Müşteri Kodu", "Sap Kodu", "Müşteri Adı", "Müşteri Temsilcisi",
            "Durum", "Kayıt Tarihi", "Müşteri Grubu"
        ] + MUSTERI_AYLIK_KG_KOLONLARI + [
            MUSTERI_TOPLAM_KOLONU,
            "Yeni/Bütçelenen Müşteri", "Durum_2", "Durum_3", "Serbest Not",
            "Değişim kontrol"
        ]
        MUSTERI_DUZENLENEBILIR_KOLONLAR = [
            "Yeni/Bütçelenen Müşteri", "Durum_2", "Durum_3", "Serbest Not"
        ]

        def musteri_gerceklesen_aylarini_hazirla(hedef_df):
            """Ocak-Ekim Kg değerlerini temizler ve dinamik dönem toplamını hesaplar."""
            sonuc = sutun_adlarini_standartlastir(hedef_df)
            if "Müşteri Kodu" not in sonuc.columns:
                sonuc["Müşteri Kodu"] = ""
            sonuc["Müşteri Kodu"] = sonuc["Müşteri Kodu"].apply(guvenli_metin_kodu)
            for ay in MUSTERI_GERCEKLESEN_AYLAR:
                hedef = f"{ay} Kg"
                if hedef not in sonuc.columns:
                    aday = next((
                        c for c in [f"2025 {ay} Kg", f"{ay} Desi", f"2025 {ay} Desi"]
                        if c in sonuc.columns
                    ), None)
                    sonuc[hedef] = sonuc[aday] if aday else 0.0
                sonuc[hedef] = desi_kg_serisini_yuvarla(sonuc[hedef])

            sonuc[MUSTERI_TOPLAM_KOLONU] = sonuc[MUSTERI_AYLIK_KG_KOLONLARI].sum(axis=1)

            # Eski bulut kayıtlarında aylık detay yoksa eski toplamı kaybetme.
            eski_toplam_kolonlari = ["10 Ay Toplam Desi", "9 Ay Toplam Desi"]
            aylik_toplam_sifir = np.isclose(sonuc[MUSTERI_TOPLAM_KOLONU], 0.0)
            for eski_kolon in eski_toplam_kolonlari:
                if eski_kolon in sonuc.columns:
                    eski_deger = desi_kg_serisini_yuvarla(
                        sonuc[eski_kolon]
                    )
                    sonuc.loc[aylik_toplam_sifir & (eski_deger != 0.0), MUSTERI_TOPLAM_KOLONU] = eski_deger
            return sonuc

        def musteri_detay_gorunumunu_hazirla(df):
            """Tabloyu yalnızca istenen 13 kolona ve sabit sıraya getirir."""
            sonuc = sutun_adlarini_standartlastir(df)
            if "Sap Kodu" not in sonuc.columns and "Sap No" in sonuc.columns:
                sonuc = sonuc.rename(columns={"Sap No": "Sap Kodu"})
            sonuc = musteri_gerceklesen_aylarini_hazirla(sonuc)

            varsayilanlar = {
                "Müşteri Kodu": "", "Sap Kodu": "", "Müşteri Adı": "",
                "Müşteri Temsilcisi": "", "Durum": "GEÇERLİ", "Kayıt Tarihi": "",
                "Müşteri Grubu": "DİĞER", MUSTERI_TOPLAM_KOLONU: 0.0,
                "Yeni/Bütçelenen Müşteri": "03.Bütçelenen", "Durum_2": None,
                "Durum_3": "", "Serbest Not": ""
            }
            for col, varsayilan in varsayilanlar.items():
                if col not in sonuc.columns:
                    sonuc[col] = varsayilan

            sonuc["Müşteri Kodu"] = sonuc["Müşteri Kodu"].apply(guvenli_metin_kodu)
            sonuc = sonuc[sonuc["Müşteri Kodu"] != ""].copy()

            # Aynı müşteri kodu dosyada birden fazla kez geçse bile ekranda tek satır göster.
            sonuc = sonuc.drop_duplicates(subset=["Müşteri Kodu"], keep="first").reset_index(drop=True)
            sonuc["Değişim kontrol"] = sonuc.apply(
                lambda row: "DOĞRU"
                if str(row.get("Durum", "")).strip().upper()
                == str(row.get("Durum_2", "")).strip().upper()
                else "YANLIŞ",
                axis=1
            )
            return sonuc.reindex(columns=MUSTERI_DETAY_KOLONLARI)

        yuklenen_musteri = st.file_uploader("Müşteri Listenizi Yükleyin", type=["xlsx", "xls", "csv"], key="m_sablon_up")

        if yuklenen_musteri:
            df_hedef = pd.read_csv(yuklenen_musteri) if yuklenen_musteri.name.lower().endswith(".csv") else pd.read_excel(yuklenen_musteri)
            df_hedef = sutun_adlarini_standartlastir(df_hedef)
            if "Sap Kodu" not in df_hedef.columns and "Sap No" in df_hedef.columns:
                df_hedef = df_hedef.rename(columns={"Sap No": "Sap Kodu"})
            if "Müşteri Kodu" in df_hedef.columns:
                df_hedef["Müşteri Kodu"] = df_hedef["Müşteri Kodu"].apply(guvenli_metin_kodu)

                for idx, row in df_hedef.iterrows():
                    m_kod = str(row["Müşteri Kodu"])
                    if m_kod not in st.session_state.musteri_ayarlari:
                        v_durum = row.get("Durum", "GEÇERLİ")
                        st.session_state.musteri_ayarlari[m_kod] = {
                            "Yeni/Bütçelenen Müşteri": "03.Bütçelenen",
                            "Durum_2": v_durum if v_durum in ["GEÇERLİ", "GEÇERSİZ"] else None,
                            "Durum_3": "2026 yılında çalışmaya devam edecektir" if v_durum == "GEÇERLİ" else "",
                            "Serbest Not": ""
                        }
                df_hedef["Yeni/Bütçelenen Müşteri"] = df_hedef["Müşteri Kodu"].apply(lambda k: st.session_state.musteri_ayarlari.get(str(k), {}).get("Yeni/Bütçelenen Müşteri", "03.Bütçelenen"))
                df_hedef["Durum_2"] = df_hedef["Müşteri Kodu"].apply(lambda k: st.session_state.musteri_ayarlari.get(str(k), {}).get("Durum_2", None))
                df_hedef["Durum_3"] = df_hedef["Müşteri Kodu"].apply(lambda k: st.session_state.musteri_ayarlari.get(str(k), {}).get("Durum_3", ""))
                df_hedef["Serbest Not"] = df_hedef["Müşteri Kodu"].apply(lambda k: st.session_state.musteri_ayarlari.get(str(k), {}).get("Serbest Not", ""))
                st.session_state.musteri_ekran_df = musteri_detay_gorunumunu_hazirla(df_hedef)
                # Diğer kaynak daha önce yüklendiyse Baz Yakıt tablosunu beklemeden yenile.
                st.session_state.baz_yakit_veri = otomatik_baz_yakit_tablosu_olustur()

        if not st.session_state.musteri_ekran_df.empty:
            df_gosterim = musteri_detay_gorunumunu_hazirla(
                st.session_state.musteri_ekran_df
            )
            kilitli = [
                col for col in MUSTERI_DETAY_KOLONLARI
                if col not in MUSTERI_DUZENLENEBILIR_KOLONLAR
            ]
            edited_m = st.data_editor(
                df_gosterim,
                use_container_width=True,
                height=400,
                disabled=kilitli,
                column_config={
                    **{
                        col: st.column_config.NumberColumn(col, format="%.0f")
                        for col in MUSTERI_AYLIK_KG_KOLONLARI
                    },
                    MUSTERI_TOPLAM_KOLONU: st.column_config.NumberColumn(
                        MUSTERI_TOPLAM_KOLONU, format="%.0f"
                    ),
                    "Yeni/Bütçelenen Müşteri": st.column_config.SelectboxColumn(
                        "Yeni/Bütçelenen Müşteri",
                        options=["01.Yeni Müşteri", "02.DOP Bütçe Dışı", "03.Bütçelenen"]
                    ),
                    "Durum_2": st.column_config.SelectboxColumn(
                        "Durum_2", options=["GEÇERLİ", "GEÇERSİZ", None]
                    )
                },
                key="ed_m_t4_exact_v3"
            )
            st.session_state.musteri_ekran_df = (
                edited_m.reindex(columns=MUSTERI_DETAY_KOLONLARI).copy()
            )

        st.markdown("---")
        c_m1, c_m2, c_m3 = st.columns(3)
        if not st.session_state.musteri_ekran_df.empty and c_m1.button("💾 Değişiklikleri Hafızaya İşle", type="primary", use_container_width=True, key="btn_m_hfz"):
            for idx, row in st.session_state.musteri_ekran_df.iterrows():
                m_kod = str(row["Müşteri Kodu"])
                st.session_state.musteri_ayarlari[m_kod] = {
                    "Yeni/Bütçelenen Müşteri": row["Yeni/Bütçelenen Müşteri"],
                    "Durum_2": row["Durum_2"] if not pd.isna(row["Durum_2"]) else None,
                    "Durum_3": row["Durum_3"], "Serbest Not": row["Serbest Not"]
                }
            st.success("Hafızaya kilitlendi!")
            st.rerun()

        if rev_secenekleri:
            r_id_m = sayfa_aktif_revizyonunu_getir(c_m2)
            if not st.session_state.musteri_ekran_df.empty and c_m2.button("💾 Müşteri Kartlarını Buluta Kaydet", use_container_width=True, key="btn_m_cloud_sv"):
                izin_verilen_db_sutunlari = (
                    ["Müşteri Kodu", "Sap Kodu", "Müşteri Adı", "Müşteri Temsilcisi", "Durum", "Kayıt Tarihi", "Müşteri Grubu"]
                    + MUSTERI_AYLIK_KG_KOLONLARI
                    + [MUSTERI_TOPLAM_KOLONU, "Yeni/Bütçelenen Müşteri", "Durum_2", "Durum_3", "Serbest Not", "Değişim kontrol"]
                )
                m_records = [{col: json_uyumlu_deger(row[col]) for col in izin_verilen_db_sutunlari if col in row} for _, row in st.session_state.musteri_ekran_df.iterrows()]
                for r in m_records: r["revizyon_id"] = r_id_m
                client.table("musteri_detay_tablosu").delete().eq("revizyon_id", r_id_m).execute()
                for i in range(0, len(m_records), 500): client.table("musteri_detay_tablosu").insert(m_records[i:i+500]).execute()
                revizyonu_degistirildi_isaretle(r_id_m)
                st.success("Buluta kilitlendi!")

            if c_m3.button("🔄 Dosya Yüklemeden Buluttan Müşteri Kartlarını Çek", use_container_width=True, key="btn_m_cloud_ld"):
                m_res = client.table("musteri_detay_tablosu").select("*").eq("revizyon_id", r_id_m).execute()
                if m_res.data:
                    gelen_df = sutun_adlarini_standartlastir(pd.DataFrame(m_res.data))
                    gelen_df = gelen_df.drop(
                        columns=[c for c in ["id", "revizyon_id"] if c in gelen_df.columns]
                    )
                    gelen_df = musteri_detay_gorunumunu_hazirla(gelen_df)
                    st.session_state.musteri_ekran_df = gelen_df.copy()
                    for _, row in gelen_df.iterrows():
                        k = str(row["Müşteri Kodu"])
                        st.session_state.musteri_ayarlari[k] = {"Yeni/Bütçelenen Müşteri": row.get("Yeni/Bütçelenen Müşteri"), "Durum_2": row.get("Durum_2"), "Durum_3": row.get("Durum_3"), "Serbest Not": row.get("Serbest Not")}
                    st.session_state.baz_yakit_veri = otomatik_baz_yakit_tablosu_olustur()
                    st.success("Buluttan çekildi!")
                    st.rerun()

# ------------------------------------------------------------
# 4. SEKME: değ.anah.-yakıt-kdv PARAMETRE YÖNETİMİ
# ------------------------------------------------------------
if sekme_acik_mi[3]:
    with sekmeler[3]:
        st.title("⚙️ değ.anah.-yakıt-kdv Parametre Yönetimi")
        parametre_mesaji = st.session_state.pop(
            "parametre_bulut_mesaji", None
        )
        if parametre_mesaji:
            st.success(parametre_mesaji)
        yuklenen_param = st.file_uploader("Parametre Şablonunu Yükle", type=["xlsx", "xls", "csv"], key="param_up")
        if yuklenen_param:
            yeni_parametre_imzasi = yuklenen_dosya_imzasi(yuklenen_param)
            if yeni_parametre_imzasi != st.session_state.parametre_upload_imzasi:
                df_p = pd.read_csv(yuklenen_param) if yuklenen_param.name.lower().endswith(".csv") else pd.read_excel(yuklenen_param)
                df_p = sutun_adlarini_standartlastir(df_p)
                if "Müşteri Kodu" in df_p.columns: df_p["Müşteri Kodu"] = df_p["Müşteri Kodu"].apply(guvenli_metin_kodu)
                st.session_state.deg_anah_veri = df_p.reindex(columns=deg_anah_sutunlari).copy()
                st.session_state.parametre_upload_imzasi = yeni_parametre_imzasi
                st.session_state.parametre_editor_nonce += 1
                st.success(
                    f"{len(st.session_state.deg_anah_veri):,} parametre "
                    "satırı dosyadan yüklendi."
                )

        if not st.session_state.deg_anah_veri.empty:
            st.session_state.deg_anah_veri["Baz Yakıt Fiyatı"] = st.session_state.deg_anah_veri["Baz Yakıt Fiyatı"].apply(guvenli_sayi)

        st.caption(
            f"Ekrandaki parametre kaydı: "
            f"{len(st.session_state.deg_anah_veri):,} satır"
        )

        edited_p = st.data_editor(st.session_state.deg_anah_veri, use_container_width=True, num_rows="dynamic", height=350,
                                  column_config={
                                      "Müşteri Kodu": st.column_config.TextColumn("Müşteri Kodu", required=True),
                                      "KDV Durumu": st.column_config.SelectboxColumn("KDV Durumu", options=["KDV'li", "KDV'siz", "Muaf"]),
                                      "Baz Yakıt Fiyatı": st.column_config.NumberColumn("Baz Yakıt Fiyatı", format="₺%.2f")
                                  }, key=f"ed_p_t5_{st.session_state.parametre_editor_nonce}")
        st.session_state.deg_anah_veri = edited_p.copy()
        # Müşteri kaynağı hazırsa Baz Yakıt tablosunu parametre değişikliğinde yenile.
        st.session_state.baz_yakit_veri = otomatik_baz_yakit_tablosu_olustur()

        if rev_secenekleri:
            st.markdown("---")
            cp1, cp2, cp3 = st.columns(3)
            r_id_p = sayfa_aktif_revizyonunu_getir(cp1)
            if cp2.button("💾 Parametreleri Seçili Versiyona Kaydet", type="primary", use_container_width=True, key="btn_p_sv"):
                try:
                    p_recs = [{str(col): json_uyumlu_deger(val) for col, val in row.items()} for _, row in edited_p.iterrows()]
                    for r in p_recs: r["revizyon_id"] = r_id_p
                    client.table("deg_anah_tablosu").delete().eq("revizyon_id", r_id_p).execute()
                    with st.spinner(
                        f"{len(p_recs):,} parametre kaydı buluta aktarılıyor..."
                    ):
                        for i in range(0, len(p_recs), 500):
                            client.table("deg_anah_tablosu").insert(
                                p_recs[i:i + 500]
                            ).execute()
                    revizyonu_degistirildi_isaretle(r_id_p)
                    st.success(
                        f"{len(p_recs):,} parametre kaydı buluta kaydedildi."
                    )
                except Exception as ex:
                    st.error(f"Parametreler buluta kaydedilemedi: {ex}")
            if cp3.button("🔄 Seçili Versiyonun Parametrelerini Çek", type="secondary", use_container_width=True, key="btn_p_ld"):
                with st.spinner("Parametrelerin tamamı buluttan getiriliyor..."):
                    p_kayitlari = supabase_revizyon_kayitlarini_getir(
                        "deg_anah_tablosu", r_id_p
                    )
                if p_kayitlari:
                    gelen_parametre = sutun_adlarini_standartlastir(
                        pd.DataFrame(p_kayitlari)
                    )
                    st.session_state.deg_anah_veri = gelen_parametre[
                        [c for c in deg_anah_sutunlari if c in gelen_parametre.columns]
                    ].reindex(columns=deg_anah_sutunlari)
                    st.session_state.parametre_upload_imzasi = None
                    st.session_state.parametre_editor_nonce += 1
                    st.session_state.baz_yakit_veri = otomatik_baz_yakit_tablosu_olustur()
                    st.session_state.parametre_bulut_mesaji = (
                        f"{len(st.session_state.deg_anah_veri):,} parametre "
                        "kaydı buluttan getirildi."
                    )
                    st.rerun()
                else:
                    st.warning("Aktif revizyonda parametre kaydı bulunamadı.")

# ------------------------------------------------------------
# 5. SEKME: BAZ YAKIT FİYATLARI
# ------------------------------------------------------------
if sekme_acik_mi[4]:
    with sekmeler[4]:
        st.title("⛽ Baz Yakıt Fiyatları KDV Dağılım Yönetimi")
        st.caption(
            "Müşteri bilgileri Yeni-Bütçe Müşteri sayfasından; KDV Durumu ve "
            "Baz Yakıt Fiyatı değ.anah.-yakıt-kdv sayfasından otomatik alınır."
        )

        kaynak_musteri_sayisi = len(
            st.session_state.get("musteri_ekran_df", pd.DataFrame())
        )
        kaynak_parametre_sayisi = len(
            st.session_state.get("deg_anah_veri", pd.DataFrame())
        )
        kb1, kb2 = st.columns(2)
        kb1.metric("Yeni-Bütçe müşteri kaynağı", f"{kaynak_musteri_sayisi:,} satır")
        kb2.metric("Yakıt/KDV parametre kaynağı", f"{kaynak_parametre_sayisi:,} satır")

        # Oturum yenilenmişse iki kaynağı aynı revizyondan tekrar kurabilmek için
        # Baz Yakıt sayfasında doğrudan kurtarma seçeneği sunulur.
        if (kaynak_musteri_sayisi == 0 or kaynak_parametre_sayisi == 0) and rev_secenekleri:
            st.warning(
                "Baz Yakıt tablosunun kaynaklarından en az biri bu oturumda bulunmuyor. "
                "Dosyaları yeniden yükleyebilir veya ikisini aynı bulut versiyonundan getirebilirsiniz."
            )
            kr1, kr2 = st.columns([2, 1])
            kaynak_rev_id = sayfa_aktif_revizyonunu_getir(kr1)
            if kr2.button(
                "🔄 Kaynakları Getir ve Oluştur",
                use_container_width=True,
                key="btn_baz_kaynak_getir"
            ):
                try:
                    musteri_kayitlari = supabase_revizyon_kayitlarini_getir(
                        "musteri_detay_tablosu", kaynak_rev_id
                    )
                    parametre_kayitlari = supabase_revizyon_kayitlarini_getir(
                        "deg_anah_tablosu", kaynak_rev_id
                    )

                    if musteri_kayitlari:
                        gelen_musteriler = sutun_adlarini_standartlastir(
                            pd.DataFrame(musteri_kayitlari)
                        ).drop(columns=["id", "revizyon_id"], errors="ignore")
                        st.session_state.musteri_ekran_df = gelen_musteriler
                    if parametre_kayitlari:
                        gelen_parametreler = sutun_adlarini_standartlastir(
                            pd.DataFrame(parametre_kayitlari)
                        ).drop(columns=["id", "revizyon_id"], errors="ignore")
                        st.session_state.deg_anah_veri = gelen_parametreler.reindex(
                            columns=deg_anah_sutunlari
                        )
                        st.session_state.parametre_upload_imzasi = None
                        st.session_state.parametre_editor_nonce += 1

                    st.session_state.baz_yakit_veri = otomatik_baz_yakit_tablosu_olustur()
                    if st.session_state.baz_yakit_veri.empty:
                        st.error(
                            "Seçilen versiyonda iki kaynak birlikte bulunamadı. "
                            "Müşteri ve parametre tablolarını aynı versiyona kaydedin."
                        )
                    else:
                        st.success("Kaynaklar getirildi ve Baz Yakıt tablosu oluşturuldu.")
                        st.rerun()
                except Exception as ex:
                    st.error(f"Kaynaklar buluttan getirilemedi: {ex}")

        def baz_yakit_tablosunu_olustur():
            musteri_df = st.session_state.get("musteri_ekran_df", pd.DataFrame()).copy()
            if musteri_df.empty or "Müşteri Kodu" not in musteri_df.columns:
                return pd.DataFrame(columns=baz_yakit_sutunlari)

            kimlikler = musteri_df.copy()
            kimlikler.columns = [str(c).strip() for c in kimlikler.columns]
            kimlikler["Müşteri Kodu"] = kimlikler["Müşteri Kodu"].apply(guvenli_metin_kodu)
            for col in ["Müşteri Adı", "Müşteri Temsilcisi", "Durum"]:
                if col not in kimlikler.columns:
                    kimlikler[col] = ""
            kimlikler = (
                kimlikler[kimlikler["Müşteri Kodu"] != ""]
                .drop_duplicates(subset=["Müşteri Kodu"], keep="first")
                [["Müşteri Kodu", "Müşteri Adı", "Müşteri Temsilcisi", "Durum"]]
            )

            parametreler = st.session_state.get("deg_anah_veri", pd.DataFrame()).copy()
            if not parametreler.empty and "Müşteri Kodu" in parametreler.columns:
                parametreler["Müşteri Kodu"] = parametreler["Müşteri Kodu"].apply(guvenli_metin_kodu)
                for col in ["KDV Durumu", "Baz Yakıt Fiyatı"]:
                    if col not in parametreler.columns:
                        parametreler[col] = np.nan
                parametreler = (
                    parametreler.drop_duplicates(subset=["Müşteri Kodu"], keep="first")
                    [["Müşteri Kodu", "KDV Durumu", "Baz Yakıt Fiyatı"]]
                )
                sonuc = pd.merge(kimlikler, parametreler, on="Müşteri Kodu", how="left")
            else:
                sonuc = kimlikler.copy()
                sonuc["KDV Durumu"] = np.nan
                sonuc["Baz Yakıt Fiyatı"] = np.nan

            sonuc["KDV Durumu"] = sonuc["KDV Durumu"].apply(
                lambda v: "" if pd.isna(v) else str(v).strip()
            )

            def fiyat_ve_kdv_hazirla(row):
                ham = row.get("Baz Yakıt Fiyatı")
                ham_bos = ham is None or (isinstance(ham, str) and ham.strip() in {"", "-"})
                try:
                    ham_bos = ham_bos or pd.isna(ham)
                except Exception:
                    pass
                if ham_bos:
                    return pd.Series([np.nan, np.nan])
                girilen = guvenli_sayi(ham)
                kdv = (
                    str(row.get("KDV Durumu", ""))
                    .strip()
                    .upper()
                    .replace("İ", "I")
                    .replace("’", "'")
                )
                if kdv == "KDV'LI":
                    net = girilen / 1.20
                elif kdv in {"KDV'SIZ", "MUAF"}:
                    net = girilen
                else:
                    net = np.nan
                return pd.Series([girilen, net])

            sonuc[["Baz Yakıt Fiyatı (Girilen)", "Esk. Baz Yakıt Fiyatı (KDV Hariç)"]] = (
                sonuc.apply(fiyat_ve_kdv_hazirla, axis=1)
            )
            return sonuc.reindex(columns=baz_yakit_sutunlari)

        st.session_state.baz_yakit_veri = otomatik_baz_yakit_tablosu_olustur()

        if not st.session_state.baz_yakit_veri.empty:
            eksik_baz_maskesi = (
                st.session_state.baz_yakit_veri["KDV Durumu"].eq("")
                | st.session_state.baz_yakit_veri["Baz Yakıt Fiyatı (Girilen)"].isna()
            )
            if eksik_baz_maskesi.any():
                st.warning(
                    f"{int(eksik_baz_maskesi.sum()):,} müşterinin KDV Durumu veya "
                    "Baz Yakıt Fiyatı bulunamadı. Bu değerler sıfır kabul edilmedi."
                )

            edited_by_df = st.data_editor(
                st.session_state.baz_yakit_veri,
                use_container_width=True,
                height=400,
                disabled=baz_yakit_sutunlari,
                column_config={
                    "Baz Yakıt Fiyatı (Girilen)": st.column_config.NumberColumn(
                        "Baz Yakıt Fiyatı (Girilen)", format="₺%.2f"
                    ),
                    "Esk. Baz Yakıt Fiyatı (KDV Hariç)": st.column_config.NumberColumn(
                        "Esk. Baz Yakıt Fiyatı (KDV Hariç)", format="₺%.2f"
                    )
                },
                key="ed_by_t6_auto_v2"
            )
            if rev_secenekleri:
                st.markdown("---")
                c_by1, c_by2, c_by3 = st.columns(3)
                r_id_by = sayfa_aktif_revizyonunu_getir(c_by1)
                if c_by2.button("💾 Baz Yakıtları Buluta Kilitle", type="primary", use_container_width=True, key="btn_by_sv"):
                    # Mevcut Supabase şemasıyla geriye dönük uyumlu alan adları.
                    by_recs = []
                    for _, row in edited_by_df.iterrows():
                        by_recs.append({
                            "Müşteri Kodu": json_uyumlu_deger(row.get("Müşteri Kodu")),
                            "Müşteri Adı": json_uyumlu_deger(row.get("Müşteri Adı")),
                            "Müşteri Temsilcisi": json_uyumlu_deger(row.get("Müşteri Temsilcisi")),
                            "Durum": json_uyumlu_deger(row.get("Durum")),
                            "KDV'li / KDV'siz": json_uyumlu_deger(row.get("KDV Durumu")),
                            "Esk. Baz Yakıt Fiyatı": json_uyumlu_deger(row.get("Baz Yakıt Fiyatı (Girilen)")),
                            "Yakıt Fiyat": json_uyumlu_deger(row.get("Esk. Baz Yakıt Fiyatı (KDV Hariç)"))
                        })
                    for r in by_recs: r["revizyon_id"] = r_id_by
                    client.table("baz_yakit_tablosu").delete().eq("revizyon_id", r_id_by).execute()
                    for i in range(0, len(by_recs), 500): client.table("baz_yakit_tablosu").insert(by_recs[i:i+500]).execute()
                    revizyonu_degistirildi_isaretle(r_id_by)
                    st.success("Mühürlendi!")
                if c_by3.button("🔄 Versiyonun Baz Yakıt Değerlerini Getir", type="secondary", use_container_width=True, key="btn_by_ld"):
                    by_res = client.table("baz_yakit_tablosu").select("*").eq("revizyon_id", r_id_by).execute()
                    if by_res.data:
                        st.success("Buluttaki Baz Yakıt kaydı doğrulandı. Güncel ekran kaynak sayfalardan otomatik oluşturulur.")
        else:
            st.info(
                "Baz Yakıt tablosunu oluşturmak için önce Yeni-Bütçe Müşteri ve "
                "değ.anah.-yakıt-kdv sayfalarına veri yükleyin veya buluttan çağırın."
            )

# ------------------------------------------------------------
# 6. SEKME: ESKALASYON & MASTER DATA
# ------------------------------------------------------------
if sekme_acik_mi[5]:
    with sekmeler[5]:
        st.title("🧾 Eskalasyon ve Master Data Yönetimi")
        st.caption(
            "Müşteri kimlikleri ve Durum (Durum_2) Yeni-Bütçe sayfasından; "
            "Değişim Anahtarı/KDV/Baz fiyat kaynak sayfalardan gelir. Durum GEÇERSİZ "
            "ise Değişim Anahtarı da otomatik GEÇERSİZ olur. Mazot oranları; "
            "başlangıç tarihi, sabit periyot ve pozitif/negatif anlık eşik kuralıyla "
            "hesaplanır; aylık sonuçlar elle değiştirilebilir. Enflasyon oranları "
            "ÜFE–TÜFE sayfasındaki kullanılan verilerden sabit periyoda göre "
            "hesaplanır ve Mazot Aralık sütununun sağında gösterilir."
            " Eskalasyon Ocak–Aralık alanları; ilgili ayın mazot ve enflasyon "
            "oranlarının müşteri bazlı değişim yüzdeleriyle ağırlıklandırılmış "
            "toplamıdır."
        )

        aktif_master_rev_id = aktif_revizyon_id_getir()
        if client and aktif_master_rev_id:
            try:
                master_bulut_kaydini_oturuma_yukle(aktif_master_rev_id)
            except Exception as ex:
                st.warning(
                    "Kayıtlı Master Data değerleri otomatik getirilemedi: "
                    f"{ex}"
                )

        try:
            master_enflasyon_kayitlari, master_asgari_kayitlari = (
                master_enflasyon_kaynaklarini_getir(
                    aktif_revizyon_id_getir()
                )
            )
            master_enflasyon_haritasi = enflasyon_kaynak_haritasi_olustur(
                master_enflasyon_kayitlari
            )
            master_enflasyon_kaynak_hatasi = None
        except Exception as ex:
            master_enflasyon_kayitlari = []
            master_asgari_kayitlari = []
            master_enflasyon_haritasi = {}
            master_enflasyon_kaynak_hatasi = str(ex)

        def master_data_tablosunu_olustur():
            musteri_df = st.session_state.get("musteri_ekran_df", pd.DataFrame()).copy()
            if musteri_df.empty or "Müşteri Kodu" not in musteri_df.columns:
                musteri_df = st.session_state.get(
                    "master_bulut_kaynak_df", pd.DataFrame()
                ).copy()
            if musteri_df.empty or "Müşteri Kodu" not in musteri_df.columns:
                return pd.DataFrame(columns=master_data_sutunlari)

            musteri_df = sutun_adlarini_standartlastir(musteri_df)
            musteri_df["Müşteri Kodu"] = musteri_df["Müşteri Kodu"].apply(guvenli_metin_kodu)

            # Master Data'daki Durum, Yeni-Bütçe sayfasında kullanıcının
            # yönettiği Durum_2 alanından gelir; ilk kaynaktaki Durum kullanılmaz.
            if "Durum_2" in musteri_df.columns:
                musteri_df["Durum"] = musteri_df["Durum_2"].apply(
                    lambda v: "" if pd.isna(v) else str(v).strip().upper()
                )
            elif "Durum" not in musteri_df.columns:
                musteri_df["Durum"] = ""
            else:
                musteri_df["Durum"] = musteri_df["Durum"].apply(
                    lambda v: "" if pd.isna(v) else str(v).strip().upper()
                )

            for col in master_data_kimlik_sutunlari:
                if col not in musteri_df.columns:
                    musteri_df[col] = ""
            sonuc = (
                musteri_df[musteri_df["Müşteri Kodu"] != ""]
                .drop_duplicates(subset=["Müşteri Kodu"], keep="first")
                [master_data_kimlik_sutunlari]
                .reset_index(drop=True)
            )

            parametre_df = sutun_adlarini_standartlastir(
                st.session_state.get("deg_anah_veri", pd.DataFrame())
            )
            if not parametre_df.empty and "Müşteri Kodu" in parametre_df.columns:
                parametre_df["Müşteri Kodu"] = parametre_df["Müşteri Kodu"].apply(guvenli_metin_kodu)
                if "Değişim Anahtarı" not in parametre_df.columns:
                    parametre_df["Değişim Anahtarı"] = ""
                degisim_df = (
                    parametre_df.drop_duplicates(subset=["Müşteri Kodu"], keep="first")
                    [["Müşteri Kodu", "Değişim Anahtarı"]]
                )
                sonuc = pd.merge(sonuc, degisim_df, on="Müşteri Kodu", how="left")
            else:
                bulut_master = sutun_adlarini_standartlastir(
                    st.session_state.get(
                        "master_bulut_kaynak_df", pd.DataFrame()
                    )
                )
                if (
                    not bulut_master.empty
                    and "Müşteri Kodu" in bulut_master.columns
                    and "Değişim Anahtarı" in bulut_master.columns
                ):
                    bulut_master["Müşteri Kodu"] = bulut_master[
                        "Müşteri Kodu"
                    ].apply(guvenli_metin_kodu)
                    sonuc = pd.merge(
                        sonuc,
                        bulut_master.drop_duplicates(
                            "Müşteri Kodu", keep="last"
                        )[["Müşteri Kodu", "Değişim Anahtarı"]],
                        on="Müşteri Kodu",
                        how="left"
                    )
                else:
                    sonuc["Değişim Anahtarı"] = ""

            # Excel mantığı:
            # EĞER(Durum="GEÇERSİZ"; "GEÇERSİZ"; DÜŞEYARA(Müşteri Kodu; ...))
            sonuc["Değişim Anahtarı"] = sonuc["Değişim Anahtarı"].apply(
                lambda v: "" if pd.isna(v) else str(v).strip()
            )
            gecersiz_musteriler = (
                sonuc["Durum"].fillna("").astype(str).str.strip().str.upper()
                == "GEÇERSİZ"
            )
            sonuc.loc[gecersiz_musteriler, "Değişim Anahtarı"] = "GEÇERSİZ"

            baz_df = otomatik_baz_yakit_tablosu_olustur()
            st.session_state.baz_yakit_veri = baz_df.copy()
            if not baz_df.empty:
                sonuc = pd.merge(
                    sonuc,
                    baz_df[[
                        "Müşteri Kodu", "KDV Durumu", "Baz Yakıt Fiyatı (Girilen)",
                        "Esk. Baz Yakıt Fiyatı (KDV Hariç)"
                    ]],
                    on="Müşteri Kodu",
                    how="left"
                )
            else:
                bulut_master = sutun_adlarini_standartlastir(
                    st.session_state.get(
                        "master_bulut_kaynak_df", pd.DataFrame()
                    )
                )
                bulut_baz_sutunlari = [
                    "Müşteri Kodu", "KDV Durumu",
                    "Baz Yakıt Fiyatı (Girilen)",
                    "Esk. Baz Yakıt Fiyatı (KDV Hariç)"
                ]
                if (
                    not bulut_master.empty
                    and all(
                        col in bulut_master.columns
                        for col in bulut_baz_sutunlari
                    )
                ):
                    bulut_master["Müşteri Kodu"] = bulut_master[
                        "Müşteri Kodu"
                    ].apply(guvenli_metin_kodu)
                    sonuc = pd.merge(
                        sonuc,
                        bulut_master.drop_duplicates(
                            "Müşteri Kodu", keep="last"
                        )[bulut_baz_sutunlari],
                        on="Müşteri Kodu",
                        how="left"
                    )
                else:
                    sonuc["KDV Durumu"] = ""
                    sonuc["Baz Yakıt Fiyatı (Girilen)"] = np.nan
                    sonuc["Esk. Baz Yakıt Fiyatı (KDV Hariç)"] = np.nan

            master_tarih_sutunlari = [
                "Esk. Yakıt Başlangıç Tarihi",
                "Esk. Enf. Başlangıç Tarihi"
            ]
            master_sayisal_sutunlari = [
                col for col in master_data_manuel_sutunlari
                if col not in master_tarih_sutunlari
            ]

            # Arrow string sütununa datetime.date yazılması TypeError üretir.
            # Kayıtlı manuel değerleri uygulamadan önce kesin veri tiplerini kur.
            for col in master_tarih_sutunlari:
                if col not in sonuc.columns:
                    sonuc[col] = pd.NaT
                sonuc[col] = pd.to_datetime(
                    sonuc[col], errors="coerce", dayfirst=True
                )
            for col in master_sayisal_sutunlari:
                if col not in sonuc.columns:
                    sonuc[col] = np.nan
                sonuc[col] = pd.to_numeric(sonuc[col], errors="coerce").astype(float)

            # Daha önce kaydedilen manuel değerler kaynaklardan yeniden üretim sırasında korunur.
            for idx, row in sonuc.iterrows():
                mkod = guvenli_metin_kodu(row["Müşteri Kodu"])
                kayitli = st.session_state.master_data_ayarlari.get(mkod, {})
                for col in master_data_manuel_sutunlari:
                    if col not in kayitli:
                        continue
                    kayitli_deger = kayitli[col]
                    kayitli_bos = kayitli_deger is None
                    if isinstance(kayitli_deger, str):
                        kayitli_bos = kayitli_bos or not kayitli_deger.strip()
                    try:
                        kayitli_bos = kayitli_bos or bool(pd.isna(kayitli_deger))
                    except (TypeError, ValueError):
                        pass
                    if not kayitli_bos:
                        if col in master_tarih_sutunlari:
                            sonuc.at[idx, col] = pd.to_datetime(
                                kayitli_deger, errors="coerce", dayfirst=True
                            )
                        else:
                            sonuc.at[idx, col] = guvenli_sayi(kayitli_deger)

            for col in [
                "Yakıt Değişim Yüzdesi (%)", "Yakıt Anlık Değişim Oranı (%)",
                "Yakıt Değişim Periyodu (Ay)", "Enf. Değişim Yüzdesi (%)",
                "Enf. Değişim Periyodu (Ay)"
            ]:
                sonuc[col] = sonuc[col].apply(guvenli_sayi).astype(float)

            # Mazot ayları, müşterinin Yakıt Değişim Periyodu ile 2026 Mazot
            # matrisindeki aynı periyot satırından otomatik başlatılır.
            for col in master_data_mazot_sutunlari:
                sonuc[col] = np.nan
            for idx, row in sonuc.iterrows():
                mkod = guvenli_metin_kodu(row["Müşteri Kodu"])
                durum_gecersiz = (
                    str(row.get("Durum", "")).strip().upper() == "GEÇERSİZ"
                )
                anahtar_gecersiz = (
                    "GECERSIZ" in degisim_anahtarini_normallestir(
                        row.get("Değişim Anahtarı", "")
                    )
                )
                if durum_gecersiz or anahtar_gecersiz:
                    otomatik_oranlar = {
                        col: np.nan for col in master_data_mazot_sutunlari
                    }
                else:
                    otomatik_oranlar = musteri_mazot_oranlarini_getir(
                        row["Yakıt Değişim Periyodu (Ay)"],
                        row["Yakıt Anlık Değişim Oranı (%)"],
                        row["Esk. Yakıt Başlangıç Tarihi"]
                    )
                manuel_oranlar = st.session_state.master_mazot_ayarlari.get(mkod, {})
                for col in master_data_mazot_sutunlari:
                    deger = otomatik_oranlar[col]
                    if col in manuel_oranlar:
                        manuel_deger = manuel_oranlar[col]
                        try:
                            manuel_bos = bool(pd.isna(manuel_deger))
                        except (TypeError, ValueError):
                            manuel_bos = False
                        deger = np.nan if manuel_bos else guvenli_sayi(manuel_deger)
                    sonuc.at[idx, col] = deger

            # Enflasyon ayları, Mazot Aralık sütununun hemen arkasında yer alır.
            for col in master_data_enflasyon_sutunlari:
                sonuc[col] = np.nan
            for idx, row in sonuc.iterrows():
                mkod = guvenli_metin_kodu(row["Müşteri Kodu"])
                durum_gecersiz = (
                    str(row.get("Durum", "")).strip().upper() == "GEÇERSİZ"
                )
                if durum_gecersiz:
                    otomatik_enflasyon = {
                        col: np.nan for col in master_data_enflasyon_sutunlari
                    }
                else:
                    otomatik_enflasyon = musteri_enflasyon_oranlarini_getir(
                        row.get("Değişim Anahtarı", ""),
                        row.get("Enf. Değişim Periyodu (Ay)"),
                        row.get("Esk. Enf. Başlangıç Tarihi"),
                        master_enflasyon_haritasi,
                        master_asgari_kayitlari,
                        hedef_yil=2026
                    )
                manuel_enflasyon = (
                    st.session_state.master_enflasyon_ayarlari.get(mkod, {})
                )
                for col in master_data_enflasyon_sutunlari:
                    deger = otomatik_enflasyon[col]
                    if col in manuel_enflasyon:
                        manuel_deger = manuel_enflasyon[col]
                        try:
                            manuel_bos = (
                                manuel_deger is None or bool(pd.isna(manuel_deger))
                            )
                        except (TypeError, ValueError):
                            manuel_bos = manuel_deger is None
                        deger = (
                            np.nan if manuel_bos
                            else guvenli_sayi(manuel_deger)
                        )
                    sonuc.at[idx, col] = deger

            # Nihai eskalasyon, aylık enflasyon ve mazot oranlarının müşteriye
            # girilen ağırlıklarıyla birleştirilmesidir. O ayda uygulama yoksa
            # kaynak hücre boş olsa bile nihai sonuç yüzde 0,00 gösterilir.
            for col in master_data_eskalasyon_sutunlari:
                sonuc[col] = 0.0
            for idx, row in sonuc.iterrows():
                durum_gecersiz = (
                    str(row.get("Durum", "")).strip().upper() == "GEÇERSİZ"
                )
                anahtar_gecersiz = (
                    "GECERSIZ" in degisim_anahtarini_normallestir(
                        row.get("Değişim Anahtarı", "")
                    )
                )
                eskalasyon_oranlari = musteri_eskalasyon_oranlarini_getir(
                    row,
                    durum_gecersiz=durum_gecersiz,
                    anahtar_gecersiz=anahtar_gecersiz
                )
                for col, deger in eskalasyon_oranlari.items():
                    sonuc.at[idx, col] = deger

            sonuc["Baz Yakıt Fiyatı (Girilen)"] = pd.to_numeric(
                sonuc["Baz Yakıt Fiyatı (Girilen)"], errors="coerce"
            )
            sonuc["Esk. Baz Yakıt Fiyatı (KDV Hariç)"] = pd.to_numeric(
                sonuc["Esk. Baz Yakıt Fiyatı (KDV Hariç)"], errors="coerce"
            )
            for col in ["Esk. Yakıt Başlangıç Tarihi", "Esk. Enf. Başlangıç Tarihi"]:
                sonuc[col] = pd.to_datetime(
                    sonuc[col], errors="coerce", dayfirst=True
                ).dt.date

            return sonuc.reindex(columns=master_data_sutunlari)

        master_df = master_data_tablosunu_olustur()
        if master_df.empty:
            st.info(
                "Master Data tablosu için önce Yeni-Bütçe Müşteri sayfasına veri yükleyin "
                "veya müşteri kartlarını buluttan çağırın."
            )
        else:
            if master_enflasyon_kaynak_hatasi:
                st.warning(
                    "ÜFE–TÜFE verileri Master Data için okunamadı: "
                    f"{master_enflasyon_kaynak_hatasi}"
                )
            elif not master_enflasyon_haritasi:
                st.warning(
                    "ÜFE–TÜFE kullanılan veri havuzu boş. Önce ÜFE–TÜFE Yönetimi "
                    "sayfasında gerçekleşen/tahmin değerlerini kaydedin."
                )
            eksik_eslesme = (
                master_df["KDV Durumu"].fillna("").eq("")
                | master_df["Baz Yakıt Fiyatı (Girilen)"].isna()
                | master_df["Değişim Anahtarı"].fillna("").eq("")
            )
            if eksik_eslesme.any():
                st.warning(
                    f"{int(eksik_eslesme.sum()):,} müşteride Değişim Anahtarı, KDV Durumu "
                    "veya Baz Yakıt Fiyatı eksik. Eksikler sıfırla doldurulmadı."
                )

            kilitli_master = (
                master_data_kimlik_sutunlari
                + master_data_kaynak_sutunlari
                + master_data_eskalasyon_sutunlari
            )
            master_editor_key = (
                f"master_data_editor_v3_{st.session_state.master_editor_nonce}"
            )
            edited_master = st.data_editor(
                master_df,
                use_container_width=True,
                height=470,
                disabled=kilitli_master,
                column_config={
                    "Yakıt Değişim Yüzdesi (%)": st.column_config.NumberColumn(
                        "Yakıt Değişim Yüzdesi (%)", format="%.2f%%", min_value=0.0
                    ),
                    "Yakıt Anlık Değişim Oranı (%)": st.column_config.NumberColumn(
                        "Yakıt Anlık Değişim Oranı (%)", format="%.2f%%"
                    ),
                    "Yakıt Değişim Periyodu (Ay)": st.column_config.NumberColumn(
                        "Yakıt Değişim Periyodu (Ay)", format="%d", min_value=0
                    ),
                    "Enf. Değişim Yüzdesi (%)": st.column_config.NumberColumn(
                        "Enf. Değişim Yüzdesi (%)", format="%.2f%%", min_value=0.0
                    ),
                    "Enf. Değişim Periyodu (Ay)": st.column_config.NumberColumn(
                        "Enf. Değişim Periyodu (Ay)", format="%d", min_value=0
                    ),
                    "Baz Yakıt Fiyatı (Girilen)": st.column_config.NumberColumn(
                        "Baz Yakıt Fiyatı (Girilen)", format="₺%.2f"
                    ),
                    "Esk. Baz Yakıt Fiyatı (KDV Hariç)": st.column_config.NumberColumn(
                        "Esk. Baz Yakıt Fiyatı (KDV Hariç)", format="₺%.2f", min_value=0.0
                    ),
                    "Esk. Yakıt Başlangıç Tarihi": st.column_config.DateColumn(
                        "Esk. Yakıt Başlangıç Tarihi", format="DD.MM.YYYY"
                    ),
                    "Esk. Enf. Başlangıç Tarihi": st.column_config.DateColumn(
                        "Esk. Enf. Başlangıç Tarihi", format="DD.MM.YYYY"
                    ),
                    **{
                        col: st.column_config.NumberColumn(
                            col, format="%.2f%%"
                        )
                        for col in master_data_mazot_sutunlari
                    },
                    **{
                        col: st.column_config.NumberColumn(
                            col, format="%.2f%%"
                        )
                        for col in master_data_enflasyon_sutunlari
                    },
                    **{
                        col: st.column_config.NumberColumn(
                            col, format="%.2f%%"
                        )
                        for col in master_data_eskalasyon_sutunlari
                    }
                },
                key=master_editor_key
            )
            st.session_state.master_data_df = edited_master.copy()

            # Streamlit'in edited_rows kaydı gerçekten dokunulan hücreleri verir.
            # Böylece otomatik hesaplanan değerler yanlışlıkla manuel sayılmaz.
            editor_durumu = st.session_state.get(master_editor_key, {})
            edited_rows = (
                editor_durumu.get("edited_rows", {})
                if isinstance(editor_durumu, dict) else {}
            )
            for _, row in edited_master.iterrows():
                mkod = guvenli_metin_kodu(row["Müşteri Kodu"])
                st.session_state.master_data_ayarlari[mkod] = {
                    col: row.get(col) for col in master_data_manuel_sutunlari
                }

            mazot_hesabi_degisti = manuel_mazot_hucrelerini_kaydet(
                edited_rows, edited_master
            )
            enflasyon_hesabi_degisti = manuel_enflasyon_hucrelerini_kaydet(
                edited_rows, edited_master
            )

            if mazot_hesabi_degisti or enflasyon_hesabi_degisti:
                # Editör anahtarını değiştirmek tabloyu yeni bir bileşen gibi
                # oluşturur ve kullanıcının yatay kaydırma konumunu sola atar.
                # Bunun yerine yalnızca hesap sürücülerinin güncel değerlerini
                # imzalayıp aynı editör anahtarıyla bir kez yeniden hesapla.
                yeniden_hesaplama_sutunlari = [
                    "Yakıt Değişim Yüzdesi (%)",
                    "Yakıt Anlık Değişim Oranı (%)",
                    "Yakıt Değişim Periyodu (Ay)",
                    "Esk. Yakıt Başlangıç Tarihi",
                    "Enf. Değişim Yüzdesi (%)",
                    "Enf. Değişim Periyodu (Ay)",
                    "Esk. Enf. Başlangıç Tarihi"
                ] + master_data_mazot_sutunlari + master_data_enflasyon_sutunlari
                surucu_imza_verisi = []
                for satir_no, degisiklikler in edited_rows.items():
                    if not isinstance(degisiklikler, dict):
                        continue
                    if not any(
                        col in degisiklikler
                        for col in yeniden_hesaplama_sutunlari
                    ):
                        continue
                    try:
                        satir_index = int(satir_no)
                    except (TypeError, ValueError):
                        continue
                    if satir_index < 0 or satir_index >= len(edited_master):
                        continue
                    surucu_row = edited_master.iloc[satir_index]
                    surucu_imza_verisi.append({
                        "Satır": satir_index,
                        "Müşteri Kodu": guvenli_metin_kodu(
                            surucu_row.get("Müşteri Kodu")
                        ),
                        **{
                            col: json_uyumlu_deger(surucu_row.get(col))
                            for col in yeniden_hesaplama_sutunlari
                        }
                    })
                surucu_imzasi = json.dumps(
                    surucu_imza_verisi,
                    ensure_ascii=False,
                    sort_keys=True,
                    default=str
                )
                if (
                    st.session_state.master_son_islenen_surucu_imzasi
                    != surucu_imzasi
                ):
                    st.session_state.master_son_islenen_surucu_imzasi = (
                        surucu_imzasi
                    )
                    # Aynı key korunduğu için yatay kaydırma ve seçili hücre
                    # mümkün olduğunca aynı yerde kalır.
                    st.rerun()

            st.markdown("---")
            md1, md2, md3 = st.columns(3)
            if md1.button(
                "💾 Manuel Değişiklikleri Hafızaya İşle",
                type="primary",
                use_container_width=True,
                key="btn_master_memory"
            ):
                st.success("Master Data manuel değerleri hafızaya kaydedildi.")

            if md1.button(
                "♻️ Mazot Oranlarını Otomatiğe Döndür",
                use_container_width=True,
                key="btn_master_mazot_reset"
            ):
                st.session_state.master_mazot_ayarlari = {}
                st.session_state.master_editor_nonce += 1
                st.rerun()

            if md1.button(
                "♻️ Enflasyon Oranlarını Otomatiğe Döndür",
                use_container_width=True,
                key="btn_master_enflasyon_reset"
            ):
                st.session_state.master_enflasyon_ayarlari = {}
                st.session_state.master_editor_nonce += 1
                st.rerun()

            master_excel = io.BytesIO()
            with pd.ExcelWriter(master_excel, engine="openpyxl") as writer:
                edited_master.to_excel(writer, index=False, sheet_name="Master Data")
            md1.download_button(
                "📥 Master Data Excel İndir",
                master_excel.getvalue(),
                "eskalasyon_master_data.xlsx",
                use_container_width=True,
                key="master_excel_download"
            )

            if rev_secenekleri:
                r_id_master = sayfa_aktif_revizyonunu_getir(md2)
                if md2.button(
                    "💾 Master Data'yı Buluta Kaydet",
                    use_container_width=True,
                    key="btn_master_cloud_save"
                ):
                    try:
                        master_records = []
                        for _, row in edited_master.iterrows():
                            record = {
                                col: json_uyumlu_deger(row.get(col))
                                for col in master_data_sutunlari
                            }
                            mkod = guvenli_metin_kodu(row.get("Müşteri Kodu"))
                            record[MASTER_MAZOT_MANUEL_ALANLAR_DB] = sorted(
                                st.session_state.master_mazot_ayarlari.get(
                                    mkod, {}
                                ).keys()
                            )
                            record[MASTER_ENFLASYON_MANUEL_ALANLAR_DB] = sorted(
                                st.session_state.master_enflasyon_ayarlari.get(
                                    mkod, {}
                                ).keys()
                            )
                            record["revizyon_id"] = r_id_master
                            master_records.append(record)
                        client.table("master_data_tablosu").delete().eq(
                            "revizyon_id", r_id_master
                        ).execute()
                        for i in range(0, len(master_records), 500):
                            client.table("master_data_tablosu").insert(
                                master_records[i:i + 500]
                            ).execute()
                        st.session_state.master_bulut_yuklenen_revizyon = (
                            r_id_master
                        )
                        st.session_state.master_bulut_kaynak_df = (
                            edited_master.copy()
                        )
                        revizyonu_degistirildi_isaretle(r_id_master)
                        st.success("Master Data seçilen bulut versiyonuna kaydedildi.")
                    except Exception as ex:
                        st.error(
                            "Master Data buluta kaydedilemedi. Önce verilen Supabase SQL'ini "
                            f"çalıştırın. Ayrıntı: {ex}"
                        )

                if md3.button(
                    "🔄 Master Data'yı Buluttan Getir",
                    use_container_width=True,
                    key="btn_master_cloud_load"
                ):
                    try:
                        kayit_sayisi = master_bulut_kaydini_oturuma_yukle(
                            r_id_master, zorla=True
                        )
                        if kayit_sayisi:
                            st.session_state.master_editor_nonce += 1
                            st.success(
                                f"{kayit_sayisi:,} Master Data kaydı ve "
                                "manuel değerleri buluttan getirildi."
                            )
                            st.rerun()
                        else:
                            st.warning("Seçilen versiyonda Master Data kaydı bulunamadı.")
                    except Exception as ex:
                        st.error(
                            "Master Data buluttan getirilemedi. Önce verilen Supabase SQL'ini "
                            f"çalıştırın. Ayrıntı: {ex}"
                        )

# ------------------------------------------------------------
# 7. SEKME: 2026 MAZOT ANALİZİ
# ------------------------------------------------------------
if sekme_acik_mi[6]:
    with sekmeler[6]:
        st.title("📊 2026 Mazot Fiyat Değişim Periyot Analizörü")
        st.caption(
            "Baz Motorin ve Ocak-Aralık fiyatlarının tamamı elle değiştirilebilir. "
            "Bir fiyat değiştiğinde matris ve Master Data otomatik mazot oranları "
            "yeni fiyatlara göre yeniden hesaplanır."
        )
        up_mazot = st.file_uploader("Yeni Mazot Fiyat Trendi Yükle", type=["xlsx", "xls", "csv"], key="mazot_up_file")
        if up_mazot:
            df_mz = pd.read_csv(up_mazot) if up_mazot.name.lower().endswith(".csv") else pd.read_excel(up_mazot)
            df_mz.columns = [str(c).strip() for c in df_mz.columns]
            st.session_state.mazot_giriş_veri = df_mz.reindex(columns=mazot_giriş_sutunlari).applymap(guvenli_sayi).copy()

        edited_mazot_input = st.data_editor(st.session_state.mazot_giriş_veri, use_container_width=True, hide_index=True, column_config={c: st.column_config.NumberColumn(c, format="₺%.4f") for c in mazot_giriş_sutunlari}, key="mazot_giriş_editor")
        st.session_state.mazot_giriş_veri = edited_mazot_input.copy()

        if not edited_mazot_input.empty:
            df_mazot_matris = mazot_degisim_matrisi_olustur(edited_mazot_input)
            df_mazot_matris_gosterim = df_mazot_matris.copy()
            for ay in aylar:
                df_mazot_matris_gosterim[ay] = (
                    pd.to_numeric(df_mazot_matris_gosterim[ay], errors="coerce")
                    * 100.0
                )
            st.subheader("📈 Hesaplanan Aylık Değişim Matrisi (%)")
            st.dataframe(
                df_mazot_matris_gosterim,
                use_container_width=True,
                hide_index=True,
                column_config={
                    ay: st.column_config.NumberColumn(ay, format="%.2f%%")
                    for ay in aylar
                }
            )

            if rev_secenekleri:
                st.markdown("---")
                cm_z1, cm_z2, cm_z3 = st.columns(3)
                r_id_z = sayfa_aktif_revizyonunu_getir(cm_z1)
                if cm_z2.button("💾 Mazot Trendini Buluta Kaydet", type="primary", use_container_width=True, key="btn_mz_sv"):
                    mz_rec = {str(col): json_uyumlu_deger(val) for col, val in edited_mazot_input.iloc[0].items()}
                    mz_rec["revizyon_id"] = r_id_z
                    client.table("mazot_tablosu").delete().eq("revizyon_id", r_id_z).execute()
                    client.table("mazot_tablosu").insert(mz_rec).execute()
                    revizyonu_degistirildi_isaretle(r_id_z)
                    st.success("Mühürlendi!")
                if cm_z3.button("🔄 Versiyonun Mazot Verilerini Getir", type="secondary", use_container_width=True, key="btn_mz_ld"):
                    mz_res = client.table("mazot_tablosu").select("*").eq("revizyon_id", r_id_z).execute()
                    if mz_res.data:
                        st.session_state.mazot_giriş_veri = pd.DataFrame([mz_res.data[0]])[[c for c in mazot_giriş_sutunlari if c in mz_res.data[0]]].reindex(columns=mazot_giriş_sutunlari)
                        st.rerun()

# ------------------------------------------------------------
# 8. SEKME: MÜŞTERİ BÜYÜME ORANLARI
# ------------------------------------------------------------
if sekme_acik_mi[7]:
    with sekmeler[7]:
        st.title("📈 Müşteri Büyüme Oranları ve Kg Simülasyonu")
        st.caption(
            "2024–2025 tarihsel Kg havuzu, 2026 güncel Kg yüklemesi, tahmin "
            "ve müşteri büyüme oranları artık bu sayfada birlikte yönetilir."
        )

        NIHAI_SUTUNLAR_9 = [
            "Uniq ID", "Yıl", "Teslimat Tipi", "Atf Tipi", "Çıkış İl Adı", "Çıkış Şube Adı",
            "Varış İl Adı", "Varış Şube Adı", "İlk Okutma Şubesi", "Müşteri Kodu", "Müşteri Adı",
            "Müşteri Temsilcisi", "Sap Kodu", "Durum", "Kayıt Tarihi", "Müşteri Grubu",
            "Esk. Yakıt Başlangıç Tarihi", "Esk. Enf. Başlangıç Tarihi",
            "Ocak Kg", "Şubat Kg", "Mart Kg", "Nisan Kg", "Mayıs Kg", "Haziran Kg",
            "Temmuz Kg", "Ağustos Kg", "Eylül Kg", "Ekim Kg", "Kasım Kg", "Aralık Kg",
            "Toplam Kg"
        ]
        AY_KOLONLARI_9 = [f"{m} Kg" for m in aylar]
        KIMLIK_KOLONLARI_9 = [
            "Müşteri Kodu", "Müşteri Adı", "Müşteri Temsilcisi",
            "Sap Kodu", "Durum", "Kayıt Tarihi", "Müşteri Grubu"
        ]

        def temiz_metin_9(value, varsayilan=""):
            if value is None:
                return varsayilan
            try:
                if pd.isna(value):
                    return varsayilan
            except Exception:
                pass
            metin = str(value).replace("\\xa0", " ").strip()
            return varsayilan if metin.lower() in {"", "nan", "none", "null", "nat"} else metin

        def oku_excel_csv_9(uploaded_file):
            if uploaded_file.name.lower().endswith(".csv"):
                try:
                    return pd.read_csv(uploaded_file, sep=None, engine="python")
                except UnicodeDecodeError:
                    uploaded_file.seek(0)
                    return pd.read_csv(uploaded_file, sep=None, engine="python", encoding="latin-1")
            return pd.read_excel(uploaded_file)

        def temizle_2026_31_kolon(df_raw):
            df = df_raw.copy()
            df.columns = [str(c).strip() for c in df.columns]

            eksik_kolonlar = [c for c in NIHAI_SUTUNLAR_9 if c not in df.columns]
            for c in eksik_kolonlar:
                df[c] = np.nan

            for c in KIMLIK_KOLONLARI_9:
                varsayilan = "DİĞER" if c == "Müşteri Grubu" else ""
                df[c] = df[c].apply(lambda v: temiz_metin_9(v, varsayilan))

            df["Müşteri Kodu"] = df["Müşteri Kodu"].apply(guvenli_metin_kodu)
            df["Müşteri Grubu"] = df["Müşteri Grubu"].str.upper()
            df["Durum"] = df["Durum"].replace("", "GEÇERLİ")
            df["Yıl"] = 2026

            for c in AY_KOLONLARI_9:
                df[c] = df[c].apply(guvenli_sayi).astype(float)

            df["Toplam Kg"] = df[AY_KOLONLARI_9].sum(axis=1)
            df = df[df["Müşteri Kodu"] != ""].reset_index(drop=True)
            return df[NIHAI_SUTUNLAR_9], eksik_kolonlar

        def musteri_bazinda_ozetle_9(df, yil, kaynak_31_kolon=False):
            if df is None or df.empty or "Müşteri Kodu" not in df.columns:
                return pd.DataFrame(columns=KIMLIK_KOLONLARI_9)

            work = df.copy()
            work["Müşteri Kodu"] = work["Müşteri Kodu"].apply(guvenli_metin_kodu)
            work = work[work["Müşteri Kodu"] != ""]

            for c in KIMLIK_KOLONLARI_9:
                if c not in work.columns:
                    work[c] = "DİĞER" if c == "Müşteri Grubu" else ""
            work["Müşteri Grubu"] = work["Müşteri Grubu"].apply(
                lambda v: temiz_metin_9(v, "DİĞER").upper()
            )

            ay_esleme = {}
            for m in aylar:
                kaynak = f"{m} Kg" if kaynak_31_kolon else f"{yil} {m} Kg"
                hedef = f"{yil} {m} Kg"
                if kaynak not in work.columns:
                    work[kaynak] = 0.0
                work[kaynak] = work[kaynak].apply(guvenli_sayi).astype(float)
                ay_esleme[kaynak] = hedef

            kimlik_agg = {
                c: (lambda s, c=c: next(
                    (temiz_metin_9(v, "DİĞER" if c == "Müşteri Grubu" else "")
                     for v in s if temiz_metin_9(v, "") != ""),
                    "DİĞER" if c == "Müşteri Grubu" else ""
                ))
                for c in KIMLIK_KOLONLARI_9 if c != "Müşteri Kodu"
            }
            Kg_agg = {c: "sum" for c in ay_esleme}
            sonuc = work.groupby("Müşteri Kodu", as_index=False).agg({**kimlik_agg, **Kg_agg})
            sonuc = sonuc.rename(columns=ay_esleme)
            sonuc[f"{yil} Toplam Kg"] = sonuc[[f"{yil} {m} Kg" for m in aylar]].sum(axis=1)
            return sonuc

        def ilk_dolu_deger_9(row, adaylar, varsayilan=""):
            for c in adaylar:
                if c in row.index:
                    value = temiz_metin_9(row.get(c), "")
                    if value:
                        return value
            return varsayilan

        HEDEF_GRUPLAR_9 = ["MP", "HOROZ CÜZDAN", "DİĞER"]

        def grup_adi_standartlastir_9(value):
            grup = temiz_metin_9(value, "DİĞER").upper()
            return grup if grup in {"MP", "HOROZ CÜZDAN"} else "DİĞER"

        def tarihsel_havuzu_sikistir_9(dataframe):
            """Eski veya yeni tarihsel kaydı müşteri başına tek satıra indirir."""
            if dataframe is None or dataframe.empty:
                return pd.DataFrame(columns=data_ekran_sutunlari)
            work = dataframe.copy()
            if "Müşteri Kodu" not in work.columns:
                return pd.DataFrame(columns=data_ekran_sutunlari)
            work["Müşteri Kodu"] = work["Müşteri Kodu"].apply(
                guvenli_metin_kodu
            )
            work = work[work["Müşteri Kodu"] != ""].copy()
            if "Müşteri Grubu" not in work.columns:
                work["Müşteri Grubu"] = "DİĞER"
            grup_haritasi = (
                work.drop_duplicates("Müşteri Kodu", keep="last")
                .set_index("Müşteri Kodu")["Müşteri Grubu"]
                .to_dict()
            )
            aylik_kolonlar = [
                f"{yil} {ay} Kg"
                for yil in ["2024", "2025"]
                for ay in aylar
            ]
            for col in aylik_kolonlar:
                if col not in work.columns:
                    work[col] = 0.0
                work[col] = work[col].apply(guvenli_sayi).astype(float)
            sonuc = work.groupby("Müşteri Kodu", as_index=False)[
                aylik_kolonlar
            ].sum()
            sonuc["Müşteri Grubu"] = (
                sonuc["Müşteri Kodu"].map(grup_haritasi)
                .apply(grup_adi_standartlastir_9)
            )
            for yil in ["2024", "2025"]:
                yil_kolonlari = [f"{yil} {ay} Kg" for ay in aylar]
                sonuc[f"{yil} Toplam Kg"] = sonuc[yil_kolonlari].sum(axis=1)
            sonuc["Yıl"] = "2026"
            sonuc["Durum"] = "GEÇERLİ"
            sonuc["Uniq ID"] = "2026" + sonuc["Müşteri Kodu"].astype(str)
            for col in data_ekran_sutunlari:
                if col not in sonuc.columns:
                    sonuc[col] = np.nan
            kolon_sirasi = (
                data_ekran_sutunlari
                + [f"2024 {ay} Kg" for ay in aylar]
                + ["2024 Toplam Kg"]
                + [f"2025 {ay} Kg" for ay in aylar]
                + ["2025 Toplam Kg"]
            )
            return sonuc.reindex(columns=kolon_sirasi).reset_index(drop=True)

        # ------------------------------------------------------------
        # 2024-2025 TARİHSEL KG HAVUZU
        # Eski Data sayfasının gerekli işlevleri bu sayfaya taşınmıştır.
        # ------------------------------------------------------------
        st.session_state.data_sayfası_df = tarihsel_havuzu_sikistir_9(
            st.session_state.get("data_sayfası_df", pd.DataFrame())
        )
        st.subheader("📚 2024–2025 Tarihsel Kg Havuzu")
        st.caption(
            "Büyüme ve sezon dağılımı için kullanılan 2024–2025 verilerini "
            "buradan yükleyebilir, seçili revizyona mühürleyebilir ve sonraki "
            "oturumlarda dosya yüklemeden buluttan çağırabilirsiniz."
        )

        with st.expander(
            "📥 2024–2025 tarihsel veriyi yükle / buluttan getir",
            expanded=st.session_state.get("data_sayfası_df", pd.DataFrame()).empty
        ):
            th1, th2 = st.columns(2)
            tarihsel_yil_9 = th1.selectbox(
                "Yüklenecek yıl",
                ["2024", "2025"],
                index=1,
                key="buyume_tarihsel_yil_9"
            )
            tarihsel_metrik_9 = th2.radio(
                "Dosyadaki aylık metrik",
                ["Kg", "Tutar"],
                horizontal=True,
                key="buyume_tarihsel_metrik_9",
                help=(
                    "Normal kullanım Kg'dır. Kaynak dosyada aylık hacim "
                    "kolonları Tutar adıyla tutulmuşsa Tutar seçilebilir."
                )
            )
            tarihsel_upload_9 = st.file_uploader(
                f"{tarihsel_yil_9} tarihsel müşteri verisini yükleyin",
                type=["xlsx", "xls", "csv"],
                key=f"buyume_tarihsel_upload_9_{tarihsel_yil_9}"
            )

            if tarihsel_upload_9 is not None:
                try:
                    tarihsel_imza_9 = (
                        tarihsel_yil_9,
                        tarihsel_metrik_9,
                        yuklenen_dosya_imzasi(tarihsel_upload_9)
                    )
                    onceki_imza_9 = (
                        st.session_state.buyume_tarihsel_upload_imzalari.get(
                            tarihsel_yil_9
                        )
                    )
                    if tarihsel_imza_9 != onceki_imza_9:
                        tarihsel_raw_9 = oku_excel_csv_9(tarihsel_upload_9)
                        tarihsel_raw_9.columns = [
                            str(c).strip() for c in tarihsel_raw_9.columns
                        ]
                        if "Müşteri Kodu" not in tarihsel_raw_9.columns:
                            raise ValueError(
                                "Dosyada Müşteri Kodu sütunu bulunamadı."
                            )

                        tarihsel_raw_9["Müşteri Kodu"] = (
                            tarihsel_raw_9["Müşteri Kodu"]
                            .apply(guvenli_metin_kodu)
                        )
                        tarihsel_raw_9 = tarihsel_raw_9[
                            tarihsel_raw_9["Müşteri Kodu"] != ""
                        ].copy()
                        if "Müşteri Grubu" not in tarihsel_raw_9.columns:
                            tarihsel_raw_9["Müşteri Grubu"] = "DİĞER"
                        tarihsel_raw_9["Müşteri Grubu"] = (
                            tarihsel_raw_9["Müşteri Grubu"]
                            .apply(grup_adi_standartlastir_9)
                        )

                        sonek_9 = f" {tarihsel_metrik_9}"
                        bulunan_aylar_9 = []
                        tarihsel_gecici_9 = tarihsel_raw_9[
                            ["Müşteri Kodu", "Müşteri Grubu"]
                        ].copy()
                        for ay in aylar:
                            hedef_col_9 = f"{tarihsel_yil_9} {ay} Kg"
                            adaylar_9 = [
                                f"{ay}{sonek_9}",
                                f"{tarihsel_yil_9} {ay}{sonek_9}",
                                ay,
                                f"{tarihsel_yil_9} {ay}"
                            ]
                            kaynak_col_9 = next(
                                (c for c in adaylar_9 if c in tarihsel_raw_9.columns),
                                None
                            )
                            if kaynak_col_9 is None:
                                tarihsel_gecici_9[hedef_col_9] = 0.0
                            else:
                                tarihsel_gecici_9[hedef_col_9] = (
                                    tarihsel_raw_9[kaynak_col_9]
                                    .apply(guvenli_sayi).astype(float)
                                )
                                bulunan_aylar_9.append(ay)

                        if not bulunan_aylar_9:
                            raise ValueError(
                                f"{tarihsel_yil_9} için aylık "
                                f"{tarihsel_metrik_9} sütunları bulunamadı."
                            )

                        hedef_ay_kolonlari_9 = [
                            f"{tarihsel_yil_9} {ay} Kg" for ay in aylar
                        ]
                        tarihsel_ozet_9 = (
                            tarihsel_gecici_9.groupby(
                                ["Müşteri Kodu", "Müşteri Grubu"],
                                as_index=False
                            )[hedef_ay_kolonlari_9].sum()
                        )
                        tarihsel_ozet_9[
                            f"{tarihsel_yil_9} Toplam Kg"
                        ] = tarihsel_ozet_9[hedef_ay_kolonlari_9].sum(axis=1)

                        mevcut_havuz_9 = st.session_state.get(
                            "data_sayfası_df", pd.DataFrame()
                        ).copy()
                        mevcut_grup_haritasi_9 = {}
                        if not mevcut_havuz_9.empty:
                            mevcut_havuz_9["Müşteri Kodu"] = (
                                mevcut_havuz_9["Müşteri Kodu"]
                                .apply(guvenli_metin_kodu)
                            )
                            if "Müşteri Grubu" in mevcut_havuz_9.columns:
                                mevcut_grup_haritasi_9 = (
                                    mevcut_havuz_9
                                    .drop_duplicates("Müşteri Kodu", keep="last")
                                    .set_index("Müşteri Kodu")["Müşteri Grubu"]
                                    .to_dict()
                                )
                            diger_yil_9 = (
                                "2025" if tarihsel_yil_9 == "2024" else "2024"
                            )
                            diger_kolonlar_9 = [
                                f"{diger_yil_9} {ay} Kg" for ay in aylar
                            ]
                            for col in diger_kolonlar_9:
                                if col not in mevcut_havuz_9.columns:
                                    mevcut_havuz_9[col] = 0.0
                                mevcut_havuz_9[col] = (
                                    mevcut_havuz_9[col]
                                    .apply(guvenli_sayi).astype(float)
                                )
                            mevcut_ozet_9 = (
                                mevcut_havuz_9.groupby(
                                    "Müşteri Kodu", as_index=False
                                )[diger_kolonlar_9].sum()
                            )
                            tarihsel_birlesik_9 = pd.merge(
                                mevcut_ozet_9,
                                tarihsel_ozet_9,
                                on="Müşteri Kodu",
                                how="outer"
                            )
                        else:
                            tarihsel_birlesik_9 = tarihsel_ozet_9.copy()

                        if "Müşteri Grubu" not in tarihsel_birlesik_9.columns:
                            tarihsel_birlesik_9["Müşteri Grubu"] = (
                                tarihsel_birlesik_9["Müşteri Kodu"]
                                .map(mevcut_grup_haritasi_9)
                            )
                        else:
                            eski_gruplar_9 = (
                                tarihsel_birlesik_9["Müşteri Kodu"]
                                .map(mevcut_grup_haritasi_9)
                            )
                            tarihsel_birlesik_9["Müşteri Grubu"] = (
                                tarihsel_birlesik_9["Müşteri Grubu"]
                                .where(
                                    tarihsel_birlesik_9[
                                        "Müşteri Grubu"
                                    ].notna(),
                                    eski_gruplar_9
                                )
                            )
                        tarihsel_birlesik_9["Müşteri Grubu"] = (
                            tarihsel_birlesik_9["Müşteri Grubu"]
                            .apply(grup_adi_standartlastir_9)
                        )
                        for yil_9 in ["2024", "2025"]:
                            yil_kolonlari_9 = [
                                f"{yil_9} {ay} Kg" for ay in aylar
                            ]
                            for col in yil_kolonlari_9:
                                if col not in tarihsel_birlesik_9.columns:
                                    tarihsel_birlesik_9[col] = 0.0
                                tarihsel_birlesik_9[col] = (
                                    tarihsel_birlesik_9[col]
                                    .fillna(0.0).apply(guvenli_sayi).astype(float)
                                )
                            tarihsel_birlesik_9[f"{yil_9} Toplam Kg"] = (
                                tarihsel_birlesik_9[yil_kolonlari_9].sum(axis=1)
                            )

                        tarihsel_birlesik_9["Yıl"] = "2026"
                        tarihsel_birlesik_9["Durum"] = "GEÇERLİ"
                        tarihsel_birlesik_9["Uniq ID"] = (
                            "2026"
                            + tarihsel_birlesik_9["Müşteri Kodu"].astype(str)
                        )
                        for col in data_ekran_sutunlari:
                            if col not in tarihsel_birlesik_9.columns:
                                tarihsel_birlesik_9[col] = np.nan

                        st.session_state.data_sayfası_df = (
                            tarihsel_havuzu_sikistir_9(tarihsel_birlesik_9)
                        )
                        st.session_state.buyume_tarihsel_upload_imzalari[
                            tarihsel_yil_9
                        ] = tarihsel_imza_9
                        st.session_state.data_sayfası_df.to_parquet(
                            CACHE_DATA_MASTER, index=False
                        )
                        st.success(
                            f"{tarihsel_yil_9} verisi müşteri bazında "
                            f"özetlendi: {len(tarihsel_ozet_9):,} müşteri; "
                            f"bulunan aylar: {', '.join(bulunan_aylar_9)}."
                        )
                except Exception as ex:
                    st.error(f"Tarihsel veri işlenemedi: {ex}")

            tarihsel_havuz_9 = st.session_state.get(
                "data_sayfası_df", pd.DataFrame()
            ).copy()
            if not tarihsel_havuz_9.empty:
                tarihsel_gosterim_kolonlari_9 = [
                    "Müşteri Kodu", "Müşteri Grubu",
                    *[f"2024 {ay} Kg" for ay in aylar], "2024 Toplam Kg",
                    *[f"2025 {ay} Kg" for ay in aylar], "2025 Toplam Kg"
                ]
                for col in tarihsel_gosterim_kolonlari_9:
                    if col not in tarihsel_havuz_9.columns:
                        tarihsel_havuz_9[col] = (
                            "" if col in ["Müşteri Kodu", "Müşteri Grubu"]
                            else 0.0
                        )
                st.caption(
                    f"Tarihsel havuz: {len(tarihsel_havuz_9):,} müşteri. "
                    "Ön izleme ilk 500 kaydı gösterir."
                )
                st.dataframe(
                    tarihsel_havuz_9[tarihsel_gosterim_kolonlari_9].head(500),
                    use_container_width=True,
                    hide_index=True,
                    height=300,
                    column_config={
                        col: st.column_config.NumberColumn(
                            col, format="%.0f"
                        )
                        for col in tarihsel_gosterim_kolonlari_9
                        if col not in ["Müşteri Kodu", "Müşteri Grubu"]
                    }
                )
            else:
                st.info(
                    "Henüz 2024–2025 tarihsel veri yok. Dosya yükleyin veya "
                    "seçili revizyondan bulut kaydını çağırın."
                )

            if client and rev_secenekleri:
                tarihsel_rev_id_9 = sayfa_aktif_revizyonunu_getir()
                tb1, tb2, tb3 = st.columns(3)

                if tarihsel_havuz_9.empty:
                    tb1.info("Excel için önce tarihsel veri yükleyin.")
                else:
                    tarihsel_excel_9 = io.BytesIO()
                    with pd.ExcelWriter(
                        tarihsel_excel_9, engine="openpyxl"
                    ) as writer:
                        tarihsel_havuz_9.to_excel(
                            writer, index=False, sheet_name="Tarihsel Kg"
                        )
                    tb1.download_button(
                        "📥 Tarihsel Havuzu Excel İndir",
                        data=tarihsel_excel_9.getvalue(),
                        file_name="buyume_tarihsel_2024_2025.xlsx",
                        mime=(
                            "application/vnd.openxmlformats-officedocument."
                            "spreadsheetml.sheet"
                        ),
                        use_container_width=True,
                        key="btn_buyume_tarihsel_excel_9"
                    )

                if tb2.button(
                    "💾 Tarihsel Havuzu Buluta Kaydet",
                    type="primary",
                    use_container_width=True,
                    disabled=tarihsel_havuz_9.empty,
                    key="btn_buyume_tarihsel_save_9"
                ):
                    try:
                        tarihsel_db_kolonlari_9 = (
                            data_ekran_sutunlari
                            + [f"2024 {ay} Kg" for ay in aylar]
                            + ["2024 Toplam Kg"]
                            + [f"2025 {ay} Kg" for ay in aylar]
                            + ["2025 Toplam Kg"]
                        )
                        tarihsel_records_9 = []
                        for _, row in tarihsel_havuz_9.iterrows():
                            rec_9 = {
                                col: json_uyumlu_deger(row.get(col))
                                for col in tarihsel_db_kolonlari_9
                                if col in tarihsel_havuz_9.columns
                            }
                            rec_9["revizyon_id"] = tarihsel_rev_id_9
                            tarihsel_records_9.append(rec_9)
                        client.table("data_tablosu").delete().eq(
                            "revizyon_id", tarihsel_rev_id_9
                        ).execute()
                        for i in range(0, len(tarihsel_records_9), 500):
                            client.table("data_tablosu").insert(
                                tarihsel_records_9[i:i + 500]
                            ).execute()
                        revizyonu_degistirildi_isaretle(tarihsel_rev_id_9)
                        st.success(
                            "2024–2025 tarihsel havuz seçili revizyona "
                            "mühürlendi."
                        )
                    except Exception as ex:
                        st.error(f"Tarihsel havuz buluta kaydedilemedi: {ex}")

                if tb3.button(
                    "🔄 Tarihsel Havuzu Buluttan Getir",
                    use_container_width=True,
                    key="btn_buyume_tarihsel_load_9"
                ):
                    try:
                        tarihsel_kayitlar_9 = (
                            supabase_revizyon_kayitlarini_getir(
                                "data_tablosu", tarihsel_rev_id_9
                            )
                        )
                        if tarihsel_kayitlar_9:
                            gelen_tarihsel_9 = pd.DataFrame(
                                tarihsel_kayitlar_9
                            ).drop(
                                columns=["id", "revizyon_id"],
                                errors="ignore"
                            )
                            gelen_tarihsel_9["Müşteri Kodu"] = (
                                gelen_tarihsel_9["Müşteri Kodu"]
                                .apply(guvenli_metin_kodu)
                            )
                            for yil_9 in ["2024", "2025"]:
                                yil_kolonlari_9 = [
                                    f"{yil_9} {ay} Kg" for ay in aylar
                                ]
                                for col in yil_kolonlari_9:
                                    if col not in gelen_tarihsel_9.columns:
                                        gelen_tarihsel_9[col] = 0.0
                                    gelen_tarihsel_9[col] = (
                                        gelen_tarihsel_9[col]
                                        .apply(guvenli_sayi).astype(float)
                                    )
                                gelen_tarihsel_9[f"{yil_9} Toplam Kg"] = (
                                    gelen_tarihsel_9[yil_kolonlari_9]
                                    .sum(axis=1)
                                )
                            st.session_state.data_sayfası_df = (
                                tarihsel_havuzu_sikistir_9(gelen_tarihsel_9)
                            )
                            st.session_state.buyume_tarihsel_upload_imzalari = {}
                            st.session_state.data_sayfası_df.to_parquet(
                                CACHE_DATA_MASTER, index=False
                            )
                            st.success(
                                "Tarihsel havuz seçili revizyondan getirildi."
                            )
                            st.rerun()
                        else:
                            st.warning(
                                "Seçili revizyonda 2024–2025 tarihsel kayıt "
                                "bulunamadı."
                            )
                    except Exception as ex:
                        st.error(f"Tarihsel havuz buluttan getirilemedi: {ex}")
            elif not client:
                st.warning("Bulut bağlantısı olmadığı için kayıt kullanılamıyor.")
            else:
                st.warning(
                    "Tarihsel havuzu kaydetmek için önce bir bulut revizyonu açın."
                )

        # Tarihsel veriler artık doğrudan bu sayfanın kendi havuzundan alınır.
        data_havuzu_9 = tarihsel_havuzu_sikistir_9(
            st.session_state.get("data_sayfası_df", pd.DataFrame())
        )
        st.session_state.data_sayfası_df = data_havuzu_9.copy()
        hist_24_9 = musteri_bazinda_ozetle_9(data_havuzu_9, "2024")
        hist_25_9 = musteri_bazinda_ozetle_9(data_havuzu_9, "2025")

        def tarihsel_grup_dagilimlarini_hazirla_9():
            """2024 ve 2025'in grup bazlı aylık dağılım ortalamasını üretir."""
            yil_dagilimlari = {}
            for yil, kaynak in [("2024", hist_24_9), ("2025", hist_25_9)]:
                aylik_kolonlar = [f"{yil} {ay} Kg" for ay in aylar]
                if kaynak is None or kaynak.empty:
                    grup_toplamlari = pd.DataFrame(
                        0.0, index=HEDEF_GRUPLAR_9, columns=aylik_kolonlar
                    )
                else:
                    work = kaynak.copy()
                    work["Müşteri Grubu"] = work["Müşteri Grubu"].apply(
                        grup_adi_standartlastir_9
                    )
                    for kolon in aylik_kolonlar:
                        if kolon not in work.columns:
                            work[kolon] = 0.0
                        work[kolon] = work[kolon].apply(guvenli_sayi).astype(float)
                    grup_toplamlari = (
                        work.groupby("Müşteri Grubu")[aylik_kolonlar]
                        .sum()
                        .reindex(HEDEF_GRUPLAR_9, fill_value=0.0)
                    )

                dagilimlar = {}
                for grup in HEDEF_GRUPLAR_9:
                    degerler = grup_toplamlari.loc[grup].to_numpy(dtype=float)
                    toplam = float(degerler.sum())
                    dagilimlar[grup] = (
                        degerler / toplam if toplam > 0 else np.zeros(len(aylar))
                    )
                yil_dagilimlari[yil] = dagilimlar

            return {
                grup: (
                    yil_dagilimlari["2024"][grup]
                    + yil_dagilimlari["2025"][grup]
                ) / 2.0
                for grup in HEDEF_GRUPLAR_9
            }

        def calisma_gunu_25to26_oranlari_9():
            takvim = st.session_state.get("takvim_verisi_yillar", pd.DataFrame())
            oranlar = {ay: 1.0 for ay in aylar}
            if takvim is None or takvim.empty or "YIL" not in takvim.columns:
                return oranlar

            yil_serisi = takvim["YIL"].astype(str).str.strip()
            satir_2025 = takvim[yil_serisi == "2025"]
            satir_2026 = takvim[yil_serisi == "2026"]
            if satir_2025.empty or satir_2026.empty:
                return oranlar

            for ay in aylar:
                gun_2025 = guvenli_sayi(satir_2025.iloc[0].get(ay, 0.0))
                gun_2026 = guvenli_sayi(satir_2026.iloc[0].get(ay, 0.0))
                oranlar[ay] = gun_2026 / gun_2025 if gun_2025 > 0 else 0.0
            return oranlar

        def detay_satirlarina_2026_tahmini_uygula_9(
            df_gercek, son_gerceklesen_ay, grup_dagilimlari, gun_oranlari
        ):
            """Sabit baz tahminini detay satırlarında hesaplayıp boş aylara yazar."""
            if df_gercek is None or df_gercek.empty:
                return pd.DataFrame(columns=NIHAI_SUTUNLAR_9)

            sonuc = df_gercek.copy().reindex(columns=NIHAI_SUTUNLAR_9)
            for kolon in AY_KOLONLARI_9:
                sonuc[kolon] = sonuc[kolon].apply(guvenli_sayi).astype(float)

            son_ay_index = aylar.index(son_gerceklesen_ay)
            gercek_kolonlar = [f"{ay} Kg" for ay in aylar[:son_ay_index + 1]]
            sabit_baz_toplami = sonuc[gercek_kolonlar].sum(axis=1).to_numpy(float)

            satir_gruplari = sonuc["Müşteri Grubu"].apply(
                grup_adi_standartlastir_9
            )
            grup_paydalari = {
                grup: float(grup_dagilimlari[grup][:son_ay_index + 1].sum())
                for grup in HEDEF_GRUPLAR_9
            }
            payda = satir_gruplari.map(grup_paydalari).fillna(0.0).to_numpy(float)
            yillik_baz = np.divide(
                sabit_baz_toplami,
                payda,
                out=np.zeros_like(sabit_baz_toplami, dtype=float),
                where=payda > 0
            )

            for hedef_index in range(son_ay_index + 1, len(aylar)):
                hedef_ay = aylar[hedef_index]
                onceki_uc_ay = [
                    f"{ay} Kg"
                    for ay in aylar[max(0, hedef_index - 3):hedef_index]
                ]
                hareket_toplami = (
                    sonuc[onceki_uc_ay].sum(axis=1).to_numpy(float)
                    if onceki_uc_ay else np.zeros(len(sonuc), dtype=float)
                )
                hedef_grup_payi = satir_gruplari.map({
                    grup: float(grup_dagilimlari[grup][hedef_index])
                    for grup in HEDEF_GRUPLAR_9
                }).fillna(0.0).to_numpy(float)
                calisma_gunu_orani = float(gun_oranlari.get(hedef_ay, 1.0))

                tahmin = yillik_baz * hedef_grup_payi * calisma_gunu_orani
                sonuc[f"{hedef_ay} Kg"] = np.where(
                    np.isclose(hareket_toplami, 0.0), 0.0, tahmin
                )

            sonuc["Toplam Kg"] = sonuc[AY_KOLONLARI_9].sum(axis=1)
            return sonuc[NIHAI_SUTUNLAR_9]

        ortalama_grup_dagilimlari_9 = tarihsel_grup_dagilimlarini_hazirla_9()
        gun_oranlari_25to26_9 = calisma_gunu_25to26_oranlari_9()

        mevcut_yillar_9 = []
        if any(f"2024 {m} Kg" in data_havuzu_9.columns for m in aylar):
            mevcut_yillar_9.append("2024")
        if any(f"2025 {m} Kg" in data_havuzu_9.columns for m in aylar):
            mevcut_yillar_9.append("2025")

        c_bilgi1, c_bilgi2, c_bilgi3 = st.columns(3)
        c_bilgi1.metric("Tarihsel havuz satırı", f"{len(data_havuzu_9):,}")
        c_bilgi2.metric("Hazır geçmiş yıllar", ", ".join(mevcut_yillar_9) if mevcut_yillar_9 else "Yok")
        c_bilgi3.metric(
            "2026 yükleme durumu",
            f"{len(st.session_state.get('df_2026_buyume_9', pd.DataFrame())):,} satır"
            if not st.session_state.get("df_2026_buyume_9", pd.DataFrame()).empty else "Bekleniyor"
        )

        if len(mevcut_yillar_9) < 2:
            st.warning(
                "2024 ve/veya 2025 Kg verisi tarihsel havuzda bulunamadı. "
                "Bu sayfanın üstündeki tarihsel veri alanından eksik yılı "
                "yükleyin veya seçili revizyonun bulut kaydını çağırın."
            )

        # ------------------------------------------------------------
        # 2026: SADECE BU SEKMEDE 31 KOLONLU DOSYA
        # ------------------------------------------------------------
        with st.expander("🚀 2026 Güncel Kg Dosyası (31 kolon)", expanded=True):
            st.markdown(
                "Dosya yüklendiğinde otomatik işlenir. 2024–2025 verileri yeniden istenmez ve "
                "ana havuzdaki geçmiş değerler değiştirilmez."
            )

            son_gerceklesen_ay_9 = st.selectbox(
                "📅 2026 Gerçekleşen Son Ay",
                aylar,
                key="son_gerceklesen_ay_2026_9",
                help=(
                    "Seçilen aya kadar dosyadaki Kg değerleri gerçekleşen olarak korunur. "
                    "Sonraki aylar detay satırı bazında tahmin edilerek ilgili Kg kolonlarına yazılır."
                )
            )
            up_2026_9 = st.file_uploader(
                "2026 güncel Kg dosyasını yükleyin",
                type=["xlsx", "xls", "csv"],
                key="up_2026_only_9"
            )

            if up_2026_9 is not None:
                upload_imza_9 = (
                    up_2026_9.name,
                    getattr(up_2026_9, "size", None),
                    getattr(up_2026_9, "file_id", None)
                )
                if upload_imza_9 != st.session_state.upload_2026_imza_9:
                    try:
                        df_raw_26_9 = oku_excel_csv_9(up_2026_9)
                        df_clean_26_9, eksik_26_9 = temizle_2026_31_kolon(df_raw_26_9)
                        st.session_state.df_2026_gercek_9 = df_clean_26_9.copy()
                        st.session_state.upload_2026_imza_9 = upload_imza_9
                        st.session_state.eksik_2026_kolonlari_9 = eksik_26_9
                        st.session_state.tahmin_uygulama_imza_9 = None
                        df_clean_26_9.to_parquet(CACHE_2026_GERCEK_B, index=False)
                    except Exception as ex:
                        st.error(f"2026 dosyası işlenemedi: {ex}")

            df_2026_gercek_9 = st.session_state.get(
                "df_2026_gercek_9", pd.DataFrame()
            )
            if not df_2026_gercek_9.empty:
                dagilim_imzasi_9 = tuple(
                    round(float(deger), 12)
                    for grup in HEDEF_GRUPLAR_9
                    for deger in ortalama_grup_dagilimlari_9[grup]
                )
                gun_imzasi_9 = tuple(
                    round(float(gun_oranlari_25to26_9[ay]), 12) for ay in aylar
                )
                tahmin_imzasi_9 = (
                    st.session_state.upload_2026_imza_9,
                    len(df_2026_gercek_9),
                    son_gerceklesen_ay_9,
                    dagilim_imzasi_9,
                    gun_imzasi_9
                )

                if (
                    tahmin_imzasi_9 != st.session_state.tahmin_uygulama_imza_9
                    or st.session_state.get("df_2026_buyume_9", pd.DataFrame()).empty
                ):
                    df_tahminli_2026_9 = detay_satirlarina_2026_tahmini_uygula_9(
                        df_2026_gercek_9,
                        son_gerceklesen_ay_9,
                        ortalama_grup_dagilimlari_9,
                        gun_oranlari_25to26_9
                    )
                    st.session_state.df_2026_buyume_9 = df_tahminli_2026_9
                    st.session_state.tahmin_uygulama_imza_9 = tahmin_imzasi_9
                    df_tahminli_2026_9.to_parquet(CACHE_2026_B, index=False)

                tahmin_aylari_9 = aylar[aylar.index(son_gerceklesen_ay_9) + 1:]
                st.success(
                    f"2026 dosyası işlendi: {len(df_2026_gercek_9):,} satır."
                )
                if tahmin_aylari_9:
                    st.info(
                        f"Gerçekleşen son ay: {son_gerceklesen_ay_9}. "
                        + ", ".join(f"{ay} Kg" for ay in tahmin_aylari_9)
                        + " kolonları sabit baz tahminiyle tamamlandı."
                    )
                eksik_26_9 = st.session_state.get("eksik_2026_kolonlari_9", [])
                if eksik_26_9:
                    st.warning(
                        "Dosyada bulunmadığı için boş oluşturulan kolonlar: "
                        + ", ".join(eksik_26_9)
                    )

            df_2026_raw_9 = st.session_state.get("df_2026_buyume_9", pd.DataFrame())
            if not df_2026_raw_9.empty:
                df_work_2026 = df_2026_raw_9.copy()
                kg_sutunlari = [c for c in df_work_2026.columns if "Kg" in c]
                toplam_dict = {}

                # Bütün Kg kolonları tek sayı motoruyla temizlenir.
                # Böylece 85.0 değeri 850'ye dönüşmez; boşlar ve gerçek 0'lar 0 kalır.
                for col in df_work_2026.columns:
                    if col in kg_sutunlari:
                        sayisal_seri = df_work_2026[col].apply(guvenli_sayi).astype(float)
                        df_work_2026[col] = sayisal_seri
                        toplam_dict[col] = sayisal_seri.sum()
                    elif col in ["Müşteri Kodu", "Müşteri Adı"]:
                        toplam_dict[col] = "🔥 GENEL TOPLAM"
                    else:
                        toplam_dict[col] = "-"

                genel_toplam_kg = guvenli_sayi(toplam_dict.get("Toplam Kg", 0.0))
                genel_toplam_metin = f"{genel_toplam_kg:,.0f}".replace(",", ".")
                st.metric(
                    label="📊 2026 YILI TOPLAM SEVKİYAT (Kg)",
                    value=f"{genel_toplam_metin} Kg"
                )

                df_gosterim = df_work_2026.copy()
                df_toplam_satiri = pd.DataFrame([toplam_dict])

                def kg_gosterim_formatla(value):
                    sayi = guvenli_sayi(value)
                    return f"{sayi:,.0f} Kg".replace(",", ".")

                # Sadece ekranda gösterilecek kopyalar metne çevrilir.
                # Hesaplamalarda kullanılan df_work_2026 sayısal kalır.
                df_gosterim_formatli = df_gosterim.copy()
                df_toplam_formatli = df_toplam_satiri.copy()

                for col in kg_sutunlari:
                    if col in df_gosterim_formatli.columns:
                        df_gosterim_formatli[col] = (
                            df_gosterim_formatli[col].map(kg_gosterim_formatla)
                        )
                    if col in df_toplam_formatli.columns:
                        df_toplam_formatli[col] = (
                            df_toplam_formatli[col].map(kg_gosterim_formatla)
                        )

                # Kaydırılabilir ana tablo. Styler kullanılmadığı için büyük veri hatası vermez.
                st.dataframe(
                    df_gosterim_formatli,
                    use_container_width=True,
                    hide_index=True,
                    height=430
                )

                # Genel toplam, kayan tablonun dışında ve hemen altında sabit görünür.
                st.markdown("##### 🔥 GENEL TOPLAM")
                st.dataframe(
                    df_toplam_formatli,
                    use_container_width=True,
                    hide_index=True,
                    height=85
                )

                if st.button("🧹 2026 yüklemesini hafızadan temizle", key="clear_2026_9"):
                    st.session_state.df_2026_buyume_9 = pd.DataFrame(columns=NIHAI_SUTUNLAR_9)
                    st.session_state.df_2026_gercek_9 = pd.DataFrame(columns=NIHAI_SUTUNLAR_9)
                    st.session_state.upload_2026_imza_9 = None
                    st.session_state.tahmin_uygulama_imza_9 = None
                    st.session_state.eksik_2026_kolonlari_9 = []
                    if os.path.exists(CACHE_2026_B):
                        os.remove(CACHE_2026_B)
                    if os.path.exists(CACHE_2026_GERCEK_B):
                        os.remove(CACHE_2026_GERCEK_B)
                    st.rerun()

        hist_26_9 = musteri_bazinda_ozetle_9(
            st.session_state.get("df_2026_buyume_9", pd.DataFrame()),
            "2026",
            kaynak_31_kolon=True
        )

        # ------------------------------------------------------------
        # MÜŞTERİ EVRENİ VE KİMLİKLERİ: YENİ-BÜTÇE MÜŞTERİ SAYFASINDAN
        # 2024/2025/2026 AYLIK DEĞERLER: İLGİLİ DATA KAYNAKLARINDAN
        # ------------------------------------------------------------
        musteri_kartlari_9 = st.session_state.get("musteri_ekran_df", pd.DataFrame()).copy()
        if not musteri_kartlari_9.empty and "Müşteri Kodu" in musteri_kartlari_9.columns:
            musteri_kartlari_9.columns = [str(c).strip() for c in musteri_kartlari_9.columns]
            musteri_kartlari_9["Müşteri Kodu"] = (
                musteri_kartlari_9["Müşteri Kodu"].apply(guvenli_metin_kodu)
            )
            musteri_kartlari_9 = (
                musteri_kartlari_9[musteri_kartlari_9["Müşteri Kodu"] != ""]
                .drop_duplicates(subset=["Müşteri Kodu"], keep="first")
                .reset_index(drop=True)
            )

            for c in KIMLIK_KOLONLARI_9:
                if c not in musteri_kartlari_9.columns:
                    musteri_kartlari_9[c] = "DİĞER" if c == "Müşteri Grubu" else ""

            df_calc_9 = musteri_kartlari_9[KIMLIK_KOLONLARI_9].copy()

            for yil, kaynak_df in [("2024", hist_24_9), ("2025", hist_25_9), ("2026", hist_26_9)]:
                aylik_kolonlar = [f"{yil} {m} Kg" for m in aylar]
                if kaynak_df is None or kaynak_df.empty:
                    for c in aylik_kolonlar:
                        df_calc_9[c] = 0.0
                    continue

                kaynak_aylik = kaynak_df.copy()
                kaynak_aylik["Müşteri Kodu"] = (
                    kaynak_aylik["Müşteri Kodu"].apply(guvenli_metin_kodu)
                )
                for c in aylik_kolonlar:
                    if c not in kaynak_aylik.columns:
                        kaynak_aylik[c] = 0.0
                    kaynak_aylik[c] = kaynak_aylik[c].apply(guvenli_sayi).astype(float)
                kaynak_aylik = kaynak_aylik.groupby("Müşteri Kodu", as_index=False)[aylik_kolonlar].sum()
                df_calc_9 = pd.merge(
                    df_calc_9, kaynak_aylik, on="Müşteri Kodu", how="left"
                )

            sayisal_kolonlar_9 = [
                f"{yil} {m} Kg" for yil in ["2024", "2025", "2026"] for m in aylar
            ]
            for c in sayisal_kolonlar_9:
                if c not in df_calc_9.columns:
                    df_calc_9[c] = 0.0
                df_calc_9[c] = df_calc_9[c].fillna(0.0).apply(guvenli_sayi)
        else:
            df_calc_9 = pd.DataFrame()

        # ------------------------------------------------------------
        # MÜŞTERİ BAZLI BÜYÜME MATRİSİ
        # ------------------------------------------------------------
        if df_calc_9.empty:
            st.info(
                "Büyüme matrisini oluşturmak için önce 👤 Yeni-Bütçe Müşteri "
                "Detay Yönetimi sayfasına müşteri verisi yükleyin veya buluttan çağırın."
            )
        else:
            st.subheader("📈 Müşteri Bazlı Büyüme Matrisi")
            st.caption(
                "Müşteri ve kimlik bilgileri Yeni-Bütçe Müşteri Detay Yönetimi "
                "sayfasından; karşılaştırmalar Ocak-Eylül döneminden alınır."
            )
            karsilastirma_ay_sayisi_9 = 9
            secili_aylar_9 = ilk_9_ay
            donem_24_adi_9 = "2024 ilk 9 ay desi"
            donem_25_adi_9 = "2025 ilk 9 ay desi"
            pay_25_adi_9 = "2025 % desi pay"
            yoy_adi_9 = "Y To Y Desi"

            for y in ["2024", "2025", "2026"]:
                for m in aylar:
                    c = f"{y} {m} Kg"
                    if c not in df_calc_9.columns:
                        df_calc_9[c] = 0.0
                    df_calc_9[c] = df_calc_9[c].apply(guvenli_sayi)

            df_calc_9[donem_24_adi_9] = df_calc_9[[f"2024 {m} Kg" for m in secili_aylar_9]].sum(axis=1)
            df_calc_9[donem_25_adi_9] = df_calc_9[[f"2025 {m} Kg" for m in secili_aylar_9]].sum(axis=1)

            # 2025 ilk 9 ay desi, Yeni-Bütçe sayfasındaki Ocak-Eylül Kg toplamıdır.
            kart_9_ay_kolonlari_9 = [
                f"{ay} Kg" for ay in ilk_9_ay if f"{ay} Kg" in musteri_kartlari_9.columns
            ]
            if kart_9_ay_kolonlari_9:
                kart_9_ay_df_9 = musteri_kartlari_9[["Müşteri Kodu"] + kart_9_ay_kolonlari_9].copy()
                for col in kart_9_ay_kolonlari_9:
                    kart_9_ay_df_9[col] = kart_9_ay_df_9[col].apply(guvenli_sayi).astype(float)
                kart_toplamlari_9 = (
                    kart_9_ay_df_9.set_index("Müşteri Kodu")[kart_9_ay_kolonlari_9]
                    .sum(axis=1)
                )
                kart_degerleri_9 = df_calc_9["Müşteri Kodu"].map(kart_toplamlari_9)
                df_calc_9[donem_25_adi_9] = kart_degerleri_9.where(
                    kart_degerleri_9.notna() & (kart_degerleri_9 != 0.0),
                    df_calc_9[donem_25_adi_9]
                )

            toplam_25_9 = df_calc_9[donem_25_adi_9].sum()
            df_calc_9[pay_25_adi_9] = (
                df_calc_9[donem_25_adi_9] / toplam_25_9 * 100.0 if toplam_25_9 > 0 else 0.0
            )
            df_calc_9[yoy_adi_9] = np.where(
                df_calc_9[donem_24_adi_9] > 0,
                (df_calc_9[donem_25_adi_9] / df_calc_9[donem_24_adi_9] - 1.0) * 100.0,
                0.0
            )

            final_rows_9 = []
            for _, row in df_calc_9.iterrows():
                mkod = guvenli_metin_kodu(row["Müşteri Kodu"])
                ayar = st.session_state.buyume_ayarlari.get(mkod, {})
                kullanilacak = guvenli_sayi(ayar.get("KULLANICAK BÜYÜME", 0.0))
                r = {
                    "Müşteri Kodu": mkod,
                    "Müşteri Adı": ilk_dolu_deger_9(row, ["Müşteri Adı"]),
                    "Müşteri Temsilcisi": ilk_dolu_deger_9(row, ["Müşteri Temsilcisi"]),
                    "Sap Kodu": ilk_dolu_deger_9(row, ["Sap Kodu"]),
                    "Durum": ilk_dolu_deger_9(row, ["Durum"], "GEÇERLİ"),
                    "Kayıt Tarihi": ilk_dolu_deger_9(row, ["Kayıt Tarihi"]),
                    "Müşteri Grubu": ilk_dolu_deger_9(row, ["Müşteri Grubu"], "DİĞER"),
                    donem_24_adi_9: row[donem_24_adi_9],
                    donem_25_adi_9: row[donem_25_adi_9],
                    pay_25_adi_9: row[pay_25_adi_9],
                    yoy_adi_9: row[yoy_adi_9],
                    "25 kullanılan büyüme": ayar.get("25 kullanılan büyüme", ""),
                    "KULLANICAK BÜYÜME": kullanilacak,
                    "Gelen Özet Bilgi": ayar.get("Gelen Özet Bilgi", ""),
                    "Müşteriden Gelen Büyüme": ayar.get("Müşteriden Gelen Büyüme", "")
                }
                for m in aylar:
                    r[m] = guvenli_sayi(ayar.get(m, kullanilacak))
                final_rows_9.append(r)

            ekran_kolonlari_9 = (
                KIMLIK_KOLONLARI_9 + aylar +
                [donem_24_adi_9, donem_25_adi_9, pay_25_adi_9, yoy_adi_9,
                 "25 kullanılan büyüme", "KULLANICAK BÜYÜME",
                 "Gelen Özet Bilgi", "Müşteriden Gelen Büyüme"]
            )
            df_final_b_9 = pd.DataFrame(final_rows_9).reindex(columns=ekran_kolonlari_9)
            kilitli_9 = [
                c for c in ekran_kolonlari_9
                if c not in ["25 kullanılan büyüme", "KULLANICAK BÜYÜME",
                             "Gelen Özet Bilgi", "Müşteriden Gelen Büyüme"]
            ]

            # KULLANICAK BÜYÜME değiştiği anda değeri müşteri bazında hafızaya al.
            # Sonraki otomatik Streamlit yenilemesinde aynı satırdaki Ocak-Aralık
            # kolonları yukarıdaki döngü tarafından bu yeni değere eşitlenir.
            buyume_editor_key_9 = "buyume_matris_editoru_musteri_detay_v2"
            musteri_kodlari_9 = df_final_b_9["Müşteri Kodu"].tolist()
            duzenlenebilir_alanlar_9 = [
                "25 kullanılan büyüme", "KULLANICAK BÜYÜME",
                "Gelen Özet Bilgi", "Müşteriden Gelen Büyüme"
            ]

            def buyume_matris_degisimini_uygula_9():
                editor_durumu = st.session_state.get(buyume_editor_key_9, {})
                for satir_no, degisiklikler in editor_durumu.get("edited_rows", {}).items():
                    try:
                        satir_no = int(satir_no)
                    except (TypeError, ValueError):
                        continue
                    if not 0 <= satir_no < len(musteri_kodlari_9):
                        continue

                    mkod = guvenli_metin_kodu(musteri_kodlari_9[satir_no])
                    mevcut_ayar = dict(st.session_state.buyume_ayarlari.get(mkod, {}))
                    for alan in duzenlenebilir_alanlar_9:
                        if alan not in degisiklikler:
                            continue
                        yeni_deger = degisiklikler[alan]
                        if alan == "KULLANICAK BÜYÜME":
                            yeni_deger = guvenli_sayi(yeni_deger)
                        mevcut_ayar[alan] = yeni_deger
                        if alan == "KULLANICAK BÜYÜME":
                            for ay in aylar:
                                mevcut_ayar[ay] = yeni_deger
                    st.session_state.buyume_ayarlari[mkod] = mevcut_ayar

            def guncel_buyume_matrisini_hazirla_9():
                guncel_df = df_final_b_9.copy()
                satir_ayarlari = [
                    st.session_state.buyume_ayarlari.get(
                        guvenli_metin_kodu(mkod), {}
                    )
                    for mkod in musteri_kodlari_9
                ]
                kullanilacak_degerler = np.array([
                    guvenli_sayi(ayar.get("KULLANICAK BÜYÜME", 0.0))
                    for ayar in satir_ayarlari
                ], dtype=float)

                guncel_df["KULLANICAK BÜYÜME"] = kullanilacak_degerler
                for ay in aylar:
                    guncel_df[ay] = np.array([
                        guvenli_sayi(
                            ayar.get(ay, kullanilacak)
                        )
                        for ayar, kullanilacak in zip(
                            satir_ayarlari, kullanilacak_degerler
                        )
                    ], dtype=float)
                for alan in [
                    "25 kullanılan büyüme", "Gelen Özet Bilgi",
                    "Müşteriden Gelen Büyüme"
                ]:
                    guncel_df[alan] = [
                        ayar.get(alan, "") for ayar in satir_ayarlari
                    ]
                return guncel_df

            # Fragment içindeki hücre değişiklikleri yalnızca bu tabloyu yeniler;
            # 9 sekme ve ağır sezon hesapları yeniden çalıştırılmaz.
            fragment_decorator_9 = getattr(st, "fragment", lambda func: func)

            @fragment_decorator_9
            def buyume_matris_editorunu_goster_9():
                st.data_editor(
                    guncel_buyume_matrisini_hazirla_9(),
                    use_container_width=True,
                    height=430,
                    disabled=kilitli_9,
                    column_config={
                        donem_24_adi_9: st.column_config.NumberColumn(
                            donem_24_adi_9, format="%.0f"
                        ),
                        donem_25_adi_9: st.column_config.NumberColumn(
                            donem_25_adi_9, format="%.0f"
                        ),
                        pay_25_adi_9: st.column_config.NumberColumn(
                            pay_25_adi_9, format="%.2f%%"
                        ),
                        yoy_adi_9: st.column_config.NumberColumn(
                            yoy_adi_9, format="%.2f%%"
                        ),
                        "KULLANICAK BÜYÜME": st.column_config.NumberColumn(
                            "KULLANICAK BÜYÜME", format="%.2f%%"
                        ),
                        **{
                            m: st.column_config.NumberColumn(m, format="%.2f%%")
                            for m in aylar
                        }
                    },
                    key=buyume_editor_key_9,
                    on_change=buyume_matris_degisimini_uygula_9
                )

            buyume_matris_editorunu_goster_9()

            # Kayıt düğmeleri her zaman Session State'teki en güncel tabloyu kullanır.
            edited_b_matris = guncel_buyume_matrisini_hazirla_9()

            # ------------------------------------------------------------
            # MÜŞTERİ GRUBU SEZON DAĞILIMLARI
            # ------------------------------------------------------------
            st.markdown("---")
            st.subheader("📊 Müşteri Grubu Sezonluk Dağılım Matrisi (%)")

            grup_calc_9 = df_calc_9.copy()
            grup_calc_9["Müşteri Grubu"] = grup_calc_9["Müşteri Grubu"].apply(
                lambda v: temiz_metin_9(v, "DİĞER").upper()
            )
            grup_calc_9["Müşteri Grubu"] = grup_calc_9["Müşteri Grubu"].where(
                grup_calc_9["Müşteri Grubu"].isin(["MP", "HOROZ CÜZDAN"]), "DİĞER"
            )
            hedef_gruplar_9 = ["MP", "HOROZ CÜZDAN", "DİĞER"]

            grup_totals_9 = {}
            for y in ["2024", "2025", "2026"]:
                y_cols = [f"{y} {m} Kg" for m in aylar]
                grup_totals_9[y] = grup_calc_9.groupby("Müşteri Grubu")[y_cols].sum()

            son_ay_index_9 = aylar.index(
                st.session_state.get("son_gerceklesen_ay_2026_9", "Ağustos")
            )
            gerceklesen_aylar_9 = aylar[:son_ay_index_9 + 1]
            tahmini_aylar_9 = aylar[son_ay_index_9 + 1:]

            if gerceklesen_aylar_9:
                st.success("2026 gerçekleşen kabul edilen aylar: " + ", ".join(gerceklesen_aylar_9))
            if tahmini_aylar_9:
                st.info(
                    "2026 tahmini tamamlanan aylar: " + ", ".join(tahmini_aylar_9)
                    + ". Tahmini aylarda 2024 ve 2025 aylık dağılım yüzdelerinin ortalaması kullanılır."
                )

            sezon_tabs_9 = st.tabs([
                "📅 2024 Dağılımı",
                "📅 2025 Dağılımı",
                "📅 2026 Gerçekleşen + Tahmin"
            ])

            def grup_aylik_kg_9(yil, grup, ay):
                tablo = grup_totals_9.get(yil, pd.DataFrame())
                kolon = f"{yil} {ay} Kg"
                if not tablo.empty and grup in tablo.index and kolon in tablo.columns:
                    return guvenli_sayi(tablo.loc[grup, kolon])
                return 0.0

            def grup_yillik_dagilim_9(yil, grup):
                aylik_kg = {ay: grup_aylik_kg_9(yil, grup, ay) for ay in aylar}
                toplam_kg = sum(aylik_kg.values())
                if toplam_kg <= 0:
                    return {ay: 0.0 for ay in aylar}
                return {ay: aylik_kg[ay] / toplam_kg * 100.0 for ay in aylar}

            for tab_index_9, target_yil_9 in enumerate(["2024", "2025"]):
                with sezon_tabs_9[tab_index_9]:
                    sezon_rows_9 = []
                    for grp in hedef_gruplar_9:
                        yuzdeler_9 = grup_yillik_dagilim_9(target_yil_9, grp)
                        row_9 = {"Müşteri Grubu": grp, **yuzdeler_9}
                        row_9["Toplam (%)"] = sum(yuzdeler_9.values())
                        sezon_rows_9.append(row_9)

                    st.dataframe(
                        pd.DataFrame(sezon_rows_9),
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            **{
                                ay: st.column_config.NumberColumn(ay, format="%.3f%%")
                                for ay in aylar
                            },
                            "Toplam (%)": st.column_config.NumberColumn(
                                "Toplam (%)", format="%.3f%%"
                            )
                        }
                    )

            with sezon_tabs_9[2]:
                sezon_rows_2026_9 = []

                for grp in hedef_gruplar_9:
                    dagilim_2024_9 = grup_yillik_dagilim_9("2024", grp)
                    dagilim_2025_9 = grup_yillik_dagilim_9("2025", grp)

                    tahmini_yuzdeler_9 = {
                        ay: (dagilim_2024_9[ay] + dagilim_2025_9[ay]) / 2.0
                        for ay in tahmini_aylar_9
                    }
                    tahmini_yuzde_toplami_9 = sum(tahmini_yuzdeler_9.values())
                    gerceklesen_aylara_kalan_9 = max(
                        0.0, 100.0 - tahmini_yuzde_toplami_9
                    )

                    gerceklesen_kg_9 = {
                        ay: grup_aylik_kg_9("2026", grp, ay)
                        for ay in gerceklesen_aylar_9
                    }
                    gerceklesen_toplam_kg_9 = sum(gerceklesen_kg_9.values())

                    if gerceklesen_toplam_kg_9 > 0:
                        gerceklesen_yuzdeler_9 = {
                            ay: (
                                gerceklesen_kg_9[ay]
                                / gerceklesen_toplam_kg_9
                                * gerceklesen_aylara_kalan_9
                            )
                            for ay in gerceklesen_aylar_9
                        }
                    elif gerceklesen_aylar_9:
                        esit_pay_9 = (
                            gerceklesen_aylara_kalan_9 / len(gerceklesen_aylar_9)
                        )
                        gerceklesen_yuzdeler_9 = {
                            ay: esit_pay_9 for ay in gerceklesen_aylar_9
                        }
                    else:
                        gerceklesen_yuzdeler_9 = {}

                    row_2026_9 = {"Müşteri Grubu": grp}
                    for ay in aylar:
                        row_2026_9[ay] = (
                            tahmini_yuzdeler_9[ay]
                            if ay in tahmini_yuzdeler_9
                            else gerceklesen_yuzdeler_9.get(ay, 0.0)
                        )

                    toplam_once_9 = sum(row_2026_9[ay] for ay in aylar)
                    duzeltme_ayi_9 = (
                        gerceklesen_aylar_9[-1]
                        if gerceklesen_aylar_9 else aylar[-1]
                    )
                    row_2026_9[duzeltme_ayi_9] += 100.0 - toplam_once_9
                    row_2026_9["Toplam (%)"] = sum(
                        row_2026_9[ay] for ay in aylar
                    )
                    sezon_rows_2026_9.append(row_2026_9)

                st.dataframe(
                    pd.DataFrame(sezon_rows_2026_9),
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        **{
                            ay: st.column_config.NumberColumn(ay, format="%.3f%%")
                            for ay in aylar
                        },
                        "Toplam (%)": st.column_config.NumberColumn(
                            "Toplam (%)", format="%.3f%%"
                        )
                    }
                )

            # ------------------------------------------------------------
            # BÜYÜME AYARLARINI HAFIZAYA / BULUTA KAYDET
            # ------------------------------------------------------------
            st.markdown("---")
            cb_1, cb_2, cb_3 = st.columns(3)

            if cb_1.button(
                "💾 Büyüme Kartlarını Hafızaya Kaydet",
                type="primary",
                use_container_width=True,
                key="btn_b_hfz_save"
            ):
                for _, row in edited_b_matris.iterrows():
                    mk = guvenli_metin_kodu(row["Müşteri Kodu"])
                    st.session_state.buyume_ayarlari[mk] = {
                        "25 kullanılan büyüme": row.get("25 kullanılan büyüme", ""),
                        "KULLANICAK BÜYÜME": guvenli_sayi(
                            row.get("KULLANICAK BÜYÜME", 0.0)
                        ),
                        **{
                            ay: guvenli_sayi(row.get(ay, 0.0))
                            for ay in aylar
                        },
                        "Gelen Özet Bilgi": row.get("Gelen Özet Bilgi", ""),
                        "Müşteriden Gelen Büyüme": row.get(
                            "Müşteriden Gelen Büyüme", ""
                        )
                    }
                st.success("Büyüme stratejileri hafızaya kaydedildi ve 12 aya eşit uygulandı.")
                st.rerun()

            if rev_secenekleri:
                r_id_b = sayfa_aktif_revizyonunu_getir(cb_2)

                if cb_2.button(
                    "💾 Büyüme Verilerini Buluta Gönder",
                    use_container_width=True,
                    key="btn_b_cloud_save"
                ):
                    izin_verilen_b_db = [
                        "Müşteri Kodu", "Müşteri Adı", "Müşteri Temsilcisi",
                        "Sap Kodu", "Durum", "Kayıt Tarihi", "Müşteri Grubu",
                        "25 kullanılan büyüme", "KULLANICAK BÜYÜME",
                        "Gelen Özet Bilgi", "Müşteriden Gelen Büyüme"
                    ]
                    b_records = [
                        {
                            col: json_uyumlu_deger(row[col])
                            for col in izin_verilen_b_db if col in row.index
                        }
                        for _, row in edited_b_matris.iterrows()
                    ]
                    for record, (_, row) in zip(
                        b_records, edited_b_matris.iterrows()
                    ):
                        record["revizyon_id"] = r_id_b
                        record[BUYUME_AYLIK_ORANLAR_DB] = {
                            ay: guvenli_sayi(row.get(ay, 0.0))
                            for ay in aylar
                        }

                    client.table("buyume_tablosu").delete().eq(
                        "revizyon_id", r_id_b
                    ).execute()
                    for i in range(0, len(b_records), 500):
                        client.table("buyume_tablosu").insert(
                            b_records[i:i + 500]
                        ).execute()
                    revizyonu_degistirildi_isaretle(r_id_b)
                    st.success("🎉 Müşteri büyüme oranları başarıyla kaydedildi.")

                if cb_3.button(
                    "🔄 Dosyasız Buluttan Büyüme Kartlarını Çek",
                    use_container_width=True,
                    key="btn_b_cloud_load"
                ):
                    b_res = client.table("buyume_tablosu").select("*").eq(
                        "revizyon_id", r_id_b
                    ).execute()
                    if b_res.data:
                        gelen_b_df = pd.DataFrame(b_res.data)
                        for _, row in gelen_b_df.iterrows():
                            mk = guvenli_metin_kodu(row.get("Müşteri Kodu"))
                            st.session_state.buyume_ayarlari[mk] = {
                                "25 kullanılan büyüme": row.get(
                                    "25 kullanılan büyüme", ""
                                ),
                                "KULLANICAK BÜYÜME": guvenli_sayi(
                                    row.get("KULLANICAK BÜYÜME", 0.0)
                                ),
                                **{
                                    ay: guvenli_sayi(
                                        (
                                            row.get(BUYUME_AYLIK_ORANLAR_DB, {})
                                            if isinstance(
                                                row.get(
                                                    BUYUME_AYLIK_ORANLAR_DB, {}
                                                ), dict
                                            ) else {}
                                        ).get(
                                            ay,
                                            row.get("KULLANICAK BÜYÜME", 0.0)
                                        )
                                    )
                                    for ay in aylar
                                },
                                "Gelen Özet Bilgi": row.get(
                                    "Gelen Özet Bilgi", ""
                                ),
                                "Müşteriden Gelen Büyüme": row.get(
                                    "Müşteriden Gelen Büyüme", ""
                                )
                            }
                        st.success("🎉 Büyüme kartları buluttan getirildi.")
                        st.rerun()
                    else:
                        st.warning(
                            "Seçili revizyonda kayıtlı büyüme kartı bulunamadı."
                        )

# ------------------------------------------------------------
# 9 / 13. SAYFA: YIL KAPANIŞ VE AYNI HESABIN DESİ TAHMİNLEME GÖRÜNÜMÜ
# ------------------------------------------------------------
if sekme_acik_mi[8] or sekme_acik_mi[12]:
    with sekmeler[8]:
        desi_tahmin_modu = sekme_acik_mi[12]
        st.title(
            "🔮 Desi Tahminleme"
            if desi_tahmin_modu else
            "🏁 Yıl Kapanış ve Sezon Dağılımı"
        )
        st.caption(
            "Verisi bulunan iki yılı seçerek MP, HOROZ CÜZDAN ve DİĞER "
            "gruplarının aylık paylarını ve iki yılın aritmetik ortalamasını "
            "hesaplayabilirsiniz. Gerçekleşen dönem toplamı seçilen son ayın "
            "kendi sütununda gösterilir."
        )

        aktif_yk_rev_id = sayfa_aktif_revizyonunu_getir()

        # Data_New başka bir sekmede olduğu için o sayfa açılmamış olsa bile
        # seçili revizyonun operasyon detayını burada bir kez otomatik hazırla.
        yerel_data_new = st.session_state.get(
            "data_new_girdi_df", pd.DataFrame()
        )
        if yerel_data_new.empty:
            yerel_data_new = st.session_state.get(
                "data_new_sonuc_df", pd.DataFrame()
            )
        detay_upload_hazir = not st.session_state.get(
            "yil_kapanis_detay_upload_df", pd.DataFrame()
        ).empty
        if (
            client
            and aktif_yk_rev_id
            and yerel_data_new.empty
            and not detay_upload_hazir
            and st.session_state.get(
                "yil_kapanis_data_new_bulut_revizyon"
            ) != aktif_yk_rev_id
        ):
            try:
                with st.spinner(
                    "Data_New detayları seçili revizyondan hazırlanıyor..."
                ):
                    data_new_kayitlari = supabase_revizyon_kayitlarini_getir(
                        "data_new_tablosu", aktif_yk_rev_id
                    )
                st.session_state.yil_kapanis_data_new_bulut_df = (
                    pd.DataFrame(data_new_kayitlari).drop(
                        columns=["id", "revizyon_id"], errors="ignore"
                    )
                    if data_new_kayitlari else pd.DataFrame()
                )
            except Exception:
                st.session_state.yil_kapanis_data_new_bulut_df = pd.DataFrame()
            st.session_state.yil_kapanis_data_new_bulut_revizyon = (
                aktif_yk_rev_id
            )

        # Mevcut uygulama kaynakları otomatik kullanılır. Ekrandan yüklenen veya
        # buluttan getirilen kg_musteri kaydı en yüksek önceliğe sahiptir.
        tarihsel_kg_kaynak = kg_musteri_verisini_hazirla(
            st.session_state.get("data_sayfası_df", pd.DataFrame())
        )
        guncel_2026_kaynak = kg_musteri_verisini_hazirla(
            st.session_state.get("df_2026_buyume_9", pd.DataFrame()),
            varsayilan_yil=2026
        )

        with st.expander("📥 Müşteri-Kg veri kaynağı", expanded=True):
            yu1, yu2 = st.columns([1, 3])
            yukleme_yili = yu1.number_input(
                "Dosyada Yıl yoksa kullanılacak yıl",
                min_value=2000,
                max_value=2100,
                value=2025,
                step=1,
                key="yil_kapanis_upload_yili"
            )
            yil_kapanis_upload = yu2.file_uploader(
                "Müşteri-Kg dosyasını yükleyin",
                type=["xlsx", "xls", "csv"],
                key="yil_kapanis_kg_upload",
                help=(
                    "Beklenen temel alanlar: Yıl, Müşteri Kodu, Müşteri Grubu "
                    "ve Ocak Kg–Aralık Kg. Yıl yoksa soldaki yıl kullanılır. "
                    "2024 Ocak Kg gibi yıl önekli kolonlar da kabul edilir."
                )
            )
            if yil_kapanis_upload is not None:
                try:
                    upload_imzasi = (
                        int(yukleme_yili),
                        yuklenen_dosya_imzasi(yil_kapanis_upload)
                    )
                    if upload_imzasi != st.session_state.yil_kapanis_upload_imzasi:
                        ham_kg = yuklenen_tabloyu_oku(yil_kapanis_upload)
                        yeni_kg = kg_musteri_verisini_hazirla(
                            ham_kg, varsayilan_yil=int(yukleme_yili)
                        )
                        yeni_detay = yil_kapanis_detayini_hazirla(
                            ham_kg, varsayilan_yil=int(yukleme_yili)
                        )
                        if yeni_kg.empty:
                            raise ValueError(
                                "Dosyada kullanılabilir müşteri ve aylık Kg "
                                "verisi bulunamadı."
                            )
                        yeni_yillar = set(
                            pd.to_numeric(yeni_kg["Yıl"], errors="coerce")
                            .dropna().astype(int).tolist()
                        )
                        mevcut_kg = st.session_state.yil_kapanis_kg_df.copy()
                        if not mevcut_kg.empty:
                            mevcut_yil_serisi = pd.to_numeric(
                                mevcut_kg["Yıl"], errors="coerce"
                            )
                            mevcut_kg = mevcut_kg[
                                ~mevcut_yil_serisi.isin(yeni_yillar)
                            ]
                        st.session_state.yil_kapanis_kg_df = (
                            kg_musteri_kaynaklarini_birlestir(
                                mevcut_kg, yeni_kg
                            )
                        )
                        st.session_state.yil_kapanis_detay_upload_df = (
                            yeni_detay
                        )
                        st.session_state.yil_kapanis_upload_imzasi = upload_imzasi
                        st.success(
                            f"{len(yeni_kg):,} müşteri-yıl kaydı işlendi. "
                            f"Yıllar: {', '.join(map(str, sorted(yeni_yillar)))}. "
                            f"Detay satırı: {len(yeni_detay):,}."
                        )
                except Exception as ex:
                    st.error(f"Müşteri-Kg dosyası işlenemedi: {ex}")

            bulut1, bulut2 = st.columns(2)
            buluttan_getir = bulut1.button(
                "🔄 Kg ve Yıl Kapanışı Buluttan Getir",
                use_container_width=True,
                disabled=(not client or not aktif_yk_rev_id),
                key="btn_yil_kapanis_cloud_load"
            )
            hafizayi_temizle = bulut2.button(
                "🧹 Yıl Kapanış Hafızasını Temizle",
                use_container_width=True,
                key="btn_yil_kapanis_clear"
            )

            if hafizayi_temizle:
                st.session_state.yil_kapanis_kg_df = pd.DataFrame(
                    columns=kg_musteri_sutunlari
                )
                st.session_state.yil_kapanis_upload_imzasi = None
                st.session_state.yil_kapanis_kayitli_sonuc_df = pd.DataFrame(
                    columns=yil_kapanis_sonuc_sutunlari
                )
                st.session_state.yil_kapanis_bulut_ayarlari = {}
                st.session_state.yil_kapanis_detay_upload_df = pd.DataFrame(
                    columns=yil_kapanis_detay_sutunlari
                )
                st.session_state.yil_kapanis_detay_bulut_df = pd.DataFrame(
                    columns=yil_kapanis_detay_sutunlari
                )
                st.session_state.yil_kapanis_data_new_bulut_df = pd.DataFrame()
                st.session_state.yil_kapanis_data_new_bulut_revizyon = None
                st.rerun()

            if buluttan_getir:
                try:
                    try:
                        data_new_kayitlari = (
                            supabase_revizyon_kayitlarini_getir(
                                "data_new_tablosu", aktif_yk_rev_id
                            )
                        )
                        st.session_state.yil_kapanis_data_new_bulut_df = (
                            pd.DataFrame(data_new_kayitlari).drop(
                                columns=["id", "revizyon_id"],
                                errors="ignore"
                            )
                            if data_new_kayitlari else pd.DataFrame()
                        )
                        st.session_state[
                            "yil_kapanis_data_new_bulut_revizyon"
                        ] = aktif_yk_rev_id
                    except Exception:
                        st.session_state.yil_kapanis_data_new_bulut_df = (
                            pd.DataFrame()
                        )

                    kg_kayitlari = []
                    try:
                        kg_kayitlari = supabase_revizyon_kayitlarini_getir(
                            KG_MUSTERI_DB_TABLOSU, aktif_yk_rev_id
                        )
                    except Exception:
                        kg_kayitlari = []

                    if kg_kayitlari:
                        bulut_kg = pd.DataFrame(kg_kayitlari).drop(
                            columns=["id", "revizyon_id", "created_at", "updated_at"],
                            errors="ignore"
                        )
                        st.session_state.yil_kapanis_kg_df = (
                            kg_musteri_verisini_hazirla(bulut_kg)
                        )
                    else:
                        # Yeni kg_musteri tablosu henüz kullanılmadıysa önceki
                        # tarihsel data_tablosu kaydı da kaynak olarak kabul edilir.
                        eski_kayitlar = supabase_revizyon_kayitlarini_getir(
                            "data_tablosu", aktif_yk_rev_id
                        )
                        if eski_kayitlar:
                            eski_kg = pd.DataFrame(eski_kayitlar).drop(
                                columns=["id", "revizyon_id"], errors="ignore"
                            )
                            st.session_state.yil_kapanis_kg_df = (
                                kg_musteri_verisini_hazirla(eski_kg)
                            )

                    kapanis_kayitlari = []
                    try:
                        kapanis_kayitlari = supabase_revizyon_kayitlarini_getir(
                            YIL_KAPANIS_DB_TABLOSU, aktif_yk_rev_id
                        )
                    except Exception:
                        kapanis_kayitlari = []
                    if kapanis_kayitlari:
                        kapanis_raw = pd.DataFrame(kapanis_kayitlari)
                        ilk_kayit = kapanis_raw.iloc[0]
                        st.session_state.yil_kapanis_bulut_ayarlari = {
                            "yil_1": guvenli_tamsayi(
                                ilk_kayit.get("Yıl 1"), nullable=False
                            ),
                            "yil_2": guvenli_tamsayi(
                                ilk_kayit.get("Yıl 2"), nullable=False
                            ),
                            "son_ay": temiz_metin(
                                ilk_kayit.get("Gerçekleşen Son Ay"), "Ağustos"
                            ),
                            "kapanis_yili": guvenli_tamsayi(
                                ilk_kayit.get("Kapanış Yılı"), nullable=True
                            )
                        }
                        st.session_state.yil_kapanis_kayitli_sonuc_df = (
                            kapanis_raw.drop(
                                columns=[
                                    "id", "revizyon_id", "Yıl 1", "Yıl 2",
                                    "Gerçekleşen Son Ay", "Kapanış Yılı",
                                    "created_at", "updated_at"
                                ],
                                errors="ignore"
                            ).reindex(columns=yil_kapanis_sonuc_sutunlari)
                        )

                    detay_kayitlari = []
                    try:
                        detay_kayitlari = supabase_revizyon_kayitlarini_getir(
                            YIL_KAPANIS_DETAY_DB_TABLOSU, aktif_yk_rev_id
                        )
                    except Exception:
                        detay_kayitlari = []
                    if detay_kayitlari:
                        detay_raw = pd.DataFrame(detay_kayitlari).drop(
                            columns=[
                                "id", "revizyon_id", "created_at", "updated_at"
                            ],
                            errors="ignore"
                        )
                        st.session_state.yil_kapanis_detay_bulut_df = (
                            yil_kapanis_detayini_hazirla(detay_raw)
                        )
                    else:
                        st.session_state.yil_kapanis_detay_bulut_df = (
                            pd.DataFrame(columns=yil_kapanis_detay_sutunlari)
                        )
                    st.session_state.yil_kapanis_detay_manuel_ayarlari = {}
                    st.success(
                        "Kayıtlı müşteri-Kg, yıl kapanış ve detay verileri "
                        "getirildi."
                    )
                    st.rerun()
                except Exception as ex:
                    st.error(f"Yıl kapanış verileri buluttan getirilemedi: {ex}")

        kg_kaynak = kg_musteri_kaynaklarini_birlestir(
            tarihsel_kg_kaynak,
            guncel_2026_kaynak,
            st.session_state.get("yil_kapanis_kg_df", pd.DataFrame())
        )
        mevcut_yillar = sorted({
            int(yil) for yil in pd.to_numeric(
                kg_kaynak.get("Yıl", pd.Series(dtype=float)), errors="coerce"
            ).dropna().tolist()
        })

        if kg_kaynak.empty or len(mevcut_yillar) < 2:
            st.warning(
                "Yıl kapanışı için en az iki farklı yılın müşteri-Kg verisi "
                "gerekir. Dosya yükleyin, Büyüme sayfasındaki tarihsel havuzu "
                "doldurun veya bulut kaydını çağırın."
            )
        else:
            kaynak_ozet = (
                kg_kaynak.groupby("Yıl")["Müşteri Kodu"]
                .nunique().reset_index(name="Müşteri Sayısı")
            )
            st.dataframe(
                kaynak_ozet,
                use_container_width=True,
                hide_index=True,
                height=min(220, 38 * len(kaynak_ozet) + 40)
            )

            kayitli_ayar = st.session_state.get(
                "yil_kapanis_bulut_ayarlari", {}
            )
            varsayilan_yil_1 = int(kayitli_ayar.get("yil_1", mevcut_yillar[-2]))
            varsayilan_yil_2 = int(kayitli_ayar.get("yil_2", mevcut_yillar[-1]))
            if varsayilan_yil_1 not in mevcut_yillar:
                varsayilan_yil_1 = mevcut_yillar[-2]
            if varsayilan_yil_2 not in mevcut_yillar:
                varsayilan_yil_2 = mevcut_yillar[-1]
            varsayilan_son_ay = kayitli_ayar.get(
                "son_ay",
                st.session_state.get("son_gerceklesen_ay_2026_9", "Ağustos")
            )
            if varsayilan_son_ay not in aylar:
                varsayilan_son_ay = "Ağustos"

            if (
                "yil_kapanis_yil_1" not in st.session_state
                or st.session_state.yil_kapanis_yil_1 not in mevcut_yillar
            ):
                st.session_state.yil_kapanis_yil_1 = varsayilan_yil_1
            if (
                "yil_kapanis_yil_2" not in st.session_state
                or st.session_state.yil_kapanis_yil_2 not in mevcut_yillar
            ):
                st.session_state.yil_kapanis_yil_2 = varsayilan_yil_2
            if "yil_kapanis_son_ay" not in st.session_state:
                st.session_state.yil_kapanis_son_ay = varsayilan_son_ay

            ys1, ys2, ys3 = st.columns(3)
            yil_1 = ys1.selectbox(
                "Karşılaştırılacak 1. yıl",
                mevcut_yillar,
                key="yil_kapanis_yil_1"
            )
            yil_2 = ys2.selectbox(
                "Karşılaştırılacak 2. yıl",
                mevcut_yillar,
                key="yil_kapanis_yil_2"
            )
            son_gerceklesen_ay = ys3.selectbox(
                "Gerçekleşen son ay",
                aylar,
                key="yil_kapanis_son_ay"
            )

            if yil_1 == yil_2:
                st.error("Ortalama hesabı için iki farklı yıl seçin.")
            else:
                matris_1, matris_2, ortalama_sonuc = (
                    yil_kapanis_ortalamasini_hesapla(
                        kg_kaynak, yil_1, yil_2, son_gerceklesen_ay
                    )
                )
                yuzde_config = {
                    ay: st.column_config.NumberColumn(ay, format="%.2f%%")
                    for ay in aylar
                }

                st.subheader(f"📊 {yil_1} Aylık Dağılımı")
                st.dataframe(
                    matris_1,
                    use_container_width=True,
                    hide_index=True,
                    column_config=yuzde_config
                )
                st.subheader(f"📊 {yil_2} Aylık Dağılımı")
                st.dataframe(
                    matris_2,
                    use_container_width=True,
                    hide_index=True,
                    column_config=yuzde_config
                )

                tamamlanacak_aylar = aylar[
                    aylar.index(son_gerceklesen_ay) + 1:
                ]
                st.subheader("📌 ORTALAMA")
                st.caption(
                    f"Gerçekleşen dönem: Ocak–{son_gerceklesen_ay}. "
                    + (
                        "Yılı tamamlamak için kullanılacak aylar: "
                        + ", ".join(tamamlanacak_aylar)
                        if tamamlanacak_aylar else
                        "Yılın 12 ayı da gerçekleşmiştir."
                    )
                )

                ortalama_gosterim_satirlari = []
                for _, row in ortalama_sonuc.iterrows():
                    grup = row["Müşteri Grubu"]
                    toplam_satiri = {
                        "Müşteri Grubu": (
                            f"{grup} — Ocak–{son_gerceklesen_ay} Toplamı"
                        ),
                        **{ay: np.nan for ay in aylar}
                    }
                    toplam_satiri[son_gerceklesen_ay] = row[
                        "Gerçekleşen Dönem Payı (%)"
                    ]
                    ortalama_gosterim_satirlari.append(toplam_satiri)
                    ortalama_gosterim_satirlari.append({
                        "Müşteri Grubu": grup,
                        **{ay: row[f"{ay} (%)"] for ay in aylar}
                    })
                ortalama_gosterim = pd.DataFrame(
                    ortalama_gosterim_satirlari,
                    columns=["Müşteri Grubu"] + aylar
                )
                st.dataframe(
                    ortalama_gosterim,
                    use_container_width=True,
                    hide_index=True,
                    column_config=yuzde_config
                )

                # Detay kaynağı önceliği: bu sayfadaki yükleme, Data_New,
                # ardından seçili revizyondan çağrılan bulut kaydıdır.
                detay_upload_kaynak = st.session_state.get(
                    "yil_kapanis_detay_upload_df", pd.DataFrame()
                )
                data_new_ham_kaynak = st.session_state.get(
                    "data_new_girdi_df", pd.DataFrame()
                )
                if data_new_ham_kaynak.empty:
                    data_new_ham_kaynak = st.session_state.get(
                        "data_new_sonuc_df", pd.DataFrame()
                    )
                data_new_kaynak_adi = "Data_New giriş/hesaplama havuzu"
                if data_new_ham_kaynak.empty:
                    data_new_ham_kaynak = st.session_state.get(
                        "yil_kapanis_data_new_bulut_df", pd.DataFrame()
                    )
                    data_new_kaynak_adi = (
                        "Seçili revizyonun Data_New bulut kaydı"
                    )
                data_new_detay_kaynak = yil_kapanis_detayini_hazirla(
                    data_new_ham_kaynak
                )
                detay_bulut_kaynak = st.session_state.get(
                    "yil_kapanis_detay_bulut_df", pd.DataFrame()
                )
                detay_buluttan_final = False

                if not detay_upload_kaynak.empty:
                    secili_detay_kaynak = detay_upload_kaynak.copy()
                    detay_kaynak_adi = "Yıl Kapanış sayfasına yüklenen dosya"
                elif not detay_bulut_kaynak.empty:
                    secili_detay_kaynak = detay_bulut_kaynak.copy()
                    detay_kaynak_adi = "Seçili revizyonun bulut detay kaydı"
                    detay_buluttan_final = True
                elif not data_new_detay_kaynak.empty:
                    secili_detay_kaynak = data_new_detay_kaynak.copy()
                    detay_kaynak_adi = data_new_kaynak_adi
                else:
                    secili_detay_kaynak = pd.DataFrame(
                        columns=yil_kapanis_detay_sutunlari
                    )
                    detay_kaynak_adi = "Kaynak bulunamadı"

                detay_sonuc = pd.DataFrame(
                    columns=yil_kapanis_detay_sutunlari
                )
                detay_export_df = pd.DataFrame(
                    columns=yil_kapanis_detay_sutunlari
                )
                kapanis_yili = None
                calisma_orani_etiketi = ""
                st.subheader("🧮 Yıl Kapanış Detay ve Tahmin")
                if secili_detay_kaynak.empty:
                    st.info(
                        "Detay tablo için bu sayfaya operasyon dosyası "
                        "yükleyin, Data_New kaynağını hazırlayın veya bulut "
                        "detay kaydını çağırın."
                    )
                    st.dataframe(
                        pd.DataFrame(columns=yil_kapanis_detay_sutunlari),
                        use_container_width=True,
                        hide_index=True,
                        height=260
                    )
                else:
                    detay_yillari = sorted({
                        int(value) for value in pd.to_numeric(
                            secili_detay_kaynak["Yıl"], errors="coerce"
                        ).dropna().tolist()
                    })
                    kayitli_kapanis_yili = kayitli_ayar.get("kapanis_yili")
                    if kayitli_kapanis_yili not in detay_yillari:
                        kayitli_kapanis_yili = detay_yillari[-1]
                    if (
                        "yil_kapanis_detay_yili" not in st.session_state
                        or st.session_state.yil_kapanis_detay_yili
                        not in detay_yillari
                    ):
                        st.session_state.yil_kapanis_detay_yili = (
                            kayitli_kapanis_yili
                        )
                    kapanis_yili = st.selectbox(
                        "Kapanışı yapılacak detay yılı",
                        detay_yillari,
                        key="yil_kapanis_detay_yili"
                    )
                    kapanacak_detay = secili_detay_kaynak[
                        pd.to_numeric(
                            secili_detay_kaynak["Yıl"], errors="coerce"
                        ) == int(kapanis_yili)
                    ].copy()
                    gun_oranlari, calisma_orani_etiketi, oran_bulundu = (
                        yil_kapanis_calisma_gunu_oranlari(
                            st.session_state.get(
                                "takvim_verisi_yillar", pd.DataFrame()
                            ),
                            kapanis_yili
                        )
                    )
                    if detay_buluttan_final:
                        detay_sonuc = yil_kapanis_detay_toplamlarini_yenile(
                            kapanacak_detay, son_gerceklesen_ay
                        )
                    else:
                        detay_sonuc = yil_kapanis_detay_tahminini_hesapla(
                            kapanacak_detay,
                            ortalama_sonuc,
                            son_gerceklesen_ay,
                            gun_oranlari
                        )
                    detay_manuel_baglam = yil_kapanis_manuel_baglami(
                        aktif_yk_rev_id, kapanis_yili, yil_1, yil_2,
                        son_gerceklesen_ay
                    )
                    detay_sonuc = yil_kapanis_manuel_degerlerini_uygula(
                        detay_sonuc, detay_manuel_baglam
                    )
                    detay_sonuc = yil_kapanis_detay_toplamlarini_yenile(
                        detay_sonuc, son_gerceklesen_ay
                    )
                    st.caption(
                        f"Kaynak: {detay_kaynak_adi} · Satır: "
                        f"{len(detay_sonuc):,} · Çalışma günü satırı: "
                        f"{calisma_orani_etiketi}. Hesaplamanın sabit bazı "
                        f"Ocak–{son_gerceklesen_ay} Gerçekleşen Toplam "
                        "Desi'dir."
                    )
                    if not oran_bulundu:
                        st.warning(
                            f"{calisma_orani_etiketi} çalışma günü verisi "
                            "bulunamadığı için aylık katsayılar 1 kabul edildi."
                        )
                    st.caption(
                        "Sarı hücrelerde aylık Desi ve tarihleri elle "
                        "değiştirebilirsiniz. Manuel değerler toplam, dışa "
                        "aktarım ve bulut kaydında önceliklidir."
                    )

                    dk1, dk2, dk3 = st.columns(3)
                    dk1_ph, dk2_ph, dk3_ph = (
                        dk1.empty(), dk2.empty(), dk3.empty()
                    )

                    detay_column_config = {
                        **{
                            col: st.column_config.NumberColumn(
                                col, format="%.0f"
                            )
                            for col in (
                                yil_kapanis_detay_ay_sutunlari
                                + [
                                    "Gerçekleşen Toplam Desi",
                                    "Tahmini Yıl Sonu Toplam Desi"
                                ]
                            )
                        },
                        "Kayıt Tarihi": st.column_config.DateColumn(
                            "Kayıt Tarihi", format="DD.MM.YYYY"
                        ),
                        "Esk. Yakıt Başlangıç Tarihi": (
                            st.column_config.DateColumn(
                                "Esk. Yakıt Başlangıç Tarihi",
                                format="DD.MM.YYYY"
                            )
                        ),
                        "Esk. Enf. Başlangıç Tarihi": (
                            st.column_config.DateColumn(
                                "Esk. Enf. Başlangıç Tarihi",
                                format="DD.MM.YYYY"
                            )
                        )
                    }
                    detay_toplam = yil_kapanis_detay_toplam_satiri(
                        detay_sonuc, kapanis_yili
                    )
                    detay_export_df = pd.concat(
                        [detay_sonuc, pd.DataFrame([detay_toplam])],
                        ignore_index=True
                    ).reindex(columns=yil_kapanis_detay_sutunlari)
                    toplam_gerceklesen = detay_sonuc[
                        "Gerçekleşen Toplam Desi"
                    ].sum()
                    toplam_tahmini = detay_sonuc[
                        "Tahmini Yıl Sonu Toplam Desi"
                    ].sum()
                    dk1_ph.metric(
                        "Gerçekleşen Toplam Desi",
                        f"{toplam_gerceklesen:,.0f}".replace(",", ".")
                    )
                    dk2_ph.metric(
                        "Tahmini Yıl Sonu Toplam Desi",
                        f"{toplam_tahmini:,.0f}".replace(",", ".")
                    )
                    dk3_ph.metric(
                        "Tahmin Edilen Ay", str(len(tamamlanacak_aylar))
                    )

                    if ST_AGGRID_AVAILABLE:
                        detay_onceki_df = detay_sonuc.copy()
                        detay_grid_df = detay_sonuc.copy()
                        tarih_sutunlari = [
                            "Kayıt Tarihi", "Esk. Yakıt Başlangıç Tarihi",
                            "Esk. Enf. Başlangıç Tarihi"
                        ]
                        for col in tarih_sutunlari:
                            detay_grid_df[col] = detay_grid_df[col].apply(
                                lambda value: (
                                    "" if pd.isna(value)
                                    else pd.Timestamp(value).strftime("%d.%m.%Y")
                                )
                            )
                        sayi_formatter = JsCode(
                            "function(p) { if (p.value === null || "
                            "p.value === undefined || p.value === '') "
                            "return ''; return Number(p.value).toLocaleString("
                            "'tr-TR', {maximumFractionDigits: 0}); }"
                        )
                        tam_sayi_parser = JsCode(
                            "function(p) { const t=String(p.newValue ?? '')"
                            ".trim().replace(/\\./g,'').replace(',','.'); "
                            "const n=Number(t); return Number.isFinite(n) ? "
                            "Math.round(n) : p.oldValue; }"
                        )
                        grid_builder = GridOptionsBuilder.from_dataframe(
                            detay_grid_df
                        )
                        grid_builder.configure_default_column(
                            editable=False,
                            sortable=True,
                            filter=True,
                            resizable=True,
                            minWidth=115
                        )
                        grid_builder.configure_column(
                            "Uniq ID", pinned="left", minWidth=180
                        )
                        for col in (
                            yil_kapanis_detay_ay_sutunlari
                        ):
                            grid_builder.configure_column(
                                col,
                                editable=True,
                                type=["numericColumn"],
                                filter="agNumberColumnFilter",
                                valueFormatter=sayi_formatter,
                                valueParser=tam_sayi_parser,
                                cellStyle={
                                    "backgroundColor": TEMA["editable"],
                                    "color": TEMA["editable_text"]
                                },
                                minWidth=125
                            )
                        for col in [
                            "Gerçekleşen Toplam Desi",
                            "Tahmini Yıl Sonu Toplam Desi"
                        ]:
                            grid_builder.configure_column(
                                col,
                                editable=False,
                                type=["numericColumn"],
                                filter="agNumberColumnFilter",
                                valueFormatter=sayi_formatter,
                                minWidth=150
                            )
                        for col in tarih_sutunlari:
                            grid_builder.configure_column(
                                col,
                                editable=True,
                                cellStyle={
                                    "backgroundColor": TEMA["editable"],
                                    "color": TEMA["editable_text"]
                                },
                                minWidth=145
                            )
                        grid_builder.configure_grid_options(
                            pinnedBottomRowData=[detay_toplam],
                            suppressScrollOnNewData=True,
                            animateRows=False
                        )
                        yil_kapanis_grid_css = {
                            **DATA_NEW_GRID_CSS,
                            ".ag-row-pinned": {
                                "background-color": TEMA["surface_3"],
                                "color": TEMA["text"],
                                "font-weight": "800",
                                "border-top": (
                                    f"2px solid {TEMA['primary']} !important"
                                )
                            }
                        }
                        detay_grid_response = AgGrid(
                            detay_grid_df,
                            gridOptions=grid_builder.build(),
                            height=560,
                            theme="streamlit",
                            data_return_mode=DataReturnMode.AS_INPUT,
                            allow_unsafe_jscode=True,
                            enable_enterprise_modules=False,
                            custom_css=yil_kapanis_grid_css,
                            update_on=["cellValueChanged"],
                            server_sync_strategy="client_wins",
                            key=(
                                "yil_kapanis_detay_grid_v1_"
                                f"{TEMA['scheme']}_{int(kapanis_yili)}_"
                                f"{son_gerceklesen_ay}"
                            )
                        )
                        detay_grid_verisi = (
                            detay_grid_response.get("data")
                            if isinstance(detay_grid_response, dict)
                            else getattr(detay_grid_response, "data", None)
                        )
                        if detay_grid_verisi is not None:
                            duzenlenen_detay = pd.DataFrame(detay_grid_verisi)
                            duzenlenen_detay = duzenlenen_detay.reindex(
                                columns=yil_kapanis_detay_sutunlari
                            )
                            for col in tarih_sutunlari:
                                duzenlenen_detay[col] = pd.to_datetime(
                                    duzenlenen_detay[col], errors="coerce",
                                    dayfirst=True
                                )
                            for col in yil_kapanis_detay_ay_sutunlari:
                                duzenlenen_detay[col] = (
                                    desi_kg_serisini_yuvarla(
                                        duzenlenen_detay[col]
                                    )
                                )
                            yil_kapanis_manuel_degisikliklerini_kaydet(
                                detay_onceki_df, duzenlenen_detay,
                                detay_manuel_baglam
                            )
                            detay_sonuc = (
                                yil_kapanis_detay_toplamlarini_yenile(
                                    duzenlenen_detay, son_gerceklesen_ay
                                )
                            )
                    else:
                        detay_onceki_df = detay_sonuc.copy()
                        detay_sonuc = st.data_editor(
                            detay_sonuc,
                            use_container_width=True,
                            hide_index=True,
                            height=520,
                            column_config=detay_column_config,
                            disabled=[
                                col for col in yil_kapanis_detay_sutunlari
                                if col not in (
                                    yil_kapanis_detay_ay_sutunlari
                                    + [
                                        "Kayıt Tarihi",
                                        "Esk. Yakıt Başlangıç Tarihi",
                                        "Esk. Enf. Başlangıç Tarihi"
                                    ]
                                )
                            ],
                            key=(
                                "yil_kapanis_detay_editor_v2_"
                                f"{int(kapanis_yili)}_{son_gerceklesen_ay}"
                            )
                        )
                        yil_kapanis_manuel_degisikliklerini_kaydet(
                            detay_onceki_df, detay_sonuc, detay_manuel_baglam
                        )
                        detay_sonuc = yil_kapanis_detay_toplamlarini_yenile(
                            detay_sonuc, son_gerceklesen_ay
                        )
                        detay_toplam = yil_kapanis_detay_toplam_satiri(
                            detay_sonuc, kapanis_yili
                        )
                        toplam_fallback = pd.DataFrame([detay_toplam])
                        for col in [
                            "Kayıt Tarihi", "Esk. Yakıt Başlangıç Tarihi",
                            "Esk. Enf. Başlangıç Tarihi"
                        ]:
                            toplam_fallback[col] = pd.NaT
                        st.dataframe(
                            toplam_fallback.reindex(
                                columns=yil_kapanis_detay_sutunlari
                            ),
                            use_container_width=True,
                            hide_index=True,
                            height=90,
                            column_config=detay_column_config
                        )
                        st.caption(
                            "Sabit dip toplam için requirements.txt dosyasında "
                            "streamlit-aggrid==1.2.1.post2 bulunmalıdır."
                        )

                    # Griddeki manuel değerler Excel/CSV, dip toplam ve bulut
                    # kaydına aynı anda yansısın.
                    detay_toplam = yil_kapanis_detay_toplam_satiri(
                        detay_sonuc, kapanis_yili
                    )
                    detay_export_df = pd.concat(
                        [detay_sonuc, pd.DataFrame([detay_toplam])],
                        ignore_index=True
                    ).reindex(columns=yil_kapanis_detay_sutunlari)

                yk_excel = io.BytesIO()
                with pd.ExcelWriter(yk_excel, engine="openpyxl") as writer:
                    matris_1.to_excel(
                        writer, index=False, sheet_name=str(yil_1)
                    )
                    matris_2.to_excel(
                        writer, index=False, sheet_name=str(yil_2)
                    )
                    ortalama_gosterim.to_excel(
                        writer, index=False, sheet_name="ORTALAMA"
                    )
                    if not detay_export_df.empty and len(detay_sonuc) <= 20000:
                        detay_export_df.to_excel(
                            writer, index=False, sheet_name="KAPANIŞ DETAY"
                        )

                yk1, yk_detay_indir, yk2 = st.columns(3)
                yk1.download_button(
                    "📥 Özet Excel İndir",
                    data=yk_excel.getvalue(),
                    file_name=f"yil_kapanis_{yil_1}_{yil_2}.xlsx",
                    mime=(
                        "application/vnd.openxmlformats-officedocument."
                        "spreadsheetml.sheet"
                    ),
                    use_container_width=True,
                    key="btn_yil_kapanis_excel"
                )

                if not detay_sonuc.empty:
                    detay_csv = detay_export_df.to_csv(
                        index=False,
                        sep=";",
                        decimal=",",
                        date_format="%d.%m.%Y"
                    ).encode("utf-8-sig")
                    yk_detay_indir.download_button(
                        "📥 Detayı CSV İndir",
                        data=detay_csv,
                        file_name=(
                            f"yil_kapanis_detay_{int(kapanis_yili)}.csv"
                        ),
                        mime="text/csv",
                        use_container_width=True,
                        key="btn_yil_kapanis_detay_csv"
                    )
                else:
                    yk_detay_indir.button(
                        "📥 Detay Kaynağı Bekleniyor",
                        disabled=True,
                        use_container_width=True,
                        key="btn_yil_kapanis_detay_bos"
                    )

                if yk2.button(
                    "💾 Kg ve Yıl Kapanışını Buluta Kaydet",
                    type="primary",
                    use_container_width=True,
                    disabled=(not client or not aktif_yk_rev_id),
                    key="btn_yil_kapanis_cloud_save"
                ):
                    try:
                        if not detay_sonuc.empty:
                            client.table(
                                YIL_KAPANIS_DETAY_DB_TABLOSU
                            ).delete().eq(
                                "revizyon_id", aktif_yk_rev_id
                            ).execute()
                            for i in range(0, len(detay_sonuc), 500):
                                detay_records = []
                                for _, row in detay_sonuc.iloc[
                                    i:i + 500
                                ].iterrows():
                                    rec = {
                                        col: json_uyumlu_deger(row.get(col))
                                        for col in yil_kapanis_detay_sutunlari
                                    }
                                    rec["revizyon_id"] = aktif_yk_rev_id
                                    detay_records.append(rec)
                                client.table(
                                    YIL_KAPANIS_DETAY_DB_TABLOSU
                                ).insert(detay_records).execute()

                        client.table(KG_MUSTERI_DB_TABLOSU).delete().eq(
                            "revizyon_id", aktif_yk_rev_id
                        ).execute()
                        for i in range(0, len(kg_kaynak), 500):
                            kg_records = []
                            for _, row in kg_kaynak.iloc[
                                i:i + 500
                            ].iterrows():
                                rec = {
                                    col: json_uyumlu_deger(row.get(col))
                                    for col in kg_musteri_sutunlari
                                }
                                rec["revizyon_id"] = aktif_yk_rev_id
                                kg_records.append(rec)
                            client.table(KG_MUSTERI_DB_TABLOSU).insert(
                                kg_records
                            ).execute()

                        kapanis_records = []
                        for _, row in ortalama_sonuc.iterrows():
                            rec = {
                                "revizyon_id": aktif_yk_rev_id,
                                "Yıl 1": int(yil_1),
                                "Yıl 2": int(yil_2),
                                "Gerçekleşen Son Ay": son_gerceklesen_ay,
                                "Kapanış Yılı": (
                                    int(kapanis_yili)
                                    if kapanis_yili is not None else None
                                ),
                                **{
                                    col: json_uyumlu_deger(row.get(col))
                                    for col in yil_kapanis_sonuc_sutunlari
                                }
                            }
                            kapanis_records.append(rec)
                        client.table(YIL_KAPANIS_DB_TABLOSU).delete().eq(
                            "revizyon_id", aktif_yk_rev_id
                        ).execute()
                        client.table(YIL_KAPANIS_DB_TABLOSU).insert(
                            kapanis_records
                        ).execute()
                        revizyonu_degistirildi_isaretle(aktif_yk_rev_id)
                        st.session_state.yil_kapanis_kg_df = kg_kaynak.copy()
                        st.session_state.yil_kapanis_kayitli_sonuc_df = (
                            ortalama_sonuc.copy()
                        )
                        if not detay_sonuc.empty:
                            st.session_state.yil_kapanis_detay_bulut_df = (
                                detay_sonuc.copy()
                            )
                        st.session_state.yil_kapanis_bulut_ayarlari = {
                            "yil_1": int(yil_1),
                            "yil_2": int(yil_2),
                            "son_ay": son_gerceklesen_ay,
                            "kapanis_yili": (
                                int(kapanis_yili)
                                if kapanis_yili is not None else None
                            )
                        }
                        st.success(
                            "Müşteri-Kg kaynağı, yıl kapanış sonucu ve detay "
                            "tahminleri seçili revizyona kaydedildi."
                        )
                    except Exception as ex:
                        st.error(
                            "Yıl kapanışı buluta kaydedilemedi. Önce Yıl "
                            f"Kapanış Supabase SQL'ini çalıştırın. Ayrıntı: {ex}"
                        )


# ------------------------------------------------------------
# 10. SEKME: ÜFE-TÜFE YÖNETİMİ VE EVDS ENTEGRASYONU
# ------------------------------------------------------------
if sekme_acik_mi[9]:
    with sekmeler[9]:
        st.title("📉 ÜFE–TÜFE Veri Yönetimi")
        st.caption(
            "Gerçekleşen aylık oranlar TCMB EVDS'den alınır. Tahmin alanları "
            "elle girilebilir; manuel düzeltme girildiğinde hesaplarda "
            "Manuel > Gerçekleşen > Tahmin önceliği uygulanır. Boş aylar 0 "
            "olarak kabul edilmez."
        )
        aktif_enflasyon_rev_id = sayfa_aktif_revizyonunu_getir()

        durum_1, durum_2, durum_3 = st.columns(3)
        durum_1.metric(
            "EVDS API Anahtarı",
            "Hazır" if EVDS_API_KEY else "Eksik"
        )
        durum_2.metric(
            "Supabase Bağlantısı",
            "Hazır" if client else "Eksik"
        )
        durum_3.metric(
            "Veri Önceliği",
            "Manuel > Gerçekleşen > Tahmin"
        )

        bugunku_yil = date.today().year
        yil_1, yil_2 = st.columns(2)
        baslangic_yili_enf = int(yil_1.number_input(
            "Başlangıç Yılı",
            min_value=2005,
            max_value=2100,
            value=max(2005, bugunku_yil - 1),
            step=1,
            key="enflasyon_baslangic_yili"
        ))
        bitis_yili_enf = int(yil_2.number_input(
            "Bitiş Yılı",
            min_value=2005,
            max_value=2100,
            value=min(2100, bugunku_yil + 1),
            step=1,
            key="enflasyon_bitis_yili"
        ))

        if bitis_yili_enf < baslangic_yili_enf:
            st.error("Bitiş yılı başlangıç yılından küçük olamaz.")
            st.stop()

        if st.session_state.pop("evds_guncelleme_basarili", False):
            adet = st.session_state.pop("evds_guncellenen_kayit_sayisi", 0)
            st.success(
                f"EVDS'den gelen {adet} aylık kayıt Supabase'e işlendi."
            )
        if st.session_state.pop("enflasyon_manuel_kayit_basarili", False):
            st.success("Tahmin ve manuel ÜFE–TÜFE değerleri buluta kaydedildi.")

        evds_col, bilgi_col = st.columns([1, 2])
        evds_guncelle_tiklandi = evds_col.button(
            "🔄 EVDS'den Gerçekleşenleri Güncelle",
            type="primary",
            use_container_width=True,
            disabled=(not EVDS_API_KEY or not client),
            key="btn_evds_enflasyon_guncelle"
        )
        bilgi_col.info(
            f"TÜFE serisi: {EVDS_TUFE_SERI_KODU}  |  "
            f"Yİ-ÜFE serisi: {EVDS_UFE_SERI_KODU}"
        )

        if evds_guncelle_tiklandi:
            try:
                with st.spinner(
                    "TCMB EVDS'den aylık gerçekleşen ÜFE–TÜFE oranları alınıyor..."
                ):
                    evds_kayitlari = evds_aylik_enflasyon_getir(
                        baslangic_yili_enf,
                        bitis_yili_enf,
                        EVDS_API_KEY
                    )
                    for paket_baslangici in range(0, len(evds_kayitlari), 250):
                        client.table(ENFLASYON_DB_TABLOSU).upsert(
                            evds_kayitlari[paket_baslangici:paket_baslangici + 250],
                            on_conflict="yil,ay"
                        ).execute()
                master_enflasyon_kaynaklarini_getir.clear()
                st.session_state.evds_guncelleme_basarili = True
                st.session_state.evds_guncellenen_kayit_sayisi = len(
                    evds_kayitlari
                )
                st.rerun()
            except Exception as hata:
                st.error(f"EVDS güncellemesi tamamlanamadı: {hata}")

        try:
            bulut_enflasyon_df = enflasyon_bulut_verilerini_getir(
                baslangic_yili_enf,
                bitis_yili_enf,
                aktif_revizyon_id_getir()
            ) if client else pd.DataFrame()
        except Exception as hata:
            bulut_enflasyon_df = pd.DataFrame()
            st.error(f"ÜFE–TÜFE tablosu Supabase'den okunamadı: {hata}")

        enflasyon_editor_df = enflasyon_editor_tablosu_olustur(
            baslangic_yili_enf,
            bitis_yili_enf,
            bulut_enflasyon_df
        )

        st.markdown("### Aylık ÜFE–TÜFE Tablosu")
        st.caption(
            "Sadece Tahmin ve Manuel sütunları düzenlenebilir. Manuel değeri "
            "temizlerseniz gerçekleşen; gerçekleşen de yoksa tahmin yeniden "
            "kullanılır. Negatif oran girebilirsiniz."
        )

        oran_gosterim_sutunlari = [
            "ÜFE Gerçekleşen (%)", "TÜFE Gerçekleşen (%)",
            "ÜFE Tahmin (%)", "TÜFE Tahmin (%)",
            "ÜFE Manuel (%)", "TÜFE Manuel (%)",
            "ÜFE Kullanılan (%)", "TÜFE Kullanılan (%)"
        ]
        enflasyon_edited_df = st.data_editor(
            enflasyon_editor_df,
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            height=min(760, 38 * len(enflasyon_editor_df) + 42),
            disabled=[
                "Yıl", "Ay", "Dönem",
                "ÜFE Gerçekleşen (%)", "TÜFE Gerçekleşen (%)",
                "ÜFE Kullanılan (%)", "TÜFE Kullanılan (%)", "Veri Durumu"
            ],
            column_config={
                "Yıl": st.column_config.NumberColumn("Yıl", format="%d"),
                "Dönem": st.column_config.DateColumn(
                    "Dönem", format="DD.MM.YYYY"
                ),
                **{
                    kolon: st.column_config.NumberColumn(
                        kolon,
                        format="%.2f%%",
                        step=0.01
                    )
                    for kolon in oran_gosterim_sutunlari
                }
            },
            key=(
                f"enflasyon_veri_editoru_"
                f"{baslangic_yili_enf}_{bitis_yili_enf}"
            )
        )

        kaydet_col, indir_col, varsayilan_col = st.columns([2, 2, 1])
        tahmin_manuel_kaydet = kaydet_col.button(
            "💾 Tahmin ve Manuel Değerleri Buluta Kaydet",
            type="primary",
            use_container_width=True,
            disabled=(not client or not aktif_enflasyon_rev_id),
            key="btn_enflasyon_tahmin_manuel_kaydet"
        )

        excel_buffer_enf = io.BytesIO()
        with pd.ExcelWriter(excel_buffer_enf, engine="openpyxl") as writer:
            enflasyon_edited_df.to_excel(
                writer,
                index=False,
                sheet_name="UFE_TUFE"
            )
        indir_col.download_button(
            "📥 ÜFE–TÜFE Tablosunu Excel İndir",
            data=excel_buffer_enf.getvalue(),
            file_name=(
                f"ufe_tufe_{baslangic_yili_enf}_{bitis_yili_enf}.xlsx"
            ),
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            use_container_width=True,
            key="btn_enflasyon_excel_indir"
        )

        enflasyon_override_sil = varsayilan_col.button(
            "↩️ Ortak Varsayılana Dön",
            use_container_width=True,
            disabled=(not client or not aktif_enflasyon_rev_id),
            key="btn_enflasyon_override_sil"
        )

        if enflasyon_override_sil:
            try:
                client.table(ENFLASYON_REVIZYON_DB_TABLOSU).delete().eq(
                    "revizyon_id", aktif_enflasyon_rev_id
                ).execute()
                master_enflasyon_kaynaklarini_getir.clear()
                revizyonu_degistirildi_isaretle(aktif_enflasyon_rev_id)
                st.rerun()
            except Exception as hata:
                st.error(f"Ortak ÜFE–TÜFE verisine dönülemedi: {hata}")

        if tahmin_manuel_kaydet:
            try:
                manuel_kayitlar = []
                for _, row in enflasyon_edited_df.iterrows():
                    yil = int(row["Yıl"])
                    ay_no = aylar.index(str(row["Ay"])) + 1
                    manuel_kayitlar.append({
                        "revizyon_id": aktif_enflasyon_rev_id,
                        "yil": yil,
                        "ay": ay_no,
                        "donem": date(yil, ay_no, 1).isoformat(),
                        "ufe_tahmin_oran": nullable_sayi(
                            row.get("ÜFE Tahmin (%)")
                        ),
                        "tufe_tahmin_oran": nullable_sayi(
                            row.get("TÜFE Tahmin (%)")
                        ),
                        "ufe_manuel_oran": nullable_sayi(
                            row.get("ÜFE Manuel (%)")
                        ),
                        "tufe_manuel_oran": nullable_sayi(
                            row.get("TÜFE Manuel (%)")
                        )
                    })
                client.table(ENFLASYON_REVIZYON_DB_TABLOSU).delete().eq(
                    "revizyon_id", aktif_enflasyon_rev_id
                ).gte("yil", baslangic_yili_enf).lte(
                    "yil", bitis_yili_enf
                ).execute()
                for paket_baslangici in range(0, len(manuel_kayitlar), 250):
                    client.table(ENFLASYON_REVIZYON_DB_TABLOSU).insert(
                        manuel_kayitlar[
                            paket_baslangici:paket_baslangici + 250
                        ]
                    ).execute()
                master_enflasyon_kaynaklarini_getir.clear()
                revizyonu_degistirildi_isaretle(aktif_enflasyon_rev_id)
                st.session_state.enflasyon_manuel_kayit_basarili = True
                st.rerun()
            except Exception as hata:
                st.error(f"Tahmin ve manuel değerler kaydedilemedi: {hata}")


# ------------------------------------------------------------
# 11. SEKME: BAZ BİRİM FİYATLAR
# ------------------------------------------------------------
if sekme_acik_mi[10]:
    with sekmeler[10]:
        st.title("💳 Baz Birim Fiyatlar")
        st.caption(
            "2026 fiyat zincirinin başlangıç değeri bu sayfadan alınır. "
            "Eşleşme anahtarı Müşteri Kodu + Atf Tipi'dir; TL/desi değeri "
            "Data_New tablosundaki 2025 Aralık Fiyat alanına yazılır."
        )

        baz_birim_upload = st.file_uploader(
            "Baz Birim Fiyat Dosyasını Yükleyin",
            type=["xlsx", "xls", "csv"],
            key="baz_birim_fiyat_upload"
        )
        if baz_birim_upload is not None:
            try:
                yeni_imza = yuklenen_dosya_imzasi(baz_birim_upload)
                if yeni_imza != st.session_state.baz_birim_upload_imzasi:
                    yuklenen_baz = yuklenen_tabloyu_oku(baz_birim_upload)
                    st.session_state.baz_birim_fiyat_df = (
                        baz_birim_fiyat_tablosunu_hazirla(yuklenen_baz)
                    )
                    st.session_state.baz_birim_upload_imzasi = yeni_imza
                    st.success(
                        f"{len(st.session_state.baz_birim_fiyat_df):,} baz birim "
                        "fiyat kaydı yüklendi."
                    )
            except Exception as ex:
                st.error(f"Baz Birim Fiyat dosyası okunamadı: {ex}")

        baz_birim_df = st.session_state.baz_birim_fiyat_df.copy()
        if baz_birim_df.empty:
            st.info(
                "Baz fiyat dosyası yükleyebilir veya aşağıdan seçilen bulut "
                "versiyonunu geri çağırabilirsiniz."
            )
        else:
            tekrar_baz_uniq = baz_birim_df["uniq"].duplicated(keep=False)
            if tekrar_baz_uniq.any():
                st.warning(
                    f"{int(tekrar_baz_uniq.sum()):,} satırda tekrarlanan uniq "
                    "bulundu. Buluta kaydetmeden önce kontrol edin."
                )

            edited_baz_birim = st.data_editor(
                baz_birim_df,
                use_container_width=True,
                hide_index=True,
                height=470,
                num_rows="dynamic",
                disabled=["uniq"],
                column_config={
                    "TL/desi": st.column_config.NumberColumn(
                        "TL/desi", format="₺%.4f", min_value=0.0, step=0.0001
                    )
                },
                key="baz_birim_fiyat_editoru"
            )
            st.session_state.baz_birim_fiyat_df = (
                baz_birim_fiyat_tablosunu_hazirla(edited_baz_birim)
            )

        baz_birim_excel = io.BytesIO()
        with pd.ExcelWriter(baz_birim_excel, engine="openpyxl") as writer:
            st.session_state.baz_birim_fiyat_df.to_excel(
                writer, index=False, sheet_name="Baz Birim Fiyatlar"
            )

        bb1, bb2, bb3 = st.columns(3)
        bb1.download_button(
            "📥 Baz Birim Fiyatları Excel İndir",
            data=baz_birim_excel.getvalue(),
            file_name="baz_birim_fiyatlar.xlsx",
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            use_container_width=True,
            key="btn_baz_birim_excel"
        )

        if rev_secenekleri:
            baz_birim_rev_id = sayfa_aktif_revizyonunu_getir(bb2)
            if bb2.button(
                "💾 Baz Birim Fiyatları Buluta Kaydet",
                type="primary",
                use_container_width=True,
                disabled=st.session_state.baz_birim_fiyat_df.empty,
                key="btn_baz_birim_save"
            ):
                try:
                    kayitlar = []
                    for _, row in st.session_state.baz_birim_fiyat_df.iterrows():
                        rec = {
                            col: json_uyumlu_deger(row.get(col))
                            for col in baz_birim_fiyat_sutunlari
                        }
                        rec["revizyon_id"] = baz_birim_rev_id
                        kayitlar.append(rec)
                    client.table("baz_birim_fiyat_tablosu").delete().eq(
                        "revizyon_id", baz_birim_rev_id
                    ).execute()
                    for i in range(0, len(kayitlar), 500):
                        client.table("baz_birim_fiyat_tablosu").insert(
                            kayitlar[i:i + 500]
                        ).execute()
                    revizyonu_degistirildi_isaretle(baz_birim_rev_id)
                    st.success("Baz Birim Fiyatlar buluta kaydedildi.")
                except Exception as ex:
                    st.error(
                        "Baz Birim Fiyatlar buluta kaydedilemedi. Önce yeni "
                        f"Supabase SQL dosyasını çalıştırın. Ayrıntı: {ex}"
                    )

            if bb3.button(
                "🔄 Baz Birim Fiyatları Buluttan Getir",
                use_container_width=True,
                key="btn_baz_birim_load"
            ):
                try:
                    tum_kayitlar = []
                    baslangic = 0
                    while True:
                        res = (
                            client.table("baz_birim_fiyat_tablosu")
                            .select("*")
                            .eq("revizyon_id", baz_birim_rev_id)
                            .range(baslangic, baslangic + 999)
                            .execute()
                        )
                        paket = res.data or []
                        tum_kayitlar.extend(paket)
                        if len(paket) < 1000:
                            break
                        baslangic += 1000
                    if tum_kayitlar:
                        gelen = pd.DataFrame(tum_kayitlar).drop(
                            columns=["id", "revizyon_id"], errors="ignore"
                        )
                        st.session_state.baz_birim_fiyat_df = (
                            baz_birim_fiyat_tablosunu_hazirla(gelen)
                        )
                        st.session_state.baz_birim_upload_imzasi = None
                        st.success("Baz Birim Fiyatlar buluttan getirildi.")
                        st.rerun()
                    else:
                        st.warning("Seçilen versiyonda baz birim fiyat bulunamadı.")
                except Exception as ex:
                    st.error(f"Baz Birim Fiyatlar buluttan getirilemedi: {ex}")


# ------------------------------------------------------------
# 12. SEKME: DATA_NEW
# ------------------------------------------------------------
if sekme_acik_mi[11]:
    with sekmeler[11]:
        st.title("🆕 Data_New Hesaplama Havuzu")
        st.caption(
            "Nihai hesaplama tablosudur. 2025 Desi/Tutar dosyası burada; "
            "2024–2025 tarihsel havuz ve büyüme oranları Müşteri Büyüme "
            "sayfasında yönetilir. Master Data eskalasyonu ve Baz Birim "
            "Fiyatlar seçilen revizyon üzerinden birleştirilerek 2026 hesaplanır."
        )

        data_new_rev_id = None
        if rev_secenekleri:
            data_new_rev_id = sayfa_aktif_revizyonunu_getir()
        else:
            st.warning(
                "Bulut revizyonu bulunamadı. Hesaplamada yalnızca aktif hafıza "
                "kaynakları kullanılabilir."
            )

        data_new_upload = st.file_uploader(
            "2025 Desi ve Tutar Dosyasını Yükleyin",
            type=["xlsx", "xls", "csv"],
            key="data_new_upload"
        )
        if data_new_upload is not None:
            try:
                yeni_imza = yuklenen_dosya_imzasi(data_new_upload)
                if yeni_imza != st.session_state.data_new_upload_imzasi:
                    raw_data_new = yuklenen_tabloyu_oku(data_new_upload)
                    st.session_state.data_new_girdi_df = (
                        data_new_girdisini_hazirla(raw_data_new)
                    )
                    st.session_state.data_new_sonuc_df = pd.DataFrame(
                        columns=data_new_tum_sutunlar
                    )
                    st.session_state.data_new_kaynak_df = pd.DataFrame(
                        columns=data_new_tum_sutunlar
                    )
                    st.session_state.data_new_kontrol_bilgisi = {}
                    st.session_state.data_new_buyume_ayarlari = {}
                    st.session_state.data_new_upload_imzasi = yeni_imza
                    st.success(
                        f"{len(st.session_state.data_new_girdi_df):,} operasyon "
                        "satırı Data_New için hazırlandı."
                    )
            except Exception as ex:
                st.error(f"Data_New giriş dosyası okunamadı: {ex}")

        hesap_col, temizle_col, buluttan_getir_col = st.columns([3, 1, 1])
        data_new_hesapla_tiklandi = hesap_col.button(
            "⚙️ Kaynakları Al ve Data_New'u Hesapla",
            type="primary",
            use_container_width=True,
            disabled=st.session_state.data_new_girdi_df.empty,
            key="btn_data_new_hesapla"
        )
        if temizle_col.button(
            "🧹 Data_New Hafızasını Temizle",
            use_container_width=True,
            key="btn_data_new_temizle"
        ):
            st.session_state.data_new_girdi_df = pd.DataFrame()
            st.session_state.data_new_sonuc_df = pd.DataFrame(
                columns=data_new_tum_sutunlar
            )
            st.session_state.data_new_kaynak_df = pd.DataFrame(
                columns=data_new_tum_sutunlar
            )
            st.session_state.data_new_upload_imzasi = None
            st.session_state.data_new_kontrol_bilgisi = {}
            st.session_state.data_new_buyume_ayarlari = {}
            st.session_state.data_new_liste_filtreleri = {}
            st.session_state.data_new_filtre_nonce += 1
            st.rerun()

        data_new_buluttan_getir_tiklandi = buluttan_getir_col.button(
            "🔄 Data_New'u Buluttan Getir",
            use_container_width=True,
            disabled=(not client or not data_new_rev_id),
            key="btn_data_new_cloud_load"
        )
        if data_new_buluttan_getir_tiklandi:
            try:
                tum_kayitlar = supabase_revizyon_kayitlarini_getir(
                    "data_new_tablosu", data_new_rev_id
                )
                if tum_kayitlar:
                    gelen_raw = pd.DataFrame(tum_kayitlar)
                    manuel_ayarlar = {}
                    for _, row in gelen_raw.iterrows():
                        uniq_id = str(row.get("Uniq ID", ""))
                        ham_ayar = row.get(DATA_NEW_MANUEL_BUYUME_DB, {})
                        if isinstance(ham_ayar, str):
                            try:
                                ham_ayar = json.loads(ham_ayar)
                            except (
                                TypeError, ValueError, json.JSONDecodeError
                            ):
                                ham_ayar = {}
                        if not isinstance(ham_ayar, dict):
                            ham_ayar = {}
                        temiz_ayar = {
                            col: guvenli_sayi(value)
                            for col, value in ham_ayar.items()
                            if col in data_new_2026_buyume_sutunlari
                            and nullable_sayi(value) is not None
                        }
                        if uniq_id and temiz_ayar:
                            manuel_ayarlar[uniq_id] = temiz_ayar

                    gelen = gelen_raw.drop(
                        columns=["id", "revizyon_id"], errors="ignore"
                    )
                    for col in data_new_tum_sutunlar:
                        if col not in gelen.columns:
                            gelen[col] = np.nan
                    gelen = gelen[data_new_tum_sutunlar]

                    buyume_kaynak = pd.DataFrame(
                        supabase_revizyon_kayitlarini_getir(
                            "buyume_tablosu", data_new_rev_id
                        )
                    )
                    if buyume_kaynak.empty:
                        buyume_kaynak = buyume_ayarlari_dataframe_olustur(
                            st.session_state.get("buyume_ayarlari", {})
                        )
                    if buyume_kaynak.empty:
                        kaynak_df = gelen.copy()
                    else:
                        kaynak_df, _ = data_new_buyume_kaynaklarini_uygula(
                            gelen, buyume_kaynak, hesaplari_yenile=True
                        )
                    st.session_state.data_new_kaynak_df = kaynak_df
                    st.session_state.data_new_buyume_ayarlari = manuel_ayarlar
                    st.session_state.data_new_sonuc_df = (
                        data_new_manuel_buyumeleri_uygula(
                            kaynak_df, manuel_ayarlar
                        )
                    )
                    st.session_state.data_new_kontrol_bilgisi = {
                        "satir_sayisi": len(gelen),
                        "tekrarlanan_uniq": int(
                            gelen["Uniq ID"].duplicated(keep=False).sum()
                        ),
                        "master_eslesmeyen": 0,
                        "buyume_eslesmeyen": 0,
                        "baz_fiyat_eslesmeyen": int(
                            gelen["2025 Aralık Fiyat"].isna().sum()
                        )
                    }
                    st.success("Data_New buluttan getirildi.")
                    st.rerun()
                else:
                    st.warning("Seçilen versiyonda Data_New kaydı bulunamadı.")
            except Exception as ex:
                st.error(f"Data_New buluttan getirilemedi: {ex}")

        if data_new_hesapla_tiklandi:
            try:
                with st.spinner(
                    "Master Data, büyüme ve baz fiyat kaynakları birleştiriliyor..."
                ):
                    master_kaynak = pd.DataFrame()
                    buyume_kaynak = pd.DataFrame()
                    baz_birim_kaynak = pd.DataFrame()

                    if client and data_new_rev_id:
                        master_kaynak = pd.DataFrame(
                            supabase_revizyon_kayitlarini_getir(
                                "master_data_tablosu", data_new_rev_id
                            )
                        )
                        buyume_kaynak = pd.DataFrame(
                            supabase_revizyon_kayitlarini_getir(
                                "buyume_tablosu", data_new_rev_id
                            )
                        )
                        baz_birim_kaynak = pd.DataFrame(
                            supabase_revizyon_kayitlarini_getir(
                                "baz_birim_fiyat_tablosu", data_new_rev_id
                            )
                        )

                    if master_kaynak.empty:
                        master_kaynak = st.session_state.get(
                            "master_data_df", pd.DataFrame()
                        ).copy()
                    if buyume_kaynak.empty:
                        buyume_kaynak = buyume_ayarlari_dataframe_olustur(
                            st.session_state.get("buyume_ayarlari", {})
                        )
                    if baz_birim_kaynak.empty:
                        baz_birim_kaynak = st.session_state.get(
                            "baz_birim_fiyat_df", pd.DataFrame()
                        ).copy()

                    hesaplanan, kontrol = data_new_tablosunu_hesapla(
                        st.session_state.data_new_girdi_df,
                        master_kaynak,
                        buyume_kaynak,
                        baz_birim_kaynak
                    )
                    st.session_state.data_new_kaynak_df = hesaplanan.copy()
                    hesaplanan = data_new_manuel_buyumeleri_uygula(
                        hesaplanan,
                        st.session_state.data_new_buyume_ayarlari
                    )
                    st.session_state.data_new_sonuc_df = hesaplanan
                    st.session_state.data_new_kontrol_bilgisi = kontrol
                st.success("Data_New hesaplaması tamamlandı.")
            except Exception as ex:
                st.error(f"Data_New hesaplanamadı: {ex}")

        kontrol = st.session_state.get("data_new_kontrol_bilgisi", {})
        if kontrol:
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Satır", f"{kontrol.get('satir_sayisi', 0):,}")
            k2.metric("Master Eşleşmeyen", f"{kontrol.get('master_eslesmeyen', 0):,}")
            k3.metric("Büyüme Eşleşmeyen", f"{kontrol.get('buyume_eslesmeyen', 0):,}")
            k4.metric("Baz Fiyat Eşleşmeyen", f"{kontrol.get('baz_fiyat_eslesmeyen', 0):,}")
            if kontrol.get("tekrarlanan_uniq", 0):
                st.error(
                    "Beklenmeyen tekrarlı Uniq ID bulundu: "
                    f"{kontrol['tekrarlanan_uniq']:,} satır."
                )
            if kontrol.get("baz_fiyat_eslesmeyen", 0):
                st.warning(
                    "Baz fiyatı eşleşmeyen satırlarda 2025 Aralık Fiyat ile "
                    "2026 Fiyat/Tutar alanları boş bırakıldı."
                )

        data_new_sonuc = st.session_state.data_new_sonuc_df.copy()
        if not data_new_sonuc.empty:
            yuzde_sutunlari = (
                [
                    "Yakıt Değişim Yüzdesi (%)",
                    "Yakıt Anlık Değişim Oranı (%)",
                    "Enf. Değişim Yüzdesi (%)"
                ]
                + data_new_2026_buyume_sutunlari
                + data_new_2026_esk_sutunlari
            )
            fiyat_sutunlari = (
                data_new_2025_fiyat_sutunlari
                + data_new_2026_fiyat_sutunlari
            )
            desi_sutunlari = (
                data_new_2025_desi_sutunlari
                + data_new_2026_desi_sutunlari
            )
            tutar_sutunlari = (
                data_new_2025_tutar_sutunlari
                + data_new_2026_tutar_sutunlari
            )
            sayisal_sutunlar = desi_sutunlari + tutar_sutunlari
            data_new_column_config = {
                    **{
                        col: st.column_config.NumberColumn(
                            col, format="%.2f%%"
                        ) for col in yuzde_sutunlari
                    },
                    **{
                        col: st.column_config.NumberColumn(
                            col, format="₺%.4f"
                        ) for col in fiyat_sutunlari
                    },
                    **{
                        col: st.column_config.NumberColumn(
                            col, format="%.0f"
                        ) for col in desi_sutunlari
                    },
                    **{
                        col: st.column_config.NumberColumn(
                            col, format="localized"
                        ) for col in tutar_sutunlari
                    },
                    "Kayıt Tarihi": st.column_config.DateColumn(
                        "Kayıt Tarihi", format="DD.MM.YYYY"
                    ),
                    "Esk. Yakıt Başlangıç Tarihi": st.column_config.DateColumn(
                        "Esk. Yakıt Başlangıç Tarihi", format="DD.MM.YYYY"
                    ),
                    "Esk. Enf. Başlangıç Tarihi": st.column_config.DateColumn(
                        "Esk. Enf. Başlangıç Tarihi", format="DD.MM.YYYY"
                    )
                }
            data_new_editor_key = "data_new_buyume_editoru_v3"

            def data_new_liste_filtrelerini_uygula(dataframe):
                filtreli = dataframe.copy()
                for col, secimler in (
                    st.session_state.data_new_liste_filtreleri.items()
                ):
                    if col not in filtreli.columns:
                        continue
                    secimler = [str(v) for v in (secimler or [])]
                    seri = filtreli[col].where(
                        filtreli[col].notna(), "(boş)"
                    ).astype(str)
                    filtreli = filtreli[seri.isin(secimler)]
                return filtreli

            def data_new_manuel_degisiklikleri_kaydet(duzenlenmis_df):
                if duzenlenmis_df is None:
                    return False
                duzenlenmis = pd.DataFrame(duzenlenmis_df).copy()
                if duzenlenmis.empty or "Uniq ID" not in duzenlenmis.columns:
                    return False

                guncel = st.session_state.data_new_sonuc_df.copy()
                kaynak = st.session_state.data_new_kaynak_df.copy()
                if kaynak.empty:
                    kaynak = guncel.copy()
                    st.session_state.data_new_kaynak_df = kaynak.copy()
                guncel_map = guncel.set_index(
                    guncel["Uniq ID"].astype(str)
                )
                kaynak_map = kaynak.set_index(
                    kaynak["Uniq ID"].astype(str)
                )
                degisti = False

                for _, row in duzenlenmis.iterrows():
                    uniq_id = str(row.get("Uniq ID", ""))
                    if uniq_id not in guncel_map.index:
                        continue
                    uniq_ayarlari = dict(
                        st.session_state.data_new_buyume_ayarlari.get(
                            uniq_id, {}
                        )
                    )
                    for col in data_new_2026_buyume_sutunlari:
                        if col not in row.index:
                            continue
                        yeni = nullable_sayi(row.get(col))
                        eski = nullable_sayi(guncel_map.at[uniq_id, col])
                        ayni = (
                            yeni is None and eski is None
                        ) or (
                            yeni is not None and eski is not None
                            and np.isclose(yeni, eski, rtol=0.0, atol=1e-9)
                        )
                        if ayni:
                            continue
                        kaynak_deger = nullable_sayi(
                            kaynak_map.at[uniq_id, col]
                        )
                        # Hücre temizlenirse veya kaynak değer yeniden yazılırsa
                        # manuel geçersiz kılma kaldırılır.
                        kaynaga_esit = (
                            yeni is not None and kaynak_deger is not None
                            and np.isclose(
                                yeni, kaynak_deger, rtol=0.0, atol=1e-9
                            )
                        )
                        if yeni is None or kaynaga_esit:
                            uniq_ayarlari.pop(col, None)
                        else:
                            uniq_ayarlari[col] = guvenli_sayi(yeni)
                        degisti = True
                    if uniq_ayarlari:
                        st.session_state.data_new_buyume_ayarlari[
                            uniq_id
                        ] = uniq_ayarlari
                    else:
                        st.session_state.data_new_buyume_ayarlari.pop(
                            uniq_id, None
                        )

                if degisti:
                    st.session_state.data_new_sonuc_df = (
                        data_new_manuel_buyumeleri_uygula(
                            kaynak,
                            st.session_state.data_new_buyume_ayarlari
                        )
                    )
                return degisti

            data_new_fragment = getattr(st, "fragment", lambda func: func)

            @data_new_fragment
            def data_new_editorunu_goster():
                tum_df = st.session_state.data_new_sonuc_df.copy()
                if ST_AGGRID_AVAILABLE:
                    tum_df = data_new_tarihlerini_gosterime_hazirla(tum_df)
                nonce = st.session_state.data_new_filtre_nonce
                st.caption(
                    "Başlıkların altındaki kutular yazdıkça filtreler. "
                    "Açılır liste filtresinde sütun seçip arama yapabilir, "
                    "Tümünü Seç ile yeniden bütün kayıtları gösterebilirsiniz. "
                    "Yalnızca 2026 büyüme hücreleri düzenlenebilir."
                )

                with st.expander("☑️ Açılır Liste Sütun Filtreleri", expanded=False):
                    f1, f2, f3 = st.columns([2, 1, 1])
                    filtre_col = f1.selectbox(
                        "Filtrelenecek sütun",
                        data_new_tum_sutunlar,
                        key=f"dn_filter_col_{nonce}"
                    )
                    ham_degerler = tum_df[filtre_col].where(
                        tum_df[filtre_col].notna(), "(boş)"
                    ).astype(str)
                    filtre_degerleri = sorted(
                        ham_degerler.unique().tolist(),
                        key=lambda value: value.casefold()
                    )
                    mevcut_secimler = (
                        st.session_state.data_new_liste_filtreleri.get(
                            filtre_col
                        )
                    )
                    tumu_secili = f2.checkbox(
                        "Tümünü Seç",
                        value=mevcut_secimler is None,
                        key=f"dn_filter_all_{nonce}_{filtre_col}"
                    )
                    if tumu_secili:
                        st.session_state.data_new_liste_filtreleri.pop(
                            filtre_col, None
                        )
                    else:
                        secilenler = st.multiselect(
                            "Ara ve değerleri seç",
                            filtre_degerleri,
                            default=(
                                mevcut_secimler
                                if mevcut_secimler is not None else []
                            ),
                            key=f"dn_filter_values_{nonce}_{filtre_col}"
                        )
                        st.session_state.data_new_liste_filtreleri[
                            filtre_col
                        ] = secilenler
                    if f3.button(
                        "🧹 Tüm Filtreleri Temizle",
                        use_container_width=True,
                        key=f"dn_filter_clear_{nonce}"
                    ):
                        st.session_state.data_new_liste_filtreleri = {}
                        st.session_state.data_new_filtre_nonce += 1
                        if hasattr(st, "fragment"):
                            st.rerun(scope="fragment")
                        else:
                            st.rerun()

                    aktifler = [
                        f"{col}: {len(values)} seçim"
                        for col, values in
                        st.session_state.data_new_liste_filtreleri.items()
                    ]
                    if aktifler:
                        st.info("Aktif liste filtreleri — " + " | ".join(aktifler))

                gosterilecek_df = data_new_liste_filtrelerini_uygula(tum_df)
                st.caption(
                    f"Gösterilen satır: {len(gosterilecek_df):,} / "
                    f"{len(tum_df):,}"
                )

                if gosterilecek_df.empty:
                    st.warning("Seçili filtrelere uyan kayıt bulunamadı.")
                    return

                if ST_AGGRID_AVAILABLE:
                    yuzde_formatter = JsCode(
                        "function(p) { if (p.value === null || p.value === undefined || p.value === '') return ''; "
                        "return Number(p.value).toLocaleString('tr-TR', {minimumFractionDigits: 2, maximumFractionDigits: 2}) + '%'; }"
                    )
                    para_formatter = JsCode(
                        "function(p) { if (p.value === null || p.value === undefined || p.value === '') return ''; "
                        "return '₺' + Number(p.value).toLocaleString('tr-TR', {minimumFractionDigits: 4, maximumFractionDigits: 4}); }"
                    )
                    sayi_formatter = JsCode(
                        "function(p) { if (p.value === null || p.value === undefined || p.value === '') return ''; "
                        "return Number(p.value).toLocaleString('tr-TR', {maximumFractionDigits: 2}); }"
                    )
                    desi_formatter = JsCode(
                        "function(p) { if (p.value === null || p.value === undefined || p.value === '') return ''; "
                        "return Math.round(Number(p.value)).toLocaleString('tr-TR', {maximumFractionDigits: 0}); }"
                    )
                    gb = GridOptionsBuilder.from_dataframe(gosterilecek_df)
                    gb.configure_default_column(
                        editable=False,
                        sortable=True,
                        filter="agTextColumnFilter",
                        floatingFilter=True,
                        resizable=True,
                        minWidth=110
                    )
                    for col in data_new_tum_sutunlar:
                        col_ayari = {
                            "editable": col in data_new_2026_buyume_sutunlari,
                            "filter": (
                                "agNumberColumnFilter"
                                if col in yuzde_sutunlari
                                or col in fiyat_sutunlari
                                or col in sayisal_sutunlar
                                else "agTextColumnFilter"
                            ),
                            "floatingFilter": True
                        }
                        if col in data_new_2026_buyume_sutunlari:
                            col_ayari.update({
                                "type": ["numericColumn"],
                                "valueFormatter": yuzde_formatter,
                                "cellStyle": {
                                    "backgroundColor": TEMA["editable"],
                                    "color": TEMA["editable_text"],
                                    "fontWeight": "600"
                                }
                            })
                        elif col in yuzde_sutunlari:
                            col_ayari["valueFormatter"] = yuzde_formatter
                        elif col in fiyat_sutunlari:
                            col_ayari["valueFormatter"] = para_formatter
                        elif col in desi_sutunlari:
                            col_ayari["valueFormatter"] = desi_formatter
                        elif col in sayisal_sutunlar:
                            col_ayari["valueFormatter"] = sayi_formatter
                        gb.configure_column(col, **col_ayari)
                    gb.configure_grid_options(
                        getRowId=JsCode(
                            "function(params) { return String(params.data['Uniq ID']); }"
                        ),
                        singleClickEdit=True,
                        stopEditingWhenCellsLoseFocus=True,
                        suppressScrollOnNewData=True,
                        animateRows=False
                    )
                    grid_response = AgGrid(
                        gosterilecek_df,
                        gridOptions=gb.build(),
                        height=560,
                        theme="streamlit",
                        data_return_mode=DataReturnMode.AS_INPUT,
                        update_on=["cellValueChanged"],
                        allow_unsafe_jscode=True,
                        enable_enterprise_modules=False,
                        custom_css=DATA_NEW_GRID_CSS,
                        server_sync_strategy="server_wins",
                        key=(
                            "data_new_aggrid_community_v2_"
                            + TEMA["scheme"]
                        )
                    )
                    grid_data = (
                        grid_response.get("data")
                        if isinstance(grid_response, dict)
                        else getattr(grid_response, "data", None)
                    )
                    if data_new_manuel_degisiklikleri_kaydet(grid_data):
                        if hasattr(st, "fragment"):
                            st.rerun(scope="fragment")
                        else:
                            st.rerun()
                else:
                    st.warning(
                        "Otomatik başlık filtreleri için requirements.txt "
                        "dosyanıza streamlit-aggrid==1.2.1.post2 satırını ekleyin. "
                        "Paket kurulana kadar güvenli Streamlit editörü kullanılıyor."
                    )
                    kilitli_data_new = [
                        col for col in data_new_tum_sutunlar
                        if col not in data_new_2026_buyume_sutunlari
                    ]
                    fallback_key = (
                        f"{data_new_editor_key}_{nonce}_"
                        f"{hash(tuple(gosterilecek_df['Uniq ID'].astype(str)))}"
                    )
                    fallback_sonuc = st.data_editor(
                        gosterilecek_df,
                        use_container_width=True,
                        hide_index=True,
                        height=520,
                        num_rows="fixed",
                        disabled=kilitli_data_new,
                        column_config=data_new_column_config,
                        key=fallback_key
                    )
                    if data_new_manuel_degisiklikleri_kaydet(fallback_sonuc):
                        if hasattr(st, "fragment"):
                            st.rerun(scope="fragment")
                        else:
                            st.rerun()

            data_new_editorunu_goster()

            data_new_excel = io.BytesIO()
            with pd.ExcelWriter(data_new_excel, engine="openpyxl") as writer:
                st.session_state.data_new_sonuc_df.to_excel(
                    writer, index=False, sheet_name="Data_New"
                )
            dn1, dn2 = st.columns(2)
            dn1.download_button(
                "📥 Data_New Excel İndir",
                data=data_new_excel.getvalue(),
                file_name="data_new.xlsx",
                mime=(
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                ),
                use_container_width=True,
                key="btn_data_new_excel"
            )

            if client and data_new_rev_id:
                if dn2.button(
                    "💾 Data_New'u Buluta Kaydet",
                    type="primary",
                    use_container_width=True,
                    key="btn_data_new_cloud_save"
                ):
                    try:
                        records = []
                        for _, row in st.session_state.data_new_sonuc_df.iterrows():
                            rec = {
                                col: json_uyumlu_deger(row.get(col))
                                for col in data_new_tum_sutunlar
                            }
                            rec["revizyon_id"] = data_new_rev_id
                            rec[DATA_NEW_MANUEL_BUYUME_DB] = {
                                col: guvenli_sayi(value)
                                for col, value in (
                                    st.session_state.data_new_buyume_ayarlari.get(
                                        str(row.get("Uniq ID")), {}
                                    )
                                ).items()
                                if col in data_new_2026_buyume_sutunlari
                            }
                            records.append(rec)
                        client.table("data_new_tablosu").delete().eq(
                            "revizyon_id", data_new_rev_id
                        ).execute()
                        for i in range(0, len(records), 100):
                            client.table("data_new_tablosu").insert(
                                records[i:i + 100]
                            ).execute()
                        revizyonu_degistirildi_isaretle(data_new_rev_id)
                        st.success("Data_New seçilen revizyona kaydedildi.")
                    except Exception as ex:
                        st.error(
                            "Data_New buluta kaydedilemedi. Önce yeni Supabase "
                            f"SQL dosyasını çalıştırın. Ayrıntı: {ex}"
                        )
