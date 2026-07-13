import streamlit as st
import pandas as pd
import numpy as np
import io

st.set_page_config(page_title="Gelişmiş Bütçe Simülatörü", layout="wide")

# --- SÜTUN YAPISININ PROGRAMMATİK OLARAK HAZIRLANMASI ---
aylar = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]

ana_kolonlar = [
    "Uniq ID", "Yıl", "Teslimat Tipi", "Atf Tipi", "Çıkış İl Adı", "Çıkış Şube Adı", "Varış İl Adı", "Varış Şube Adı",
    "İlk Okutma Şubesi", "Müşteri Kodu", "Müşteri Adı", "Müşteri Temsilcisi", "Sap Kodu", "Durum", "Kayıt Tarihi", "Müşteri Grubu"
]
parametre_kolonlari = [
    "Yakıt Değişim Yüzdesi (%)", "Yakıt Anlık Değişim Oranı (%)", "Yakıt Değişim Periyodu (Ay)",
    "Enf. Değişim Yüzdesi (%)", "Enf. Değişim Periyodu (Ay)", " Esk. Baz Yakıt Fiyatı ", "Esk. Yakıt Başlangıç Tarihi", "Esk. Enf. Başlangıç Tarihi"
]

# 2025 ve 2026 Aylık Kolon Grupları
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

# --- GÜVENLİ SAYI DÖNÜŞTÜRÜCÜ (Türkçe Format Hassasiyeti) ---
def guvenli_sayi(val):
    if pd.isna(val): return 0.0
    if isinstance(val, (int, float)): return float(val)
    
    val = str(val).strip()
    if val in ['-', '', 'nan', 'NaN']: return 0.0
    
    # "₺", "%" ve boşlukları temizle
    val = val.replace('₺', '').replace('%', '').replace(' ', '')
    
    # Binlik ayırıcı (nokta) ve ondalık ayırıcı (virgül) kontrolü (Örn: 1.049,50)
    if ',' in val and '.' in val:
        val = val.replace('.', '') # Binlik ayırıcıyı yok et
        val = val.replace(',', '.') # Ondalığı Python standartına çevir
    elif ',' in val:
        val = val.replace(',', '.')
        
    try:
        return float(val)
    except:
        return 0.0

# --- SESSION STATE (HAFIZA) BAŞLATMA ---
if 'ana_veri' not in st.session_state:
    st.session_state.ana_veri = pd.DataFrame(columns=tum_kolonlar)

# --- 1. SEKMELİ YAPI ---
sekme1, sekme2 = st.tabs(["🚚 Çarşaf Liste & Bütçe", "📅 Çalışma Günleri Takvimi"])

with sekme1:
    st.title("🚚 Operasyonel Bütçe Simülatörü")
    st.markdown("Excel dosyanızı yükleyin, verileri ekleyin veya temizleyin. Tüm eskalasyonlar arka planda kumülatif hesaplanır.")

    # --- SIDEBAR (KONTROL PANELİ) ---
    st.sidebar.header("📁 Veri Yükleme Yönetimi")
    
    yuklenen_dosya = st.sidebar.file_uploader("SharePoint / Yerel Excel Yükle", type=["xlsx", "xls", "csv"])
    
    col_btn1, col_btn2 = st.sidebar.columns(2)
    
    if col_btn1.button("📥 Veriyi Ekle"):
        if yuklenen_dosya is not None:
            try:
                # Excel'i veya CSV'yi oku
                if yuklenen_dosya.name.endswith('.csv'):
                    yeni_df = pd.read_csv(yuklenen_dosya)
                else:
                    yeni_df = pd.read_excel(yuklenen_dosya)
                
                # Eksik kolonları güvenceye al ve sadece bizim şablondaki kolonları al
                yeni_df = yeni_df.reindex(columns=tum_kolonlar)
                
                # Mevcut verinin altına ekle
                st.session_state.ana_veri = pd.concat([st.session_state.ana_veri, yeni_df], ignore_index=True)
                st.sidebar.success(f"{len(yeni_df)} satır başarıyla eklendi!")
            except Exception as e:
                st.sidebar.error(f"Dosya okuma hatası: {e}")
        else:
            st.sidebar.warning("Lütfen önce bir dosya yükleyin.")

    if col_btn2.button("🗑️ Temizle"):
        # Hafızayı sıfırla
        st.session_state.ana_veri = pd.DataFrame(columns=tum_kolonlar)
        st.sidebar.success("Tüm veriler temizlendi!")

    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ Global Bütçe Revizyonu")
    global_enflasyon = st.sidebar.slider("2026 Global Eskalasyon (%)", 0, 100, 0, step=1)

    # --- VERİ EDİTÖRÜ (GİRİŞ KATMANI) ---
    st.subheader("📝 1. Çarşaf Liste Veri Girişi")
    
    duzenlenen_df = st.data_editor(
        st.session_state.ana_veri,
        num_rows="dynamic",
        use_container_width=True,
        height=300
    )

    # --- MATEMATİKSEL HESAPLAMA MOTORU (KUMÜLATİF) ---
    if not duzenlenen_df.empty:
        df_nihai = duzenlenen_df.copy()

        # 1. Aşama: 2025 Güvenliği
        for ay in aylar:
            df_nihai[f"2025 {ay} Desi"] = df_nihai[f"2025 {ay} Desi"].apply(guvenli_sayi)
            df_nihai[f"2025 {ay} Fiyat"] = df_nihai[f"2025 {ay} Fiyat"].apply(guvenli_sayi)
            df_nihai[f"2025 {ay} Tutar"] = df_nihai[f"2025 {ay} Desi"] * df_nihai[f"2025 {ay} Fiyat"]

        # 2. Aşama: 2026 Kumülatif Hesaplama
        onceki_fiyat = df_nihai["2025 Aralık Fiyat"]

        for ay in aylar:
            df_nihai[f"2026 {ay} Büyüme"] = df_nihai[f"2026 {ay} Büyüme"].apply(guvenli_sayi)
            
            # Eğer hücre boşsa veya 0 ise, sidebar'daki global enflasyonu kullan. Yoksa hücredekini kullan.
            df_nihai[f"2026 {ay} Esk."] = df_nihai[f"2026 {ay} Esk."].apply(guvenli_sayi)
            aktif_eskalasyon = np.where(df_nihai[f"2026 {ay} Esk."] == 0, global_enflasyon, df_nihai[f"2026 {ay} Esk."])
            
            # Desi Hesaplama
            df_nihai[f"2026 {ay} Desi"] = df_nihai[f"2025 {ay} Desi"] * (1 + (df_nihai[f"2026 {ay} Büyüme"] / 100))
            
            # Kumülatif Fiyat
            df_nihai[f"2026 {ay} Fiyat"] = onceki_fiyat * (1 + (aktif_eskalasyon / 100))
            
            # Tutar
            df_nihai[f"2026 {ay} Tutar"] = df_nihai[f"2026 {ay} Desi"] * df_nihai[f"2026 {ay} Fiyat"]
            
            # Hafızayı Güncelle
            onceki_fiyat = df_nihai[f"2026 {ay} Fiyat"]

        st.markdown("---")
        st.subheader("📊 2. Projeksiyon Sonuçları")

        toplam_2025_tutar = sum(df_nihai[f"2025 {ay} Tutar"].sum() for ay in aylar)
        toplam_2026_tutar = sum(df_nihai[f"2026 {ay} Tutar"].sum() for ay in aylar)
        fark = toplam_2026_tutar - toplam_2025_tutar

        m1, m2, m3 = st.columns(3)
        m1.metric("2025 Toplam Gerçekleşen Tutar", value=f"₺{toplam_2025_tutar:,.2f}")
        m2.metric("2026 Projeksiyon Toplam Bütçe", value=f"₺{toplam_2026_tutar:,.2f}", delta="Artış Etkisi")
        m3.metric("Bütçe Üzerindeki Toplam Artış Yükü", value=f"₺{fark:,.2f}")

        # Nihai tablo formatlaması
        st.dataframe(df_nihai, use_container_width=True)
    else:
        st.info("👆 Başlamak için sol menüden bir Excel dosyası yükleyip 'Veriyi Ekle' butonuna basın veya yukarıdaki tabloya manuel satır ekleyin.")

with sekme2:
    st.title("📅 Operasyonel Çalışma Günleri")
    st.markdown("Buraya gireceğiniz çalışma günleri ileride desi veya kapasite hesaplamalarına çarpan olarak eklenebilir.")

    takvim_verisi = {
        "Ay": aylar,
        "2025 Çalışma Günü": [22, 20, 21, 22, 21, 20, 23, 21, 22, 23, 20, 22],
        "2026 Çalışma Günü": [21, 20, 20, 21, 17, 22, 22, 21, 22, 21, 21, 23],
        "Resmi Tatiller / Notlar": ["-", "-", "Ramazan Bayramı", "23 Nisan", "Kurban Bayramı", "-", "-", "30 Ağustos", "-", "29 Ekim", "-", "-"]
    }
    
    st.data_editor(pd.DataFrame(takvim_verisi), use_container_width=True, hide_index=True)
