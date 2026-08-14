# Yapay Zekâ / Geliştirici Devir Notu (AI Hand-off)

## Güncel Durum ve Mimari Özeti (2026-08-14)

Proje tek, temiz, modern ve kurşungeçirmez bir mimariye dönüştürülmüştür (ADR-030):

- **Tek Paket:** `src/terim_etmeni/`
- **Giriş Noktası:** `run.py` (CLI komutları: `serve`, `scan`, `dictionary`, `abbreviations`, `evaluate-expected`)
- **Web Arayüzü:** `src/terim_etmeni/web_app.py` (Bağımsız standart kütüphane HTTP sunucusu, sıfır dış JS/CSS bağımlılığı, 18px+ ferah ve yüksek kontrastlı tipografi)
- **Birim Testler:** `tests/` altında **65 testin tamamı** saniyenin onda birinde başarıyla geçmektedir.
- **Raporlama:** 2 sekmeli profesyonel Excel (`.xlsx`) — 1. Sekme: Bağlam cümleli ve komite çalışma sütunlu Eksik Terimler, 2. Sekme: Sözlükte Bulunanlar.
- **Kota Yönetimi:** Google Gemini (5 RPM) ve bulut sağlayıcıları için HTTP 429 otomatik bekleme ve tekrar deneme mekanizması aktif.
- **Git & Gizlilik:** `data/runtime/`, `output/`, `pdfs/` ve `ornek_makaleler/` tamamen `.gitignore` altındadır; kişisel API anahtarları asla Git'e gitmez.

---

## Sıradaki Hedef / Yeni Sohbet Görevi

1. **Masaüstü Kurulum Paketleri (Installer / Setup):**
   - **Windows:** PyInstaller + Inno Setup ile tek tıklamalık `TurkceTerimEtmeni_Setup.exe` kurulum sihirbazı.
   - **macOS:** PyInstaller ile `.dmg` veya bağımsız `.app` paketlemesi.
2. **Özel Uygulama İkonu (App Icon):**
   - TBD ve Özenli Türkçe ruhunu yansıtan, yüksek çözünürlüklü şık bir kurumsal uygulama ikonu (`.ico` ve `.icns`).
3. **Kök Dizin Temizliği:**
   - Eski `BASLAT_WINDOWS.bat` ve `BASLAT_APPLE.command` dosyaları kurulum paketleri gelince kaldırılacaktır.

---

## Zorunlu Doğrulama Komutları

Herhangi bir değişiklik sonrasında çalıştırılması gereken komut:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Uygulamayı başlatmak için:
```bash
python3 run.py
```
*(Tarayıcıda otomatik olarak `http://127.0.0.1:8876` açılır).*
