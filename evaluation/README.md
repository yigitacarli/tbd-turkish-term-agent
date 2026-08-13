# V2 kabul kümesi ve ölçüm

Bu klasör gerçek makalelerde V1/V2 kalite karşılaştırmasının insan tarafından
incelenmiş girdisini taşır. `acceptance_set.example.json` yalnız şema örneğidir;
gerçek kalite kanıtı değildir. İlk küme proje sahibi ve yapay zekâ tarafından
hazırlanır ve `internal_review` statüsüyle saklanır; uzman onayı sayılmaz.

Güncel politikanın kalan düşük puanlı, modelce kabul edilmiş teknik kalıpları
`five_snapshot_residual_technical_pattern_audit.json` içinde ayrıca denetlenir.
Tek belgeye dayanan `tree`/`protocol` örnekleri yeni filtre kanıtı sayılmaz.

Her makale için V1 ve V2 raporlarındaki adayların birleşimi önce şablona alınır:

```bash
python3 run_v2.py prepare-acceptance \
  --v1-result output/model/makale/makale_terms.json \
  --v2-result output_v2/model/makale/makale_terms.json \
  --output evaluation/acceptance_set.json
```

Yalnız bir sürümün başlangıç raporları hazırsa sadece ilgili `--v1-result` veya
`--v2-result` seçeneği de kullanılabilir.

Şablondaki her adayın `observed_in` alanı hangi sistem ve sonuç grubundan
geldiğini gösterir. İnceleyen kişi bütün boş `label` alanlarını şu değerlerden
biriyle eksiksiz doldurmalıdır:

- `dictionary_match`: Gerçek teknik terim ve etkin TBD sözlüğünde bulunuyor.
- `missing_term`: Gerçek teknik terim fakat etkin TBD sözlüğünde bulunmuyor.
- `noise`: Teknik terim değil; sonuçta görünmemeli veya elenmiş olmalı.

Komut kullanmak yerine V2 web arayüzündeki `/evaluation` sayfasına birden fazla
V1/V2 JSON raporu yüklenebilir. Ekran bütün adayları birleştirir ve kararlar
tamamlandığında `internal_acceptance_set.json` dosyasını indirir.

Etiketlenmemiş bir teknik-terim tahmini hassasiyet hesabında yanlış pozitif kabul
edilir; sonuç gruplarındaki bütün etiketsiz kayıtlar ayrıca
`unlabelled_prediction_count` alanında gösterilir. Bu nedenle yarım etiketli bir
dosya ile hassasiyet ölçümü yapılmamalıdır. `possible_matches` teknik terim
yakalamada olumlu sayılır fakat kesin sözlük sınıfı olarak doğru sayılmaz.

Önceden üretilmiş V1/V2 JSON raporlarını karşılaştırmak için:

```bash
python3 run_v2.py evaluate evaluation/acceptance_set.json \
  --v1-result output/model/makale/makale_terms.json \
  --v2-result output_v2/model/makale/makale_terms.json \
  --output evaluation/sonuc.json
```

Birden fazla makale için her `--v1-result` ve `--v2-result` seçeneği tekrar edilir.
Araç teknik-terim ve gerçek-açık hassasiyet/yakalama oranlarını, gürültü eleme
oranını, kesin etiket doğruluğunu, analiz durumlarını ve raporda varsa ortalama
`analysis_duration_seconds` değerini üretir.

## Taslak inceleme

Yapay zekâ tarafından bağlamla hazırlanan fakat proje sahibinin henüz
onaylamadığı dosyalar `internal_draft` statüsünü taşır. `evaluate` komutu bu
dosyaları bilerek reddeder. Orta güvenli kararlar onaylandıktan sonra statü
`internal_review` yapılır ve ancak bundan sonra kalite ölçümünde kullanılır.

## Mevcut iç ölçüm

`five_article_internal_review.json`, aynı `qwen3.5:2b` modeliyle üretilen beş
makaledeki V1 ve V2 raporlarının 734 adaylık tam birleşimini içerir. Toplu sonuç
`five_article_v1_v2_measurement.json`, belge bazlı kırılım
`five_article_document_breakdown.json` dosyasındadır. GFS'nin ilk 134 adaylık
`google_file_system_internal_draft.json` taslağı denetim izi olarak korunur.

V2 şu anda V1'in aynı analiz çekirdeğini içe aktarır. Bu nedenle ayrı model
koşularından gelen farklar sürüm üstünlüğü sayılmaz; mevcut sonuç kabul kümesi,
çalışma süresi ve model tekrar kararlılığı için tabandır. Filtre etkisi aynı
kayıtlı model adayları üzerinde deterministik yeniden oynatmayla ölçülmelidir.

## Aday anlık görüntüsünü yeniden oynatma

Yeni V2 analizleri JSON/CSV/Excel raporunun yanına
`<belge>_candidate_snapshot.json` yazar. Bu dosya modelin doğrulanmış adaylarını,
aday kaynaklarını, sayfa metnini ve teknik model inceleme kararını sabitler.
Mevcut etkin sözlük ve V2 filtreleriyle Ollama çağırmadan yeniden sınıflandırmak
için:

```bash
python3 run_v2.py replay \
  output_v2/qwen3.5-2b/makale/makale_candidate_snapshot.json \
  --output evaluation/makale_replay.json
```

Eski raporlarda bu snapshot alanı yoktur; sonuç gruplarından geriye doğru sahte
bir ham aday kümesi üretilmez. İlk gerçek replay tabanı yeni bir analizden sonra
oluşacaktır.

İlk gerçek taban ve filtre deneyi dağıtık sistemler makalesinde kaydedildi:

- `distributed_systems_compendium_replay_baseline.json`
- `distributed_systems_compendium_replay_transparency_candidate.json`
- `distributed_systems_compendium_replay_filter_experiment.json`

`transparency` teknik başı değişikliği açık terim hassasiyetini düşürmeden
yakalamayı artırdı. Sonuç tek belgeye ait olduğundan sonraki filtreler mümkünse
birden fazla snapshot üzerinde doğrulanmalıdır.

İkinci gerçek snapshot `bitcoin-whitepaper.pdf` ve `qwen3.5:2b` ile üretildi.
Canlı analiz `41,658 sn` sürdü ve 86 doğrulanmış adayla `complete` tamamlandı.
`transparency` istisnası kapalı taban ile etkin politika dört sonuç grubunda
birebir aynı kaldı; 93 etiketli kabul kümesindeki bütün ölçüler değişmedi. Deney
özeti `bitcoin_whitepaper_replay_filter_experiment.json` dosyasındadır. Bu ikinci
belge ilk kazanımın başka bir alanda gerileme üretmediğine dair ek kanıttır;
yeni teknik başları korumak için tek başına yeterli genelleme kanıtı değildir.

İki snapshot üzerindeki ikinci filtre deneyi
`two_snapshot_titlecase_technical_pattern_experiment.json` dosyasındadır. Yalnız
`technical_pattern` kaynağı taşıyan, model incelemesinde kabul edilmiş ve tam iki
Title Case sözcükten oluşan adaylar düşük puandan korunmuştur. 228 etikette açık
terim hassasiyeti/yakalama `%75,0 / %61,1`den `%76,6 / %66,7`ye, kesin etiket
doğruluğu `%83,3`ten `%84,7`ye yükselmiş; yanlış pozitif sayısı değişmemiştir.
Baş harf şartı olmayan geniş varyant 3 doğru terime karşı 2 gürültü geçirdiği
için V2'ye alınmamıştır.

Üçüncü gerçek snapshot `intrusion-detection-systems-survey.pdf` ve
`qwen3.5:2b` ile `48,659 sn`de üretildi; 173 doğrulanmış adayla `complete`
tamamlandı. Canlı rapor replay ile birebir aynıydı. Mevcut iki dar V2 kuralı bu
belgede hiçbir adayın sınıfını değiştirmedi. Üç snapshot ve 426 etikette Title
Case teknik kalıp kuralının açık terim hassasiyeti/yakalama etkisi
`%75,0 / %43,3`ten `%76,2 / %46,2`ye, kesin etiket doğruluğu etkisi `%79,3`ten
`%80,0`a çıktı; yanlış pozitif değişmedi. Sonuç
`three_snapshot_titlecase_technical_pattern_experiment.json` içindedir.

Modelce kabul edilmiş düşük puanlı ve açık kısaltma taşıyan n-gram adayı üç IDS
terimini geri kazandı. Ancak üç terimin tamamı aynı makaleden geldiği için bu
kural tek belgeye aşırı uyum riskiyle ertelendi ve V2'ye taşınmadı. Denetim izi
`three_snapshot_acronym_ngram_candidate_experiment.json` dosyasındadır.

Dördüncü gerçek snapshot `google-file-system.pdf` ve `qwen3.5:2b` ile
`86,894 sn`de üretildi; 134 doğrulanmış adayla `complete` tamamlandı. Canlı
rapor replay ile birebir aynıydı. Mevcut iki dar V2 kuralı bu belgede de hiçbir
sınıfı değiştirmedi. Dört snapshot ve 608 etikette Title Case kuralı açık terim
hassasiyeti/yakalamayı `%77,3 / %38,2`den `%78,0 / %39,9`a, kesin etiket
doğruluğunu `%73,7`den `%74,2`ye taşıdı; yanlış pozitif değişmedi. Sonuç
`four_snapshot_titlecase_technical_pattern_experiment.json` içindedir.

Düşük puanlı model-kabul adaylarının dört belge karşılaştırmasında yeni ve
belgeler arası tekrarlanan güvenli bir desen bulunmadı. Kısaltmalı n-gram adayı
hâlâ yalnız IDS belgesinde örnek verdiği için ertelenmiş kalır.

Beşinci gerçek snapshot `spanner-globally-distributed-database.pdf` ve
`qwen3.5:2b` ile `86,403 sn`de üretildi; 126 doğrulanmış adayla `complete`
tamamlandı. Canlı rapor replay ile birebir aynıydı. Spanner'daki `GPS masters`,
ertelenmiş kısaltmalı n-gram desenine ikinci bağımsız belge kanıtını sağladı.
Kural beş snapshot ve 734 etikette dört doğru terimi geri kazandı, yeni yanlış
pozitif üretmedi; açık terim hassasiyeti/yakalama `%82,3 / %48,9`dan
`%82,8 / %50,6`ya, kesin etiket doğruluğu `%75,5`ten `%76,0`a çıktı. Sonuç
`five_snapshot_acronym_ngram_experiment.json` içindedir.

Üç ölçümlü V2 replay kuralının birleşik son ölçümü
`five_snapshot_final_v2_policy_experiment.json` dosyasındadır. Filtreler öncesi
tabana göre açık terim hassasiyeti/yakalama `%81,6 / %46,8`den
`%82,8 / %50,6`ya, teknik terim hassasiyeti/yakalama `%90,4 / %79,2`den
`%90,6 / %80,7`ye ve kesin etiket doğruluğu `%74,8`den `%76,0`a yükseldi;
gürültü eleme oranı değişmedi.

Beş snapshot'taki kalan düşük puanlı adayların belge bazlı denetiminde yalnız
`model` kaynağından gelen, teknik model incelemesinde kabul edilmiş düzenli tek
sözcüklü çoğullar iki bağımsız belgede ortak güvenli desen verdi. Dar kural
`rulesets` ve `accessors` terimlerini geri kazandı; yanlış pozitif üretmedi. Açık
terim hassasiyeti/yakalama `%82,8 / %50,6`dan `%83,0 / %51,5`e, kesin etiket
doğruluğu `%76,0`dan `%76,3`e çıktı. Deney
`five_snapshot_reviewed_model_plural_experiment.json` içindedir. Örnek sayısı iki
olduğu için yeni snapshotlarda aşırı uyum riski izlenmeye devam edilmelidir. Dört
dar V2 kuralının filtreler öncesi ortak tabana göre güncel birleşik ölçümü
`five_snapshot_current_v2_policy_experiment.json` dosyasındadır: açık terim
hassasiyeti/yakalama `%81,6 / %46,8`den `%83,0 / %51,5`e, teknik terim
hassasiyeti/yakalama `%90,4 / %79,2`den `%90,6 / %81,0`a ve kesin etiket
doğruluğu `%74,8`den `%76,3`e yükselmiştir.

## Ayrı kısaltma kaynağı ölçümü

Resmî TBD Bilişim Kısaltmaları Sözlüğü ana terim sözlüğüne birleştirilmeden ayrı
indekslenir. Belgede açılımı açıkça tanımlanan kayıtlar `defined_abbreviation`,
tanımı bulunmayan fakat resmî kısaltma kaynağında yer alanlar
`abbreviation_source` eşleşmesidir; ikisi de insan kararı gerektiren
`possible_matches` grubunda kalır.

Beş snapshot replayinde yalnız `NoSQL`, `missing_terms` grubundan resmî
kısaltma kaynağındaki `Not Only SQL` olası eşleşmesine taşındı. Teknik terim
hassasiyeti/yakalama değişmedi. Kabul kümesi yalnız ana sözlük sınıfını taşıdığı
için açık terim yakalama oranı `%51,5`ten `%51,1`e ve kesin etiket doğruluğu
`%76,3`ten `%76,2`ye indi. Bu, aday kaybı değil bilinçli kaynak sınıfı değişimidir;
kabul etiketleri otomatik değiştirilmedi. Deney
`five_snapshot_abbreviation_source_experiment.json` içindedir.
