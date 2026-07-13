import streamlit as st
import pandas as pd
import numpy as np
import io
from datetime import date, datetime

# ============================================================
# SUPABASE IMPORT
# ============================================================

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
# SÜTUN TANIMLARI
# ============================================================

aylar = [
    "Ocak",
    "Şubat",
    "Mart",
    "Nisan",
    "Mayıs",
    "Haziran",
    "Temmuz",
    "Ağustos",
    "Eylül",
    "Ekim",
    "Kasım",
    "Aralık"
]

ana_kolonlar = [
    "Uniq ID",
    "Yıl",
    "Teslimat Tipi",
    "Atf Tipi",
    "Çıkış İl Adı",
    "Çıkış Şube Adı",
    "Varış İl Adı",
    "Varış Şube Adı",
    "İlk Okutma Şubesi",
    "Müşteri Kodu",
    "Müşteri Adı",
    "Müşteri Temsilcisi",
    "Sap Kodu",
    "Durum",
    "Kayıt Tarihi",
    "Müşteri Grubu"
]

parametre_kolonlari = [
    "Yakıt Değişim Yüzdesi (%)",
    "Yakıt Anlık Değişim Oranı (%)",
    "Yakıt Değişim Periyodu (Ay)",
    "Enf. Değişim Yüzdesi (%)",
    "Enf. Değişim Periyodu (Ay)",
    "Esk. Baz Yakıt Fiyatı",
    "Esk. Yakıt Başlangıç Tarihi",
    "Esk. Enf. Başlangıç Tarihi"
]

kolonlar_2025_desi = [
    f"2025 {ay} Desi" for ay in aylar
]

kolonlar_2025_tutar = [
    f"2025 {ay} Tutar" for ay in aylar
]

kolonlar_2025_fiyat = [
    f"2025 {ay} Fiyat" for ay in aylar
]

kolonlar_2026_buyume = [
    f"2026 {ay} Büyüme" for ay in aylar
]

kolonlar_2026_esk = [
    f"2026 {ay} Esk." for ay in aylar
]

kolonlar_2026_desi = [
    f"2026 {ay} Desi" for ay in aylar
]

kolonlar_2026_tutar = [
    f"2026 {ay} Tutar" for ay in aylar
]

kolonlar_2026_fiyat = [
    f"2026 {ay} Fiyat" for ay in aylar
]

tum_kolonlar = (
    ana_kolonlar
    + parametre_kolonlari
    + kolonlar_2025_desi
    + kolonlar_2025_tutar
    + kolonlar_2025_fiyat
    + kolonlar_2026_buyume
    + kolonlar_2026_esk
    + kolonlar_2026_desi
    + kolonlar_2026_tutar
    + kolonlar_2026_fiyat
)


# ============================================================
# SUPABASE VERİ TİPİ TANIMLARI
# ============================================================

# Supabase tarafında BIGINT veya INTEGER olması gereken sütunlar
BIGINT_KOLONLAR = [
    "Uniq ID",
    "Yıl",
    "Yakıt Değişim Periyodu (Ay)",
    "Enf. Değişim Periyodu (Ay)"
]

# Ondalıklı sayı olması gereken sütunlar
NUMERIC_KOLONLAR = (
    [
        "Yakıt Değişim Yüzdesi (%)",
        "Yakıt Anlık Değişim Oranı (%)",
        "Enf. Değişim Yüzdesi (%)",
        "Esk. Baz Yakıt Fiyatı"
    ]
    + kolonlar_2025_desi
    + kolonlar_2025_tutar
    + kolonlar_2025_fiyat
    + kolonlar_2026_buyume
    + kolonlar_2026_esk
    + kolonlar_2026_desi
    + kolonlar_2026_tutar
    + kolonlar_2026_fiyat
)

TARIH_KOLONLARI = [
    "Kayıt Tarihi",
    "Esk. Yakıt Başlangıç Tarihi",
    "Esk. Enf. Başlangıç Tarihi"
]


# ============================================================
# YARDIMCI FONKSİYONLAR
# ============================================================

def guvenli_sayi(value):
    """
    Excel, CSV veya kullanıcı girişinden gelen değerleri
    güvenli biçimde float tipine çevirir.
    """

    if value is None:
        return 0.0

    try:
        if pd.isna(value):
            return 0.0
    except (TypeError, ValueError):
        pass

    if isinstance(value, (int, float, np.integer, np.floating)):
        try:
            numeric_value = float(value)

            if np.isfinite(numeric_value):
                return numeric_value

            return 0.0

        except (TypeError, ValueError, OverflowError):
            return 0.0

    value = str(value).strip()

    if value.lower() in {
        "",
        "-",
        "nan",
        "none",
        "null",
        "nat"
    }:
        return 0.0

    value = (
        value
        .replace("₺", "")
        .replace("%", "")
        .replace(" ", "")
    )

    # Türkçe sayı biçimi:
    # 1.234,56 -> 1234.56
    if "," in value and "." in value:
        value = value.replace(".", "").replace(",", ".")

    # 56,78 -> 56.78
    elif "," in value:
        value = value.replace(",", ".")

    try:
        numeric_value = float(value)

        if np.isfinite(numeric_value):
            return numeric_value

        return 0.0

    except (TypeError, ValueError, OverflowError):
        return 0.0


def guvenli_tamsayi(value, nullable=True):
    """
    Değeri Supabase BIGINT uyumlu Python int tipine çevirir.

    Örneğin:
    2026.0 -> 2026
    "2026" -> 2026

    Ondalıklı bir değer gelirse en yakın tam sayıya yuvarlar.
    """

    if value is None:
        return None if nullable else 0

    try:
        if pd.isna(value):
            return None if nullable else 0
    except (TypeError, ValueError):
        pass

    if isinstance(value, str):
        cleaned_value = value.strip()

        if cleaned_value.lower() in {
            "",
            "-",
            "nan",
            "none",
            "null",
            "nat"
        }:
            return None if nullable else 0

    numeric_value = guvenli_sayi(value)

    if not np.isfinite(numeric_value):
        return None if nullable else 0

    return int(round(numeric_value))


def bos_deger_mi(value):
    """
    Değerin boş, NaN, NaT veya sonsuz olup olmadığını kontrol eder.
    """

    if value is None:
        return True

    if isinstance(value, (float, np.floating)):
        return not np.isfinite(float(value))

    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def json_uyumlu_deger(value):
    """
    Pandas ve NumPy değerlerini Supabase/PostgREST için
    JSON uyumlu Python tiplerine dönüştürür.
    """

    if bos_deger_mi(value):
        return None

    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")

    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d")

    if isinstance(value, np.integer):
        return int(value)

    if isinstance(value, np.floating):
        numeric_value = float(value)

        if np.isfinite(numeric_value):
            return numeric_value

        return None

    if isinstance(value, np.bool_):
        return bool(value)

    return value


def tarih_duzenle(value):
    """
    Tarih değerlerini YYYY-MM-DD biçimine dönüştürür.
    Geçersiz veya boş değerlerde None döndürür.
    """

    if bos_deger_mi(value):
        return None

    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")

    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d")

    parsed_date = pd.to_datetime(
        value,
        errors="coerce",
        dayfirst=True
    )

    if pd.isna(parsed_date):
        return None

    return parsed_date.strftime("%Y-%m-%d")


def uniq_id_hazirla(dataframe):
    """
    Uniq ID boş olan kayıtlar için yeni tam sayı kimlik üretir.
    Mevcut geçerli kimlikleri korur.
    """

    df = dataframe.copy()

    if "Uniq ID" not in df.columns:
        return df

    converted_ids = []

    for value in df["Uniq ID"]:
        converted_ids.append(
            guvenli_tamsayi(value, nullable=True)
        )

    mevcut_idler = [
        value
        for value in converted_ids
        if value is not None
    ]

    sonraki_id = max(mevcut_idler, default=0) + 1
    kullanilan_idler = set()

    sonuc_idler = []

    for value in converted_ids:

        # Boş ya da tekrarlanan ID için yeni ID oluştur
        if value is None or value in kullanilan_idler:
            while sonraki_id in kullanilan_idler:
                sonraki_id += 1

            value = sonraki_id
            sonraki_id += 1

        kullanilan_idler.add(value)
        sonuc_idler.append(value)

    df["Uniq ID"] = sonuc_idler

    return df


def supabase_verisini_hazirla(dataframe):
    """
    DataFrame'i Supabase şemasına uygun hale getirir.
    """

    df = dataframe.copy()

    # Sütun adlarındaki görünmez veya gereksiz boşlukları temizle
    df.columns = [
        str(column).strip()
        for column in df.columns
    ]

    # Eksik sütunları ekle ve doğru sıralamayı uygula
    df = df.reindex(columns=tum_kolonlar)

    # Tamamen boş satırları kaldır
    df = df.dropna(how="all").reset_index(drop=True)

    # Uniq ID değerlerini düzelt
    df = uniq_id_hazirla(df)

    # BIGINT sütunlarını Python int tipine dönüştür
    for column in BIGINT_KOLONLAR:
        if column in df.columns:
            df[column] = df[column].apply(
                lambda value: guvenli_tamsayi(
                    value,
                    nullable=True
                )
            )

    # Ondalıklı sütunları Python float tipine dönüştür
    for column in NUMERIC_KOLONLAR:
        if column in df.columns:
            df[column] = df[column].apply(
                lambda value: float(guvenli_sayi(value))
            )

    # Tarih sütunlarını standart metin biçimine dönüştür
    for column in TARIH_KOLONLARI:
        if column in df.columns:
            df[column] = df[column].apply(tarih_duzenle)

    # NumPy, Pandas, NaN ve tarih değerlerini JSON uyumlu yap
    records = []

    for row_index, row in df.iterrows():
        record = {}

        for column, value in row.items():
            record[column] = json_uyumlu_deger(value)

        records.append(record)

    return df, records


def records_kontrol_et(records):
    """
    Supabase'e gönderilecek kayıtları temel veri tipi
    sorunlarına karşı kontrol eder.
    """

    errors = []

    for row_index, record in enumerate(records, start=1):

        for column in BIGINT_KOLONLAR:
            if column not in record:
                continue

            value = record[column]

            if value is not None and not isinstance(value, int):
                errors.append(
                    f"Satır {row_index}, sütun '{column}': "
                    f"BIGINT beklenirken {value!r} gönderiliyor."
                )

        for column in NUMERIC_KOLONLAR:
            if column not in record:
                continue

            value = record[column]

            if value is not None and not isinstance(
                value,
                (int, float)
            ):
                errors.append(
                    f"Satır {row_index}, sütun '{column}': "
                    f"sayısal değer beklenirken {value!r} gönderiliyor."
                )

    return errors


# ============================================================
# SESSION STATE
# ============================================================

if "ana_veri" not in st.session_state:
    st.session_state.ana_veri = pd.DataFrame(
        columns=tum_kolonlar
    )


# ============================================================
# SUPABASE AYARLARI
# ============================================================

st.sidebar.header("🔐 Supabase Bağlantısı")

url = st.sidebar.text_input(
    "Supabase URL",
    value="https://your-project.supabase.co",
    type="password"
)

key = st.sidebar.text_input(
    "Supabase API Key",
    value="your-anon-key",
    type="password"
)


def get_supabase_client():
    """
    Geçerli bağlantı bilgileri varsa Supabase istemcisi döndürür.
    """

    if not SUPABASE_AVAILABLE:
        return None

    if not url or url == "https://your-project.supabase.co":
        return None

    if not key or key == "your-anon-key":
        return None

    try:
        return create_client(url, key)
    except Exception:
        return None


# ============================================================
# ARAYÜZ SEKMELERİ
# ============================================================

sekme1, sekme2 = st.tabs(
    [
        "🚚 Çarşaf Liste & Bütçe",
        "📅 Çalışma Günleri Takvimi"
    ]
)


# ============================================================
# SEKME 1
# ============================================================

with sekme1:

    st.title("🚚 Operasyonel Bütçe Simülatörü")

    st.markdown(
        """
        Verileri lokalden yükleyebilir, Excel olarak indirebilir
        veya Supabase bulut veritabanına senkronize edebilirsiniz.
        """
    )

    # --------------------------------------------------------
    # LOKAL VERİ YÖNETİMİ
    # --------------------------------------------------------

    st.sidebar.markdown("---")
    st.sidebar.header("📁 Lokal Veri Yönetimi")

    yuklenen_dosya = st.sidebar.file_uploader(
        "Excel / CSV Yükle",
        type=["xlsx", "xls", "csv"]
    )

    c1, c2 = st.sidebar.columns(2)

    if c1.button("📥 Veriyi Ekle"):

        if yuklenen_dosya is None:
            st.sidebar.warning(
                "Önce bir Excel veya CSV dosyası seçin."
            )

        else:
            try:
                if yuklenen_dosya.name.lower().endswith(".csv"):
                    yeni_df = pd.read_csv(yuklenen_dosya)
                else:
                    yeni_df = pd.read_excel(yuklenen_dosya)

                yeni_df.columns = [
                    str(column).strip()
                    for column in yeni_df.columns
                ]

                yeni_df = yeni_df.reindex(
                    columns=tum_kolonlar
                )

                st.session_state.ana_veri = pd.concat(
                    [
                        st.session_state.ana_veri,
                        yeni_df
                    ],
                    ignore_index=True
                )

                st.sidebar.success(
                    f"{len(yeni_df)} satır hafızaya eklendi."
                )

            except Exception as error:
                st.sidebar.error(
                    f"Dosya okuma hatası: {error}"
                )

    if c2.button("🗑️ Hafızayı Temizle"):

        st.session_state.ana_veri = pd.DataFrame(
            columns=tum_kolonlar
        )

        st.sidebar.success("Hafıza sıfırlandı.")

    # --------------------------------------------------------
    # SUPABASE'DEN VERİ ÇEKME
    # --------------------------------------------------------

    st.sidebar.markdown("---")
    st.sidebar.header("🗄️ Bulut Senkronizasyonu")

    if st.sidebar.button(
        "🔄 Buluttan Son Veriyi Çek"
    ):
        client = get_supabase_client()

        if client is None:
            st.sidebar.error(
                "Geçerli Supabase URL ve API Key girin."
            )

        else:
            try:
                response = (
                    client
                    .table("butce_tablosu")
                    .select("*")
                    .execute()
                )

                if response.data:
                    gelen_df = pd.DataFrame(response.data)

                    gelen_df.columns = [
                        str(column).strip()
                        for column in gelen_df.columns
                    ]

                    st.session_state.ana_veri = (
                        gelen_df
                        .reindex(columns=tum_kolonlar)
                    )

                    st.sidebar.success(
                        "Veriler Supabase'den yüklendi."
                    )

                    st.rerun()

                else:
                    st.sidebar.warning(
                        "Veritabanında kayıt bulunamadı."
                    )

            except Exception as error:
                st.sidebar.error(
                    f"Buluttan çekme hatası: {error}"
                )

    # --------------------------------------------------------
    # GLOBAL BÜTÇE PARAMETRESİ
    # --------------------------------------------------------

    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ Global Bütçe Revizyonu")

    global_enflasyon = st.sidebar.slider(
        "2026 Global Eskalasyon (%)",
        min_value=0,
        max_value=100,
        value=0,
        step=1
    )

    # --------------------------------------------------------
    # VERİ EDİTÖRÜ
    # --------------------------------------------------------

    st.subheader("📝 1. Çarşaf Liste Veri Girişi")

    duzenlenen_df = st.data_editor(
        st.session_state.ana_veri,
        num_rows="dynamic",
        use_container_width=True,
        height=250,
        key="butce_veri_editoru"
    )

    if not duzenlenen_df.empty:

        df_nihai = duzenlenen_df.copy()

        df_nihai.columns = [
            str(column).strip()
            for column in df_nihai.columns
        ]

        df_nihai = df_nihai.reindex(
            columns=tum_kolonlar
        )

        # ----------------------------------------------------
        # 2025 HESAPLAMALARI
        # ----------------------------------------------------

        for ay in aylar:

            desi_column = f"2025 {ay} Desi"
            fiyat_column = f"2025 {ay} Fiyat"
            tutar_column = f"2025 {ay} Tutar"

            df_nihai[desi_column] = (
                df_nihai[desi_column]
                .apply(guvenli_sayi)
            )

            df_nihai[fiyat_column] = (
                df_nihai[fiyat_column]
                .apply(guvenli_sayi)
            )

            df_nihai[tutar_column] = (
                df_nihai[desi_column]
                * df_nihai[fiyat_column]
            )

        # 2026 başlangıç fiyatı 2025 Aralık fiyatıdır
        onceki_fiyat = (
            df_nihai["2025 Aralık Fiyat"]
            .apply(guvenli_sayi)
        )

        # ----------------------------------------------------
        # 2026 HESAPLAMALARI
        # ----------------------------------------------------

        for ay in aylar:

            buyume_column = f"2026 {ay} Büyüme"
            esk_column = f"2026 {ay} Esk."
            desi_column = f"2026 {ay} Desi"
            fiyat_column = f"2026 {ay} Fiyat"
            tutar_column = f"2026 {ay} Tutar"

            df_nihai[buyume_column] = (
                df_nihai[buyume_column]
                .apply(guvenli_sayi)
            )

            df_nihai[esk_column] = (
                df_nihai[esk_column]
                .apply(guvenli_sayi)
            )

            aktif_eskalasyon = np.where(
                df_nihai[esk_column] == 0,
                float(global_enflasyon),
                df_nihai[esk_column]
            )

            df_nihai[desi_column] = (
                df_nihai[f"2025 {ay} Desi"]
                * (
                    1
                    + (
                        df_nihai[buyume_column]
                        / 100
                    )
                )
            )

            df_nihai[fiyat_column] = (
                onceki_fiyat
                * (
                    1
                    + (
                        aktif_eskalasyon
                        / 100
                    )
                )
            )

            df_nihai[tutar_column] = (
                df_nihai[desi_column]
                * df_nihai[fiyat_column]
            )

            onceki_fiyat = df_nihai[fiyat_column]

        # Hesaplanmış veriyi hafızada da sakla
        st.session_state.ana_veri = df_nihai.copy()

        # ----------------------------------------------------
        # SONUÇLAR
        # ----------------------------------------------------

        st.markdown("---")
        st.subheader(
            "📊 2. Projeksiyon Sonuçları ve Çıktı Yönetimi"
        )

        toplam_2025_tutar = sum(
            df_nihai[f"2025 {ay} Tutar"].sum()
            for ay in aylar
        )

        toplam_2026_tutar = sum(
            df_nihai[f"2026 {ay} Tutar"].sum()
            for ay in aylar
        )

        fark = (
            toplam_2026_tutar
            - toplam_2025_tutar
        )

        m1, m2, m3 = st.columns(3)

        m1.metric(
            "2025 Toplam Gerçekleşen",
            value=f"₺{toplam_2025_tutar:,.2f}"
        )

        m2.metric(
            "2026 Projeksiyon Toplamı",
            value=f"₺{toplam_2026_tutar:,.2f}",
            delta="Artış Trendi"
        )

        m3.metric(
            "Bütçeye Gelen Ek Yük",
            value=f"₺{fark:,.2f}"
        )

        # ----------------------------------------------------
        # İNDİRME VE SUPABASE BUTONLARI
        # ----------------------------------------------------

        col_down1, col_down2 = st.columns(2)

        with col_down1:

            output_excel = io.BytesIO()

            with pd.ExcelWriter(
                output_excel,
                engine="openpyxl"
            ) as writer:

                df_nihai.to_excel(
                    writer,
                    index=False,
                    sheet_name="Bütçe Raporu"
                )

            st.download_button(
                label="📥 Mevcut Senaryoyu Excel Olarak İndir",
                data=output_excel.getvalue(),
                file_name=(
                    "horoz_lojistik_"
                    "simulasyon_sonuc.xlsx"
                ),
                mime=(
                    "application/vnd.openxmlformats-"
                    "officedocument.spreadsheetml.sheet"
                ),
                use_container_width=True
            )

        with col_down2:

            buluta_gonder = st.button(
                "🚀 Hesaplanan Veriyi Supabase'e Gönder",
                use_container_width=True
            )

            if buluta_gonder:

                client = get_supabase_client()

                if client is None:

                    if not SUPABASE_AVAILABLE:
                        st.error(
                            "Supabase kütüphanesi kurulu değil. "
                            "`pip install supabase` komutunu çalıştırın."
                        )
                    else:
                        st.error(
                            "Sol menüden geçerli Supabase URL "
                            "ve API Key girin."
                        )

                else:
                    try:
                        with st.spinner(
                            "Veriler kontrol ediliyor ve hazırlanıyor..."
                        ):

                            (
                                df_bulut,
                                records
                            ) = supabase_verisini_hazirla(
                                df_nihai
                            )

                            validation_errors = (
                                records_kontrol_et(records)
                            )

                            if validation_errors:
                                st.error(
                                    "Veri tipi kontrolünde hata bulundu."
                                )

                                for error in validation_errors[:20]:
                                    st.code(error)

                                st.stop()

                            if not records:
                                st.warning(
                                    "Supabase'e gönderilecek "
                                    "kayıt bulunamadı."
                                )
                                st.stop()

                        with st.spinner(
                            "Eski kayıtlar temizleniyor..."
                        ):

                            # ÖNEMLİ:
                            # "YOK" metni yerine geçerli bir bigint
                            # karşılaştırması kullanıyoruz.
                            #
                            # Bu değer pratikte hiçbir Uniq ID ile
                            # eşleşmeyeceği için tüm normal kayıtlar silinir.
                            silme_sentinel_id = -9223372036854775808

                            (
                                client
                                .table("butce_tablosu")
                                .delete()
                                .neq(
                                    "Uniq ID",
                                    silme_sentinel_id
                                )
                                .execute()
                            )

                        with st.spinner(
                            "Veriler Supabase'e aktarılıyor..."
                        ):

                            chunk_size = 500

                            for start_index in range(
                                0,
                                len(records),
                                chunk_size
                            ):
                                chunk = records[
                                    start_index:
                                    start_index + chunk_size
                                ]

                                (
                                    client
                                    .table("butce_tablosu")
                                    .insert(chunk)
                                    .execute()
                                )

                        st.success(
                            f"🎉 {len(records)} kayıt başarıyla "
                            "Supabase'e yazıldı."
                        )

                    except Exception as error:

                        error_text = str(error)

                        st.error(
                            f"Buluta gönderme hatası: {error_text}"
                        )

                        if (
                            "invalid input syntax for type bigint"
                            in error_text.lower()
                        ):
                            st.warning(
                                """
                                Supabase tablosunda ondalıklı veri içeren
                                bir sütun BIGINT olarak tanımlanmış.

                                Fiyat, tutar, desi, büyüme ve eskalasyon
                                sütunlarının Supabase veri tipi
                                NUMERIC veya DOUBLE PRECISION olmalıdır.
                                """
                            )

        # ----------------------------------------------------
        # SONUÇ TABLOSU
        # ----------------------------------------------------

        st.dataframe(
            df_nihai,
            use_container_width=True
        )

    else:
        st.info(
            "👆 Başlamak için veri yükleyin "
            "veya manuel satır ekleyin."
        )


# ============================================================
# SEKME 2
# ============================================================

with sekme2:

    st.title("📅 Operasyonel Çalışma Günleri")

    takvim_verisi = {
        "Ay": aylar,
        "2025 Çalışma Günü": [
            22,
            20,
            21,
            22,
            21,
            20,
            23,
            21,
            22,
            23,
            20,
            22
        ],
        "2026 Çalışma Günü": [
            21,
            20,
            20,
            21,
            17,
            22,
            22,
            21,
            22,
            21,
            21,
            23
        ],
        "Resmi Tatiller / Notlar": [
            "-",
            "-",
            "Ramazan Bayramı",
            "23 Nisan",
            "Kurban Bayramı",
            "-",
            "-",
            "30 Ağustos",
            "-",
            "29 Ekim",
            "-",
            "-"
        ]
    }

    st.data_editor(
        pd.DataFrame(takvim_verisi),
        use_container_width=True,
        hide_index=True,
        key="calisma_gunleri_editoru"
    )
