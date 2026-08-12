# İleride Yapay Zekâ Geliştirmeleri İçin Proje Notu

## Görev

Projenin adı **TBD Dictionary Control**. Metin katmanlı PDF'lerdeki İngilizce bilişim
terimlerini çıkarır, `data/tbd_dictionary_2026_coordinate.json` içindeki
İngilizce–Türkçe sözlükle karşılaştırır ve özellikle sözlükte bulunmayan terimleri
listeler.

Kaynak sözlük sitesi: https://bilisimde.ozenliturkce.org.tr/

## Mevcut durum

- Python 3.9+ ile çalışır.
- Yerel model sağlayıcısı Ollama'dır.
- Varsayılan model `qwen3.5:2b`; model adı CLI, web arayüzü veya `OLLAMA_MODEL`
  ile değişebilir.
- Yerel web arayüzü `python3 run.py` ile açılır.
- CLI: `python3 run.py scan <pdf-veya-klasör>`.
- CSV ve JSON raporları `output/` altında oluşturulur.
- PDF sayfa numaraları ve terim geçiş sayıları korunur.
- Bulunan, olası, eksik ve elenen adaylar ayrı raporlanır.
- Üretim akışı varsayılan olarak tek geçişli model aday çıkarımı yapar;
  `OllamaClient` deneyler için iki geçişi destekler ancak CLI ve web arayüzü bu
  seçeneği henüz açmaz. Çok sözcüklü sözlük terimleri ayrıca deterministik taranır.
- Sözlükte olmayan tek sözcükler ve teknik kısaltmalar sessizce elenmez; düşük
  öncelikli inceleme adayı olarak korunur.
- Modelin kaçırdığı kontrollü teknik baş kalıpları ve açıkça tanımlanan
  kısaltma açılımları deterministik olarak geri kazanılır; ham n-gram üretilmez.
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

Son temizlemede 33 test başarılıydı. Yeni değişikliklerden sonra bu komut yeniden
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
