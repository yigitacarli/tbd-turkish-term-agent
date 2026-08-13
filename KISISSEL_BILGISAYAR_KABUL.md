# Kişisel Bilgisayar Kabul Kontrolü

Bu liste, V2'nin hedef bilgisayarda ilk kurulumdan ilk rapora kadar güvenle
çalıştığını doğrulamak içindir. Uygulama yalnız yerel bilgisayarda çalışır;
PDF ve analiz sonucu dışarı gönderilmez.

## Hazırlık

- [ ] Python 3.9 veya üstü kurulu: `python3 --version` (Windows'ta `py -3 --version`).
- [ ] [Ollama](https://ollama.com/download) kurulu ve çalışıyor.
- [ ] Terminalde `ollama list` komutu yanıt veriyor.
- [ ] Seçilen model indirildi: `ollama pull qwen3.5:2b`.
- [ ] Bu proje klasörü bilgisayara kopyalandı; metin seçilebilen bir İngilizce PDF hazır.

`qwen3.5:2b`, mevcut geliştirme ölçümlerinde düşük kaynak tüketimi için kullanılan
başlangıç noktasıdır. Uygulama bu modele sabit değildir; kurulu modeller listeden
seçilebilir.

## İlk kurulum

macOS veya Linux terminalinde, proje klasöründe:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Windows PowerShell'de:

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .
```

## İlk çalışma

- [ ] macOS'ta `BASLAT_APPLE.command`, Windows'ta `BASLAT_WINDOWS.bat` dosyasını
  çift tıklayın. Gerekirse terminalden `python3 run_v2.py` çalıştırın.
- [ ] Tarayıcıda `http://127.0.0.1:8876` açılıyor.
- [ ] Ana sayfada “Ollama hazır” ve en az bir model görünüyor.
- [ ] Bir metin katmanlı İngilizce PDF seçin, modeli seçin ve **Eksik terimleri bul**
  düğmesine basın.
- [ ] Sonuç `tamamlandı` durumunda; “Öncelikli açık”, “İkincil aday”, “Bulunan” ve
  varsa “Kısaltma kaynağında” grupları görünür.
- [ ] CSV, Excel ve JSON raporları indirilebiliyor.

Kısmi veya başarısız sonuç, sıfır sözlük açığı demek değildir. Bu durumda model
ve Ollama bağlantısı kontrol edilip aynı PDF yeniden çalıştırılmalıdır.

## Kayıt altına alınacak ölçüm

Beş belgeli hedef makine deneyi için her koşuda aşağıdakileri kaydedin:

| Belge | Model | Süre | Tamamlanma durumu | Öncelikli açık | Not |
| --- | --- | --- | --- | --- | --- |
| PDF adı | Ollama etiketi | Ekrandaki süre | tamamlandı/kısmi/başarısız | Ekrandaki sayı | Isınma, bellek veya hata |

Sonuçlar önceki kabul kümesiyle ancak aynı model ve benzer belge koşullarında
karşılaştırılmalıdır. Ayrı model koşularındaki fark, tek başına V2'nin kalite
üstünlüğü kanıtı değildir.

## Başarılı kabul ölçütü

- Arayüz yalnız `127.0.0.1:8876` üzerinde açılır.
- Seçilen modelle bir PDF tamamlanır ve indirilebilir rapor oluşur.
- Başarısız/kısmi durum açıkça görünür; boş sonuç olarak sunulmaz.
- İlk beş belge koşusunun süre ve kaynak gözlemleri kaydedilir.
