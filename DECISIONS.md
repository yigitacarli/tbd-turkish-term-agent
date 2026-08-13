# Mimari ve Ürün Kararları

Bu kayıt append-only mantığıyla kullanılmalıdır. Eski karar silinmez; değişirse
`Yerine geçen karar` alanıyla yeni bir kayıt eklenir.

## ADR-001 — V1'i koruyarak yan yana V2 geliştirme

- Tarih: 2026-08-13
- Durum: Kabul edildi
- Karar: V1 `src/terim_etmeni` ve `run.py` altında korunacak. V2 ayrı
  `src/terim_etmeni_v2` paketi, `run_v2.py`, `tests_v2` ve `output_v2` alanını
  kullanacak.
- Gerekçe: Birden fazla geliştirici/yapay zekâ tarafından yapılan eklemelerin
  çalışan sürümü bozmasını ve geçmişin kaybolmasını önlemek.

## ADR-002 — Hibrit ve modelden bağımsız analiz

- Tarih: 2026-08-13
- Durum: Kabul edildi
- Karar: Yerel Ollama başlangıç model sağlayıcısıdır. Model yalnız aday üretir;
  sözlük kararı deterministik katmandadır. Sağlayıcı arayüzü ileride başka kurum
  modellerine izin verecek şekilde sınırlı tutulur.
- Gerekçe: Teknik terim çıkarımı dilsel değerlendirme gerektirir; sözlük üyeliği
  ise kesin ve tekrarlanabilir olmalıdır.

## ADR-003 — JSON çalışma biçimi, PDF/Excel kaynak biçimi

- Tarih: 2026-08-13
- Durum: Kabul edildi
- Karar: Analiz motorunun etkin sözlüğü doğrulanmış JSON'dur. PDF ve ileride Excel,
  JSON üretmek için içe aktarma biçimleridir; Excel zorunlu değildir.
- Gerekçe: JSON hızlı ve kararlı çalışma biçimidir. Kaynak dosya biçimi sonuç
  semantiğini değiştirmemelidir.

## ADR-004 — Doğrulamasız otomatik sözlük etkinleştirmeme

- Tarih: 2026-08-13
- Durum: Kabul edildi
- Karar: Uzak kaynak değiştiğinde dosya geçici alana alınır, dönüştürülür,
  doğrulanır ve yalnız bundan sonra atomik olarak etkinleştirilir. Başarısızlıkta
  son sağlam sürüm kullanılmaya devam eder.
- Gerekçe: Site veya PDF düzeni değiştiğinde sessiz veri kaybı, eski sözlük
  kullanmaktan daha tehlikelidir.

## ADR-005 — Kısaltmaları kaynak olarak ayrı tutma

- Tarih: 2026-08-13
- Durum: Kabul edildi
- Karar: Ana terim sözlüğü ve kısaltmalar sözlüğü aynı kaynağa körlemesine
  birleştirilmez. Sonuç hangi kaynakta eşleştiğini saklar.
- Gerekçe: `NLP`, `CISO` gibi kısaltmaların açılım ve karşılık ilişkisi normal
  terim eşleşmesinden farklıdır.

## ADR-006 — V2 kalite kapısı

- Tarih: 2026-08-13
- Durum: Kabul edildi
- Karar: V2, V1'den daha iyi ilan edilmeden önce uzman etiketli küçük bir gerçek
  makale kabul kümesinde hassasiyet, yakalama oranı, çalışma süresi ve başarısız
  analiz davranışı karşılaştırılacaktır.
- Gerekçe: Birim testleri modelin gerçek makaledeki kalitesini kanıtlamaz.

