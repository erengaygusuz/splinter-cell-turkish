# Sam Fisher — kesim onarımı ve QA teslimi

**Tarih:** 21 Ekim 2026

**Durum:** Teknik kesim onarımı ve 201 kayıtlık kanıt dökümü hazır. **Nihai işitsel kabul tamamlanmadı.** Bu oturumda ses dinleme aracı yoktu; hiçbir kayıt dinlenmiş veya APPROVED olarak işaretlenmedi.

## Sonuç

| Kontrol / çıktı | Sonuç |
|---|---:|
| Katalog ve referans TXT satırlarının birebir eşleşmesi | 201/201 |
| Kapsam | B001: 10, B002: 167, B003: 24 |
| Seçim | 174 mevcut v01 + 27 yeni v03 |
| Yeniden kesilen zincir bölgesi `u000467–u000596` | 24 kayıt |
| Diğer yeni kesimler | u000043, u000045, u000047 |
| Manuel zamanlama listesindeki 7 kayıt | 6 yeni kesim + 1 korunan v01 |
| APPROVED / NEEDS_LISTEN | 0 / 201 |
| Teknik taramada kalan NEEDS_CUT | 0; işitsel kesinlik anlamına gelmez |
| Kesinleşmiş NEEDS_RERECORD | 0; kaynak telaffuz farkları hâlâ belirsiz |
| Seçili klipte normalize ASR metni %100 | 159; onay değildir |
| ASR metninde fark bulunan | 42; 21'i %95 altında |
| Komşu kaynak sınırı | 198/198 bitişik, boşluk/çakışma yok |
| Kapsanan kaynak ses | 3 MP3, 370.000 saniye |
| Yeni WAV / kaynak PCM eşitliği | 27/27 örnek düzeyinde birebir |
| Korunan başlangıç dosyası | 290/290 SHA-256 aynı |

Görev devrindeki üç durumun yanına **NEEDS_LISTEN** eklendi. Dinlenmemiş ama teknik taramadan geçmiş kayıtları APPROVED, NEEDS_CUT veya NEEDS_RERECORD diye yanlış sınıflandırmamak için bu durum kullanıldı. 201 satırın tamamında `manual_listen=NOT_PERFORMED`; `overall_qa_complete=false`.

## Dosyalar

- [fisher_qa_decisions.tsv](fisher_qa_decisions.tsv): 201 benzersiz ID; beklenen metin, seçilen sürüm/yol, ASR, dinleme durumu, karar, gerekçe, SHA-256, kaynak zamanı, ilk/son ASR sözcüğü ve akustik sınır ölçümleri.
- [cuts/B002_20261021](cuts/B002_20261021/): 27 adet `uNNNNNN_v03_candidate.wav`. Mono 44100 Hz PCM16; normalizasyon, fade, esnetme veya oyun kodlaması uygulanmadı.
- [new_cut_manifest.tsv](new_cut_manifest.tsv): kaynak MP3 hash'i ve örnek hassasiyetinde başlangıç / hariç bitiş konumu.
- [candidate_comparison.tsv](candidate_comparison.tsv): 201 v01, 27 eski v02 ve 27 yeni v03 için toplam 255 karşılaştırma satırı; ASR metinleri, sınır enerjisi, gerçek WAV ölçümleri ve seçim.
- [source_word_evidence.tsv](source_word_evidence.tsv): tam MP3 transkriptindeki yaklaşık sözcük zamanları ve karakter eşlemesi. Zorlanmış fonetik hizalama veya kelime sınırı onayı değildir. Tam MP3 ASR'nin atladığı `u000497` ünlemi bu dosyada yoktur; yeni klip ASR'si “Ah!” tanır.
- [neighbor_audit.tsv](neighbor_audit.tsv): aynı partideki 198 komşu çiftin sınır ve kaynak sıra kontrolü.
- [text_discrepancies.tsv](text_discrepancies.tsv): ASR ile beklenen metnin farklı olduğu 42 seçili kayıt.
- [listen_review.html](listen_review.html): 201 seçili WAV ve çevresinden 0,5 saniye paylı kaynak MP3 bağlantıları. 73 öncelikli kayıt filtresi; kalanlar da dinlenecek.
- [selected_201.m3u8](selected_201.m3u8): katalog sırasındaki 201 WAV'ın oynatma listesi; dosyalar taşınmadan kullanılabilir.
- [waveforms/index.html](waveforms/index.html): 201 kaynak dalga biçimi için 11 sayfa ve 27 yeni kesim için 3 ayrıntılı sayfa. Yeşil çizgiler seçili sınırlar, ayrıntılı sayfalarda kırmızı kesik çizgiler eski v01 sınırlarıdır.
- [validation.json](validation.json), [input_snapshot.tsv](input_snapshot.tsv): teknik doğrulama ve değişmez girdi kanıtı.

Yollar proje köküne göredir; rapor/oynatma listesi bağlantıları rapor klasörüne göredir. Eski WAV'lar, MP3'ler, katalog, eski QA raporları, approved_log, approved ve game_ready değiştirilmedi.

## Yedi manuel kayıt

| ID | Seçim | Kaynak saniye | Bulgular ve kalan kontrol |
|---|---|---|---|
| u000435 | v01 korundu | 140.950–142.315 | Sınırlar sessiz, özel ad dahil kaynak konuşma mevcut. “Dougherty” ASR'de “Dorothy”; baştan kesmek gerekmiyor, telaffuz dinlenecek. |
| u000476 | yeni v03 | 145.801–146.758 | “Artık sizin” ayrı; sonraki “Hayır” dışarıda. Yeni ASR %100. |
| u000495 | yeni v03 | 146.758–147.961 | “Hayır” doğru aralığa alındı; sonraki “Ah” ayrı. Yeni ASR %100. |
| u000497 | yeni v03 | 147.961–148.669 | Atlanan kısa ünlem ayrıldı; yeni klip ASR'si “Ah!” tanıyor. Ünlemin niteliği dinlenecek. |
| u000499 | yeni v03 | 148.669–149.972 | “Sağ ol, Wilkes” tam aralık. Yeni ASR %100. |
| u000572 | yeni v03 | 156.881–158.213 | İlk “Sen Ivan mısın”. Medium tek klipte “Sen İvanlısın”, large-v3 bağlamda doğru soruyu tanıyor; dinleme zorunlu. |
| u000582 | yeni v03 | 166.696–167.953 | İkinci “Sen Ivan mısın”. Farklı kaynak aralığı; ilk kayıt kopyalanmadı. Yeni ASR %100. |

## Önemli kesim bulguları

- `u000043` v01 sonuna “Ne gibi” taşmış, `u000045` v01 ise sonraki “Hımm” sesini almıştı. Yeni ortak sınır 24.038 saniye.
- `u000047` hem v01 hem v02'de “Hımm” başlangıcını kaçırıyordu. 24.811 saniyeden başlayan v03 bunu geri alıyor; yeni ASR de ünlemi tanıyor.
- `u000041` v01 korundu. v02'nin 19.46 saniyelik başlangıcı “Hah” sesinin içindeydi.
- `u000467–u000596` içindeki 24 kaydın tümü kaynak sırasına göre yeniden ayrıldı. Her yeni komşu çift aynı sessiz sınırı paylaşıyor.
- `u000510` v02 baştaki sesi kesiyor ve sonundan sonraki “Zaten”e taşıyordu. v03: 149.972–150.850; yeni ASR “Hallederim”.
- `u000512` v02 hem baştan kesiliyor hem “Wilkes”i eksiltiyordu. v03: 150.850–152.952; yeni ASR tam replik.
- `u000474`, `u000586`, `u000588`, `u000594`, `u000596` v02 sürümlerinde metin eşleşmesi güçlü olsa da sınır konuşma içindeydi. v03 sınırları sessizliklere taşındı. Örneğin `u000586` bitişi / `u000588` başlangıcında 30 ms kaynak RMS yaklaşık −17,6 dBFS idi.
- `u000604` v01 korundu; v02 başlangıcı “Sence” içindeydi (yaklaşık −29,6 dBFS).
- `u000721/u000723/u000725` v01 korundu. “İyi iş” tek klip medium ASR'de yanlış, large-v3 kaynak bağlamında doğru tanınıyor. Bu, `u000723` için dinleme onayı değildir.

## Kalan iş ve içerik belirsizlikleri

**201 kaydın tamamı** seçili WAV ve kaynak komşularıyla dinlenmeli: ilk/son hece, nefes/ünlem, komşu kelime, telaffuz ve beklenen içerik. İlk 10 B001 de öncelikli kuyruğa dahil edildi. Sessiz kesim noktası doğru cümleye atanmış olmayı tek başına ispatlamaz.

Özellikle aşağıdaki ASR farkları doğru kesimle çözülemeyebilir; kaynak konuşmada gerçekten varsa daha sonra yeniden üretim gerekebilir. Şimdilik yeniden üretim kararı verilmedi:

| ID | Beklenen / ASR farkı |
|---|---|
| u000047 | 2000'deki / 2000'lerdeki |
| u000111 | NSA / NCA |
| u000123 | Ne haber / Naber |
| u000253 | avludaki lazer ağını / Avru'daki Lazera'nı |
| u000337 | Veriyi / Vereyi |
| u000467 | almam / alman (iki model bağlamında da fark var) |
| u000572 | Ivan mısın / İvanlısın (modeller farklı sonuç veriyor) |
| u000584 | dostun / dostum |
| u000592 | yapacağımı / yapacağını; FBI / FBA |
| u000594 | dağarcığın / dağarcının |
| u000637 | Anahtarın / Anahtarım |
| u000702 | sığınak / sinanak |
| u000719 | sanıyordum / sanıyorum |
| u000732 | Bilmediğim / Bilmediğin |
| u000817 | Yaptığım / Yaptığın |
| u000914 | tehlikesi / tevfikesi |

Özel ad farkları (Echelon, Gurgenidze, Nikoladze, Grinko, Masse, Grimsdottir, Dougherty, Wilkes, Mouke Tsoe Bo, Cristavi, Ark) otomatik kesim hatası sayılmadı. 42 farkın tamamı `text_discrepancies.tsv` içinde; bu tablo yalnız örnek bir kısa liste değildir.

## Yöntem ve doğrulama sınırı

Mevcut 201 klip ASR'si, tam üç MP3 transkripti ve eski 27 v02 sonucu hash doğrulamasıyla kullanıldı. Yeni 27 kesime medium CPU/int8, dört öncelikli kaynak penceresine large-v3 CPU/int8 çalıştırıldı; beklenen metin modele prompt olarak verilmedi. Tam kaynak transkriptindeki karakter eşlemesi birleşik kelime ve özel adları takip etmek için kullanıldı; sözcük zamanları yaklaşık kabul edildi.

Yeni sınırlar kaynakta yaklaşık 5 ms pencereli RMS ve −55 dBFS sessizlik aralıklarıyla yerleştirildi, 27 yeni kesimin dalga biçimleri görsel olarak incelendi. 201 seçili klibin tamamında baş/son akustik tarama yapıldı: ölçülen en kısa baş sessizliği 39,9 ms, son sessizliği 34,9 ms; sınır çevresindeki en yüksek 30 ms RMS −62,17 dBFS. Bunlar fonetik veya işitsel kabul değildir.

Altı regresyon testi geçti: örnek hassasiyeti, geçersiz aralığı reddetme, mevcut WAV'ın üzerine yazmayı engelleme, girdi değişikliğini yakalama, aktif/sessiz sınır ayrımı ve aynı metnin iki farklı kaynak zamanına atanması. Entegrasyon kontrolü 201 hash'i, kaynak PCM uyumunu, 198 kesintisiz komşuluğu, üç tam kaynak kapsamını ve korunan 290 dosyayı doğruladı. Eski WAV'larda manifest/decoder yuvarlaması için ±2 örneklik karşılaştırma kullanıldı; en büyük RMS farkı 0,743 PCM birimidir (tam ölçek 32768). Yeni 27 dosyada tolerans kullanılmadı: PCM birebir aynı.

Dinleme sayfasındaki 201 ses öğesi ve 402 yerel dosya bağlantısı dosya sistemi üzerinden doğrulandı. Kullanılabilir tarayıcı oturumu olmadığından sayfanın tarayıcıda görsel/oynatma testi yapılamadı. Dalga biçimi PNG'leri ayrıca açılıp incelendi. `approved/` veya `game_ready/` için yeni ses üretilmedi.

## Git

Başlangıçta proje kökünde Git deposu yoktu. `fisher-audio-qa` dalında yerel depo oluşturuldu; yalnız bu teslimin araçları, yeni sesleri ve kanıt dosyaları izleniyor. Önceden mevcut proje içeriği arşive topluca alınmadı; `.git/info/exclude` yerel dışlama kullanıyor. İngilizce mesajlı ayrı commitler: girdi hash'leri, kesim aracı/planı, 27 ses ve ASR kanıtı, kaynak kapsamı/görseller, son QA teslimi. Uzak depoya gönderim yapılmadı.
