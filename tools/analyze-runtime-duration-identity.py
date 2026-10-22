#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import struct
from collections import defaultdict
from pathlib import Path

PROJECT = Path("/run/media/ereng/files/projects/splinter-cell-turkish")

CORPUS = PROJECT / "manifests/corpus.csv"
WORKLISTS = [
    PROJECT / "manifests/fisher-lambert-dub-worklist.csv",
    PROJECT / "manifests/fisher-lambert-dub-worklist-tr-ready.csv",
]
AUTHORITATIVE = PROJECT / "manifests/runtime-dub-authoritative.csv"


def load_csv(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def choose_worklist():
    for path in WORKLISTS:
        if path.is_file():
            return path
    raise SystemExit("ERROR: Fisher/Lambert worklist not found")


def duration_seconds(row):
    sample_count = int(row["sample_count"])
    sample_rate = int(row["sample_rate"])
    if sample_rate <= 0:
        raise ValueError("invalid sample rate")
    return sample_count / sample_rate


def q01ms(seconds):
    # Integer tenths of a millisecond. Avoid Python float-string matching.
    return int(round(seconds * 10000.0))


def main():
    print("===== PRECHECK =====")

    worklist_path = choose_worklist()

    for path in [CORPUS, worklist_path, AUTHORITATIVE]:
        if not path.is_file():
            raise SystemExit(f"ERROR: missing file: {path}")

    corpus = load_csv(CORPUS)
    work = load_csv(worklist_path)
    authoritative = load_csv(AUTHORITATIVE)

    if len(corpus) != 1093:
        raise SystemExit(f"ERROR: expected 1093 corpus rows, got {len(corpus)}")
    if len(work) != 408:
        raise SystemExit(f"ERROR: expected 408 worklist rows, got {len(work)}")

    corpus_by_id = {row["id"].strip(): row for row in corpus}
    target_ids = {row["id"].strip() for row in work}

    if len(target_ids) != 408:
        raise SystemExit("ERROR: target UID set is not unique")

    print("PASS: corpus rows 1093")
    print("PASS: Fisher/Lambert rows 408")

    print()
    print("===== GLOBAL DURATION COLLISIONS =====")

    all_by_duration = defaultdict(list)
    for row in corpus:
        all_by_duration[q01ms(duration_seconds(row))].append(row)

    target_safe_global = []
    target_ambiguous_global = []

    for uid in sorted(target_ids):
        row = corpus_by_id[uid]
        key = q01ms(duration_seconds(row))
        candidates = all_by_duration[key]

        if len(candidates) == 1:
            target_safe_global.append(uid)
        else:
            target_ambiguous_global.append(
                (uid, key, [(x["id"], x.get("speaker", ""), x["map_name"]) for x in candidates])
            )

    print(f"Target rows unique globally at 0.1 ms: {len(target_safe_global)}/408")
    print(f"Target rows ambiguous globally: {len(target_ambiguous_global)}")

    for item in target_ambiguous_global[:40]:
        print("GLOBAL_AMBIG", item)

    print()
    print("===== BANK + DURATION COLLISIONS =====")

    all_by_bank_duration = defaultdict(list)

    for row in corpus:
        header = int(row["header_id"], 0)
        bank = header & 0xFFFF0000
        key = (bank, q01ms(duration_seconds(row)))
        all_by_bank_duration[key].append(row)

    target_safe_bank = []
    target_ambiguous_bank = []

    for uid in sorted(target_ids):
        row = corpus_by_id[uid]
        header = int(row["header_id"], 0)
        bank = header & 0xFFFF0000
        key = (bank, q01ms(duration_seconds(row)))
        candidates = all_by_bank_duration[key]

        if len(candidates) == 1:
            target_safe_bank.append(uid)
        else:
            target_ambiguous_bank.append(
                (
                    uid,
                    f"{bank:08X}",
                    key[1],
                    [(x["id"], x.get("speaker", ""), x["map_name"]) for x in candidates],
                )
            )

    print(f"Target rows unique by old bank + 0.1 ms: {len(target_safe_bank)}/408")
    print(f"Target rows ambiguous by old bank + 0.1 ms: {len(target_ambiguous_bank)}")

    for item in target_ambiguous_bank[:40]:
        print("BANK_AMBIG", item)

    print()
    print("===== VERIFIED ACTUAL BANK STABILITY =====")

    actual_by_uid = {}
    for row in authoritative:
        uid = (row.get("id") or "").strip()
        editor = (row.get("editor_id") or "").strip()
        if not uid or not editor or uid not in corpus_by_id:
            continue
        actual_by_uid[uid] = int(editor, 0)

    same_bank = 0
    different_bank = []

    for uid, actual in sorted(actual_by_uid.items()):
        old = int(corpus_by_id[uid]["header_id"], 0)
        if (old & 0xFFFF0000) == (actual & 0xFFFF0000):
            same_bank += 1
        else:
            different_bank.append(
                (uid, f"{old:08X}", f"{actual:08X}")
            )

    total_verified = same_bank + len(different_bank)

    print(f"Verified UID anchors checked: {total_verified}")
    print(f"Same high-word bank: {same_bank}")
    print(f"Different high-word bank: {len(different_bank)}")

    for item in different_bank[:40]:
        print("BANK_DIFFER", item)

    print()
    print("===== TARGET ORIGINAL DURATION UNIQUENESS =====")

    target_exact = defaultdict(list)
    for uid in target_ids:
        row = corpus_by_id[uid]
        key = (
            int(row["sample_count"]),
            int(row["sample_rate"]),
        )
        target_exact[key].append(uid)

    exact_collisions = [
        ids for ids in target_exact.values()
        if len(ids) > 1
    ]

    print(f"Exact target duration keys: {len(target_exact)}/408")
    print(f"Exact target collision groups: {len(exact_collisions)}")
    for ids in exact_collisions:
        print("TARGET_EXACT_AMBIG", ids)

    print()
    print("===== DECISION =====")

    if not target_ambiguous_bank:
        print("RUNTIME_DURATION_DISPATCH: BANK_PLUS_0_1MS_SAFE")
    elif len(target_ambiguous_global) <= 10:
        print("RUNTIME_DURATION_DISPATCH: GLOBAL_MOSTLY_SAFE_NEEDS_SMALL_EXCEPTION_TABLE")
    else:
        print("RUNTIME_DURATION_DISPATCH: NEEDS_ADDITIONAL_DISAMBIGUATION")


if __name__ == "__main__":
    main()
