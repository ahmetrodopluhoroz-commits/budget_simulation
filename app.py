import streamlit as st
import pandas as pd
import numpy as np
import io

# Supabase kütüphanesini içeri alıyoruz
# (Eğer henüz kurmadıysanız localde hata vermemesi için güvenli import yapıyoruz)
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

st.set_page_config(page_title="Gelişmiş Bütçe Simülatörü", layout="wide")

# --- SÜTUN YAPISININ PROGRAMMATİK OLARAK HAZIRLANMASI ---
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

tum_kolonlar = (
    ana_kolonlar + parametre_kolonlari + 
    kolonlar_2025_desi + kolonlar_2025_tutar + kolonlar_2025_fiyat +
    kolonlar_2026_buyume + kolonlar_2026_esk + 
    kolonlar_2026_desi + kolonlar_2026_tutar + kolonlar_2026_fiyat
)

# --- GÜVENLİ SAYI DÖNÜŞTÜRÜCÜ ---
def guvenli_sayi(val):
    if pd.isna(val): return 0.0
    if isinstance(val, (int, float)): return float(val)
    val = str(val).strip()
    if val in ['-', '', 'nan', 'NaN']: return 0.0
    val = val.replace('₺', '').replace('%', '').replace(' ', '')
    if ',' in val and '.' in val:
        val = val.replace('.', '').replace(',', '.')
    elif ',' in val:
        val = val.replace(',', '.')
    try: return float(val)
    except: return 0.0

# --- SESSION STATE BAŞLATMA ---
if 'ana_veri' not in st.session_state:
    st.session_state.ana_veri = pd.DataFrame(columns=tum_kolonlar)

# --- SUPABASE BAĞLANTI AYARLARI ---
# Streamlit Secrets veya doğrudan erişim için (Buraya kendi Supabase bilgilerinizi girebilirsiniz)
url = st.sidebar.text_input("Supabase URL", "https://your-project.supabase.co", type="password")
key = st.sidebar.text_input("Supabase API Key", "your-anon-key", type="password")

def get_supabase_client():
    if SUPABASE_AVAILABLE and url != "https://your-project.supabase.co":
        return create_client(url, key)
    return None

# --- ARAYÜZ SEKMELERİ ---
sekme1, sekme2 = st.tabs(["🚚 Çarşaf Liste & Bütçe", "📅 Çalışma Günleri Takvimi"])

with sekme1:
    st.title("🚚 Operasyonel Bütçe Simülatörü")
    st.markdown("Verileri lokalden yükleyebilir, **Excel olarak indirebilir** veya **Supabase bulut veritabanına** senkronize edebilirsiniz.")

    # --- SIDEBAR KONTROLLERİ ---
    st.sidebar.header("📁 Lokal Veri Yönetimi")
    yuklenen_dosya = st.sidebar.file_uploader("Excel / CSV Yükle", type=["xlsx", "xls", "csv"])
    
    c1, c2 = st.sidebar.columns(2)
    if c1.button("📥 Veriyi Ekle"):
        if yuklenen_dosya is not None:
            if yuklenen_dosya.name.endswith('.csv'): yeni_df = pd.read_csv(yuklenen_dosya)
            else: yeni_df = pd.read_excel(yuklenen_dosya)
            yeni_df = yeni_df.reindex(columns=tum_kolonlar)
            st.session_state.ana_veri = pd.concat([st.session_state.ana_veri, yeni_df], ignore_index=True)
            st.sidebar.success(f"{len(yeni_df)} satır hafızaya eklendi.")
            
    if c2.button("🗑️ Hafızayı Temizle"):
        st.session_state.ana_veri = pd.DataFrame(columns=tum_kolonlar)
        st.sidebar.success("Hafıza sıfırlandı.")

    # --- BULUT VERİTABANI KONTROLLERİ (SUPABASE) ---
    st.sidebar.markdown("---")
    st.sidebar.header("🗄️ Bulut Senkronizasyonu (Supabase)")
    
    # Supabase'den veri çekme butonu
    if st.sidebar.button("🔄 Buluttan Son Veriyi Çek (Getir)"):
        client = get_supabase_client()
        if client:
            try:
                # 'butce_tablosu' isimli tablodaki tüm verileri çekiyoruz
                response = client.table("butce_tablosu").select("*").execute()
                if response.data:
                    st.session_state.ana_veri = pd.DataFrame(response.data).reindex(columns=tum_kolonlar)
                    st.sidebar.success("Son bütçe verisi buluttan başarıyla yüklendi!")
                    st.rerun()
                else:
                    st.sidebar.warning("Veritabanında kayıtlı veri bulunamadı.")
            except Exception as e:
                st.sidebar.error(f"Buluttan çekme hatası: {e}")
        else:
            st.sidebar.error("Lütfen geçerli Supabase URL ve Key bilgisi girin.")

    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ Global Bütçe Revizyonu")
    global_enflasyon = st.sidebar.slider("2026 Global Eskalasyon (%)", 0, 100, 0, step=1)

    # --- VERİ EDİTÖRÜ ---
    st.subheader("📝 1. Çarşaf Liste Veri Girişi")
    duzenlenen_df = st.data_editor(st.session_state.ana_veri, num_rows="dynamic", use_container_width=True, height=250)

    # --- HESAPLAMA MOTORU ---
    if not duzenlenen_df.empty:
        df_nihai = duzenlenen_df.copy()

        for ay in aylar:
            df_nihai[f"2025 {ay} Desi"] = df_nihai[f"2025 {ay} Desi"].apply(guvenli_sayi)
            df_nihai[f"2025 {ay} Fiyat"] = df_nihai[f"2025 {ay} Fiyat"].apply(guvenli_sayi)
            df_nihai[f"2025 {ay} Tutar"] = df_nihai[f"2025 {ay} Desi"] * df_nihai[f"2025 {ay} Fiyat"]

        onceki_fiyat = df_nihai["2025 Aralık Fiyat"]

        for ay in aylar:
            df_nihai[f"2026 {ay} Büyüme"] = df_nihai[f"2026 {ay} Büyüme"].apply(guvenli_sayi)
            df_nihai[f"2026 {ay} Esk."] = df_nihai[f"2026 {ay} Esk."].apply(guvenli_sayi)
            aktif_eskalasyon = np.where(df_nihai[f"2026 {ay} Esk."] == 0, global_enflasyon, df_nihai[f"2026 {ay} Esk."])
            
            df_nihai[f"2026 {ay} Desi"] = df_nihai[f"2025 {ay} Desi"] * (1 + (df_nihai[f"2026 {ay} Büyüme"] / 100))
            df_nihai[f"2026 {ay} Fiyat"] = onceki_fiyat * (1 + (aktif_eskalasyon / 100))
            df_nihai[f"2026 {ay} Tutar"] = df_nihai[f"2026 {ay} Desi"] * df_nihai[f"2026 {ay} Fiyat"]
            onceki_fiyat = df_nihai[f"2026 {ay} Fiyat"]

        st.markdown("---")
        st.subheader("📊 2. Projeksiyon Sonuçları ve Çıktı Yönetimi")

        # Özet Metrikler
        toplam_2025_tutar = sum(df_nihai[f"2025 {ay} Tutar"].sum() for ay in aylar)
        toplam_2026_tutar = sum(df_nihai[f"2026 {ay} Tutar"].sum() for ay in aylar)
        fark = toplam_2026_tutar - toplam_2025_tutar

        m1, m2, m3 = st.columns(3)
        m1.metric("2025 Toplam Gerçekleşen", value=f"₺{toplam_2025_tutar:,.2f}")
        m2.metric("2026 Projeksiyon Toplamı", value=f"₺{toplam_2026_tutar:,.2f}", delta="Artış Trendi")
        m3.metric("Bütçeye Gelen Ek Yük", value=f"₺{fark:,.2f}")

        # BUTON ALANI (Excel İndirme ve Buluta Gönderme Yan Yana)
        col_down1, col_down2 = st.columns(2)

        with col_down1:
            # Excel İndirme İşlemi
            output_excel = io.BytesIO()
            with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
                df_nihai.to_excel(writer, index=False, sheet_name='Bütçe Raporu')
            st.download_button(
                label="📥 Mevcut Senaryoyu Excel Olarak İndir",
                data=output_excel.getvalue(),
                file_name="horoz_lojistik_simulasyon_sonuc.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

        with col_down2:
            # Supabase'e Gönderme İşlemi
            if st.button("🚀 Hesaplanan Bu Veriyi Buluta (Supabase) Gönder", use_container_width=True):
                client = get_supabase_client()
                if client:
                    try:
                        with st.spinner("Büyük veri paketi optimize ediliyor ve buluta aktarılıyor..."):
                            # Önce eski veriyi temizle
                            client.table("butce_tablosu").delete().neq("Uniq ID", "YOK").execute()
                            
                            # === ZIRHLAMA ADIMI ===
                            df_bulut = df_nihai.copy()
                            
                            # YENİ EKLENEN KORUMA: Sütun isimlerinin başındaki/sonundaki görünmez boşlukları temizler
                            df_bulut.columns = df_bulut.columns.str.strip()
                            
                            # NaN değerlerini JSON uyumlu None (null) ile değiştir
                            df_bulut = df_bulut.replace({np.nan: None})
                            
                            # Tarih nesnelerini JSON uyumlu metne çeviriyoruz
                            for col in df_bulut.columns:
                                df_bulut[col] = df_bulut[col].apply(lambda x: x.strftime('%Y-%m-%d') if hasattr(x, 'strftime') else x)
                            
                            # Tamamen temizlenmiş sözlüğü üretiyoruz
                            records = df_bulut.to_dict(orient="records")
                            # ==========================================================
                            
                            # Güvenli transfer için 1000'er satırlık chunk'lara bölüyoruz
                            chunk_size = 1000
                            for i in range(0, len(records), chunk_size):
                                chunk = records[i:i + chunk_size]
                                client.table("butce_tablosu").insert(chunk).execute()
                                
                        st.success("🎉 Harika! Tüm veriler başarıyla Supabase'e yazıldı. Diğer kullanıcılar anlık olarak çekebilir.")
                    except Exception as e:
                        st.error(f"Buluta gönderme hatası: {e}")
                else:
                    st.error("Lütfen sol menüdeki Supabase bağlantı parametrelerini doldurun.")

        st.dataframe(df_nihai, use_container_width=True)
    else:
        st.info("👆 Başlamak için veri yükleyin veya manuel satır ekleyin.")

with sekme2:
    st.title("📅 Operasyonel Çalışma Günleri")
    takvim_verisi = {
        "Ay": aylar,
        "2025 Çalışma Günü": [22, 20, 21, 22, 21, 20, 23, 21, 22, 23, 20, 22],
        "2026 Çalışma Günü": [21, 20, 20, 21, 17, 22, 22, 21, 22, 21, 21, 23],
        "Resmi Tatiller / Notlar": ["-", "-", "Ramazan Bayramı", "23 Nisan", "Kurban Bayramı", "-", "-", "30 Ağustos", "-", "29 Ekim", "-", "-"]
    }
    st.data_editor(pd.DataFrame(takvim_verisi), use_container_width=True, hide_index=True)
