# Splinter Cell — Dublajı bitirme planı (27 Ekim 2026)

## Öncelik

1. Oyun içi dublajı ve bütün yeni tespit edilen konuşma seslerini bitir.
2. Hazırlanan sıralı ElevenLabs MP3 dosyalarını `new_id` / `u000xxx` eşlemesiyle böl.
3. Oyuna aktarımı ve runtime doğrulamasını yap.
4. **Ancak tüm dublaj tamamlandıktan sonra** altyazı kapsamını oyunun tamamına genişlet.

Kullanıcıdan eski sesleri tekrar dinlemesi istenmeyecek. Hedef harfiyen çeviri değil, sahne/karakter/hikâye açısından uygun Türkçe.

## Envanter — sayıları birbirine ekleme mantığı

Eski Türkçe gameplay corpus'u: **1086** farklı ID. Kullanılan 408 ses korunur; kalan 678 ID için önceki ElevenLabs üretimi:

- Stage A: 144/144 repliğin kaynak sesi ve kesim adayı var. 7 karakterin 29+23+37+23+13+10+9 oyun içi replikleri.
- Stage B (figüran B001): 177/177 üretilmiş, kesim adayı var; bir erkek sesinin yanlış atanması nedeniyle yinelenmiş alternatifler teslim dışı.
- Stage C (B002): 357 ID'den 355'i için 391 ayrı clean/FX kesim adayı var. İki kesin eksik `u000972`, `u000975` (S126).
- Toplam kesim adayı olan ID: **676/678**. Bunlar otomatik/süreç adaylarıdır; nihai oyun kurulumuna eşit değildir.
- Önceki 408 sesin dışında 678 için yeni DLL runtime hazır raporlanmamıştır.

EKSİK LEGACY S126:

1. `u000972` — daha kıdemli/otoriter erkek: `[annoyed] Avtandil, şu köpeğinin pisliğini temizlesene.`
2. `u000975` — ast/uyumlu erkek: `[respectfully] Emredersiniz.`

**Yeni keşfedilen ve Türkçesi tamamlanan 1258 benzersiz konuşma kaydı**, mevcut 1086 ID'nin dışındadır. Yeni seslerin seslendirme/teslim kapsamı:
- 979 BARK_* düşman/NPC repliği
- 98 telsiz/kamera anonsu
- 130 görev içi konuşma; tamamı karakter/sahne rolüne atanmış durumda
- 51 kısa komut / diğer konuşma

Toplam 1258. Sahnelerin 36 repliği proje içindeki senaryo konuşmacı referanslarından, kalan 94 teknik `S*_Voice` kaydı ise Vselka/Kola görev transkriptlerindeki gerçek konuşma sırasından karakter/rol bazında çözüldü. **Konuşmacısı belirsiz görev içi replik kalmadı (0).**

`manifests/full-game-voice-audit/final-turkish-production-voices.csv` üzerinde **FINAL_TR=1258, NEEDS_TR_TRANSLATION=0**; bu metin kapsamıdır, MP3 kaydı değildir.

Ayrıca `final-vocalization-review.csv` kapsamındaki 54 sözsüz insan sesi (bağımsız üretim kararı) ve FMV'ler (önceki envanterde 265 video içi konuşma, ayrı akış) son toplam çalışmadan çıkarılmamalı.

## ElevenLabs üretimi

`tools/full_game_voice_audit/create_elevenlabs_dubbing_queue.py` dosyası:
- ana çeviri manifestini ve `event-source-text.csv` senaryo konuşmacı referanslarını okur;
- oynanabilir karakter/asker arketipini veya senaryodaki FISHER/LAMBERT/GRIMSDOTTIR gibi gerçek rolü ayırır;
- 1258/1258 yeni repliği ses grubuna atar ve duygu etiketi + `[short pause]` ile varsayılan **1000 karakter** üst sınırında üretim paketlerine böler;
- görev içi 130 repliğin tamamını Fisher/Lambert/Grimsdottir/Bobrov/Masse/Alekseevich veya sahneye özel muhafız-teknisyen-mafya rolleriyle ayırır;
- her MP3 içinde replik sıra numarası ve ID'yi `00_production_index.csv` dosyasında korur;
- eksik S126 iki repliği iki ayrı karakter TXT dosyasına çıkarır;
- oyun dosyalarına, ses bankalarına, mevcut seslere ve DLL'ye dokunmaz.

Kullanım: projeye ait dalı değiştirmeden scripti indir ve şu biçimde çağır:

```bash
python3 create_elevenlabs_dubbing_queue.py \
  --root "/run/media/ereng/files/projects/splinter-cell-turkish" \
  --out "$HOME/Downloads/SplinterCell-ElevenLabs"
```

Duygu etiketleri Eleven v3 tarzındadır. `[shouts]`, `[whispers]`, `[curious]` gibi tag'ler sese yön verir ama seçilen sesin karakteristiklerini aşamayabilir. Dry/temiz ses üret; telsiz filtresi, eski cihaz/kamera radyo tonu ve mekan efekti sonradan uygulanır. Tek MP3 içinde birden çok karakter birleştirme. Dosya adlarını `00_production_index.csv` ile eşle.

Sıra: S126 2 replik → karaktere göre ayrılmış yeni BARK/SHORT_COMMAND ve kamera/telsiz → karakteri belirlenmiş 130 hikâye repliği → 54 vocalization ihtiyacı → FMV'ler → ses kesimi ve entegrasyon → tüm oyun altyazısı.

## Kaynaklar

- `dubbing/qa/remaining678_v1_20261023/expected_candidates.json`
- `dubbing/qa/remaining678_v1_20261023/cuts_A.tsv`
- `dubbing/qa/remaining678_v1_20261023/cuts_B.tsv`
- `dubbing/qa/remaining678_v1_20261023/cuts_C.tsv`
- `tools/remaining678/B002_REPAIR_20261023.md`
- `manifests/full-game-voice-audit/final-turkish-production-voices.csv`
- `manifests/full-game-voice-audit/event-source-text.csv`

Bu plan bir ses dinleme veya runtime testi yerine geçmez; kullanıcı kapsamı gereği ses dinleme zorunluluğu yoktur. Kararları esasen konuşmacı bağlamı, ID ve metin eşlemesi belirler.

## 27 Ekim konuşmacı çözümleme sonucu

- Teknik görev etiketi çözümü: **94/94**.
- Yeni konuşma manifesti: **1258/1258 ses grubuna atanmış**.
- Ses grubu sayısı: **55**.
- Varsayılan 1000 karakterlik ElevenLabs paketlemesinde: **101 prompt/TXT**.
- Önceki 678 paketten kaynak MP3'ü bulunmayan: **2** (`u000972`, `u000975`).
- Toplam kalan sözlü üretim hedefi: **1260 replik**.
