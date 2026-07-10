import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Gelişmiş Bütçe Simülatörü", layout="wide")
st.title("🚚 Lojistik & Bütçe Senaryo Simülatörü (Gelişmiş PoC)")
st.markdown("120 Kolonlu çarşaf liste yapısının temassız ve dinamik hesaplama demosu.")

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
def ornek_çarşaf_liste_uret():
    # Boş bir dataframe oluşturup sütunları tanımlıyoruz
    df = pd.DataFrame(columns=tum_kolonlar)
    
    # Simülasyon için 1 satırlık gerçekçi bir veri ekleyelim
    ornek_satir = {col: 0.0 for col in tum_kolonlar} # Varsayılan sayısal değerler
    
    # Metin alanlarını dolduralım
    ornek_satir.update({
        "Yıl": "2025-2026", "Teslimat Tipi": "FTL", "Atf Tipi": "Standart",
        "Çıkış İl Adı": "İstanbul", "Çıkış Şube Adı": "Mahmutbey",
        "Varış İl Adı": "İzmir", "Varış Şube Adı": "Bornova",
        "Müşteri Kodu": "M-10045", "Müşteri Adı": "Hedef Lojistik Müşterisi A.Ş.",
        "Müşteri Grubu": "Stratejik", "Durum": "Aktif"
    })
    
    # 2025 Yılı için Örnek Başlangıç Değerleri (Ocak - Aralık)
    for ay in aylar:
        ornek_satir[f"2025 {ay} Desi"] = 5000.0
        ornek_satir[f"2025 {ay} Fiyat"] = 12.50
        ornek_satir[f"2025 {ay} Tutar"] = 62500.0
        ornek_satir[f"2026 {ay} Büyüme"] = 0.05 # %5 organik büyüme beklentisi
        
    df = pd.concat([df, pd.DataFrame([ornek_satir])], ignore_index=True)
    return df

df_orijinal = ornek_çarşaf_liste_uret()

# --- SIDEBAR / SENARYO YÖNETİMİ ---
st.sidebar.header("⚙️ Global Bütçe Revizyonu")
st.sidebar.markdown("Buradan yapacağınız değişiklikler 2026 yılındaki tüm eskalasyon ve tutar sütunlarını etkiler.")

global_enflasyon = st.sidebar.slider("2026 Yılı Ek Enflasyon Beklentisi (%)", 0, 100, 35, step=5)
global_yakit_etkisi = st.sidebar.slider("2026 Yılı Ek Yakıt Artış Etkisi (%)", 0, 50, 15, step=5)

# --- VERİ EDİTÖRÜ (GİRİŞ KATMANI) ---
st.subheader("📝 1. Çarşaf Liste Veri Giriş Ekranı (Yatay Kaydırılabilir)")
st.markdown("Hücrelere çift tıklayarak değiştirebilirsiniz. Sütunların tamamını görmek için sağa doğru kaydırın:")

duzenlenen_df = st.data_editor(
    df_orijinal,
    num_rows="dynamic",
    use_container_width=True
)

# --- MATEMATİKSEL HESAPLAMA MOTORU (PYTHON ETKİSİ) ---
# Düzenlenen veriyi kopyalayıp 2026 projeksiyonlarını formüle ediyoruz
df_nihai = duzenlenen_df.copy()

# Excel'i kilitleyecek 12 aylık döngüsel hesaplamayı Python vektörel olarak tek seferde yapar
for ay in aylar:
    # Sayısal güvenliği sağla (boş hücreleri sıfırla)
    df_nihai[f"2025 {ay} Desi"] = pd.to_numeric(df_nihai[f"2025 {ay} Desi"]).fillna(0)
    df_nihai[f"2025 {ay} Fiyat"] = pd.to_numeric(df_nihai[f"2025 {ay} Fiyat"]).fillna(0)
    df_nihai[f"2026 {ay} Büyüme"] = pd.to_numeric(df_nihai[f"2026 {ay} Büyüme"]).fillna(0)
    
    # 1. 2026 Desi Hesaplama = 2025 Desi * (1 + 2026 Büyüme)
    df_nihai[f"2026 {ay} Desi"] = df_nihai[f"2025 {ay} Desi"] * (1 + df_nihai[f"2026 {ay} Büyüme"])
    
    # 2. 2026 Eskalasyon Oranı = Global Gelen Revizyonlar
    df_nihai[f"2026 {ay} Esk."] = (global_enflasyon + global_yakit_etkisi) / 100
    
    # 3. 2026 Yeni Fiyat = 2025 Fiyat * (1 + Eskalasyon Oranı)
    df_nihai[f"2026 {ay} Fiyat"] = df_nihai[f"2025 {ay} Fiyat"] * (1 + df_nihai[f"2026 {ay} Esk."])
    
    # 4. 2026 Yeni Tutar = 2026 Desi * 2026 Fiyat
    df_nihai[f"2026 {ay} Tutar"] = df_nihai[f"2026 {ay} Desi"] * df_nihai[f"2026 {ay} Fiyat"]

st.markdown("---")

# --- NİHAİ PROJEKSİYON VE ÖZET METRİKLER ---
st.subheader("📊 2. 2026 Yılı Aylık Bütçe Projeksiyon Sonuçları")

# Toplam bütçe yükünü hızlıca hesaplayıp gösterelim
toplam_2025_tutar = sum(df_nihai[f"2025 {ay} Tutar"].sum() for ay in aylar)
toplam_2026_tutar = sum(df_nihai[f"2026 {ay} Tutar"].sum() for ay in aylar)
fark = toplam_2026_tutar - toplam_2025_tutar

m1, m2, m3 = st.columns(3)
m1.metric("2025 Toplam Gerçekleşen Tutar", value=f"₺{toplam_2025_tutar:,.2f}")
m2.metric("2026 Projeksiyon Toplam Bütçe", value=f"₺{toplam_2026_tutar:,.2f}", delta=f"Önceki Yıla Göre Değişim")
m3.metric("Bütçe Üzerindeki Toplam Artış Yükü", value=f"₺{fark:,.2f}")

# Hesaplanmış tam listeyi okuma modunda gösteriyoruz
st.dataframe(df_nihai, use_container_width=True)