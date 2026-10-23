"""
Sentetik seçmen verisi üretir -> data/secmenler.csv

Bu dosya DVC ile versiyonlanır. Gerçek kişisel veri YOKTUR:
uygulamadaki gibi ad, soyad, doğum tarihi ve adres hiçbir zaman ham
halde yazılmaz; sadece tuzlanmış SHA-256 özeti (hash) ve il tutulur.

Kullanım:
    python veri_uret.py                 # varsayılan: 300 gerçek, 150 sahte hesap
    python veri_uret.py --gercek 500 --sahte 200
"""
import argparse
import csv
import hashlib
import os
import random

TUZ = "ders-projesi-tuz"  # uygulamadaki S.tuz karşılığı


def sha(metin: str) -> str:
    return hashlib.sha256(metin.encode("utf-8")).hexdigest()


def uret(gercek: int, sahte: int, tohum: int, yol: str) -> None:
    rnd = random.Random(tohum)
    iller = ["ankara"] * 30 + ["istanbul"] * 50 + ["izmir"] * 20  # nüfus payı (%)
    satirlar = []
    no = 1

    # Gerçek kullanıcılar: farklı adresler, kayıt günleri zamana yayılmış
    for i in range(gercek):
        il = rnd.choice(iller)
        adres = f"{il}|ilce{rnd.randint(1, 15)}|sokak {i}|no {rnd.randint(1, 200)}"
        satirlar.append({
            "id": no,
            "takma": f"kullanici{i + 1}",
            "il": il,
            "adres_ozeti": sha(TUZ + "|" + adres)[:16],
            "kayit_gunu": rnd.randint(0, 365),
            "tip": "gercek",
        })
        no += 1

    # Sahte hesaplar (bot çiftliği): aynı adres, aynı gün kayıt -> uygulamadaki
    # bz() fonksiyonu bunları birbirine bağlar (adres +40, kayıt günü +20 = 60)
    for i in range(sahte):
        satirlar.append({
            "id": no,
            "takma": f"bot{i + 1}",
            "il": "istanbul",
            "adres_ozeti": sha(TUZ + "|istanbul|esenyurt|sahte sk. 1")[:16],
            "kayit_gunu": 300 + rnd.randint(0, 1),
            "tip": "sahte",
        })
        no += 1

    os.makedirs(os.path.dirname(yol), exist_ok=True)
    with open(yol, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(satirlar[0].keys()))
        w.writeheader()
        w.writerows(satirlar)
    print(f"{yol}: {gercek} gerçek + {sahte} sahte = {len(satirlar)} satır")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--gercek", type=int, default=300)
    p.add_argument("--sahte", type=int, default=150)
    p.add_argument("--tohum", type=int, default=42)
    p.add_argument("--cikti", default="data/secmenler.csv")
    a = p.parse_args()
    uret(a.gercek, a.sahte, a.tohum, a.cikti)
