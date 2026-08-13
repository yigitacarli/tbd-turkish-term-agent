# Türkçe Terim Etmeni

> **V2 geliştirmesi başladı.** Çalışan V1 bu dosyalarla birlikte korunmaktadır.
> Yeni geliştirme bağlamı için önce [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md),
> [DECISIONS.md](DECISIONS.md) ve [V2_ROADMAP.md](V2_ROADMAP.md) okunmalıdır.

## V2'yi çalıştırma

V2, V1'i değiştirmeden ayrı paket ve giriş noktası kullanır:

```bash
python3 run_v2.py
```

Bu komut yerel V2 sunucusunu başlatır ve tarayıcıyı otomatik açar. Tarayıcının
otomatik açılması istenmezse `python3 run_v2.py serve --no-browser` kullanılır.

V2 geliştirme sunucusu varsayılan olarak aynı anda tek analiz çalıştırır. Hedef
sunucunun kapasitesi ölçüldükten sonra sınır örneğin
`MAX_CONCURRENT_ANALYSES=2 python3 run_v2.py` ile artırılabilir. Kimlik doğrulama
ve HTTPS eklenmeden uygulama yalnız `localhost`/loopback adresinde çalışır; genel
ağa bağlanmayı reddeder. Yerel sağlık kontrolü `GET /healthz` adresindedir.
Kurum sunucusu zorunlu değildir. İleride istenirse gerekli teknik ve veri
politikası bilgileri `DEPLOYMENT_READINESS.md` dosyasında toplanmıştır.

Arayüz `http://127.0.0.1:8876` adresinde açılır. Ana sayfada makale analizi,
`/evaluation` sayfasında gerçek raporlardan iç değerlendirme kümesi hazırlama,
`/dictionary` sayfasında ise etkin sözlük sürümü, TBD sitesini kontrol etme ve
resmî sözlük PDF'sini elle doğrulama bulunur.

Sözlük durumunu terminalden görmek için:

```bash
python3 run_v2.py dictionary status
```

Ayrı TBD kısaltma kaynağının sürüm ve kayıt durumunu görmek için:

```bash
python3 run_v2.py abbreviations status
```

Resmî kısaltmalar PDF'sini ana sözlüğe eklemeden doğrulanmış JSON'a dönüştürmek
için `python3 run_v2.py abbreviations convert KAYNAK.pdf --output KISALTMALAR.json`
kullanılır. V2, kısaltma eşleşmelerini ana sözlük eşleşmesi saymaz; sonuçta
`Kısaltma kaynağında` başlığı ve teknik JSON'da kaynak etiketiyle gösterir.

İnsan tarafından etiketli gerçek makalelerde V1/V2 sonuçlarını çevrimdışı karşılaştırmak için
`evaluation/README.md` içindeki kabul kümesi biçimi ve `evaluate` komutu
kullanılır. Araç kaydedilmiş JSON raporlarından teknik-terim ve sözlük-açığı
hassasiyet/yakalama oranlarını hesaplar; yeni model çağrısı yapmaz.

Erişilebilir alan uzmanı yoksa web arayüzündeki **İç değerlendirme** sayfası bir
veya daha fazla V1/V2 JSON raporunu birleştirir. Proje sahibi her adayı
`Sözlükte var`, `Gerçek sözlük açığı` veya `Gürültü` olarak işaretler ve kabul
kümesini JSON olarak indirir. Bu çıktı `internal_review` statüsündedir; uzman
onayı olarak sunulmaz.

Yeni V2 analizleri ayrıca rapor klasörüne bir `candidate_snapshot.json` dosyası
yazar. Bu dosya, aynı Qwen adaylarını modele yeniden çağrı yapmadan güncel V2
filtrelerinden geçirmek için `run_v2.py replay SNAPSHOT --output RAPOR.json`
komutuyla kullanılabilir. Bu geliştirme/ölçüm aracıdır; ana kullanıcı akışını
değiştirmez.

V2'nin sözlük güncellemesi yeni PDF'yi önce geçici alanda dönüştürür ve kayıt
sayılarını doğrular. Başarısız bir indirme veya PDF düzeni değişikliği son sağlam
sözlüğü bozmaz. V2 raporları `output_v2/`, yönetilen sözlük sürümleri ise
`data/v2_runtime/` altında tutulur; her ikisi de çalışma zamanı verisidir ve Git'e
eklenmez.

Türkçe Terim Etmeni, metin katmanı bulunan PDF belgelerindeki İngilizce bilişim
terimlerini çıkarır ve Bilişimde Özenli Türkçe sitesinden hazırlanmış yerel
İngilizce–Türkçe sözlükle karşılaştırır. Sözlükte bulunmayan adayları sayfa ve
geçiş bilgileriyle gösterir; Excel, CSV ve JSON raporu üretir.

PDF içeriği ve model çalışması yerel bilgisayarda kalır. Sistem hibrit bir akış
kullanır: yerel model ve kontrollü metin kalıpları aday üretir; sözlük eşleşmesi,
metindeki kanıt, aday kaynağı ve model doğrulaması birlikte puanlanır. Yalnız
puan eşiğini geçen sözlük açıkları ana inceleme listesinde gösterilir.

## Gereksinimler

- Python 3.9+
- [Ollama](https://ollama.com/)
- Ollama içinde yapılandırılmış çıktı verebilen güncel bir model
- Metin seçilebilen bir PDF

```bash
ollama pull MODEL_ETIKETI
```

## Yapay zekâ motoru ve platform desteği

Bu teslim sürümü **yerel Ollama** ile çalışır: PDF ve terim sonuçları bilgisayardan
çıkmaz. Uygulama herhangi bir modeli kalıcı varsayılan yapmaz; Ollama'da kurulu
modeller arayüzde listelenir ve kullanıcı her analiz için modeli açıkça seçer.
İstenirse `OLLAMA_MODEL` ortam değişkeniyle kuruma özel bir ön seçim yapılabilir.

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

- **macOS:** `BASLAT_APPLE.command` dosyasına çift tıklayın. Bu, macOS için en kolay
  günlük kullanım yöntemidir.
- **Windows:** `BASLAT_WINDOWS.bat` dosyasına çift tıklayın. Pencere açık kaldığı sürece
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
python3 run.py scan /dosya/yolu/pdf-klasoru --model MODEL_ETIKETI
```

Başka bir Ollama modeli kullanmak için:

```bash
python3 run.py scan makale.pdf --model qwen3.5:2b
```

Web arayüzündeki isteğe bağlı ön seçim `OLLAMA_MODEL`, Ollama adresi `OLLAMA_URL`
ortam değişkeniyle ayarlanabilir. CLI kullanımında model açıkça verilmelidir.

## Sonuçlar

Arayüz ve terminal dört grup gösterir:

- **Bulunan:** Sözlükte tam eşleşen terimler
- **Olası:** Açılımı sözlükte bulunan kısaltma gibi insan kararı isteyen eşleşmeler
- **Öncelikli açık:** Sözlükte karşılığı bulunmayan yüksek güvenli adaylar
- **İkincil aday:** Orta güvenli, kaybolmaması için raporda tutulan fakat ana sayıyı
  şişirmeyen adaylar
- **Elenen:** Düşük güvenli adaylar; denetim amacıyla raporda korunur

Raporlar model sonuçları birbirinin üzerine yazılmasın diye
`output/<model>/<pdf-adı>/` klasöründe oluşur:

- `<ad>_terim_raporu.csv`
- `<ad>_terim_raporu.xlsx`
- `<ad>_terms.json`

CSV, Excel ile uyumlu UTF-8 BOM biçimindedir. Satırlar önce karar gerektiren
adayları gösterir: **İnceleme gerekli** ve **Yakın eşleşme** satırları en üstte,
ardından bilgi ve elenen adaylar gelir. `öncelik` ve `önerilen işlem` sütunları
sözlük sorumlusunun hangi satırı ele alacağını açıklar; uygulama sözlüğe otomatik
terim eklemez.

Web arayüzündeki büyük sayı yalnız yüksek güvenli açıkları gösterir. Orta güvenli
adaylar kapalı **İkincil inceleme adayları** bölümünde ve indirilen raporlarda
korunur. Böylece küçük modellerin belirsiz önerileri ana sonucu şişirmez.

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
  kısaltma tanımları ve tekrarlanan teknik öbeklerle geri kazanılır. Bu adaylar
  model kararına ek olarak kaynak ve tekrar sinyalleriyle puanlanır; zayıf cümle
  parçaları ana inceleme listesine alınmaz.
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
BASLAT_APPLE.command   macOS başlatıcısı
BASLAT_WINDOWS.bat     Windows başlatıcısı
run.py                 Kurulumsuz giriş noktası
pyproject.toml         Paket ve bağımlılık tanımı
AI_HANDOFF.md          Yeni yapay zekâ sohbeti için teknik devir notu
```
