# Yapay Zekâ / Geliştirici Devir Notu (AI Hand-off)

## Teslim Durumu (2026-08-22)

Bu bölüm 22 Ağustos 2026 çalışmasını kaydeder. Önceki teslim durumları
aşağıda korunmuştur.

### Yapılan işler

1. **Eksik terim gürültü taksonomisi ölçüldü (internal_draft).** 14 belgedeki
   1.853 eksik terimin tamamı sınıflandırıldı (yapay zekâ iç etiketi,
   ADR-008/009 ruhunda; uzman onayı değildir). Sonuç: **%26,8 gerçek aday**
   (489), **%72,5 gürültü** (1.324). Gürültünün dağılımı: tanımlayıcı öbek
   %46,1, kavram tekrarı %8,9, sistem özel adı %7,1, kod tanımlayıcısı %3,9,
   kaynakça/başlık/metrik/genel sözcük kalanı. **Sonuç: gürültünün büyük
   bölümü hat yapısından geliyor; model değiştirmek bu tabloyu düzeltmez.**
   Ölçüm notu ve etiket verisi depo dışındadır (geçici çalışma dizini).
2. **ADR-042 uygulandı:** eksik terimlerde kavram bazında birleştirme
   (`condensed_key` + belge kanıtlı kısaltma eşleri + `variants` alanı).
   Mevcut koşu üzerinde simüle edilen etki dürüstçe küçük: -8 satır (%0,4).
   Değer, güvenli deterministik birleştirmenin üst sınırını belgeler.
3. **Kaynak PDF'lerin yeri belirlendi:** `Desktop\PROJELER\Makaleler`
   (depo dışı) altında eski 14 makale + ~13 yeni makale (Dynamo, Spanner,
   GFS, MapReduce, Bitcoin, IDS survey, TensorFlow, Zero Trust vb.) mevcut.
   Recall tarafı analizi artık mümkün.

### Doğrulanmış durum (2026-08-22)

- **Testler:** `tests/` altındaki **115 testin tamamı geçmektedir**
  (Windows, Python 3.14, ~0,16 sn); `compileall` temiz.
- **Dal:** çalışma `feat/variant-merging` dalında; main'e birleştirme ve
  push henüz yapılmadı.

### Bekleyen işler (öncelik sırasıyla)

1. **İstem genişletmesi canlı ölçümle doğrulandı ve uygulandı
   (ADR-043).** `12_webassembly` üzerinde her istemle ikişer koşum:
   kararlı kümelerde net -29 gürültü satırı (~%13), gerçek terim dengesi
   değişmedi (3 kayıp / 3 kazanım). Kullanıcının DeepSeek anahtarıyla 6
   koşum yapıldı; toplam maliyet birkaç sent. Eski raporlar depo dışında
   `yedek-output-20260822` klasörüne yedeklendi.
2. Kaynakça temizliğinin belge sonuna yayınması (bilinen sınır #3);
   PDF'ler bulunduğu için etkisi artık ölçülebilir.
3. Kalan öbek gürültüsü (%46) için eleme değil sıralama/gruplama sunumu.
4. Uzman etiketli altın küme hâlâ açık; internal_draft etiketleri yalnızca
   geliştirme sinyali olarak kullanılmalıdır.
5. **Yeni makaleler tarandı (2026-08-22).** `Desktop\PROJELER\Makaleler`
   altındaki 9 benzersiz yeni belge birleştirilmiş hatla
   (ADR-042 + ADR-043) analiz edildi: 162 sayfa, 1.574 aday, 999 eksik
   terim, 390 sözlük eşleşmesi, toplam 293 sn (~1,8 sn/sayfa). Kod
   tanımlayıcı sızıntısı 14/999 (%1,4) ile tarihsel düzeyin çok altında;
   ADR-042 `variants` alanı 42 maddede doldu. Kopya PDF'ler dosya karması
   ile ayıklandı (attention×3, bert×2, raft×2, rag×2, bitcoin×2 tekil).
   Kirli `8_ebpf` belgesi bilinçli atlandı. Raporlar
   `output/deepseek-v4-flash/<belge>/` altında. Kalan bakiye ~0,46 USD.

---

## Teslim Durumu (2026-08-19)

Bu bölüm 19 Ağustos 2026 tarihli son teslim rötuşunu kaydeder. Bir önceki
teslim durumu (2026-08-18) aşağıda olduğu gibi korunmuştur.

### Bu rötuşta yapılan düzeltmeler

1. **PDF metin çıkarımı düzeltildi (ADR-037).** İki sütunlu sayfalar artık
   sütun sütun okunuyor, pdfplumber `x_tolerance=1.5` ile çağrılıyor ve satırın
   yalnızca bir bölümü bitişikse okunabilir kalan korunuyor. Ölçüm: `BSGRJS18`
   belgesinde ham metin 47.692 → 100.492 karakter (2,19x).
2. **Yerel model çıktı bütçesi bulutla eşitlendi (ADR-037).** `num_predict`
   256 → 4096, `num_ctx=8192` açıkça veriliyor.
3. **Aday doğrulaması satır sonu tirelemesine ve çekim farkına tolerans
   kazandı (ADR-038).** Ölçüm: 14 makalelik kümede haksız elenen aday sayısı
   **142 → 68** (−%52); `block cipher`, `digital signature`, `smart contract`
   gibi gerçek terimler artık rapora giriyor. Eşleşme bir yüzey biçimi
   üzerinden kurulduysa rapora `matched_form` alanı yazılıyor.
4. **Sıfır aday dönen analiz artık sessiz kalmıyor (ADR-039).** Model hiç aday
   döndürmediğinde rapora uyarı yazılıyor ve arayüzde bildirim gösteriliyor.
5. **Parça başına aday tavanı 8'den 16'ya çıkarıldı (ADR-040).** Tavanın konduğu
   2026-08-14 koşulları (boş yanıtlar, yapılandırılmamış çıktı, dar token bütçesi,
   bozuk PDF metni) ortadan kalkmıştı. Ölçüm: 8 → 16 geçişi aday hacmini ikiye
   katlarken uydurma oranını 1-2 puan artırıyor; 16 → 24 kazancı yarıya indirip
   uydurmayı tabanın 2,7 katına çıkarıyor. Değer `MAX_TERMS_PER_CHUNK` ortam
   değişkeniyle ölçüm için değiştirilebilir.
6. **Tek sözcüklü sözlük eşleşmeleri işaretleniyor (ADR-041).** `attention` →
   "uyarı" gibi bağlama uymayan karşılıklar raporda "Sözlükte Kayıtlı (Tek
   Sözcük)" ve "Karşılığın bağlama uygunluğunu doğrula" olarak görünüyor.
   Hiçbir terim gizlenmiyor.
7. **`docs/DECISIONS.md` başına yürürlük dizini eklendi.** 18 ADR'nin kaldırılmış
   V2/replay hattına ait olduğu ve hangi kararların ürünün taşıyıcısı olduğu
   ayrıldı; hiçbir kayıt silinmedi.

### Doğrulanmış durum (2026-08-19 ölçümü)

- **Testler:** `tests/` altındaki **99 testin tamamı** geçmektedir (~0,15 sn).
  `python -m compileall -q src tests` temiz.
- **14 makalelik tam koşu, DeepSeek-V4-Flash ile bu deponun kendi `scan`
  komutuyla üretilmiştir** (`output/deepseek-v4-flash/`, 19.08.2026 13:47–13:54):

  | Ölçüt | Değer |
  |---|---|
  | Belge / sayfa | 14 / 318 |
  | Toplam süre | 509 sn (~1,6 sn/sayfa) |
  | Terim adayı | 2.544 |
  | Sözlük eşleşmesi | 399 |
  | TBD kısaltması / yakın eşleşme | 9 |
  | Eksik terim (insan incelemesi) | 1.849 |
  | Metinde bulunamadığı için elenen aday | 182 (%7,2) |
  | Başarısız parça | 0 |
  | Yüzey biçimiyle kurtarılan terim (ADR-038) | 86 |
  | Bağlam denetimi işaretli eşleşme (ADR-041) | 182 |

- **Aynı küme üzerinde üç aşamanın karşılaştırması:**

  | Aşama | Aday | Sözlük eşleşmesi | Eksik terim | Elenen | Süre |
  |---|---|---|---|---|---|
  | Düzeltme öncesi (tavan 8) | 1.371 | 231 | 956 | 142 (%10,4) | 428 sn |
  | ADR-037/038 sonrası (tavan 8) | 1.351 | 240 | 997 | 68 (%5,0) | 446 sn |
  | ADR-040 sonrası (tavan 16) | 2.544 | 399 | 1.849 | 182 (%7,2) | 509 sn |

  Eşleştirme düzeltmesi uydurma oranını yarıya indirdi; tavan yükseltmesi uzman
  incelemesine giden terim sayısını 997'den 1.849'a çıkarırken uydurma oranını
  başlangıçtaki %10,4'ün altında tuttu. Toplam süre artışı %19.

### Bu rötuşta ölçülen, kapatılmayan sorunlar

1. **`8_ebpf_xdp_packet_processing.pdf` yanlış içerik taşıyor.** Dosya adı
   eBPF/XDP diyor, gerçek metin güneş paneli/fotovoltaik hakkında
   (`concentrator photovoltaic`, `downconverting layer`, `luminescence`).
   Bu, 2026-08-18 devir notunda `output/deepseek-chat/` için bildirilen sorunun
   aynısıdır; kaynak PDF hâlâ yanlış. **Bu belgenin 27 "eksik terimi" bilişim
   terimi değildir ve komiteye gönderilmemelidir.** Kod hatası değildir; küme
   kirliliğidir, doğru PDF ile değiştirilmelidir.
2. **Sözlük eşleşmelerinde anlam denetimi yoktur (ADR-041 ile kısmen ele
   alındı: tek sözcüklü eşleşmeler raporda işaretlenir, karşılığın bağlama
   uygunluğunu hâlâ insan denetler).** Eşleşme birebir dizgi
   üzerinden kurulduğu için genel sözcükler yanlış anlamla eşleşebiliyor:
   `attention` → "uyarı" (belgede 213 geçiş), `leader` → "öncü",
   `rank` → "sıra", `call` → "çağrı", `page` → "sayfa". Terim gerçekten
   sözlükte kayıtlıdır; yanlış olan, bağlama uymayan karşılığın "Sözlükte
   Bulunanlar" sekmesinde doğruymuş gibi görünmesidir. Bu bir kod hatası değil,
   TBD komitesinin karar vermesi gereken bir **politika sorusudur**: tek
   sözcüklük genel terimler ayrı bir başlık altında mı gösterilmeli?
3. **Elenen 182 adayın bir bölümü hâlâ araştırılmamıştır.** Bunlar metinde
   hiçbir yüzey biçimiyle bulunamayan adaylardır; bir kısmı modelin uydurması,
   bir kısmı ise `_is_low_quality_line` tarafından silinen satırlardan geliyor
   olabilir. Ölçülmeden yeni bir filtre gevşetmesi yapılmamıştır.

### Denenip ölçümle reddedilen fikir: çapraz-belge sıklığı

**Fikir:** Bir aday birden çok bağımsız makalede geçiyorsa gerçek bir alan terimi
olma olasılığı yüksektir; tek makalede geçiyorsa o makaleye özgüdür. Rapor buna
göre **sıralanabilir** (elenmez). Referans derlemin bedava bir taklidi.

**Ölçüm (2026-08-19, API çağrısı yapılmadan, 13 belge — `8_ebpf` hariç):**

- 1.740 benzersiz eksik terimin **%96,4'ü yalnızca tek belgede** çıkarılmış.
  İki veya daha fazla belgede geçen yalnızca 63 terim var.
- `BSGRJS18`'in 124 eksik teriminin **119'u diğer 12 belgenin metninde hiç
  geçmiyor**. Yani sıralama yapılsa 124 terimin 119'u sıfırda berabere kalırdı.
- Geçen 5 terim: `right` (8 belge), `control flow` (2), `left-hand side` (1),
  `right-hand side` (1), `systematic literature review` (1). Bunların dördü elle
  yapılan incelemede zaten **gürültü veya alan dışı** sayılmıştı. Yani sinyal
  sıralamayı iyileştirmek bir yana, gürültüyü en üste taşırdı.

**Neden çalışmadı:** 14 makale birbirinden çok uzak alt alanlardan geliyor
(transformer mimarisi, dağıtık uzlaşı, homomorfik şifreleme, WebAssembly, UML
güvenliği). Aralarında paylaşılan sözcük dağarcığı neredeyse yok.

**Mekanizma yanlış değil, derlem yanlış.** Yapay zekâ kümesindeki makaleler kendi
aralarında sinyal veriyor: `transformer`, `dropout`, `gradient`, `beam search`,
`attention head`, `positional embedding` 2-5 belgede birden çıkarılmış ve bunlar
gerçekten sağlam terimler. Yani fikir, **aynı alt alandan yeterince belge
biriktiğinde** (ör. 50 yapay zekâ makalesi) yeniden değerlendirilmelidir. Bugünkü
14 belgelik karışık kümede uygulanmamalıdır.

### Belge dışı kalan eski kayıtlar

- `data/live_benchmarks/` klasörü ve `deepseek_expanded_results.json` **çalışma
  ağacında artık yoktur** (`.gitignore` kapsamındadır). ADR-036'daki 6 makalelik
  kıyaslama tarihsel kayıt olarak durur; bugün doğrulanabilir olan ölçüm,
  yukarıdaki 14 makalelik koşudur.
- `output/deepseek-chat/` ve `output/gemini-3.7-flash/` klasörleri de artık
  diskte yoktur. Aşağıdaki 2026-08-18 bölümünün 7. ve 10. maddeleri bu
  klasörlere atıf yapar; tarihsel kayıt olarak korunmuşlardır.
- Yerel Ollama koşuları (`qwen3.8-latest`, `qwen3.5:9b-q4_K_M`)
  `output/_arsiv/` altına alınmıştır; gerekçesi `output/_arsiv/OKUBENI.md`
  içindedir. Teslim edilen sonuç kümesi yalnızca `output/deepseek-v4-flash/`.

---

## Teslim Durumu (2026-08-18)

Proje teslim edilebilir durumdadır. Bu bölüm, teslim anındaki **doğrulanmış**
durumu ve **bilinen sınırlamaları** ayrı ayrı kaydeder. Doğrulanmamış hiçbir
iddia bu belgede doğrulanmış gibi sunulmamalıdır.

### Bu teslimde yapılan düzeltmeler

1. **Sürüm denetimi kuruldu.** Depo artık git altındadır; ilk tam commit
   alınmıştır. `data/runtime/` ve `output/` `.gitignore` ile depo dışındadır;
   derleme çıktısı (`*.egg-info/`) izlemeden çıkarılmıştır.
2. **Anthropic sağlayıcı varsayılanı düzeltildi** (`api_client.py`):
   `claude-sonnet-4-20250514` → `claude-sonnet-5`. Önceki model 15 Haziran
   2026'da emekliye ayrıldı. OpenAI (`gpt-4o-mini`) ve Google
   (`gemini-2.0-flash`) varsayılanları geçerli olduğu için değiştirilmedi.

   > **Not:** Bu denetim sırasında `deepseek-v4-flash` de önce hatalı
   > sanılıp `deepseek-chat`'e çevrilmişti. Bu bir hataydı: DeepSeek-V4-Flash
   > 31 Temmuz 2026'da genel betaya, DeepSeek-V4-Pro 13 Ağustos 2026'da genel
   > kullanıma açıldı ([DeepSeek API Docs](https://api-docs.deepseek.com/updates/)) —
   > modelin kendisi eğitim kesim tarihimin (Mayıs 2026) ötesinde kalıyordu.
   > Web araması ile doğrulanıp `deepseek-v4-flash` varsayılanına geri
   > alındı. Ders: yeni bir modeli "geçersiz" işaretlemeden önce, özellikle
   > kesim tarihine yakın veya sonraki tarihli sürümlerde, doğrulama yapılmalı.
3. **API anahtarı depodan ve çalışma ağacından temizlendi.**
   `data/runtime/provider.json` içindeki anahtar alanı boşaltıldı; sağlayıcı ve
   model bilgisi korundu. **Kullanıcının yapması gereken:** eski anahtarı
   sağlayıcı panelinden iptal edip yenisini üretmek.
4. **README gerçekle hizalandı:** test sayısı (65 → 86) ve sağlayıcı model
   listesi koddaki değerlere çekildi.

### Doğrulanmış durum

- **Testler:** `tests/` altındaki **99 testin tamamı** geçmektedir (~0,15 sn).
- **Mimari:** Tek paket `src/terim_etmeni/`, tek giriş `run.py` (ADR-030).
  İşlem hattı sadedir: `PDF → parçalama → LLM aday çıkarımı → normalizasyon →
  deterministik sözlük araması → eksik terimler`.
- **Ürün kuralı korunuyor:** Sözlük üyeliği kararını model değil Python verir.
  Başarısız analizde `analysis_status = "failed"` üretilir ve **hiç rapor dosyası
  yazılmaz** — yani "0 eksik terim" yanılsaması kod düzeyinde engellenmiştir.
- **Sözlük:** 30.247 kayıt, 28.492 benzersiz İngilizce terim (sürüm 2026-07-20).
  Etkinleştirme `os.replace` ile atomiktir ve doğrulama sonrasıdır (ADR-004).
- **DeepSeek canlı kıyaslaması (ADR-036) doğrulanabilirdir.**
  `data/live_benchmarks/deepseek_expanded_results.json` verisi 6 makale,
  224 sayfa, 232 parça ve toplam 321,2 saniye bildirmektedir — parça başına
  ~1,4 saniye. Bu hız gerçek bir bulut API çağrısıyla tutarlıdır ve kayıttaki
  sayılar kendi içinde tutarlıdır.

### Bilinen sınırlamalar (teslim kapsamı dışında bırakıldı)

Bunlar bilinçli olarak bu teslimde kapatılmamıştır. Aceleyle yapılacak bir
düzeltme, teslim edilen çalışan sürümü bozma riski taşıdığı için tercih
edilmemiştir.

1. **Yerel sunucuda çapraz-köken koruması yoktur.** `web_app.py` içindeki POST
   uç noktaları `Origin`, `Host` veya oturum belirteci doğrulaması yapmaz.
   Uygulama yalnızca `127.0.0.1` dinlediği için dışarıdan erişilemez; ancak
   uygulama açıkken ziyaret edilen kötü niyetli bir web sayfası
   `/settings/save` adresine form gönderip sağlayıcı adresini değiştirebilir.
   **Öneri:** ağ erişimi açılmadan önce mutlaka kapatılmalıdır.
2. **Uzun analiz tek senkron HTTP isteği içinde yürür.** İlerleme bildirimi,
   iptal veya kaldığı yerden devam yoktur. Ölçülen hız sayfa başına ~1,3–1,4
   saniyedir; 224 sayfalık bir küme tek bağlantıda beş dakikanın üzerindedir.
   `MAX_CONCURRENT_ANALYSES = 1` olduğu için bu süre boyunca ikinci belge
   503 alır.
3. **Kaynakça temizliği yalnızca başlığın bulunduğu sayfada çalışır.**
   `clean_extracted_text` sayfa başına çağrıldığı için sonraki kaynakça
   sayfaları modele gider. Köşeli ayraçlı (`[3]`) biçimler tesadüfen elenir,
   numaralı ve düz biçimler elenmez.
4. **Kısaltma eşlemesi büyük/küçük harfe duyarsızdır.** Kısaltma listesindeki
   1.199 kaydın 759'u üç karakter veya daha kısadır; `set`, `art`, `pin`, `as`
   gibi 17 sıradan sözcük bir TBD kısaltmasıyla çakışmaktadır. Bu durumda
   incelenmesi gereken bir terim "eksik terimler" listesinden çıkıp
   "TBD Kısaltması" grubuna düşebilir.
5. **`singular_key` kısaltmalarda gövde kırpar** (`HTTPS` → `http`,
   `CORS` → `cor`). Bugün zarar görünmemektedir; denetim sırasında bu
   biçimlerin hiçbiri mevcut sözlükte karşılık bulmamıştır. Sözlük büyüdükçe
   sahte "sözlükte bulundu" üretme riski taşır.
6. **Aynı adlı belge önceki raporun üzerine yazar.** Çıktı yolu
   `output/<model>/<belge-adı>/` olduğu için aynı model ve aynı dosya adıyla
   yapılan ikinci analiz ilk raporu uyarısız siler.
7. **`output/gemini-3.7-flash/` verisi bu depodaki otomatik işlem hattından
   üretilmemiştir.** Proje sahibinden gelen bilgiye göre bu koşular
   Google Antigravity IDE'sinde Gemini 3.7 Flash modeliyle **canlı, elle
   yürütülen bir oturumdan** geliyor — `api_client.py`/`service.py` üzerinden
   programatik olarak çağrılmamış. Antigravity ve Gemini 3.7 Flash'ın gerçek
   ürünler olduğu doğrulandı ([Google Antigravity duyurusu](https://antigravity.google/blog/gemini-3-7-flash-in-google-antigravity)).
   Buna göre: bu klasördeki `duration_seconds` gibi süre alanları, DeepSeek'in
   bu depodaki betikle üretilmiş otomatik kıyaslamasıyla (ADR-036) doğrudan
   karşılaştırılabilir **değildir** — farklı bir süreçten geliyorlar ve bu
   depodaki `scan`/`serve` komutlarıyla yeniden üretilemezler.
   `output/comparison_deepseek_vs_gemini37.json` da aynı nedenle yalnızca
   bilgi amaçlıdır, ölçülebilir bir kıyaslama değildir. ADR-036'nın dayandığı
   DeepSeek verisi bu deponun kendi betiğiyle üretildiği için ayrıdır ve
   yukarıda belirtildiği gibi doğrulanabilirdir.
8. **Python 3.9 desteği sınanmamıştır.** `pyproject.toml` `>=3.9` demektedir;
   geliştirme 3.14 üzerinde yürümüştür ve sürekli tümleştirme yoktur.
9. **Başlatıcılarda bağımlılık denetimi yoktur.** `pdfplumber` kurulu olmayan
   temiz bir bilgisayarda program Türkçe açıklama yerine ham `ImportError`
   ile kapanır. `BASLAT_WINDOWS.bat` içindeki `%errorlevel%` bir parantez
   bloğunun içinde erken genişlemektedir; `py` dalı güvenilir değildir.
10. **Eksik terim hacmi büyük ölçüde beklenen davranıştır; iki dar kapsamlı
    gerçek sorun ölçüldü.** 8 gerçek DeepSeek raporundaki (`output/deepseek-chat/`)
    381 "eksik terim" kaydı bu depodaki güncel eşleme koduyla yeniden
    kontrol edildi (2026-08-18):
    - **Sözlük eşleme katmanında sıfır hata bulundu.** 381 kaydın tamamı
      gerçekten TBD sözlüğünde yok; yanlışlıkla "eksik" damgalanmış tek bir
      kayıt yok.
    - **TBD sözlüğü (30.247 kayıt) temel derin öğrenme kavramlarını zaten
      içeriyor** (`attention mechanism`, `convolutional neural network`,
      `backpropagation`, `gradient descent`, `fine-tuning`, `pretrained`,
      `deep learning` vb. sözlükte kayıtlı). Buna karşın `softmax`, `dropout`,
      `BLEU` sözlükte **sıfır** eşleşme veriyor — modern literatürün çok
      spesifik jargonu henüz kapsanmamış. Bu, sözlüğün zayıflığı değil,
      alanın hızla büyümesinin doğal sonucu.
    - **camelCase/protokol kimlik sızması (gerçek, dar kapsamlı sorun):**
      369 terimin 9'unda (~%2), `term_extraction.py`'deki istemin **açıkça
      yasakladığı** kod/RPC değişken adları (`candidateId`, `AppendEntries`,
      `prevLogTerm`, `RequestVoteRPC`) sızmış — hepsi tek belgede
      (`3_raft_consensus_algorithm.pdf`). İstem zaten bu türden örnekleri
      yasaklıyor (`SYSTEM_PROMPT` içinde "candidateId, AppendEntries,
      prevLogIndex, matchIndex" örnekleri var) ama pratikte tam
      uygulanmıyor. **Düzeltme önerisi:** `USER_TASK` içindeki
      "STRICT EXCLUSIONS" listesine camelCase/RPC alan adı yasağını
      açıkça ekleyip gerçek bir API anahtarıyla ölçmek. Bu denetim
      sırasında geçerli bir anahtar olmadığı için (kullanıcının kendi
      anahtarı iptal edilip henüz yenisi üretilmedi) **uygulanmadı** —
      `AGENTS.md`'nin "ölçmeden değiştirme" kuralı gereği.
    - **Sunum/algı sorunu (kod değil, politika kararı):** Eksik terimlerin
      %61'inde (218/360, camelCase ve yanlış etiketli `8_ebpf_...` belgesi
      hariç) terimi oluşturan **her kelime** sözlükte başka bağlamda zaten
      geçiyor (`embedding`, `Transformer`, `attention heads`, `batch size`
      gibi) — tam ifade kayıtlı olmasa da okuyana "zaten biliniyor" hissi
      veriyor. Bunu koddan filtrelemek `ADR-028`'in reddettiği türden bir
      sezgisel filtre olur ve yanlış pozitif riski taşır (`hidden
      representations` gibi gerçekten yeni bir kavramı, bileşen kelimeleri
      başka yerde geçiyor diye gizleyebilir). Bu, TBD komitesinin "eksik"
      tanımını nasıl belirlediğine dair bir **politika sorusu** —
      kod değişikliği değil.
    - **`output/deepseek-chat/8_ebpf_xdp_packet_processing/` yanlış PDF
      içeriyor** — dosya adı eBPF/XDP diyor ama gerçek içerik güneş paneli/
      fotovoltaik hakkında (önceki kaotik oturumlardan kalma kirli test
      verisi, kaynak PDF artık diskte yok). Kod hatası değil; bu klasördeki
      12 "eksik terim" göz ardı edilmeli.

### Bir sonraki geliştirici için sıra

Öncelik sırası: (1) çapraz-köken koruması, (2) analizi arka plan işine taşımak
ve ilerleme göstermek, (3) kaynakça/kısaltma/tekilleştirme düzeltmeleri,
(4) camelCase/RPC sızmasını istem düzeyinde kapatıp gerçek bir API anahtarıyla
ölçmek (madde 10), (5) ölçüm altyapısı (altın küme + kayıt-yeniden oynatma
testleri).

Kalıcı ürün veya mimari kararı `docs/DECISIONS.md` içine yeni bir ADR olarak
eklenmelidir. Yukarıdaki 3, 4 ve 5 numaralı maddelerin düzeltilmesi davranış
değişikliği olduğu için birer ADR gerektirir.

---

## Zorunlu Doğrulama Komutları

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Uygulamayı başlatmak için:

```bash
python3 run.py
```

*(Tarayıcıda otomatik olarak `http://127.0.0.1:8876` açılır.)*

---

## Önceki Mimari Özeti (2026-08-15)

Aşağıdaki başlıklar ADR-030 – ADR-036 arasındaki çalışmanın özetidir ve
tarihsel kayıt olarak korunmuştur.

- **Çift Model Sağlayıcı Geçişi ve Çıktı Yalıtımı:** DeepSeek ↔ Google Gemini
  geçişleri (`/settings` ve `provider.json`) test edilmiştir. Raporlar
  `output/<model>/<belge>/` hiyerarşisinde birbirini ezmeden saklanır ve
  `/reports/<file>` uç noktasıyla indirilebilir.
- **2 Sekmeli Excel (.xlsx) ve CSV:** `Eksik Terimler (İnceleme)` ve
  `Sözlükte Bulunanlar` sekmeleri, freeze-pane (`A5`), otomatik filtre ve
  insan incelemesi için boş komite sütunları (Sütun 4 ve Sütun 8) openpyxl ile
  doğrulanmıştır. Türkçe özel karakterler ve UTF-8-SIG noktalı virgüllü CSV
  uçtan uca sınanmıştır.
- **Morfoloji ve Çoğul İyileştirmesi (ADR-035):** Düzensiz bilişim çoğulları
  (`matrices` → `matrix`, `indices` → `index`, `criteria` → `criterion` vb.) ve
  Grek/Latin kökenli `-ses` → `-sis` kuralı eklenmiştir. Türkçe noktalı `İ`
  normalizasyonu ve Unicode tire standardizasyonu tamamlanmıştır.
- **Web ve Güvenlik Katmanı:** Tüm HTTP uç noktaları test edilmiştir. Hatalı
  istek korumaları (boş dosya, PDF olmayan yükleme, 60 MB üzeri istek, geçersiz
  gövde) Türkçe 400 yanıtı verir. Güvenlik başlıkları (`X-Frame-Options`,
  `X-Content-Type-Options`, `Referrer-Policy`, `Content-Security-Policy`,
  `Cache-Control`) tüm sayfalarda zorunludur. Yalnızca loopback (`127.0.0.1`,
  `localhost`, `::1`) bağlantılarına izin verilir. Rapor indirmelerinde
  Path Traversal ve izinsiz uzantılar engellenir.
- **Servis Katmanı ve Eşzamanlılık:** `MAX_CONCURRENT_ANALYSES = 1` kısıtı
  `analyze_upload` ve `analyze_path` üzerinde işletilir; kapasite aşımında 503
  döner. Hata durumunda dahi geçici dosyaların silinmesi ve kilitlerin serbest
  bırakılması `finally` blokları ve testlerle teminat altındadır.
- **Excel Güvenliği:** Geçersiz XML kontrol karakterleri (`\x00`–`\x1f`,
  form-feed `\x0c`) `_clean_str` ile ayıklanarak `openpyxl`'in çökmesi
  engellenir.
- **PDF Okuyucu:** Numaralı bölüm başlıklarını (`12. References`,
  `VIII. References`, `References and Notes`) kapsayan kaynakça temizliği ve
  formül/kod filtresi entegre edilmiştir. (Sınırlaması için yukarıdaki
  "Bilinen sınırlamalar" 3. maddeye bakınız.)
