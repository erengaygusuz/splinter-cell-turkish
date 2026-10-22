#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
import struct
from pathlib import Path

PROJECT = Path("/run/media/ereng/files/projects/splinter-cell-turkish")
GAME = Path("/run/media/ereng/files/games/tom-clancys-splinter-cell/drive_c/GOG Games/Splinter Cell")

CORPUS = PROJECT / "manifests/corpus.csv"
AUTH = PROJECT / "manifests/runtime-dub-authoritative.csv"
LOG = GAME / "system/snd-waveout-training-v16.log"

TRAINING_IDS = [f"u{n:06d}" for n in range(13, 30)]

def load_csv(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def f32_bits(value: float) -> int:
    return struct.unpack("<I", struct.pack("<f", value))[0]

def bits_to_f32(bits: int) -> float:
    return struct.unpack("<f", struct.pack("<I", bits))[0]

def main():
    print("===== PRECHECK =====")
    for p in (CORPUS, AUTH, LOG):
        if not p.is_file():
            raise SystemExit(f"ERROR: missing required file: {p}")

    corpus = {r["id"].strip(): r for r in load_csv(CORPUS)}
    auth = {r["id"].strip(): r for r in load_csv(AUTH) if (r.get("id") or "").strip()}

    expected = {}
    editor_to_uid = {}

    for uid in TRAINING_IDS:
        if uid not in corpus:
            raise SystemExit(f"ERROR: missing corpus row: {uid}")
        if uid not in auth:
            raise SystemExit(f"ERROR: missing authoritative mapping: {uid}")

        row = corpus[uid]
        seconds = int(row["sample_count"]) / int(row["sample_rate"])
        bits = f32_bits(seconds)
        editor = int(auth[uid]["editor_id"], 0)

        expected[uid] = (bits, seconds, editor)
        editor_to_uid[editor] = uid

    print("PASS: 17 expected Training duration identities loaded")

    seen = {}
    pattern = re.compile(
        r"^runtime_trigger\s+([0-9A-Fa-f]{8})\s+([0-9A-Fa-f]{8})\s+"
    )

    for line in LOG.read_text(encoding="utf-8", errors="replace").splitlines():
        m = pattern.match(line)
        if not m:
            continue
        editor = int(m.group(1), 16)
        old_bits = int(m.group(2), 16)
        uid = editor_to_uid.get(editor)
        if uid:
            seen[uid] = old_bits

    missing = [uid for uid in TRAINING_IDS if uid not in seen]
    if missing:
        raise SystemExit(f"ERROR: missing runtime_trigger rows: {missing}")

    print()
    print("===== DURATION BIT COMPARISON =====")

    max_ulps = 0
    max_ms = 0.0

    for uid in TRAINING_IDS:
        expected_bits, expected_seconds, editor = expected[uid]
        actual_bits = seen[uid]

        # All values are positive IEEE754 floats, so raw bit ordering is monotonic.
        ulps = abs(actual_bits - expected_bits)
        actual_seconds = bits_to_f32(actual_bits)
        delta_ms = abs(actual_seconds - expected_seconds) * 1000.0

        max_ulps = max(max_ulps, ulps)
        max_ms = max(max_ms, delta_ms)

        print(
            f"{uid} editor={editor:08X} "
            f"expected={expected_bits:08X} actual={actual_bits:08X} "
            f"ulps={ulps} delta_ms={delta_ms:.6f}"
        )

    print()
    print(f"Max ULP delta: {max_ulps}")
    print(f"Max duration delta ms: {max_ms:.6f}")

    if max_ms >= 0.05:
        raise SystemExit(
            "ERROR: runtime original duration differs by >= 0.05 ms; "
            "duration dispatch is not safe"
        )

    if max_ulps > 128:
        raise SystemExit(
            f"ERROR: runtime original duration exceeds 128 ULP: {max_ulps}"
        )

    print("PASS: runtime USound original durations stay within 128 ULP")
    print("DURATION_DISPATCH_PREFLIGHT: PASS")

if __name__ == "__main__":
    main()
