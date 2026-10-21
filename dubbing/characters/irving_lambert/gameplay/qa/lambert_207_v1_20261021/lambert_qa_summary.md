# Irving Lambert — 207 repliğin kesim teslimi

207 benzersiz oyun ses kimliğinin tamamı dört MP3 içinde eşleştirildi ve ayrı WAV dosyalarına bölündü. Seçili teslim seti **203 v01 + 4 v02 = 207 WAV** içerir. Önceki sürümler korunduğu için `review_pending/` altında toplam 211 WAV bulunur. Hangi dosyanın kullanılacağı `selected_cuts.tsv` içinde açıkça belirtilmiştir.

Kullanıcının son açıklaması doğrultusunda **seslendirmeler doğru kabul edilmiştir**. İşin kapsamı doğru bölme, doğru ID ile adlandırma ve kesim sınırlarının kontrolüdür. Whisper yazım/telaffuz farklarından yeniden seslendirme talebi çıkarılmamıştır.

## Dosyalara erişim

- [Yalnızca seçili 207 WAV'ı içeren ZIP](../../review_pending/lambert_207_selected_v1_20261021.zip) — eski alternatif sürümleri içermez; [arşiv SHA-256 kaydı](delivery_archive.json).
- [207 kayıtlık karar ve eşleme tablosu](lambert_qa_decisions.tsv)
- [Seçili 207 WAV ve SHA-256 listesi](selected_cuts.tsv)
- [Dinleme sayfası](listen.html): seçili sürümleri oynatır; kaynak MP3 ve komşu bağlamına bağlantı verir.
- [E001 — 10 WAV](../../review_pending/E001_20261021/)
- [R001 — 197 ID, eski ve yeni WAV sürümleri](../../review_pending/R001_20261021/)
- [Dört kaynak MP3'ün transkriptleri ve kelime zamanları](source_asr/)
- [203 komşu sınırının kontrol tablosu](neighbor_boundaries.tsv) ve [dalga biçimi dizini](boundary_plots/index.tsv)
- [Dört düzeltmenin eski/yeni karşılaştırması](revision_comparison.tsv)
- [Öncelikli üç kayıt](boundary_listen_priority.tsv)
- [211 WAV sürümünün bütünlük denetimi](all_wav_integrity.tsv) ve [sayısal doğrulama sonucu](validation.json)

TSV içindeki dosya yolları proje köküne göredir. HTML bağlantıları taşınabilir, kendi klasörüne göre bağıl yollardır. HTML sayfasını yerel tarayıcıda açmak yeterlidir; sesler dışarı yüklenmez.

## Kaynakların kesin replik dağılımı

| Kaynak | Üretim sırası | İlk / son ID | Replik | Çözülmüş ses süresi |
|---|---|---|---:|---:|
| E001 part01 | Pilot 1–10 | u000004 / u001064 | 10 | 40,64 sn |
| R001 part01 | Kalan liste 1–79 | u000001 / u000305 | 79 | 417,28 sn |
| R001 part02 | Kalan liste 80–165 | u000311 / u000910 | 86 | 416,64 sn |
| R001 part03 | Kalan liste 166–197 | u000912 / u001080 | 32 | 156,24 sn |
| Toplam | | | **207** | **1030,80 sn** |

Dağılım, kaynak transkriptindeki sıralı kelime eşleştirmesinden çıkarıldı; dosya süresinden oranlanmadı. E001'in ardışık olmayan on pilot ID'si kendi üretim sırasıyla ele alındı. Pilot/kalan liste kesişimi, eksik ID ve tekrar eden ID yok. Bir MP3'ten diğerine bölünmüş replik saptanmadı. Ayrıntılı sınır metinleri `source_boundaries.tsv` içinde.

Dört özgün MP3'ün SHA-256 değerleri paket manifestleriyle eşleşiyor. Kaynaklar mono, 44100 Hz. Kesimler 44100 Hz mono PCM16 WAV; örnek indeksleri `[start_sample, end_sample_exclusive)` biçiminde. Paketlerdeki yaklaşık süreler yerine gerçek çözülmüş örnek sayısı esas alındı.

## Kesim kontrolleri

1. Dört uzun kaynak yerel faster-whisper medium ile, Türkçe ve kelime zamanları açık olarak çözümlendi. E001 ve R001 part01 CPU/int8; diğer iki parça CUDA/int8_float16. Beklenen replikler ASR istemine verilmedi.
2. Tüm 207 v01 WAV bağımsız olarak tekrar transkribe edildi. Dört v02 de yeniden transkribe edildi. 26 belirsiz ASR sonucu large-v3 ile kaynak bağlamında, altısı ayrıca tek WAV üzerinde kontrol edildi. Bunlar kesim eşleştirmesinin yardımcı kanıtlarıdır.
3. Her kesimin başı/sonu, kaynakta ±15 ms RMS ve yaklaşık 5 ms pencereli sessizlik ölçümüyle tarandı. 203 komşu sınırının tamamı ayrıca kaynak dalga biçimleri üzerinden görsel olarak incelendi; dört MP3'ün sekiz dış kenarı da görüntülendi.
4. 202 komşu sınırı belirgin sessiz bölgede. `u000285–u000287` sınırında düşük seviyeli kuyruk/nefes belirsizliği var; aşağıda açıklanıyor. Seçili kesimlerde −45 dBFS üstü aktif kenar bayrağı ve tam ölçeğe ulaşmış örnek yok.
5. Her WAV'ın PCM örnekleri kaynak MP3'ün FFmpeg ile çözülen ilgili aralığıyla birebir karşılaştırıldı. Tüm 211 sürüm eşleşiyor. Seçili 207 WAV dört kaynağı boşluk veya üst üste binme olmadan tam olarak bölüyor; kaynak başlangıcı/sonu atılmadı. Bu bütünlük kontrolü tek başına anlamsal kesim onayı sayılmaz.

Sessizlikleri topluca kırpma, ses yüksekliği normalizasyonu, filtreleme, fade, yapay padding veya zaman esnetme uygulanmadı. Doğal iç duraklamalar korunuyor. Replikte birden fazla cümle bulunması, beklenen metnin parçasıysa bölünme hatası kabul edilmedi.

Whisper kelime zamanları bazı sessizliklerin içine taşıyor. Karar tablosundaki negatif ASR kenar payı bu zaman tahmini taşmasını gösterir; tek başına kesilmiş hece anlamına gelmez. Kesim kararında gerçek dalga biçimi, kaynak sırası ve bağımsız WAV transkripti birlikte kullanıldı. `Altyazı M.K.` gibi büyük model halüsinasyonları da ham kanıtta saklandı, seslendirme hatası sayılmadı.

## Sürümlendirilen dört kesim

- `u000009_v02.wav` / `u000010_v02.wav`: ortak sınır R001 part01 içinde **28,689796 → 28,901814 sn**. Daha geniş, görsel olarak doğrulanmış sessiz aralığa taşındı.
- `u000698_v02.wav` / `u000700_v02.wav`: ortak sınır R001 part02 içinde **256,001610 → 256,080499 sn**. Aynı şekilde sessizlik payı iyileştirildi.

Bu değişiklikler sınır payını iyileştirir; v01 sürümlerde kelime eksikliği kesinleştiği iddiası değildir. Dört v02'nin bağımsız medium transkriptleri beklenen metinle %100 eşleşti; bu oran işitsel onay yerine kullanılmadı. v01 dosyalarının hiçbiri değiştirilmedi.

## Kalan sınır kontrolü ve durumlar

| Durum | Sayı | Açıklama |
|---|---:|---|
| Teknik kesim kontrolünü geçen aday | 204 | ID, kaynak sırası, PCM bütünlüğü ve kenar ölçümleri uygun |
| Öncelikli sınır dinlemesi | 3 | u000285, u000287, u000912 |
| İşitsel onayı tamamlanan | 0 | Bu oturumda ses dinlenmedi |
| İnceleme bekleyen toplam | 207 | 204 standart + 3 öncelikli |
| Yeniden seslendirme talebi | 0 | Kullanıcı seslendirmelerin doğru olduğunu belirtti |

**u000285 / u000287:** ortak sınır R001 part01 içinde 379,507483 sn. −55 dBFS sessizlik ölçütünde iki tarafta yaklaşık 24,9 ms pay var. Ana konuşmalar ayrışıyor, ancak çok düşük seviyeli kuyruk/nefes sınır çevresinde sürüyor. Grafikten nefesin hangi repliğe ait olduğu kesinleştirilemediği için gelişigüzel yeni kesim yapılmadı. [Ayrıntılı görüntü](boundary_plots/u000285_u000287_detail.png). Öncelik: bu geçişte son hece ve sonraki nefesi kaynakla karşılaştırarak dinlemek.

**u000912:** R001 part03'ün ilk repliği. Kaynak sıfırıncı örnekten alındı; başından hiçbir veri atılmadı. İlk “Tüh” sözcüğü kaynak ve bağlam ASR'sinde bulunuyor. Kaynağın kendi başlangıç sessizliği yaklaşık 24,9 ms olduğundan kısa pay uyarısı var. [Kaynakların başı/sonu](boundary_plots/source_edges.png). Öncelik: ilk hecenin kaynaktaki başlangıcını dinlemek; bu kesimin önüne eklenebilecek kayıp kaynak örneği yok.

İşitsel son kontrol yapılmadığı için hiçbir dosya `approved/` veya `game_ready/` klasörüne taşınmadı. Bu teslim teknik kesim arşividir; kesin duyumsal onay iddiası içermez.

## Koruma, Git ve yeniden üretim

- Başlangıçta kaydedilen 421 özgün dosyanın SHA-256 değerleri korunuyor. Fisher klasörünün dosya kümesi ve içerikleri değişmedi. FMV kapsam dışında kaldı.
- Özgün Lambert README gibi önceki “üretim tamamlanmadı” ifadeleri tarihsel belge olarak bırakıldı; güncel durum bu raporda.
- Git'te `.gitignore` yok; yerel `.git/info/exclude` genel dışlama kuralı içeriyor. Büyük MP3/WAV dosyaları zorla Git'e eklenmedi. Araçlar, tablolar, transkriptler, küçük görsel kanıtlar ve hash manifestleri ayrı İngilizce commitlerle kaydedildi. WAV dosyaları yerel çalışma arşivindedir; tek başına Git klonu sesleri taşımaz.
- Araçlar: `../../../tools/lambert_audio_qa.py`, `../../../tools/lambert_boundary_plots.py`, `../../../tools/lambert_delivery.py`. Proje kökünden çalıştırılır. `lambert_audio_qa.py` özgün kaynakları korur, mevcut WAV'ın üstüne farklı veri yazmayı reddeder. Python ortamı: `~/.cache/splinter-cell-whisper-venv/`.
- `lambert_delivery.py` kaynak/çıktı hashlerini, 207 ID'yi, tüm sürümlerin kaynakla örnek eşitliğini, 203 ortak sınırın sürekliliğini ve ASR önbelleğinin seçili WAV'a ait olduğunu yeniden doğrular.
- 10 araç testi geçti: üretim sırası, kaynak geçişi, sessizlik seçimi, mevcut WAV'ın üzerine yazmayı reddetme, kaynak dışına çıkma ve teslimde eksik/çakışan örnek ya da yinelenen ID denetimleri. ZIP içindeki 207 WAV da seçili manifestin hashleriyle doğrulandı.

Oyun SND biçimine, slot süresine veya kodlama boyutuna uyarlama yapılmadı.
