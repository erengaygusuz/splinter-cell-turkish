#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import re
import shutil
import struct
import subprocess
import time
import wave
from collections import defaultdict
from pathlib import Path

PROJECT = Path("/run/media/ereng/files/projects/splinter-cell-turkish")
GAME = Path(
    "/run/media/ereng/files/games/tom-clancys-splinter-cell/"
    "drive_c/GOG Games/Splinter Cell"
)
SYSTEM = GAME / "system"

CORPUS = PROJECT / "manifests/corpus.csv"
AUTH = PROJECT / "manifests/runtime-dub-authoritative.csv"
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

V16_LOG = SYSTEM / "snd-waveout-training-v16.log"

OUT_SOURCE = (
    PROJECT
    / "gameplay-subtitle-poc/src/snd_waveout_fisher_lambert_v17.cpp"
)
OUT_MANIFEST = PROJECT / "manifests/fisher-lambert-runtime-v17.csv"

BASEOUT = PROJECT / "build/snd-runtime-manifest-v15-1"
OUT = PROJECT / "build/snd-waveout-fisher-lambert-v17"

TARGET_AUDIO = SYSTEM / "sc-tr-audio"

TRAINING_IDS = [f"u{n:06d}" for n in range(13, 30)]


def run(args):
    print("+", " ".join(map(str, args)))
    subprocess.run(args, check=True)


def load_csv(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def load_tsv(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def choose_worklist() -> Path:
    for path in WORKLIST_CANDIDATES:
        if path.is_file():
            return path
    raise SystemExit(
        "ERROR: Fisher/Lambert worklist not found: "
        + ", ".join(map(str, WORKLIST_CANDIDATES))
    )


def f32_bits(value: float) -> int:
    return struct.unpack("<I", struct.pack("<f", value))[0]


def bits_to_f32(bits: int) -> float:
    return struct.unpack("<f", struct.pack("<I", bits))[0]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def wav_info(path: Path):
    with wave.open(str(path), "rb") as w:
        if w.getcomptype() != "NONE":
            raise SystemExit(f"ERROR: WAV must be PCM: {path}")
        frames = w.getnframes()
        rate = w.getframerate()
        channels = w.getnchannels()
        sample_width = w.getsampwidth()

    if frames <= 0 or rate <= 0:
        raise SystemExit(f"ERROR: invalid WAV frames/rate: {path}")

    seconds = frames / rate
    return {
        "frames": frames,
        "rate": rate,
        "channels": channels,
        "sample_width": sample_width,
        "duration_ms": int(round(seconds * 1000.0)),
        "duration_bits": f32_bits(seconds),
    }


def original_duration_bits(row: dict) -> int:
    sample_count = int(row["sample_count"])
    sample_rate = int(row["sample_rate"])

    if sample_count <= 0 or sample_rate <= 0:
        raise SystemExit(
            f"ERROR: invalid corpus duration data for {row.get('id')}"
        )

    return f32_bits(sample_count / sample_rate)


def verify_v16_duration_preflight(
    corpus_by_id: dict[str, dict],
    auth_by_id: dict[str, dict],
) -> int:
    print("===== V16 ORIGINAL-DURATION PREFLIGHT =====")

    if not V16_LOG.is_file():
        raise SystemExit(f"ERROR: missing V16 log: {V16_LOG}")

    expected_by_editor = {}

    for uid in TRAINING_IDS:
        corpus_row = corpus_by_id.get(uid)
        auth_row = auth_by_id.get(uid)

        if corpus_row is None or auth_row is None:
            raise SystemExit(
                f"ERROR: preflight metadata missing for {uid}"
            )

        editor = int(auth_row["editor_id"], 0)
        expected_by_editor[editor] = (
            uid,
            original_duration_bits(corpus_row),
            int(corpus_row["sample_count"]) / int(corpus_row["sample_rate"]),
        )

    seen = {}
    pattern = re.compile(
        r"^runtime_trigger\s+([0-9A-Fa-f]{8})\s+([0-9A-Fa-f]{8})\s+"
    )

    for line in V16_LOG.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines():
        match = pattern.match(line)
        if not match:
            continue

        editor = int(match.group(1), 16)
        old_bits = int(match.group(2), 16)

        if editor in expected_by_editor:
            seen[editor] = old_bits

    if len(seen) != 17:
        missing = [
            f"{editor:08X}"
            for editor in expected_by_editor
            if editor not in seen
        ]
        raise SystemExit(
            "ERROR: V16 preflight missing runtime_trigger editors: "
            + ", ".join(missing)
        )

    max_ulps = 0
    max_delta_ms = 0.0

    for editor, actual_bits in seen.items():
        uid, expected_bits, expected_seconds = expected_by_editor[editor]
        ulps = abs(actual_bits - expected_bits)
        actual_seconds = bits_to_f32(actual_bits)
        delta_ms = abs(actual_seconds - expected_seconds) * 1000.0

        max_ulps = max(max_ulps, ulps)
        max_delta_ms = max(max_delta_ms, delta_ms)

        print(
            f"{uid} editor={editor:08X} "
            f"expected={expected_bits:08X} actual={actual_bits:08X} "
            f"ulps={ulps} delta_ms={delta_ms:.6f}"
        )

    if max_delta_ms >= 0.05:
        raise SystemExit(
            "ERROR: V16 runtime original-duration delta is >= 0.05 ms; "
            "refusing duration dispatch"
        )

    # DareAudio stores the cached duration with low mantissa bits
    # quantized. Training showed up to 112 ULP while the absolute error
    # stayed below 0.015 ms. Use one conservative integer-only tolerance
    # and revalidate all 408 identities against the full 1093-row corpus
    # before any live game file is changed.
    tolerance_ulps = 128

    if max_ulps > tolerance_ulps:
        raise SystemExit(
            f"ERROR: observed runtime ULP delta exceeds {tolerance_ulps}: "
            f"{max_ulps}"
        )

    print(f"PASS: max runtime duration delta: {max_delta_ms:.6f} ms")
    print(f"PASS: max runtime ULP delta: {max_ulps}")
    print(f"PASS: runtime duration match tolerance: {tolerance_ulps} ULP")
    return tolerance_ulps


def load_selected_wavs(
    work_ids: set[str],
):
    print()
    print("===== VALIDATE 408 SELECTED WAVS =====")

    fisher = load_tsv(FISHER_SELECTED)
    lambert = load_tsv(LAMBERT_SELECTED)

    if len(fisher) != 201:
        raise SystemExit(
            f"ERROR: expected 201 Fisher selected cuts, got {len(fisher)}"
        )

    if len(lambert) != 207:
        raise SystemExit(
            f"ERROR: expected 207 Lambert selected cuts, got {len(lambert)}"
        )

    selected = {}

    for speaker, rows in (
        ("FISHER", fisher),
        ("LAMBERT", lambert),
    ):
        for row in rows:
            uid = row["id"].strip()

            if uid in selected:
                raise SystemExit(
                    f"ERROR: duplicate selected WAV UID: {uid}"
                )

            source = PROJECT / row["wav_path"]

            if not source.is_file():
                raise SystemExit(
                    f"ERROR: selected WAV missing: {source}"
                )

            expected_sha = (row.get("sha256") or "").strip().lower()
            actual_sha = sha256_file(source)

            if expected_sha and actual_sha != expected_sha:
                raise SystemExit(
                    f"ERROR: selected WAV SHA mismatch for {uid}: "
                    f"{actual_sha} != {expected_sha}"
                )

            info = wav_info(source)

            selected[uid] = {
                "speaker": speaker,
                "source": source,
                "sha256": actual_sha,
                **info,
            }

    if set(selected) != work_ids:
        missing = sorted(work_ids - set(selected))
        extra = sorted(set(selected) - work_ids)
        raise SystemExit(
            "ERROR: selected WAV UID set mismatch; "
            f"missing={missing[:12]} extra={extra[:12]}"
        )

    print("PASS: 408/408 final WAVs exist")
    print("PASS: 408/408 final WAV hashes match")
    return selected


def build_runtime_identity(
    corpus: list[dict],
    work: list[dict],
    selected: dict,
    tolerance_ulps: int,
):
    print()
    print("===== BUILD 408 DURATION IDENTITIES =====")

    corpus_by_id = {
        row["id"].strip(): row
        for row in corpus
    }

    target_ids = [
        row["id"].strip()
        for row in work
    ]

    if len(target_ids) != 408 or len(set(target_ids)) != 408:
        raise SystemExit(
            "ERROR: Fisher/Lambert worklist must contain 408 unique UIDs"
        )

    corpus_identity = []

    for row in corpus:
        bits = original_duration_bits(row)
        old_header = int(row["header_id"], 0)

        corpus_identity.append(
            {
                "uid": row["id"].strip(),
                "bits": bits,
                "bank": old_header & 0xFFFF0000,
            }
        )

    target_rows = []

    for row in work:
        uid = row["id"].strip()
        corpus_row = corpus_by_id.get(uid)

        if corpus_row is None:
            raise SystemExit(
                f"ERROR: target UID missing from corpus: {uid}"
            )

        expected_bits = original_duration_bits(corpus_row)
        old_header = int(corpus_row["header_id"], 0)
        old_bank = old_header & 0xFFFF0000

        near_global = [
            item
            for item in corpus_identity
            if abs(item["bits"] - expected_bits) <= tolerance_ulps
        ]

        if len(near_global) == 1:
            required_bank = 0
            identity_mode = "duration_only"
        else:
            near_bank = [
                item
                for item in near_global
                if item["bank"] == old_bank
            ]

            if len(near_bank) != 1 or near_bank[0]["uid"] != uid:
                raise SystemExit(
                    "ERROR: runtime identity is ambiguous for "
                    f"{uid}: global={near_global} bank={near_bank}"
                )

            required_bank = old_bank
            identity_mode = "bank_plus_duration"

        sel = selected[uid]

        target_rows.append(
            {
                "id": uid,
                "speaker": row["speaker"].strip().upper(),
                "map_name": row.get("map_name", ""),
                "resource_name": row.get("resource_name", ""),
                "stream_offset": row.get("stream_offset", ""),
                "old_header_id": f"{old_header:08X}",
                "required_runtime_bank": (
                    f"{required_bank:08X}" if required_bank else ""
                ),
                "identity_mode": identity_mode,
                "original_duration_bits": f"{expected_bits:08X}",
                "tolerance_ulps": str(tolerance_ulps),
                "turkish_duration_ms": str(sel["duration_ms"]),
                "turkish_duration_bits": f"{sel['duration_bits']:08X}",
                "source_wav": str(sel["source"].relative_to(PROJECT)),
                "runtime_path": f"sc-tr-audio\\{uid}.wav",
                "turkish_wav_sha256": sel["sha256"],
            }
        )

    duration_only = sum(
        row["identity_mode"] == "duration_only"
        for row in target_rows
    )
    bank_plus = len(target_rows) - duration_only

    # Full-model safety check: every target identity must select exactly
    # its own corpus UID and no other corpus asset.
    target_by_uid = {
        row["id"]: row
        for row in target_rows
    }

    for uid, target in target_by_uid.items():
        expected_bits = int(target["original_duration_bits"], 16)
        required_bank_text = target["required_runtime_bank"]
        required_bank = (
            int(required_bank_text, 16)
            if required_bank_text
            else 0
        )

        matches = []

        for item in corpus_identity:
            if abs(item["bits"] - expected_bits) > tolerance_ulps:
                continue

            if required_bank and item["bank"] != required_bank:
                continue

            matches.append(item["uid"])

        if matches != [uid]:
            raise SystemExit(
                f"ERROR: modeled runtime identity not unique for {uid}: "
                f"{matches}"
            )

    print(f"PASS: duration-only identities: {duration_only}")
    print(f"PASS: bank+duration identities: {bank_plus}")
    print("PASS: 408/408 identities select exactly one corpus asset")

    return target_rows


def write_manifest(rows: list[dict]):
    fields = [
        "id",
        "speaker",
        "map_name",
        "resource_name",
        "stream_offset",
        "old_header_id",
        "required_runtime_bank",
        "identity_mode",
        "original_duration_bits",
        "tolerance_ulps",
        "turkish_duration_ms",
        "turkish_duration_bits",
        "source_wav",
        "runtime_path",
        "turkish_wav_sha256",
    ]

    with OUT_MANIFEST.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fields,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)

    print("PASS: runtime manifest written:", OUT_MANIFEST)


def generate_v17_source(
    rows: list[dict],
    tolerance_ulps: int,
):
    print()
    print("===== GENERATE V17 SOURCE =====")

    source = V16_SOURCE.read_text(encoding="utf-8")

    source = source.replace(
        '"snd-waveout-training-v16.log"',
        '"snd-waveout-fisher-lambert-v17.log"',
    )

    table_start = source.find("struct TrainingOverride")
    table_end_marker = "\n\nstatic DWORD g_raw_base = 0;"
    table_end = source.find(table_end_marker, table_start)

    if table_start < 0 or table_end < 0:
        raise SystemExit(
            "ERROR: could not locate V16 TrainingOverride block"
        )

    table_lines = []

    for row in rows:
        old_bits = int(row["original_duration_bits"], 16)
        bank_text = row["required_runtime_bank"]
        bank = int(bank_text, 16) if bank_text else 0
        duration_ms = int(row["turkish_duration_ms"])
        duration_bits = int(row["turkish_duration_bits"], 16)
        uid = row["id"]

        table_lines.append(
            '    {0x%08Xu, 0x%08Xu, %uu, 0x%08Xu, '
            '"sc-tr-audio\\\\%s.wav"}, // %s'
            % (
                old_bits,
                bank,
                duration_ms,
                duration_bits,
                uid,
                uid,
            )
        )

    replacement = r'''
struct TrainingOverride
{
    DWORD original_duration_bits;
    DWORD required_bank;
    DWORD duration_ms;
    DWORD duration_bits;
    const char* path;
};

static const TrainingOverride g_training_overrides[] =
{
%s
};

static const DWORD kTrainingOverrideCount =
    sizeof(g_training_overrides) /
    sizeof(g_training_overrides[0]);

static const DWORD kDurationToleranceUlps = %uu;

static const TrainingOverride* g_training_pending = 0;
static LONG g_training_request = -1;
static DWORD g_training_active_editor = 0xFFFFFFFFu;
static DWORD g_training_until = 0u;
static DWORD g_training_extend_logged = 0u;
static DWORD g_training_release_logged = 0u;

static const TrainingOverride*
training_override_by_identity(
    DWORD editor_id,
    DWORD old_duration_bits)
{
    DWORD bank = editor_id & 0xFFFF0000u;

    for (DWORD i = 0; i < kTrainingOverrideCount; ++i) {
        const TrainingOverride* entry =
            &g_training_overrides[i];

        DWORD delta =
            old_duration_bits >= entry->original_duration_bits
            ? old_duration_bits - entry->original_duration_bits
            : entry->original_duration_bits - old_duration_bits;

        if (delta > kDurationToleranceUlps)
            continue;

        if (
            entry->required_bank &&
            entry->required_bank != bank
        )
            continue;

        return entry;
    }

    return 0;
}
''' % (
        "\n".join(table_lines),
        tolerance_ulps,
    )

    source = (
        source[:table_start]
        + replacement
        + source[table_end:]
    )

    old_hook = r'''    const TrainingOverride* training =
        training_override_by_editor(editor_id);

    if (training && sound) {
        DWORD* duration =
            (DWORD*)((char*)sound + 0x2C);

        DWORD old_duration_bits = *duration;

        *duration = training->duration_bits;
'''

    new_hook = r'''    DWORD* duration =
        sound
        ? (DWORD*)((char*)sound + 0x2C)
        : (DWORD*)NULLPTR;

    DWORD old_duration_bits =
        duration
        ? *duration
        : 0u;

    const TrainingOverride* training =
        duration
        ? training_override_by_identity(
            editor_id,
            old_duration_bits)
        : 0;

    if (training && duration) {
        *duration = training->duration_bits;
'''

    if old_hook not in source:
        raise SystemExit(
            "ERROR: V16 dare_play_hook identity block not found"
        )

    source = source.replace(old_hook, new_hook, 1)

    OUT_SOURCE.write_text(source, encoding="utf-8")

    check = OUT_SOURCE.read_text(encoding="utf-8")

    if check.count("// u") < 408:
        raise SystemExit(
            "ERROR: generated V17 source table row count check failed"
        )

    if "training_override_by_editor" in check:
        raise SystemExit(
            "ERROR: old editor-ID matcher remains in V17 source"
        )

    if "training_override_by_identity" not in check:
        raise SystemExit(
            "ERROR: V17 duration identity matcher missing"
        )

    if '"snd-waveout-fisher-lambert-v17.log"' not in check:
        raise SystemExit(
            "ERROR: V17 log filename missing"
        )

    print("PASS: V17 duration-dispatch source generated")
    print("PASS: 408 runtime entries")


def compile_and_link():
    print()
    print("===== BUILD V17 =====")

    required = [
        OUT_SOURCE,
        BASEOUT / "SNDDSound3DDLL_VBR.def",
        BASEOUT / "kernel32.lib",
        BASEOUT / "kernel32-time.lib",
        BASEOUT / "winmm.lib",
        SYSTEM / "SNDDSound3DDLL_VBR_orig.dll",
    ]

    for path in required:
        if not path.is_file():
            raise SystemExit(
                f"ERROR: missing build input: {path}"
            )

    OUT.mkdir(parents=True, exist_ok=True)

    shutil.copy2(
        BASEOUT / "SNDDSound3DDLL_VBR.def",
        OUT / "SNDDSound3DDLL_VBR.def",
    )

    obj = OUT / "snd_waveout_fisher_lambert_v17.obj"
    dll = OUT / "SNDDSound3DDLL_VBR.dll"

    for path in [
        obj,
        dll,
        OUT / "SNDDSound3DDLL_VBR.lib",
        OUT / "SNDDSound3DDLL_VBR.exp",
    ]:
        try:
            path.unlink()
        except FileNotFoundError:
            pass

    print()
    print("===== COMPILE =====")

    run([
        "clang-cl",
        "--target=i686-pc-windows-msvc",
        "/nologo",
        "/c",
        "/O2",
        "/GS-",
        "/GR-",
        "/EHs-c-",
        "/Zl",
        "/utf-8",
        f"/Fo{obj}",
        str(OUT_SOURCE),
    ])

    print("PASS: compile")

    print()
    print("===== OBJECT CHECK =====")

    nm = subprocess.check_output(
        ["llvm-nm", str(obj)],
        text=True,
    )

    undefined_symbols = {
        parts[-1]
        for line in nm.splitlines()
        if (parts := line.split())
        and "U" in parts[:-1]
    }

    for forbidden_crt in {
        "__fltused",
        "_memcpy",
        "_memset",
        "_memmove",
        "_malloc",
        "_free",
    }:
        if forbidden_crt in undefined_symbols:
            raise SystemExit(
                "ERROR: unexpected CRT dependency: "
                + forbidden_crt
            )

    print("PASS: no forbidden CRT dependency")

    print()
    print("===== LINK =====")

    run([
        "lld-link",
        "/dll",
        "/nodefaultlib",
        "/machine:x86",
        "/subsystem:windows,5.1",
        "/entry:DllMain@12",
        f"/def:{OUT / 'SNDDSound3DDLL_VBR.def'}",
        f"/out:{dll}",
        str(obj),
        str(BASEOUT / "kernel32.lib"),
        str(BASEOUT / "kernel32-time.lib"),
        str(BASEOUT / "winmm.lib"),
    ])

    print("PASS: link")

    print()
    print("===== VERIFY EXPORT ABI =====")

    def exports(path: Path):
        text = subprocess.check_output(
            ["llvm-readobj", "--coff-exports", str(path)],
            text=True,
        )
        result = []
        for block in re.findall(
            r"Export \{(.*?)\n\}",
            text,
            re.S,
        ):
            ordinal = re.search(
                r"Ordinal: (\d+)",
                block,
            )
            name = re.search(
                r"Name: (.+)",
                block,
            )
            if ordinal and name:
                result.append(
                    (
                        int(ordinal.group(1)),
                        name.group(1).strip(),
                    )
                )
        return result

    original_exports = exports(
        SYSTEM / "SNDDSound3DDLL_VBR_orig.dll"
    )
    new_exports = exports(dll)

    if len(original_exports) != 291:
        raise SystemExit(
            "ERROR: original export parser did not return 291 exports"
        )

    if len(new_exports) != 291:
        raise SystemExit(
            f"ERROR: V17 export count is {len(new_exports)}, expected 291"
        )

    if new_exports != original_exports:
        mismatch = next(
            (
                (i, a, b)
                for i, (a, b)
                in enumerate(
                    zip(original_exports, new_exports),
                    start=1,
                )
                if a != b
            ),
            None,
        )
        raise SystemExit(
            f"ERROR: export ABI mismatch: {mismatch}"
        )

    print("PASS: 291/291 exports match")

    return dll


def stage_and_install(
    rows: list[dict],
    selected: dict,
    dll: Path,
):
    print()
    print("===== BACKUP + STAGE + INSTALL =====")

    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = (
        PROJECT
        / "backups"
        / f"snd-waveout-fisher-lambert-v17-{stamp}"
    )
    backup.mkdir(parents=True)

    live_dll = SYSTEM / "SNDDSound3DDLL_VBR.dll"

    shutil.copy2(
        live_dll,
        backup / "SNDDSound3DDLL_VBR-pre-v17.dll",
    )

    audio_backup = backup / "sc-tr-audio-overwritten"
    audio_backup.mkdir()

    TARGET_AUDIO.mkdir(parents=True, exist_ok=True)

    overwritten = 0

    for row in rows:
        uid = row["id"]
        src = selected[uid]["source"]
        dst = TARGET_AUDIO / f"{uid}.wav"

        if dst.exists():
            shutil.copy2(
                dst,
                audio_backup / dst.name,
            )
            overwritten += 1

    # Only mutate the live game after every mapping/build/ABI check above passed.
    for row in rows:
        uid = row["id"]
        src = selected[uid]["source"]
        dst = TARGET_AUDIO / f"{uid}.wav"

        shutil.copy2(src, dst)

        if sha256_file(dst) != selected[uid]["sha256"]:
            raise SystemExit(
                f"ERROR: staged WAV verification failed: {uid}"
            )

    shutil.copy2(dll, live_dll)

    if live_dll.read_bytes() != dll.read_bytes():
        raise SystemExit(
            "ERROR: installed V17 DLL verification failed"
        )

    log = SYSTEM / "snd-waveout-fisher-lambert-v17.log"
    log.write_bytes(b"")

    print("PASS: staged 408 Fisher/Lambert WAVs")
    print(f"Existing WAVs backed up: {overwritten}")
    print("PASS: V17 DLL installed")
    print("Backup:", backup)
    print("Log:", log)


def main():
    print("===== PRECHECK =====")

    worklist_path = choose_worklist()

    required = [
        CORPUS,
        AUTH,
        V16_SOURCE,
        FISHER_SELECTED,
        LAMBERT_SELECTED,
        V16_LOG,
    ]

    for path in required:
        if not path.is_file():
            raise SystemExit(
                f"ERROR: missing required file: {path}"
            )

    corpus = load_csv(CORPUS)
    work = load_csv(worklist_path)
    auth = load_csv(AUTH)

    if len(corpus) != 1093:
        raise SystemExit(
            f"ERROR: expected 1093 corpus rows, got {len(corpus)}"
        )

    if len(work) != 408:
        raise SystemExit(
            f"ERROR: expected 408 Fisher/Lambert rows, got {len(work)}"
        )

    work_ids = {
        row["id"].strip()
        for row in work
    }

    if len(work_ids) != 408:
        raise SystemExit(
            "ERROR: Fisher/Lambert worklist UID set is not unique"
        )

    corpus_by_id = {
        row["id"].strip(): row
        for row in corpus
    }

    auth_by_id = {
        row["id"].strip(): row
        for row in auth
        if (row.get("id") or "").strip()
    }

    print("PASS: corpus rows 1093")
    print("PASS: Fisher/Lambert rows 408")

    tolerance_ulps = verify_v16_duration_preflight(
        corpus_by_id,
        auth_by_id,
    )

    selected = load_selected_wavs(work_ids)

    rows = build_runtime_identity(
        corpus,
        work,
        selected,
        tolerance_ulps,
    )

    write_manifest(rows)

    generate_v17_source(
        rows,
        tolerance_ulps,
    )

    dll = compile_and_link()

    stage_and_install(
        rows,
        selected,
        dll,
    )

    print()
    print("===== RESULT =====")
    print("PASS: Fisher 201 + Lambert 207 runtime V17 installed")
    print("Runtime entries: 408")
    print("Dispatch: original USound duration; bank only on collisions")


if __name__ == "__main__":
    main()
