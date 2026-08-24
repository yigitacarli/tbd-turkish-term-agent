# Türkçe Terim Etmeni — Proje Bağlamı

> Bu dosya projenin kalıcı bağlamıdır. Yeni bir sohbet, geliştirici veya yapay
> zekâ önce bu dosyayı, ardından `docs/DECISIONS.md`
> dosyalarını okumalıdır. Sohbet içinde alınan kararlar burada yazmıyorsa kalıcı
> karar sayılmaz.

## Ürün amacı

İngilizce bir bilişim makalesi PDF olarak yüklenir. Program makaledeki gerçek
teknik terim adaylarını bir dil modeliyle çıkarır ve güncel TBD Bilişim Terimleri
Sözlüğü ile deterministik olarak karşılaştırır. Uzmanın asıl görmek istediği çıktı,
sözlükte bulunmayan ve insan incelemesi gerektiren terimlerdir.

Program sözlüğe kendiliğinden terim eklemez ve Türkçe karşılığın doğruluğu
konusunda nihai karar vermez. Son karar Tuncer Ören ve TBD çalışma grubundaki
uzmanlara aittir.

## Hedef kullanıcı ve kullanım

- Birincil kullanıcı: Emeritüs Prof. Dr. Tuncer Ören gibi alan uzmanları.
- Ana akış basittir: makale seçimi, analiz, sözlükte bulunmayan terimlerin listesi
  ve Excel indirme.
- Birincil kullanım kişisel bilgisayarda yerel tarayıcı arayüzüdür. Bulut API
  (DeepSeek, OpenAI, Gemini, Anthropic) veya yerel Ollama modeli seçilebilir.

## Değişmez ürün kuralları

1. Sözlükte bulunma kararını dil modeli değil deterministik Python kodu verir.
2. Dil modeli yalnızca teknik terim adayı üretir; sözlük verisi model'e verilmez.
3. Başarısız ya da kısmi model çalışması kullanıcıya "0 eksik terim" olarak sunulmaz.
4. Her rapor kullanılan sözlük sürümünü ve modeli kaydeder.
5. Yeni sözlük doğrulanmadan etkin sözlüğün üzerine yazılmaz; son sağlam sürüm korunur.
6. Kısaltmalar sözlüğü ana sözlükten ayrı bir kaynak olarak ele alınır.
7. Yeni karmaşık filtre eklenmez; işlem hattı sade kalır:
   `PDF → LLM çıkarımı → normalizasyon → sözlük arama → eksik terimler`.

## İşlem hattı

```
PDF → metin çıkarımı (pdf_reader) → parçalama (chunker)
   → LLM terim çıkarımı (few-shot; ollama_client/api_client)
   → normalizasyon + tekilleştirme (term_extraction)
   → kesin sözlük eşleşmesi (pipeline.TermDictionary)
   → eksik terimler + rapor (reporting)
```

- Sözlük araması normalize edilmiş İngilizce terimler üzerinden kesin `dict`
  eşleşmesiyle yapılır (`FOUND`/`NOT_FOUND`); fuzzy/embedding otomatik karar vermez.
- Modelin metinde geçmeyen adayları (halüsinasyon) rapora alınmaz.
- Kısaltma kaynağı bilgi amaçlı olası eşleşme olarak ayrı grupta gösterilir.

## Yapı

- Paket: `src/terim_etmeni/`
- Giriş: `run.py`
- Testler: `tests/`
- Dokümanlar: `docs/`
- Etkin sözlük: `data/tbd_dictionary_2026_coordinate.json`
- Kısaltma kaynağı: `data/tbd_abbreviations_2025_03_17.json`
- Çalışma zamanı (git dışı): `data/runtime/`, `output/`

## Veri kaynakları

- Ana kaynak: TBD Bilişim Sözlüğü, İngilizce–Türkçe yönü.
- Kaynak site: <https://bilisimde.ozenliturkce.org.tr/>
- Site zaman zaman otomatik isteklere doğrulama ekranı döndürebilir. Otomatik
  güncelleme başarısız olduğunda uygulama son sağlam yerel sözlükle çalışmalıdır.

## Bilinen belirsizlikler

- Kullanılacak kişisel bilgisayarın işletim sistemi ve donanımı kesinleşmedi.
- TBD verisinin yeniden dağıtım ve otomatik indirme koşulları kurum tarafından
  doğrulanmalıdır.

## Yeni geliştirici için çalışma kuralı

1. `README.md`, `docs/PROJECT_CONTEXT.md`, `docs/DECISIONS.md`
   ve `docs/AI_HANDOFF.md` oku.
2. `git status --short --branch` ile dalı ve değişiklikleri kontrol et.
3. Testleri çalıştır.
4. Bir varsayım ürün davranışını değiştirecekse `docs/DECISIONS.md`ye kaydet.
5. Geliştirme sonunda `docs/AI_HANDOFF.md` içindeki durumu güncelle.
6. Çalışan davranışı ölçmeden filtre, model veya sözlük kaynağı değiştirme.
