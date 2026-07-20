import streamlit as st
import pandas as pd
import numpy as np
import io
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
    "Yakıt Değişim Yüzdesi (%)", "Yakıt Anlık Değişim Oranı (%)", "Yakıt Değişim Periyodu (Ay)",
    "Enf. Değişim Yüzdesi (%)", "Enf. Değişim Periyodu (Ay)", "Esk. Baz Yakıt Fiyatı", "Esk. Yakıt Başlangıç Tarihi", "Esk. Enf. Başlangıç Tarihi"
]

kolonlar_2025_desi = [f"2025 {ay} Desi" for ay in aylar]
kolonlar_2025_tutar = [f"2025 {ay} Tutar" for ay in aylar]
kolonlar_2025_fiyat = [f"2025 {ay} Fiyat" for ay in aylar]

kolonlar_2026_buyume = [f"2026 {ay} Büyüme" for ay in aylar]
kolonlar_2026_esk = [f"2026 {ay} Esk." for ay in aylar]
kolonlar_2026_desi = [f"2026 {ay} Desi" for ay in aylar]
kolonlar_2026_tutar = [f"2026 {ay} Tutar" for ay in aylar]
kolonlar_2026_fiyat = [f"2026 {ay} Fiyat" for ay in aylar]

tum_kolonlar = (ana_kolonlar + parametre_kolonlari + kolonlar_2025_desi + kolonlar_2025_tutar + kolonlar_2025_fiyat +
                kolonlar_2026_buyume + kolonlar_2026_esk + kolonlar_2026_desi + kolonlar_2026_tutar + kolonlar_2026_fiyat)

BIGINT_KOLONLAR = ["Uniq ID", "Yıl", "Yakıt Değişim Periyodu (Ay)", "Enf. Değişim Periyodu (Ay)"]
NUMERIC_KOLONLAR = (["Yakıt Değişim Yüzdesi (%)", "Yakıt Anlık Değişim Oranı (%)", "Enf. Değişim Yüzdesi (%)", "Esk. Baz Yakıt Fiyatı"] +
                    kolonlar_2025_desi + kolonlar_2025_tutar + kolonlar_2025_fiyat + kolonlar_2026_buyume + kolonlar_2026_esk +
                    kolonlar_2026_desi + kolonlar_2026_tutar + kolonlar_2026_fiyat)

# Özel Sayfa Şablon Sütun Tanımları
data_ekran_sutunlari = [
    "Uniq ID", "Yıl", "Teslimat Tipi", "Atf Tipi", "Çıkış İl Adı", "Çıkış Şube Adı", "Varış İl Adı", "Varış Şube Adı",
    "İlk Okutma Şubesi", "Müşteri Kodu", "Müşteri Adı", "Müşteri Temsilcisi", "Sap Kodu", "Durum", "Kayıt Tarihi", "Müşteri Grubu",
    "Yakıt Değişim Yüzdesi (%)", "Yakıt Anlık Değişim Oranı (%)", "Yakıt Değişim Periyodu (Ay)", "Enf. Değişim Yüzdesi (%)",
    "Enf. Değişim Periyodu (Ay)", "Esk. Baz Yakıt Fiyatı", "Esk. Yakıt Başlangıç Tarihi", "Esk. Enf. Başlangıç Tarihi"
]
deg_anah_sutunlari = ["Müşteri Kodu", "Sap No", "Ünvan", "Müşteri Temsilcisi 1", "Müşteri Temsilcisi 2", "Değişim Anahtarı", "KDV Durumu", "Baz Yakıt Fiyatı"]
baz_yakit_sutunlari = ["Müşteri Kodu", "Müşteri Adı", "Müşteri Temsilcisi", "Durum", "KDV'li / KDV'siz", "Esk. Baz Yakıt Fiyatı", "Yakıt Fiyat"]
mazot_giriş_sutunlari = ["Baz Motorin"] + aylar
buyume_ekran_sutunlari = [
    "Müşteri Kodu", "Müşteri Adı", "Müşteri Temsilcisi", "Sap Kodu", "Durum", "Kayıt Tarihi", "Müşteri Grubu"
] + aylar + [
    "2024 ilk 9 ay desi", "2025 ilk 9 ay desi", "2025 % desi pay", "Y To Y Desi", 
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
# ARAYÜZ SEKMELERİ (9 SEKMEYE ÇIKARILDI - DATA EN BAŞTA 🎉)
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
# 1. SEKME: 📁 DATA GİRİŞ VE ÇAPRAZ PARAMETRE HAVUZU (YENİ MODÜL 🚀)
# ------------------------------------------------------------
with sekmeler[0]:
    st.title("📁 Operasyonel Ana Data Yönetim Havuzu")
    st.markdown("Aşağıya operasyonel ham listenizi yükleyin. Sistem, `Durum` bilgisini **Yeni-Bütçe** sayfasından, `Esk. Baz Yakıt Fiyatı`nı ise **Baz Yakıtlar** sayfasından çapraz eşleyerek (Düşeyara) çekecektir. Kalan alanlar yüklediğiniz şablondan alınır.")

    yuklenen_data_havuzu = st.file_uploader("Data Listenizi Yükleyin (Excel/CSV)", type=["xlsx", "xls", "csv"], key="data_havuz_up")

    # Çarşaf listeden Düşeyara (VLOOKUP) için verileri belleğe al (Yedek Havuz)
    lookup_parametleri = {}
    if not st.session_state.ana_veri.empty:
        df_c_tmp = st.session_state.ana_veri.copy()
        df_c_tmp["Müşteri Kodu"] = df_c_tmp["Müşteri Kodu"].apply(guvenli_metin_kodu)
        df_uniq_m = df_c_tmp.drop_duplicates(subset=["Müşteri Kodu"])
        for _, r in df_uniq_m.iterrows():
            mk = str(r["Müşteri Kodu"])
            lookup_parametleri[mk] = {
                "Kayıt Tarihi": r.get("Kayıt Tarihi", ""),
                "Müşteri Grubu": r.get("Müşteri Grubu", "DİĞER"),
                "Yakıt Değişim Yüzdesi (%)": guvenli_sayi(r.get("Yakıt Değişim Yüzdesi (%)", 0.0)),
                "Yakıt Anlık Değişim Oranı (%)": guvenli_sayi(r.get("Yakıt Anlık Değişim Oranı (%)", 0.0)),
                "Yakıt Değişim Periyodu (Ay)": guvenli_tamsayi(r.get("Yakıt Değişim Periyodu (Ay)", 0)),
                "Enf. Değişim Yüzdesi (%)": guvenli_sayi(r.get("Enf. Değişim Yüzdesi (%)", 0.0)),
                "Enf. Değişim Periyodu (Ay)": guvenli_tamsayi(r.get("Enf. Değişim Periyodu (Ay)", 0)),
                "Esk. Yakıt Başlangıç Tarihi": r.get("Esk. Yakıt Başlangıç Tarihi", ""),
                "Esk. Enf. Başlangıç Tarihi": r.get("Esk. Enf. Başlangıç Tarihi", "")
            }

    # 6. Sekmedeki (Baz Yakıt Fiyatları) güncel "Yakıt Fiyat" verilerini Düşeyara için hazırla
    baz_yakit_map = {}
    if not st.session_state.baz_yakit_veri.empty:
        for _, r in st.session_state.baz_yakit_veri.iterrows():
            baz_yakit_map[str(r["Müşteri Kodu"])] = guvenli_sayi(r.get("Yakıt Fiyat", 0.0))

    if yuklenen_data_havuzu:
        df_d_giren = pd.read_csv(yuklenen_data_havuzu) if yuklenen_data_havuzu.name.lower().endswith(".csv") else pd.read_excel(yuklenen_data_havuzu)
        df_d_giren.columns = [str(c).strip() for c in df_d_giren.columns]
        
        data_rows = []
        for idx, row in df_d_giren.iterrows():
            mkod = guvenli_metin_kodu(row.get("Müşteri Kodu", ""))
            
            # KURAL: Uniq ID kombinasyon motoru
            join_cols = ["Yıl", "Teslimat Tipi", "Atf Tipi", "Çıkış İl Adı", "Çıkış Şube Adı", "Varış İl Adı", "Varış Şube Adı", "İlk Okutma Şubesi", "Müşteri Kodu"]
            uniq_str = "".join([str(row.get(c, "")).strip() for c in join_cols]).replace("nan", "").replace("None", "")
            
            p_set = lookup_parametleri.get(mkod, {})

            # 1. ÖZEL KURAL: DURUM -> Yeni-Bütçe Müşteri sayfasındaki Durum_2'den alınacak
            durum_2_val = st.session_state.musteri_ayarlari.get(mkod, {}).get("Durum_2")
            if pd.isna(durum_2_val) or durum_2_val is None or str(durum_2_val).strip() == "":
                durum_2_val = row.get("Durum", "GEÇERLİ")  # Bulamazsa Excel'den veya varsayılan

            # 2. ÖZEL KURAL: ESK BAZ YAKIT -> Baz Yakıt Fiyatları sayfasındaki Yakıt Fiyat'tan alınacak
            esk_baz_yakit_val = baz_yakit_map.get(mkod)
            if esk_baz_yakit_val is None or esk_baz_yakit_val == 0.0:
                esk_baz_yakit_val = guvenli_sayi(row.get("Esk. Baz Yakıt Fiyatı", 0.0)) # Bulamazsa Excel'den al

            # 3. KURAL: Diğer parametreler direkt yüklenen Excel'den (Yoksa eski havuzdan)
            data_rows.append({
                "Uniq ID": uniq_str,
                "Yıl": row.get("Yıl", ""),
                "Teslimat Tipi": row.get("Teslimat Tipi", ""),
                "Atf Tipi": row.get("Atf Tipi", ""),
                "Çıkış İl Adı": row.get("Çıkış İl Adı", ""),
                "Çıkış Şube Adı": row.get("Çıkış Şube Adı", ""),
                "Varış İl Adı": row.get("Varış İl Adı", ""),
                "Varış Şube Adı": row.get("Varış Şube Adı", ""),
                "İlk Okutma Şubesi": row.get("İlk Okutma Şubesi", ""),
                "Müşteri Kodu": mkod,
                "Müşteri Adı": row.get("Müşteri Adı", ""),
                "Müşteri Temsilcisi": row.get("Müşteri Temsilcisi", ""),
                "Sap Kodu": row.get("Sap Kodu", row.get("Sap No", "")),
                
                # Dinamik Çekilen Alanlar
                "Durum": durum_2_val,
                "Esk. Baz Yakıt Fiyatı": esk_baz_yakit_val,
                
                # Excel'den Yüklenen Alanlar
                "Kayıt Tarihi": row.get("Kayıt Tarihi", p_set.get("Kayıt Tarihi", "")),
                "Müşteri Grubu": row.get("Müşteri Grubu", p_set.get("Müşteri Grubu", "DİĞER")),
                "Yakıt Değişim Yüzdesi (%)": guvenli_sayi(row.get("Yakıt Değişim Yüzdesi (%)", p_set.get("Yakıt Değişim Yüzdesi (%)", 0.0))),
                "Yakıt Anlık Değişim Oranı (%)": guvenli_sayi(row.get("Yakıt Anlık Değişim Oranı (%)", p_set.get("Yakıt Anlık Değişim Oranı (%)", 0.0))),
                "Yakıt Değişim Periyodu (Ay)": guvenli_tamsayi(row.get("Yakıt Değişim Periyodu (Ay)", p_set.get("Yakıt Değişim Periyodu (Ay)", 0))),
                "Enf. Değişim Yüzdesi (%)": guvenli_sayi(row.get("Enf. Değişim Yüzdesi (%)", p_set.get("Enf. Değişim Yüzdesi (%)", 0.0))),
                "Enf. Değişim Periyodu (Ay)": guvenli_tamsayi(row.get("Enf. Değişim Periyodu (Ay)", p_set.get("Enf. Değişim Periyodu (Ay)", 0))),
                "Esk. Yakıt Başlangıç Tarihi": row.get("Esk. Yakıt Başlangıç Tarihi", p_set.get("Esk. Yakıt Başlangıç Tarihi", "")),
                "Esk. Enf. Başlangıç Tarihi": row.get("Esk. Enf. Başlangıç Tarihi", p_set.get("Esk. Enf. Başlangıç Tarihi", ""))
            })
        st.session_state.data_sayfası_df = pd.DataFrame(data_rows).reindex(columns=data_ekran_sutunlari)
        st.success("🎉 Ham veri yüklendi, `Durum` ve `Yakıt Fiyat` çapraz sekme sorgularıyla başarıyla güncellendi!")

    # Tabloyu data_editor olarak ekrana bas
    if not st.session_state.data_sayfası_df.empty:
        edited_data_grid = st.data_editor(
            st.session_state.data_sayfası_df,
            use_container_width=True,
            height=400,
            disabled=data_ekran_sutunlari, # Sadece görüntüleme ve çapraz kontrol amaçlı kilitli
            column_config={
                "Esk. Baz Yakıt Fiyatı": st.column_config.NumberColumn("Esk. Baz Yakıt Fiyatı", format="₺%.2f"),
                "Yakıt Değişim Yüzdesi (%)": st.column_config.NumberColumn("Yakıt Değişim Yüzdesi (%)", format="%.2f%%"),
                "Enf. Değişim Yüzdesi (%)": st.column_config.NumberColumn("Enf. Değişim Yüzdesi (%)", format="%.2f%%")
            },
            key="data_sayfası_grid_editor"
        )
        st.session_state.data_sayfası_df = edited_data_grid.copy()

        # Bulut Yönetim Paneli (Her Zaman Aktif - Dosya Yüklemeden Çağırma Garantili)
        st.markdown("---")
        st.subheader("☁️ Bulut Entegrasyonu (Yüklemeden Bağımsız Çağırma)")
        cd1, cd2, cd3 = st.columns(3)
        
        # Excel İndirme Butonu
        output_d_excel = io.BytesIO()
        with pd.ExcelWriter(output_d_excel, engine="openpyxl") as writer: edited_data_grid.to_excel(writer, index=False, sheet_name="Data_Master")
        cd1.download_button("📥 Tabloyu Excel Olarak İndir", output_d_excel.getvalue(), "data_master_havuz.xlsx", use_container_width=True)

        if rev_secenekleri:
            r_id_data = rev_secenekleri[cd2.selectbox("Data Yönetimi İçin Bulut Versiyonu:", list(rev_secenekleri.keys()), key="sb_data_rev")]
            
            # BULUTA KAYDETME BUTONU
            if cd2.button("💾 Bu Tabloyu Buluta Kaydet (Mühürle)", type="primary", use_container_width=True, key="btn_data_cloud_sv"):
                # Supabase veritabanında tam karşılığı olan sütunların listesi (Güvenlik Kalkanı)
                izin_verilen_db_sutunlari_data = [
                    "Uniq ID", "Yıl", "Teslimat Tipi", "Atf Tipi", "Çıkış İl Adı", "Çıkış Şube Adı", 
                    "Varış İl Adı", "Varış Şube Adı", "İlk Okutma Şubesi", "Müşteri Kodu", "Müşteri Adı", 
                    "Müşteri Temsilcisi", "Sap Kodu", "Durum", "Kayıt Tarihi", "Müşteri Grubu",
                    "Yakıt Değişim Yüzdesi (%)", "Yakıt Anlık Değişim Oranı (%)", "Yakıt Değişim Periyodu (Ay)", 
                    "Enf. Değişim Yüzdesi (%)", "Enf. Değişim Periyodu (Ay)", "Esk. Baz Yakıt Fiyatı", 
                    "Esk. Yakıt Başlangıç Tarihi", "Esk. Enf. Başlangıç Tarihi"
                ]
                
                data_records = []
                for _, row in edited_data_grid.iterrows():
                    # Ekranda olan verilerden SADECE veritabanında olanları filtreliyoruz
                    rc = {col: json_uyumlu_deger(row[col]) for col in izin_verilen_db_sutunlari_data if col in row}
                    rc["revizyon_id"] = r_id_data
                    data_records.append(rc)
                
                with st.spinner("Data havuzu buluta işleniyor..."):
                    client.table("data_tablosu").delete().eq("revizyon_id", r_id_data).execute()
                    for i in range(0, len(data_records), 500): 
                        client.table("data_tablosu").insert(data_records[i:i+500]).execute()
                    st.success("🎉 Data havuzu bulut sunucularına kalıcı olarak mühürlendi!")

            # BULUTTAN DOĞRUDAN ÇEKME ENGINE (YARIN UPLOADSIZ ÇALIŞACAK KISIM 🚀)
            if cd3.button("🔄 Dosya Yüklemeden Buluttan Datayı Getir", type="secondary", use_container_width=True, key="btn_data_cloud_ld"):
                with st.spinner("Veriler veritabanından çekiliyor..."):
                    d_res = client.table("data_tablosu").select("*").eq("revizyon_id", r_id_data).execute()
                    if d_res.data:
                        gelen_d_df = pd.DataFrame(d_res.data)
                        if "id" in gelen_d_df.columns: gelen_d_df = gelen_d_df.drop(columns=["id"])
                        st.session_state.data_sayfası_df = gelen_d_df.reindex(columns=data_ekran_sutunlari)
                        st.success("🎉 Harika! Dün kaydettiğiniz tüm ana data şablonu buluttan geri yüklendi.")
                        st.rerun()
                    else: st.warning("Bu revizyona ait kaydedilmiş veri havuzu bulunamadı.")
    else:
        st.info("Lütfen işlem yapmak istediğiniz ham operasyonel Excel/CSV dosyanızı yükleyin ya da alttaki butondan bulut yedeğinizi çağırın.")

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
        for ay in aylar:
            desi_col, fiyat_col, tutar_col = f"2025 {ay} Desi", f"2025 {ay} Fiyat", f"2025 {ay} Tutar"
            df_nihai[desi_col] = df_nihai[desi_col].apply(guvenli_sayi)
            df_nihai[fiyat_col] = df_nihai[fiyat_col].apply(guvenli_sayi)
            df_nihai[tutar_col] = df_nihai[desi_col] * df_nihai[fiyat_col]
        onceki_fiyat = df_nihai["2025 Aralık Fiyat"].apply(guvenli_sayi)
        for ay in aylar:
            buyume_col, esk_col, desi_col, fiyat_col, tutar_col = f"2026 {ay} Büyüme", f"2026 {ay} Esk.", f"2026 {ay} Desi", f"2026 {ay} Fiyat", f"2026 {ay} Tutar"
            df_nihai[buyume_col] = df_nihai[buyume_col].apply(guvenli_sayi)
            df_nihai[esk_col] = df_nihai[esk_col].apply(guvenli_sayi)
            aktif_eskalasyon = np.where(df_nihai[esk_col] == 0, float(global_enflasyon), df_nihai[esk_col])
            df_nihai[desi_col] = df_nihai[f"2025 {ay} Desi"] * (1 + (df_nihai[buyume_col] / 100))
            df_nihai[fiyat_col] = onceki_fiyat * (1 + (aktif_eskalasyon / 100))
            df_nihai[tutar_col] = df_nihai[desi_col] * df_nihai[fiyat_col]
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
# 3. SEKME: ÇALIŞMA GÜNLERİ
# ------------------------------------------------------------
with sekmeler[2]:
    st.title("📅 Operasyonel Çalışma Günleri")
    takvim_verisi = {
        "Ay": aylar,
        "2025 Çalışma Günü": [22, 20, 21, 22, 21, 20, 23, 21, 22, 23, 20, 22],
        "2026 Çalışma Günü": [21, 20, 20, 21, 17, 22, 22, 21, 22, 21, 21, 23],
        "Resmi Tatiller / Notlar": ["-", "-", "Ramazan Bayramı", "23 Nisan", "Kurban Bayramı", "-", "-", "30 Ağustos", "-", "29 Ekim", "-", "-"]
    }
    st.data_editor(pd.DataFrame(takvim_verisi), use_container_width=True, hide_index=True, key="calendar_grid_key")

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
                    col_desi = f"2026 {ay} Desi"
                    if col_desi in df_m_tmp.columns and df_m_tmp[col_desi].apply(guvenli_sayi).sum() > 0:
                        aktif_aylar_2026.append(col_desi)
                dolu_ay_sayisi = len(aktif_aylar_2026)
            
            desi_toplam_kolon_adi = f"{max(1, dolu_ay_sayisi)} Ay Toplam Desi"
            if not st.session_state.ana_veri.empty and aktif_aylar_2026:
                df_m_tmp[desi_toplam_kolon_adi] = df_m_tmp[aktif_aylar_2026].sum(axis=1)
                desi_grouped = df_m_tmp.groupby("Müşteri Kodu", as_index=False)[desi_toplam_kolon_adi].sum()
                df_hedef = pd.merge(df_hedef, desi_grouped, on="Müşteri Kodu", how="left")
            else: df_hedef[desi_toplam_kolon_adi] = 0.0

            df_hedef[desi_toplam_kolon_adi] = df_hedef[desi_toplam_kolon_adi].fillna(0.0)

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
                        c_d = f"2026 {ay} Desi"
                        if c_d in df_m_tmp.columns and df_m_tmp[c_d].apply(guvenli_sayi).sum() > 0: aktif_aylar_2026.append(c_d)
                    dolu_ay_sayisi = len(aktif_aylar_2026)
                
                desi_toplam_kolon_adi = f"{max(1, dolu_ay_sayisi)} Ay Toplam Desi"
                if not st.session_state.ana_veri.empty and aktif_aylar_2026:
                    df_m_tmp[desi_toplam_kolon_adi] = df_m_tmp[aktif_aylar_2026].sum(axis=1)
                    desi_grouped = df_m_tmp.groupby("Müşteri Kodu", as_index=False)[desi_toplam_kolon_adi].sum()
                    gelen_df = pd.merge(gelen_df, desi_grouped, on="Müşteri Kodu", how="left")
                else: gelen_df[desi_toplam_kolon_adi] = 0.0
                
                gelen_df[desi_toplam_kolon_adi] = gelen_df[desi_toplam_kolon_adi].fillna(0.0)
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
# 9. SEKME: MÜŞTERI BÜYÜME ORANLARI
# ------------------------------------------------------------
with sekmeler[8]:
    st.title("📈 Müşteri Büyüme Oranları ve Desi Simülasyonu")
    st.markdown("Aşağıya müşteri listenizi yükleyebilir ya da **doğrudan aşağıdaki bulut butonlarıyla** veriyi çağırabilirsiniz. `KULLANICAK BÜYÜME` hücresine girdiğiniz oran, 12 aya otomatik yayılır.")

    yuklenen_buyume = st.file_uploader("Büyüme Müşteri Listesi Yükle (Excel/CSV)", type=["xlsx", "xls", "csv"], key="buyume_up_file")

    if yuklenen_buyume:
        df_bg = pd.read_csv(yuklenen_buyume) if yuklenen_buyume.name.lower().endswith(".csv") else pd.read_excel(yuklenen_buyume)
        df_bg.columns = [str(c).strip() for c in df_bg.columns]
        if "Müşteri Kodu" in df_bg.columns:
            df_bg["Müşteri Kodu"] = df_bg["Müşteri Kodu"].apply(guvenli_metin_kodu)
            st.session_state.buyume_ekran_df = df_bg.reindex(columns=[c for c in buyume_ekran_sutunlari if c not in aylar + ["2024 ilk 9 ay desi", "2025 ilk 9 ay desi", "2025 % desi pay", "Y To Y Desi", "25 kullanılan büyüme", "KULLANICAK BÜYÜME", "Gelen Özet Bilgi", "Müşteriden Gelen Büyüme"]]).copy()
            st.success("Müşteri listesi yüklendi, çapraz hesaplamalar yapılıyor...")

    if not st.session_state.buyume_ekran_df.empty:
        df_b_work = st.session_state.buyume_ekran_df.copy()
        df_b_work["Müşteri Kodu"] = df_b_work["Müşteri Kodu"].apply(guvenli_metin_kodu)

        desi_24_map = {}
        desi_25_map = {}

        if not st.session_state.ana_veri.empty:
            df_master_c = st.session_state.ana_veri.copy()
            df_master_c["Müşteri Kodu"] = df_master_c["Müşteri Kodu"].apply(guvenli_metin_kodu)
            
            cols_24_desi = [f"2024 {m} Desi" for m in ilk_9_ay]
            mevcut_24_cols = [c for c in cols_24_desi if c in df_master_c.columns]
            if mevcut_24_cols:
                df_master_c["tmp_24_sum"] = df_master_c[mevcut_24_cols].applymap(guvenli_sayi).sum(axis=1)
                desi_24_map = df_master_c.groupby("Müşteri Kodu")["tmp_24_sum"].sum().to_dict()

            cols_25_desi = [f"2025 {m} Desi" for m in ilk_9_ay]
            mevcut_25_cols = [c for c in cols_25_desi if c in df_master_c.columns]
            if mevcut_25_cols:
                df_master_c["tmp_25_sum"] = df_master_c[mevcut_25_cols].applymap(guvenli_sayi).sum(axis=1)
                desi_25_map = df_master_c.groupby("Müşteri Kodu")["tmp_25_sum"].sum().to_dict()

        final_rows = []
        for idx, row in df_b_work.iterrows():
            mkod = str(row["Müşteri Kodu"])
            dur_v = st.session_state.musteri_ayarlari.get(mkod, {}).get("Durum_2", row.get("Durum", "GEÇERLİ"))
            if dur_v is None: dur_v = "GEÇERLİ"

            d24 = desi_24_map.get(mkod, guvenli_sayi(row.get("2024 ilk 9 ay desi", 0.0)))
            d25 = desi_25_map.get(mkod, guvenli_sayi(row.get("2025 ilk 9 ay desi", 0.0)))

            if mkod not in st.session_state.buyume_ayarlari:
                st.session_state.buyume_ayarlari[mkod] = {
                    "25 kullanılan büyüme": row.get("25 kullanılan büyüme", ""),
                    "KULLANICAK BÜYÜME": guvenli_sayi(row.get("KULLANICAK BÜYÜME", 0.0)),
                    "Gelen Özet Bilgi": row.get("Gelen Özet Bilgi", ""),
                    "Müşteriden Gelen Büyüme": row.get("Müşteriden Gelen Büyüme", "")
                }

            b_set = st.session_state.buyume_ayarlari[mkod]
            kb_orani = guvenli_sayi(b_set["KULLANICAK BÜYÜME"])

            r_dict = {
                "Müşteri Kodu": mkod,
                "Müşteri Adı": row.get("Müşteri Adı", row.get("Ünvan", "")),
                "Müşteri Temsilcisi": row.get("Müşteri Temsilcisi", row.get("Müşteri Temsilcisi 1", "")),
                "Sap Kodu": row.get("Sap Kodu", row.get("Sap No", "")),
                "Durum": dur_v,
                "Kayıt Tarihi": row.get("Kayıt Tarihi", ""),
                "Müşteri Grubu": row.get("Müşteri Grubu", ""),
                "2024 ilk 9 ay desi": d24,
                "2025 ilk 9 ay desi": d25,
                "25 kullanılan büyüme": b_set["25 kullanılan büyüme"],
                "KULLANICAK BÜYÜME": kb_orani,
                "Gelen Özet Bilgi": b_set["Gelen Özet Bilgi"],
                "Müşteriden Gelen Büyüme": b_set["Müşteriden Gelen Büyüme"]
            }

            for m in aylar: r_dict[m] = kb_orani / 100.0
            final_rows.append(r_dict)

        df_final_b = pd.DataFrame(final_rows)
        total_25_desi = df_final_b["2025 ilk 9 ay desi"].sum()
        df_final_b["2025 % desi pay"] = df_final_b["2025 ilk 9 ay desi"] / total_25_desi if total_25_desi > 0 else 0.0
        df_final_b["Y To Y Desi"] = df_final_b.apply(lambda r: (r["2025 ilk 9 ay desi"] / r["2024 ilk 9 ay desi"] - 1) if r["2024 ilk 9 ay desi"] > 0 else 0.0, axis=1)
        df_final_b = df_final_b.reindex(columns=buyume_ekran_sutunlari)

        kilitli_b_cols = [c for c in buyume_ekran_sutunlari if c not in ["25 kullanılan büyüme", "KULLANICAK BÜYÜME", "Gelen Özet Bilgi", "Müşteriden Gelen Büyüme"]]

        edited_b_matris = st.data_editor(
            df_final_b, use_container_width=True, height=400, disabled=kilitli_b_cols,
            column_config={
                "2025 % desi pay": st.column_config.NumberColumn("2025 % desi pay", format="%.2f%%"),
                "Y To Y Desi": st.column_config.NumberColumn("Y To Y Desi", format="%.2f%%"),
                "KULLANICAK BÜYÜME": st.column_config.NumberColumn("KULLANICAK BÜYÜME", format="%.2f"),
                **{m: st.column_config.NumberColumn(m, format="%.2f%%") for m in aylar}
            }, key="buyume_matris_editoru"
        )

        st.markdown("---")
        cb_1, cb_2, cb_3 = st.columns(3)
        if cb_1.button("💾 Büyüme Kartlarını Hafızaya Kaydet", type="primary", use_container_width=True, key="btn_b_hfz_save"):
            for idx, row in edited_b_matris.iterrows():
                mk = str(row["Müşteri Kodu"])
                st.session_state.buyume_ayarlari[mk] = {
                    "25 kullanılan büyüme": row["25 kullanılan büyüme"], "KULLANICAK BÜYÜME": guvenli_sayi(row["KULLANICAK BÜYÜME"]),
                    "Gelen Özet Bilgi": row["Gelen Özet Bilgi"], "Müşteriden Gelen Büyüme": row["Müşteriden Gelen Büyüme"]
                }
            st.success("Büyüme stratejileri hafızaya mühürlendi!")
            st.rerun()

        if rev_secenekleri:
            r_id_b = rev_secenekleri[cb_2.selectbox("Büyüme İçin Bulut Versiyonu:", list(rev_secenekleri.keys()), key="sb_b_rev_box")]
            if cb_2.button("💾 Büyüme Verilerini Buluta Gönder", use_container_width=True, key="btn_b_cloud_save"):
                izin_verilen_b_db = ["Müşteri Kodu", "Müşteri Adı", "Müşteri Temsilcisi", "Sap Kodu", "Durum", "Kayıt Tarihi", "Müşteri Grubu", "25 kullanılan büyüme", "KULLANICAK BÜYÜME", "Gelen Özet Bilgi", "Müşteriden Gelen Büyüme"]
                b_records = [{col: json_uyumlu_deger(row[col]) for col in izin_verilen_b_db if col in row} for _, row in edited_b_matris.iterrows()]
                for r in b_records: r["revizyon_id"] = r_id_b
                client.table("buyume_tablosu").delete().eq("revizyon_id", r_id_b).execute()
                for i in range(0, len(b_records), 500): client.table("buyume_tablosu").insert(b_records[i:i+500]).execute()
                st.success("🎉 Müşteri büyüme oranları seçili versiyona mühürlendi!")

            if cb_3.button("🔄 Dosyasız Buluttan Büyüme Kartlarını Çek", use_container_width=True, key="btn_b_cloud_load"):
                b_res = client.table("buyume_tablosu").select("*").eq("revizyon_id", r_id_b).execute()
                if b_res.data:
                    gelen_b_df = pd.DataFrame(b_res.data)
                    if "id" in gelen_b_df.columns: gelen_b_df = gelen_b_df.drop(columns=["id"])
                    st.session_state.buyume_ekran_df = gelen_b_df.copy()
                    for _, row in gelen_b_df.iterrows():
                        mk = str(row["Müşteri Kodu"])
                        st.session_state.buyume_ayarlari[mk] = {
                            "25 kullanılan büyüme": row.get("25 kullanılan büyüme"), "KULLANICAK BÜYÜME": guvenli_sayi(row.get("KULLANICAK BÜYÜME")),
                            "Gelen Özet Bilgi": row.get("Gelen Özet Bilgi"), "Müşteriden Gelen Büyüme": row.get("Müşteriden Gelen Büyüme")
                        }
                    st.success("🎉 Tüm senaryo bağımsız olarak buluttan çekildi.")
                    st.rerun()
