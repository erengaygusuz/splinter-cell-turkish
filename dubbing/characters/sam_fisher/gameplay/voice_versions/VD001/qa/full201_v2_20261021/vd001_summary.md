# Sam Fisher VD001 — 201 WAV kesim adayı

Teslim kontrolü: 22 Ekim 2026. `20261021` adları üretim grubunu belirtir.

190 R001 ve 11 E001 repliğinin tamamı ayrı WAV adaylarına ayrıldı. **Eksik kaynak/ID yok; işitsel nihai kabul bekliyor.** Önceki 190 kayıtlık teslim değiştirilmedi. Güncel seçki 200 adet v01 ve `u000125_v02.wav` içerir; bu repliğin v01 sürümü de saklanır.

- [201 WAV ZIP](../../review_pending/sam_fisher_VD001_201_v2_20261021.zip)
- [201 ID QA karar tablosu](vd001_qa_decisions_201.tsv)
- [Dinleme ve kaynak karşılaştırma sayfası](listen.html)
- [Seçili kesim manifesti](selected_cuts_201.tsv), [doğrulama sonucu](validation.json)

## Kaynak ve kesim

Yeni kaynak, Downloads dosyası korunarak `batches/E001_20261021/sam_fisher_vd001_test11_E001_20261021_143751.mp3` adıyla kopyalandı. SHA-256: `ff8102a00dea5caa330da2c0600f2297faa2cbac77fbfa6b489c32941706f71d`.

| Kaynak | Replik | İlk–son ID | Süre |
|---|---:|---|---:|
| R001 part01 | 167 | u000005–u000914 | 308,72 sn |
| R001 part02 | 23 | u000926–u001092 | 50,40 sn |
| E001 part01 | 11 | u000034–u000125 (üretim sırası) | 27,36 sn |

Üç kaynak MP3 hash ile doğrulandı. WAV'lar mono, 44.100 Hz, 16-bit PCM. Seçili 201 dosyanın ve saklanan önceki CIA kesiminin örnekleri kaynak MP3'ten çözümlenen ilgili PCM aralıklarıyla birebir aynı. Fade, normalizasyon, sentez veya süre değiştirme uygulanmadı. 198 komşu sınırı sessiz bölgede; replikler arasında örnek boşluğu/örtüşmesi yok. Altı kaynak kenarı ayrıca incelendi. Tam kaynak kapsamından tek çıkarılan bölüm aşağıdaki belgeli E001 kuyruğudur.

`u000125`: kaynak sonundaki ayrı kısa ses çıkıntısı, son cümleden sonraki sessiz bölgeden ayrıldı. v02 bitişi 27,285487528 sn; dışarıda bırakılan kuyruk 3.286 örnek / 74,512 ms. İki model v02 metnini %100 eşleştirdi. Son hece ve CIA telaffuzu dinleme önceliğinde. [v01/v02 karşılaştırması](revision_comparison.tsv), [kuyruk kaydı](excluded_source_tails.json), [dalga biçimi](boundary_plots/e001_source_tail_detail.png).

R001 ilk hizalamada atlanan `u000497` (Ah) ve `u000047` başlangıcı, önceki v01 tesliminde kaynak dalga biçimiyle korunmuştu; bu dosyalar aynen kullanıldı. [Kesim düzeltmeleri](cut_corrections.tsv).

## Whisper ve kalan kontrol

Türkçe faster-whisper medium ile üç tam kaynak için transkript/kelime zamanları, 201 v01 kesim için bağımsız transkript ve CIA v02 için tekrar kontrol mevcut. Seçili 201 dosyanın 171'i normalleştirilmiş metinle %100 eşleşiyor. 31 ID large-v3 ile yeniden kontrol edildi; CIA v02 ayrıca large-v3 kontrolünden geçti. Dört kaynak bağlamı kontrolü R001 tesliminden korundu. ASR'ye beklenen metin başlangıç istemi verilmedi.

[Kaynak ASR](source_asr/), [E001 kesim ASR](clip_asr_E001_20261021.json), [large-v3 tekrarları](isolated_retry_large_v3.json), [v02 medium](revision_asr.json), [v02 large-v3](revision_large_v3.json). Eski tekrar dosyasındaki u000125 v01'e aittir; güncel tablo v02 kanıtını kullanır.

**Sesler bu ortamda dinlenmedi.** Dalga biçimi, kelime zamanları, komşu sınırlar, PCM bütünlüğü ve ASR birlikte kontrol edildi; bunlar işitsel onay yerine geçirilmedi. 198 kayıt `NEEDS_LISTEN`, üç kayıt `NEEDS_BOUNDARY_LISTEN`. Hiçbir kayda approved kararı verilmedi.

- Başlangıç payı kısa iki kaynak: `u000034` 24,9 ms, `u000926` 29,9 ms. Her ikisi de sıfırıncı örnekten korunur; ek bir başlangıç kesilmedi.
- Sınır dinleme önceliği: bu iki kayıt ve düzeltilen `u000125`.
- [Telaffuz belirsizlikleri](pronunciation_review.tsv): u000102, u000109, u000111, u000432, u000987, u001084, u001092, u000426, u000742, u000125. Bunlar doğrulanmış telaffuz hataları değildir.
- [Sözcük biçimi belirsizlikleri](content_review.tsv): u000047, u000187, u000732, u000978. ASR farkı tek başına kayıp kelime veya yanlış seslendirme sayılmadı.
- [Yeniden üretim gerekenler](regenerate_required.tsv): doğrulanmış kayıt yok. Aktif kesim kenarı ve dijital kırpılma saptanmadı.

## Koruma ve teslim doğrulaması

14 otomatik test geçti. ZIP içindeki 201 ad/hash seçili manifestle eşleşiyor. Önceki Fisher sesleri, VD001 R001 WAV'ları/teslimi, eski Lambert sesleri ve Downloads kaynağı dahil **958 mevcut başlangıç dosyasının hash'i değişmedi**.

Devam oturumunun başındaki taramada Lambert `game_ready` klasöründe başlangıç envanterine göre 207 ek WAV ve eksik bir boş `.gitkeep` görüldü. Bu devam oturumunda Lambert klasörüne yazılmadı; değişikliğin kaynağı belirlenmedi. Dosyalar korunarak fark ve hash'ler [workspace_changes.json](workspace_changes.json) içinde kaydedildi. Bu nedenle karakter klasörlerinin dosya kümelerinin tamamen aynı kaldığı iddia edilmez. Başlangıç envanteri değiştirilmedi.

VD001 adayları yalnız `review_pending/` altında. Oyun formatına dönüşüm ve approved/game_ready taşıması yapılmadı. Önceki R001-only teslimi tarihsel kayıt olarak [korunuyor](../r001_v1_20261021/vd001_summary.md); oradaki E001 eksik durumu bu birleşik teslimle giderildi.
