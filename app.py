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

st.set_page_config(page_title="Gelişmiş Bütçe Simülatörü", layout="wide")

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

# --- VERİ TİPİ TANIMLARI ---
BIGINT_KOLONLAR = ["Uniq ID", "Yıl", "Yakıt Değişim Periyodu (Ay)", "Enf. Değişim Periyodu (Ay)"]
NUMERIC_KOLONLAR = (["Yakıt Değişim Yüzdesi (%)", "Yakıt Anlık Değişim Oranı (%)", "Enf. Değişim Yüzdesi (%)", "Esk. Baz Yakıt Fiyatı"] +
                    kolonlar_2025_desi + kolonlar_2025_tutar + kolonlar_2025_fiyat + kolonlar_2026_buyume + kolonlar_2026_esk +
                    kolonlar_2026_desi + kolonlar_2026_tutar + kolonlar_2026_fiyat)
TARIH_KOLONLARI = ["Kayıt Tarihi", "Esk. Yakıt Başlangıç Tarihi", "Esk. Enf. Başlangıç Tarihi"]

# --- YARDIMCI FONKSİYONLAR ---
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

# --- SESSION STATE ---
if "ana_veri" not in st.session_state: st.session_state.ana_veri = pd.DataFrame(columns=tum_kolonlar)
if "secili_revizyon" not in st.session_state: st.session_state.secili_revizyon = None

# --- SUPABASE BAĞLANTISI ---
st.sidebar.header("🔐 Supabase Bağlantısı")
url = st.sidebar.text_input("Supabase URL", type="password")
key = st.sidebar.text_input("Supabase API Key", type="password")

def get_supabase_client():
    if SUPABASE_AVAILABLE and url and key:
        try: return create_client(url, key)
        except: return None
    return None

sekme1, sekme2 = st.tabs(["🚚 Çarşaf Liste & Bütçe", "📅 Çalışma Günleri Takvimi"])

with sekme1:
    st.title("🚚 Operasyonel Bütçe Simülatörü")

    # --- LOKAL VERİ YÖNETİMİ ---
    st.sidebar.markdown("---")
    st.sidebar.header("📁 Lokal Veri Yönetimi")
    yuklenen_dosya = st.sidebar.file_uploader("Excel / CSV Yükle", type=["xlsx", "xls", "csv"])
    c1, c2 = st.sidebar.columns(2)
    if c1.button("📥 Veriyi Ekle") and yuklenen_dosya:
        yeni_df = pd.read_csv(yuklenen_dosya) if yuklenen_dosya.name.lower().endswith(".csv") else pd.read_excel(yuklenen_dosya)
        yeni_df.columns = [str(c).strip() for c in yeni_df.columns]
        yeni_df = yeni_df.reindex(columns=tum_kolonlar)
        st.session_state.ana_veri = pd.concat([st.session_state.ana_veri, yeni_df], ignore_index=True)
        st.sidebar.success(f"{len(yeni_df)} satır eklendi.")
    if c2.button("🗑️ Temizle"):
        st.session_state.ana_veri = pd.DataFrame(columns=tum_kolonlar)
        st.sidebar.success("Sıfırlandı.")

    # --- BULUT REVİZYON YÖNETİMİ (YÜKLEME) ---
    st.sidebar.markdown("---")
    st.sidebar.header("🗄️ Bulut Revizyon Yönetimi")
    
    client = get_supabase_client()
    if client:
        try:
            # Önce geçmiş logları çekiyoruz
            log_res = client.table("revizyon_log").select("*").order("kayit_zamani", desc=True).execute()
            if log_res.data:
                # Kullanıcıya göstermek için formatlı bir liste hazırlıyoruz
                revizyonlar = {f"{r['kayit_zamani'][:10]} | {r['olusturan_kisi']} - {r['revizyon_notu']}": r['revizyon_id'] for r in log_res.data}
                secilen_etiket = st.sidebar.selectbox("Geçmiş Senaryolardan Seçin:", list(revizyonlar.keys()))
                st.session_state.secili_revizyon = revizyonlar[secilen_etiket]
                
                if st.sidebar.button("🔄 Seçili Versiyonu Ekrana Çek", type="primary"):
                    with st.spinner("İlgili bütçe versiyonu buluttan indiriliyor..."):
                        # Sadece seçilen revizyona ait verileri çekiyoruz (filtreleme)
                        data_res = client.table("butce_tablosu").select("*").eq("revizyon_id", st.session_state.secili_revizyon).execute()
                        if data_res.data:
                            gelen_df = pd.DataFrame(data_res.data)
                            gelen_df.columns = [str(c).strip() for c in gelen_df.columns]
                            st.session_state.ana_veri = gelen_df.reindex(columns=tum_kolonlar)
                            st.sidebar.success("Başarıyla yüklendi!")
                            st.rerun()
            else:
                st.sidebar.info("Henüz kaydedilmiş bir revizyon yok.")
        except Exception as e:
            st.sidebar.error(f"Revizyonlar çekilemedi: {e}")

    # --- EDİTÖR VE HESAPLAMA ---
    st.sidebar.markdown("---")
    global_enflasyon = st.sidebar.slider("2026 Global Eskalasyon (%)", 0, 100, 0, step=1)

    st.subheader("📝 1. Çarşaf Liste Veri Girişi")
    duzenlenen_df = st.data_editor(st.session_state.ana_veri, num_rows="dynamic", use_container_width=True, height=250)

    if not duzenlenen_df.empty:
        df_nihai = duzenlenen_df.copy()
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

        # --- SONUÇLAR VE KAYIT ---
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
            # --- YENİ VERSİYON KAYIT FORMU ---
            with st.expander("🚀 Yeni Bir Versiyon Olarak Buluta Kaydet", expanded=True):
                kisi = st.text_input("Revizyonu Yapan Kişi", value="Ahmet Rodoplu")
                not_ = st.text_input("Revizyon Notu", placeholder="Örn: 2026 FTL büyüme oranları güncellendi, Berkan & Yiğit onayı eklendi.")
                
                if st.button("💾 Senaryoyu Kaydet", use_container_width=True):
                    if client:
                        try:
                            with st.spinner("Yeni versiyon oluşturuluyor..."):
                                df_bulut, records = supabase_verisini_hazirla(df_nihai)
                                
                                # 1. Eşsiz bir Revizyon ID oluştur
                                yeni_rev_id = f"REV-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                                
                                # 2. Log tablosuna kimin, ne zaman, ne notla yaptığını yaz
                                client.table("revizyon_log").insert({
                                    "revizyon_id": yeni_rev_id,
                                    "olusturan_kisi": kisi,
                                    "revizyon_notu": not_
                                }).execute()
                                
                                # 3. Her bir satıra bu revizyon kimliğini ekle ve ana tabloya gönder
                                for r in records: r["revizyon_id"] = yeni_rev_id
                                
                                for i in range(0, len(records), 500):
                                    client.table("butce_tablosu").insert(records[i:i+500]).execute()
                                    
                            st.success(f"🎉 Başarılı! Veri '{kisi}' adına yeni bir versiyon olarak kaydedildi.")
                        except Exception as e:
                            st.error(f"Kayıt Hatası: {e}")
                    else:
                        st.error("Lütfen Supabase bağlantısını yapın.")

        st.dataframe(df_nihai, use_container_width=True)
