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

## V2.4 — Teslim rötuşu (2026-08-19)

- [x] PDF metin çıkarımını düzelt: iki sütunlu düzen, kelime boşluğu toleransı,
      kısmen bitişik satırlar (ADR-037).
- [x] Yerel model çıktı bütçesini bulut sağlayıcıyla eşitle (ADR-037).
- [x] Aday doğrulamasında satır sonu tirelemesi ve tekil/çoğul toleransı
      (ADR-038) — haksız elenen aday 142'den 68'e indi.
- [x] Sıfır aday dönen analizi raporda ve arayüzde uyar (ADR-039).
- [x] Parça başına aday tavanını ölçerek 8'den 16'ya çıkar (ADR-040) —
      eksik terim 997'den 1.849'a çıktı.
- [x] Tek sözcüklü sözlük eşleşmelerini bağlam denetimi için işaretle (ADR-041).
- [x] `docs/DECISIONS.md` başına yürürlük dizini ekle.
- [ ] Uzman etiketli altın küme hazırla ve `evaluate-expected` ile recall/precision
      ölç. **Kalite iddiası için kalan tek eksik budur.**
- [ ] `8_ebpf_xdp_packet_processing.pdf` yerine doğru içerikli PDF koy.

## İsteğe bağlı sonraki aşama — Kurum sunucusu

- Kurum sunucusu istenirse `DEPLOYMENT_READINESS.md` formunu tamamla.
- HTTPS, kimlik doğrulama, saklama, yedekleme, günlükleme ve eşzamanlılık
  kararlarını yalnız gerçek kurum gereksinimleriyle ekle.

## V2 dışında

- Sözlüğe otomatik Türkçe karşılık ekleme
- Uzman onayı olmadan sözlüğü değiştirme
- Terim salkımlarını ana sözlüğe tekrar ekleme
- OCR (ayrı ürün kararı verilene kadar)
