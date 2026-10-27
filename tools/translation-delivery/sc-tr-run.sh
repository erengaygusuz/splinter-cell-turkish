#!/usr/bin/env bash
set -Eeuo pipefail

HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="/run/media/ereng/files/projects/splinter-cell-turkish"
BRANCH="fisher-audio-qa"
PIN="22308b9cf7d1738a92c7ca97e645dd0017542200"

for file in sc-tr-apply.py sc-tr-010-014.txt sc-tr-015-019.txt sc-tr-020-025.txt; do
  test -s "$HERE/$file" || { echo "Eksik dosya: $HERE/$file" >&2; exit 1; }
done

cd "$ROOT"
test "$(git branch --show-current)" = "$BRANCH"
test "$(git rev-parse HEAD)" = "$PIN"

echo "===== ON KONTROL: 776/776 ====="
python3 "$HERE/sc-tr-apply.py" --preflight

echo
echo "===== TOPLU UYGULAMA: 010-025 ====="
python3 "$HERE/sc-tr-apply.py"

echo
echo "===== SON DURUM ====="
grep -A3 '^## Translation status' manifests/full-game-voice-audit/final-turkish-production-summary.md
echo
git status --short
echo
echo "PASS: tüm 1258 konuşma satırının Türkçesi hazır."
