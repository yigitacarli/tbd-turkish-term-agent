# Türkçe Terim Etmeni — Teslim Özeti

**Tarih:** 18 Ağustos 2026 · **Sürüm:** 1.0.0 · **Kurum:** Türkiye Bilişim Derneği,
Bilişimde Özenli Türkçe Çalışma Grubu

---

## Ne yapar

İngilizce bir bilişim makalesi PDF olarak yüklenir. Program makaledeki teknik
terim adaylarını bir yapay zekâ modeliyle çıkarır ve **30.247 kayıtlık TBD
Bilişim Terimleri Sözlüğü** ile karşılaştırır. Uzmanın gördüğü asıl çıktı,
sözlükte bulunmayan ve insan incelemesi gerektiren terimlerdir.

Sonuç, uzmanın Türkçe karşılık önerisini yazabileceği boş sütunlar içeren
2 sekmeli bir Excel dosyası olarak indirilir.

## Kurumsal güvence: kararı yapay zekâ vermez

Bu, ürünün en önemli özelliğidir ve kod düzeyinde garanti altındadır:

- Yapay zekâ modeline sözlük verilmez ve "bu terim sözlükte var mı?" diye
  sorulmaz. Model yalnızca **aday terim** üretir.
- Sözlükte bulunma kararını deterministik Python kodu verir; aynı girdi her
  zaman aynı sonucu üretir.
- Program sözlüğe kendiliğinden terim **eklemez**. Son karar TBD çalışma
  grubundaki uzmanlara aittir.
- Model veya bağlantı hatası olursa sonuç "0 eksik terim" olarak
  **gösterilmez**; açık bir hata ekranı çıkar ve rapor dosyası üretilmez.

## Doğrulanmış durum

| Ölçüt | Değer |
|---|---|
| Otomatik test | 86 test, tamamı geçiyor |
| Sözlük | 30.247 kayıt · 28.492 benzersiz terim (sürüm 2026-07-20) |
| Kısaltma kaynağı | 1.199 resmî TBD kısaltması, ana sözlükten ayrı |
| Canlı kıyaslama | 6 ileri makale · 224 sayfa · 232 metin parçası · 321 saniye |
| Çıktı biçimleri | Excel (.xlsx), CSV, JSON |
| Desteklenen sağlayıcılar | Google Gemini, DeepSeek, OpenAI, Anthropic, yerel Ollama |

Kıyaslamada 6 makale (DeepSeek-R1, Stable Diffusion, Google Spanner, Kademlia,
Rowhammer, Kuantum Yüzey Kodları) uçtan uca taranmış, hiçbir parça kaybı
yaşanmamıştır. Ortalama hız sayfa başına yaklaşık **1,4 saniye**.

## Nasıl çalıştırılır

Kullanıcının teknik bilgisine gerek yoktur:

- **Windows:** `BASLAT_WINDOWS.bat` dosyasına çift tıklanır.
- **macOS:** `BASLAT_APPLE.command` dosyasına çift tıklanır.

Program tarayıcıda otomatik açılır. Yalnızca kullanıcının kendi bilgisayarında
çalışır; dışarıdan erişime kapalıdır.

**Kurulum gereksinimi:** Python 3.9+ ve iki kütüphane (`pdfplumber`, `openpyxl`).
Temiz bir bilgisayarda önce `pip install -e .` komutu çalıştırılmalıdır.

## Maliyet

Bulut sağlayıcı kullanıldığında maliyet, taranan sayfa sayısına göre oluşur
(sayfa başına bir model çağrısı). Yerel Ollama seçilirse maliyet sıfırdır ve
belge cihazdan hiç çıkmaz. API anahtarı kullanıcının kendi hesabına aittir ve
yalnızca kendi bilgisayarındaki dosyada saklanır.

## Tamamlanmamış işler

Bunlar bilinerek bu sürümün dışında bırakılmıştır:

1. **Ağ erişimi açılmadan önce güvenlik katmanı gerekir.** Program şu anda
   yalnızca kullanıcının kendi bilgisayarında çalışacak biçimde tasarlanmıştır.
   Kurum ağına veya internete açılması istenirse önce HTTPS, kimlik doğrulama
   ve çapraz-köken koruması eklenmelidir.
2. **Uzun belgelerde ilerleme göstergesi yoktur.** 200 sayfanın üzerindeki
   belgelerde işlem birkaç dakika sürer ve bu sırada ekranda yalnızca bekleme
   mesajı görünür; iptal veya kaldığı yerden devam seçeneği yoktur.
3. **Kalite ölçümü için uzman etiketli veri gerekir.** Sistemin kaç doğru terim
   yakaladığını sayısal olarak raporlamak için 3 makalelik uzmanca işaretlenmiş
   bir "altın küme" hazırlanmalıdır. Ölçüm altyapısı hazırdır, eksik olan
   yalnızca etiketli veridir.
4. **Kurum sunucusu kararları verilmemiştir.** `docs/DEPLOYMENT_READINESS.md`
   içindeki form, kurumun donanım, erişim ve belge saklama politikası
   netleştiğinde doldurulmalıdır.

Teknik ayrıntılar ve bilinen sınırlamaların tam listesi
`docs/AI_HANDOFF.md` içindedir.

## Önerilen sonraki adım

Program bugünkü hâliyle kişisel bilgisayarda kullanıma hazırdır. Önerilen ilk
iş, bir uzmanın kendi bilgisayarında baştan sona bir kabul denemesi yapması
(kurulum → makale yükleme → Excel indirme) ve sonucun çalışma grubunda
değerlendirilmesidir.

---

*Bu yazılım Prof. Dr. Tuncer Ören'in öncülük ettiği Türkçe terim bilinci
doğrultusunda, TBD Bilişimde Özenli Türkçe Çalışma Grubu için geliştirilmiştir.*
