# Yerel Model Seçim Rehberi

Bu uygulama bir yapay zekâ ajanından çok, dil modelini **tek bir sınırlı işte**
kullanan deterministik bir belge işlem hattıdır: PDF parçasından İngilizce teknik
terim adaylarını çıkarmak. Modelin ikinci bir doğrulama geçişi yoktur (ADR-028).

Sözlük eşleşmesi, kanıt sayımı ve raporlama Python kodunda yapılır. Bu nedenle
Claude Code, OpenCode veya benzeri genel amaçlı bir ajan eklemek doğruluğu doğrudan
artırmaz; günlük kullanımda yalnızca uygun Ollama modelini seçmek gerekir.

## Donanıma göre model boyutu

Model dosyası boyutu tek başına yeterli bellek ölçüsü değildir. Ollama ayrıca
çalışma belleği ve bağlam önbelleği kullanır; tabloda baş boşluğu bırakılmıştır.

| Profil | Yaklaşık donanım | Model boyutu | Amaç |
|---|---|---|---|
| Hafif | 8 GB bellek / Apple Silicon | Yaklaşık 2–4B | Günlük hızlı tarama |
| Orta seviye | 12–16 GB bellek veya VRAM | Yaklaşık 4–9B | Hız ve terim bulma dengesi |
| Güçlü | 16 GB+ bellek veya VRAM | 9B ve üzeri | Daha güçlü terim çıkarımı |

Model aileleri ve sürümleri sürekli değiştiği için uygulama belirli bir etiketi
varsayılan yapmaz. Güncel bir modeli kurma biçimi:

```bash
ollama pull MODEL_ETIKETI
```

Kurulan modeller uygulamanın web arayüzündeki model listesinde otomatik görünür.
Arayüz herhangi bir modeli kendiliğinden seçmez ve doğrudan Ollama model etiketini
gösterir. Terminalden model kaldırmak için
aynı etiketi kullanın:

```bash
ollama list
ollama rm MODEL_ETIKETI
```

Örneğin `ollama rm qwen:latest`. Silme geri alınamaz; tekrar kullanmak için modelin
yeniden indirilmesi gerekir.

## Ölçülmüş durum (2026-08-19)

**Uyarı:** Bu bölümün önceki sürümü `qwen3.5:9b` profilini "en yüksek önerilen"
olarak gösteriyordu. O öneri ölçüme değil model tanıtımlarına dayanıyordu ve
19.08.2026'da yapılan 14 makalelik koşuyla **çürütüldü**. Aşağıdaki sayılar aynı
gün, aynı kod ve aynı 14 belge üzerinde ölçülmüştür.

| Model | Belge | Sayfa başına süre | Bulunan terim | Not |
|---|---|---|---|---|
| `deepseek-v4-flash` (bulut) | 14/14 | ~1,6 sn | 2.544 aday | Referans koşu |
| `qwen3.8:latest` (yerel) | 9/14 | ~25 sn | 308 aday | Koşu yarıda kaldı, bir parça HTTP 500 |
| `qwen3.5:9b-q4_K_M` (yerel) | 14/14 | ~1,2 sn | 192 aday | **5 belgede hiç aday döndürmedi** |

- Yerel modeller bulut sağlayıcının bulduğu terimlerin belge başına yalnızca
  **%3–51'ini** yakaladı.
- `qwen3.5:9b-q4_K_M` 14 belgenin 5'inde sıfır aday döndürdü. Bu sessiz boş sonuç
  davranışı ADR-039 ile artık raporda ve arayüzde uyarı olarak görünür.
- `qwen3.8:latest` bulut sağlayıcıdan yaklaşık **19 kat yavaştı** ve uzun
  belgelerde Ollama bağlantısı koptu.
- Ayrıntılı koşu kayıtları `output/_arsiv/` altındadır.

**Tablodaki aday sayıları doğrudan karşılaştırılamaz:** yerel model koşuları parça
başına 8 aday tavanıyla (ADR-031), DeepSeek referans koşusu 16 tavanıyla (ADR-040)
yapılmıştır. Tavandan bağımsız olan iki bulgu şunlardır: yerel modellerin sayfa
başına süresi ve `qwen3.5:9b-q4_K_M`'nin 5 belgede hiç aday döndürmemesi. Üstteki
"%3–51 yakalama" oranı ise her iki tarafın da 8 tavanıyla çalıştığı koşulardan
hesaplanmıştır, o karşılaştırma adildir.

**Pratik öneri:** Belgeler gizli değilse bulut API kullanın — hız ve terim bulma
farkı büyüktür. Yerel model yalnızca belgenin cihazdan çıkmaması zorunluysa
tercih edilmelidir; bu durumda 9B altı profillerden kaçının ve sıfır aday
uyarısını dikkate alın.

Gemma, Granite ve `gpt-oss` aileleri bu kümede hiç ölçülmedi; onlar hakkında
öneri yapılmamıştır.

## Nihai sıralama için kabul deneyi

Yukarıdaki tablo **hacim ve hız** farkını gösterir; hangi modelin daha *doğru*
terim bulduğunu göstermez. Bunun için uzman etiketli bir altın küme gerekir.

Üç belge seçilmelidir. Bugünkü 14 makalelik kümeden seçilmesi önerilir
(`8_ebpf_xdp_packet_processing.pdf` hariç — o dosya yanlış içerik taşıyor):

- Güvenlik/ağ ve kısaltma yoğun bir belge (ör. `11_zero_knowledge_proof_frameworks`)
- Yoğun akademik yapay zekâ terminolojisi (ör. `5_flash_attention_io_aware`)
- Model/ürün adı ile gerçek terim ayrımının zor olduğu bir belge
  (ör. `10_homomorphic_encryption_survey`)

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
