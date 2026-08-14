# V2 Yol Haritası

## V2.0 — Güvenli iskelet

- [x] V1'i ayrı dal ve dosya yollarıyla koru.
- [x] Kalıcı proje bağlamı ve karar kaydı oluştur.
- [x] V2 paketini ve ayrı giriş noktasını oluştur.
- [x] Etkin sözlük deposu ve sürüm durumunu oluştur.
- [x] Kaynak PDF içe aktarma, doğrulama ve son sağlam sürüm davranışı ekle.
- [x] Sade makale analiz ekranı ve ayrı sözlük yönetimi ekranı oluştur.
- [x] V1 ve V2 testlerini birlikte doğrula.

## V2.1 — Sade tek-geçişli işlem hattı (ADR-028)

- [x] Eski aday filtre yığınını ve çevrimdışı replay katmanını kaldır.
- [x] `PDF → chunk → LLM çıkarımı (few-shot) → normalizasyon → sözlük arama → eksik terimler`
      hattını kur.
- [x] LLM'in yalnızca aday üretmesini, sözlük kararını deterministik katmana bırakmasını sağla.
- [x] Normalize edilmiş anahtar üzerinden kesin sözlük eşleşmesi (`FOUND`/`NOT_FOUND`).
- [x] Metinde geçmeyen model çıktılarını (halüsinasyon) rapora alma.
- [x] Bulut API sağlayıcısını (OpenAI/DeepSeek/Anthropic/Google) ve yerel Ollama'yı
      anahtar varlığına göre otomatik seç.
- [x] Arayüzden iç değerlendirme sayfasını ve `evaluate`/`prepare-acceptance`
      komutlarını kaldır.
- [x] Basit beklenen-terim ölçümü ekle: `evaluate-expected`.

## V2.2 — Kısaltmalar

- [x] Resmî kısaltmalar kaynağının dosya biçimini doğrula.
- [x] Ayrı kısaltma dizini ve kaynak etiketli eşleşme ekle.

## V2.3 — Güvenilir kişisel bilgisayar kullanımı

- [x] Yerel çalıştırmayı güvenli loopback erişimiyle sınırla.
- [x] Aynı anda tek analizle kişisel bilgisayar için güvenli kaynak varsayılanı uygula.
- [x] Tek V2 komutuyla sunucuyu ve tarayıcı arayüzünü başlat.
- [ ] Temiz bir kişisel bilgisayar kurulumunda başlangıçtan rapor indirmeye kadar
      uçtan uca kabul deneyi yap.

## İsteğe bağlı sonraki aşama — Kurum sunucusu

- Kurum sunucusu istenirse `DEPLOYMENT_READINESS.md` formunu tamamla.
- HTTPS, kimlik doğrulama, saklama, yedekleme, günlükleme ve eşzamanlılık
  kararlarını yalnız gerçek kurum gereksinimleriyle ekle.

## V2 dışında

- Sözlüğe otomatik Türkçe karşılık ekleme
- Uzman onayı olmadan sözlüğü değiştirme
- Terim salkımlarını ana sözlüğe tekrar ekleme
- OCR (ayrı ürün kararı verilene kadar)
