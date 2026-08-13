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

| Profil | Yaklaşık donanım | Önerilen model | Amaç |
|---|---|---|---|
| Hafif | 8 GB bellek / Apple Silicon | `qwen3.5:2b` | Günlük hızlı tarama |
| Orta seviye | 12–16 GB bellek veya VRAM | `qwen3.5:4b` | Hız ve terim bulma dengesi |
| Güçlü | 16 GB+ bellek veya VRAM | `qwen3.5:9b` | Daha güçlü terim çıkarımı |

8 GB M2 MacBook Air için önerilen ilk kurulum:

```bash
ollama pull qwen3.5:2b
```

Orta seviye bilgisayarda:

```bash
ollama pull qwen3.5:4b
```

Güçlü bilgisayarda:

```bash
ollama pull qwen3.5:9b
```

Kurulan modeller uygulamanın web arayüzündeki model listesinde otomatik görünür.
Arayüz doğrudan Ollama model etiketini gösterir. Terminalden model kaldırmak için
aynı etiketi kullanın:

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

1. `qwen3.5:9b` — güçlü bilgisayarlar için en yüksek önerilen Qwen 3.5 profili
2. `qwen3.5:4b` — orta seviye bilgisayarlar için dengeli profil
3. `qwen3.5:2b` — hafif bilgisayarlar için varsayılan profil

Gemma ve Granite, bu projedeki terim çıkarma denemelerinde Qwen 3.5 modellerinden
daha zayıf sonuç verdiği için önerilen modeller arasında yer almaz. `gpt-oss` ve
diğer model aileleri bu görevde henüz ölçülmediğinden varsayılan veya öneri olarak
kullanılmamalıdır.

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
- [Ollama yapılandırılmış çıktı belgeleri](https://docs.ollama.com/capabilities/structured-outputs)
