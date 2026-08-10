# TBD Dictionary Control

TBD Dictionary Control, metin katmanı bulunan PDF belgelerindeki İngilizce bilişim
terimlerini çıkarır ve Bilişimde Özenli Türkçe sitesinden hazırlanmış yerel
İngilizce–Türkçe sözlükle karşılaştırır. Sözlükte bulunmayan adayları sayfa ve
geçiş bilgileriyle gösterir; CSV ve JSON raporu üretir.

PDF içeriği ve model çalışması yerel bilgisayarda kalır. Qwen yalnızca aday terim
çıkarır; sözlük üyeliğine Python kodu karar verir.

## Gereksinimler

- Python 3.9+
- [Ollama](https://ollama.com/)
- Ollama içinde `qwen:latest` modeli
- Metin seçilebilen bir PDF

```bash
ollama pull qwen:latest
```

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

## Kullanım

Arayüzü başlatmak için:

```bash
python3 run.py
```

macOS'ta `Baslat.command` dosyasına çift tıklanabilir. Arayüz
`http://127.0.0.1:8765` adresinde açılır. PDF seçildikten sonra sonuçlar ekranda
incelenebilir ve raporlar indirilebilir. Uygulamayı kapatmak için terminalde
`Control-C` kullanılır.

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
- **Eksik:** Sözlükte karşılığı bulunmayan adaylar
- **Elenen:** Düşük güvenli adaylar; denetim amacıyla raporda korunur

`output/` klasöründe her PDF için şu dosyalar oluşur:

- `<ad>_terim_raporu.csv`
- `<ad>_terms.json`

CSV, Excel ile uyumlu UTF-8 BOM biçimindedir.

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
- Küçük yerel modeller bazı terimleri atlayabilir veya yanlış aday üretebilir.
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
run.py                 Kurulumsuz giriş noktası
pyproject.toml         Paket ve bağımlılık tanımı
AI_HANDOFF.md          Yeni yapay zekâ sohbeti için teknik devir notu
```
