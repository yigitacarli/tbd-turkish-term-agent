# Mimari ve Ürün Kararları

Bu kayıt append-only mantığıyla kullanılmalıdır. Eski karar silinmez; değişirse
`Yerine geçen karar` alanıyla yeni bir kayıt eklenir.

## Yürürlük dizini (2026-08-19)

Kayıtların yarısı bugün çalışmayan bir mimariye aittir. Aşağıdaki ayrım
okuyanın hangi kuralın bağlayıcı olduğunu görmesi içindir; **hiçbir kayıt
silinmemiştir**.

**Yürürlükte olmayan kararlar (tarihsel kayıt).** Bunlar kaldırılmış "V2 / replay"
işlem hattına aittir: `run_v2.py`, `src/terim_etmeni_v2`, `evaluation/`,
`data/v2_runtime/` ve aday anlık görüntüsü katmanı bugün depoda yoktur.

- **ADR-001** — V1/V2 ayrı paket düzeni → ADR-030 ile tek pakete birleştirildi.
- **ADR-006, ADR-007, ADR-008, ADR-009, ADR-010, ADR-011** — V2 kalite kapısı,
  kabul kümesi ve iç değerlendirme süreci → ADR-029 iç değerlendirmeyi,
  `evaluate` ve `prepare-acceptance` komutlarını kaldırdı.
- **ADR-012, ADR-013, ADR-014, ADR-015, ADR-016, ADR-017, ADR-018, ADR-019,
  ADR-025** — replay anlık görüntüsü ve aday koruma filtreleri → ADR-028 ile
  açıkça yürürlükten kaldırıldı.
- **ADR-031'in "en fazla sekiz aday" hükmü** → ADR-040 ile 16'ya çıkarıldı.
  ADR-031'in zorunlu JSON ve kapalı düşünme modu hükümleri yürürlüktedir.
- **ADR-036** — 6 makalelik kıyaslama; dayandığı `data/live_benchmarks/` verisi
  artık depoda yoktur. Bugün doğrulanabilir ölçüm 14 makalelik koşudur
  (`docs/AI_HANDOFF.md`, 2026-08-19).

**Ürünün taşıyıcı kararları.** Bunlar değiştirilmeden önce mutlaka tartışılmalıdır;
teslim belgesindeki kurumsal güvenceler bunlara dayanır.

- **ADR-002 + ADR-028** — Model yalnızca aday üretir; sözlük üyeliği kararını
  deterministik Python kodu verir ve aday filtre yığını kurulmaz.
- **ADR-004** — Doğrulanmamış sözlük etkinleştirilmez.
- **ADR-005 + ADR-020** — Kısaltmalar ana sözlüğe birleştirilmez.
- **ADR-021** — Aynı anda tek analiz (`MAX_CONCURRENT_ANALYSES`).
- **ADR-022** — Yalnızca loopback erişimi.
- **ADR-030** — Tek paket, tek giriş noktası.

Kalan kayıtlar (ADR-003, 023, 024, 026, 027, 029, 032, 033, 034, 035, 037, 038,
039, 040, 041, 042) yürürlüktedir.

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
- Yerine geçen karar: İlk V2 kalite kapısındaki etiketleyici için ADR-008.

## ADR-007 — Kabul kümesini çevrimdışı ve aday birleşimi üzerinde ölçme

- Tarih: 2026-08-13
- Durum: Kabul edildi
- Karar: V1/V2 kalite karşılaştırması canlı model çağrısını ölçüm aracının içine
  gömmeyecek. Aynı gerçek makalelerden önceden üretilmiş JSON raporları ile insan
  tarafından etiketli kabul kümesi çevrimdışı karşılaştırılacak. Etiketleme, iki sistemin
  aday birleşimini kapsayacak; etiketlenmemiş tahminler yanlış pozitif olarak
  görünür kalacak.
- Gerekçe: Aynı kabul kümesini tekrarlanabilir biçimde değerlendirmek, yerel
  model çağrı maliyetini ayırmak ve yarım etiketli veriden yanıltıcı hassasiyet
  sonucu çıkmasını önlemek.

## ADR-008 — İlk kabul kümesini iç değerlendirme olarak hazırlama

- Tarih: 2026-08-13
- Durum: Kabul edildi
- Karar: Erişilebilir alan uzmanı bulunmadığı için ilk gerçek makale kabul kümesi
  proje sahibi ve yapay zekâ tarafından birlikte etiketlenecek. Kayıt
  `internal_review` statüsünü taşıyacak ve uzman onayı gibi sunulmayacak. İleride
  bağımsız alan uzmanı erişimi oluşursa aynı küme yeniden doğrulanabilir.
- Gerekçe: Ölçümsüz filtre geliştirmesine devam etmemek, buna karşılık mevcut
  değerlendirmenin kanıt düzeyini açık ve dürüst biçimde sınırlamak.

## ADR-009 — Onaysız iç taslağı kalite ölçümüne almama

- Tarih: 2026-08-13
- Durum: Kabul edildi
- Karar: Yapay zekânın ilk bağlam incelemesi `internal_draft` statüsünde
  saklanacak. Proje sahibinin orta güvenli kararları incelemesinden önce
  `evaluate` komutu bu dosyayı kabul etmeyecek. Onaylanan dosya
  `internal_review` statüsüne geçirilecek.
- Gerekçe: Yapay zekâ etiketlerini kendi ürettiği sistem davranışının bağımsız
  kalite kanıtı gibi göstermemek.

## ADR-010 — Aynı çekirdeğin ayrı model koşularını sürüm üstünlüğü saymama

- Tarih: 2026-08-13
- Durum: Kabul edildi
- Karar: V2, V1'in `analyze_pdf` çekirdeğini kullandığı sürece ayrı zamanlarda
  üretilmiş yerel model raporları arasındaki fark V1/V2 algoritma üstünlüğü
  olarak yorumlanmayacak. Bu raporlar kabul kümesini ve tekrar kararlılığını
  ölçmek için kullanılabilir. Bir filtre değişikliğinin etkisi, aynı kayıtlı
  model adayları üzerinde deterministik olarak veya yeterli tekrarlı koşuyla
  karşılaştırılacaktır.
- Gerekçe: `temperature: 0` kullanılsa bile ayrı yerel model koşuları farklı aday
  kümeleri üretebilir; aynı analiz çekirdeğindeki bu oynaklık sürüm etkisiyle
  karıştırılmamalıdır.

## ADR-011 — MacBook geliştirmesinde Qwen 3.5 ile sınırlı ölçüm

- Tarih: 2026-08-13
- Durum: Kabul edildi
- Karar: Mevcut MacBook geliştirme ve kabul ölçümlerinde pratik model kapsamı
  `qwen3.5:2b`, gerektiğinde `qwen3.5:4b` olacaktır. Ürün kodu yine belirli bir
  modele sabitlenmeyecek. Geçmiş Gemma ve Granite denemelerinde Qwen daha iyi
  gözlenmiştir; bu gözlem mevcut beş makalelik kabul kümesinde ölçülmediği için
  kesin model sıralaması olarak sunulmayacaktır.
- Gerekçe: Yerel donanımda daha fazla veya daha büyük model denemesi süre ve ısı
  maliyetini gereksiz artırır. Kalite geliştirmesi önce sabit Qwen adaylarını
  çevrimdışı yeniden oynatarak yapılabilir.

## ADR-012 — Model aday anlık görüntüsünü çevrimdışı yeniden oynatma

- Tarih: 2026-08-13
- Durum: Kabul edildi
- Yerine geçen karar: ADR-028
- Karar: Yeni V2 analizleri temizlenmiş PDF sayfalarını, doğrulanmış adayları,
  aday kaynaklarını, kanıt sayılarını ve teknik model incelemesini ayrı bir
  `candidate_snapshot` JSON dosyasında saklayacak. Filtre ve sözlük kararları bu
  dosyadan Ollama çağrısı yapılmadan yeniden üretilebilecek.
- Gerekçe: Aynı model koşusunu sabitlemek, model oynaklığını filtre etkisinden
  ayırır ve MacBook'ta tekrar çağrı maliyetini azaltır.

## ADR-013 — Transparency teknik başını genel İngilizce filtresinden koruma

- Tarih: 2026-08-13
- Durum: Kabul edildi
- Karar: V2 replay politikasında 2–3 sözcüklü ve `transparency` ile biten adaylar
  genel İngilizce sözcük filtresinden otomatik elenmeyecek. Mevcut kanıt puanı ve
  sabit teknik model incelemesi uygulanmaya devam edecek; bu nedenle her
  transparency öbeği otomatik kabul edilmeyecek.
- Gerekçe: Sabit `distributed-systems-compendium` snapshot ölçümünde gerçek açık
  hassasiyeti `%94,1`den `%94,7`ye, yakalama `%61,5`ten `%69,2`ye ve kesin etiket
  doğruluğu `%89,6`dan `%91,1`e yükseldi; gürültü eleme oranı değişmedi.

## ADR-014 — İncelenmiş iki sözcüklü Title Case teknik kalıpları koruma

- Tarih: 2026-08-13
- Durum: Kabul edildi
- Karar: V2 replay politikasında yalnız `technical_pattern` kaynağı taşıyan,
  sabit teknik model incelemesinde kabul edilmiş ve tam iki sözcüğünün de ilk
  harfi büyük olan adaylar düşük inceleme puanı nedeniyle elenmeyecek. Daha geniş
  `technical_pattern + model accepted` kuralı uygulanmayacak.
- Gerekçe: Sabit `distributed-systems-compendium` ve `bitcoin-whitepaper`
  snapshot'larındaki 228 etikette `Asymmetric Encryption`,
  `Symmetric Encryption` ve `Merkle Tree` geri kazanıldı. Gerçek açık
  hassasiyeti/yakalama `%75,0 / %61,1`den `%76,6 / %66,7`ye, kesin etiket
  doğruluğu `%83,3`ten `%84,7`ye çıktı; yanlış pozitif ve gürültü eleme değişmedi.
  Büyük harf şartı kaldırıldığında iki gürültü de kabul edileceğinden geniş kural
  aşırı filtreleme riski taşır.

## ADR-015 — Title Case filtresini üçüncü snapshot ile doğrulama

- Tarih: 2026-08-13
- Durum: Kabul edildi
- Karar: ADR-014 korunacak. `intrusion-detection-systems-survey` üçüncü sabit
  snapshot olarak ölçüme eklendi. Bu belgede kural hiçbir sınıfı değiştirmedi;
  üç snapshot'ta yanlış pozitif artışı veya gerileme görülmedi.
- Gerekçe: 426 etikette gerçek açık hassasiyeti/yakalama `%75,0 / %43,3`ten
  `%76,2 / %46,2`ye ve kesin etiket doğruluğu `%79,3`ten `%80,0`a çıktı.
  Kısaltmalı düşük puanlı n-gram adayında sayısal kazanç görülse de üç kazanımın
  tamamı IDS belgesinden geldiğinden bu ayrı kural tek belgeye aşırı uyum riskiyle
  ertelendi.

## ADR-016 — Title Case filtresini dördüncü snapshot ile doğrulama

- Tarih: 2026-08-13
- Durum: Kabul edildi
- Karar: ADR-014 korunacak. `google-file-system` dördüncü sabit snapshot olarak
  ölçüme eklendi. Bu belgede mevcut iki V2 kuralı hiçbir sınıfı değiştirmedi;
  dört snapshot'ta yanlış pozitif artışı veya gerileme görülmedi.
- Gerekçe: 608 etikette gerçek açık hassasiyeti/yakalama `%77,3 / %38,2`den
  `%78,0 / %39,9`a ve kesin etiket doğruluğu `%73,7`den `%74,2`ye çıktı. Düşük
  puanlı model-kabul adaylarında belgeler arası yeni güvenli desen bulunmadı;
  kısaltmalı n-gram kuralı yalnız IDS belgesindeki örneklere dayandığı için
  ertelenmiş kalır.

## ADR-017 — İncelenmiş kısaltmalı n-gramları düşük puandan koruma

- Tarih: 2026-08-13
- Durum: Kabul edildi
- Karar: V2 replay politikasında yalnız `ngram_scan` kaynağı taşıyan, sabit
  teknik model incelemesinde kabul edilmiş ve en az bir iki-harfli büyük harf
  kısaltması içeren adaylar düşük inceleme puanı nedeniyle elenmeyecek. Genel
  n-gram veya genel kısaltma kurtarması yapılmayacak.
- Gerekçe: Beş sabit snapshot ve 734 etikette `network-based IDS`, `SNMP trap`,
  `switch SPAN port` ve `GPS masters` geri kazanıldı. Gerçek açık
  hassasiyeti/yakalama `%82,3 / %48,9`dan `%82,8 / %50,6`ya, kesin etiket
  doğruluğu `%75,5`ten `%76,0`a çıktı; yanlış pozitif ve gürültü eleme değişmedi.
  İlk üç terim IDS, dördüncü terim Spanner belgesinden geldiği için desen artık
  iki bağımsız belgede desteklenmektedir.

## ADR-018 — Beş snapshot üzerinde birleşik V2 replay kalite kapısı

- Tarih: 2026-08-13
- Durum: Kabul edildi
- Yerine geçen karar: ADR-028
- Karar: ADR-013, ADR-014 ve ADR-017 ile kabul edilen üç dar replay kuralı beş
  sabit `qwen3.5:2b` snapshot üzerinde birlikte korunacak. Yeni filtreler bu
  birleşik taban ölçülmeden eklenmeyecek.
- Gerekçe: Beş makale ve 734 etikette filtreler öncesi tabana göre gerçek açık
  hassasiyeti/yakalama `%81,6 / %46,8`den `%82,8 / %50,6`ya, teknik terim
  hassasiyeti/yakalama `%90,4 / %79,2`den `%90,6 / %80,7`ye ve kesin etiket
  doğruluğu `%74,8`den `%76,0`a çıktı. Gürültü eleme değişmedi ve yanlış pozitif
  artışı görülmedi.

## ADR-019 — İncelenmiş tek sözcüklü model çoğullarını koruma

- Tarih: 2026-08-13
- Durum: Kabul edildi
- Karar: V2 replay politikasında yalnız `model` kaynağı taşıyan, sabit teknik
  model incelemesinde kabul edilmiş, küçük harfli tek ASCII sözcükten oluşan ve
  sözlük katmanındaki düzenli çoğul sonlandırma koşulunu sağlayan adaylar düşük
  inceleme puanı nedeniyle elenmeyecek. N-gramlar, çok sözcüklü adaylar ve modelce
  reddedilen çoğullar bu kuralla korunmayacak.
- Gerekçe: Beş sabit snapshot ve 734 etikette IDS belgesindeki `rulesets` ile
  Spanner belgesindeki `accessors` geri kazanıldı. Gerçek açık
  hassasiyeti/yakalama `%82,8 / %50,6`dan `%83,0 / %51,5`e, teknik terim
  hassasiyeti/yakalama `%90,6 / %80,7`den `%90,6 / %81,0`a ve kesin etiket
  doğruluğu `%76,0`dan `%76,3`e çıktı; yanlış pozitif ve gürültü eleme değişmedi.
  İki terim iki bağımsız belgeden gelse de örnek sayısı düşüktür; yeni snapshotlar
  bu çoğul sezgisinin aşırı uyum riskini ayrıca izlemelidir. Dört dar V2 kuralının
  filtreler öncesi ortak tabana göre birleşik ölçümü
  `evaluation/five_snapshot_current_v2_policy_experiment.json` içindedir.

## ADR-020 — Resmî kısaltmaları ayrı kaynak ve olası eşleşme olarak kullanma

- Tarih: 2026-08-13
- Durum: Kabul edildi
- Karar: TBD Bilişim Kısaltmaları Sözlüğü ana terim sözlüğüne birleştirilmeyecek.
  Resmî sayfanın gömdüğü `2025-03-17` tarihli PDF koordinat ve yazı tipi bilgisiyle
  doğrulanmış ayrı JSON dizinine dönüştürülecek. Aynı kısaltmanın farklı açılımları
  korunacak. Belgede `uzun ad (KISALTMA)` biçiminde tanımlanan açılım resmî kayıtla
  uyuşursa `defined_abbreviation`, tanım yoksa `abbreviation_source` türüyle
  `possible_matches` grubunda ve `match_source=tbd_abbreviations` etiketiyle
  gösterilecek; kesin ana-sözlük eşleşmesi sayılmayacak.
- Gerekçe: Kaynak PDF 52 sayfa, metin katmanlı ve Excel üretimidir. Başlık 1.215
  kısaltma beyan ederken 1.199 eksiksiz satır ve 1.020 benzersiz kısaltma
  okunmaktadır; 16 satırlık `%1,32` fark metadata'da görünür tutulur. Beş snapshot
  replayinde yalnız `NoSQL`, ana sözlük açığından kısaltma kaynağındaki olası
  eşleşmeye taşındı. Teknik terim hassasiyeti/yakalama değişmedi; ana sözlük açığı
  yakalama oranı `%51,5`ten `%51,1`e indi. Bu düşüş filtre kaybı değil, ayrı kaynak
  kapsamının bilinçli sınıf değişimidir; kabul kümesi otomatik yeniden etiketlenmedi.
  Kanıt `evaluation/five_snapshot_abbreviation_source_experiment.json` içindedir.

## ADR-021 — Sunucu kapasitesi ölçülene kadar tek eşzamanlı analiz

- Tarih: 2026-08-13
- Durum: Kabul edildi
- Karar: V2 web hizmeti varsayılan olarak aynı anda yalnız bir PDF analizi
  çalıştıracak. Kapasite doluyken yeni analiz bekletilmeyecek; kullanıcıya açık
  bir yoğunluk mesajı ve HTTP 503 durumu döndürülecek. Hedef sunucuda kabul
  kümesiyle kaynak kullanımı ölçüldükten sonra sınır `MAX_CONCURRENT_ANALYSES`
  ortam değişkeniyle artırılabilir.
- Gerekçe: Mevcut geliştirme sunucusu her isteği ayrı iş parçacığında işlerken
  Ollama analizi yüksek RAM ve işlem yükü oluşturur. Donanım bilinmeden sınırsız
  paralellik seçmek hizmet kararlılığını ve rapor yazım bütünlüğünü riske atar.

## ADR-022 — Kimlik doğrulama ve HTTPS gelene kadar yalnız loopback erişimi

- Tarih: 2026-08-13
- Durum: Kabul edildi
- Karar: V2 geliştirme HTTP sunucusu yalnız `localhost`, `127.0.0.1` veya `::1`
  üzerinde dinleyecek; genel, LAN veya belirsiz ana makine adreslerini
  reddedecek. Yanıtlar temel tarayıcı güvenlik başlıklarını taşıyacak ve
  ayrıntı sızdırmayan `GET /healthz` kontrolü sunulacak. Kurum erişim politikası,
  HTTPS sonlandırma ve kimlik doğrulama seçilmeden uzaktan erişim açılmayacak.
- Gerekçe: Uygulama PDF, değerlendirme ve indirilebilir rapor verisi işler.
  Mevcut geliştirme sunucusunu `0.0.0.0` üzerinde kimlik doğrulamasız çalıştırmak
  bu verileri yetkisiz ağ kullanıcılarına açabilir.

## ADR-023 — Kişisel bilgisayar kullanımını birincil dağıtım hedefi sayma

- Tarih: 2026-08-13
- Durum: Kabul edildi
- Karar: V2'nin birincil teslim hedefi kişisel bilgisayarda yerel Ollama ve
  tarayıcı arayüzüyle sade kullanım olacaktır. Kurum sunucusu kesin hedef
  sayılmayacak; HTTPS, kimlik doğrulama, çok kullanıcılı işletim ve kurumsal
  saklama altyapısı gerçek bir talep oluşana kadar ürün kapsamına eklenmeyecek.
  `python3 run_v2.py` sunucuyu başlatıp tarayıcıyı otomatik açacaktır.
- Gerekçe: Kullanıcının önceliği dağıtım mimarisi değil, PDF içindeki gerçek
  teknik terimleri doğru ve güvenilir biçimde bulmaktır. Belirsiz kurumsal
  gereksinimlere erken yatırım ana ürün kalitesinden uzaklaştırır.

## ADR-024 — Sözlük verisini Git'te düz izlemek, LFS ve geçmiş yeniden yazmayı erteleme

- Tarih: 2026-08-14
- Durum: Kabul edildi
- Karar: Doğrulanmış sözlük JSON'ları (`tbd_dictionary_2026_coordinate.json`,
  `tbd_abbreviations_2025_03_17.json`) ve kaynak PDF Git'te olduğu gibi izlenmeye
  devam edecek. Git LFS eklenmeyecek ve `.git` geçmişini küçültmek için geçmiş
  yeniden yazımı yapılmayacak. Yeni büyük ikili dosyalar (çalışma PDF'leri,
  üretim raporları) zaten `.gitignore` ile dışarıda tutulur.
- Gerekçe: Deponun 133 MB'lık boyutu büyük ölçüde geçmişte eklenip çıkarılan
  PDF'lerden gelir; etkin çalışma verisi yalnızca ~5,5 MB'dır. Tek geliştiricili
  projede geçmiş yeniden yazmak veri kaybı ve push karmaşası riskini, sağladığı
  yer kazancına kıyasla fazla taşır. LFS ayrı bir araç gerektirir ve mevcut
  akışa somut yarar getirmez. Kurum dağıtımı kesinleşirse bu karar yeniden
  değerlendirilir.

## ADR-025 — En az iki kez geçen çok sözcüklü öbeği genel İngilizce filtresinden koruma

- Tarih: 2026-08-14
- Durum: Kabul edildi
- Yerine geçen karar: ADR-028
- Karar: V2 replay politikasında en az iki sözcükten oluşan ve belgede iki veya
  daha fazla kez geçen adaylar, yalnızca genel İngilizce sözcüklerden oluştuğu
  gerekçesiyle elenmeyecek. Tek sözcüklü genel İngilizce adaylar ve yalnızca bir
  kez geçen çok sözcüklü düz yazı parçaları eskisi gibi elenir.
- Gerekçe: `read lock`, `write lock`, `operation log`, `replication factor`,
  `distributed transactions`, `external consistency` gibi gerçek teknik terimler
  sıradan İngilizce sözcüklerden oluşur. Beş sabit snapshot ve 734 etikette bu
  kural 13 gerçek açığı geri kazandı: açık terim hassasiyeti/yakalama
  `%83,2 / %52,3`ten `%84,6 / %57,8`e çıktı; yeni yanlış pozitif oluşmadı.
  Tekil kullanımlı gürültü öbekleri (`client originated requests` vb.) aynı
  eşiğin dışında kaldığı için gürültü eleme oranı değişmedi.

## ADR-026 — OpenAI uyumlu bulut API sağlayıcısını Ollama'nın yanına ekleme

- Tarih: 2026-08-14
- Durum: Kabul edildi
- Karar: V2'ye OpenAI uyumlu `/chat/completions` bitiş noktasını konuşan
  `ApiClient` sağlayıcısı eklendi. `MODEL_PROVIDER=api` ile seçilir; `API_BASE_URL`,
  `API_KEY` ve `API_MODEL` ortam değişkenleriyle yapılandırılır. İstemler ve JSON
  ayrıştırma mantığı `ollama_client` içinden yeniden kullanılır; sağlayıcı yine
  yalnız aday üretir, sözlük üyeliği kararı vermez. Yerel Ollama varsayılan olarak
  kalır; API anahtarı veya adres verilmeden API moduna geçilmez.
- Gerekçe: Belgeler gizli olmadığı için bulut modeli güçlü bir doğruluk kaynağıdır.
  OpenAI, DeepSeek ve birçok sağlayıcı aynı uyumlu biçimi kullandığından tek kod
  birden çok sağlayıcıyı destekler. Yerel küçük modelin (qwen3.5:2b/4b) gerçek
  açık yakalaması ölçümde `%40-46` bandındadır; güçlü API modeli aday kapsamını
  artırır ancak kesin kazanç aynı kabul kümesinde ölçülmeden iddia edilmez.

## ADR-027 — Bulut API ayarlarını arayüzden girmek ve çoklu sağlayıcı desteği

- Tarih: 2026-08-14
- Durum: Kabul edildi
- Karar: Kullanıcı API sağlayıcısını, anahtarını, model adını ve isteğe bağlı
  adresi web arayüzündeki `/settings` sayfasından girer; değerler yerel
  `data/v2_runtime/provider.json` dosyasında saklanır (Git'e eklenmez). Ücreti
  kullanıcı öder; uygulama herhangi bir sağlayıcıyı sabitlemez. `ApiClient`
  OpenAI-uyumlu, Anthropic ve Google (Gemini) olmak üzere dört sağlayıcıyı ortak
  arayüzle destekler; DeepSeek OpenAI-uyumlu varsayılan adresiyle ayrı bir seçenektir.
- Gerekçe: Anahtar ve ücret sorumluluğu kullanıcıya aittir; ortam değişkeni
  düzenlemek hedef kullanıcı için zordur. Arayüzden giriş, profesörün kendi
  sağlayıcısını tek adımda tanımlamasını sağlar. Aynı istem ve JSON ayrıştırma
  mantığı tüm sağlayıcılarda yeniden kullanıldığı için model davranışı sabit kalır.

## ADR-028 — Tek geçişli LLM çıkarımı ve kesin sözlük araması ile sadeleştirme

- Tarih: 2026-08-14
- Durum: Kabul edildi
- Karar: V2 analiz akışı tek ve sade bir hatta indirildi:
  `PDF → chunk → LLM terim çıkarımı (few-shot) → normalizasyon → deterministik
  sözlük araması (kesin eşleşme) → eksik terimler`. LLM'e sözlük verilmez ve
  "sözlükte var mı?" diye sorulmaz; yalnızca teknik terim adayı üretir. Sözlük
  üyeliği, normalize edilmiş İngilizce terimler üzerinden Python `dict` ile kesin
  eşleşmeyle karar verir. Normalizasyon muhafazakârdır (NFKC, küçük harf, tire→boşluk,
  baş/bitiş noktalaması temizleme, boşluk daraltma) ve farklı kavramları birleştirmez.
  Modelin metinde geçmeyen adayları (halüsinasyon) rapora alınmaz. Eski aday filtre
  yığını ve çevrimdışı replay katmanı (`technical_pattern`, `ngram_scan`,
  `quoted_phrase`, genel İngilizce filtresi, metadata/kişi/kıyaslama regex'leri,
  inceleme puanı ve V2 koruma kuralları) ana akıştan kaldırıldı; kısaltma kaynağı
  yalnızca bilgi amaçlı olası eşleşme olarak korundu.
- Gerekçe: Birbirine eklenen POS/n-gram/stopword/TF-IDF benzeri heuristic'ler sonuç
  kalitesini iyileştirmeden karmaşıklığı artırdı. Ölçümler (ADR-026 sonrası) açık
  terim hassasiyeti ve yakalamasının asıl belirleyicisinin model aday kalitesi olduğunu
  gösterdi. Asıl ürün hedefi basit, anlaşılır ve test edilebilir bir akıştır.
- Yerine geçtiği kararlar: ADR-012 (aday anlık görüntüsü/replay), ADR-013, ADR-014,
  ADR-015, ADR-016, ADR-017, ADR-018, ADR-019 (replay koruma filtreleri) ve ADR-025
  (genel İngilizce öbek koruması). Bu kurallar kaldırılan eski işlem hattına aitti.

## ADR-029 — Anahtar varlığına göre sağlayıcı seçimi ve iç değerlendirmenin kaldırılması

- Tarih: 2026-08-14
- Durum: Kabul edildi
- Karar: Sağlayıcı seçimi artık `MODEL_PROVIDER` ortam değişkenine bağlı değildir.
  `MODEL_PROVIDER=api` API'yi, `MODEL_PROVIDER=ollama` yerel modeli zorlar; ayar yoksa
  kayıtlı bir API anahtarı varsa API, yoksa yerel Ollama kullanılır. Anahtar
  `/settings` sayfasından veya `API_PROVIDER`/`API_KEY`/`API_MODEL`/`API_BASE_URL`
  ortam değişkenlerinden okunur; arayüz API modundayken model seçim listesini gizler.
  Ayrıca uzman etiketi olmadan kullanılan **iç değerlendirme** sayfası, `evaluate` ve
  `prepare-acceptance` komutları ve kabul kümesi verileri kaldırıldı; yerine makale
  bazlı basit `evaluate-expected` ölçümü korunur.
- Gerekçe: Kullanıcı anahtar girmesine rağmen sistem hâlâ yerel modeli kullanıyordu;
  sağlayıcı seçimi kullanıcıya görünmez bir ortam değişkenine bağlı kalmamalıdır.
  İç değerlendirme akışı ana ürün hedefi (eksik terimleri bul) için gürültüdür ve
  kaldırılması arayüzü sadeleştirir.

## ADR-030 — Tek pakete birleştirme ve klasör düzeni

- Tarih: 2026-08-14
- Durum: Kabul edildi
- Karar: V1/V2 ayrımı kaldırıldı. Kullanılan V1 parçaları (PDF okuma, parçalama,
  sözlük, Ollama istemcisi, raporlama) ile V2 ürün kodu tek `src/terim_etmeni`
  paketinde birleştirildi; kullanılmayan eski V1 filtre yığını ve çift giriş noktası
  silindi. Tek giriş `run.py`, tek test dizini `tests/`, dokümanlar `docs/` altında,
  çalışma zamanı `data/runtime/` ve `output/` altında toplandı.
- Gerekçe: V1/V2 ikiliği ve çok sayıda dağınık `.md` dosyası projeyi gereksiz
  karmaşıklaştırıyordu. Tek, anlaşılır ve bitirilebilir bir V1 hedefi için düzleştirme.

## ADR-031 — API sağlayıcısında zorunlu JSON ve parça başına aday sınırı

- Tarih: 2026-08-14
- Durum: Kabul edildi
- Karar: OpenAI uyumlu API sağlayıcılarında JSON nesne modu istenir; DeepSeek'te
  düşünme modu kapalı tutulur. Terim çıkarım istemi her PDF parçası için en fazla
  sekiz, belgeye özgü olay veya aktör değil bağımsız sözlük başlığı olabilecek aday
  ister. Bu karar yeni bir regex/heuristic filtresi değildir; modelin tek görevi
  olan aday çıkarımının sözleşmesini daraltır.
- Gerekçe: Gerçek `deepseek-v4-flash` raporlarında Bitcoin belgesinde sekiz parçada
  64 eksik aday ve bağlama özgü ifadeler görülürken, NIST belgesinde 24 parçanın
  21'i boş yanıt vermiş; zero-trust belgesinde 59 parçanın tamamı başarısız olmuştur.
  Önce yapılandırılmış çıktı ve ölçülü aday hacmi güvenceye alınmadan model kalitesi
  hakkında karar verilemez.

## ADR-032 — Deterministik çoğul/morfolojik sözlük eşleme ve JSON ayrıştırma dayanıklılığı

- Tarih: 2026-08-14
- Durum: Kabul edildi
- Karar:
  1. `TermDictionary` sözlük aramasında 2 kademeli deterministik eşleme uygulandı:
     Tam/gevşek eşleşme ve tekil/çoğul normalizasyonu (`singular_key`). Sözlükte tekili
     bulunan çoğul terimler (`transactions` -> `transaction`, `public keys` -> `public key`)
     `found_in_dictionary = True` ve `match_type = "singular_variant"` olarak işaretlenip
     doğrudan sözlükte bulunanlar grubuna aktarıldı.
  2. Eksik terim adaylarında aynı kavramın tekil ve çoğul varyantları (`downstream task` ve
     `downstream tasks`) tek bir kanonik madde altında birleştirildi; geçiş ve sayfa bilgileri
     harmanlandı.
  3. `_json_from_text` ayrıştırıcısı Markdown kod bloklarını (` ```json `), nesne dışı
     metinleri, ham listeleri (`[...]`) ve trailing comma hatalarını kurtaracak biçimde
     kurşungeçirmez hale getirildi; `ApiClient` varsayılan `max_tokens` değeri 1024'e çıkarıldı.
- Gerekçe: Sözlükte tekili bulunan çoğul kelimelerin eksik terimler listesine düşmesi sahte
  eksik terim gürültüsünün yaklaşık %30'unu oluşturuyordu. Bu deterministik adımla sözlük
  eşleşmesi morfolojik olarak güçlendirildi ve API yanıtlarındaki JSON kırılganlığı giderildi.

## ADR-033 — Gürültü terimlerini ve kurgusal senaryo aktörlerini eleyen istem optimizasyonu

- Tarih: 2026-08-14
- Durum: Kabul edildi
- Karar: `SYSTEM_PROMPT` ve `USER_TASK` istemleri 3 ana gürültü kategorisini kesin olarak dışlayacak
  biçimde yapılandırıldı:
  1. **Kurgusal/Senaryo Rolleri:** Oyun teorisi, protokol analizi veya düşünce deneylerine özgü kurgusal
     roller (`honest nodes`, `attacker chain`, `honest blocks`, `attacker node`, `malicious peer`, `victim`)
     evrensel bilişim sözlük başlığı olmadıkları için kesin olarak dışlandı.
  2. **Sıradan Tekil Kelimeler:** Bilişim literatürüne özgü bir standart/ilkel (`mutex`, `semaphore`, `nonce`,
     `hypervisor`) olmadıkça genel dilden, ekonomiden veya yönetimden gelen tekil sözcüklerin (`incentive`,
     `acting`, `dependencies`, `causality`, `tools`, `seeds`, `mint`, `cost`, `rules`) çıkarımı yasaklandı.
  3. **Tanımlayıcı Cümle Parçaları:** Yazarın konuyu açıklarken kurduğu n-gram veya tanım parçaları
     (`chain of digital signatures`, `public history of transactions`, `block broadcasts`) yerine yalnızca
     standart teknik terimin (`digital signature`, `transaction`) çıkarılması kurala bağlandı.
  4. **Bölüm Başlıkları ve Metrikler:** Bölüm/paragraf başlıkları (`6. Incentive`, `8. Calculations`) ve
     deneysel metrikler (`99.9th percentile`, `BLEU`) kesin dışlamalar arasına alındı.
- Gerekçe: Bitcoin ve benzeri akademik makalelerde eksik terimler listesinde beliren sahte kavramların
  büyük kısmı makaleye özgü kurgusal rollerden ve genel dilden gelen sıradan kelimelerden kaynaklanıyordu.
  İstemin bu kurallarla netleştirilmesi, modelin yalnızca bağımsız bir bilişim sözlüğü başlığı olabilecek
  kavramlara odaklanmasını sağlar.

## ADR-034 — Web rotası esnekliği, Excel XML karakter sanitizasyonu ve eşzamanlılık güvencesi

- Tarih: 2026-08-15
- Durum: Kabul edildi
- Karar:
  1. **Web Rota Desteği:** `web_app.py` Handler'ı hem web arayüz formlarını hem de standart API rotalarını
     (`/api/analyze`, `/settings`, `/api/dictionary/update`) karşılayacak rota takma adlarını destekleyecek
     biçimde genişletildi.
  2. **Excel XML Karakter Sanitizasyonu:** PDF metin çıkarımından veya LLM çıktılarından gelebilecek
     geçersiz XML kontrol karakterleri (`\x00`–`\x1f`, form-feed `\x0c` vb.) `_clean_str` ve
     `ILLEGAL_CHARACTERS_RE` filtresi ile temizlenerek `openpyxl`'in çökmesi engellendi.
  3. **Eşzamanlılık ve Geçici Dosya Güvencesi:** `MAX_CONCURRENT_ANALYSES = 1` kilidi `analyze_path`
     fonksiyonunu da kapsayacak şekilde eşitlendi; analiz sırasında model hatası veya istisna oluşsa bile
     geçici dosyaların (`tempfile`) `finally` bloğu ile silinmesi ve kilitlerin serbest bırakılması
     testlerle teminat altına alındı.
  4. **Gelişmiş Kaynakça Temizliği:** `clean_extracted_text` kaynakça filtreleme regex'i numaralı
     bölüm başlıklarını (`12. References`, `VIII. References`, `References and Notes` vb.) kapsayacak
     şekilde genişletildi.
- Gerekçe: Güvenlik, veri bütünlüğü ve sistem kararlılığını uçtan uca sağlamak.

## ADR-035 — Düzensiz bilişim çoğulları, Latin/Grek morfolojisi ve Unicode İ normalizasyonu

- Tarih: 2026-08-15
- Durum: Kabul edildi
- Karar:
  1. `dictionary.py` içindeki `singular_key` fonksiyonuna düzensiz bilişim çoğulları haritası
     (`matrices` -> `matrix`, `indices` -> `index`, `vertices` -> `vertex`, `criteria` -> `criterion`,
     `caches` -> `cache`, `buses` -> `bus`, `statuses` -> `status`, `data` -> `datum`, `phenomena` -> `phenomenon`,
     `automata` -> `automaton`, `media` -> `medium`, `spectra` -> `spectrum` vb.) eklendi.
  2. Grek/Latin kökenli `-ses` -> `-sis` kuralı (`analyses` -> `analysis`, `hypotheses` -> `hypothesis`,
     `diagnoses` -> `diagnosis`, `theses` -> `thesis`, `parentheses` -> `parenthesis`) ile TBD sözlüğündeki
     198 terim çoğul sahte eksik terim olmaktan kurtarıldı.
  3. `normalized_key` içinde Türkçe noktalı `İ` karakterinin ASCII `i`ye dönüşümü güvenceye alındı;
     Unicode `_DASHES` sabiti `\u2015` (Horizontal Bar) ile senkronize edildi.

## ADR-036 — Genişletilmiş 6 yeni ileri bilişim makalesi canlı kıyaslama (benchmark) ve stres testi

- Tarih: 2026-08-15
- Durum: Kabul edildi
- Karar: 6 yeni ileri bilişim makalesi (`ai_deepseek_r1_reasoning`, `ai_diffusion_stable_diffusion`,
  `database_spanner_distributed`, `distributed_p2p_kademlia`, `security_hardware_rowhammer`,
  `quantum_surface_codes`) `data/live_benchmarks/` dizinine indirilmiş ve DeepSeek-Chat canlı API'si ile
  tam hat stres testinden geçirilmiştir:
  1. Toplam 224 sayfalık akademik literatür taranmış, 232 metin parçası (chunk) analiz edilmiştir.
  2. Toplam 91 TBD sözlük eşleşmesi (78 tam eşleşme, 13 çoğul varyant eşleşmesi), 4 TBD kısaltması ve
     389 eksik terim adayı tespit edilmiştir.
  3. Tüm makaleler için 2 sekmeli Excel (.xlsx), UTF-8-SIG noktalı virgüllü CSV (.csv) ve JSON (.json)
     raporları `output/deepseek-chat/<makale>/` altında üretilmiş, `openpyxl` ile sekmeler, filtreler ve
     veri bütünlüğü eksiksiz doğrulanmıştır.
  4. Analiz ve kıyaslama özet verileri `data/live_benchmarks/deepseek_expanded_results.json` dosyasına işlenmiştir.
- Gerekçe: Sistemin akıl yürütme LLM'leri (R1), üretken yapay zekâ (Stable Diffusion), dağıtık veritabanları
  ve TrueTime (Spanner), P2P DHT ağları (Kademlia), donanım güvenliği ve DRAM hata enjeksiyonu (Rowhammer)
  ve kuantum hesaplama/hata düzeltme (Surface Codes) gibi çok çeşitli ve modern alanlarda üstün terim
  çıkarma, deterministik sözlük eşleştirme ve raporlama kararlılığını kanıtlamak.

## ADR-037 — İki sütunlu düzen, kelime boşluğu toleransı ve yerel model çıktı bütçesi

- Tarih: 2026-08-19
- Durum: Kabul edildi
- Karar:
  1. `pdf_reader.py` içinde pdfplumber çağrıları `x_tolerance=1.5` ile yapılır.
     Varsayılan `3` değeri akademik yayınların sıkı kernli fontlarında kelime
     boşluğunu kaçırıp kelimeleri birbirine yapıştırıyordu.
  2. İki sütunlu sayfalarda sütunlar ayrı ayrı okunur. Sütun ayracı, sayfanın
     orta bandında hiçbir kelimenin üzerinden geçmediği ve iki yanında da kayda
     değer kelime bulunan x konumu olarak bulunur (`_find_column_gutter`).
  3. Satırın yalnızca bir bölümü bitişikse (28+ harflik kesintisiz dizi) o bölüm
     ayıklanır, satırın okunabilir geri kalanı korunur.
  4. `ollama_client.py` içindeki `num_predict` 256'dan 4096'ya çıkarılıp bulut
     sağlayıcının `max_tokens` değeriyle eşitlendi; `num_ctx=8192` açıkça verilir.
- Gerekçe: Ölçüm — `BSGRJS18` belgesinde ham metin 47.692 karakterden 100.492
  karaktere çıktı (2,19x); örnek makalelerin %2-39'u bitişik kelime olarak
  okunuyordu ve `_is_low_quality_line` bu satırları tümden siliyordu. Yerel model
  ise 256 token bütçesiyle terim listesi JSON'unun ortasında kesiliyor, bu yüzden
  bulut sağlayıcıdan yapısal olarak daha az terim buluyordu.
- Sonuç: Bu düzeltmelerden önce `output/` altına üretilmiş tüm raporlar belgenin
  yalnızca bir bölümünü görmüştür ve model kıyaslaması için kullanılamaz.

## ADR-038 — Aday doğrulamasında satır sonu tirelemesi ve çekim farkına tolerans

- Tarih: 2026-08-19
- Durum: Kabul edildi
- Karar: Bir aday terim metinde birebir bulunamazsa sırasıyla iki deneme daha
  yapılır (`term_extraction.locate_term`):
  1. Satır sonunda tirelenerek bölünmüş sözcükler yalnızca **arama kopyasında**
     birleştirilir (`compu-\ntation` → `computation`). Sayfa metni ve modele giden
     parçalar değişmez.
  2. Terimin son sözcüğünün tekil/çoğul yüzey biçimleri denenir
     (`block cipher` → `block ciphers`). İlk sözcükler hiç değiştirilmez.
  Eşleşme bu yollardan biriyle kurulduysa rapora `matched_form` alanı yazılır;
  geçiş sayısı ve sayfa listesi metinde gerçekten bulunan biçim üzerinden sayılır.
  Hiçbir biçimle bulunamayan aday, önceden olduğu gibi `rejected_candidates`
  listesine düşer ve rapora girmez.
- Gerekçe: Ölçüm — 14 makalelik kümede elenen 130 adayın 70'i (%54) metinde
  gerçekten geçiyordu: 24'ü satır sonu tirelemesi, 46'sı çekim farkı yüzünden
  kaybediliyordu (`block cipher`, `digital signature`, `smart contract` gibi
  gerçek terimler dahil). Kayıp modelden değil eşleştirme katmanından geliyordu.
- Sınır: Bu bir sezgisel filtre değildir; yeni kavram üretmez ve sözlük üyeliği
  kararına dokunmaz (ADR-002 ve ADR-028 korunur). Model tarafından uydurulan
  terimler hâlâ elenir.

## ADR-039 — Sıfır aday dönen analizin sessiz kalmaması

- Tarih: 2026-08-19
- Durum: Kabul edildi
- Karar: Tüm parçalar hatasız işlendiği hâlde model hiç aday döndürmediyse
  `analysis_status` `complete` kalır (analiz gerçekten tamamlanmıştır) ancak
  `processing_warnings` listesine açık bir uyarı yazılır ve web arayüzünde
  "model hiç terim adayı döndürmedi, bu sonuç 'eksik terim yok' anlamına gelmez"
  bildirimi gösterilir.
- Gerekçe: Ölçüm — yerel `qwen3.5:9b-q4_K_M` çalıştırmasında 14 belgenin 5'i
  `candidate_count: 0`, `failed_chunk_count: 0` ve `analysis_status: "complete"`
  ile sonuçlandı; kullanıcıya yalnızca başlık satırından ibaret bir CSV üretildi.
  Bağlantı hatası için var olan koruma (ADR: başarısız analizde rapor yazılmaz)
  bu durumu kapsamıyordu.
- Sınır: Durum kodu bilinçli olarak `failed` yapılmadı; aksi hâlde gerçekten
  terim içermeyen bir belge hata gibi görünür ve raporu hiç üretilmezdi.

## ADR-040 — Parça başına aday tavanını 8'den 16'ya çıkarma

- Tarih: 2026-08-19
- Durum: Kabul edildi
- Yerine geçtiği karar: ADR-031'in yalnızca "en fazla sekiz aday" hükmü.
  ADR-031'in zorunlu JSON ve kapalı düşünme modu hükümleri yürürlüktedir.
- Karar: Terim çıkarım isteminin parça başına istediği en fazla aday sayısı 16
  olarak değiştirildi. Değer `term_extraction.MAX_TERMS_PER_CHUNK` sabitindedir
  ve `MAX_TERMS_PER_CHUNK` ortam değişkeniyle ölçüm için geçici olarak
  değiştirilebilir. Bu bir filtre değişikliği değildir; modelin aday üretim
  sözleşmesinin tavanıdır.
- Gerekçe: ADR-031'in sekizlik tavanı 2026-08-14'te, modelin boş yanıt verdiği
  ve bağlama özgü ifadeler taşıdığı koşullarda konmuştu. O koşulların dördü de
  ortadan kalktı: JSON modu zorunlu (ADR-031), istem gürültü kategorilerini açıkça
  dışlıyor (ADR-033), çıktı bütçesi 4096 token (ADR-037), PDF metni iki kat
  düzgün okunuyor (ADR-037). Ölçüm (3 belge, aynı gün, aynı kod):

  | Belge | Tavan | Aday | Sözlük eşleşmesi | Eksik terim | Elenen (uydurma) oranı |
  |---|---|---|---|---|---|
  | 1_attention | 8 | 73 | 19 | 48 | %2,7 |
  | 1_attention | 16 | 128 | 25 | 93 | %3,1 |
  | 1_attention | 24 | 167 | 29 | 122 | %4,8 |
  | 3_raft | 8 | 77 | 13 | 60 | %2,6 |
  | 3_raft | 16 | 157 | 26 | 117 | %4,5 |
  | 3_raft | 24 | 209 | 32 | 150 | %7,2 |
  | 10_homomorphic | 8 | 129 | 26 | 93 | %3,1 |
  | 10_homomorphic | 16 | 266 | 40 | 193 | %5,6 |

  8 → 16 geçişi aday hacmini yaklaşık ikiye katlarken uydurma oranını yalnızca
  1-2 puan artırıyor. 16 → 24 geçişinde kazanç yarıya inerken uydurma oranı
  tabanın 2,7 katına çıkıyor. Dizin noktası 16'dır.
- Sınır: Tavanın yükselmesi tek sözcüklü genel aday oranını da bir miktar
  artırır (`3_raft`'ta %29,7 → %34,7). Bu adaylar elenmez; rapordaki öncelik
  sütunu ve ADR-041'deki işaret uzmanın ayıklamasını kolaylaştırır.

## ADR-041 — Tek sözcüklü sözlük eşleşmelerini bağlam denetimi için işaretleme

- Tarih: 2026-08-19
- Durum: Kabul edildi
- Karar: Sözlükte tam eşleşen tek sözcüklü terimler rapora
  `context_check_needed` alanıyla yazılır. CSV/Excel'de eşleşme türü
  "Sözlükte Kayıtlı (Tek Sözcük)" olarak gösterilir ve önerilen işlem
  "Karşılığın bağlama uygunluğunu doğrula" olur. **Hiçbir terim gizlenmez veya
  elenmez**; yalnızca sunum değişir.
- Gerekçe: Ölçüm — sözlük eşleşmesi birebir dizgi üzerinden kurulduğu için genel
  sözcükler makaledeki teknik anlamdan farklı bir karşılıkla eşleşebiliyor:
  `attention` → "uyarı" (bir belgede 213 geçiş), `leader` → "öncü",
  `rank` → "sıra", `call` → "çağrı", `page` → "sayfa". Terim gerçekten sözlükte
  kayıtlıdır; yanıltıcı olan, karşılığın bu bağlamda doğruymuş gibi görünmesidir.
- Sınır: Ölçüt tamamen deterministiktir (terim tek sözcük mü?) ve ADR-028'in
  yasakladığı türden bir aday eleme sezgiseli değildir. `nonce`, `blockchain`
  gibi doğru eşleşen tek sözcüklü terimler de işaretlenir; bu bilinçlidir —
  işaret "yanlış" demez, "denetlenmeli" der.

## ADR-042 — Eksik terimlerde kavram bazında birleştirme (belge kanıtlı)

- Tarih: 2026-08-22
- Durum: Kabul edildi
- Karar: Eksik terim tekilleştirmesi üç deterministik anahtarla yapılır:
  1. Tekil/çoğul anahtarı (mevcut, ADR-032).
  2. Ayraç duyarsız sıkıştırılmış anahtar (`condensed_key`): tire ve boşluk
     yazım farkları (`over-fitting` ↔ `overfitting`, `pre-condition` ↔
     `precondition`). Yalnızca ayraç farklılığı kavram ayrımı değildir.
  3. Belge içi kısaltma ↔ açılım eşleri (`document_acronyms`): metinde
     `uzun biçim (KISALTMA)` kalıbında geçen ve baş harfleri birebir
     örtüşen çiftler (`masked language model (MLM)`, `proof of work
     (PoW)`). Eşitlik kararı belgenin kendi tanımına dayanır; modelden
     veya sözlükten bilgi gelmez (ADR-002 korunur).
  Birleşen yüzey biçimleri raporda `variants` alanında korunur; **hiçbir
  terim gizlenmez** (ADR-041 ile aynı sunum ilkesi). Açılım biçimi görünür
  ad olur; yalın kısaltma `variants`'a taşınır.
- Gerekçe: Ölçüm (2026-08-22, internal_draft etiketiyle 14 belgedeki
  1.853 eksik terimin sınıflandırılması) gürültünün %72,5 olduğunu ve
  bunun %8,9'luk diliminin aynı kavramın yinelenen biçimleri olduğunu
  gösterdi. Bu birleştirme filtre değildir: yeni kavram üretmez, terim
  elemez, geçiş sayısı ve sayfa bilgisi harmanlanır.
- Sınır: Anlamsal varyantlar (`masked LM` ↔ `MLM` zincirleri, `BLEU score`
  ↔ `BLEU`, öbek-içi kapsama varyantları) bilinçli olarak birleştirilmez;
  bunlar ADR-028'in yasakladığı türden bir sezgisel eşleşme gerektirir.
- Ölçülen etki (mevcut deepseek-v4-flash koşusu üzerinde simülasyon):
  1.853 → 1.845 satır (-8, %0,4). Etki küçüktür; kaydın amacı bu
  birleştirmenin güvenli üst sınırını dürüstçe belgelemektir. Kalan
  varyant gürültüsü istem tarafı (ADR-033 uzantısı) ve sunum düzeyinde
  gruplama ile ele alınmalıdır.

## ADR-043 — STRICT EXCLUSIONS genişletmesi: özel adlar, metrikler, kod tanımlayıcıları

- Tarih: 2026-08-22
- Durum: Kabul edildi
- Yerine geçtiği karar: ADR-033'ün yalnızca genişletilen maddeleri;
  kalan hükümleri yürürlüktedir.
- Karar: `USER_TASK` içindeki STRICT EXCLUSIONS listesine üç sınıf eklendi:
  1. Belirli yazılım sistemi/araç/kitaplık/ürün/veri kümesi/çerçeve özel
     adları (HElib, SEAL, Docker, TensorFlow, GLUE, SQuAD); genel kavram
     adı varsa onun döndürülmesi istenir.
  2. Değerlendirme metrik adları ve tablo sütunu / şekil altyazısı
     parçaları (validation loss, win rate, BLEU score).
  3. Harf durumu gözetmeksizin kod/protokol tanımlayıcıları: değişken/
     fonksiyon adları, komut mnemonikleri, yapılandırma anahtarları
     (candidateId, commitIndex, i32.add, br_if, warmup_steps).
- Gerekçe: Ölçüm (2026-08-22 taksonomisi) bu üç sınıfın eksik terim
  gürültüsünün ~%16'sı olduğunu gösterdi. Canlı doğrulama: `12_webassembly`
  belgesi üzerinde her istemle ikişer koşum (deepseek-v4-flash). Kararlı
  kümeler karşılaştırıldığında hedeflenen sınıflar çöktü (kod benzeri
  adaylar 18 → 10; özel adlar 26 → 8) ve **net -29 gürültü satırı**
  (listenin ~%13'ü) elde edildi. Gerçek terim dengesi değişmedi: 3 kararlı
  kayıp, 3 farklı kararlı kazanım. Yeni istemle iki koşum birebir aynı
  sonucu verdi (eski istemde jaccard 0,83).
- Sınır: Model uyumu kusursuz değil; yasağa rağmen yeni tek sözcüklü
  genel adaylar girebiliyor. Tek belge derinlemesine + ikinci belgede tek
  çift koşuma dayanır; altın küme oluştuğunda tekrar ölçülmelidir.
  Maliyet: 6 koşumun toplamı birkaç sent.

## ADR-044 — Eksik terimlerde öncelik puanı ve puana göre sıralama

- Tarih: 2026-08-22
- Durum: Kabul edildi
- Yerine geçtiği karar: Önceki kuralın ("çok sözcüklü VEYA 2+ geçiş ->
  yüksek öncelik" davranışı) yerine geçer.
- Karar: Her eksik terim için deterministik bir `priority_score` üretilir:
  çok sözcüklük +2, tek sözcük -1, sıklık 2 geçiş +1 / 3+ geçiş +2.
  Puan bantları: >=2 yüksek, 1 orta, <=0 düşük (`review_priority`).
  Eksik terimler raporda puan azalan, puan eşitliğinde alfabetik dizilir.
- Sınır: Bu yalnızca sunumdur; hiçbir terim listeden çıkarılmaz veya
  Excel'de gizlenmez (ADR-028/041 ilkeleri korunur). Tek sözcükler düşük
  banta düşer ama listede kalır — istem düzeyindeki tek-sözcük caydırması
  bu kararla aşağı akışta "yasak değil, sona at" ilkesine bağlanmıştır.
- Gerekçe: Taksonomi ölçümü (2026-08-22) gürültünün büyük bölümünün tek
  genel sözcükler ve tanımlayıcı öbekler olduğunu gösterdi; eski kural
  ise sık geçen genel tek sözcüğü bile "yüksek öncelik" yapıyordu
  (örn. 'model' ×200). Uzman incelemesinin baştan itibaren gerçek
  adaylara odaklanması için liste sırasının kendisi triyaj aracıdır.
