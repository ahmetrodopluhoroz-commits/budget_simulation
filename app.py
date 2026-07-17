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
TARIH_KOLONLARI = ["Kayıt Tarihi", "Esk. Yakıt Başlangıç Tarihi", "Esk. Enf. Başlangıç Tarihi"]

# ============================================================
# YARDIMCI FONKSİYONLAR
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
    tamsayi = guvenli_tamsayi(value, nullable=True)
    return str(tamsayi) if tamsayi is not None else str(value).strip()

def bos_deger_mi(value):
    if value is None: return True
    if isinstance(value, (float, np.floating)): return not np.isfinite(float(value))
    try: return bool(pd.isna(value))
    except: return False

def json_uyumlu_deger(value):
    if bos_deger_mi(value): return None
    if isinstance(value, (pd.Timestamp, datetime, date)): return value.strftime("%Y-%m-%d")
    if isinstance(value, np.integer): return int(value)
    if isinstance(value, np.floating): return float(value) if np.isfinite(float(value)) else None
    if isinstance(value, np.bool_): return bool(value)
    return value

def tarih_duzenle(value):
    if bos_deger_mi(value): return None
    if isinstance(value, (pd.Timestamp, datetime, date)): return value.strftime("%Y-%m-%d")
    parsed_date = pd.to_datetime(value, errors="coerce", dayfirst=True)
    if pd.isna(parsed_date): return None
    return parsed_date.strftime("%Y-%m-%d")

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
    df = df.reindex(columns=tum_kolonlar)
    df = df.dropna(how="all").reset_index(drop=True)
    df = uniq_id_hazirla(df)
    
    for c in BIGINT_KOLONLAR:
        if c in df.columns: df[c] = df[c].apply(lambda v: guvenli_tamsayi(v, nullable=True))
    for c in NUMERIC_KOLONLAR:
        if c in df.columns: df[c] = df[c].apply(lambda v: float(guvenli_sayi(v)))
    for c in TARIH_KOLONLARI:
        if c in df.columns: df[c] = df[c].apply(tarih_duzenle)
        
    records = []
    for _, row in df.iterrows():
        records.append({c: json_uyumlu_deger(v) for c, v in row.items()})
    return df, records

# ============================================================
# SESSION STATE & SUPABASE AYARLARI
# ============================================================
if "ana_veri" not in st.session_state: st.session_state.ana_veri = pd.DataFrame(columns=tum_kolonlar)
if "editor_key" not in st.session_state: st.session_state.editor_key = 0
if "musteri_ayarlari" not in st.session_state: st.session_state.musteri_ayarlari = {}

GIZLI_SUPABASE_URL = "https://bejimguyethsxdyhtttp.supabase.co"
GIZLI_SUPABASE_KEY = "sb_publishable_TXXAdObu4G68RolqZYwdIA_6xJiQIXO"

def get_supabase_client():
    if not SUPABASE_AVAILABLE: return None
    try: return create_client(GIZLI_SUPABASE_URL, GIZLI_SUPABASE_KEY)
    except: return None

# ============================================================
# ARAYÜZ SEKMELERİ
# ============================================================
sekme1, sekme2, sekme3, sekme4 = st.tabs([
    "🚚 Çarşaf Liste & Bütçe", 
    "📅 Çalışma Günleri Takvimi", 
    "☁️ Bulut Revizyon Yönetimi",
    "👤 Yeni-Bütçe Müşteri"
])

# ------------------------------------------------------------
# 1. SEKME: ANA BÜTÇE EKRANI
# ------------------------------------------------------------
with sekme1:
    st.title("🚚 Operasyonel Bütçe Simülatörü")

    st.sidebar.markdown("---")
    st.sidebar.header("📁 Lokal Veri Yönetimi")
    yuklenen_dosya = st.sidebar.file_uploader("Excel / CSV Yükle", type=["xlsx", "xls", "csv"])
    
    yukleme_tipi = st.sidebar.radio(
        "Yükleme Amacı:", 
        [
            "Yeni Satırlar Ekle", 
            "Düşeyara (VLOOKUP) ile Güncelle"
        ],
        help="Sadece Uniq ID ve güncellemek istediğiniz sütunları içeren bir Excel yükleyin. Sistem eşleşen ID'leri bulup verileri üzerine yazar."
    )
    
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
                st.sidebar.success(f"Düşeyara tamamlandı! {len(guncellenecek_sutunlar)} sütun başarıyla güncellendi.")
                st.rerun()
            else:
                st.sidebar.error("Düşeyara yapabilmek için ekranda veri olmalı ve yüklediğiniz Excel'de mutlaka 'Uniq ID' sütunu bulunmalıdır.")
        else:
            yeni_df = yeni_df.reindex(columns=tum_kolonlar)
            st.session_state.ana_veri = pd.concat([st.session_state.ana_veri, yeni_df], ignore_index=True)
            st.session_state.editor_key += 1
            st.sidebar.success(f"{len(yeni_df)} yeni satır bütçeye eklendi.")
            st.rerun()

    if c2.button("🗑️ Havuzu Temizle", key="havuzu_temizle_btn"):
        st.session_state.ana_veri = pd.DataFrame(columns=tum_kolonlar)
        st.session_state.musteri_ayarlari = {}
        st.session_state.editor_key += 1
        st.sidebar.success("Tüm bütçe hafızası sıfırlandı.")
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.header("🔍 Dinamik Filtreleme")
    filtre_kolonlari = st.sidebar.multiselect("Filtrelemek İstediğiniz Sütunları Seçin:", options=tum_kolonlar)
    
    mask = pd.Series(True, index=st.session_state.ana_veri.index)
    if filtre_kolonlari:
        st.sidebar.markdown("**Filtre Değerlerini Seçin:**")
        for col in filtre_kolonlari:
            unique_vals = st.session_state.ana_veri[col].dropna().unique().tolist()
            secilen_degerler = st.sidebar.multiselect(f"{col}:", options=unique_vals, default=unique_vals)
            mask &= st.session_state.ana_veri[col].isin(secilen_degerler)
            
    gosterilecek_df = st.session_state.ana_veri[mask]
    gizli_df = st.session_state.ana_veri[~mask]
    
    st.sidebar.markdown("---")
    with st.sidebar.expander("🧹 Sütun Bazlı İçerik Sıfırlama"):
        silinecek_sutun = st.selectbox("İçini boşaltmak istediğiniz sütun:", options=["Seçiniz..."] + tum_kolonlar)
        if st.button("Sütun İçini Sıfırla (0.0 Yap)") and silinecek_sutun != "Seçiniz...":
            if not st.session_state.ana_veri.empty:
                if silinecek_sutun in BIGINT_KOLONLAR:
                    st.session_state.ana_veri[silinecek_sutun] = 0
                elif silinecek_sutun in NUMERIC_KOLONLAR:
                    st.session_state.ana_veri[silinecek_sutun] = 0.0
                else:
                    st.session_state.ana_veri[silinecek_sutun] = ""
                st.session_state.editor_key += 1
                st.success(f"'{silinecek_sutun}' sütununun içeriği sıfırlandı! Yeni verileri yükleyebilir veya girebilirsiniz.")
                st.rerun()

    st.sidebar.markdown("---")
    global_enflasyon = st.sidebar.slider("2026 Global Eskalasyon (%)", 0, 100, 0, step=1)

    st.subheader("📝 1. Çarşaf Liste Veri Girişi")
    if filtre_kolonlari:
        st.info(f"Filtre aktif: Toplam {len(st.session_state.ana_veri)} kaydın {len(gosterilecek_df)} tanesi gösteriliyor.")
    
    duzenlenen_df = st.data_editor(
        gosterilecek_df, 
        num_rows="dynamic", 
        use_container_width=True, 
        height=400, 
        key=f"butce_veri_{st.session_state.editor_key}" 
    )

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
        st.subheader("📊 2. Projeksiyon Sonuçları ve Çıktı Yönetimi")
        
        t25 = sum(df_nihai[f"2025 {ay} Tutar"].sum() for ay in aylar)
        t26 = sum(df_nihai[f"2026 {ay} Tutar"].sum() for ay in aylar)
        m1, m2, m3 = st.columns(3)
        m1.metric("2025 Toplam Gerçekleşen", value=f"₺{t25:,.2f}")
        m2.metric("2026 Projeksiyon Toplamı", value=f"₺{t26:,.2f}", delta="Artış")
        m3.metric("Bütçeye Gelen Ek Yük", value=f"₺{(t26-t25):,.2f}")

        col_down1, col_down2 = st.columns([1, 1.5])
        
        with col_down1:
            output_excel = io.BytesIO()
            with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
                df_nihai.to_excel(writer, index=False, sheet_name="Bütçe")
            st.download_button("📥 Excel Olarak İndir", output_excel.getvalue(), "horoz_butce.xlsx", use_container_width=True)

        with col_down2:
            with st.expander("🚀 Yeni Bir Versiyon Olarak Buluta Kaydet", expanded=True):
                kisi = st.text_input("Revizyonu Yapan Kişi")
                not_ = st.text_input("Revizyon Notu", placeholder="Örn: Ekim 2026 gerçekleşen veriler yüklendi.")
                
                if st.button("💾 Senaryoyu Kaydet", use_container_width=True):
                    client = get_supabase_client()
                    if client:
                        try:
                            with st.spinner("Yeni versiyon oluşturuluyor..."):
                                df_bulut, records = supabase_verisini_hazirla(df_nihai)
                                yeni_rev_id = f"REV-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                                
                                client.table("revizyon_log").insert({
                                    "revizyon_id": yeni_rev_id,
                                    "olusturan_kisi": kisi,
                                    "revizyon_notu": not_
                                }).execute()
                                
                                for r in records: r["revizyon_id"] = yeni_rev_id
                                
                                for i in range(0, len(records), 500):
                                    client.table("butce_tablosu").insert(records[i:i+500]).execute()
                                    
                            st.success(f"🎉 Başarılı! Veri '{kisi}' adına yeni bir versiyon olarak kaydedildi.")
                        except Exception as e:
                            st.error(f"Kayıt Hatası: {e}")
                    else:
                        st.error("Lütfen Supabase bağlantısını yapın.")

        st.dataframe(df_nihai, use_container_width=True)

# ------------------------------------------------------------
# 2. SEKME: ÇALIŞMA GÜNLERİ
# ------------------------------------------------------------
with sekme2:
    st.title("📅 Operasyonel Çalışma Günleri")
    takvim_verisi = {
        "Ay": aylar,
        "2025 Çalışma Günü": [22, 20, 21, 22, 21, 20, 23, 21, 22, 23, 20, 22],
        "2026 Çalışma Günü": [21, 20, 20, 21, 17, 22, 22, 21, 22, 21, 21, 23],
        "Resmi Tatiller / Notlar": ["-", "-", "Ramazan Bayramı", "23 Nisan", "Kurban Bayramı", "-", "-", "30 Ağustos", "-", "29 Ekim", "-", "-"]
    }
    st.data_editor(pd.DataFrame(takvim_verisi), use_container_width=True, hide_index=True)

# ------------------------------------------------------------
# 3. SEKME: BULUT REVİZYON YÖNETİMİ
# ------------------------------------------------------------
with sekme3:
    st.title("☁️ Bulut Revizyon Geçmişi")
    st.markdown("Aşağıdaki listeden **işlem yapmak istediğiniz versiyonun başındaki kutucuğu** işaretleyin.")
    
    client = get_supabase_client()
    if client:
        try:
            log_res = client.table("revizyon_log").select("*").order("kayit_zamani", desc=True).execute()
            
            if log_res.data:
                df_log = pd.DataFrame(log_res.data)
                df_log["kayit_zamani"] = pd.to_datetime(df_log["kayit_zamani"]).dt.strftime("%Y-%m-%d %H:%M")
                
                df_log_gorsel = df_log.rename(columns={
                    "kayit_zamani": "Kayıt Tarihi",
                    "olusturan_kisi": "Oluşturan Kişi",
                    "revizyon_notu": "Revizyon Notu",
                    "revizyon_id": "Versiyon Kodu"
                })
                
                df_log_gorsel.insert(0, "Seç", False)
                
                edited_log = st.data_editor(
                    df_log_gorsel, 
                    hide_index=True, 
                    use_container_width=True,
                    disabled=["Kayıt Tarihi", "Oluşturan Kişi", "Revizyon Notu", "Versiyon Kodu"]
                )
                
                secili_satirlar = edited_log[edited_log["Seç"] == True]
                
                if len(secili_satirlar) > 1:
                    st.warning("⚠️ Lütfen aynı anda sadece **bir tane** versiyon seçin.")
                
                elif len(secili_satirlar) == 1:
                    secili_rev = secili_satirlar.iloc[0]["Versiyon Kodu"]
                    
                    st.markdown("---")
                    st.subheader("🛠️ Seçili Versiyon İşlemleri")
                    c_sol, c_sag = st.columns(2)
                    
                    if c_sol.button("📥 Seçili Versiyonu Ekrana Çek (Yükle)", type="primary", use_container_width=True, key="versiyon_yukle_btn"):
                        with st.spinner("Bütçe verileri buluttan indiriliyor..."):
                            data_res = client.table("butce_tablosu").select("*").eq("revizyon_id", secili_rev).execute()
                            if data_res.data:
                                gelen_df = pd.DataFrame(data_res.data)
                                gelen_df.columns = [str(c).strip() for c in gelen_df.columns]
                                st.session_state.ana_veri = gelen_df.reindex(columns=tum_kolonlar)
                                
                                st.session_state.editor_key += 1
                                st.success("🎉 Versiyon başarıyla hafızaya alındı! 'Çarşaf Liste & Bütçe' sekmesine giderek veriler üzerinde çalışabilirsiniz.")
                            else:
                                st.warning("Bu versiyona ait detaylı bütçe kaydı bulunamadı.")
                    
                    if c_sag.button("🗑️ Seçili Versiyonu Kalıcı Olarak Sil", type="secondary", use_container_width=True, key="versiyon_sil_btn"):
                        with st.spinner("Versiyon buluttan tamamen siliniyor..."):
                            client.table("butce_tablosu").delete().eq("revizyon_id", secili_rev).execute()
                            client.table("revizyon_log").delete().eq("revizyon_id", secili_rev).execute()
                            
                            st.success("Versiyon ve içerdiği tüm veriler kalıcı olarak silindi!")
                            st.rerun() 
            else:
                st.info("Sistemde henüz kaydedilmiş bir bütçe versiyonu bulunmuyor.")
        except Exception as e:
            st.error(f"Veritabanına erişilirken bir hata oluştu: {e}")
    else:
        st.error("Lütfen Supabase bağlantı ayarlarının yapıldığından emin olun.")

# ------------------------------------------------------------
# 4. SEKME: YENİ-BÜTÇE MÜŞTERİ (MÜŞTERİ LİSTESİ YÜKLEME)
# ------------------------------------------------------------
with sekme4:
    st.title("👤 Yeni-Bütçe Müşteri Detay Yönetimi")
    st.markdown("Aşağıya sadece işlem yapmak istediğiniz (Müşteri Kodu, Adı vb. içeren) **müşteri listesini (Excel/CSV)** yükleyin. Sistem, ana bütçeden toplam desileri Düşeyara mantığıyla getirip ekranı sizin için hazırlayacaktır.")

    # SADECE MÜŞTERİ YÜKLEME ALANI
    yuklenen_musteri = st.file_uploader("Müşteri Listenizi Yükleyin (Excel veya CSV)", type=["xlsx", "xls", "csv"], key="musteri_sablonu_yukle")

    if yuklenen_musteri:
        df_hedef = pd.read_csv(yuklenen_musteri) if yuklenen_musteri.name.lower().endswith(".csv") else pd.read_excel(yuklenen_musteri)
        
        # Müşteri Kodu kolonu zorunlu
        if "Müşteri Kodu" not in df_hedef.columns:
            st.error("❌ Yüklediğiniz dosyada eşleştirme yapılabilmesi için mutlaka **'Müşteri Kodu'** adında bir sütun bulunmalıdır!")
        else:
            # 1. Hedef listedeki Müşteri Kodlarını string'e çevirip garantile
            df_hedef["Müşteri Kodu"] = df_hedef["Müşteri Kodu"].apply(guvenli_metin_kodu)
            
            # 2. Çarşaf Listeden (st.session_state.ana_veri) dolu ay sayısını ve desileri bul
            aktif_aylar_2026 = []
            dolu_ay_sayisi = 0
            
            if not st.session_state.ana_veri.empty:
                df_master_tmp = st.session_state.ana_veri.copy()
                df_master_tmp["Müşteri Kodu"] = df_master_tmp["Müşteri Kodu"].apply(guvenli_metin_kodu)
                
                for ay in aylar:
                    col_desi = f"2026 {ay} Desi"
                    if col_desi in df_master_tmp.columns:
                        if df_master_tmp[col_desi].apply(guvenli_sayi).sum() > 0:
                            aktif_aylar_2026.append(col_desi)
                
                dolu_ay_sayisi = len(aktif_aylar_2026)
            
            desi_toplam_kolon_adi = f"{max(1, dolu_ay_sayisi)} Ay Toplam Desi" # En az 1 ay gibi isimlendir
            
            # 3. Düşeyara (Merge) Mantığıyla Desileri Hedef Tabloya Çek
            if not st.session_state.ana_veri.empty and aktif_aylar_2026:
                df_master_tmp[desi_toplam_kolon_adi] = df_master_tmp[aktif_aylar_2026].applymap(guvenli_sayi).sum(axis=1)
                desi_grouped = df_master_tmp.groupby("Müşteri Kodu", as_index=False)[desi_toplam_kolon_adi].sum()
                
                # Eşleştir
                df_hedef = pd.merge(df_hedef, desi_grouped, on="Müşteri Kodu", how="left")
            else:
                # Ana bütçe boşsa desiler 0 gelsin
                df_hedef[desi_toplam_kolon_adi] = 0.0
                
            # Eşleşmeyen/Boş kalan desileri 0.0 yap
            df_hedef[desi_toplam_kolon_adi] = df_hedef[desi_toplam_kolon_adi].fillna(0.0)
            
            # 4. Kalan Düzenlenebilir Kolonları (Durum_2, Yeni Müşteri vb.) Hafızadan Doldur
            for idx, row in df_hedef.iterrows():
                m_kod = str(row["Müşteri Kodu"])
                if m_kod not in st.session_state.musteri_ayarlari:
                    # Mevcut dosyadaki Durum'u çek veya GEÇERLİ varsay
                    varsayilan_durum = row.get("Durum", "GEÇERLİ")
                    
                    st.session_state.musteri_ayarlari[m_kod] = {
                        "Yeni/Bütçelenen Müşteri": "03.Bütçelenen",
                        "Durum_2": varsayilan_durum if varsayilan_durum in ["GEÇERLİ", "GEÇERSİZ"] else None,
                        "Durum_3": "2026 yılında çalışmaya devam edecektir" if varsayilan_durum == "GEÇERLİ" else "",
                        "Serbest Not": ""
                    }
                    
            # Session State'teki değerleri tabloya yedir
            df_hedef["Yeni/Bütçelenen Müşteri"] = df_hedef["Müşteri Kodu"].apply(lambda k: st.session_state.musteri_ayarlari.get(str(k), {}).get("Yeni/Bütçelenen Müşteri", "03.Bütçelenen"))
            df_hedef["Durum_2"] = df_hedef["Müşteri Kodu"].apply(lambda k: st.session_state.musteri_ayarlari.get(str(k), {}).get("Durum_2", None))
            df_hedef["Durum_3"] = df_hedef["Müşteri Kodu"].apply(lambda k: st.session_state.musteri_ayarlari.get(str(k), {}).get("Durum_3", ""))
            df_hedef["Serbest Not"] = df_hedef["Müşteri Kodu"].apply(lambda k: st.session_state.musteri_ayarlari.get(str(k), {}).get("Serbest Not", ""))
            
            # 5. Değişim Kontrol Formülü
            def degisim_kontrol_formulu_hedef(row):
                d1 = str(row.get("Durum", "")).strip().upper()
                d2 = str(row.get("Durum_2", "")).strip().upper() if row.get("Durum_2") is not None and not pd.isna(row.get("Durum_2")) else ""
                return "DOĞRU" if d1 == d2 else "YANLIŞ"
                
            df_hedef["Değişim kontrol"] = df_hedef.apply(degisim_kontrol_formulu_hedef, axis=1)

            st.success(f"Yüklenen {len(df_hedef)} müşteri başarıyla ana bütçe (çarşaf liste) ile eşleştirildi! Aşağıdaki tablodan doldurmaya başlayabilirsiniz.")

            # Kilitlenecek kolonları belirle (Yüklenen kolonların hepsi + desi + değişim kontrol)
            kilitli_kolonlar = list(df_hedef.columns)
            if "Yeni/Bütçelenen Müşteri" in kilitli_kolonlar: kilitli_kolonlar.remove("Yeni/Bütçelenen Müşteri")
            if "Durum_2" in kilitli_kolonlar: kilitli_kolonlar.remove("Durum_2")
            if "Durum_3" in kilitli_kolonlar: kilitli_kolonlar.remove("Durum_3")
            if "Serbest Not" in kilitli_kolonlar: kilitli_kolonlar.remove("Serbest Not")

            # 6. Ekrana Data Editor'ü Bas
            edited_musteri = st.data_editor(
                df_hedef,
                use_container_width=True,
                height=500,
                disabled=kilitli_kolonlar,
                column_config={
                    "Yeni/Bütçelenen Müşteri": st.column_config.SelectboxColumn(
                        "Yeni/Bütçelenen Müşteri",
                        options=["01.Yeni Müşteri", "02.DOP Bütçe Dışı", "03.Bütçelenen"],
                        required=True
                    ),
                    "Durum_2": st.column_config.SelectboxColumn(
                        "Durum_2",
                        options=["GEÇERLİ", "GEÇERSİZ", None]
                    )
                },
                key="musteri_ekran_editoru_ozel"
            )

            # 7. Kaydet ve Excel Çıktısı Al Butonları
            st.markdown("---")
            c_kaydet, c_indir = st.columns(2)
            
            if c_kaydet.button("💾 Ekranda Yaptığım Değişiklikleri Hafızaya Kaydet", type="primary", use_container_width=True):
                for idx, row in edited_musteri.iterrows():
                    m_kod = str(row["Müşteri Kodu"])
                    st.session_state.musteri_ayarlari[m_kod] = {
                        "Yeni/Bütçelenen Müşteri": row["Yeni/Bütçelenen Müşteri"],
                        "Durum_2": row["Durum_2"] if not pd.isna(row["Durum_2"]) else None,
                        "Durum_3": row["Durum_3"],
                        "Serbest Not": row["Serbest Not"]
                    }
                st.success("Tüm değişiklikler başarıyla hafızaya alındı! Başka bir sayfaya geçseniz dahi kaybolmayacak.")
                st.rerun()

            output_musteri_excel = io.BytesIO()
            with pd.ExcelWriter(output_musteri_excel, engine="openpyxl") as writer:
                edited_musteri.to_excel(writer, index=False, sheet_name="Müşteri Detay Özet")
            
            c_indir.download_button(
                "📥 Ekranda Gördüğüm (Nihai) Tabloyu Excel İndir", 
                output_musteri_excel.getvalue(), 
                "ozel_musteri_durum_detay.xlsx", 
                use_container_width=True
            )
    else:
        st.info("Lütfen örnekteki gibi sadece ilgilendiğiniz müşterileri içeren Excel veya CSV dosyanızı yükleyin.")
