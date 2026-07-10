import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Gelişmiş Bütçe Simülatörü", layout="wide")

# --- 1. SEKMELİ YAPI (TABS) ---
# Uygulamayı iki ayrı sayfaya bölüyoruz
sekme1, sekme2 = st.tabs(["🚚 Çarşaf Liste & Bütçe", "📅 Çalışma Günleri Takvimi"])

# ==========================================
# SEKME 1: 120 KOLONLU ÇARŞAF LİSTE VE BÜTÇE
# ==========================================
with sekme1:
    st.title("🚚 Lojistik & Bütçe Senaryo Simülatörü")
    st.markdown("120 Kolonlu yapı ve aydan aya **bileşik (kumülatif)** hesaplama demosu.")

    # --- SÜTUN YAPISININ PROGRAMMATİK OLARAK HAZIRLANMASI ---
    aylar = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]

    ana_kolonlar = [
        "Yıl", "Teslimat Tipi", "Atf Tipi", "Çıkış İl Adı", "Çıkış Şube Adı", "Varış İl Adı", "Varış Şube Adı",
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

    # Tüm sütunların birleştirilmesi (Tam 120 Kolon)
    tum_kolonlar = (
        ana_kolonlar + parametre_kolonlari + 
        kolonlar_2025_desi + kolonlar_2025_tutar + kolonlar_2025_fiyat +
        kolonlar_2026_buyume + kolonlar_2026_esk + 
        kolonlar_2026_desi + kolonlar_2026_tutar + kolonlar_2026_fiyat
    )

    # --- ÖRNEK VERİ ÜRETİMİ (120 KOLONLU TEK SATIR) ---
    @st.cache_data
    def ornek_carsaf_liste_uret():
        df = pd.DataFrame(columns=tum_kolonlar)
        ornek_satir = {col: 0.0 for col in tum_kolonlar} 
        
        ornek_satir.update({
            "Yıl": "2025-2026", "Teslimat Tipi": "FTL", "Atf Tipi": "Standart",
            "Çıkış İl Adı": "İstanbul", "Çıkış Şube Adı": "Mahmutbey",
            "Varış İl Adı": "İzmir", "Varış Şube Adı": "Bornova",
            "Müşteri Kodu": "M-10045", "Müşteri Adı": "Hedef Lojistik Müşterisi A.Ş.",
            "Müşteri Grubu": "Stratejik", "Durum": "Aktif"
        })
        
        # 2025 Yılı için Örnek Başlangıç Değerleri (Aylık 10 TL ile başlatıyoruz)
        for ay in aylar:
            ornek_satir[f"2025 {ay} Desi"] = 5000.0
            ornek_satir[f"2025 {ay} Fiyat"] = 10.00
            ornek_satir[f"2025 {ay} Tutar"] = 50000.0
            ornek_satir[f"2026 {ay} Büyüme"] = 0.05 
            ornek_satir[f"2026 {ay} Esk."] = 10.0 # Örnek %10 artış girili geliyor
            
        df = pd.concat([df, pd.DataFrame([ornek_satir])], ignore_index=True)
        return df

    df_orijinal = ornek_carsaf_liste_uret()

    st.subheader("📝 1. Çarşaf Liste Veri Giriş Ekranı (Yatay Kaydırılabilir)")
    st.markdown("Hücrelere çift tıklayarak değiştirebilirsiniz. **2026 Esk.** kolonlarında yapacağınız % değişiklikler, fiyatları zincirleme etkiler.")

    duzenlenen_df = st.data_editor(
        df_orijinal,
        num_rows="dynamic",
        use_container_width=True
    )

    # --- MATEMATİKSEL HESAPLAMA MOTORU (KUMÜLATİF) ---
    df_nihai = duzenlenen_df.copy()

    # 1. Aşama: Önce 2025 Tutarlarını Güvenceye Alalım
    for ay in aylar:
        df_nihai[f"2025 {ay} Desi"] = pd.to_numeric(df_nihai[f"2025 {ay} Desi"]).fillna(0)
        df_nihai[f"2025 {ay} Fiyat"] = pd.to_numeric(df_nihai[f"2025 {ay} Fiyat"]).fillna(0)
        df_nihai[f"2025 {ay} Tutar"] = df_nihai[f"2025 {ay} Desi"] * df_nihai[f"2025 {ay} Fiyat"]

    # 2. Aşama: 2026 İçin Zincirleme (Kumülatif) Fiyat Hesaplaması
    # Zincirin başlangıç noktası: 2025 Aralık Fiyatı
    onceki_fiyat = df_nihai["2025 Aralık Fiyat"]

    for ay in aylar:
        df_nihai[f"2026 {ay} Büyüme"] = pd.to_numeric(df_nihai[f"2026 {ay} Büyüme"]).fillna(0)
        df_nihai[f"2026 {ay} Esk."] = pd.to_numeric(df_nihai[f"2026 {ay} Esk."]).fillna(0)
        
        # Desi Hesaplama = 2025 Desi * (1 + 2026 Büyüme)
        df_nihai[f"2026 {ay} Desi"] = df_nihai[f"2025 {ay} Desi"] * (1 + df_nihai[f"2026 {ay} Büyüme"])
        
        # KUMÜLATİF FİYAT: Bir önceki ayın fiyatı * (1 + Bu ayın Eskalasyon Oranı)
        # Tabloda girilen %10 gibi değerleri 100'e bölerek işliyoruz
        df_nihai[f"2026 {ay} Fiyat"] = onceki_fiyat * (1 + (df_nihai[f"2026 {ay} Esk."] / 100))
        
        # Tutar = 2026 Desi * 2026 Fiyat
        df_nihai[f"2026 {ay} Tutar"] = df_nihai[f"2026 {ay} Desi"] * df_nihai[f"2026 {ay} Fiyat"]
        
        # HAFIZAYI GÜNCELLE: Sonraki ay için "onceki_fiyat" artık bu ayın hesaplanan fiyatı oldu
        onceki_fiyat = df_nihai[f"2026 {ay} Fiyat"]

    st.markdown("---")

    st.subheader("📊 2. Kumülatif Hesaplanmış Nihai Tablo ve Özet Metrikler")

    toplam_2025_tutar = sum(df_nihai[f"2025 {ay} Tutar"].sum() for ay in aylar)
    toplam_2026_tutar = sum(df_nihai[f"2026 {ay} Tutar"].sum() for ay in aylar)
    fark = toplam_2026_tutar - toplam_2025_tutar

    m1, m2, m3 = st.columns(3)
    m1.metric("2025 Toplam Tutar", value=f"₺{toplam_2025_tutar:,.2f}")
    m2.metric("2026 Projeksiyon Tutar", value=f"₺{toplam_2026_tutar:,.2f}", delta=f"Fark")
    m3.metric("Oluşan Ek Yük", value=f"₺{fark:,.2f}")

    st.dataframe(df_nihai, use_container_width=True)


# ==========================================
# SEKME 2: ÇALIŞMA GÜNLERİ VE TAKVİM
# ==========================================
with sekme2:
    st.title("📅 Operasyonel Çalışma Günleri")
    st.markdown("Buraya gireceğiniz çalışma günleri ileride desi veya kapasite hesaplamalarına çarpan olarak eklenebilir.")

    # Basit bir çalışma takvimi matrisi
    takvim_verisi = {
        "Ay": aylar,
        "2025 Çalışma Günü": [22, 20, 21, 22, 21, 20, 23, 21, 22, 23, 20, 22],
        "2026 Çalışma Günü": [21, 20, 20, 21, 17, 22, 22, 21, 22, 21, 21, 23],
        "Resmi Tatiller / Notlar": ["-", "-", "Ramazan Bayramı", "23 Nisan", "Kurban Bayramı", "-", "-", "30 Ağustos", "-", "29 Ekim", "-", "-"]
    }
    
    takvim_df = pd.DataFrame(takvim_verisi)
    
    # Bu sayfadaki tabloyu da interaktif (düzenlenebilir) yapıyoruz
    duzenlenen_takvim = st.data_editor(
        takvim_df, 
        use_container_width=True, 
        hide_index=True
    )
