# Yapay Zekâ / Geliştirici Devir Notu (AI Hand-off)

## Güncel Durum ve Mimari Özeti (2026-08-15)

Proje tek, temiz, modern, güvenli ve kurşungeçirmez bir mimaridedir (ADR-030 - ADR-035):

- **Tek Paket:** `src/terim_etmeni/` ve giriş noktası `run.py`.
- **Birim ve Entegrasyon Testleri:** `tests/` altında **86 testin tamamı** ~0.14 saniyede eksiksiz geçmektedir (`tests/test_provider_transition_and_excel.py` dahil).
- **Çift Model Sağlayıcı Geçişi ve Çıktı Yalıtımı:**
  - DeepSeek (`deepseek-chat`) $\leftrightarrow$ Google Gemini (`gemini-2.5-flash`) geçişleri (`/settings` ve `provider.json`) test edilip doğrulandı.
  - Raporların `output/<model>/<stem>/` hiyerarşisinde (`output/deepseek-chat/` ve `output/gemini-2.5-flash/`) birbirini ezmeden yalıtılmış olarak saklandığı ve `/reports/<file>` uç noktasıyla güvenli indirilebildiği doğrulandı.
- **Gemini Excel (.xlsx) ve CSV openpyxl Denetimi:**
  - 2 sekmeli Excel yapısı (`Eksik Terimler (İnceleme)` ve `Sözlükte Bulunanlar`), freeze-pane (`A5`), showGridLines doğrulandı.
  - İnsan incelemesi için tasarlanan boş komite sütunları (Sütun 4: `Önerilen Türkçe Karşılık (Komite)` vurgulu `FFFDF0` kutusu ve Sütun 8: `Komite Notu / Karar`) kontrol edildi.
  - Türkçe özel karakterler (`ç, Ç, ğ, Ğ, ı, İ, ö, Ö, ş, Ş, ü, Ü, â, î, û`) ve noktalı virgüllü UTF-8-SIG CSV senkronizasyonu openpyxl ile uçtan uca test edildi.
- **Genişletilmiş Canlı DeepSeek Benchmark Başarısı (ADR-036):**
  - 6 yeni ileri bilişim makalesi (DeepSeek-R1, Latent Diffusion, Google Spanner, Kademlia DHT, DRAM Rowhammer, Quantum Surface Codes) 224 sayfa ve 232 metin parçası boyunca DeepSeek API ile uçtan uca taranmış ve **%100 başarıyla (0 çökme, 0 parça kaybı)** tamamlanmıştır (`data/live_benchmarks/deepseek_expanded_results.json`).
  - Çıktılar `output/deepseek-chat/<makale>/` altında 2 sekmeli Excel (.xlsx), CSV (.csv) ve JSON (.json) formatlarında kaydedilmiş ve openpyxl ile doğrulanmıştır.
- **Morfoloji ve Çoğul İyileştirmesi (ADR-035):**

  - Düzensiz bilişim çoğulları (`matrices` -> `matrix`, `indices` -> `index`, `criteria` -> `criterion`, `caches` -> `cache`, `buses` -> `bus`) ve Grek/Latin kökenli `-ses` -> `-sis` kuralı (`analyses` -> `analysis`, `hypotheses` -> `hypothesis`) ile TBD sözlüğündeki **320'den fazla terim** sahte eksik terim olmaktan kurtarılmıştır.
  - Türkçe noktalı `İ` normalizasyonu ve Unicode tire standardizasyonu (`\u2015`) tamamlanmıştır.
- **Web ve Güvenlik Katmanı:**
  - Tüm HTTP uç noktaları (`GET /`, `GET /settings`, `POST /settings`, `GET /dictionary`, `POST /api/analyze`, `POST /api/dictionary/update`, `GET /healthz`, `GET /reports/<file>`) test edildi ve doğrulandı.
  - Hatalı istek korumaları: Boş dosya, PDF olmayan yükleme, 60MB üzeri aşırı büyük istek, geçersiz urlencoded/multipart gövde, eksik form alanları durumunda Türkçe açıklayıcı 400 Bad Request yanıtları verilir.
  - Güvenlik başlıkları (`X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `Content-Security-Policy`, `Cache-Control: no-store`) tüm sayfalarda ve dosya indirmelerinde zorunludur.
  - Yalnızca güvenli loopback (`127.0.0.1`, `localhost`, `::1`) bağlantılarına izin verilir; harici/LAN IP'ler reddedilir.
  - Rapor indirmelerinde Path Traversal (`../`) ve izinsiz uzantılar engellenir.
- **Servis Katmanı ve Eşzamanlılık:**
  - `MAX_CONCURRENT_ANALYSES = 1` kısıtı `analyze_upload` ve `analyze_path` üzerinde işletilir; kapasite aşımında 503 meşgul yanıtı döner.
  - Analiz sırasında veya model çağrısında hata oluşsa dahi geçici dosyaların (`tempfile`) silinmesi ve kilitlerin serbest bırakılması `finally` bloklarıyla teminat altındadır.
- **Raporlama ve Excel / CSV Güvenliği:**
  - 2 sekmeli Excel (.xlsx) ve UTF-8-SIG noktalı virgüllü CSV (.csv) raporları üretilir.
  - `openpyxl`'in çökmesini engellemek için metinlerdeki geçersiz XML kontrol karakterleri (`\x00`–`\x1f`, form-feed `\x0c`) `_clean_str` ile otomatik ayıklanır.
  - Türkçe özel karakterler (`ç, Ç, ğ, Ğ, ı, İ, ö, Ö, ş, Ş, ü, Ü, â, î, û`), uzun metinler ve formül sembolleri başarıyla doğrulanmıştır.
- **PDF Okuyucu:**
  - Numaralı bölüm başlıklarını (`12. References`, `VIII. References`, `References and Notes`) kapsayan kaynakça temizliği ve formül/kod filtresi entegre edilmiştir.

---

## Zorunlu Doğrulama Komutları

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```

Uygulamayı başlatmak için:
```bash
python3 run.py
```
*(Tarayıcıda otomatik olarak `http://127.0.0.1:8876` açılır).*



