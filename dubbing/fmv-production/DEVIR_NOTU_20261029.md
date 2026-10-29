# FMV Türkçe dublaj — 29 Ekim 2026 devir notu

Kullanıcının “bir şey yapma, sadece not düş; gerisini ben devam ettiririm” talimatıyla çalışma durduruldu. Bu nottan sonra kesim, miks, dönüştürme, kurulum veya oyun testi yapılmayacak.

## Güncel durum

- Branch: `work/fmv-turkish-dub-20261029`.
- 17 FMV için 192 seslendirme birimi eşleştirildi.
- 18 ham MP3'ün (17 ana kaynak + 07 GR-03 eki) SHA-256 ve boyutları `SOURCE_MANIFEST.tsv` ile doğrulandı.
- 192 adet işlenmemiş, 48 kHz mono PCM24 WAV master kesildi. Bunların 12'sine ayrıca v02 sınır düzeltmesi yapıldı; v01 dosyaları saklandı.
- 192 seçili master ayrı ayrı Whisper medium ile yeniden transkripte edildi. Kaynak 05 için medium'ın atladığı son Bowers repliği large-v3 ile bulundu; eksik üretim değil.
- 17 adet 48 kHz stereo PCM24 WAV ve FLAC kontrol miksi hazır.
- 17 adet MP4 görüntülü kontrol önizlemesi ve yerel HTML kontrol ekranı hazır.
- 34 benzersiz replikte hedefli inceleme uyarısı var: 23'ünde ASR/metin farkı, 15'inde zamanlama/tempo uyarısı bulunuyor; bu kümeler kesişiyor. Bu sayılar üretim hatası veya eksik kayıt sayısı değildir.
- **İnsan dinleme, baştan sona izleme ve oyun testi yapılmadı. Dosyalar onaylanmış/final sayılmıyor.**
- **Canlı oyuna veya izole oyun kopyasına hiçbir yeni FMV kurulmadı. Oyun açılmadı.**

## Dosyalar

Proje köküne göre:

- Ham kaynaklar: `dubbing/fmv-production/raw-elevenlabs/`
- Yetkili metinler: `dubbing/fmv-production/reference/`
- Kontrol ekranı: `work/fmv-dub/R001_20261029/index.html`
- Master'lar: `work/fmv-dub/R001_20261029/review_pending/<video>/master/`
- Miks WAV/FLAC: `work/fmv-dub/R001_20261029/review_pending/<video>/mix_v01/turkish_mix_48k.*`
- Önizlemeler: `work/fmv-dub/R001_20261029/review_pending/<video>/preview_v01.mp4`
- Kaynak Whisper çıktıları: `work/fmv-dub/R001_20261029/asr/`
- Kesim Whisper çıktıları: `work/fmv-dub/R001_20261029/cut_asr/`
- QA ve izlenebilirlik: `dubbing/fmv-production/qa/R001_20261029/`
- Araçlar: `tools/fmv_dubbing/`

QA klasöründeki önemli dosyalar:

- `inventory.json`: MP3/BIK/arka plan yolları, hash'ler ve medya bilgileri.
- `catalog.json`: 192 birim, Türkçe metinler, karakterler, üretim sırası, görüntü zamanları.
- `catalog_errors.json`: boş liste; katalog eşleştirmesi tamamlandı.
- `cuts_v01.json`: ilk kesimler.
- `cut_revisions_v02.json`: seçilmesi gereken 12 v02 kesimi. Diğer 180 kayıtta v01 kullanılacak.
- `cut_asr_v01.json`, `cut_asr_v02.json`: ayrı kesim transkriptleri; v02 dosyası güncel 192 seçimin tamamını kapsar.
- `qa_decisions_v01.json`, `QA_TABLE.md`: güncel 192 kayıtlık karar tablosu. Her kayıt `REVIEW_PENDING`.
- `mixes_v01.json`: replik başına tempo, EQ, kazanç, başlangıç/bitiş, taşma uyarıları ve miks hash'leri.
- `previews_v01.json`: 17 önizleme yolu.
- `installed_game_readonly_audit.json`: kurulu videoların ve dört mevcut oyun ikilisinin salt okunur hash kaydı.

HTML ekrandaki kararlar yalnız tarayıcı localStorage alanına kaydedilir; proje JSON'ları kendiliğinden güncellenmez. “Kararları dışa aktar” ile ayrı JSON indirilir.

## Özellikle dikkat edilecekler

### 06 CIA

- OD-03, “Sivil kayıplarınsa çok daha az olduğu düşünülüyor.” cümlesini tam olarak içeriyor.
- OD-05 / GE-01 sınırı ilk adayda 60.250 saniyeydi; “Gazeteler” başlangıcını kesiyordu.
- Dalga biçimi ve komşu kelimeler incelenerek sınır **59.870 saniyeye** taşındı. İki kaydın v02 yeniden transkriptinde önceki repliğe taşma giderildi ve GE-01 “Gazeteler…” ile başlıyor.

### 07 CIA Osprey

- Kullanıcının Kdenlive projesindeki 26 elle kesilmiş parça sınırı kullanıldı; 25 fps inclusive out değerine 0.04 saniye eklendi.
- GR-03 için `source_patch_GR-03.mp3` kullanıldı.
- SR-03 ve içindeki “Ah!” tek master olarak korundu; ASR'nin ünlemi yazmaması kesilmesi için gerekçe sayılmadı.
- Miks temposu replik bazında hesaplanıyor ve 1.20 ile sınırlandırılıyor. Lambert LA-04 hâlâ yaklaşık **1.44 saniye** taşıyor; doğal senkron kabulü verilmedi. Diğer kısa taşmalar `mixes_v01.json` içinde.

### Kaynak/metin farkları

- 04 Defense Ministry kaynağındaki bazı cümleler referans TXT'den farklı ifadeler içeriyor. Bu, hem kaynak hem kesim ASR'sinde görülüyor; metin veya ses yeniden üretilmedi/değiştirilmedi. Dinleyerek değerlendirilmeli.
- 10'da altyazı CSV'sinin üç birimindeki ifade, ElevenLabs TXT'sinden farklıydı. TXT'deki açık üretim ID'leri ile eşleştirildi ve TXT esas alındı; önceki CSV metni katalogda `subtitle_reference_text` olarak saklandı.
- 17'de “Tarih kararlılığınızı unutmayacak.” hem BO-02'nin sonunda hem ayrı BO-03'te bulunuyor. Referans üretim metni ve kaynak ses ikisini de içeriyor; kendiliğinden silinmedi.
- 01 Training'de yaklaşık 117.2 saniyedeki düşük güvenli İngilizce “Oh, my God” adayı mevcut üretim kapsamına dahil edilmedi; yeni replik uydurulmadı.
- 16'nın ayrı “ek üç HALO repliği” kontrol dosyası, ana üretim kataloğuna otomatik eklenmedi.

### Altı sınır düzeltmesi / 12 v02 master

| Video | Sol ID | Sağ ID | Yeni kaynak sınırı (s) |
|---|---|---|---:|
| 02 | TBI-001 | TBI-005 | 1.450 |
| 08 | OD-01 | OD-02 | 3.120 |
| 10 | SA-01 | SA-02 | 3.780 |
| 05 | OD-01 | OD-02 | 16.800 |
| 05 | OD-03 | OD-04 | 44.520 |
| 06 | OD-05 | GE-01 | 59.870 |

Dalga biçimi kanıtı: `work/fmv-dub/R001_20261029/boundary_review_2.png`.

## Miks yöntemi ve sınırları

- Master'lara tempo, filtre veya kazanç yazılmadı.
- Türetilmiş miks parçalarında kenar sessizliği azaltıldı; replikler kendi kaynak görüntü başlangıcına yerleştirildi. Bir önceki replik uzadığı için sonraki başlangıç ileri itilmedi.
- Replik başına atempo 1.00–1.20, yaklaşık -20 LUFS konuşma hedefi; çok kısa parçalarda aktif RMS yedeği kullanıldı.
- Lambert/radyo, ilgili Sarah/telefon ve pilot/interkom için ayrı filtreler uygulandı.
- Verilen konuşması bastırılmış arka planlar kullanıldı; konuşma çevresinde 250 ms geçişli -4 dB fon azaltma ve final limiter uygulandı.
- Training arka planı proje içindeki boş 01 klasöründen değil, görev notunun belirttiği `/home/ereng/Downloads/SC_FMV_01_Training_diyalog_bastirilmis_v2_Alarm_48k.wav` dosyasından alındı.
- İngilizce kalıntısı ve algısal denge kulakla onaylanmadı.

## Son teknik doğrulama: tamamlanmamış işler

### Önizleme doğrulamasındaki hata

`tools/fmv_dubbing/validate.py` çalıştırıldı, fakat **tam doğrulama başarılı sonuçlanmadı**. `validation.json` başarı raporu üretilmedi.

İlk denemede BIK ffprobe çıktısında `nb_frames` olmadığı görüldü. Kod `duration_ts` yedeği kullanacak şekilde düzeltildi. Sonraki denemede Training MP4 önizlemesi **4010 kare**, BIK kaynak **4011 kare** çıktı. İşlem bu assert üzerinde durdu.

Muhtemel neden önizleme komutundaki `-shortest` / varsayılan kare zamanlaması. Henüz düzeltme uygulanmadı. Devam eden ekip `-fps_mode passthrough` ve `-shortest` kaldırma seçeneğini yeni sürümde deneyip tüm 17 önizlemeyi yeniden doğrulayabilir. Bu MP4'ler yalnız kontrol kopyasıdır; kaynak BIK görüntüsü değişmedi. Tüm videoların tam decode kontrolünün geçtiği iddia edilmemeli.

### BIK dönüştürme denemesi

Kullanıcı, Wine kullanımını sonradan **yalnız BIK dönüştürme için** açıkça yetkilendirdi; **oyun açılması yasak**.

Araç:
`/home/ereng/Downloads/rad-video-tools/unpacked/radvideo64.exe`

Ayrı dönüştürücü Wine prefix'i:
`work/fmv-dub/R001_20261029/rad-prefix`

Tek tamamlanan deneme:
`work/fmv-dub/R001_20261029/bink-proof/07-test.bik`

- Boyut: RAD tamamlandı ekranında 169774236 bayt.
- Girdi: `staging/ps2-fmvs/Videos/2_1_0CIA_Osprey.bik` + yeni `07_CIA_Osprey/mix_v01/turkish_mix_48k.wav`.
- Komut alt işlemi: `BinkMix <input.bik> <mix.wav> <output.bik> /T0 /L4 /R48000 /C2`.
- Wine Xvfb sanal ekranında çalıştırıldı; oyun açılmadı.
- İlk denemede kullanılan `/AutoClose` bu alt komutta yardım ekranı açılmasına neden oldu; seçenek kaldırılınca dosya oluştu.
- Tamamlanma ekranı `bink-proof/completed.png` içinde. “Done” düğmesine tıklandı; sonraki süreç kapanışı ayrıca teyit edilmedi.
- ffprobe çıktı süresini **102.135469 saniye**, beş ses kanalını da Bink DCT / 48000 Hz / stereo gösteriyor.
- **Önemli:** RAD, değiştirilen track ID 0'ı sona taşıdı. Kaynak ses ID sırası `0,1,2,3,4`, test dosyası sırası `1,2,3,4,0`. ID sayısı korunuyor, fakat fiziksel sıra korunmuyor.
- Görüntü paketlerinin birebir aynı kaldığı, diğer dil paketlerinin değişmediği ve eski oyun Bink decoder'ıyla uyum henüz doğrulanmadı. Test BIK'i kuruluma hazır kabul etmeyin.
- Gerekirse track dizilerini ve her karedeki ses blok sırasını kaynak sıraya geri alan, video payload'ına dokunmayan bir repack yapılabilir; **böyle bir kod henüz yazılmadı**.
- Yapı incelemesinde birincil teknik kaynak: https://raw.githubusercontent.com/FFmpeg/FFmpeg/master/libavformat/bink.c . BIKi başlığında audio track dizileri ve kare başına uzunluk önekli audio blokları açıklanıyor. Kaynak incelendi; dönüştürme sonrası birebir paket hash kontrolü henüz yapılmadı.

Diğer 16 BIK henüz oluşturulmadı.

## Kurulu oyun / entegrasyon farkları

Canlı oyun yolu:
`/run/media/ereng/files/games/tom-clancys-splinter-cell/drive_c/GOG Games/Splinter Cell`

- `Videos/` altında iki PowerPlant videosu (09/10) bulunmuyor. Dosya eklemek tek başına görev akışında çağrılacaklarını kanıtlamaz.
- Kurulu 11 Chinese Embassy yaklaşık **80.914248 s**, verilen kaynak **63.763764 s**.
- Kurulu 12 Chinese Embassy Osprey yaklaşık **110.410300 s**, verilen kaynak **93.326660 s**.
- Yeni miksler verilen `staging/ps2-fmvs/Videos/` kaynaklarına senkronlandı; daha uzun kurulu videolara doğrudan aynı ses bindirilmemeli.
- Kurulu 04 de staging kaynağından farklı hash/boyutta; süresi aynı ve track ID 0 sonda. Eski değişikliğin üzerine yazılmadı.
- Canlı `system/SplinterCell.exe`, `dinput8.dll`, `dsound.dll`, `binkw32.dll` hash'leri audit JSON'unda saklandı; bu dosyalar değiştirilmedi.
- Henüz bu FMV çalışması için izole oyun kopyası hazırlanmadı, BIK yedek/rollback kurulumu uygulanmadı. Önceki new1258 test prefix'inin mevcut canlı oyunla aynı olduğu varsayılmamalı.

## Git ve devam edecek ekip için

Atılan commit'ler:

1. `49b6720` — `Inventory FMV sources and resolve production text order`
2. `d5a72a3` — `Cut 192 FMV voice masters and repair six adjacent boundaries`

3. `52f3e8d` — `Add FMV review mixes, previews, and QA reports`

Kullanıcının daha sonraki açık commit/push talimatıyla miks, önizleme, kontrol ekranı ve doğrulama araçları ile QA raporları commit edildi. Projede geniş ignore kuralları var. Büyük WAV/FLAC/MP4/BIK dosyaları ve üretilmiş yerel HTML ekranı Git'e eklenmedi; medya dosyaları yukarıdaki yerel yollarda duruyor. HTML ekranı `tools/fmv_dubbing/review.py` ile yeniden oluşturulabilir.

Başlangıçtan beri mevcut olan ve dokunulmayan başka işe ait iki değişiklik:

- `tools/new1258/review.py`
- `tools/new1258/transcribe.py`

Bu not durdurma talimatı üzerine yazıldı. Sonraki commit/push izni yalnız sürüm kontrolü işlemleri için kullanıldı; kesim, miks, dönüştürme ve oyun testi yeniden başlatılmadı. Commit öncesinde Python sözdizimi, JSON okunabilirliği, dosya boyutları ve staged diff boşluk kontrolü yapıldı. Yukarıdaki başarısız medya doğrulaması düzeltilmiş veya geçmiş sayılmıyor.
