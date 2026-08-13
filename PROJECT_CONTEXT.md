# Türkçe Terim Etmeni — Proje Bağlamı

> Bu dosya projenin kalıcı bağlamıdır. Yeni bir sohbet, geliştirici veya yapay
> zekâ önce bu dosyayı, ardından `DECISIONS.md` ve `V2_ROADMAP.md` dosyalarını
> okumalıdır. Sohbet içinde alınan kararlar burada yazmıyorsa kalıcı karar
> sayılmaz.

## Ürün amacı

İngilizce bir bilişim makalesi PDF olarak yüklenir. Program makaledeki gerçek
teknik terim adaylarını çıkarır ve güncel TBD Bilişim Terimleri Sözlüğü ile
karşılaştırır. Uzmanın asıl görmek istediği çıktı, sözlükte bulunmayan ve insan
incelemesi gerektiren terimlerdir.

Program sözlüğe kendiliğinden terim eklemez ve Türkçe karşılığın doğruluğu
konusunda nihai karar vermez. Son karar Tuncer Ören ve TBD çalışma grubundaki
uzmanlara aittir.

## Hedef kullanıcı ve kullanım

- Birincil kullanıcı: Emeritüs Prof. Dr. Tuncer Ören gibi alan uzmanları.
- Ana akış mümkün olduğunca basit olmalıdır: güncel sözlük durumu, makale seçimi,
  analiz, karar listesi ve Excel indirme.
- Model, parça boyutu, Ollama adresi ve sözlük dönüştürme gibi teknik ayrıntılar
  ana kullanıcı ekranını kalabalıklaştırmamalıdır.
- Kurum sunucusunda tarayıcı bağlantısıyla kullanım olası nihai dağıtım biçimidir;
  hedef donanım ve erişim politikası henüz doğrulanmamıştır.

## Değişmez ürün kuralları

1. Sözlükte bulunma kararını dil modeli değil deterministik Python kodu verir.
2. Dil modeli yalnız teknik terim adayı üretir veya adayları yardımcı sinyal
   olarak değerlendirir.
3. Başarısız ya da kısmi model çalışması kullanıcıya "0 eksik terim" olarak
   sunulmaz.
4. Her rapor kullanılan sözlük sürümünü ve modeli kaydeder.
5. Yeni sözlük doğrulanmadan etkin sözlüğün üzerine yazılmaz; son sağlam sürüm
   korunur.
6. Terim salkımları ve yapay zekâ seçkileri ana sözlüğün alt kümeleridir; ayrı
   sözlükler gibi ana veriye yeniden eklenmez.
7. Kısaltmalar sözlüğü ana sözlükten ayrı bir kaynak olarak ele alınacaktır.
8. Gerçek makale kabul kümesi olmadan model ya da filtre kalitesi hakkında kesin
   üstünlük iddiası yapılmaz.

## V1 ve V2

### V1 — korunmuş çalışan prototip

- Paket: `src/terim_etmeni/`
- Giriş: `run.py`
- Testler: `tests/`
- Git'teki güvenli taban: `main` dalı ve `6e98514` commit'i
- V1 üzerinde V2 geliştirmesi yapılmaz. Yalnız kritik V1 düzeltmeleri ayrı ve
  bilinçli değişiklik olarak ele alınır.

### V2 — etkin geliştirme

- Paket: `src/terim_etmeni_v2/`
- Giriş: `run_v2.py`
- Testler: `tests_v2/`
- Dal: `codex/v2`
- V2 ilk aşamada V1'in doğrulanmış PDF okuma, Ollama ve analiz çekirdeğini yeniden
  kullanabilir. Bu geçiş uyumluluğudur; V1 dosyalarını değiştirme izni değildir.

## Veri kaynakları

- Ana kaynak: TBD Bilişim Sözlüğü, İngilizce–Türkçe yönü.
- Mevcut başlangıç verisi:
  `data/tbd_dictionary_2026_coordinate.json`
- Kaynak PDF'den çıkarılmış metadata:
  - sürüm: `2026-07-20`
  - ham kayıt: `30247`
  - benzersiz İngilizce terim: `28492`
  - sayfa: `599`
- Kaynak site: <https://bilisimde.ozenliturkce.org.tr/>
- Site zaman zaman otomatik isteklere doğrulama ekranı döndürebilir. Otomatik
  güncelleme başarısız olduğunda uygulama son sağlam yerel sözlükle çalışmalıdır.

## Bilinen belirsizlikler

- Kurumun sunucusu, işletim sistemi, RAM'i ve GPU'su bilinmiyor.
- İnternet/VPN erişim biçimi ve kullanıcı girişi gereksinimi bilinmiyor.
- Kurumun kullandığı Excel şeması görülmedi; Excel zorunlu değildir.
- Kısaltmalar sözlüğünün makinece okunabilir resmî dosya adresi doğrulanmadı.
- TBD verisinin yeniden dağıtım ve otomatik indirme koşulları kurum tarafından
  doğrulanmalıdır.

## Yeni geliştirici için çalışma kuralı

1. `PROJECT_CONTEXT.md`, `DECISIONS.md`, `V2_ROADMAP.md` ve `AI_HANDOFF.md` oku.
2. `git status --short --branch` ile dalı ve kullanıcı değişikliklerini kontrol et.
3. V1 ve V2 testlerini çalıştır.
4. Bir varsayım ürün davranışını değiştirecekse `DECISIONS.md`ye kaydet.
5. Geliştirme sonunda `AI_HANDOFF.md` içindeki mevcut durum ve sonraki adımı
   güncelle.
6. Çalışan davranışı ölçmeden filtre, model veya sözlük kaynağı değiştirme.

