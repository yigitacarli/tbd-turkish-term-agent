# Yapay Zekâ / Geliştirici Devir Notu (AI Hand-off)

## Güncel Durum ve Mimari Özeti (2026-08-14)

Proje, eski dağınık V1/V2 ve yarım kalmış V3 parçalarından tamamen arındırılarak tek, temiz, modern ve kurşungeçirmez bir mimariye dönüştürülmüştür (ADR-030).

- **Tek Paket:** `src/terim_etmeni/`
- **Giriş Noktası:** `run.py` (CLI komutları: `serve`, `scan`, `dictionary`, `abbreviations`, `evaluate-expected`)
- **Web Arayüzü:** `src/terim_etmeni/web_app.py` (Bağımsız standart kütüphane HTTP sunucusu, sıfır dış JS/CSS bağımlılığı)
- **Birim Testler:** `tests/` altında 63 testin tamamı 0.025 saniyede başarıyla geçmektedir.
- **İşlem Hattı:** `PDF → LLM Çıkarımı (few-shot) → Normalizasyon + Tekil/Çoğul Eşleme → Deterministik TBD Sözlük Araması → Eksik Terim Raporlama (Web / Excel / CSV / JSON)`.

---

## Önemli Özellikler ve Tasarım İlkeleri

### 1. Akademik ve Zamansız (Timeless) Web Arayüzü
- **Prof. Dr. Tuncer Ören Standartları:** Sıfır emoji, ciddi ve kurumsal Türkçe, 16px+ yüksek kontrastlı tipografi (`#1e3a5f` TBD laciverti).
- **Geleceğe Uyumlu API Ayarları:** Yıllar sonra eskiyecek geçici model isimleri kaldırıldı; kullanıcının dilediği güncel modeli yazabileceği serbest alan ve resmî dokümantasyon referansları eklendi.
- **Maskeli API Anahtarı:** Kayıtlı anahtar arayüzde `••••••••••••••••` olarak korunur; ayar güncellendiğinde silinmez.

### 2. Çoklu Sağlayıcı (Provider) Desteği
- **Google Gemini:** `gemini-2.5-flash`, `gemini-2.0-flash`, `gemini-1.5-flash`, `gemini-1.5-pro` (saf JSON modu, 4096 token tavanı, Google AI Studio ücretsiz kotası ile tam uyum).
- **OpenAI (ChatGPT):** `gpt-4o-mini`, `gpt-4o`, `gpt-4-turbo`, `o1-mini`, `o3-mini` (Standart modellerde JSON modu, reasoning modellerinde `max_completion_tokens`).
- **DeepSeek:** `deepseek-chat` (V3) ve `deepseek-reasoner` (R1) (Düşünme zinciri içinden JSON ayıklama desteği).
- **Anthropic (Claude):** `claude-3-5-sonnet-latest`, `claude-3-5-haiku-latest`, `claude-3-7-sonnet-latest`.
- **Yerel Ollama:** `http://127.0.0.1:11434` üzerinden cihazdaki yerel modeller (`deepseek-r1:8b`, `llama3:8b`, `qwen2.5:7b` vb.) ile %100 çevrimdışı çalışma.
- **Çapraz Adres İzolasyonu:** Bir sağlayıcı seçildiğinde diğer firmanın base URL'i otomatik olarak temizlenir, asla çapraz istek gönderilmez.

### 3. Deterministik Morfolojik / Çoğul Eşleme (ADR-032)
- Sözlükte tekili bulunan (`transaction`, `public key`, `trusted third party`, `block header`) kelimelerin çoğul varyantları (`transactions`, `public keys`, vb.) sahte eksik terim olarak işaretlenmez; doğrudan **Sözlükte Bulundu (Çoğul Eşleşme)** olarak sınıflandırılır.
- Eksik terim adaylarında aynı kavramın tekil ve çoğul varyantları (`downstream task` ve `downstream tasks`) tek bir kanonik madde altında birleştirilir.

### 4. Hata ve Raporlama Güvenliği
- Analiz başarısız olduğunda (`status == 'failed'`) `output/` klasörüne boş rapor dosyaları yazılmaz.
- Hata durumunda ekranda indirme butonları yerine doğrudan sunucudan dönen hata ayrıntısı ve çözüm adımlarını içeren bilgilendirme paneli açılır.

---

## Zorunlu Doğrulama Komutları

Herhangi bir değişiklik sonrasında çalıştırılması gereken komut:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```

Uygulamayı başlatmak için:
```bash
python3 run.py
```
*(Tarayıcıda otomatik olarak `http://127.0.0.1:8876` açılır).*
