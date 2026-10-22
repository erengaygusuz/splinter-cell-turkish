#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import re
import shutil
import struct
import time
import wave
from collections import defaultdict
from pathlib import Path

PROJECT = Path("/run/media/ereng/files/projects/splinter-cell-turkish")
GAME = Path("/run/media/ereng/files/games/tom-clancys-splinter-cell/drive_c/GOG Games/Splinter Cell")
SYSTEM = GAME / "system"

UAX_CATALOG = PROJECT / "manifests/uax-editor-id-catalog.csv"
CORPUS = PROJECT / "manifests/corpus.csv"
AUTHORITATIVE = PROJECT / "manifests/runtime-dub-authoritative.csv"

GAMEPLAY_UID_SOUND_MANIFESTS = [
    PROJECT / "manifests/full-gameplay-subtitle-ready.csv",
    PROJECT / "manifests/full-gameplay-subtitle-review.csv",
    PROJECT / "manifests/full-gameplay-subtitle-recovered-section-order.csv",
    PROJECT / "manifests/full-gameplay-subtitle-still-review-after-section-order.csv",
]

V16_SOURCE = PROJECT / "gameplay-subtitle-poc/src/snd_waveout_training_v16.cpp"

WORKLIST_CANDIDATES = [
    PROJECT / "manifests/fisher-lambert-dub-worklist.csv",
    PROJECT / "manifests/fisher-lambert-dub-worklist-tr-ready.csv",
]

FISHER_SELECTED = (
    PROJECT
    / "dubbing/characters/sam_fisher/gameplay/voice_versions/VD001/qa"
    / "full201_v2_20261021/selected_cuts_201.tsv"
)

LAMBERT_SELECTED = (
    PROJECT
    / "dubbing/characters/irving_lambert/gameplay/qa"
    / "lambert_207_v1_20261021/selected_cuts.tsv"
)

OUT_MANIFEST = PROJECT / "manifests/fisher-lambert-runtime-v17.csv"
OUT_UNRESOLVED = PROJECT / "manifests/fisher-lambert-runtime-v17-unresolved.csv"
OUT_BANKS = PROJECT / "manifests/fisher-lambert-runtime-v17-banks.csv"
OUT_SOURCE = PROJECT / "gameplay-subtitle-poc/src/snd_waveout_fisher_lambert_v17.cpp"

TARGET_AUDIO = SYSTEM / "sc-tr-audio"


def load_csv(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def load_tsv(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def parse_int(value: str) -> int:
    value = str(value or "").strip()
    if not value:
        raise ValueError("empty integer")
    return int(value, 0)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def wav_duration_ms(path: Path) -> int:
    with wave.open(str(path), "rb") as w:
        frames = w.getnframes()
        rate = w.getframerate()
        if rate <= 0:
            raise RuntimeError(f"invalid WAV sample rate: {path}")
        return int(round(frames * 1000.0 / rate))


def float_bits_seconds(ms: int) -> int:
    return struct.unpack("<I", struct.pack("<f", ms / 1000.0))[0]


def choose_worklist() -> Path:
    found = [p for p in WORKLIST_CANDIDATES if p.is_file()]
    if not found:
        raise SystemExit(
            "ERROR: Fisher/Lambert worklist not found. Expected one of:\n"
            + "\n".join(str(p) for p in WORKLIST_CANDIDATES)
        )
    return found[0]


def full_sound_object(row: dict) -> str:
    value = (row.get("sound_object") or "").strip()
    if not value:
        return ""
    if "." in value:
        return value
    package = (row.get("package") or row.get("uax_package") or "").strip()
    return f"{package}.{value}" if package else value


def normalize_text(value: str) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def load_direct_uid_sound_mappings(
    manifests: list[Path],
    uax_by_sound: dict[str, int],
    work_by_id: dict[str, dict],
):
    resolved = {}
    sound_by_uid = {}
    source_by_uid = {}
    conflicts = []
    rejected = []

    for manifest in manifests:
        if not manifest.is_file():
            continue

        for row in load_csv(manifest):
            uid = (row.get("id") or "").strip()
            sound = full_sound_object(row)

            if not uid or not sound or uid not in work_by_id:
                continue

            work = work_by_id[uid]

            # Never trust the legacy editor_id column here.
            # Accept UID -> sound_object only when the row also identifies
            # the same physical LS0 asset as the Fisher/Lambert worklist.
            same_resource = (
                (row.get("resource_name") or "").strip()
                == (work.get("resource_name") or "").strip()
            )
            same_offset = (
                str(row.get("stream_offset") or "").strip()
                == str(work.get("stream_offset") or "").strip()
            )

            row_text = normalize_text(
                row.get("english_text")
                or row.get("canonical_text")
                or ""
            )
            work_text = normalize_text(work.get("english_text") or "")

            same_text = (
                not row_text
                or not work_text
                or row_text == work_text
            )

            if not (same_resource and same_offset and same_text):
                rejected.append(
                    (
                        uid,
                        manifest.name,
                        same_resource,
                        same_offset,
                        same_text,
                    )
                )
                continue

            actual = uax_by_sound.get(sound.lower())
            if actual is None:
                continue

            previous = resolved.get(uid)
            if previous is not None and previous != actual:
                conflicts.append(
                    (
                        uid,
                        previous,
                        actual,
                        source_by_uid[uid],
                        manifest.name,
                    )
                )
                continue

            resolved[uid] = actual
            sound_by_uid[uid] = sound
            source_by_uid[uid] = manifest.name

    return (
        resolved,
        sound_by_uid,
        source_by_uid,
        conflicts,
        rejected,
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--stage-audio",
        action="store_true",
        help="Copy the 408 selected WAV files into system/sc-tr-audio after all validation passes.",
    )
    args = ap.parse_args()

    print("===== PRECHECK =====")

    worklist_path = choose_worklist()

    for p in [
        worklist_path,
        UAX_CATALOG,
        CORPUS,
        AUTHORITATIVE,
        V16_SOURCE,
        FISHER_SELECTED,
        LAMBERT_SELECTED,
    ]:
        if not p.is_file():
            raise SystemExit(f"ERROR: missing required file: {p}")

    work = load_csv(worklist_path)
    corpus = load_csv(CORPUS)
    uax = load_csv(UAX_CATALOG)
    authoritative = load_csv(AUTHORITATIVE)
    fisher_selected = load_tsv(FISHER_SELECTED)
    lambert_selected = load_tsv(LAMBERT_SELECTED)

    if len(work) != 408:
        raise SystemExit(f"ERROR: expected 408 worklist rows, got {len(work)}")
    if len(fisher_selected) != 201:
        raise SystemExit(
            f"ERROR: expected 201 Fisher selected cuts, got {len(fisher_selected)}"
        )
    if len(lambert_selected) != 207:
        raise SystemExit(
            f"ERROR: expected 207 Lambert selected cuts, got {len(lambert_selected)}"
        )

    work_ids = [r["id"].strip() for r in work]
    if len(set(work_ids)) != 408:
        raise SystemExit("ERROR: worklist UID set is not unique")

    work_by_id = {
        row["id"].strip(): row
        for row in work
    }

    print("PASS: 408 unique Fisher/Lambert worklist rows")
    print("PASS: Fisher selected cuts 201")
    print("PASS: Lambert selected cuts 207")

    print()
    print("===== INDEX CORPUS / UAX =====")

    corpus_by_id = {}
    corpus_bank_ids = defaultdict(set)

    for row in corpus:
        uid = (row.get("id") or "").strip()
        if not uid:
            continue

        old_id = parse_int(row.get("header_id", ""))
        corpus_by_id[uid] = row
        corpus_bank_ids[old_id & 0xFFFF0000].add(old_id)

    uax_by_id = {}
    uax_by_sound = {}

    for row in uax:
        actual = parse_int(row["editor_id"])
        full = f"{row['package'].strip()}.{row['sound_object'].strip()}"

        if actual in uax_by_id:
            raise SystemExit(f"ERROR: duplicate UAX editor ID: {actual:08X}")

        uax_by_id[actual] = row
        uax_by_sound[full.lower()] = actual

    print(f"PASS: corpus rows: {len(corpus_by_id)}")
    print(f"PASS: UAX editor IDs: {len(uax_by_id)}")

    print()
    print("===== DIRECT GAMEPLAY UID -> SOUND OBJECT =====")

    (
        direct_ids,
        direct_sound,
        direct_source,
        direct_conflicts,
        direct_rejected,
    ) = load_direct_uid_sound_mappings(
        GAMEPLAY_UID_SOUND_MANIFESTS,
        uax_by_sound,
        work_by_id,
    )

    if direct_conflicts:
        print(f"Direct mapping conflicts: {len(direct_conflicts)}")
        for conflict in direct_conflicts[:20]:
            print("CONFLICT:", conflict)
        raise SystemExit(
            "ERROR: direct gameplay UID -> UAX conflicts found"
        )

    direct_targets = [
        uid for uid in work_ids
        if uid in direct_ids
    ]

    print(
        "PASS: direct UAX-resolved Fisher/Lambert targets: "
        f"{len(direct_targets)}"
    )
    print(
        "Rejected direct rows failing physical/text identity checks: "
        f"{len(direct_rejected)}"
    )

    print()
    print("===== VERIFIED UID -> UAX PAIRS =====")

    explicit = {}
    explicit_sound = {}

    for row in authoritative:
        uid = (row.get("id") or "").strip()
        sound = full_sound_object(row)

        if not uid or not sound:
            continue

        actual = uax_by_sound.get(sound.lower())
        if actual is None:
            raise SystemExit(
                f"ERROR: authoritative sound object missing from UAX catalog: {uid} {sound}"
            )

        previous = explicit.get(uid)
        if previous is not None and previous != actual:
            raise SystemExit(
                f"ERROR: authoritative UID conflict: {uid} "
                f"{previous:08X} vs {actual:08X}"
            )

        explicit[uid] = actual
        explicit_sound[uid] = sound

    # Local gameplay subtitle manifests are stronger for UID coverage than
    # the deduplicated runtime manifest. They are still verified against
    # the authoritative UAX catalog before use.
    for uid, actual in direct_ids.items():
        previous = explicit.get(uid)
        if previous is not None and previous != actual:
            raise SystemExit(
                f"ERROR: authoritative/direct UID conflict for {uid}: "
                f"{previous:08X} vs {actual:08X}"
            )

        explicit[uid] = actual
        explicit_sound[uid] = direct_sound[uid]

    verified_targets = [uid for uid in work_ids if uid in explicit]
    all_verified_corpus_uids = [
        uid for uid in explicit
        if uid in corpus_by_id
    ]

    print(f"PASS: verified Fisher/Lambert UID mappings: {len(verified_targets)}")
    print(
        "PASS: all authoritative UID anchors available for bank learning: "
        f"{len(all_verified_corpus_uids)}"
    )

    print()
    print("===== LEARN BANK TRANSFORMS =====")

    known_by_bank = defaultdict(list)

    for uid in all_verified_corpus_uids:
        c = corpus_by_id[uid]

        old = parse_int(c["header_id"])
        actual = explicit[uid]

        if (old & 0xFFFF0000) != (actual & 0xFFFF0000):
            # A row may legitimately point at a different package/bank.
            # Such a row cannot teach a within-bank header transform.
            continue

        known_by_bank[old & 0xFFFF0000].append((uid, old, actual))

    bank_rules = {}
    bank_report = []

    target_banks = defaultdict(list)
    for row in work:
        uid = row["id"].strip()
        c = corpus_by_id.get(uid)
        if c is None:
            continue
        old = parse_int(c["header_id"])
        target_banks[old & 0xFFFF0000].append(uid)

    for bank in sorted(target_banks):
        known = known_by_bank.get(bank, [])
        target_count = len(target_banks[bank])
        distinct_known = {(old, actual) for _, old, actual in known}

        candidates = []

        if known:
            # Identity.
            if all(old == actual for _, old, actual in known):
                def identity(value: int, _bank=bank) -> int:
                    return value

                candidates.append(("identity", "", identity))

            # Constant low-word offset.
            deltas = {
                (actual & 0xFFFF) - (old & 0xFFFF)
                for _, old, actual in known
            }

            if len(deltas) == 1:
                delta = next(iter(deltas))

                def offset_rule(value: int, _bank=bank, _delta=delta) -> int:
                    low = (value & 0xFFFF) + _delta
                    if low < 0 or low > 0xFFFF:
                        return 0xFFFFFFFF
                    return _bank | low

                if all(
                    offset_rule(old) == actual
                    for _, old, actual in known
                ):
                    candidates.append(
                        ("offset", f"{delta:+d}", offset_rule)
                    )

            # Full reverse: actual_low = K - old_low.
            sums_all = {
                (old & 0xFFFF) + (actual & 0xFFFF)
                for _, old, actual in known
            }

            if len(sums_all) == 1:
                k = next(iter(sums_all))

                if k <= 0xFFFF:
                    def reverse_rule(value: int, _bank=bank, _k=k) -> int:
                        low = _k - (value & 0xFFFF)
                        if low < 0 or low > 0xFFFF:
                            return 0xFFFFFFFF
                        return _bank | low

                    if all(
                        reverse_rule(old) == actual
                        for _, old, actual in known
                    ):
                        candidates.append(
                            ("reverse", f"0x{k:04X}", reverse_rule)
                        )

            # Piecewise reverse:
            #   low <= K  -> K-low
            #   low >  K  -> identity
            non_identity = [
                (old, actual)
                for _, old, actual in known
                if old != actual
            ]

            sums = {
                (old & 0xFFFF) + (actual & 0xFFFF)
                for old, actual in non_identity
            }

            if len(non_identity) >= 2 and len(sums) == 1:
                k = next(iter(sums))

                if k <= 0xFFFF:
                    def reverse_piecewise(value: int, _bank=bank, _k=k) -> int:
                        low = value & 0xFFFF
                        mapped_low = low if low > _k else _k - low
                        return _bank | mapped_low

                    if all(
                        reverse_piecewise(old) == actual
                        for _, old, actual in known
                    ):
                        candidates.append(
                            ("reverse_piecewise", f"0x{k:04X}", reverse_piecewise)
                        )

        valid = []

        for name, param, fn in candidates:
            predicted = {}
            reverse_seen = {}
            ok = True

            for old in corpus_bank_ids.get(bank, set()):
                actual = fn(old)

                if actual not in uax_by_id:
                    ok = False
                    break

                previous_old = reverse_seen.get(actual)
                if previous_old is not None and previous_old != old:
                    ok = False
                    break

                predicted[old] = actual
                reverse_seen[actual] = old

            if ok and all(fn(old) == actual for _, old, actual in known):
                valid.append((name, param, fn))

        # If only one target exists and it is explicit, no inference is needed.
        if target_count == 1 and all(uid in explicit for uid in target_banks[bank]):
            bank_rules[bank] = ("explicit_only", "", None)
            chosen = "explicit_only"
            param = ""
        elif len(valid) == 1:
            chosen, param, fn = valid[0]
            bank_rules[bank] = (chosen, param, fn)
        else:
            chosen = "unresolved"
            param = ""

        bank_report.append({
            "bank_hex": f"{bank:08X}",
            "target_rows": str(target_count),
            "verified_pairs": str(len(distinct_known)),
            "rule": chosen,
            "parameter": param,
            "candidate_count": str(len(valid)),
        })

        print(
            f"{bank:08X}: targets={target_count:3d} "
            f"verified={len(distinct_known):3d} rule={chosen} {param}"
        )

    with OUT_BANKS.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "bank_hex",
                "target_rows",
                "verified_pairs",
                "rule",
                "parameter",
                "candidate_count",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(bank_report)

    print()
    print("===== RESOLVE 408 TARGETS =====")

    resolved = []
    unresolved = []

    for row in work:
        uid = row["id"].strip()
        speaker = row["speaker"].strip().upper()

        c = corpus_by_id.get(uid)
        if c is None:
            unresolved.append({
                "id": uid,
                "speaker": speaker,
                "reason": "missing_corpus_row",
            })
            continue

        # Ensure worklist and corpus refer to the same physical stream.
        for key in ("resource_name", "stream_offset", "stream_size"):
            if str(row.get(key, "")).strip() != str(c.get(key, "")).strip():
                unresolved.append({
                    "id": uid,
                    "speaker": speaker,
                    "reason": f"worklist_corpus_{key}_mismatch",
                })
                c = None
                break

        if c is None:
            continue

        old = parse_int(c["header_id"])
        bank = old & 0xFFFF0000

        if uid in explicit:
            actual = explicit[uid]
            if uid in direct_ids:
                method = "uax_verified_gameplay_sound_object"
            else:
                method = "uax_verified_sound_object"
            sound = explicit_sound[uid]
        else:
            rule = bank_rules.get(bank)
            if not rule or rule[2] is None:
                unresolved.append({
                    "id": uid,
                    "speaker": speaker,
                    "reason": "no_verified_bank_transform",
                })
                continue

            actual = rule[2](old)
            method = f"bank_{rule[0]}"
            uax_row = uax_by_id.get(actual)
            sound = (
                f"{uax_row['package']}.{uax_row['sound_object']}"
                if uax_row else ""
            )

        if actual not in uax_by_id:
            unresolved.append({
                "id": uid,
                "speaker": speaker,
                "reason": f"resolved_id_not_in_uax_{actual:08X}",
            })
            continue

        resolved.append({
            "id": uid,
            "speaker": speaker,
            "map_name": row.get("map_name", ""),
            "resource_name": row.get("resource_name", ""),
            "stream_offset": row.get("stream_offset", ""),
            "stream_size": row.get("stream_size", ""),
            "old_header_id_hex": f"{old:08X}",
            "editor_id": str(actual),
            "editor_id_hex": f"{actual:08X}",
            "sound_object": sound,
            "mapping_method": method,
            "english_text": row.get("english_text", ""),
            "turkish_text": row.get("turkish_text", ""),
        })

    # No two target lines should resolve to the same runtime event.
    by_editor = defaultdict(list)
    for row in resolved:
        by_editor[row["editor_id_hex"]].append(row["id"])

    duplicates = {
        editor: ids
        for editor, ids in by_editor.items()
        if len(ids) > 1
    }

    if duplicates:
        for editor, ids in sorted(duplicates.items()):
            for uid in ids:
                unresolved.append({
                    "id": uid,
                    "speaker": "",
                    "reason": f"duplicate_runtime_editor_id_{editor}",
                })
        resolved = [
            row for row in resolved
            if row["editor_id_hex"] not in duplicates
        ]

    print(f"Resolved:   {len(resolved)}")
    print(f"Unresolved: {len(unresolved)}")

    unresolved_fields = ["id", "speaker", "reason"]
    with OUT_UNRESOLVED.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=unresolved_fields,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(unresolved)

    if len(resolved) != 408 or unresolved:
        print()
        print("READY_FOR_RUNTIME: NO")
        print("No game audio was changed.")
        print("Unresolved report:", OUT_UNRESOLVED)
        return

    print("PASS: 408/408 editor IDs resolved through UAX-validated rules")

    print()
    print("===== VALIDATE 408 SELECTED WAVS =====")

    selected = {}
    for speaker, rows in (
        ("FISHER", fisher_selected),
        ("LAMBERT", lambert_selected),
    ):
        for row in rows:
            uid = row["id"].strip()
            if uid in selected:
                raise SystemExit(f"ERROR: duplicate selected WAV UID: {uid}")

            wav_path = PROJECT / row["wav_path"]
            if not wav_path.is_file():
                raise SystemExit(f"ERROR: selected WAV missing: {wav_path}")

            expected_sha = row.get("sha256", "").strip().lower()
            actual_sha = sha256_file(wav_path)
            if expected_sha and actual_sha != expected_sha:
                raise SystemExit(
                    f"ERROR: selected WAV SHA mismatch for {uid}: "
                    f"{actual_sha} != {expected_sha}"
                )

            selected[uid] = {
                "speaker": speaker,
                "source_wav": wav_path,
                "wav_sha256": actual_sha,
                "duration_ms": wav_duration_ms(wav_path),
            }

    if set(selected) != set(work_ids):
        missing = sorted(set(work_ids) - set(selected))
        extra = sorted(set(selected) - set(work_ids))
        raise SystemExit(
            "ERROR: selected WAV UID set differs from worklist; "
            f"missing={missing[:10]} extra={extra[:10]}"
        )

    print("PASS: 408/408 selected WAVs exist and hashes match")

    resolved_by_uid = {r["id"]: r for r in resolved}

    final_rows = []
    for uid in work_ids:
        r = dict(resolved_by_uid[uid])
        s = selected[uid]

        r["source_wav"] = str(s["source_wav"].relative_to(PROJECT))
        r["turkish_duration_ms"] = str(s["duration_ms"])
        r["turkish_wav_sha256"] = s["wav_sha256"]
        r["runtime_path"] = f"sc-tr-audio\\{uid}.wav"
        final_rows.append(r)

    fields = [
        "id",
        "speaker",
        "map_name",
        "resource_name",
        "stream_offset",
        "stream_size",
        "old_header_id_hex",
        "editor_id",
        "editor_id_hex",
        "sound_object",
        "mapping_method",
        "source_wav",
        "runtime_path",
        "turkish_duration_ms",
        "turkish_wav_sha256",
        "english_text",
        "turkish_text",
    ]

    with OUT_MANIFEST.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fields,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(final_rows)

    print("PASS: runtime manifest written:", OUT_MANIFEST)

    print()
    print("===== GENERATE V17 SOURCE =====")

    source = V16_SOURCE.read_text(encoding="utf-8")

    table_pattern = re.compile(
        r"static const TrainingOverride g_training_overrides\[\] =\s*"
        r"\{\n.*?\n\};",
        re.S,
    )

    table_lines = []

    for row in sorted(final_rows, key=lambda x: int(x["editor_id"])):
        editor = int(row["editor_id"])
        duration_ms = int(row["turkish_duration_ms"])
        bits = float_bits_seconds(duration_ms)
        uid = row["id"]
        speaker = row["speaker"]

        table_lines.append(
            '    {0x%08Xu, %uu, 0x%08Xu, "sc-tr-audio\\\\%s.wav"}, // %s %s'
            % (editor, duration_ms, bits, uid, uid, speaker)
        )

    table = (
        "static const TrainingOverride g_training_overrides[] =\n"
        "{\n"
        + "\n".join(table_lines)
        + "\n};"
    )

    source, count = table_pattern.subn(lambda _m: table, source, count=1)
    if count != 1:
        raise SystemExit("ERROR: could not replace V16 override table")

    source = source.replace(
        '"snd-waveout-training-v16.log"',
        '"snd-waveout-fisher-lambert-v17.log"',
    )

    OUT_SOURCE.write_text(source, encoding="utf-8")

    check = OUT_SOURCE.read_text(encoding="utf-8")
    if check.count("// u") < 408:
        raise SystemExit("ERROR: generated V17 table row count check failed")

    if '"sc-tr-audio\\\\u000013.wav"' not in check:
        raise SystemExit("ERROR: V17 C++ path escaping check failed")

    print("PASS: V17 source generated:", OUT_SOURCE)
    print("PASS: 408 runtime table entries")

    if not args.stage_audio:
        print()
        print("READY_FOR_RUNTIME: YES")
        print("Audio staging not requested; game files were not changed.")
        print("Run again with --stage-audio after V16 Training playback is verified.")
        return

    print()
    print("===== STAGE 408 WAVS =====")

    TARGET_AUDIO.mkdir(parents=True, exist_ok=True)

    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = PROJECT / "backups" / f"sc-tr-audio-pre-v17-{stamp}"
    backup.mkdir(parents=True)

    backed_up = 0
    copied = 0

    for row in final_rows:
        uid = row["id"]
        src = PROJECT / row["source_wav"]
        dst = TARGET_AUDIO / f"{uid}.wav"

        if dst.exists():
            shutil.copy2(dst, backup / dst.name)
            backed_up += 1

        shutil.copy2(src, dst)

        if sha256_file(dst) != row["turkish_wav_sha256"]:
            raise SystemExit(f"ERROR: staged WAV verification failed: {uid}")

        copied += 1

    print(f"PASS: staged WAVs: {copied}")
    print(f"Existing WAVs backed up: {backed_up}")
    print("Backup:", backup)
    print()
    print("READY_FOR_RUNTIME: YES")
    print("V17 source:", OUT_SOURCE)
    print("V17 manifest:", OUT_MANIFEST)


if __name__ == "__main__":
    main()
