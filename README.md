# Türkçe Terim Etmeni

İngilizce bir bilişim makalesi (PDF) yükleyin; program makaledeki teknik terimleri
bir dil modeliyle çıkarır, güncel TBD Bilişim Sözlüğü ile **kod seviyesinde** karşılaştırır
ve sözlükte bulunmayan terimleri öne çıkarır. Sözlüğe otomatik terim eklemez.

## Çalıştırma

```bash
python3 run.py                 # sunucuyu başlatır, tarayıcıyı açar
python3 run.py serve --no-browser
```

Arayüz `http://127.0.0.1:8876` adresinde açılır. Ana sayfada makale analizi,
`/dictionary` sayfasında sözlük yönetimi, `/settings` sayfasında bulut API ayarları bulunur.

### Komut satırı

```bash
python3 run.py scan MAKALE.pdf --model MODEL       # tek PDF analizi (yerel model için --model gerekli)
python3 run.py dictionary status                   # etkin sözlük durumu
python3 run.py dictionary check                    # TBD sitesinde güncelleme ara
python3 run.py abbreviations status                # kısaltma kaynağı durumu
python3 run.py evaluate-expected EXPECTED.json RAPOR.json   # basit eksik-terim ölçümü
```

## Analiz motoru (model) seçimi

Program iki motorla çalışır; hangisini kullanacağını kendisi anlar:

- **Bulut API** (önerilen): `/settings` sayfasından sağlayıcı, anahtar ve model girin.
  Bir API anahtarı kayıtlıysa tarama otomatik olarak API'yi kullanır.
- **Yerel Ollama**: API anahtarı yoksa yerel Ollama modeli kullanılır; model her
  analizde arayüzden seçilir.

Ortam değişkeni ile de çalıştırılabilir (`.env`):

```env
MODEL_PROVIDER=api        # açıkça API'ye zorlar (api | ollama | boş=otomatik)
API_PROVIDER=deepseek     # openai | deepseek | anthropic | google
API_KEY=sk-...
API_MODEL=deepseek-chat
API_BASE_URL=             # boşsa sağlayıcının varsayılanı kullanılır
```

Desteklenen varsayılan modeller: openai=`gpt-4o-mini`, deepseek=`deepseek-v4-flash`,
anthropic=`claude-sonnet-4-20250514`, google=`gemini-2.0-flash`. Anahtar asla kaynak
koda yazılmaz; `/settings` üzerinden girilen değerler yerel `data/runtime/provider.json`
dosyasında tutulur (Git'e eklenmez).

## İşlem hattı

```
PDF → metin çıkarımı → parçalama → LLM terim çıkarımı (few-shot)
   → normalizasyon → deterministik sözlük araması → eksik terimler
```

- LLM yalnızca teknik terim adayı üretir; sözlük karşılaştırması yapmaz.
- Sözlük araması normalize edilmiş İngilizce terimler üzerinden kesin eşleşmeyle
  (Python `dict`) yapılır: `FOUND` / `NOT_FOUND`.
- Metinde gerçekten geçmeyen model çıktıları rapora alınmaz.
- Aynı terim birden çok parçada bulunursa bir kez gösterilir; her terim bağlamı ve
  sayfa bilgisiyle raporlanır.
- DeepSeek ve OpenAI uyumlu sağlayıcılarda API'nin JSON modu kullanılır. Model her
  parçada en fazla sekiz, belge bağlamına özgü olmayan sözlük adayı döndürmek üzere
  istenir; bu bir regex filtresi değil, çıkarım talimatının parçasıdır.

## Tek makale kalite kontrolü

Yeni model, prompt veya sağlayıcıyı tüm PDF'lerde denemeden önce tek bir makale
üzerinde ölçün. Uzman tarafından gözden geçirilmiş **eksiksiz** eksik-terim listesini
oluşturun:

```json
{"expected_missing_terms": ["agentic workflow", "tool orchestration"]}
```

Ardından üretilen JSON raporuyla karşılaştırın:

```bash
python3 run.py evaluate-expected expected.json output/MODEL/MAKALE/MAKALE_terms.json
```

Komut doğru bulunan, kaçırılan ve listede olmaması gereken aday sayılarını; precision
ve recall değerlerini verir. Beklenen liste eksiksiz değilse precision sonucu geçerli
bir kalite ölçümü değildir.

## Sonuçlar

Raporlar `output/<model>/<pdf-adı>/` altında oluşur:

- `<ad>_terms.json` — makinece okunur tam sonuç
- `<ad>_terim_raporu.csv` — Excel uyumlu (UTF-8 BOM)
- `<ad>_terim_raporu.xlsx` — biçimli Excel raporu

Ana görünüm sözlükte bulunmayan terimleri (`missing_terms`) öne çıkarır; sözlükte
bulunanlar ve kısaltma kaynağından gelen olası eşleşmeler ayrı gruplarda gösterilir.

## Kurulum

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python3 run.py
```

Yerel Ollama kullanacaksanız bir model indirin:

```bash
ollama pull MODEL_ETIKETI
```

## Kolay kullanım

- **macOS:** `BASLAT_APPLE.command` dosyasına çift tıklayın.
- **Windows:** `BASLAT_WINDOWS.bat` dosyasına çift tıklayın.

## Test

```bash
PYTHONPYCACHEPREFIX=/private/tmp/terim-etmeni-pycache PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Sözlük

Etkin sözlük `data/tbd_dictionary_2026_coordinate.json`; kaynak
[Bilişimde Özenli Türkçe](https://bilisimde.ozenliturkce.org.tr/). Kısaltmalar ayrı
bir kaynak olarak `data/tbd_abbreviations_2025_03_17.json` içindedir ve ana sözlüğe
birleştirilmez.

## Proje yapısı

```text
data/                       Yerel sözlük ve kısaltma kaynağı
src/terim_etmeni/           Uygulama kaynak kodu
tests/                      Otomatik testler
output/                     Üretilen raporlar
evaluation/                 Basit eksik-terim değerlendirme örnekleri
docs/                       Proje bağlamı ve karar kayıtları
run.py                      Giriş noktası
BASLAT_APPLE.command        macOS başlatıcısı
BASLAT_WINDOWS.bat          Windows başlatıcısı
```

## Bilinen sınırlar

- Taranmış (görüntü) PDF'lerde OCR yapılmaz.
- Küçük yerel modeller bazı terimleri atlayabilir; en eksiksiz eksik-terim listesi
  güçlü bir bulut modelinden gelir.
- Sonuçlar otomatik öneridir; nihai liste uzman incelemesinden geçirilmelidir.
- Aynı adlı PDF yeniden taranırsa önceki raporun üzerine yazılır.
