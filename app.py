import streamlit as st
import pandas as pd
import numpy as np
import io
import json
from datetime import date, datetime

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

# ============================================================
# STREAMLIT SAYFA AYARLARI
# ============================================================
st.set_page_config(
    page_title="Gelişmiş Bütçe Simülatörü",
    layout="wide"
)

# ============================================================
# 🔒 KULLANICI GİRİŞ (LOGIN) SİSTEMİ
# ============================================================
if "oturum_acik" not in st.session_state:
    st.session_state.oturum_acik = False

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
                st.success("Giriş Başarılı! Sistem Yükleniyor...")
                st.rerun()
            else:
                st.error("Hatalı kullanıcı adı veya şifre girdiniz!")
                
    st.stop()

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
    "Yakıt Değişim YüzKg (%)", "Yakıt Anlık Değişim Oranı (%)", "Yakıt Değişim Periyodu (Ay)",
    "Enf. Değişim YüzKg (%)", "Enf. Değişim Periyodu (Ay)", "Esk. Baz Yakıt Fiyatı", "Esk. Yakıt Başlangıç Tarihi", "Esk. Enf. Başlangıç Tarihi"
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
NUMERIC_KOLONLAR = (["Yakıt Değişim YüzKg (%)", "Yakıt Anlık Değişim Oranı (%)", "Enf. Değişim YüzKg (%)", "Esk. Baz Yakıt Fiyatı"] +
                    kolonlar_25_Kg + kolonlar_25_tutar + kolonlar_25_fiyat + kolonlar_26_buyume + kolonlar_26_esk +
                    kolonlar_26_Kg + kolonlar_26_tutar + kolonlar_26_fiyat)

# Özel Sayfa Şablon Sütun Tanımları
data_ekran_sutunlari = [
    "Uniq ID", "Yıl", "Teslimat Tipi", "Atf Tipi", "Çıkış İl Adı", "Çıkış Şube Adı", "Varış İl Adı", "Varış Şube Adı",
    "İlk Okutma Şubesi", "Müşteri Kodu", "Müşteri Adı", "Müşteri Temsilcisi", "Sap Kodu", "Durum", "Kayıt Tarihi", "Müşteri Grubu",
    "Yakıt Değişim YüzKg (%)", "Yakıt Anlık Değişim Oranı (%)", "Yakıt Değişim Periyodu (Ay)", "Enf. Değişim YüzKg (%)",
    "Enf. Değişim Periyodu (Ay)", "Esk. Baz Yakıt Fiyatı", "Esk. Yakıt Başlangıç Tarihi", "Esk. Enf. Başlangıç Tarihi"
]
deg_anah_sutunlari = ["Müşteri Kodu", "Sap No", "Ünvan", "Müşteri Temsilcisi 1", "Müşteri Temsilcisi 2", "Değişim Anahtarı", "KDV Durumu", "Baz Yakıt Fiyatı"]
baz_yakit_sutunlari = ["Müşteri Kodu", "Müşteri Adı", "Müşteri Temsilcisi", "Durum", "KDV'li / KDV'siz", "Esk. Baz Yakıt Fiyatı", "Yakıt Fiyat"]
mazot_giriş_sutunlari = ["Baz Motorin"] + aylar
buyume_ekran_sutunlari = [
    "Müşteri Kodu", "Müşteri Adı", "Müşteri Temsilcisi", "Sap Kodu", "Durum", "Kayıt Tarihi", "Müşteri Grubu"
] + aylar + [
    "2024 ilk 9 ay Kg", "2025 ilk 9 ay Kg", "2025 % Kg pay", "Y To Y Kg", 
    "25 kullanılan büyüme", "KULLANICAK BÜYÜME", "Gelen Özet Bilgi", "Müşteriden Gelen Büyüme"
]

# ============================================================
# SESSION STATE & BULUT BAĞLANTISI
# ============================================================
if "data_sayfası_df" not in st.session_state: st.session_state.data_sayfası_df = pd.DataFrame(columns=data_ekran_sutunlari)
if "ana_veri" not in st.session_state: st.session_state.ana_veri = pd.DataFrame(columns=tum_kolonlar)
if "editor_key" not in st.session_state: st.session_state.editor_key = 0
if "musteri_ayarlari" not in st.session_state: st.session_state.musteri_ayarlari = {}
if "deg_anah_veri" not in st.session_state: st.session_state.deg_anah_veri = pd.DataFrame(columns=deg_anah_sutunlari)
if "baz_yakit_veri" not in st.session_state: st.session_state.baz_yakit_veri = pd.DataFrame(columns=baz_yakit_sutunlari)
if "musteri_ekran_df" not in st.session_state: st.session_state.musteri_ekran_df = pd.DataFrame()
if "buyume_ayarlari" not in st.session_state: st.session_state.buyume_ayarlari = {}
if "buyume_ekran_df" not in st.session_state: st.session_state.buyume_ekran_df = pd.DataFrame()

if "mazot_giriş_veri" not in st.session_state:
    st.session_state.mazot_giriş_veri = pd.DataFrame([{
        "Baz Motorin": 45.8416, "Ocak": 45.99, "Şubat": 46.82, "Mart": 47.66, "Nisan": 48.76,
        "Mayıs": 49.81, "Haziran": 50.52, "Temmuz": 50.99, "Ağustos": 51.51, "Eylül": 52.09,
        "Ekim": 52.92, "Kasım": 53.76, "Aralık": 54.60
    }])

GIZLI_SUPABASE_URL = "https://bejimguyethsxdyhtttp.supabase.co"
GIZLI_SUPABASE_KEY = "sb_publishable_TXXAdObu4G68RolqZYwdIA_6xJiQIXO"

def get_supabase_client():
    if not SUPABASE_AVAILABLE: return None
    try: return create_client(GIZLI_SUPABASE_URL, GIZLI_SUPABASE_KEY)
    except: return None

# ============================================================
# VERİ TEMİZLEME MOTORU
# ============================================================
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
    value = value.replace("₺", "").replace("%", "").replace(" ", "")
    if "," in value and "." in value: value = value.replace(".", "").replace(",", ".")
    elif "," in value: value = value.replace(",", ".")
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

# ============================================================
# ARAYÜZ SEKMELERİ (9 SEKMELİ YAPI 🎉)
# ============================================================
sekmeler = st.tabs([
    "📁 Data", "🚚 Çarşaf Liste & Bütçe", "📅 Çalışma Günleri Takvimi", "☁️ Bulut Revizyon Yönetimi",
    "👤 Yeni-Bütçe Müşteri", "⚙️ değ.anah.-yakıt-kdv", "⛽ Baz Yakıt Fiyatları",
    "📊 2026 Mazot Analizi", "📈 Müşteri Büyüme Oranları"
])

client = get_supabase_client()
rev_secenekleri = {}
if client:
    try:
        log_res = client.table("revizyon_log").select("*").order("kayit_zamani", desc=True).execute()
        if log_res.data:
            rev_secenekleri = {f"{r['kayit_zamani'][:16]} | {r['olusturan_kisi']} - {r['revizyon_notu']}": r['revizyon_id'] for r in log_res.data}
    except: pass

# ------------------------------------------------------------
# 1. SEKME: 📁 DATA GİRİŞ VE ÇAPRAZ PARAMETRE HAVUZU (ULTRA HIZLI METRİK KALKANI 🚀)
# ------------------------------------------------------------
with sekmeler[0]:
    st.title("📁 Operasyonel Ana Data Yönetim Havuzu")
    st.markdown("Aşağıya operasyonel ham listenizi yükleyin. Yıl ve dosyanızdaki metrik tipini seçerek veri ambarını dinamik olarak besleyebilirsiniz.")

    # 🎯 DİNAMİK SEÇİCİLER
    c_cfg1, c_cfg2 = st.columns(2)
    with c_cfg1:
        secilen_yil = st.selectbox("📅 Yüklenecek / Gösterilecek Veri Hangi Yıla Ait?", ["2024", "2025", "2026"], index=1, key="data_cfg_yil")
    with c_cfg2:
        metrik_tipi = st.radio("📊 Excel'deki Hangi Sütun Kg Olarak Kabul Edilsin? (Metrik Tipi)", ["Kg (Örn: Ocak Kg)", "Kg (Örn: Ocak Kg)", "Tutar (Örn: Ocak Tutar)"], horizontal=True, key="data_cfg_metrik")

    sabit_data_sutunlari = [
        "Uniq ID", "Yıl", "Teslimat Tipi", "Atf Tipi", "Çıkış İl Adı", "Çıkış Şube Adı", "Varış İl Adı", "Varış Şube Adı",
        "İlk Okutma Şubesi", "Müşteri Kodu", "Müşteri Adı", "Müşteri Temsilcisi", "Sap Kodu", "Durum", "Kayıt Tarihi", "Müşteri Grubu",
        "Yakıt Değişim YüzKg (%)", "Yakıt Anlık Değişim Oranı (%)", "Yakıt Değişim Periyodu (Ay)", "Enf. Değişim YüzKg (%)",
        "Enf. Değişim Periyodu (Ay)", "Esk. Baz Yakıt Fiyatı", "Esk. Yakıt Başlangıç Tarihi", "Esk. Enf. Başlangıç Tarihi"
    ]
    
    dinamik_Kg_kolonlari = [f"{secilen_yil} {ay} Kg" for ay in aylar] + [f"{secilen_yil} Toplam Kg" ]
    yuklenen_data_havuzu = st.file_uploader("Data Listenizi Yükleyin (Excel/CSV)", type=["xlsx", "xls", "csv"], key="data_havuz_up")

    if yuklenen_data_havuzu:
        with st.spinner("⚡ Büyük veri seti işleniyor, RAM kalkanı aktif..."):
            df_d_giren = pd.read_csv(yuklenen_data_havuzu) if yuklenen_data_havuzu.name.lower().endswith(".csv") else pd.read_excel(yuklenen_data_havuzu)
            df_d_giren.columns = [str(c).strip() for c in df_d_giren.columns]
            df_d_giren["Müşteri Kodu"] = df_d_giren["Müşteri Kodu"].apply(guvenli_metin_kodu)
            
            sonek = " Kg" if "Kg" in metrik_tipi else (" Kg" if "Kg" in metrik_tipi else " Tutar")
            
            # 🎯 EN HIZLI RAM OPTİMİZASYONU: GEÇMİŞ YILLARDA (2024-2025) VERİYİ MÜŞTERİ BAZINDA ÖZETLEYEREK SIKIŞTIRMA
            if secilen_yil in ["2024", "2025"]:
                # Geçmiş yıllar için ham dosyadan sadece hacim içeren kolonları bul ve sayıya çevir
                mapped_cols = {}
                for ay in aylar:
                    for col in [f"{ay}{sonek}", f"{secilen_yil} {ay}{sonek}", ay, f"{secilen_yil} {ay}"]:
                        if col in df_d_giren.columns:
                            df_d_giren[col] = df_d_giren[col].apply(guvenli_sayi)
                            mapped_cols[col] = f"{secilen_yil} {ay} Kg"
                            break
                
                # Sadece Müşteri Kodu, Müşteri Grubu ve Hacimleri filtrele ve gruplayarak topla
                grup_sutunlari = ["Müşteri Kodu"]
                if "Müşteri Grubu" in df_d_giren.columns:
                    grup_sutunlari.append("Müşteri Grubu")
                    df_d_giren["Müşteri Grubu"] = df_d_giren["Müşteri Grubu"].fillna("DİĞER").astype(str).str.strip().str.upper()
                
                keep_cols = grup_sutunlari + list(mapped_cols.keys())
                df_compressed = df_d_giren[keep_cols].rename(columns=mapped_cols)
                df_summary = df_compressed.groupby(grup_sutunlari, as_index=False).sum()
                
                # Toplam kolonunu vektörel ekle
                calc_cols = [v for v in mapped_cols.values()]
                df_summary[f"{secilen_yil} Toplam Kg"] = df_summary[calc_cols].sum(axis=1)
                
                # Mevcut veri havuzu boş ise şablonu ata, dolu ise sadece Müşteri Kodu bazında yanal merge yap
                if st.session_state.data_sayfası_df.empty:
                    df_base = pd.DataFrame(columns=data_ekran_sutunlari)
                    df_base["Müşteri Kodu"] = df_summary["Müşteri Kodu"]
                    if "Müşteri Grubu" in df_summary.columns: df_base["Müşteri Grubu"] = df_summary["Müşteri Grubu"]
                    df_base["Yıl"] = "2026"
                    df_base["Durum"] = "GEÇERLİ"
                    
                    join_cols_id = ["Yıl", "Müşteri Kodu"]
                    df_base["Uniq ID"] = df_base[join_cols_id].fillna("").astype(str).agg("".join, axis=1)
                    
                    st.session_state.data_sayfası_df = pd.merge(df_base, df_summary, on="Müşteri Kodu", how="left")
                else:
                    if "Müşteri Grubu" in df_summary.columns and "Müşteri Grubu" in st.session_state.data_sayfası_df.columns:
                        df_summary = df_summary.drop(columns=["Müşteri Grubu"])
                    
                    st.session_state.data_sayfası_df = pd.merge(
                        st.session_state.data_sayfası_df, 
                        df_summary, 
                        on="Müşteri Kodu", 
                        how="left",
                        suffixes=('', '_new')
                    )
                    # Çakışan kolonları temizle
                    for col in calc_cols + [f"{secilen_yil} Toplam Kg"]:
                        if f"{col}_new" in st.session_state.data_sayfası_df.columns:
                            st.session_state.data_sayfası_df[col] = st.session_state.data_sayfası_df[col].fillna(0.0) + st.session_state.data_sayfası_df[f"{col}_new"].fillna(0.0)
                            st.session_state.data_sayfası_df = st.session_state.data_sayfası_df.drop(columns=[f"{col}_new"])
                
                st.success(f"🎉 {secilen_yil} yılı geçmiş verisi Müşteri bazında özetlenerek hafızaya sıkıştırıldı! RAM yükü engellendi.")

            else:
                # 🎯 2026 ASIL DETAYLI İŞLEM YILI YÜKLEME STRATEJİSİ
                join_cols = ["Yıl", "Teslimat Tipi", "Atf Tipi", "Çıkış İl Adı", "Çıkış Şube Adı", "Varış İl Adı", "Varış Şube Adı", "İlk Okutma Şubesi", "Müşteri Kodu"]
                for c in join_cols:
                    if c not in df_d_giren.columns: df_d_giren[c] = ""
                
                df_d_giren["Uniq ID"] = df_d_giren[join_cols].fillna("").astype(str).agg("".join, axis=1).str.replace("nan", "").str.replace("None", "")
                
                if st.session_state.musteri_ayarlari:
                    m_ayarlar_df = pd.DataFrame.from_dict(st.session_state.musteri_ayarlari, orient='index').reset_index().rename(columns={"index": "Müşteri Kodu"})
                    df_d_giren = pd.merge(df_d_giren, m_ayarlar_df[["Müşteri Kodu", "Durum_2"]], on="Müşteri Kodu", how="left") if "Durum_2" in m_ayarlar_df.columns else df_d_giren.assign(Durum_2=np.nan)
                else: df_d_giren["Durum_2"] = np.nan
                    
                if "Durum" not in df_d_giren.columns: df_d_giren["Durum"] = "GEÇERLİ"
                df_d_giren["Durum_Nihai"] = df_d_giren["Durum_2"].fillna(df_d_giren["Durum"]).fillna("GEÇERLİ")

                if not st.session_state.baz_yakit_veri.empty:
                    by_df = st.session_state.baz_yakit_veri.drop_duplicates(subset=["Müşteri Kodu"])[["Müşteri Kodu", "Yakıt Fiyat"]]
                    df_d_giren = pd.merge(df_d_giren, by_df, on="Müşteri Kodu", how="left")
                else: df_d_giren["Yakıt Fiyat"] = np.nan
                    
                if "Esk. Baz Yakıt Fiyatı" not in df_d_giren.columns: df_d_giren["Esk. Baz Yakıt Fiyatı"] = 0.0
                df_d_giren["Esk_Baz_Yakit_Nihai"] = df_d_giren["Yakıt Fiyat"].fillna(df_d_giren["Esk. Baz Yakıt Fiyatı"]).apply(guvenli_sayi)

                fallback_cols = ["Kayıt Tarihi", "Müşteri Grubu", "Yakıt Değişim YüzKg (%)", "Yakıt Anlık Değişim Oranı (%)", "Yakıt Değişim Periyodu (Ay)", "Enf. Değişim YüzKg (%)", "Enf. Değişim Periyodu (Ay)", "Esk. Yakıt Başlangıç Tarihi", "Esk. Enf. Başlangıç Tarihi"]
                if not st.session_state.ana_veri.empty:
                    # ÇÖZÜM: assign() yerine köşeli parantez ile standart atama yapıyoruz
                    av_df = st.session_state.ana_veri.copy()
                    av_df["Müşteri Kodu"] = av_df["Müşteri Kodu"].apply(guvenli_metin_kodu)
                    
                    av_df = av_df.drop_duplicates(subset=["Müşteri Kodu"])[["Müşteri Kodu"] + [c for c in fallback_cols if c in av_df.columns]]
                    df_d_giren = pd.merge(df_d_giren, av_df, on="Müşteri Kodu", how="left", suffixes=("", "_av"))
                
                df_built = pd.DataFrame()
                df_built["Uniq ID"] = df_d_giren["Uniq ID"]
                for c in ["Yıl", "Teslimat Tipi", "Atf Tipi", "Çıkış İl Adı", "Çıkış Şube Adı", "Varış İl Adı", "Varış Şube Adı", "İlk Okutma Şubesi", "Müşteri Kodu", "Müşteri Adı", "Müşteri Temsilcisi"]:
                    df_built[c] = df_d_giren[c] if c in df_d_giren.columns else ""
                df_built["Sap Kodu"] = df_d_giren["Sap Kodu"] if "Sap Kodu" in df_d_giren.columns else (df_d_giren["Sap No"] if "Sap No" in df_d_giren.columns else "")
                df_built["Durum"] = df_d_giren["Durum_Nihai"]
                
                for c in fallback_cols:
                    col_av = f"{c}_av"
                    if col_av in df_d_giren.columns:
                        df_built[c] = df_d_giren[c].fillna(df_d_giren[col_av]) if c in df_d_giren.columns else df_d_giren[col_av]
                    else:
                        df_built[c] = df_d_giren[c] if c in df_d_giren.columns else ("DİĞER" if c == "Müşteri Grubu" else "")
                
                df_built["Esk. Baz Yakıt Fiyatı"] = df_d_giren["Esk_Baz_Yakit_Nihai"]
                df_built["Yakıt Değişim YüzKg (%)"] = df_built["Yakıt Değişim YüzKg (%)"].apply(guvenli_sayi)
                df_built["Yakıt Anlık Değişim Oranı (%)"] = df_built["Yakıt Anlık Değişim Oranı (%)"].apply(guvenli_sayi)
                df_built["Enf. Değişim YüzKg (%)"] = df_built["Enf. Değişim YüzKg (%)"].apply(guvenli_sayi)
                df_built["Yakıt Değişim Periyodu (Ay)"] = df_built["Yakıt Değişim Periyodu (Ay)"].apply(lambda x: guvenli_tamsayi(x, nullable=False))
                df_built["Enf. Değişim Periyodu (Ay)"] = df_built["Enf. Değişim Periyodu (Ay)"].apply(lambda x: guvenli_tamsayi(x, nullable=False))

                toplam_Kg = np.zeros(len(df_d_giren))
                for ay in aylar:
                    col_to_use = None
                    for col in [f"{ay}{sonek}", f"{secilen_yil} {ay}{sonek}", ay, f"{secilen_yil} {ay}"]:
                        if col in df_d_giren.columns:
                            col_to_use = col
                            break
                    vals = df_d_giren[col_to_use].apply(guvenli_sayi).to_numpy() if col_to_use else np.zeros(len(df_d_giren))
                    df_built[f"{secilen_yil} {ay} Kg"] = vals
                    toplam_Kg += vals
                df_built[f"{secilen_yil} Toplam Kg"] = toplam_Kg

                if st.session_state.data_sayfası_df.empty:
                    agg_init = {col: ("sum" if "Kg" in col else "first") for col in df_built.columns if col != "Uniq ID"}
                    st.session_state.data_sayfası_df = df_built.groupby("Uniq ID", as_index=False).agg(agg_init)
                else:
                    df_combined = pd.concat([st.session_state.data_sayfası_df, df_built], ignore_index=True)
                    agg_strategy = {col: ("sum" if "Kg" in col else "first") for col in df_combined.columns if col != "Uniq ID"}
                    st.session_state.data_sayfası_df = df_combined.groupby("Uniq ID", as_index=False).agg(agg_strategy)
                    
                st.success(f"🎉 2026 Ana bütçe yılı detaylı sevkiyat satırları başarıyla entegre edildi.")

    # Arayüz Gösterim Ekranı
    if st.session_state.pop("data_bulut_yukleme_basarili", False):
        st.success("🎉 Kayıtlı Data havuzu buluttan getirildi. 2024 ve 2025 değerleri artık büyüme sayfasında kullanılabilir.")

    if not st.session_state.data_sayfası_df.empty:
        gosterim_kolonlari = [c for c in sabit_data_sutunlari + dinamik_Kg_kolonlari if c in st.session_state.data_sayfası_df.columns]
        df_ekran = st.session_state.data_sayfası_df[gosterim_kolonlari]
        
        toplam_satir_sayisi = len(df_ekran)
        st.warning(f"⚠️ Sistemde toplam {toplam_satir_sayisi:,} satır veri bulunuyor. Tarayıcının çökmesini engellemek amacıyla ilk 500 satır listelenmektedir.")
        
        st.dataframe(
            df_ekran.head(500), 
            use_container_width=True,
            column_config={
                "Esk. Baz Yakıt Fiyatı": st.column_config.NumberColumn("Esk. Baz Yakıt Fiyatı", format="₺%.2f"),
                **{c: st.column_config.NumberColumn(c, format="%d") for c in dinamik_Kg_kolonlari}
            }
        )

    else:
        st.info("Lütfen işlem yapmak istediğiniz ham operasyonel Excel/CSV dosyanızı yükleyin ya da alttaki butondan bulut yedeğinizi çağırın.")

    # Bu bölüm özellikle veri havuzu boşken de görünür. Böylece uygulama ilk
    # açıldığında dosya yüklemeden daha önce mühürlenmiş kayıt çağrılabilir.
    st.markdown("---")
    st.subheader("☁️ Bulut Data Kaydı")
    st.caption("2024 ve 2025'i bir kez mühürleyin; sonraki oturumlarda aynı versiyonu seçip buluttan getirin.")

    if not client:
        st.error("Bulut bağlantısı kurulamadı. Supabase paketi, URL ve anahtar ayarlarını kontrol edin.")
    elif not rev_secenekleri:
        st.warning("Bulut Revizyon Yönetimi bölümünde henüz bir revizyon bulunmuyor. Önce bir revizyon oluşturun; ardından Data sekmesine geri dönün.")
    else:
        secilen_revizyon_etiketi = st.selectbox(
            "Data Yönetimi İçin Bulut Versiyonu",
            list(rev_secenekleri.keys()),
            key="sb_data_rev"
        )
        r_id_data = rev_secenekleri[secilen_revizyon_etiketi]
        cd1, cd2, cd3 = st.columns(3)

        if not st.session_state.data_sayfası_df.empty:
            output_d_excel = io.BytesIO()
            with pd.ExcelWriter(output_d_excel, engine="openpyxl") as writer:
                st.session_state.data_sayfası_df.to_excel(writer, index=False, sheet_name="Data_Master")
            cd1.download_button(
                "📥 Tüm Tabloyu Excel Olarak İndir",
                output_d_excel.getvalue(),
                "data_master_havuz.xlsx",
                use_container_width=True
            )
        else:
            cd1.info("Excel indirmek için önce veri yükleyin veya buluttan çağırın.")

        kaydet_tiklandi = cd2.button(
            "💾 Bu Tabloyu Buluta Kaydet (Mühürle)",
            type="primary",
            use_container_width=True,
            key="btn_data_cloud_sv",
            disabled=st.session_state.data_sayfası_df.empty
        )

        getir_tiklandi = cd3.button(
            "🔄 Dosya Yüklemeden Buluttan Datayı Getir",
            type="secondary",
            use_container_width=True,
            key="btn_data_cloud_ld"
        )

        if kaydet_tiklandi:
            tum_Kg_sutunlari_db = []
            for y in ["2024", "2025", "2026"]:
                for m in aylar:
                    tum_Kg_sutunlari_db.append(f"{y} {m} Kg")
                tum_Kg_sutunlari_db.append(f"{y} Toplam Kg")

            izin_verilen_db_sutunlari_data = sabit_data_sutunlari + tum_Kg_sutunlari_db
            mevcut_db_sutunlari = [
                c for c in izin_verilen_db_sutunlari_data
                if c in st.session_state.data_sayfası_df.columns
            ]
            df_to_save = (
                st.session_state.data_sayfası_df[mevcut_db_sutunlari]
                .copy()
                .assign(revizyon_id=r_id_data)
                .replace({np.nan: None})
            )
            data_records = df_to_save.to_dict(orient="records")

            try:
                with st.spinner(f"🚀 {len(data_records):,} satır buluta aktarılıyor..."):
                    client.table("data_tablosu").delete().eq("revizyon_id", r_id_data).execute()
                    for i in range(0, len(data_records), 500):
                        client.table("data_tablosu").insert(data_records[i:i + 500]).execute()
                st.success("🎉 Data havuzu bu revizyona başarıyla mühürlendi.")
            except Exception as ex:
                st.error(f"Data havuzu buluta kaydedilemedi: {ex}")

        if getir_tiklandi:
            try:
                with st.spinner("Kayıtlı Data havuzunun tamamı buluttan getiriliyor..."):
                    tum_kayitlar = []
                    baslangic = 0
                    paket_boyutu = 1000

                    while True:
                        d_res = (
                            client.table("data_tablosu")
                            .select("*")
                            .eq("revizyon_id", r_id_data)
                            .range(baslangic, baslangic + paket_boyutu - 1)
                            .execute()
                        )
                        paket = d_res.data or []
                        tum_kayitlar.extend(paket)
                        if len(paket) < paket_boyutu:
                            break
                        baslangic += paket_boyutu

                if tum_kayitlar:
                    gelen_d_df = pd.DataFrame(tum_kayitlar)
                    gelen_d_df = gelen_d_df.drop(
                        columns=[c for c in ["id", "revizyon_id"] if c in gelen_d_df.columns]
                    )
                    gelen_d_df["Müşteri Kodu"] = gelen_d_df["Müşteri Kodu"].apply(guvenli_metin_kodu)

                    for y in ["2024", "2025", "2026"]:
                        yil_aylari = []
                        for m in aylar:
                            col = f"{y} {m} Kg"
                            if col in gelen_d_df.columns:
                                gelen_d_df[col] = gelen_d_df[col].apply(guvenli_sayi)
                                yil_aylari.append(col)
                        if yil_aylari:
                            gelen_d_df[f"{y} Toplam Kg"] = gelen_d_df[yil_aylari].sum(axis=1)

                    st.session_state.data_sayfası_df = gelen_d_df
                    st.session_state.data_bulut_yukleme_basarili = True
                    st.rerun()
                else:
                    st.warning("Seçilen revizyona ait mühürlenmiş Data kaydı bulunamadı.")
            except Exception as ex:
                st.error(f"Data havuzu buluttan getirilemedi: {ex}")

# ------------------------------------------------------------
# 2. SEKME: ÇARŞAF LİSTE & BÜTÇE
# ------------------------------------------------------------
with sekmeler[1]:
    st.title("🚚 Operasyonel Bütçe Simülatörü")
    yuklenen_dosya = st.sidebar.file_uploader("Excel / CSV Yükle", type=["xlsx", "xls", "csv"], key="main_file_uploader_key")
    yukleme_tipi = st.sidebar.radio("Yükleme Amacı:", ["Yeni Satırlar Ekle", "Düşeyara (VLOOKUP) ile Güncelle"], key="main_upload_purpose")
    
    c1, c2 = st.sidebar.columns(2)
    if c1.button("📥 Veriyi İşle", key="veri_isle_btn") and yuklenen_dosya:
        yeni_df = pd.read_csv(yuklenen_dosya) if yuklenen_dosya.name.lower().endswith(".csv") else pd.read_excel(yuklenen_dosya)
        yeni_df.columns = [str(c).strip() for c in yeni_df.columns]
        if yukleme_tipi == "Düşeyara (VLOOKUP) ile Güncelle":
            if "Uniq ID" in yeni_df.columns and not st.session_state.ana_veri.empty:
                st.session_state.ana_veri["Uniq ID"] = st.session_state.ana_veri["Uniq ID"].astype(str)
                yeni_df["Uniq ID"] = yeni_df["Uniq ID"].astype(str)
                existing_df = st.session_state.ana_veri.set_index("Uniq ID")
                update_df = yeni_df.set_index("Uniq ID")
                guncellenecek_sutunlar = [c for c in update_df.columns if c in existing_df.columns and c != "Uniq ID"]
                existing_df.update(update_df[guncellenecek_sutunlar])
                st.session_state.ana_veri = existing_df.reset_index()
                st.session_state.ana_veri["Uniq ID"] = st.session_state.ana_veri["Uniq ID"].apply(guvenli_tamsayi)
                st.session_state.editor_key += 1
                st.sidebar.success("Düşeyara başarıyla tamamlandı!")
                st.rerun()
        else:
            yeni_df = yeni_df.reindex(columns=tum_kolonlar)
            st.session_state.ana_veri = pd.concat([st.session_state.ana_veri, yeni_df], ignore_index=True)
            st.session_state.editor_key += 1
            st.rerun()

    if c2.button("🗑️ Havuzu Temizle", key="havuzu_temizle_btn"):
        st.session_state.ana_veri = pd.DataFrame(columns=tum_kolonlar)
        st.session_state.musteri_ayarlari = {}
        st.session_state.editor_key += 1
        st.rerun()

    filtre_kolonlari = st.sidebar.multiselect("Filtrelemek İstediğiniz Sütunları Seçin:", options=tum_kolonlar, key="main_filter_cols")
    mask = pd.Series(True, index=st.session_state.ana_veri.index)
    if filtre_kolonlari:
        for col in filtre_kolonlari:
            unique_vals = st.session_state.ana_veri[col].dropna().unique().tolist()
            secilen_degerler = st.sidebar.multiselect(f"{col}:", options=unique_vals, default=unique_vals, key=f"filter_{col}")
            mask &= st.session_state.ana_veri[col].isin(secilen_degerler)
            
    gosterilecek_df = st.session_state.ana_veri[mask]
    gizli_df = st.session_state.ana_veri[~mask]
    global_enflasyon = st.sidebar.slider("2026 Global Eskalasyon (%)", 0, 100, 0, step=1, key="main_global_esk_slider")
    
    duzenlenen_df = st.data_editor(gosterilecek_df, num_rows="dynamic", use_container_width=True, height=400, key=f"butce_veri_{st.session_state.editor_key}")
    df_birlestirilmis = pd.concat([gizli_df, duzenlenen_df]).copy()

    if not df_birlestirilmis.empty:
        df_nihai = df_birlestirilmis.copy()
        df_nihai.columns = [str(c).strip() for c in df_nihai.columns]
        df_nihai = df_nihai.reindex(columns=tum_kolonlar)
        
        # ⚡ VEKTÖREL HESAPLAMA MOTORU (HIZ OPTİMİZE)
        for ay in aylar:
            Kg_col, fiyat_col, tutar_col = f"2025 {ay} Kg", f"2025 {ay} Fiyat", f"2025 {ay} Tutar"
            df_nihai[Kg_col] = pd.to_numeric(df_nihai[Kg_col].apply(guvenli_sayi), errors='coerce').fillna(0.0)
            df_nihai[fiyat_col] = pd.to_numeric(df_nihai[fiyat_col].apply(guvenli_sayi), errors='coerce').fillna(0.0)
            df_nihai[tutar_col] = df_nihai[Kg_col] * df_nihai[fiyat_col]
            
        onceki_fiyat = pd.to_numeric(df_nihai["2025 Aralık Fiyat"].apply(guvenli_sayi), errors='coerce').fillna(0.0)
        for ay in aylar:
            buyume_col, esk_col, Kg_col, fiyat_col, tutar_col = f"2026 {ay} Büyüme", f"2026 {ay} Esk.", f"2026 {ay} Kg", f"2026 {ay} Fiyat", f"2026 {ay} Tutar"
            df_nihai[buyume_col] = pd.to_numeric(df_nihai[buyume_col].apply(guvenli_sayi), errors='coerce').fillna(0.0)
            df_nihai[esk_col] = pd.to_numeric(df_nihai[esk_col].apply(guvenli_sayi), errors='coerce').fillna(0.0)
            
            aktif_eskalasyon = np.where(df_nihai[esk_col] == 0, float(global_enflasyon), df_nihai[esk_col])
            df_nihai[Kg_col] = df_nihai[f"2025 {ay} Kg"] * (1 + (df_nihai[buyume_col] / 100))
            df_nihai[fiyat_col] = onceki_fiyat * (1 + (aktif_eskalasyon / 100))
            df_nihai[tutar_col] = df_nihai[Kg_col] * df_nihai[fiyat_col]
            onceki_fiyat = df_nihai[fiyat_col]
            
        st.session_state.ana_veri = df_nihai.copy()

        st.markdown("---")
        t25 = sum(df_nihai[f"2025 {ay} Tutar"].sum() for ay in aylar)
        t26 = sum(df_nihai[f"2026 {ay} Tutar"].sum() for ay in aylar)
        m1, m2, m3 = st.columns(3)
        m1.metric("2025 Toplam Gerçekleşen", value=f"₺{t25:,.2f}")
        m2.metric("2026 Projeksiyon Toplamı", value=f"₺{t26:,.2f}", delta="Artış")
        m3.metric("Bütçeye Gelen Ek Yük", value=f"₺{(t26-t25):,.2f}")

        col_down1, col_down2 = st.columns([1, 1.5])
        with col_down1:
            output_excel = io.BytesIO()
            with pd.ExcelWriter(output_excel, engine="openpyxl") as writer: df_nihai.to_excel(writer, index=False, sheet_name="Bütçe")
            st.download_button("📥 Excel Olarak İndir", output_excel.getvalue(), "horoz_butce.xlsx", use_container_width=True, key="main_excel_down_btn")
        with col_down2:
            with st.expander("🚀 Yeni Bir Versiyon Olarak Buluta Kaydet", expanded=True):
                kisi = st.text_input("Revizyonu Yapan Kişi", key="main_save_kisi")
                not_ = st.text_input("Revizyon Notu", key="main_save_not")
                if st.button("💾 Senaryoyu Kaydet", use_container_width=True, key="main_save_btn"):
                    if client:
                        try:
                            df_bulut, records = supabase_verisini_hazirla(df_nihai)
                            yeni_rev_id = f"REV-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                            client.table("revizyon_log").insert({"revizyon_id": yeni_rev_id, "olusturan_kisi": kisi, "revizyon_notu": not_}).execute()
                            for r in records: r["revizyon_id"] = yeni_rev_id
                            for i in range(0, len(records), 500): client.table("butce_tablosu").insert(records[i:i+500]).execute()
                            st.success(f"🎉 Kaydedildi: {yeni_rev_id}")
                            st.rerun()
                        except Exception as e: st.error(f"Hata: {e}")
        st.dataframe(df_nihai, use_container_width=True)

# ------------------------------------------------------------
# 3. SEKME: ÇALIŞMA GÜNLERİ (KAYIT VE EXCEL DESTEKLİ DİNAMİK MATRİS 📅)
# ------------------------------------------------------------
with sekmeler[2]:
    st.title("📅 Operasyonel Çalışma Günleri Takvimi")
    st.markdown("Aşağıdaki matristen çalışma günlerini düzenleyebilirsiniz. Yapılan değişiklikleri **Buluta Kaydet** butonu ile kalıcı hale getirebilir veya **Excel** olarak indirebilirsiniz.")

    # 🚀 @st.fragment KALKANI: Tüm uygulamayı yormadan sadece takvim işlemlerini ışık hızında yapar
    @st.fragment
    def takvim_modulunu_calistir():
        # 1. OTOMATİK BULUT BAĞLANTISI VE HAFIZA KURULUMU
        if "takvim_verisi_yillar" not in st.session_state:
            takvim_yuklendi_mi = False
            
            # Uygulama ilk açıldığında veriyi otomatik olarak buluttan çekmeyi dene
            if client:
                try:
                    tk_res = client.table("takvim_tablosu").select("*").execute()
                    if tk_res.data:
                        df_cloud_tk = pd.DataFrame(tk_res.data)
                        if "id" in df_cloud_tk.columns: 
                            df_cloud_tk = df_cloud_tk.drop(columns=["id"])
                        # Sütun sıralamasını garanti altına alıyoruz
                        takvim_sirasi = ["YIL"] + aylar
                        st.session_state.takvim_verisi_yillar = df_cloud_tk[takvim_sirasi]
                        takvim_yuklendi_mi = True
                except:
                    pass # Bulut tablosu henüz yoksa veya hata verirse varsayılana düşer
            
            # Eğer bulutta veri yoksa şablonu varsayılan değerlerle oluştur
            if not takvim_yuklendi_mi:
                st.session_state.takvim_verisi_yillar = pd.DataFrame([
                    {"YIL": "2024", "Ocak": 26, "Şubat": 25, "Mart": 26, "Nisan": 23, "Mayıs": 26, "Haziran": 22, "Temmuz": 27, "Ağustos": 27, "Eylül": 25, "Ekim": 27, "Kasım": 26, "Aralık": 26},
                    {"YIL": "2025", "Ocak": 26, "Şubat": 24, "Mart": 25, "Nisan": 25, "Mayıs": 26, "Haziran": 22, "Temmuz": 26, "Ağustos": 26, "Eylül": 26, "Ekim": 26, "Kasım": 25, "Aralık": 27},
                    {"YIL": "2026", "Ocak": 26, "Şubat": 24, "Mart": 23, "Nisan": 26, "Mayıs": 21, "Haziran": 26, "Temmuz": 26, "Ağustos": 26, "Eylül": 26, "Ekim": 26, "Kasım": 25, "Aralık": 27},
                    {"YIL": "2027", "Ocak": 0, "Şubat": 0, "Mart": 0, "Nisan": 0, "Mayıs": 0, "Haziran": 0, "Temmuz": 0, "Ağustos": 0, "Eylül": 0, "Ekim": 0, "Kasım": 0, "Aralık": 0}
                ])

        # 2. CANLI MATEMATİKSEL FORMÜLLERİN ÇALIŞTIRILMASI
        df_yillar = st.session_state.takvim_verisi_yillar.copy()
        for m in aylar:
            df_yillar[m] = pd.to_numeric(df_yillar[m].apply(guvenli_sayi), errors='coerce').fillna(0.0)
            
        # Satır bazlı yıllık toplam gün formülü
        df_yillar["Toplam"] = df_yillar[aylar].sum(axis=1)

        def yil_satiri_getir(yr_str):
            match = df_yillar[df_yillar["YIL"] == yr_str]
            return match.iloc[0] if not match.empty else None

        # Geçmişe dönük oran satırlarının dinamik hesaplanması
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

        # 3. GELİŞMİŞ VERİ EDİTÖRÜ GÖSTERİMİ
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

        # 4. DEĞİŞİKLİKLERİ ANLIK HAFIZAYA İŞLEME MOTORU
        satir_sayisi = len(st.session_state.takvim_verisi_yillar)
        just_real_years = edited_calendar.iloc[:satir_sayisi].copy()
        
        degisim_var = False
        for i in range(satir_sayisi):
            for m in aylar:
                eski = float(guvenli_sayi(st.session_state.takvim_verisi_yillar.iloc[i][m]))
                yeni = float(guvenli_sayi(just_real_years.iloc[i][m]))
                
                if abs(eski - yeni) > 0.0001:
                    degisim_var = True
                    st.session_state.takvim_verION_yillar = just_real_years # Güncel matrisi kilitle
                    st.session_state.takvim_verisi_yillar.at[i, m] = yeni
                    
        if degisim_var:
            try: st.rerun(scope="fragment")
            except: st.rerun()

        # 5. 📥 EXCEL İNDİRME VE 💾 BULUTA KAYDETME PANELİ
        st.markdown("<br>", unsafe_allow_html=True)
        c_tk1, c_tk2 = st.columns(2)
        
        # Excel İhracat Motoru (Tüm oranlar ve toplamlar dahil tam döküm verir)
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
            
        # Bulut Mühürleme Motoru
        with c_tk2:
            if client:
                if st.button("💾 Değişiklikleri Buluta Kalıcı Kaydet", type="primary", use_container_width=True, key="btn_tk_cloud_save"):
                    # Oran satırlarını atıp sadece saf yıl verilerini temizce JSON/Sözlük formatına çeviriyoruz
                    clean_save_df = st.session_state.takvim_verisi_yillar.copy()
                    tk_records = [{c: json_uyumlu_deger(v) for c, v in row.items()} for _, row in clean_save_df.iterrows()]
                    
                    with st.spinner("Takvim bulut ambarına mühürleniyor..."):
                        try:
                            # Eski takvim kayıtlarını sıfırla ve yenilerini yaz
                            client.table("takvim_tablosu").delete().gte("YIL", "2020").execute()
                            client.table("takvim_tablosu").insert(tk_records).execute()
                            st.success("🎉 Harika! Çalışma günleri veritabanına kalıcı olarak mühürlendi. Uygulama kapansa da silinmez.")
                        except Exception as e:
                            st.error(f"Kayıt esnasında bulut hatası oluştu: {e}")
            else:
                st.info("Bulut bağlantısı aktif olmadığı için kalıcı kayıt devre dışı, verileriniz tarayıcı açık kaldığı sürece korunacaktır.")

    # Modülü güvenli alanda tetikle
    takvim_modulunu_calistir()
# ------------------------------------------------------------
# 4. SEKME: BULUT REVİZYON YÖNETİMİ
# ------------------------------------------------------------
with sekmeler[3]:
    st.title("☁️ Bulut Revizyon Geçmişi")
    if rev_secenekleri:
        df_log_gorsel = pd.DataFrame(list(rev_secenekleri.keys()), columns=["Kayıt Bilgileri"])
        df_log_gorsel.insert(0, "Seç", False)
        edited_log = st.data_editor(df_log_gorsel, hide_index=True, use_container_width=True, key="rev_history_grid")
        secili_satirlar = edited_log[edited_log["Seç"] == True]
        if len(secili_satirlar) == 1:
            lbl = secili_satirlar.iloc[0]["Kayıt Bilgileri"]
            secili_rev = rev_secenekleri[lbl]
            st.markdown("---")
            c_sol, c_sag = st.columns(2)
            if c_sol.button("📥 Seçili Versiyonu Ekrana Çek (Yükle)", type="primary", use_container_width=True, key="load_selected_rev_btn"):
                with st.spinner("İndiriliyor..."):
                    data_res = client.table("butce_tablosu").select("*").eq("revizyon_id", secili_rev).execute()
                    if data_res.data:
                        st.session_state.ana_veri = pd.DataFrame(data_res.data).reindex(columns=tum_kolonlar)
                        st.session_state.editor_key += 1
                        st.success("🎉 Yüklendi!")
                        st.rerun()
            if c_sag.button("🗑️ Seçili Versiyonu Kalıcı Olarak Sil", type="secondary", use_container_width=True, key="delete_selected_rev_btn"):
                client.table("butce_tablosu").delete().eq("revizyon_id", secili_rev).execute()
                client.table("revizyon_log").delete().eq("revizyon_id", secili_rev).execute()
                client.table("deg_anah_tablosu").delete().eq("revizyon_id", secili_rev).execute()
                client.table("baz_yakit_tablosu").delete().eq("revizyon_id", secili_rev).execute()
                client.table("musteri_detay_tablosu").delete().eq("revizyon_id", secili_rev).execute()
                client.table("mazot_tablosu").delete().eq("revizyon_id", secili_rev).execute()
                client.table("buyume_tablosu").delete().eq("revizyon_id", secili_rev).execute()
                client.table("data_tablosu").delete().eq("revizyon_id", secili_rev).execute()
                st.success("Silindi.")
                st.rerun()

# ------------------------------------------------------------
# 5. SEKME: YENİ-BÜTÇE MÜŞTERİ
# ------------------------------------------------------------
with sekmeler[4]:
    st.title("👤 Yeni-Bütçe Müşteri Detay Yönetimi")
    yuklenen_musteri = st.file_uploader("Müşteri Listenizi Yükleyin", type=["xlsx", "xls", "csv"], key="m_sablon_up")

    if yuklenen_musteri:
        df_hedef = pd.read_csv(yuklenen_musteri) if yuklenen_musteri.name.lower().endswith(".csv") else pd.read_excel(yuklenen_musteri)
        if "Müşteri Kodu" in df_hedef.columns:
            df_hedef["Müşteri Kodu"] = df_hedef["Müşteri Kodu"].apply(guvenli_metin_kodu)
            aktif_aylar_2026 = []
            dolu_ay_sayisi = 0
            if not st.session_state.ana_veri.empty:
                df_m_tmp = st.session_state.ana_veri.copy()
                df_m_tmp["Müşteri Kodu"] = df_m_tmp["Müşteri Kodu"].apply(guvenli_metin_kodu)
                for ay in aylar:
                    col_Kg = f"2026 {ay} Kg"
                    if col_Kg in df_m_tmp.columns and df_m_tmp[col_Kg].apply(guvenli_sayi).sum() > 0:
                        aktif_aylar_2026.append(col_Kg)
                dolu_ay_sayisi = len(aktif_aylar_2026)
            
            Kg_toplam_kolon_adi = f"{max(1, dolu_ay_sayisi)} Ay Toplam Kg"
            if not st.session_state.ana_veri.empty and aktif_aylar_2026:
                df_m_tmp[Kg_toplam_kolon_adi] = df_m_tmp[aktif_aylar_2026].sum(axis=1)
                Kg_grouped = df_m_tmp.groupby("Müşteri Kodu", as_index=False)[Kg_toplam_kolon_adi].sum()
                df_hedef = pd.merge(df_hedef, Kg_grouped, on="Müşteri Kodu", how="left")
            else: df_hedef[Kg_toplam_kolon_adi] = 0.0

            df_hedef[Kg_toplam_kolon_adi] = df_hedef[Kg_toplam_kolon_adi].fillna(0.0)

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
            st.session_state.musteri_ekran_df = df_hedef.copy()

    if not st.session_state.musteri_ekran_df.empty:
        df_gosterim = st.session_state.musteri_ekran_df.copy()
        df_gosterim["Değişim kontrol"] = df_gosterim.apply(lambda r: "DOĞRU" if str(r.get("Durum", "")).strip().upper() == str(r.get("Durum_2", "")).strip().upper() else "YANLIŞ", axis=1)
        gosterilecek_kolonlar = [c for c in df_gosterim.columns if not any(m in str(c) for m in aylar)]
        df_gosterim = df_gosterim[gosterilecek_kolonlar]

        kilitli = [c for c in df_gosterim.columns if c not in ["Yeni/Bütçelenen Müşteri", "Durum_2", "Durum_3", "Serbest Not"]]
        edited_m = st.data_editor(df_gosterim, use_container_width=True, height=400, disabled=kilitli,
                                  column_config={
                                      "Yeni/Bütçelenen Müşteri": st.column_config.SelectboxColumn("Yeni/Bütçelenen Müşteri", options=["01.Yeni Müşteri", "02.DOP Bütçe Dışı", "03.Bütçelenen"]),
                                      "Durum_2": st.column_config.SelectboxColumn("Durum_2", options=["GEÇERLİ", "GEÇERSİZ", None])
                                  }, key="ed_m_t4")
        st.session_state.musteri_ekran_df = edited_m.copy()

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
        r_id_m = rev_secenekleri[c_m2.selectbox("Müşteri Bilgileri İçin Bulut Versiyonu:", list(rev_secenekleri.keys()), key="sb_m_rev")]
        if not st.session_state.musteri_ekran_df.empty and c_m2.button("💾 Müşteri Kartlarını Buluta Kaydet", use_container_width=True, key="btn_m_cloud_sv"):
            izin_verilen_db_sutunlari = ["Müşteri Kodu", "Sap Kodu", "Müşteri Adı", "Müşteri Temsilcisi", "Durum", "Kayıt Tarihi", "Müşteri Grubu", "Yeni/Bütçelenen Müşteri", "Durum_2", "Durum_3", "Serbest Not", "Değişim kontrol"]
            m_records = [{col: json_uyumlu_deger(row[col]) for col in izin_verilen_db_sutunlari if col in row} for _, row in st.session_state.musteri_ekran_df.iterrows()]
            for r in m_records: r["revizyon_id"] = r_id_m
            client.table("musteri_detay_tablosu").delete().eq("revizyon_id", r_id_m).execute()
            for i in range(0, len(m_records), 500): client.table("musteri_detay_tablosu").insert(m_records[i:i+500]).execute()
            st.success("Buluta kilitlendi!")

        if c_m3.button("🔄 Dosya Yüklemeden Buluttan Müşteri Kartlarını Çek", use_container_width=True, key="btn_m_cloud_ld"):
            m_res = client.table("musteri_detay_tablosu").select("*").eq("revizyon_id", r_id_m).execute()
            if m_res.data:
                gelen_df = pd.DataFrame(m_res.data)
                if "id" in gelen_df.columns: gelen_df = gelen_df.drop(columns=["id"])
                aktif_aylar_2026 = []
                dolu_ay_sayisi = 0
                if not st.session_state.ana_veri.empty:
                    df_m_tmp = st.session_state.ana_veri.copy()
                    df_m_tmp["Müşteri Kodu"] = df_m_tmp["Müşteri Kodu"].apply(guvenli_metin_kodu)
                    for ay in aylar:
                        c_d = f"2026 {ay} Kg"
                        if c_d in df_m_tmp.columns and df_m_tmp[c_d].apply(guvenli_sayi).sum() > 0: aktif_aylar_2026.append(c_d)
                    dolu_ay_sayisi = len(aktif_aylar_2026)
                
                Kg_toplam_kolon_adi = f"{max(1, dolu_ay_sayisi)} Ay Toplam Kg"
                if not st.session_state.ana_veri.empty and aktif_aylar_2026:
                    df_m_tmp[Kg_toplam_kolon_adi] = df_m_tmp[aktif_aylar_2026].sum(axis=1)
                    Kg_grouped = df_m_tmp.groupby("Müşteri Kodu", as_index=False)[Kg_toplam_kolon_adi].sum()
                    gelen_df = pd.merge(gelen_df, Kg_grouped, on="Müşteri Kodu", how="left")
                else: gelen_df[Kg_toplam_kolon_adi] = 0.0
                
                gelen_df[Kg_toplam_kolon_adi] = gelen_df[Kg_toplam_kolon_adi].fillna(0.0)
                st.session_state.musteri_ekran_df = gelen_df.copy()
                for _, row in gelen_df.iterrows():
                    k = str(row["Müşteri Kodu"])
                    st.session_state.musteri_ayarlari[k] = {"Yeni/Bütçelenen Müşteri": row.get("Yeni/Bütçelenen Müşteri"), "Durum_2": row.get("Durum_2"), "Durum_3": row.get("Durum_3"), "Serbest Not": row.get("Serbest Not")}
                st.success("Buluttan çekildi!")
                st.rerun()

# ------------------------------------------------------------
# 6. SEKME: değ.anah.-yakıt-kdv PARAMETRE YÖNETİMİ
# ------------------------------------------------------------
with sekmeler[5]:
    st.title("⚙️ değ.anah.-yakıt-kdv Parametre Yönetimi")
    yuklenen_param = st.file_uploader("Parametre Şablonunu Yükle", type=["xlsx", "xls", "csv"], key="param_up")
    if yuklenen_param:
        df_p = pd.read_csv(yuklenen_param) if yuklenen_param.name.lower().endswith(".csv") else pd.read_excel(yuklenen_param)
        df_p.columns = [str(c).strip() for c in df_p.columns]
        if "Müşteri Kodu" in df_p.columns: df_p["Müşteri Kodu"] = df_p["Müşteri Kodu"].apply(guvenli_metin_kodu)
        st.session_state.deg_anah_veri = df_p.reindex(columns=deg_anah_sutunlari).copy()

    if not st.session_state.deg_anah_veri.empty:
        st.session_state.deg_anah_veri["Baz Yakıt Fiyatı"] = st.session_state.deg_anah_veri["Baz Yakıt Fiyatı"].apply(guvenli_sayi)

    edited_p = st.data_editor(st.session_state.deg_anah_veri, use_container_width=True, num_rows="dynamic", height=350,
                              column_config={
                                  "Müşteri Kodu": st.column_config.TextColumn("Müşteri Kodu", required=True),
                                  "KDV Durumu": st.column_config.SelectboxColumn("KDV Durumu", options=["KDV'li", "KDV'siz", "Muaf"]),
                                  "Baz Yakıt Fiyatı": st.column_config.NumberColumn("Baz Yakıt Fiyatı", format="₺%.2f")
                              }, key="ed_p_t5")
    st.session_state.deg_anah_veri = edited_p.copy()

    if rev_secenekleri:
        st.markdown("---")
        cp1, cp2, cp3 = st.columns(3)
        r_id_p = rev_secenekleri[cp1.selectbox("Parametre İçin Bulut Versiyonu:", list(rev_secenekleri.keys()), key="sb_p_rev")]
        if cp2.button("💾 Parametreleri Seçili Versiyona Kaydet", type="primary", use_container_width=True, key="btn_p_sv"):
            p_recs = [{str(col): json_uyumlu_deger(val) for col, val in row.items()} for _, row in edited_p.iterrows()]
            for r in p_recs: r["revizyon_id"] = r_id_p
            client.table("deg_anah_tablosu").delete().eq("revizyon_id", r_id_p).execute()
            for i in range(0, len(p_recs), 500): client.table("deg_anah_tablosu").insert(p_recs[i:i+500]).execute()
            st.success("Parametreler kaydedildi!")
        if cp3.button("🔄 Seçili Versiyonun Parametrelerini Çek", type="secondary", use_container_width=True, key="btn_p_ld"):
            p_res = client.table("deg_anah_tablosu").select("*").eq("revizyon_id", r_id_p).execute()
            if p_res.data:
                st.session_state.deg_anah_veri = pd.DataFrame(p_res.data)[[c for c in deg_anah_sutunlari if c in pd.DataFrame(p_res.data).columns]].reindex(columns=deg_anah_sutunlari)
                st.rerun()

# ------------------------------------------------------------
# 7. SEKME: BAZ YAKIT FİYATLARI
# ------------------------------------------------------------
with sekmeler[6]:
    st.title("⛽ Baz Yakıt Fiyatları KDV Dağılım Yönetimi")
    up_baz_yakit = st.file_uploader("Baz Yakıt Fiyat Listesi Yükle", type=["xlsx", "xls", "csv"], key="baz_yakit_up")
    if up_baz_yakit:
        df_by = pd.read_csv(up_baz_yakit) if up_baz_yakit.name.lower().endswith(".csv") else pd.read_excel(up_baz_yakit)
        df_by.columns = [str(c).strip() for c in df_by.columns]
        if "Müşteri Kodu" in df_by.columns:
            df_by["Müşteri Kodu"] = df_by["Müşteri Kodu"].apply(guvenli_metin_kodu)
            by_rows = []
            for idx, row in df_by.iterrows():
                mkod = str(row["Müşteri Kodu"])
                durum_v = st.session_state.musteri_ayarlari.get(mkod, {}).get("Durum_2", "GEÇERLİ")
                if durum_v is None: durum_v = "GEÇERLİ"
                kdv_v = "KDV'li"
                eski_baz_fiyat = 0.0
                if not st.session_state.deg_anah_veri.empty:
                    match_p = st.session_state.deg_anah_veri[st.session_state.deg_anah_veri["Müşteri Kodu"] == mkod]
                    if not match_p.empty:
                        kdv_raw = str(match_p.iloc[0].get("KDV Durumu", "KDV'li"))
                        kdv_v = "KDV'siz" if "KDV'siz" in kdv_raw else "KDV'li"
                        eski_baz_fiyat = guvenli_sayi(match_p.iloc[0].get("Baz Yakıt Fiyatı", 0.0))
                
                yakit_fiyat_nihai = eski_baz_fiyat / 1.2 if kdv_v == "KDV'li" else eski_baz_fiyat
                by_rows.append({
                    "Müşteri Kodu": mkod, "Müşteri Adı": row.get("Müşteri Adı", row.get("Ünvan", "")),
                    "Müşteri Temsilcisi": row.get("Müşteri Temsilcisi", row.get("Müşteri Temsilcisi 1", "")),
                    "Durum": durum_v, "KDV'li / KDV'siz": kdv_v, "Esk. Baz Yakıt Fiyatı": eski_baz_fiyat, "Yakıt Fiyat": yakit_fiyat_nihai
                })
            st.session_state.baz_yakit_veri = pd.DataFrame(by_rows).reindex(columns=baz_yakit_sutunlari)

    if not st.session_state.baz_yakit_veri.empty:
        edited_by_df = st.data_editor(st.session_state.baz_yakit_veri, use_container_width=True, height=400, disabled=baz_yakit_sutunlari,
                                      column_config={
                                          "Esk. Baz Yakıt Fiyatı": st.column_config.NumberColumn("Esk. Baz Yakıt Fiyatı", format="₺%.2f"),
                                          "Yakıt Fiyat": st.column_config.NumberColumn("Yakıt Fiyat", format="₺%.2f")
                                      }, key="ed_by_t6")
        if rev_secenekleri:
            st.markdown("---")
            c_by1, c_by2, c_by3 = st.columns(3)
            r_id_by = rev_secenekleri[c_by1.selectbox("Baz Yakıt İçin Bulut Versiyonu:", list(rev_secenekleri.keys()), key="sb_by_rev")]
            if c_by2.button("💾 Baz Yakıtları Buluta Kilitle", type="primary", use_container_width=True, key="btn_by_sv"):
                by_recs = [{str(col): json_uyumlu_deger(val) for col, val in row.items()} for _, row in edited_by_df.iterrows()]
                for r in by_recs: r["revizyon_id"] = r_id_by
                client.table("baz_yakit_tablosu").delete().eq("revizyon_id", r_id_by).execute()
                for i in range(0, len(by_recs), 500): client.table("baz_yakit_tablosu").insert(by_recs[i:i+500]).execute()
                st.success("Mühürlendi!")
            if c_by3.button("🔄 Versiyonun Baz Yakıt Değerlerini Getir", type="secondary", use_container_width=True, key="btn_by_ld"):
                by_res = client.table("baz_yakit_tablosu").select("*").eq("revizyon_id", r_id_by).execute()
                if by_res.data:
                    st.session_state.baz_yakit_veri = pd.DataFrame(by_res.data)[[c for c in baz_yakit_sutunlari if c in pd.DataFrame(by_res.data).columns]].reindex(columns=baz_yakit_sutunlari)
                    st.rerun()

# ------------------------------------------------------------
# 8. SEKME: 2026 MAZOT ANALİZİ
# ------------------------------------------------------------
with sekmeler[7]:
    st.title("📊 2026 Mazot Fiyat Değişim Periyot Analizörü")
    up_mazot = st.file_uploader("Yeni Mazot Fiyat Trendi Yükle", type=["xlsx", "xls", "csv"], key="mazot_up_file")
    if up_mazot:
        df_mz = pd.read_csv(up_mazot) if up_mazot.name.lower().endswith(".csv") else pd.read_excel(up_mazot)
        df_mz.columns = [str(c).strip() for c in df_mz.columns]
        st.session_state.mazot_giriş_veri = df_mz.reindex(columns=mazot_giriş_sutunlari).applymap(guvenli_sayi).copy()

    edited_mazot_input = st.data_editor(st.session_state.mazot_giriş_veri, use_container_width=True, hide_index=True, column_config={c: st.column_config.NumberColumn(c, format="₺%.4f") for c in mazot_giriş_sutunlari}, key="mazot_giriş_editor")
    st.session_state.mazot_giriş_veri = edited_mazot_input.copy()

    if not edited_mazot_input.empty:
        mz_base = edited_mazot_input.iloc[0]
        matris_rows = []
        for k in range(1, 7):
            row_data = {"Periyot": f"{k} ay"}
            for j, ay in enumerate(aylar):
                val_curr = guvenli_sayi(mz_base.get(ay, 0.0))
                idx_prev = j - k
                val_prev = guvenli_sayi(mz_base.get("Baz Motorin", 0.0)) if idx_prev == -1 else (0.0 if idx_prev < -1 else guvenli_sayi(mz_base.get(aylar[idx_prev], 0.0)))
                row_data[ay] = (val_curr / val_prev) - 1 if val_prev > 0 and val_curr > 0 else None
            matris_rows.append(row_data)

        df_mazot_matris = pd.DataFrame(matris_rows)
        st.subheader("📈 Hesaplanan Aylık Değişim Matrisi (%)")
        st.dataframe(df_mazot_matris, use_container_width=True, hide_index=True, column_config={ay: st.column_config.NumberColumn(ay, format="%.2f%%") for ay in aylar})

        if rev_secenekleri:
            st.markdown("---")
            cm_z1, cm_z2, cm_z3 = st.columns(3)
            r_id_z = rev_secenekleri[cm_z1.selectbox("Mazot Analizi İçin Bulut Versiyonu:", list(rev_secenekleri.keys()), key="sb_mz_rev")]
            if cm_z2.button("💾 Mazot Trendini Buluta Kaydet", type="primary", use_container_width=True, key="btn_mz_sv"):
                mz_rec = {str(col): json_uyumlu_deger(val) for col, val in edited_mazot_input.iloc[0].items()}
                mz_rec["revizyon_id"] = r_id_z
                client.table("mazot_tablosu").delete().eq("revizyon_id", r_id_z).execute()
                client.table("mazot_tablosu").insert(mz_rec).execute()
                st.success("Mühürlendi!")
            if cm_z3.button("🔄 Versiyonun Mazot Verilerini Getir", type="secondary", use_container_width=True, key="btn_mz_ld"):
                mz_res = client.table("mazot_tablosu").select("*").eq("revizyon_id", r_id_z).execute()
                if mz_res.data:
                    st.session_state.mazot_giriş_veri = pd.DataFrame([mz_res.data[0]])[[c for c in mazot_giriş_sutunlari if c in mz_res.data[0]]].reindex(columns=mazot_giriş_sutunlari)
                    st.rerun()

# ------------------------------------------------------------
# 9. SEKME: MÜŞTERİ BÜYÜME ORANLARI
# ------------------------------------------------------------
with sekmeler[8]:
    st.title("📈 Müşteri Büyüme Oranları ve Kg Simülasyonu")
    st.caption("2024 ve 2025 verileri doğrudan 📁 Data sekmesindeki ana havuzdan alınır. Bu sayfada yalnızca 31 kolonlu 2026 güncel Kg dosyası yüklenir.")

    # ------------------------------------------------------------
    # 9. SEKME YARDIMCI TANIMLARI
    # ------------------------------------------------------------
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
        """31 kolonlu 2026 dosyasını güvenli biçimde temizler; metinleri bozmaz."""
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
        """Kaynağı müşteri bazına indirir ve sütunları '2026 Ocak Kg' biçimine getirir."""
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

    # ------------------------------------------------------------
    # 2024-2025: YALNIZCA ANA DATA HAVUZUNDAN
    # ------------------------------------------------------------
    data_havuzu_9 = st.session_state.get("data_sayfası_df", pd.DataFrame()).copy()
    hist_24_9 = musteri_bazinda_ozetle_9(data_havuzu_9, "2024")
    hist_25_9 = musteri_bazinda_ozetle_9(data_havuzu_9, "2025")

    mevcut_yillar_9 = []
    if any(f"2024 {m} Kg" in data_havuzu_9.columns for m in aylar):
        mevcut_yillar_9.append("2024")
    if any(f"2025 {m} Kg" in data_havuzu_9.columns for m in aylar):
        mevcut_yillar_9.append("2025")

    c_bilgi1, c_bilgi2, c_bilgi3 = st.columns(3)
    c_bilgi1.metric("Ana Data satırı", f"{len(data_havuzu_9):,}")
    c_bilgi2.metric("Hazır geçmiş yıllar", ", ".join(mevcut_yillar_9) if mevcut_yillar_9 else "Yok")
    c_bilgi3.metric(
        "2026 yükleme durumu",
        f"{len(st.session_state.get('df_2026_buyume_9', pd.DataFrame())):,} satır"
        if not st.session_state.get("df_2026_buyume_9", pd.DataFrame()).empty else "Bekleniyor"
    )

    if len(mevcut_yillar_9) < 2:
        st.warning("2024 ve/veya 2025 Kgleri ana Data havuzunda bulunamadı. Önce 📁 Data sekmesinden eksik yılı yükleyin veya buluttaki Data revizyonunu çağırın.")

    # ------------------------------------------------------------
    # 2026: SADECE BU SEKMEDE 31 KOLONLU DOSYA
    # ------------------------------------------------------------
    with st.expander("🚀 2026 Güncel Kg Dosyası (31 kolon)", expanded=True):
        st.markdown(
            "Dosya yüklendiğinde otomatik işlenir. 2024–2025 verileri yeniden istenmez ve "
            "ana havuzdaki geçmiş değerler değiştirilmez."
        )
        up_2026_9 = st.file_uploader(
            "2026 güncel Kg dosyasını yükleyin",
            type=["xlsx", "xls", "csv"],
            key="up_2026_only_9"
        )

        if up_2026_9 is not None:
            try:
                df_raw_26_9 = oku_excel_csv_9(up_2026_9)
                df_clean_26_9, eksik_26_9 = temizle_2026_31_kolon(df_raw_26_9)
                st.session_state.df_2026_buyume_9 = df_clean_26_9
                st.success(f"2026 dosyası işlendi: {len(df_clean_26_9):,} satır.")
                if eksik_26_9:
                    st.warning(
                        "Dosyada bulunmadığı için boş oluşturulan kolonlar: "
                        + ", ".join(eksik_26_9)
                    )
            except Exception as ex:
                st.error(f"2026 dosyası işlenemedi: {ex}")

        df_2026_raw_9 = st.session_state.get("df_2026_buyume_9", pd.DataFrame())
        if not df_2026_raw_9.empty:
            st.dataframe(df_2026_raw_9.head(20), use_container_width=True, hide_index=True)
            if st.button("🧹 2026 yüklemesini hafızadan temizle", key="clear_2026_9"):
                st.session_state.df_2026_buyume_9 = pd.DataFrame(columns=NIHAI_SUTUNLAR_9)
                st.rerun()

    hist_26_9 = musteri_bazinda_ozetle_9(
        st.session_state.get("df_2026_buyume_9", pd.DataFrame()),
        "2026",
        kaynak_31_kolon=True
    )

    # ------------------------------------------------------------
    # ÜÇ YILI MÜŞTERİ KODU ÜZERİNDEN TEK HESAPLAMA KAYNAĞINDA BİRLEŞTİR
    # ------------------------------------------------------------
    kaynaklar_9 = [df for df in [hist_24_9, hist_25_9, hist_26_9] if not df.empty]
    if kaynaklar_9:
        df_calc_9 = kaynaklar_9[0].copy()
        for siradaki_9 in kaynaklar_9[1:]:
            df_calc_9 = pd.merge(
                df_calc_9,
                siradaki_9,
                on="Müşteri Kodu",
                how="outer",
                suffixes=("", "_yeni")
            )
            for c in KIMLIK_KOLONLARI_9:
                if c == "Müşteri Kodu":
                    continue
                yeni_c = f"{c}_yeni"
                if yeni_c in df_calc_9.columns:
                    if c not in df_calc_9.columns:
                        df_calc_9[c] = df_calc_9[yeni_c]
                    else:
                        sol = df_calc_9[c].apply(lambda v: temiz_metin_9(v, ""))
                        sag = df_calc_9[yeni_c].apply(lambda v: temiz_metin_9(v, ""))
                        df_calc_9[c] = sol.where(sol != "", sag)
                    df_calc_9 = df_calc_9.drop(columns=[yeni_c])
        df_calc_9 = df_calc_9.fillna(0)
    else:
        df_calc_9 = pd.DataFrame()

    # ------------------------------------------------------------
    # MÜŞTERİ BAZLI BÜYÜME MATRİSİ
    # ------------------------------------------------------------
    if df_calc_9.empty:
        st.info("Büyüme matrisini oluşturmak için ana Data havuzunda 2024–2025 verisi bulunmalıdır.")
    else:
        st.subheader("📈 Müşteri Bazlı Büyüme Matrisi")
        karsilastirma_ay_sayisi_9 = st.selectbox(
            "Karşılaştırmada kullanılacak gerçekleşen ay sayısı",
            options=list(range(1, 13)),
            index=8,
            format_func=lambda x: f"İlk {x} ay",
            key="karsilastirma_ay_sayisi_9"
        )
        secili_aylar_9 = aylar[:karsilastirma_ay_sayisi_9]
        donem_24_adi_9 = f"2024 ilk {karsilastirma_ay_sayisi_9} ay Kg"
        donem_25_adi_9 = f"2025 ilk {karsilastirma_ay_sayisi_9} ay Kg"
        pay_25_adi_9 = f"2025 ilk {karsilastirma_ay_sayisi_9} ay % Kg pay"

        for y in ["2024", "2025", "2026"]:
            for m in aylar:
                c = f"{y} {m} Kg"
                if c not in df_calc_9.columns:
                    df_calc_9[c] = 0.0
                df_calc_9[c] = df_calc_9[c].apply(guvenli_sayi)

        df_calc_9[donem_24_adi_9] = df_calc_9[[f"2024 {m} Kg" for m in secili_aylar_9]].sum(axis=1)
        df_calc_9[donem_25_adi_9] = df_calc_9[[f"2025 {m} Kg" for m in secili_aylar_9]].sum(axis=1)
        toplam_25_9 = df_calc_9[donem_25_adi_9].sum()
        df_calc_9[pay_25_adi_9] = (
            df_calc_9[donem_25_adi_9] / toplam_25_9 * 100.0 if toplam_25_9 > 0 else 0.0
        )
        df_calc_9["Y To Y Kg (%)"] = np.where(
            df_calc_9[donem_24_adi_9] > 0,
            (df_calc_9[donem_25_adi_9] / df_calc_9[donem_24_adi_9] - 1.0) * 100.0,
            0.0
        )

        final_rows_9 = []
        for _, row in df_calc_9.iterrows():
            mkod = guvenli_metin_kodu(row["Müşteri Kodu"])
            ayar = st.session_state.buyume_ayarlari.get(mkod, {})
            kullanilacak = guvenli_sayi(ayar.get("KULLANICAK BÜYÜME", 0.0))
            durum = st.session_state.musteri_ayarlari.get(mkod, {}).get(
                "Durum_2", ilk_dolu_deger_9(row, ["Durum"], "GEÇERLİ")
            )
            r = {
                "Müşteri Kodu": mkod,
                "Müşteri Adı": ilk_dolu_deger_9(row, ["Müşteri Adı"]),
                "Müşteri Temsilcisi": ilk_dolu_deger_9(row, ["Müşteri Temsilcisi"]),
                "Sap Kodu": ilk_dolu_deger_9(row, ["Sap Kodu"]),
                "Durum": durum or "GEÇERLİ",
                "Kayıt Tarihi": ilk_dolu_deger_9(row, ["Kayıt Tarihi"]),
                "Müşteri Grubu": ilk_dolu_deger_9(row, ["Müşteri Grubu"], "DİĞER"),
                donem_24_adi_9: row[donem_24_adi_9],
                donem_25_adi_9: row[donem_25_adi_9],
                pay_25_adi_9: row[pay_25_adi_9],
                "Y To Y Kg (%)": row["Y To Y Kg (%)"],
                "25 kullanılan büyüme": ayar.get("25 kullanılan büyüme", ""),
                "KULLANICAK BÜYÜME": kullanilacak,
                "Gelen Özet Bilgi": ayar.get("Gelen Özet Bilgi", ""),
                "Müşteriden Gelen Büyüme": ayar.get("Müşteriden Gelen Büyüme", "")
            }
            for m in aylar:
                r[m] = kullanilacak
            final_rows_9.append(r)

        ekran_kolonlari_9 = (
            KIMLIK_KOLONLARI_9 + aylar +
            [donem_24_adi_9, donem_25_adi_9, pay_25_adi_9, "Y To Y Kg (%)",
             "25 kullanılan büyüme", "KULLANICAK BÜYÜME",
             "Gelen Özet Bilgi", "Müşteriden Gelen Büyüme"]
        )
        df_final_b_9 = pd.DataFrame(final_rows_9).reindex(columns=ekran_kolonlari_9)
        kilitli_9 = [
            c for c in ekran_kolonlari_9
            if c not in ["25 kullanılan büyüme", "KULLANICAK BÜYÜME",
                         "Gelen Özet Bilgi", "Müşteriden Gelen Büyüme"]
        ]

        edited_b_matris = st.data_editor(
            df_final_b_9,
            use_container_width=True,
            height=430,
            disabled=kilitli_9,
            column_config={
                pay_25_adi_9: st.column_config.NumberColumn(pay_25_adi_9, format="%.2f%%"),
                "Y To Y Kg (%)": st.column_config.NumberColumn("Y To Y Kg (%)", format="%.2f%%"),
                "KULLANICAK BÜYÜME": st.column_config.NumberColumn("KULLANICAK BÜYÜME", format="%.2f%%"),
                **{m: st.column_config.NumberColumn(m, format="%.2f%%") for m in aylar}
            },
            key=f"buyume_matris_editoru_{karsilastirma_ay_sayisi_9}"
        )

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

        toplam_2026_ay_9 = {
            m: grup_totals_9["2026"][f"2026 {m} Kg"].sum()
            if f"2026 {m} Kg" in grup_totals_9["2026"].columns else 0.0
            for m in aylar
        }
        gerceklesen_aylar_9 = [m for m in aylar if toplam_2026_ay_9[m] > 0]
        tahmini_aylar_9 = [m for m in aylar if m not in gerceklesen_aylar_9]

        if gerceklesen_aylar_9:
            st.success("2026 gerçekleşen kabul edilen aylar: " + ", ".join(gerceklesen_aylar_9))
        if tahmini_aylar_9:
            st.info(
                "2026 tahmini tamamlanan aylar: " + ", ".join(tahmini_aylar_9)
                + ". Bu aylarda 2024 ve 2025 aynı ay Kglerinin ortalaması kullanılır."
            )

        sezon_tabs_9 = st.tabs([
            "📅 2024 Dağılımı",
            "📅 2025 Dağılımı",
            "📅 2026 Gerçekleşen + Tahmin"
        ])

        for tab_index_9, target_yil_9 in enumerate(["2024", "2025", "2026"]):
            with sezon_tabs_9[tab_index_9]:
                sezon_rows_9 = []
                for grp in hedef_gruplar_9:
                    ham_aylar_9 = []
                    kaynak_tipi_9 = []
                    for m in aylar:
                        col = f"{target_yil_9} {m} Kg"
                        val = (
                            guvenli_sayi(grup_totals_9[target_yil_9].loc[grp, col])
                            if grp in grup_totals_9[target_yil_9].index else 0.0
                        )
                        kaynak = "Gerçekleşen"

                        if target_yil_9 == "2026" and m in tahmini_aylar_9:
                            val24 = (
                                guvenli_sayi(grup_totals_9["2024"].loc[grp, f"2024 {m} Kg"])
                                if grp in grup_totals_9["2024"].index else 0.0
                            )
                            val25 = (
                                guvenli_sayi(grup_totals_9["2025"].loc[grp, f"2025 {m} Kg"])
                                if grp in grup_totals_9["2025"].index else 0.0
                            )
                            dolu_gecmis = [v for v in [val24, val25] if v > 0]
                            val = sum(dolu_gecmis) / len(dolu_gecmis) if dolu_gecmis else 0.0
                            kaynak = "2024-2025 Ortalaması"

                        ham_aylar_9.append(val)
                        kaynak_tipi_9.append(kaynak)

                    yillik_toplam_9 = sum(ham_aylar_9)
                    row_9 = {"Müşteri Grubu": grp}
                    for j, m in enumerate(aylar):
                        row_9[m] = (
                            ham_aylar_9[j] / yillik_toplam_9 * 100.0
                            if yillik_toplam_9 > 0 else 0.0
                        )
                    row_9["Toplam (%)"] = sum(row_9[m] for m in aylar)
                    sezon_rows_9.append(row_9)

                sezon_df_9 = pd.DataFrame(sezon_rows_9)
                st.dataframe(
                    sezon_df_9,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        **{m: st.column_config.NumberColumn(m, format="%.2f%%") for m in aylar},
                        "Toplam (%)": st.column_config.NumberColumn("Toplam (%)", format="%.2f%%")
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
                    "KULLANICAK BÜYÜME": guvenli_sayi(row.get("KULLANICAK BÜYÜME", 0.0)),
                    "Gelen Özet Bilgi": row.get("Gelen Özet Bilgi", ""),
                    "Müşteriden Gelen Büyüme": row.get("Müşteriden Gelen Büyüme", "")
                }
            st.success("Büyüme stratejileri hafızaya kaydedildi ve 12 aya eşit uygulandı.")
            st.rerun()

        if rev_secenekleri:
            r_id_b = rev_secenekleri[
                cb_2.selectbox(
                    "Büyüme İçin Bulut Versiyonu:",
                    list(rev_secenekleri.keys()),
                    key="sb_b_rev_box"
                )
            ]

            if cb_2.button(
                "💾 Büyüme Verilerini Buluta Gönder",
                use_container_width=True,
                key="btn_b_cloud_save"
            ):
                izin_verilen_b_db = [
                    "Müşteri Kodu", "Müşteri Adı", "Müşteri Temsilcisi", "Sap Kodu",
                    "Durum", "Kayıt Tarihi", "Müşteri Grubu", "25 kullanılan büyüme",
                    "KULLANICAK BÜYÜME", "Gelen Özet Bilgi", "Müşteriden Gelen Büyüme"
                ]
                b_records = [
                    {
                        col: json_uyumlu_deger(row[col])
                        for col in izin_verilen_b_db if col in row.index
                    }
                    for _, row in edited_b_matris.iterrows()
                ]
                for record in b_records:
                    record["revizyon_id"] = r_id_b
                client.table("buyume_tablosu").delete().eq("revizyon_id", r_id_b).execute()
                for i in range(0, len(b_records), 500):
                    client.table("buyume_tablosu").insert(b_records[i:i + 500]).execute()
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
                            "25 kullanılan büyüme": row.get("25 kullanılan büyüme", ""),
                            "KULLANICAK BÜYÜME": guvenli_sayi(
                                row.get("KULLANICAK BÜYÜME", 0.0)
                            ),
                            "Gelen Özet Bilgi": row.get("Gelen Özet Bilgi", ""),
                            "Müşteriden Gelen Büyüme": row.get(
                                "Müşteriden Gelen Büyüme", ""
                            )
                        }
                    st.success("🎉 Büyüme kartları buluttan getirildi.")
                    st.rerun()
                else:
                    st.warning("Seçili revizyonda kayıtlı büyüme kartı bulunamadı.")
