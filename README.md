# TBD Dictionary Control (Türkçe Terim Etmeni)

TBD Dictionary Control (Türkçe Terim Etmeni), metin katmanı bulunan PDF belgelerindeki İngilizce bilişim
terimlerini çıkarır ve Bilişimde Özenli Türkçe sitesinden hazırlanmış yerel
İngilizce–Türkçe sözlükle karşılaştırır. Sözlükte bulunmayan adayları sayfa ve
geçiş bilgileriyle gösterir; CSV ve JSON raporu üretir.

PDF içeriği ve model çalışması yerel bilgisayarda kalır. Qwen yalnızca aday terim
çıkarır; sözlük üyeliğine Python kodu karar verir.

## Gereksinimler

- Python 3.9+
- [Ollama](https://ollama.com/)
- Ollama içinde `qwen3.5:2b` modeli (Windows ve macOS için önerilen hafif varsayılan)
- Metin seçilebilen bir PDF

```bash
ollama pull qwen3.5:2b
```

## Yapay zekâ motoru ve platform desteği

Bu teslim sürümü **yerel Ollama** ile çalışır: PDF ve terim sonuçları bilgisayardan
çıkmaz. `qwen3.5:2b` günlük kullanım için önerilen varsayılandır; bilgisayarda
yüklü başka bir Ollama modeli arayüzden seçilebilir.

OpenAI, Azure OpenAI veya başka bir kurum API'si bu sürümde henüz uygulanmamıştır.
Bu tür bir entegrasyon için kurumun sağlayıcı, anahtar yönetimi, maliyet ve veri
politikası kararları gerekir; arayüz desteklemediği bir API seçeneğini göstermez.

Uygulamanın çalışma şekli Windows, macOS ve Linux'ta aynıdır: Python, Ollama ve
aynı model gerekir. Fark yalnızca ilk kurulum ve başlatma komutlarındadır.

Donanıma göre önerilen yerel modeller ve nihai seçim için kabul deneyi
[MODEL_REHBERI.md](MODEL_REHBERI.md) içinde açıklanmıştır.

## Kurulum

Proje klasöründe:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Windows PowerShell'de sanal ortamı etkinleştirme komutu:

```powershell
.venv\Scripts\Activate.ps1
```

Arayüzü Windows'ta başlatmak için:

```powershell
python run.py
```

## Kolay kullanım

İlk kurulum yapıldıktan sonra komut yazmadan başlatmak için:

- **macOS:** `Baslat.command` dosyasına çift tıklayın. Bu, macOS için en kolay
  günlük kullanım yöntemidir.
- **Windows:** `Baslat.bat` dosyasına çift tıklayın. Pencere açık kaldığı sürece
  arayüz çalışır.

Her iki başlatıcı da `http://127.0.0.1:8765` adresinde arayüzü açar. PDF seçin,
modeli seçin ve analizden sonra önce yüksek öncelikli adayları inceleyin.

## Komut satırı kullanımı

Arayüzü başlatmak için:

```bash
python3 run.py
```

PDF seçildikten sonra sonuçlar ekranda incelenebilir ve raporlar indirilebilir.
Model parçalarından biri okunamazsa arayüz analizi `kısmi` veya `başarısız`
olarak işaretler; böyle bir durum “sözlükte olmayan terim yok” anlamına gelmez.
Uygulamayı kapatmak için açık terminal penceresinde `Control-C` kullanılır.

Komut satırından tek PDF taramak için:

```bash
python3 run.py scan /dosya/yolu/makale.pdf
```

Bir klasördeki bütün PDF'leri taramak için:

```bash
python3 run.py scan /dosya/yolu/pdf-klasoru
```

Başka bir Ollama modeli kullanmak için:

```bash
python3 run.py scan makale.pdf --model qwen3:4b
```

Varsayılan model `OLLAMA_MODEL`, Ollama adresi `OLLAMA_URL` ortam değişkeniyle de
değiştirilebilir.

## Sonuçlar

Arayüz ve terminal dört grup gösterir:

- **Bulunan:** Sözlükte tam eşleşen terimler
- **Olası:** Tekil/çoğul veya kontrollü yazım farkıyla eşleşenler
- **Eksik:** Sözlükte karşılığı bulunmayan adaylar. Tek sözcüklü terimler ve
  kısaltmalar kaybolmamaları için düşük öncelikli inceleme satırı olarak korunur.
- **Elenen:** Düşük güvenli adaylar; denetim amacıyla raporda korunur

`output/` klasöründe her PDF için şu dosyalar oluşur:

- `<ad>_terim_raporu.csv`
- `<ad>_terms.json`

CSV, Excel ile uyumlu UTF-8 BOM biçimindedir. Satırlar önce karar gerektiren
adayları gösterir: **İnceleme gerekli** ve **Yakın eşleşme** satırları en üstte,
ardından bilgi ve elenen adaylar gelir. `öncelik` ve `önerilen işlem` sütunları
sözlük sorumlusunun hangi satırı ele alacağını açıklar; uygulama sözlüğe otomatik
terim eklemez.

Güvenli tire ve düzenli tekil-çoğul farkları sözlük tarafından kapsanmış sayılır.
Kısaltma açılımı gibi karar gerektiren yakın eşleşmeler **Olası** grubunda insan
doğrulamasına bırakılır.

## Test

Testler Ollama çağırmadan çalışır:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Sözlük

Uygulama `data/tbd_dictionary_2026_coordinate.json` dosyasını kullanır. Kaynak:
[Bilişimde Özenli Türkçe](https://bilisimde.ozenliturkce.org.tr/). Teslim veya
kurumsal dağıtım öncesinde sözlüğün kullanım ve yeniden dağıtım koşulları kurum
tarafından doğrulanmalıdır.

## Bilinen sınırlar

- Görüntü olarak taranmış PDF'lerde OCR yapılmaz.
- Küçük yerel modeller bazı terimleri atlayabilir veya yanlış aday üretebilir. Varsayılan
  ayarlar tek model geçişi ve 6.000 karakterlik parça kullanır; özellikle ayrıntılı
  inceleme gerektiğinde daha büyük bir model seçilebilir.
- Modelin hiç önermediği bazı terimler kontrollü teknik baş kalıpları, açık
  kısaltma tanımları ve tekrarlanan teknoloji kuşak adlarıyla deterministik olarak
  geri kazanılır. Bu adaylar gürültü riskinden dolayı düşük öncelikli insan
  incelemesinde tutulur; ham n-gram listesi üretilmez.
- Sonuçlar otomatik öneridir; nihai liste uzman incelemesinden geçirilmelidir.
- Aynı adlı PDF yeniden taranırsa önceki raporun üzerine yazılır.
- Ollama hedef bilgisayarda kurulu değilse uygulama model indirmez; açıklayıcı hata
  verir.

## Proje yapısı

```text
data/                  Yerel sözlük
src/terim_etmeni/      Uygulama kaynak kodu
tests/                 Otomatik testler
output/                Üretilen raporlar
Baslat.command         macOS başlatıcısı
Baslat.bat             Windows başlatıcısı
run.py                 Kurulumsuz giriş noktası
pyproject.toml         Paket ve bağımlılık tanımı
AI_HANDOFF.md          Yeni yapay zekâ sohbeti için teknik devir notu
```
