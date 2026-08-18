# Yapay Zekâ / Geliştirici Devir Notu (AI Hand-off)

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

- **Testler:** `tests/` altındaki **86 testin tamamı** geçmektedir (~0,15 sn).
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
