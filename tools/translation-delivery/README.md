# Splinter Cell Türkçe — Toplu çeviri teslim paketi

Bu dizindeki beş dosyayı aynı klasöre (ör. `~/Downloads`) indir:

- `sc-tr-run.sh` — tek-komut çalıştırıcı
- `sc-tr-apply.py` — ortak uygulayıcı / kapsam ve disk QA
- `sc-tr-010-014.txt` — 250 bark (son başarısız makro düzeltilmiş)
- `sc-tr-015-019.txt` — 250 bark
- `sc-tr-020-025.txt` — 276 bark + kısa replik

Sonra:

```bash
bash "$HOME/Downloads/sc-tr-run.sh"
```

**Beklenen başlangıç:** 482 FINAL_TR / 776 NEEDS_TR_TRANSLATION.

**Ara sonuçlar:**
- 010–014: 732 / 526
- 015–019: 982 / 276
- 020–025: 1258 / 0

Çalıştırma iki aşamalıdır: üç parçanın tamamını önce **yazmadan doğrular**, ardından sırayla uygular. Her grupta kaynak ID, source metin, çeviri kapsamı, Türkçe Latin gösterim dönüşümü ve satır sayısı denetlenir. İşlem öncesinde dizin/branch ve commit SHA korunur.

Sadece `manifests/full-game-voice-audit/final-turkish-production-voices.csv`, ilgili özetler ve `translation-work` içerisindeki resolved çıktıları değişir. Ses dosyalarına, V27'ye, oyun kurulumuna, ses bankalarına dokunulmaz. **Commit/push yapılmaz.**

Not: Kaynakta şüpheli otomatik transkripsiyon olan satırların İngilizce metinleri korunmuştur; bağlam temelli Türkçeler ayrıca ses kontrolü gerektirebilir. Sayısal 1258/1258 veri kapsamını bildirir, sesle nihai editöryal uyumu garanti etmez.
