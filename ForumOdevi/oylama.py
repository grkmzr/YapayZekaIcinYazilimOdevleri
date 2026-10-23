"""
forum_uygulamasi.html içindeki oy sayma mantığının Python karşılığı.

JS -> Python eşleşmesi:
    sec()   -> oy_hakki_var()   bölgesel/ulusal kapsam kontrolü
    bz()    -> benzerlik()      iki hesabın aynı kişi/bot olma puanı
    kume()  -> kume_agirliklari()  bağlı n hesabın toplam gücü = karekök(n)
    kapat() -> oylamayi_kapat()  eşik, katılım, sonuç

Yöntemler (MLflow'da karşılaştırılan "model" ayarı):
    tek_oy          : herkes 1 oy, ağırlık 1 (klasik çoğunluk)
    kuadratik       : yoğunluk 1-3, maliyeti yoğunluk^2 kredi (küme yok)
    kuadratik_kume  : kuadratik + sahte hesap kümelerine 1/sqrt(n) ağırlık
                      (uygulamadaki tam sistem)
"""
from dataclasses import dataclass, field
from math import sqrt

YONTEMLER = ["tek_oy", "kuadratik", "kuadratik_kume"]


@dataclass
class Kullanici:
    id: int
    takma: str
    il: str
    adres_ozeti: str
    kayit_gunu: int
    tip: str
    kredi: int = 20
    gecmis: dict = field(default_factory=dict)  # oylama_id -> evet/hayır


@dataclass
class Oy:
    evet: bool
    yogunluk: int = 1


def oy_hakki_var(u: Kullanici, kapsam: str) -> bool:
    return kapsam == "ULUSAL" or kapsam == u.il


def benzerlik(a: Kullanici, b: Kullanici) -> int:
    p = 0
    if a.adres_ozeti == b.adres_ozeti:
        p += 40
    if abs(a.kayit_gunu - b.kayit_gunu) <= 1:
        p += 20
    ortak = [k for k in a.gecmis if k in b.gecmis]
    if len(ortak) >= 3 and sum(a.gecmis[k] == b.gecmis[k] for k in ortak) / len(ortak) >= 0.95:
        p += 40
    return p


def kume_agirliklari(secmenler, oy_verenler, esik=60):
    """Union-find ile şüpheli hesapları kümeler. n kişilik kümede her oy 1/sqrt(n)."""
    ebeveyn = {u.id: u.id for u in secmenler}

    def bul(x):
        while ebeveyn[x] != x:
            ebeveyn[x] = ebeveyn[ebeveyn[x]]
            x = ebeveyn[x]
        return x

    for i, a in enumerate(secmenler):
        for b in secmenler[i + 1:]:
            if benzerlik(a, b) >= esik:
                ebeveyn[bul(a.id)] = bul(b.id)

    gruplar = {}
    for uid in oy_verenler:
        gruplar.setdefault(bul(uid), []).append(uid)

    w, supheli = {}, []
    for uyeler in gruplar.values():
        for uid in uyeler:
            w[uid] = 1 / sqrt(len(uyeler))
        if len(uyeler) >= 3:
            supheli.append(len(uyeler))
    return w, supheli


def oylamayi_kapat(tur, kapsam, kullanicilar, oylar, yontem, kume_esigi=60):
    """oylar: {kullanici_id: Oy}. Uygulamadaki kapat() ile aynı kurallar."""
    secmenler = [u for u in kullanicilar if oy_hakki_var(u, kapsam)]
    ids = list(oylar.keys())

    if yontem == "kuadratik_kume":
        w, supheli = kume_agirliklari(secmenler, ids, kume_esigi)
    else:
        w, supheli = {i: 1.0 for i in ids}, []

    e = h = 0.0
    he = hh = 0
    for uid in ids:
        o = oylar[uid]
        y = 1 if yontem == "tek_oy" else o.yogunluk
        g = y * w[uid]
        if o.evet:
            e += g
            he += 1
        else:
            h += g
            hh += 1

    katilim = len(ids) / max(1, len(secmenler))
    oran = e / (e + h) if e + h else 0.0
    esik = 0.5 if tur == "KONU" else 2 / 3
    min_katilim = 0.1 if tur == "KONU" else 0.2
    if katilim < min_katilim:
        sonuc = "GECERSIZ_KATILIM_YETERSIZ"
    elif oran > esik:
        sonuc = "KABUL"
    else:
        sonuc = "RED"

    return {
        "sonuc": sonuc,
        "evet_agirlikli": round(e, 3),
        "hayir_agirlikli": round(h, 3),
        "ham_evet": he,
        "ham_hayir": hh,
        "evet_orani": round(oran, 4),
        "esik": round(esik, 4),
        "katilim": round(katilim, 4),
        "supheli_kumeler": supheli,
    }
