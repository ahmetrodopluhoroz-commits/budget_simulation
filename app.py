import gc
import gzip
import io
import math
import os
import tempfile
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

import numpy as np
import pandas as pd
import streamlit as st

try:
    from supabase import create_client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False


# ============================================================
# SAYFA AYARLARI
# ============================================================
st.set_page_config(
    page_title="Gelişmiş Bütçe Simülatörü",
    page_icon="🚚",
    layout="wide",
)


# ============================================================
# SABİTLER
# ============================================================
aylar = [
    "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
]

ana_kolonlar = [
    "Uniq ID", "Yıl", "Teslimat Tipi", "Atf Tipi", "Çıkış İl Adı",
    "Çıkış Şube Adı", "Varış İl Adı", "Varış Şube Adı",
    "İlk Okutma Şubesi", "Müşteri Kodu", "Müşteri Adı",
    "Müşteri Temsilcisi", "Sap Kodu", "Durum", "Kayıt Tarihi",
    "Müşteri Grubu",
]

parametre_kolonlari = [
    "Yakıt Değişim Yüzdesi (%)",
    "Yakıt Anlık Değişim Oranı (%)",
    "Yakıt Değişim Periyodu (Ay)",
    "Enf. Değişim Yüzdesi (%)",
    "Enf. Değişim Periyodu (Ay)",
    "Esk. Baz Yakıt Fiyatı",
    "Esk. Yakıt Başlangıç Tarihi",
    "Esk. Enf. Başlangıç Tarihi",
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

BIGINT_KOLONLAR = [
    "Uniq ID",
    "Yıl",
    "Yakıt Değişim Periyodu (Ay)",
    "Enf. Değişim Periyodu (Ay)",
]

NUMERIC_KOLONLAR = (
    [
        "Yakıt Değişim Yüzdesi (%)",
        "Yakıt Anlık Değişim Oranı (%)",
        "Enf. Değişim Yüzdesi (%)",
        "Esk. Baz Yakıt Fiyatı",
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
    "Esk. Enf. Başlangıç Tarihi",
]

TEXT_KOLONLAR = [
    c for c in tum_kolonlar
    if c not in BIGINT_KOLONLAR
    and c not in NUMERIC_KOLONLAR
    and c not in TARIH_KOLONLARI
]

SUPABASE_OKUMA_SAYFA_BOYUTU = 1000
SUPABASE_YAZMA_PAKET_BOYUTU = 500
EDITOR_SAYFA_SECENEKLERI = [100, 250, 500, 1000]


# ============================================================
# SESSION STATE
# ============================================================
def init_state():
    defaults = {
        "oturum_acik": False,
        "ana_veri": pd.DataFrame(columns=tum_kolonlar),
        "editor_key": 0,
        "hesaplandi": False,
        "aktif_sayfa_no": 1,
        "uygulama_oturum_id": uuid4().hex,
        "indirilecek_dosya": None,
        "indirilecek_dosya_adi": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_state()


# ============================================================
# GİRİŞ
# ============================================================
def secret_get(name: str, default: str = "") -> str:
    try:
        return str(st.secrets.get(name, default))
    except Exception:
        return os.getenv(name, default)


# Giriş bilgileri önceki uygulamadaki haliyle sabit bırakıldı.
APP_USERNAME = "rasg"
APP_PASSWORD = "Hrz1234"

if not st.session_state.oturum_acik:
    st.markdown("<br><br>", unsafe_allow_html=True)
    _, login_col, _ = st.columns([1, 1, 1])
    with login_col:
        st.title("🔒 Bütçe Sistemine Giriş")
        st.markdown("Lütfen devam etmek için yetkili bilgilerinizi girin.")
        kullanici_adi = st.text_input("Kullanıcı Adı")
        sifre = st.text_input("Şifre", type="password")

        if st.button("Giriş Yap", type="primary", use_container_width=True):
            if kullanici_adi == APP_USERNAME and sifre == APP_PASSWORD:
                st.session_state.oturum_acik = True
                st.success("Giriş Başarılı! Sistem Yükleniyor...")
                st.rerun()
            else:
                st.error("Hatalı kullanıcı adı veya şifre girdiniz!")
    st.stop()


# ============================================================
# SUPABASE
# ============================================================
@st.cache_resource(show_spinner=False)
def get_supabase_client():
    if not SUPABASE_AVAILABLE:
        return None

    url = secret_get("SUPABASE_URL")
    key = secret_get("SUPABASE_KEY")
    if not url or not key:
        return None

    return create_client(url, key)


# ============================================================
# VERİ DÖNÜŞÜM FONKSİYONLARI
# ============================================================
def kolonlari_duzenle(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [str(c).strip() for c in df.columns]
    return df


def sayisal_seriye_cevir(series: pd.Series) -> pd.Series:
    """Türkçe/İngilizce sayı biçimlerini vektörel olarak float64'e çevirir."""
    if pd.api.types.is_numeric_dtype(series):
        result = pd.to_numeric(series, errors="coerce")
        return result.replace([np.inf, -np.inf], np.nan).fillna(0.0).astype("float64")

    text = series.astype("string").str.strip()
    text = (
        text.str.replace("₺", "", regex=False)
        .str.replace("%", "", regex=False)
        .str.replace(" ", "", regex=False)
    )

    bos_mask = text.str.lower().isin(["", "-", "nan", "none", "null", "nat"])
    text = text.mask(bos_mask)

    hem_nokta_hem_virgul = (
        text.str.contains(".", regex=False, na=False)
        & text.str.contains(",", regex=False, na=False)
    )
    sadece_virgul = (
        text.str.contains(",", regex=False, na=False)
        & ~text.str.contains(".", regex=False, na=False)
    )

    text.loc[hem_nokta_hem_virgul] = (
        text.loc[hem_nokta_hem_virgul]
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    text.loc[sadece_virgul] = text.loc[sadece_virgul].str.replace(",", ".", regex=False)

    result = pd.to_numeric(text, errors="coerce")
    return result.replace([np.inf, -np.inf], np.nan).fillna(0.0).astype("float64")


def tamsayi_seriye_cevir(series: pd.Series, nullable: bool = True) -> pd.Series:
    numeric = sayisal_seriye_cevir(series).round()
    if nullable:
        # Boş kaynak değerleri korumak için yeniden boşluk maskesi oluşturulur.
        source_empty = series.isna() | series.astype("string").str.strip().str.lower().isin(
            ["", "-", "nan", "none", "null", "nat"]
        )
        numeric = numeric.mask(source_empty)
        return numeric.astype("Int64")
    return numeric.fillna(0).astype("int64")


def tarih_seriye_cevir(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, errors="coerce", dayfirst=True)
    return parsed.dt.strftime("%Y-%m-%d")


def uniq_idleri_duzenle(df: pd.DataFrame) -> None:
    """Boş ve yinelenen Uniq ID değerlerini tek geçişte düzeltir."""
    if "Uniq ID" not in df.columns:
        return

    ids = tamsayi_seriye_cevir(df["Uniq ID"], nullable=True)
    valid_ids = ids.dropna().astype("int64")
    next_id = int(valid_ids.max()) + 1 if not valid_ids.empty else 1
    used = set()
    result = np.empty(len(df), dtype=np.int64)

    for pos, value in enumerate(ids.array):
        temiz = None if pd.isna(value) else int(value)
        if temiz is None or temiz in used:
            while next_id in used:
                next_id += 1
            temiz = next_id
            next_id += 1
        used.add(temiz)
        result[pos] = temiz

    df["Uniq ID"] = result


def butce_hesapla_inplace(df: pd.DataFrame, global_enflasyon: float) -> None:
    """Tüm hesaplamaları vektörel olarak aynı DataFrame üzerinde yapar."""
    if df.empty:
        return

    for ay in aylar:
        desi_2025 = f"2025 {ay} Desi"
        fiyat_2025 = f"2025 {ay} Fiyat"
        tutar_2025 = f"2025 {ay} Tutar"

        df[desi_2025] = sayisal_seriye_cevir(df[desi_2025])
        df[fiyat_2025] = sayisal_seriye_cevir(df[fiyat_2025])
        df[tutar_2025] = df[desi_2025].to_numpy() * df[fiyat_2025].to_numpy()

    onceki_fiyat = df["2025 Aralık Fiyat"].to_numpy(copy=True)

    for ay in aylar:
        buyume = f"2026 {ay} Büyüme"
        esk = f"2026 {ay} Esk."
        desi_2026 = f"2026 {ay} Desi"
        fiyat_2026 = f"2026 {ay} Fiyat"
        tutar_2026 = f"2026 {ay} Tutar"

        df[buyume] = sayisal_seriye_cevir(df[buyume])
        df[esk] = sayisal_seriye_cevir(df[esk])

        buyume_arr = df[buyume].to_numpy()
        esk_arr = df[esk].to_numpy()
        aktif_esk = np.where(esk_arr == 0.0, float(global_enflasyon), esk_arr)

        desi_arr = df[f"2025 {ay} Desi"].to_numpy() * (1.0 + buyume_arr / 100.0)
        fiyat_arr = onceki_fiyat * (1.0 + aktif_esk / 100.0)

        df[desi_2026] = desi_arr
        df[fiyat_2026] = fiyat_arr
        df[tutar_2026] = desi_arr * fiyat_arr
        onceki_fiyat = fiyat_arr


def supabase_chunk_hazirla(
    df: pd.DataFrame,
    start: int,
    stop: int,
    revizyon_id: str,
) -> list[dict]:
    """Yalnızca gönderilecek küçük parçayı kopyalar ve JSON uyumlu hale getirir."""
    chunk = df.iloc[start:stop].reindex(columns=tum_kolonlar).copy()

    for col in BIGINT_KOLONLAR:
        chunk[col] = tamsayi_seriye_cevir(chunk[col], nullable=True)
        chunk[col] = chunk[col].map(lambda x: None if pd.isna(x) else int(x))

    for col in NUMERIC_KOLONLAR:
        chunk[col] = sayisal_seriye_cevir(chunk[col])

    for col in TARIH_KOLONLARI:
        chunk[col] = tarih_seriye_cevir(chunk[col])

    chunk.replace([np.inf, -np.inf], np.nan, inplace=True)
    chunk["revizyon_id"] = revizyon_id
    chunk = chunk.astype(object).where(pd.notna(chunk), None)

    return chunk.to_dict(orient="records")


def supabase_tum_revizyonu_getir(
    client,
    revizyon_id: str,
    beklenen_satir: int | None = None,
) -> pd.DataFrame:
    """Supabase'in 1000 satırlık varsayılan sınırını range() ile aşar."""
    parcalar: list[pd.DataFrame] = []
    baslangic = 0
    progress = st.progress(0, text="Veri indiriliyor...")

    while True:
        bitis = baslangic + SUPABASE_OKUMA_SAYFA_BOYUTU - 1
        response = (
            client.table("butce_tablosu")
            .select("*")
            .eq("revizyon_id", revizyon_id)
            .order("Uniq ID")
            .range(baslangic, bitis)
            .execute()
        )
        rows = response.data or []
        if not rows:
            break

        parcalar.append(pd.DataFrame.from_records(rows))
        baslangic += len(rows)

        if beklenen_satir and beklenen_satir > 0:
            oran = min(baslangic / beklenen_satir, 1.0)
        else:
            # Toplam bilinmiyorsa her paket geldiğinde hareketli geri bildirim ver.
            oran = min(0.95, 0.05 + (len(parcalar) % 18) * 0.05)
        progress.progress(oran, text=f"{baslangic:,} satır indirildi...")

        if len(rows) < SUPABASE_OKUMA_SAYFA_BOYUTU:
            break

    progress.progress(1.0, text=f"{baslangic:,} satır indirildi.")

    if not parcalar:
        return pd.DataFrame(columns=tum_kolonlar)

    result = pd.concat(parcalar, ignore_index=True, copy=False)
    del parcalar
    gc.collect()

    result = kolonlari_duzenle(result)
    return result.reindex(columns=tum_kolonlar)


def gecici_dosya_yolu(suffix: str) -> Path:
    folder = Path(tempfile.gettempdir()) / f"butce_{st.session_state.uygulama_oturum_id}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"butce_{datetime.now():%Y%m%d_%H%M%S}{suffix}"


# ============================================================
# NAVİGASYON
# ============================================================
st.sidebar.title("🚚 Bütçe Sistemi")
sayfa = st.sidebar.radio(
    "Sayfa",
    ["Çarşaf Liste & Bütçe", "Çalışma Günleri", "Bulut Revizyon Yönetimi"],
    key="aktif_uygulama_sayfasi",
)

if st.sidebar.button("Çıkış Yap"):
    st.session_state.oturum_acik = False
    st.rerun()


# ============================================================
# 1. SAYFA: ÇARŞAF LİSTE & BÜTÇE
# ============================================================
if sayfa == "Çarşaf Liste & Bütçe":
    st.title("🚚 Operasyonel Bütçe Simülatörü")
    st.caption(
        "Büyük veri modu: Tüm veri hafızada tutulur; ekranda yalnızca seçilen sayfa gösterilir."
    )

    # --------------------------------------------------------
    # DOSYA YÜKLEME
    # --------------------------------------------------------
    st.sidebar.markdown("---")
    st.sidebar.header("📁 Lokal Veri Yönetimi")
    yuklenen_dosya = st.sidebar.file_uploader(
        "Excel / CSV Yükle", type=["xlsx", "xls", "csv"]
    )
    yukleme_tipi = st.sidebar.radio(
        "Yükleme Amacı",
        ["Yeni Satırlar Ekle", "Düşeyara (VLOOKUP) ile Güncelle"],
    )

    col_load, col_clear = st.sidebar.columns(2)

    if col_load.button("📥 Veriyi İşle", use_container_width=True):
        if yuklenen_dosya is None:
            st.sidebar.warning("Önce bir dosya seçin.")
        else:
            try:
                with st.spinner("Dosya okunuyor..."):
                    if yuklenen_dosya.name.lower().endswith(".csv"):
                        yeni_df = pd.read_csv(yuklenen_dosya, low_memory=False)
                    else:
                        yeni_df = pd.read_excel(yuklenen_dosya)
                    kolonlari_duzenle(yeni_df)

                if yukleme_tipi == "Düşeyara (VLOOKUP) ile Güncelle":
                    if "Uniq ID" not in yeni_df.columns:
                        st.error("Güncelleme dosyasında 'Uniq ID' sütunu bulunmalı.")
                    elif st.session_state.ana_veri.empty:
                        st.error("Güncelleme için önce ana veriyi yükleyin.")
                    else:
                        with st.spinner("Eşleşen kayıtlar güncelleniyor..."):
                            ana = st.session_state.ana_veri
                            ana_ids = tamsayi_seriye_cevir(ana["Uniq ID"], nullable=True)
                            yeni_ids = tamsayi_seriye_cevir(yeni_df["Uniq ID"], nullable=True)

                            guncellenecek = [
                                c for c in yeni_df.columns
                                if c in ana.columns and c != "Uniq ID"
                            ]

                            # Aynı Uniq ID birden fazla geldiyse son satırı esas al.
                            yeni_gecerli = pd.DataFrame({"__id": yeni_ids})
                            for col in guncellenecek:
                                yeni_gecerli[col] = yeni_df[col].to_numpy()
                            yeni_gecerli = yeni_gecerli.dropna(subset=["__id"]).drop_duplicates(
                                subset=["__id"], keep="last"
                            )

                            for col in guncellenecek:
                                mapping = pd.Series(
                                    yeni_gecerli[col].to_numpy(),
                                    index=yeni_gecerli["__id"],
                                )
                                eslesen_index = ana_ids.map(mapping)
                                mask = eslesen_index.notna()
                                ana.loc[mask, col] = eslesen_index.loc[mask].to_numpy()

                            st.session_state.hesaplandi = False
                            st.session_state.editor_key += 1
                            st.success(
                                f"{len(guncellenecek)} sütun üzerinden güncelleme tamamlandı."
                            )
                else:
                    yeni_df = yeni_df.reindex(columns=tum_kolonlar)
                    if st.session_state.ana_veri.empty:
                        st.session_state.ana_veri = yeni_df.reset_index(drop=True)
                    else:
                        st.session_state.ana_veri = pd.concat(
                            [st.session_state.ana_veri, yeni_df],
                            ignore_index=True,
                            copy=False,
                        )
                    st.session_state.hesaplandi = False
                    st.session_state.editor_key += 1
                    st.success(f"{len(yeni_df):,} satır eklendi.")

                del yeni_df
                gc.collect()
                st.rerun()
            except Exception as exc:
                st.error(f"Dosya işleme hatası: {exc}")

    if col_clear.button("🗑️ Temizle", use_container_width=True):
        st.session_state.ana_veri = pd.DataFrame(columns=tum_kolonlar)
        st.session_state.hesaplandi = False
        st.session_state.editor_key += 1
        st.session_state.indirilecek_dosya = None
        gc.collect()
        st.rerun()

    df = st.session_state.ana_veri

    # --------------------------------------------------------
    # HESAPLAMA
    # --------------------------------------------------------
    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ Hesaplama")
    global_enflasyon = st.sidebar.slider(
        "2026 Global Eskalasyon (%)", 0, 100, 0, step=1
    )

    if st.sidebar.button("🧮 Tüm Veriyi Hesapla", type="primary", use_container_width=True):
        if df.empty:
            st.sidebar.warning("Hesaplanacak veri yok.")
        else:
            try:
                with st.spinner(f"{len(df):,} satır vektörel olarak hesaplanıyor..."):
                    uniq_idleri_duzenle(df)
                    butce_hesapla_inplace(df, global_enflasyon)
                    st.session_state.hesaplandi = True
                    st.session_state.editor_key += 1
                    gc.collect()
                st.success("Hesaplama tamamlandı.")
                st.rerun()
            except Exception as exc:
                st.error(f"Hesaplama hatası: {exc}")

    # --------------------------------------------------------
    # FİLTRE VE SAYFALAMA
    # --------------------------------------------------------
    st.sidebar.markdown("---")
    st.sidebar.header("🔎 Filtre ve Sayfalama")
    filtre_kolonu = st.sidebar.selectbox(
        "Filtre sütunu", ["Filtre yok"] + tum_kolonlar
    )
    filtre_metni = st.sidebar.text_input("Aranan değer")
    sayfa_boyutu = st.sidebar.selectbox(
        "Sayfa başına satır", EDITOR_SAYFA_SECENEKLERI, index=2
    )

    if df.empty:
        st.info("Excel/CSV yükleyin veya buluttan bir versiyon getirin.")
    else:
        if filtre_kolonu != "Filtre yok" and filtre_metni:
            mask = (
                df[filtre_kolonu]
                .astype("string")
                .str.contains(filtre_metni, case=False, na=False, regex=False)
            )
            filtreli_index = df.index[mask]
        else:
            filtreli_index = df.index

        toplam_filtreli = len(filtreli_index)
        toplam_sayfa = max(1, math.ceil(toplam_filtreli / sayfa_boyutu))

        if st.session_state.aktif_sayfa_no > toplam_sayfa:
            st.session_state.aktif_sayfa_no = toplam_sayfa

        sayfa_no = st.sidebar.number_input(
            "Sayfa",
            min_value=1,
            max_value=toplam_sayfa,
            step=1,
            key="aktif_sayfa_no",
        )

        start = (int(sayfa_no) - 1) * sayfa_boyutu
        stop = min(start + sayfa_boyutu, toplam_filtreli)
        sayfa_indexleri = filtreli_index[start:stop]
        sayfa_df = df.loc[sayfa_indexleri].copy()

        st.subheader("📝 Sayfalı Veri Editörü")
        st.info(
            f"Toplam {len(df):,} kayıt; filtre sonucu {toplam_filtreli:,} kayıt. "
            f"Şu an {start + 1 if toplam_filtreli else 0:,}-{stop:,} arası gösteriliyor."
        )

        with st.form("sayfa_editor_form", clear_on_submit=False):
            duzenlenen_sayfa = st.data_editor(
                sayfa_df,
                num_rows="fixed",
                width="stretch",
                height=520,
                key=f"butce_editor_{st.session_state.editor_key}_{sayfa_no}",
            )
            sayfa_kaydet = st.form_submit_button(
                "💾 Bu Sayfadaki Değişiklikleri Hafızaya Kaydet",
                type="primary",
                use_container_width=True,
            )

        if sayfa_kaydet:
            st.session_state.ana_veri.loc[
                duzenlenen_sayfa.index, duzenlenen_sayfa.columns
            ] = duzenlenen_sayfa
            st.session_state.hesaplandi = False
            st.success("Sayfa değişiklikleri kaydedildi. Sonuçlar için yeniden hesaplayın.")

        del sayfa_df

        # ----------------------------------------------------
        # ÖZET
        # ----------------------------------------------------
        st.markdown("---")
        st.subheader("📊 Projeksiyon Özeti")

        if st.session_state.hesaplandi:
            toplam_2025 = float(df[kolonlar_2025_tutar].sum(numeric_only=True).sum())
            toplam_2026 = float(df[kolonlar_2026_tutar].sum(numeric_only=True).sum())
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Satır Sayısı", f"{len(df):,}")
            m2.metric("2025 Toplam", f"₺{toplam_2025:,.2f}")
            m3.metric("2026 Toplam", f"₺{toplam_2026:,.2f}")
            m4.metric("Ek Yük", f"₺{toplam_2026 - toplam_2025:,.2f}")
        else:
            st.warning("Veriler değişti. Güncel sonuçlar için 'Tüm Veriyi Hesapla'ya basın.")

        # ----------------------------------------------------
        # DOSYA ÇIKTISI: OTOMATİK EXCEL YOK
        # ----------------------------------------------------
        st.markdown("---")
        st.subheader("📦 Dosya Çıktısı")
        st.caption(
            "100.000+ satırda Excel dosyasını her ekran yenilemesinde üretmek belleği tüketir. "
            "Bu sürüm çıktıyı yalnızca düğmeye basıldığında sıkıştırılmış CSV olarak hazırlar."
        )

        if st.button("📦 Sıkıştırılmış CSV Hazırla", use_container_width=True):
            try:
                path = gecici_dosya_yolu(".csv.gz")
                with st.spinner("CSV sıkıştırılıyor..."):
                    df.to_csv(path, index=False, compression="gzip", encoding="utf-8-sig")
                st.session_state.indirilecek_dosya = str(path)
                st.session_state.indirilecek_dosya_adi = path.name
                st.success("Dosya hazırlandı.")
            except Exception as exc:
                st.error(f"Dosya oluşturma hatası: {exc}")

        download_path = st.session_state.indirilecek_dosya
        if download_path and Path(download_path).exists():
            with open(download_path, "rb") as file_obj:
                st.download_button(
                    "⬇️ Hazırlanan CSV.GZ Dosyasını İndir",
                    data=file_obj,
                    file_name=st.session_state.indirilecek_dosya_adi,
                    mime="application/gzip",
                    use_container_width=True,
                )

        # ----------------------------------------------------
        # SUPABASE KAYIT
        # ----------------------------------------------------
        st.markdown("---")
        st.subheader("☁️ Yeni Revizyon Olarak Kaydet")

        with st.form("revizyon_kayit_form"):
            kisi = st.text_input("Revizyonu Yapan Kişi")
            not_ = st.text_input("Revizyon Notu")
            kaydet = st.form_submit_button(
                "💾 Senaryoyu Supabase'e Kaydet",
                type="primary",
                use_container_width=True,
            )

        if kaydet:
            client = get_supabase_client()
            if client is None:
                st.error("Supabase bağlantısı kurulamadı. Secrets ayarlarını kontrol edin.")
            elif not kisi.strip():
                st.error("Revizyonu yapan kişi boş bırakılamaz.")
            elif not st.session_state.hesaplandi:
                st.error("Kaydetmeden önce 'Tüm Veriyi Hesapla' düğmesine basın.")
            else:
                rev_id = f"REV-{datetime.now():%Y%m%d-%H%M%S-%f}"
                log_yeni_sema = True
                progress = st.progress(0, text="Revizyon kaydı oluşturuluyor...")

                try:
                    uniq_idleri_duzenle(df)
                    if df["Uniq ID"].duplicated().any():
                        raise ValueError("Uniq ID değerleri revizyon içinde benzersiz değil.")

                    # Yeni şema varsa durum/satır sayısı kaydedilir; eski şemada geriye uyumlu çalışır.
                    try:
                        client.table("revizyon_log").insert({
                            "revizyon_id": rev_id,
                            "olusturan_kisi": kisi.strip(),
                            "revizyon_notu": not_.strip(),
                            "durum": "yukleniyor",
                            "satir_sayisi": int(len(df)),
                        }).execute()
                    except Exception:
                        log_yeni_sema = False
                        client.table("revizyon_log").insert({
                            "revizyon_id": rev_id,
                            "olusturan_kisi": kisi.strip(),
                            "revizyon_notu": not_.strip(),
                        }).execute()

                    total = len(df)
                    for start_pos in range(0, total, SUPABASE_YAZMA_PAKET_BOYUTU):
                        stop_pos = min(start_pos + SUPABASE_YAZMA_PAKET_BOYUTU, total)
                        records = supabase_chunk_hazirla(df, start_pos, stop_pos, rev_id)
                        client.table("butce_tablosu").insert(records).execute()
                        del records

                        progress.progress(
                            stop_pos / total,
                            text=f"{stop_pos:,}/{total:,} satır yüklendi...",
                        )

                    if log_yeni_sema:
                        client.table("revizyon_log").update({
                            "durum": "tamamlandi",
                            "satir_sayisi": int(total),
                        }).eq("revizyon_id", rev_id).execute()

                    progress.progress(1.0, text="Yükleme tamamlandı.")
                    st.success(
                        f"{total:,} satır '{rev_id}' revizyonuyla başarıyla kaydedildi."
                    )
                    gc.collect()

                except Exception as exc:
                    # Kısmi yüklemeyi temizle. revizyon_id indeksli olduğu için hızlı çalışır.
                    try:
                        client.table("butce_tablosu").delete().eq(
                            "revizyon_id", rev_id
                        ).execute()
                        client.table("revizyon_log").delete().eq(
                            "revizyon_id", rev_id
                        ).execute()
                    except Exception:
                        pass
                    st.error(f"Kayıt hatası: {exc}")


# ============================================================
# 2. SAYFA: ÇALIŞMA GÜNLERİ
# ============================================================
elif sayfa == "Çalışma Günleri":
    st.title("📅 Operasyonel Çalışma Günleri")
    takvim_verisi = {
        "Ay": aylar,
        "2025 Çalışma Günü": [22, 20, 21, 22, 21, 20, 23, 21, 22, 23, 20, 22],
        "2026 Çalışma Günü": [21, 20, 20, 21, 17, 22, 22, 21, 22, 21, 21, 23],
        "Resmi Tatiller / Notlar": [
            "-", "-", "Ramazan Bayramı", "23 Nisan", "Kurban Bayramı", "-",
            "-", "30 Ağustos", "-", "29 Ekim", "-", "-",
        ],
    }
    st.data_editor(
        pd.DataFrame(takvim_verisi),
        width="stretch",
        hide_index=True,
        num_rows="fixed",
    )


# ============================================================
# 3. SAYFA: BULUT REVİZYON YÖNETİMİ
# ============================================================
else:
    st.title("☁️ Bulut Revizyon Yönetimi")
    client = get_supabase_client()

    if client is None:
        st.error("Supabase bağlantısı kurulamadı. Secrets ayarlarını kontrol edin.")
        st.stop()

    try:
        log_res = (
            client.table("revizyon_log")
            .select("*")
            .order("kayit_zamani", desc=True)
            .execute()
        )
        logs = log_res.data or []
    except Exception as exc:
        st.error(f"Revizyon listesi alınamadı: {exc}")
        st.stop()

    if not logs:
        st.info("Kayıtlı revizyon bulunmuyor.")
        st.stop()

    df_log = pd.DataFrame.from_records(logs)
    if "kayit_zamani" in df_log.columns:
        df_log["kayit_zamani"] = pd.to_datetime(
            df_log["kayit_zamani"], errors="coerce"
        ).dt.strftime("%Y-%m-%d %H:%M")

    def rev_label(row: pd.Series) -> str:
        durum = row.get("durum", "tamamlandi")
        satir = row.get("satir_sayisi", "?")
        return (
            f"{row.get('kayit_zamani', '')} | {row.get('olusturan_kisi', '')} | "
            f"{row.get('revizyon_notu', '')} | {satir} satır | {durum}"
        )

    labels = {rev_label(row): row["revizyon_id"] for _, row in df_log.iterrows()}
    secili_label = st.selectbox("Revizyon seçin", list(labels.keys()))
    secili_rev = labels[secili_label]
    secili_row = df_log.loc[df_log["revizyon_id"] == secili_rev].iloc[0]

    st.dataframe(
        pd.DataFrame([secili_row]),
        width="stretch",
        hide_index=True,
    )

    c_getir, c_sil = st.columns(2)

    if c_getir.button(
        "📥 Seçili Versiyonu Ekrana Çek",
        type="primary",
        use_container_width=True,
    ):
        try:
            beklenen = secili_row.get("satir_sayisi")
            try:
                beklenen = int(beklenen) if pd.notna(beklenen) else None
            except Exception:
                beklenen = None

            with st.spinner("Revizyon sayfalı olarak indiriliyor..."):
                gelen_df = supabase_tum_revizyonu_getir(
                    client, secili_rev, beklenen_satir=beklenen
                )

            if gelen_df.empty:
                st.warning("Bu revizyona ait bütçe satırı bulunamadı.")
            else:
                st.session_state.ana_veri = gelen_df
                st.session_state.hesaplandi = True
                st.session_state.editor_key += 1
                st.session_state.aktif_sayfa_no = 1
                st.success(
                    f"{len(gelen_df):,} satır hafızaya alındı. "
                    "Sol menüden 'Çarşaf Liste & Bütçe' sayfasına geçin."
                )
                gc.collect()
        except Exception as exc:
            st.error(f"Revizyon getirme hatası: {exc}")

    if c_sil.button(
        "🗑️ Seçili Versiyonu Kalıcı Sil",
        use_container_width=True,
    ):
        try:
            with st.spinner("Revizyon siliniyor..."):
                # FK + ON DELETE CASCADE varsa yalnızca log silmek yeterlidir.
                # Geriye uyumluluk için önce detay kayıtları da siliyoruz.
                client.table("butce_tablosu").delete().eq(
                    "revizyon_id", secili_rev
                ).execute()
                client.table("revizyon_log").delete().eq(
                    "revizyon_id", secili_rev
                ).execute()
            st.success("Revizyon silindi.")
            st.rerun()
        except Exception as exc:
            st.error(f"Silme hatası: {exc}")f
