"""
MLflow deneyleri: "Çoğunluk azınlığı yutmasın" fikrini ölçmek.

İki senaryo, her biri 3 yöntemle (tek_oy, kuadratik, kuadratik_kume):

  1) sahte_cogunluk : Gerçek kullanıcıların çoğu HAYIR diyor, sahte hesaplar
                      (bot çiftliği) EVET basıyor. Bot sayısı arttıkça sonuç
                      değişiyor mu?
  2) tutkulu_azinlik: Azınlık konuyu çok önemsiyor (yoğunluk 3, HAYIR),
                      çoğunluk umursamıyor (yoğunluk 1, EVET). Azınlık hangi
                      oranda sesini duyurabiliyor?

Her ayar MLflow'da bir "run" olur: parametreler, metrikler, grafikler ve
sonuç tablosu kaydedilir. Senaryo başına bir üst run, altında alt run'lar.

Kullanım:
    python deney.py                          # yerel: ./mlruns, sonra `mlflow ui`
    MLFLOW_TRACKING_URI=... python deney.py  # DagsHub'a gönderir (README'ye bak)
"""
import argparse
import csv
import hashlib
import os
import random

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mlflow

from oylama import YONTEMLER, Kullanici, Oy, oylamayi_kapat

DENEY_ADI = "oylama-azinlik-koruma"


def veri_yukle(yol):
    with open(yol, encoding="utf-8") as f:
        return [
            Kullanici(int(r["id"]), r["takma"], r["il"], r["adres_ozeti"], int(r["kayit_gunu"]), r["tip"])
            for r in csv.DictReader(f)
        ]


def dosya_ozeti(yol):
    with open(yol, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()  # DVC de md5 kullanır


# ---------------- senaryolar ----------------

def sahte_cogunluk(kisiler, bot_sayisi, gercek_destek, katilim, tohum, bot_yogunluk):
    rnd = random.Random(tohum)
    gercek = [u for u in kisiler if u.tip == "gercek"]
    botlar = [u for u in kisiler if u.tip == "sahte"][:bot_sayisi]
    oy_verenler = rnd.sample(gercek, int(len(gercek) * katilim))
    oylar = {u.id: Oy(evet=rnd.random() < gercek_destek, yogunluk=1) for u in oy_verenler}
    for b in botlar:
        oylar[b.id] = Oy(evet=True, yogunluk=bot_yogunluk)  # 3 = 9 kredi, 20 krediyle mümkün
    havuz = gercek + botlar  # sistemde kayıtlı olanlar
    gercek_evet = sum(oylar[u.id].evet for u in oy_verenler) / max(1, len(oy_verenler))
    return havuz, oylar, gercek_evet


def tutkulu_azinlik(kisiler, azinlik_orani, katilim, tohum):
    rnd = random.Random(tohum)
    gercek = [u for u in kisiler if u.tip == "gercek"]
    oy_verenler = rnd.sample(gercek, int(len(gercek) * katilim))
    oylar = {}
    for u in oy_verenler:
        if rnd.random() < azinlik_orani:
            oylar[u.id] = Oy(evet=False, yogunluk=3)  # azınlık: çok önemsiyor
        else:
            oylar[u.id] = Oy(evet=True, yogunluk=1)  # çoğunluk: hafif tercih
    return gercek, oylar


# ---------------- grafik ----------------

def grafik(satirlar, x, y, xetiket, baslik, yol, esik=0.5):
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for yontem in YONTEMLER:
        s = [r for r in satirlar if r["yontem"] == yontem]
        ax.plot([r[x] for r in s], [r[y] for r in s], marker="o", label=yontem)
    ax.axhline(esik, color="gray", linestyle="--", linewidth=1, label="kabul eşiği")
    ax.set_xlabel(xetiket)
    ax.set_ylabel("Ağırlıklı evet oranı")
    ax.set_title(baslik)
    ax.set_ylim(0, 1)
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(yol, dpi=130)
    plt.close(fig)


def tablo_yaz(satirlar, yol):
    with open(yol, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(satirlar[0].keys()))
        w.writeheader()
        w.writerows(satirlar)


# ---------------- ana akış ----------------

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--veri", default="data/secmenler.csv")
    p.add_argument("--katilim", type=float, default=0.6)
    p.add_argument("--gercek-destek", type=float, default=0.3)
    p.add_argument("--bot-yogunluk", type=int, default=3, choices=[1, 2, 3])
    p.add_argument("--tohum", type=int, default=42)
    a = p.parse_args()

    kisiler = veri_yukle(a.veri)
    veri_md5 = dosya_ozeti(a.veri)
    os.makedirs("ciktilar", exist_ok=True)
    mlflow.set_experiment(DENEY_ADI)

    ortak = {
        "veri_dosyasi": a.veri,
        "veri_md5": veri_md5,  # hangi veri sürümüyle çalıştığı (DVC ile eşleşir)
        "katilim": a.katilim,
        "tohum": a.tohum,
    }

    # ---- Senaryo 1: sahte çoğunluk ----
    maks_bot = sum(u.tip == "sahte" for u in kisiler)
    bot_listesi = sorted({0, 10, 25, 50, 75, 100, 150, maks_bot} & set(range(maks_bot + 1)))
    satirlar1 = []
    with mlflow.start_run(run_name="senaryo1_sahte_cogunluk"):
        mlflow.log_params({**ortak, "senaryo": "sahte_cogunluk", "gercek_destek": a.gercek_destek,
                           "bot_yogunluk": a.bot_yogunluk})
        mlflow.set_tag("senaryo", "sahte_cogunluk")
        for yontem in YONTEMLER:
            for n in bot_listesi:
                havuz, oylar, gercek_evet = sahte_cogunluk(kisiler, n, a.gercek_destek, a.katilim, a.tohum, a.bot_yogunluk)
                r = oylamayi_kapat("KONU", "ULUSAL", havuz, oylar, yontem)
                saldiri = r["sonuc"] == "KABUL" and gercek_evet <= 0.5
                with mlflow.start_run(run_name=f"{yontem}_bot{n}", nested=True):
                    mlflow.set_tags({"senaryo": "sahte_cogunluk", "yontem": yontem})
                    mlflow.log_params({**ortak, "yontem": yontem, "bot_sayisi": n,
                                       "gercek_destek": a.gercek_destek, "bot_yogunluk": a.bot_yogunluk})
                    mlflow.log_metrics({
                        "evet_orani": r["evet_orani"],
                        "gercek_evet_orani": round(gercek_evet, 4),
                        "kabul": int(r["sonuc"] == "KABUL"),
                        "saldiri_basarili": int(saldiri),
                        "tespit_edilen_kume": max(r["supheli_kumeler"], default=0),
                        "katilim_orani": r["katilim"],
                    })
                satirlar1.append({"yontem": yontem, "bot_sayisi": n, "evet_orani": r["evet_orani"],
                                  "gercek_evet_orani": round(gercek_evet, 4), "sonuc": r["sonuc"],
                                  "saldiri_basarili": saldiri,
                                  "tespit_edilen_kume": max(r["supheli_kumeler"], default=0)})
        grafik(satirlar1, "bot_sayisi", "evet_orani", "Sahte hesap sayısı",
               "Senaryo 1: Sahte çoğunluk saldırısı", "ciktilar/senaryo1.png")
        tablo_yaz(satirlar1, "ciktilar/senaryo1.csv")
        mlflow.log_artifact("ciktilar/senaryo1.png")
        mlflow.log_artifact("ciktilar/senaryo1.csv")
        for yontem in YONTEMLER:
            mlflow.log_metric(f"{yontem}_basarili_saldiri_sayisi",
                              sum(r["saldiri_basarili"] for r in satirlar1 if r["yontem"] == yontem))

    # ---- Senaryo 2: tutkulu azınlık ----
    satirlar2 = []
    with mlflow.start_run(run_name="senaryo2_tutkulu_azinlik"):
        mlflow.log_params({**ortak, "senaryo": "tutkulu_azinlik"})
        mlflow.set_tag("senaryo", "tutkulu_azinlik")
        for yontem in YONTEMLER:
            for oran in [0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45]:
                havuz, oylar = tutkulu_azinlik(kisiler, oran, a.katilim, a.tohum)
                r = oylamayi_kapat("KONU", "ULUSAL", havuz, oylar, yontem)
                azinlik_kazandi = r["sonuc"] == "RED"
                with mlflow.start_run(run_name=f"{yontem}_azinlik{int(oran * 100)}", nested=True):
                    mlflow.set_tags({"senaryo": "tutkulu_azinlik", "yontem": yontem})
                    mlflow.log_params({**ortak, "yontem": yontem, "azinlik_orani": oran})
                    mlflow.log_metrics({
                        "evet_orani": r["evet_orani"],
                        "azinlik_agirlik_payi": round(1 - r["evet_orani"], 4),
                        "azinlik_kazandi": int(azinlik_kazandi),
                    })
                satirlar2.append({"yontem": yontem, "azinlik_orani": oran, "evet_orani": r["evet_orani"],
                                  "ham_evet": r["ham_evet"], "ham_hayir": r["ham_hayir"],
                                  "sonuc": r["sonuc"], "azinlik_kazandi": azinlik_kazandi})
        grafik(satirlar2, "azinlik_orani", "evet_orani", "Tutkulu azınlığın oranı",
               "Senaryo 2: Azınlığın sesi duyuluyor mu?", "ciktilar/senaryo2.png")
        tablo_yaz(satirlar2, "ciktilar/senaryo2.csv")
        mlflow.log_artifact("ciktilar/senaryo2.png")
        mlflow.log_artifact("ciktilar/senaryo2.csv")

    # Konsol özeti
    print("\nSenaryo 1 (sahte çoğunluk): saldırı başarılı olan bot sayıları")
    for yontem in YONTEMLER:
        b = [r["bot_sayisi"] for r in satirlar1 if r["yontem"] == yontem and r["saldiri_basarili"]]
        print(f"  {yontem:15s}: {b or 'hiç'}")
    print("Senaryo 2 (tutkulu azınlık): azınlığın kazandığı oranlar")
    for yontem in YONTEMLER:
        z = [r["azinlik_orani"] for r in satirlar2 if r["yontem"] == yontem and r["azinlik_kazandi"]]
        print(f"  {yontem:15s}: {z or 'hiç'}")
    print(f"\nMLflow deneyi: {DENEY_ADI}  (izleme adresi: {mlflow.get_tracking_uri()})")


if __name__ == "__main__":
    main()
