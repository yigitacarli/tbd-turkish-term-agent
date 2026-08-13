# V2 İsteğe Bağlı Kurum Sunucusu Hazırlık Formu

Kişisel bilgisayarda yerel kullanım birincil hedeftir. Bu form yalnız ileride
kurum sunucusu istenirse kararları varsayımla değil, kurumun gerçek altyapısı ve
veri politikasıyla vermek için kullanılır.

## Mevcut güvenli durum

- Uygulama yalnız `localhost`, `127.0.0.1` veya `::1` üzerinde dinler.
- Aynı anda tek analiz çalışır; ikinci istek HTTP 503 ile açıkça reddedilir.
- Yüklenen geçici PDF analiz sonunda silinir.
- JSON, CSV, Excel ve replay için temizlenmiş sayfa metni taşıyan aday snapshot'ı
  `output_v2/` altında kalır.
- HTTP erişim günlüğü tutulmaz. HTTPS ve kullanıcı girişi henüz yoktur.
- `GET /healthz` yalnız uygulamanın HTTP yanıtı verebildiğini gösterir; Ollama,
  sözlük veya disk sağlığını doğrulamaz.

## Kurumdan alınacak bilgiler

### 1. Sunucu

- İşletim sistemi ve sürümü:
- CPU ve çekirdek sayısı:
- RAM:
- GPU, VRAM ve sürücü:
- Kullanılabilir disk alanı:
- Ollama kurulmasına izin var mı:
- Sunucunun internete çıkış izni var mı:

### 2. Kullanım ve erişim

- Tek kullanıcı mı, çok kullanıcı mı:
- Beklenen eşzamanlı kullanıcı ve günlük PDF sayısı:
- Yalnız sunucu başında mı, kurum LAN/VPN üzerinden mi, internetten mi:
- Kurumun ters vekil/HTTPS hizmeti var mı:
- Tercih edilen kimlik doğrulama: kurum SSO, ters vekil hesabı veya başka yöntem:
- Yönetici ile normal kullanıcı ayrımı gerekli mi:

### 3. Belge ve rapor politikası

- Kaynak PDF cihazdan veya kurum ağından çıkabilir mi:
- Rapor ve aday snapshot'ı kaç gün saklanmalı:
- Temizlenmiş tam sayfa metni snapshot'ta saklanabilir mi:
- Raporları kimler indirebilir ve silebilir:
- Yedeklenecek içerik ve yedek saklama süresi:
- Günlüklerde belge/model/kullanıcı adlarından hangileri tutulabilir:
- TBD sözlük verisinin kurum içinde saklanması ve yedeklenmesi onaylı mı:

## Üretim kabul kapısı

Bilgiler tamamlandıktan sonra aşağıdakilerin tümü doğrulanır:

1. Seçilecek model beş sabit kabul belgesinde kalite, süre, RAM ve GPU kullanımıyla
   ölçülür; geliştirme bilgisayarındaki model sıralaması varsayılmaz.
2. Eşzamanlı analiz sınırı hedef sunucuda yük testiyle belirlenir.
3. HTTPS ve kimlik doğrulama uygulamanın ağ erişimi açılmadan önce çalışır.
4. PDF, rapor, snapshot, günlük ve yedek saklama/silme davranışı kurum politikasıyla
   test edilir.
5. Başarısız ve kısmi analizler kullanıcıya sıfır sonuç gibi gösterilmez.
6. Etkin sözlük, kısaltma kaynağı, model ve uygulama sürümü raporda izlenebilir
   kalır.
