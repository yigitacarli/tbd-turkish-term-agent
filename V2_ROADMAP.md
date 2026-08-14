# V2 Yol Haritası

## V2.0 — Güvenli iskelet

- [x] V1'i ayrı dal ve dosya yollarıyla koru.
- [x] Kalıcı proje bağlamı ve karar kaydı oluştur.
- [x] V2 paketini ve ayrı giriş noktasını oluştur.
- [x] Etkin sözlük deposu ve sürüm durumunu oluştur.
- [x] Kaynak PDF içe aktarma, doğrulama ve son sağlam sürüm davranışı ekle.
- [x] Sade makale analiz ekranı ve ayrı sözlük yönetimi ekranı oluştur.
- [x] V1 ve V2 testlerini birlikte doğrula.

## V2.1 — Kalite ölçümü

- [x] İnsan tarafından etiketli kabul kümesi şemasını ve örneğini oluştur.
- [x] Birden fazla V1/V2 raporunu birleştiren iç değerlendirme ekranı ekle.
- [x] 5–10 gerçek makaleden küçük kabul kümesi oluştur.
  - [x] Beş belgede 734 adaylı birleşik iç değerlendirme ve belge bazlı ölçüm.
- [x] Proje sahibi ve yapay zekâ ile doğru terim, sözlükte bulunan, gerçek açık
  ve gürültü etiketlerini `internal_review` statüsünde tamamla.
- [x] V1/V2 hassasiyet, yakalama oranı ve süre karşılaştırma aracı ekle.
- [x] Aynı model adaylarını deterministik olarak yeniden oynatan sürüm
  karşılaştırması ekle.
- [x] Yalnız ölçümle kanıtlanan filtreleri V2 çekirdeğine taşı.
  - [x] `transparency` teknik başını genel İngilizce filtresinden koru; sabit
    snapshot'ta hassasiyet ve yakalamayı geriletmediğini doğrula.
  - [x] Model incelemesinin kabul ettiği iki sözcüklü Title Case teknik kalıpları
    düşük puandan koru; beş sabit snapshot'ta gerilemesiz kazancı doğrula.
  - [x] Model incelemesinin kabul ettiği ve açık kısaltma taşıyan düşük puanlı
    n-gramları koru; beş sabit snapshot'ta gerilemesiz kazancı doğrula.
  - [x] Yalnız model kaynağından gelen, model incelemesinin kabul ettiği düzenli
    tek sözcüklü çoğulları koru; iki bağımsız belgede gerilemesiz kazancı doğrula.
  - [x] En az iki kez geçen çok sözcüklü genel İngilizce öbekleri elenen filtre
    kuralını daralt; beş sabit snapshot'ta açık terim hassasiyeti/yakalamayı
    `%83,2 / %52,3`ten `%84,6 / %57,8`e taşı ve yanlış pozitif artışı olmadığını doğrula.

## V2.2 — Kısaltmalar

- [x] Resmî kısaltmalar kaynağının dosya biçimini doğrula.
- [x] Ayrı kısaltma dizini ve kaynak etiketli eşleşme ekle.
- [x] Açılımı metinde tanımlanmış kısaltmalar için açık karar sınıfı ekle.

## V2.3 — Güvenilir kişisel bilgisayar kullanımı

- [x] Yerel çalıştırmayı güvenli loopback erişimiyle sınırla.
- [x] Aynı anda tek analizle kişisel bilgisayar için güvenli kaynak varsayılanı
  uygula; yoğunlukta açık durum mesajı göster.
- [x] Tek V2 komutuyla sunucuyu ve tarayıcı arayüzünü başlat.
- [ ] Temiz bir kişisel bilgisayar kurulumunda başlangıçtan rapor indirmeye kadar
  uçtan uca kabul deneyi yap.
- [ ] Hedef kişisel bilgisayarda modeli beş belgeli kabul kümesiyle kalite, süre
  ve kaynak kullanımı açısından doğrula.

## İsteğe bağlı sonraki aşama — Kurum sunucusu

- Kurum sunucusu istenirse `DEPLOYMENT_READINESS.md` formunu tamamla.
- HTTPS, kimlik doğrulama, saklama, yedekleme, günlükleme ve eşzamanlılık
  kararlarını yalnız gerçek kurum gereksinimleriyle ekle.

## V2 dışında

- Sözlüğe otomatik Türkçe karşılık ekleme
- Uzman onayı olmadan sözlüğü değiştirme
- Terim salkımlarını ana sözlüğe tekrar ekleme
- OCR (ayrı ürün kararı verilene kadar)
- Kaynağı belirsiz onlarca sözlüğü birleştirme
