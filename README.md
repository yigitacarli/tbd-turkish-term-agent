# Türkiye Bilişim Derneği — Türkçe Terim Etmeni

İngilizce bilişim makalelerindeki (PDF) teknik terimleri yapay zekâ ile çıkaran, **TBD Bilişim Terimleri Sözlüğü** ile deterministik olarak karşılaştıran ve sözlükte henüz yer almayan eksik terimleri tespit eden açık kaynaklı denetim sistemi.

---

## 🚀 Hızlı Başlangıç

### 1. Çift Tıklayarak Başlatma (En Kolay Yol)
- **macOS:** Klasördeki `BASLAT_APPLE.command` dosyasına çift tıklayın.
- **Windows:** Klasördeki `BASLAT_WINDOWS.bat` dosyasına çift tıklayın.

*(Program arka planda başlayacak ve tarayıcınızda otomatik olarak `http://127.0.0.1:8876` adresini açacaktır).*

---

### 2. Terminal ile Başlatma

```bash
# Bağımlılıkları yükleyin
pip install -e .

# Uygulamayı başlatın
python3 run.py
```

---

## 🎯 Temel Özellikler

- **Deterministik Sözlük Eşlemesi:** Yapay zekâ sözlük kararı vermez; 30.247 terimlik TBD Bilişim Sözlüğü ile doğrudan kod seviyesinde matematiksel eşleme yapılır.
- **Akıllı Çoğul Eşleme:** Metindeki çoğul terimler (`transactions`, `routing tables`), sözlükteki tekil karşılıklarıyla (`işlem`, `yol atama çizelgesi`) otomatik eşlenir; sahte eksik terimler engellenir.
- **Kanıtlı Terim Doğrulaması:** Modelin döndürdüğü her aday, PDF metninde gerçekten geçtiği doğrulanmadan rapora girmez. Satır sonunda tirelenerek bölünmüş sözcükler (`compu-` + `tation`) ve tekil/çoğul farkları (`block cipher` ↔ `block ciphers`) bu doğrulamada göz ardı edilir; metinde hiç geçmeyen aday elenir.
- **TBD Kısaltmalar Ayrımı:** Resmî TBD Kısaltmalar tablosu ayrı taranır; `RAM`, `CPU`, `RBAC`, `DNS` gibi kavramlar TBD açılımlarıyla gösterilir.
- **Çoklu Sağlayıcı Desteği:** 
  - **Google Gemini** (`gemini-2.0-flash` — varsayılan)
  - **DeepSeek** (`deepseek-v4-flash` — varsayılan, `deepseek-v4-pro`, `deepseek-chat`, `deepseek-reasoner`)
  - **OpenAI** (`gpt-4o-mini`, `gpt-4o`, `o1`, `o3-mini`)
  - **Anthropic Claude** (`claude-sonnet-5`, `claude-opus-5`)
  - **Yerel Ollama** (İnternetsiz, %100 çevrimdışı yerel modeller)
- **2 Sekmeli Profesyonel Excel Raporu (.xlsx):**
  - **1. Sekme (Eksik Terimler):** Yalnızca incelenmesi gereken yeni kavramlar, makaledeki bağlam cümleleri ve uzmanın önerisini yazacağı özel çalışma sütunu.
  - **2. Sekme (Sözlükte Bulunanlar):** TBD sözlüğünde kayıtlı terimler ve Türkçe karşılıkları.

---

## 📂 Proje Yapısı

```text
├── src/terim_etmeni/      # Uygulama çekirdek paketi ve web sunucusu
├── data/                  # TBD Sözlüğü ve Kısaltmalar veri tabanı
├── docs/                  # Mimari kararlar (ADR) ve devir belgeleri
├── tests/                 # Otomatik doğrulama testleri (99 birim testi)
├── output/                # Üretilen Excel, CSV ve JSON raporları (Git dışı)
├── run.py                 # Ana çalıştırma dosyası
├── BASLAT_APPLE.command   # macOS tek tık başlatıcısı
└── BASLAT_WINDOWS.bat     # Windows tek tık başlatıcısı
```

---

## 🧪 Testleri Çalıştırma

Tüm sistem bileşenlerini doğrulamak için:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -v
```

---

## 🏛️ Kurumsal Not

Bu yazılım, **Türkiye Bilişim Derneği (TBD) Bilişimde Özenli Türkçe Çalışma Grubu** standartlarına uygun olarak Prof. Dr. Tuncer Ören'in öncülük ettiği Türkçe terim bilinci doğrultusunda geliştirilmiştir.
