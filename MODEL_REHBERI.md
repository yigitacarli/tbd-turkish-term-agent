# Yerel Model Seçim Rehberi

Bu uygulama bir yapay zekâ ajanından çok, yerel bir dil modelini iki sınırlı işte
kullanan deterministik bir belge işlem hattıdır:

1. PDF parçasından İngilizce teknik terim adaylarını çıkarma
2. Sözlükte bulunmayan adayları teknik terim niteliği bakımından doğrulama

Sözlük eşleşmesi, kanıt sayımı ve raporlama Python kodunda yapılır. Bu nedenle
Claude Code, OpenCode veya benzeri genel amaçlı bir ajan eklemek doğruluğu doğrudan
artırmaz; günlük kullanımda yalnızca uygun Ollama modelini seçmek gerekir.

## Donanıma göre başlangıç profilleri

Model dosyası boyutu tek başına yeterli bellek ölçüsü değildir. Ollama ayrıca
çalışma belleği ve bağlam önbelleği kullanır; tabloda baş boşluğu bırakılmıştır.

| Profil | Yaklaşık donanım | İlk aday | Alternatif | Amaç |
|---|---|---|---|---|
| Hafif | 8 GB Apple Silicon | `qwen3.5:2b` | `granite4.1:3b` | Günlük hızlı tarama |
| Mac kalite deneyi | 8 GB Apple Silicon | `qwen3.5:4b` | `gemma3:4b` | Daha yavaş, olası kalite artışı |
| Dengeli masaüstü | 12–16 GB VRAM | `qwen3.5:9b` | `granite4.1:8b` | Hız/kalite dengesi |
| Kalite masaüstü | 24 GB VRAM | `qwen3.5:27b` | `gpt-oss:20b` | Daha güçlü çıkarım ve ikinci aile kontrolü |
| Üst seviye | 32 GB+ VRAM | `qwen3.6:35b` | `qwen3.6:27b` | Deneysel en yüksek yerel kapasite |

8 GB M2 MacBook Air için önerilen ilk kurulum:

```bash
ollama pull qwen3.5:2b
ollama pull granite4.1:3b
```

Güçlü masaüstünde ekran kartı belleği doğrulandıktan sonra önerilen başlangıç:

```bash
ollama pull qwen3.5:9b
```

24 GB VRAM varsa kalite adayları ayrıca kurulabilir:

```bash
ollama pull qwen3.5:27b
ollama pull gpt-oss:20b
```

Kurulan modeller uygulamanın web arayüzündeki model listesinde otomatik görünür.
Arayüz okunabilir model adını ve parantez içinde gerçek Ollama etiketini birlikte
gösterir. Terminalden model kaldırmak için gerçek etiket kullanılır:

```bash
ollama list
ollama rm MODEL_ETIKETI
```

Örneğin `ollama rm qwen:latest`. Silme geri alınamaz; tekrar kullanmak için modelin
yeniden indirilmesi gerekir.

## Göreve özel geçici sıralama

Bu sıralama genel model tanıtımlarına, yapılandırılmış çıktı desteğine, bellek
boyutuna ve projenin İngilizce terim çıkarma gereksinimine göre hazırlanmış bir
**kısa listedir**; kabul kümesi ölçümü yapılmadan nihai kalite sıralaması değildir.

1. `qwen3.5:9b` — güçlü masaüstü için ilk hız/kalite adayı
2. `qwen3.5:2b` — 8 GB M2 için günlük kullanım adayı
3. `granite4.1:3b` — metin çıkarma ve yapılandırılmış JSON odaklı hafif karşılaştırma modeli
4. `qwen3.5:27b` — 24 GB VRAM sınıfında kalite adayı
5. `gpt-oss:20b` — farklı model ailesinden yapılandırılmış çıktı destekli doğrulayıcı
6. `mistral-small3.2:24b` — talimat takibi güçlü ikinci karşılaştırma modeli
7. `qwen3.6:27b` / `qwen3.6:35b` — daha yeni fakat öncelikle ajan/kod yetenekleriyle
   tanıtıldığı için bu çıkarım görevinde ölçülmeden varsayılan yapılmamalı

Önceki `qwen2.5:1.5b` modeli çalışmaya devam eder; yeni varsayılan ölçülürken
karşılaştırma tabanı olarak tutulabilir.

## Nihai sıralama için kabul deneyi

Üç farklı belge seçilmelidir:

- `nist-5g-security.pdf`: güvenlik, ağ ve kısaltmalar
- `efficient-transformers-survey.pdf`: yoğun akademik yapay zekâ terminolojisi
- `diffusion-models-vision-survey.pdf`: model/ürün adı ile gerçek terim ayrımı

Bir uzman bu belgelerde sözlükte eksik olan doğru terimleri bir kez etiketlemelidir.
Her model aynı uygulama sürümü, istem, parça boyutu ve tek geçiş ayarıyla en az üç
kez çalıştırılmalıdır. Şu ölçüler kaydedilmelidir:

- recall: etiketli eksik terimlerin kaçının bulunduğu
- precision: önerilen eksik terimlerin kaçının gerçekten terim olduğu
- F1: precision ve recall dengesi
- çalışma süresi
- üç tekrar arasındaki değişkenlik
- geçersiz/yarım JSON ve atlanan parça sayısı

Patron için önerilen karar kuralı: önce en yüksek recall, eşitliğe yakın sonuçlarda
daha yüksek precision, ardından daha kısa süre. Yalnızca bulunan terim sayısına
göre model seçilmemelidir.

## Kaynaklar

- [Ollama Qwen 3.5 model ve boyutları](https://ollama.com/library/qwen3.5/tags)
- [Ollama Qwen 3.6 model ve boyutları](https://ollama.com/library/qwen3.6)
- [Ollama Granite 4.1 model ve boyutları](https://ollama.com/library/granite4.1/tags)
- [Ollama gpt-oss model ve boyutları](https://ollama.com/library/gpt-oss)
- [Ollama Mistral Small 3.2](https://ollama.com/library/mistral-small3.2)
- [Ollama yapılandırılmış çıktı belgeleri](https://docs.ollama.com/capabilities/structured-outputs)
