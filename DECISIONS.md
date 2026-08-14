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
