# Yapay Zekâ / Geliştirici Devir Notu

> **Önce `PROJECT_CONTEXT.md`, `DECISIONS.md` ve `V2_ROADMAP.md` dosyalarını oku.**
> Bu dosya yalnız güncel çalışma durumunu ve pratik komutları taşır. Ürün amacı ve
> kalıcı kararlar yukarıdaki dosyalardadır.

## Güncel çalışma yönü — V2

- V1 korunmuştur: `src/terim_etmeni/`, `run.py`, `tests/`.
- V2 etkin geliştirmedir: `src/terim_etmeni_v2/`, `run_v2.py`, `tests_v2/`.
- V2 dalı: `codex/v2`.
- V1'e yeni V2 özelliği ekleme; geçiş uyumluluğu için V2'nin V1 modüllerini
  içe aktarması kabul edilebilir.
- Sohbet içinde alınan kalıcı bir karar aynı turda `DECISIONS.md` veya
  `PROJECT_CONTEXT.md` içine yazılmalıdır.

### 2026-08-13 V2.0 durumu

- `codex/v2` dalı oluşturuldu; `main` üzerindeki V1 korunuyor.
- V2 etkin sözlük deposu ve `dictionary status/import/check` komutları çalışıyor.
- Gerçek TBD sayfasındaki WordPress PDF Poster yapılandırmasından resmî
  İngilizce–Türkçe PDF bağlantısı bulunuyor.
- Canlı otomatik kontrol, 599 sayfalık 2026-07-20 PDF'sini indirip 30.247 kayıt ve
  28.492 benzersiz İngilizce terim olarak doğruladı ve etkinleştirdi.
- Başarısız ağ/ayrıştırma durumunda son sağlam sözlük korunuyor.
- V2 ana ekranı makale analizini, ayrı `/dictionary` ekranı sözlük yönetimini
  sunuyor. Yerel geliştirme adresi `http://127.0.0.1:8876`.
- Kabul kümesi şeması `evaluation/` altında; `run_v2.py evaluate` önceden
  üretilmiş V1/V2 JSON raporlarında hassasiyet, yakalama oranı, analiz durumu ve
  varsa süre karşılaştırması yapıyor. `prepare-acceptance` iki sistemin aday
  birleşiminden boş insan inceleme şablonu çıkarıyor. Yeni V2 raporları analiz
  süresini kaydediyor.
- Web arayüzündeki `/evaluation` sayfası birden fazla V1/V2 JSON raporunu yükler,
  bütün adayları üç karar sınıfıyla etiketletir ve eksiksiz kümeyi
  `internal_review` statüsünde indirir. Bu çalışma uzman onayı olarak sunulmaz.
- `google-file-system.pdf` iç değerlendirmesi tamamlandı. İlk 134 V2 adayındaki
  10 orta güvenli karar makale bağlamıyla sonuçlandırıldı; ADR-007 gereği V1'e
  özgü 48 aday da eklenerek 182 adayın tümü
  `evaluation/google_file_system_internal_review.json` içinde etiketlendi: 68
  sözlük eşleşmesi, 74 gerçek açık ve 40 gürültü. İlk taslak denetim izi olarak
  korunuyor; çalışma uzman onayı değildir.
- Kabul kümesi beş gerçek makaleye ve 734 birleşik adaya genişletildi:
  `google-file-system`, `bitcoin-whitepaper`, `distributed-systems-compendium`,
  `intrusion-detection-systems-survey` ve `spanner-globally-distributed-database`.
  Birleşik küme `evaluation/five_article_internal_review.json`, toplu sonuç
  `evaluation/five_article_v1_v2_measurement.json`, belge kırılımı
  `evaluation/five_article_document_breakdown.json` içindedir.
- Beş makalelik `qwen3.5:2b` ölçümünde gerçek açık hassasiyet/yakalama oranı
  eski V1 raporlarında `%81,9 / %61,2`, yeni V2 raporlarında `%81,6 / %46,8`;
  teknik terimde sırasıyla `%90,4 / %85,0` ve `%90,4 / %79,2`. Dört yeni V2
  raporunun ortalama süresi `60,95 sn`; eski V1 raporlarında süre alanı yok.
- V2 hâlâ V1'in aynı analiz çekirdeğini içe aktarıyor. İki belgede raporlar
  birebir aynı, diğer farklar ayrı yerel model koşularında oluştu. ADR-010 gereği
  bu sonuç V2 algoritmasının daha kötü ya da daha iyi olduğu kanıtı değildir;
  filtre değişikliğinden önce aynı kayıtlı adaylar üzerinde deterministik bir
  karşılaştırma gerekir.
- Yeni V2 analizleri raporun yanında `<belge>_candidate_snapshot.json` oluşturur.
  Snapshot temizlenmiş sayfa metnini, aday kanıtlarını ve teknik model inceleme
  kararını saklar. `run_v2.py replay SNAPSHOT --output RAPOR.json` aynı adayları
  Ollama çağırmadan etkin sözlük ve V2 filtreleriyle yeniden sınıflandırır.
- MacBook geliştirme kapsamı `qwen3.5:2b`, gerektiğinde `qwen3.5:4b` ile
  sınırlıdır. Gemma/Granite geçmiş gözlemi mevcut kabul kümesinde ölçülmediği
  için kesin karşılaştırma değildir; ürün seçili kurulu modele açık kalır.
- İlk gerçek snapshot `distributed-systems-compendium.pdf` ve `qwen3.5:2b` ile
  üretildi; canlı analiz `42,83 sn` sürdü. Çevrimdışı replay dört sonuç grubunda
  canlı raporla birebir aynı. Taban
  `evaluation/distributed_systems_compendium_replay_baseline.json` içindedir.
- İlk ölçümlü V2 filtre değişikliği `transparency` teknik başını genel İngilizce
  filtresinden korur. Deney
  `evaluation/distributed_systems_compendium_replay_filter_experiment.json`
  içinde: açık terim hassasiyeti/yakalama `%94,1 / %61,5`ten
  `%94,7 / %69,2`ye, kesin etiket doğruluğu `%89,6`dan `%91,1`e çıktı; gürültü
  eleme değişmedi.
- İkinci gerçek snapshot `bitcoin-whitepaper.pdf` ve `qwen3.5:2b` ile üretildi;
  canlı analiz `41,658 sn` sürdü, `complete` tamamlandı ve 86 doğrulanmış aday
  sakladı. Aynı snapshot'ta `transparency` istisnası kapalı taban ile etkin
  politika dört sonuç grubunda birebir aynı kaldı. 93 etiketli kabul kümesindeki
  açık terim hassasiyeti/yakalama iki koşulda da `%60,0 / %53,6`, kesin etiket
  doğruluğu `%72,0` oldu. Deney
  `evaluation/bitcoin_whitepaper_replay_filter_experiment.json` içindedir.
- İkinci ölçümlü V2 iyileştirmesi, yalnız model incelemesinin kabul ettiği iki
  sözcüklü Title Case `technical_pattern` adaylarını düşük puandan korur. İki
  sabit snapshot ve 228 etikette `Asymmetric Encryption`,
  `Symmetric Encryption` ve `Merkle Tree` geri kazanıldı; açık terim
  hassasiyeti/yakalama `%75,0 / %61,1`den `%76,6 / %66,7`ye, kesin etiket
  doğruluğu `%83,3`ten `%84,7`ye çıktı. Yanlış pozitif değişmedi. Büyük harf
  şartı olmayan geniş varyant iki gürültüyü de geçirdiği için reddedildi. Deney
  `evaluation/two_snapshot_titlecase_technical_pattern_experiment.json`
  içindedir.
- Üçüncü gerçek snapshot `intrusion-detection-systems-survey.pdf` ve
  `qwen3.5:2b` ile üretildi; analiz `48,659 sn` sürdü, `complete` tamamlandı ve
  173 doğrulanmış aday sakladı. Canlı rapor replay ile birebir aynıydı. Mevcut
  `transparency` ve Title Case kuralları bu belgede hiçbir sınıfı değiştirmedi.
  Üç snapshot ve 426 etikette Title Case kuralı açık terim
  hassasiyeti/yakalamayı `%75,0 / %43,3`ten `%76,2 / %46,2`ye, kesin etiket
  doğruluğunu `%79,3`ten `%80,0`a taşıdı; yanlış pozitif değişmedi. Deney
  `evaluation/three_snapshot_titlecase_technical_pattern_experiment.json`
  içindedir.
- Modelce kabul edilmiş düşük puanlı ve açık kısaltma taşıyan n-gram kuralı
  `network-based IDS`, `SNMP trap` ve `switch SPAN port` terimlerini geri
  kazandırdı; ancak üçü de aynı IDS belgesinden geldiği için aşırı uyum riskiyle
  ertelendi ve koda alınmadı. Denetim izi
  `evaluation/three_snapshot_acronym_ngram_candidate_experiment.json`
  içindedir.
- Dördüncü gerçek snapshot `google-file-system.pdf` ve `qwen3.5:2b` ile
  üretildi; analiz `86,894 sn` sürdü, `complete` tamamlandı ve 134 doğrulanmış
  aday sakladı. Canlı rapor replay ile birebir aynıydı. Mevcut iki V2 kuralı bu
  belgede de hiçbir sınıfı değiştirmedi. Dört snapshot ve 608 etikette Title
  Case kuralı açık terim hassasiyeti/yakalamayı `%77,3 / %38,2`den
  `%78,0 / %39,9`a, kesin etiket doğruluğunu `%73,7`den `%74,2`ye taşıdı;
  yanlış pozitif değişmedi. Deney
  `evaluation/four_snapshot_titlecase_technical_pattern_experiment.json`
  içindedir.
- Dört belgenin düşük puanlı model-kabul adaylarında yeni ve belgeler arası
  tekrarlanan güvenli bir desen bulunmadı. Kısaltmalı n-gram adayı hâlâ yalnız
  IDS belgesinde örnek verdiği için ertelenmiş kalır; yeni filtre eklenmedi.
- Beşinci gerçek snapshot `spanner-globally-distributed-database.pdf` ve
  `qwen3.5:2b` ile üretildi; analiz `86,403 sn` sürdü, `complete` tamamlandı ve
  126 doğrulanmış aday sakladı. Canlı rapor replay ile birebir aynıydı.
- Spanner'daki `GPS masters`, kısaltmalı n-gram desenine ikinci bağımsız belge
  kanıtını sağladı. Yalnız `ngram_scan` kaynağı taşıyan, model incelemesinde
  kabul edilmiş ve açık büyük-harf kısaltması içeren düşük puanlı adaylar V2'de
  korunuyor. Beş snapshot ve 734 etikette dört doğru terim kazanıldı, yeni yanlış
  pozitif oluşmadı; açık terim hassasiyeti/yakalama `%82,3 / %48,9`dan
  `%82,8 / %50,6`ya, kesin etiket doğruluğu `%75,5`ten `%76,0`a çıktı.
- Üç ölçümlü V2 replay kuralının birleşik son ölçümünde filtreler öncesi tabana
  göre açık terim hassasiyeti/yakalama `%81,6 / %46,8`den `%82,8 / %50,6`ya,
  teknik terim hassasiyeti/yakalama `%90,4 / %79,2`den `%90,6 / %80,7`ye ve
  kesin etiket doğruluğu `%74,8`den `%76,0`a çıktı; gürültü eleme değişmedi.
  Kanıt `evaluation/five_snapshot_final_v2_policy_experiment.json` içindedir.
- Beş snapshot'taki kalan düşük puanlı adaylarda, yalnız `model` kaynağından
  gelen ve model incelemesinde kabul edilmiş düzenli tek sözcüklü çoğul deseni
  iki bağımsız belgede gerilemesiz kazanç sağladı. `rulesets` ve `accessors`
  geri kazanıldı; açık terim hassasiyeti/yakalama `%82,8 / %50,6`dan
  `%83,0 / %51,5`e, kesin etiket doğruluğu `%76,0`dan `%76,3`e çıktı. Yanlış
  pozitif değişmedi. Kanıt
  `evaluation/five_snapshot_reviewed_model_plural_experiment.json` içindedir;
  yalnız iki örneğe dayandığı için yeni snapshotlarda aşırı uyum riski izlenmelidir.
  Dört dar V2 kuralının filtreler öncesi ortak tabana göre güncel birleşik ölçümü
  `evaluation/five_snapshot_current_v2_policy_experiment.json` içindedir: açık
  terim hassasiyeti/yakalama `%81,6 / %46,8`den `%83,0 / %51,5`e, teknik terim
  hassasiyeti/yakalama `%90,4 / %79,2`den `%90,6 / %81,0`a ve kesin etiket
  doğruluğu `%74,8`den `%76,3`e çıktı.
- V2.2 kısaltma kaynağı tamamlandı. Resmî sayfanın gömdüğü `2025-03-17` PDF'si
  52 sayfa ve metin katmanlıdır; başlıktaki 1.215 beyana karşı 1.199 eksiksiz
  kayıt ve 1.020 benzersiz kısaltma çıkarıldı. 16 kayıtlık `%1,32` fark metadata'da
  saklanıyor. Kaynak `data/tbd_abbreviations_2025_03_17.json` altında ana
  sözlükten ayrıdır; `abbreviations status/convert` komutları çalışır.
- Belgede tanımlı açılım resmî kayıtla uyuşursa `defined_abbreviation`, yalnız
  kısaltma bulunursa `abbreviation_source` türüyle `possible_matches` grubunda ve
  `match_source=tbd_abbreviations` etiketiyle raporlanır. Beş snapshotta yalnız
  `NoSQL`, ana sözlük açığından kısaltma kaynağındaki olası eşleşmeye taşındı;
  teknik terim ölçüsü değişmedi. Açık terim yakalama `%51,5`ten `%51,1`e indi;
  bu filtre kaybı değil bilinçli kaynak sınıfı değişimidir. Kanıt
  `evaluation/five_snapshot_abbreviation_source_experiment.json` içindedir.
- 44 V2 testi ve 47 V1 testi geçiyor. İç değerlendirme uzman onayı değildir ve
  V2 analiz kalitesinin V1'den üstün olduğu henüz iddia edilmemelidir.
- V2.3 yönü kişisel bilgisayarda güvenilir yerel kullanım olarak güncellendi;
  kurum sunucusu kesin hedef değildir ve isteğe bağlı sonraki aşamadır. Ana
  öncelik doğru terim bulma, basit yerel çalıştırma ve rapor üretimidir.
- V2.3 için donanımdan bağımsız ilk güvenlik adımı eklendi: aynı anda tek analiz
  çalışır; kapasite doluyken ikinci istek Ollama çağrısı yapmadan HTTP 503 ve açık
  yoğunluk mesajı alır. Hedef sunucu ölçümünden sonra sınır
  `MAX_CONCURRENT_ANALYSES` ile artırılabilir. HTTPS, kimlik doğrulama, saklama,
  yedekleme ve günlükleme kararları kurum bilgilerini beklemektedir.
- V2 geliştirme sunucusu artık HTTPS ve kimlik doğrulama eklenene kadar yalnız
  loopback adreslerinde çalışır; `0.0.0.0`, LAN adresi ve belirsiz ana makine
  adları reddedilir. HTML/rapor/JSON yanıtlarında temel tarayıcı güvenlik
  başlıkları vardır. `GET /healthz` yalnız `{"status":"ok"}` döndürür ve Ollama
  ya da sözlük ayrıntısı sızdırmaz.
- `DEPLOYMENT_READINESS.md`, hedef donanım, erişim, kullanıcı, saklama, günlük ve
  yedekleme kararlarını tek formda toplar. Özellikle geçici PDF silinse de replay
  snapshot'ının temizlenmiş tam sayfa metnini kalıcı olarak taşıdığı açıkça
  belgelenmiştir; kurum politikası gelmeden otomatik saklama/silme eklenmemelidir.
- `python3 run_v2.py` artık yerel sunucuyu başlattıktan sonra V2 arayüzünü
  tarayıcıda otomatik açar; komut satırı kullanımı için `serve --no-browser`
  seçeneği vardır.
- Günlük macOS ve Windows başlatıcıları da `run_v2.py` çalıştıracak şekilde
  V2'ye yönlendirildi; README'deki kolay kullanım adresi `127.0.0.1:8876` olarak
  güncellendi. `run.py` ve V1 komutları yalnız karşılaştırma/geri dönüş amacıyla
  açıkça ayrı belgelenir.
- Hedef cihazda kalan iki V2.3 kabul maddesi için
  `KISISSEL_BILGISAYAR_KABUL.md` eklendi. İlk kurulum, tek PDF, indirme ve beş
  belge ölçümü bu listeyle kaydedilebilir; fiziksel hedef cihaz erişimi olmadan
  bu kabul tamamlandı diye işaretlenmemelidir.
- Beş snapshot güncel politikayla yeniden oynatılıp kalan düşük puanlı,
  model-kabul `technical_pattern` adayları denetlendi. Yedi adayın yalnız üçü
  doğru, dördü gürültüdür. `protocol` kazanımları tek Spanner belgesinde,
  iki-sözcüklü `tree` kazanımı tek GFS örneğindedir; belgeler arası kanıt olmadığı
  için yeni filtre eklenmedi. Denetim
  `evaluation/five_snapshot_residual_technical_pattern_audit.json` içindedir.
- 2026-08-14 devir: GPT 5.6 SOL'un Codex worktree'lerinde commit edilmeden kalmış
  iş kurtarıldı ve `codex/v2`'ye `50d4c06` commit'iyle eklendi (başlatıcılar V2'ye
  yönlendirildi, README V2 birincil yapıldı, `KISISSEL_BILGISAYAR_KABUL.md` ve
  `tests_v2/test_launchers.py` eklendi). Depo `codex/v2` dalına geçirildi.
  Sözlük verisinin Git'te düz izlenmesi, LFS ve geçmiş yeniden yazmanın ertelenmesi
  ADR-024 olarak kaydedildi. Eski `7a76` ve `f4ef` Codex worktree'leri bayat kalmış
  ve temizlenebilir.
- 2026-08-14 ikinci devir: Beş sabit snapshot'ta yeni bir ölçümlü V2 replay
  iyileştirmesi eklendi (ADR-025): en az iki kez geçen çok sözcüklü genel İngilizce
  öbekler artık elenmiyor. Gerçek açık hassasiyeti/yakalama `%83,2 / %52,3`ten
  `%84,6 / %57,8`e çıktı; yanlış pozitif ve gürültü eleme değişmedi. Kalan doğruluk
  açığı hâlâ büyük ölçüde model aday kalitesinden (qwen3.5:2b) gelir; daha büyük
  model (`qwen3.5:4b`) aynı kabul kümesinde ölçülmeden üstünlük iddiası yapılmamalıdır.
- `qwen3.5:4b` aynı beş belgede çalıştırıldı. Mevcut 734 etiketlik kabul kümesi
  2b adaylarından üretildiği için 4b'yi adil ölçemedi (4b'nin 94 yeni tahmini
  etiketsiz kaldı ve yanlış pozitif gibi göründü). Proje sahibinin isteğiyle
  2b∪4b birleşiminden `evaluation/five_article_union_internal_review.json`
  (890 etiket) üretildi; yeni 156 terim yapay zekâ tarafından
  `internal_review` statüsünde etiketlendi ve uzman onayı değildir. Bu adil
  kümede iki model birbirine yakın çıktı: 2b açık-terim P/R `%84,6 / %41,4`,
  4b `%84,6 / %46,5`; 4b aynı hassasiyette daha yüksek yakalama sağladı. Fark
  küçük olduğundan tek başına kesin model üstünlüğü kanıtı değildir; daha güçlü
  model (veya API) gerçek kazanç için ayrı deneme gerektirir.
- OpenAI uyumlu bulut API sağlayıcısı eklendi (ADR-026). `MODEL_PROVIDER=api`
  ile `API_BASE_URL`, `API_KEY`, `API_MODEL` ortam değişkenleri kullanılır;
  istemler ve JSON ayrıştırma Ollama istemcisinden yeniden kullanılır. Yerel
  Ollama varsayılan olarak kalır; sağlayıcı seçimi kod değişikliği gerektirmez.
  Belge gizli olmadığı için kurum sağlayıcısı ve sunucu kararı verildiğinde aynı
  kod birden çok OpenAI-uyumlu API'yi (OpenAI, DeepSeek vb.) destekler. Henüz
  gerçek bir API anahtarıyla uçtan uca denenmedi; adil kazanç ölçümü bekler.
- DeepSeek (`deepseek-chat`) gerçek API anahtarıyla beş belgede çalıştırıldı.
  Aday üretimi 2b/4b'den çok daha zengin ve hızlıydı (5 belge ~126 sn; 2b ~218,
  4b ~725). Üç modelin tümü 2b∪4b∪DeepSeek birleşiminden oluşan 1193 etiketlik
  `evaluation/five_article_triple_internal_review.json` üzerinde adil ölçüldü
  (yeni 303 terim yapay zekâ tarafından `internal_review` statüsünde etiketlendi;
  uzman onayı değildir). Sonuç: 2b açık-terim P/R `%84,6 / %24,3`, 4b
  `%84,6 / %27,3`, DeepSeek `%92,3 / %66,1`; teknik-terim P/R sırasıyla
  `%90,9 / %51,6`, `%91,1 / %52,7`, `%93,6 / %79,4`. DeepSeek hem hassasiyet
  hem yakalamada açık ara üstün; etiket doğruluğu `%77,3` (2b `%54,4`, 4b
  `%55,2`). Profesör için en eksiksiz eksik-terim listesi güçlü API modelinden
  gelir; yerel küçük modeller ciddi ölçüde yetersiz kalır.

## V1 referans bilgisi

Projenin adı **TBD Dictionary Control**. Metin katmanlı PDF'lerdeki İngilizce bilişim
terimlerini çıkarır, `data/tbd_dictionary_2026_coordinate.json` içindeki
İngilizce–Türkçe sözlükle karşılaştırır ve özellikle sözlükte bulunmayan terimleri
listeler.

Kaynak sözlük sitesi: https://bilisimde.ozenliturkce.org.tr/

### V1 durumu

- Python 3.9+ ile çalışır.
- Yerel model sağlayıcısı Ollama'dır.
- Kalıcı varsayılan model yoktur. Web arayüzü kurulu Ollama modellerini dinamik
  listeler ve açık seçim ister; `OLLAMA_MODEL` yalnız isteğe bağlı ön seçimdir.
- Yerel web arayüzü `python3 run.py` ile açılır.
- CLI: `python3 run.py scan <pdf-veya-klasör> --model MODEL_ETIKETI`.
- Excel, CSV ve JSON raporları çakışmayı önlemek için
  `output/<model>/<belge>/` altında oluşturulur.
- PDF sayfa numaraları ve terim geçiş sayıları korunur.
- Bulunan, olası, eksik ve elenen adaylar ayrı raporlanır.
- Üretim akışı varsayılan olarak tek geçişli model aday çıkarımı yapar;
  `OllamaClient` deneyler için iki geçişi destekler ancak CLI ve web arayüzü bu
  seçeneği henüz açmaz. Çok sözcüklü sözlük terimleri ayrıca deterministik taranır.
- Sözlükte olmayan adaylar kaynak, tekrar sayısı ve model doğrulamasını birleştiren
  açıklanabilir puanla sınıflandırılır; düşük puanlılar denetim listesine alınır.
- Modelin kaçırdığı kontrollü teknik baş kalıpları ve açıkça tanımlanan
  kısaltma açılımları deterministik olarak geri kazanılır; sınır ve referans
  filtrelerinden geçen tekrarlı öbekler de düşük ağırlıklı sinyal olabilir.
- Düşünme destekli Ollama modellerinde yapılandırılmış JSON yanıtının boş
  kalmaması için `think: false` gönderilir.
- Başarısız model parçaları `failed` veya `partial` analiz durumuyla görünür;
  başarısız tarama kullanıcıya “0 eksik” sonucu olarak sunulmaz.
- Güvenli tire ve düzenli tekil/çoğul farkları sözlük tarafından kapsanan biçim
  değişkeleri sayılır; tanımlı kısaltmalar **olası** eşleşme olarak gösterilir.
- Kod değişkenleri (`num_heads`, `assume_bos`), pseudo-code satırları, İngilizce tanımlıklar (`the ...`) ve ticari model/sürüm isimleri (`GPT-4`, `GPT-3.5`) otomatik süzülür.
- Çoğul kısaltmalar (`LLMs`) otomatik olarak tekil kök haline (`LLM`) dönüştürülür.
- Test takımı Ollama kullanmaz.

## Mimari

- `pdf_reader.py`: PDF metnini sayfa bazında çıkarır, drop-cap baş harflerini korur ve kod bloklarını temizler.
- `chunker.py`: Metni modele gönderilecek parçalara böler.
- `ollama_client.py`: Ollama durumu, model kontrolü ve yapılandırılmış çıkarım.
- `dictionary.py`: Sözlük yükleme, normalizasyon ve eşleştirme.
- `term_extractor.py`: Aday temizliği, ayırma ve kaynak metinde doğrulama.
- `pipeline.py`: Tüm analiz akışını ve sonuç gruplarını birleştirir; marka/model süzgeçlerini uygular.
- `reporting.py`: Terminal, CSV ve JSON çıktıları.
- `web_app.py`: Bağımlılıksız yerel HTTP arayüzü.
- `cli.py`: Komut satırı giriş noktası.

## Doğrulama komutu

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```

Son temizlemede 43 test başarılıydı. Yeni değişikliklerden sonra bu komut yeniden
çalıştırılmalıdır.

## Bilinen kararlar ve sınırlar

- Bu sistem tam özerk bir ajan değil; yerel LLM destekli hibrit belge analiz
  işlem hattıdır.
- Sözlük eşleşmesini model değil deterministik Python kodu yapar.
- OCR kapsam dışıdır.
- Hedef şirket bilgisayarlarının işletim sistemi ve donanımı henüz bilinmiyor.
- Bu nedenle `.app`/`.exe` paketleme ve kesin model seçimi yapılmadı.
- Ollama'nın hedef bilgisayarda bulunmama ihtimali teslimin sonraki aşamasında
  çözülecek.
- Sözlük lisansı ve kurum içi yeniden dağıtım izni doğrulanmalıdır.
- Model değişikliği sabit bir PDF kabul kümesinde doğruluk, yanlış pozitif, kaçırma
  ve süre ölçülmeden yapılmamalıdır.

## Sonraki sohbet için önerilen ilk mesaj

> Bu klasördeki `README.md` ve `AI_HANDOFF.md` dosyalarını okuyarak projeyi devral.
> Önce testleri çalıştır ve mevcut durumu raporla. Benden açık onay almadan kapsamı
> büyütme, model değiştirme veya yeni dağıtım teknolojisi ekleme.

## Sonraki mantıklı adım

Prototipi görev veren kişiye gösterip şu bilgileri almak:

1. Hedef işletim sistemi ve yaklaşık donanım
2. Tek kullanıcı mı, çok kullanıcı mı
3. Belgelerin cihazdan çıkmama gereksinimi
4. Ollama kurulumuna izin verilip verilmediği
5. OCR ve Word/PDF rapor beklentisi
6. Sözlük güncelleme ve lisans yöntemi
