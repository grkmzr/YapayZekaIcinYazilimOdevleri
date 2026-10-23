# Oylamalı Konu Platformu: MLflow + DVC

Bu repo, oylamalı konu/tartışma platformunun "çoğunluk azınlığı yutmasın"
mekanizmalarını deneylerle ölçer.

- `app/forum_uygulamasi.html`: çalışan web uygulaması (tarayıcıda açılır)
- `oylama.py`: uygulamadaki oy sayma mantığının Python karşılığı
- `veri_uret.py`: sentetik seçmen verisi üretir (`data/secmenler.csv`, **DVC ile versiyonlanır**)
- `deney.py`: deneyleri çalıştırır, sonuçları **MLflow**'a kaydeder

Veride gerçek kişisel bilgi yoktur. Uygulamadaki gibi adres yalnızca tuzlanmış
özet (hash) olarak tutulur.

## Deneyler

Üç yöntem karşılaştırılır:

| Yöntem | Açıklama |
|---|---|
| `tek_oy` | Herkes 1 oy (klasik çoğunluk) |
| `kuadratik` | Yoğunluk 1-3, maliyeti yoğunluk² kredi |
| `kuadratik_kume` | Kuadratik + sahte hesap kümelerine 1/√n ağırlık (uygulamadaki tam sistem) |

**Senaryo 1 – Sahte çoğunluk:** Gerçek seçmenlerin %67'si HAYIR diyor, bot
hesaplar EVET basıyor. Sonuç (300 gerçek kullanıcı, %60 katılım):

- `tek_oy`: 75 botla saldırı başarılı
- `kuadratik`: sadece 25 botla başarılı (kuadratik oy tek başına sahte hesaplara açık)
- `kuadratik_kume`: 150 botla bile başarısız

**Senaryo 2 – Tutkulu azınlık:** Azınlık konuyu çok önemsiyor (yoğunluk 3,
HAYIR), çoğunluk hafif tercihle EVET diyor.

- `tek_oy`: azınlık %45 olsa bile hiç kazanamıyor
- `kuadratik` / `kuadratik_kume`: azınlık %20'den itibaren sesini duyurabiliyor

## Kurulum (Mac)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Yerelde çalıştırma

```bash
python veri_uret.py
python deney.py
mlflow ui          # tarayıcıda http://127.0.0.1:5000
```

## DagsHub'a yükleme (kod + veri + MLflow)

DagsHub; GitHub gibi bir git sunucusu, DVC veri deposu ve MLflow sunucusunu tek
yerde verir. `KULLANICI` ve `REPO` yerine kendi adlarınızı yazın.

### 1. Repo oluştur

- GitHub'da boş bir repo aç (ör. `oylama-platformu`).
- dagshub.com'a GitHub hesabınla gir, **Create → Connect a repository → GitHub**
  ile bu repoyu bağla. Kod GitHub'da durur, DagsHub ona veri ve MLflow ekler.
- DagsHub'da **Your Settings → Tokens** kısmından bir token al.

### 2. Git + DVC

```bash
git init
git branch -M main
dvc init
python veri_uret.py
dvc add data/secmenler.csv          # data/secmenler.csv.dvc oluşur, veri git'e girmez

# DagsHub repo sayfasındaki "Remote → Data → DVC" kısmındaki komutları kopyala.
# Genelde şöyle görünür:
dvc remote add origin https://dagshub.com/KULLANICI/REPO.dvc
dvc remote modify origin --local auth basic
dvc remote modify origin --local user KULLANICI
dvc remote modify origin --local password TOKEN
dvc remote default origin

git add .
git commit -m "Oylama platformu, MLflow deneyleri ve DVC verisi"
git remote add origin https://github.com/KULLANICI/REPO.git
git push -u origin main
dvc push                             # veriyi DagsHub'a yükler
```

### 3. MLflow'u DagsHub'a bağla

```bash
export MLFLOW_TRACKING_URI=https://dagshub.com/KULLANICI/REPO.mlflow
export MLFLOW_TRACKING_USERNAME=KULLANICI
export MLFLOW_TRACKING_PASSWORD=TOKEN
python deney.py
```

Sonuçlar DagsHub repo sayfasındaki **Experiments** sekmesinde görünür.
Run'ları seçip **Compare** ile yöntemleri yan yana karşılaştırabilirsin.

### Veri sürümü değişince

```bash
python veri_uret.py --gercek 500 --sahte 200
dvc add data/secmenler.csv
git commit -am "Veri v2: 500 gerçek, 200 sahte"
git push && dvc push
python deney.py      # her run, verinin md5'ini "veri_md5" parametresi olarak kaydeder
```

Eski veriye dönmek için: `git checkout <commit> data/secmenler.csv.dvc && dvc checkout`
