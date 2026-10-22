#!/usr/bin/env python3
from __future__ import annotations

import csv
import importlib.util
import re
import shutil
import subprocess
import time
from pathlib import Path

PROJECT = Path("/run/media/ereng/files/projects/splinter-cell-turkish")
GAME = Path(
    "/run/media/ereng/files/games/tom-clancys-splinter-cell/"
    "drive_c/GOG Games/Splinter Cell"
)
SYSTEM = GAME / "system"

V18_BUILDER = PROJECT / "tools/build-install-snd-waveout-fisher-lambert-v18.py"
V19_SOURCE = PROJECT / "gameplay-subtitle-poc/src/snd_waveout_fisher_lambert_v19.cpp"
V19_MANIFEST = PROJECT / "manifests/fisher-lambert-runtime-v19.csv"
V19_OUT = PROJECT / "build/snd-waveout-fisher-lambert-v19"
TARGET_AUDIO = SYSTEM / "sc-tr-audio"


def load_v18_module():
    spec = importlib.util.spec_from_file_location(
        "sc_v18_builder",
        V18_BUILDER,
    )
    if spec is None or spec.loader is None:
        raise SystemExit("ERROR: could not load V18 builder")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(args):
    print("+", " ".join(map(str, args)))
    subprocess.run(args, check=True)


def write_manifest(rows: list[dict]):
    if not rows:
        raise SystemExit("ERROR: no V19 runtime rows")

    fields = list(rows[0].keys())

    with V19_MANIFEST.open(
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

    print("PASS: V19 runtime manifest written:", V19_MANIFEST)


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise SystemExit(
            f"ERROR: V19 patch {label!r} expected one match, got {count}"
        )
    return source.replace(old, new, 1)


def build_v19_source(v18):
    print()
    print("===== GENERATE V19 SOURCE =====")

    source = v18.OUT_SOURCE.read_text(encoding="utf-8")

    source = replace_once(
        source,
        '"snd-waveout-fisher-lambert-v18.log"',
        '"snd-waveout-fisher-lambert-v19.log"',
        "log filename",
    )

    source = replace_once(
        source,
        """struct ExternalVoiceSlot
{
    DWORD active;
    DWORD editor_id;
    DWORD expected_end;
""",
        """struct ExternalVoiceSlot
{
    DWORD active;
    DWORD editor_id;
    DWORD request_id;
    DWORD expected_end;
""",
        "voice slot request id field",
    )

    source = replace_once(
        source,
        """    slot->active = 0u;
    slot->editor_id = 0u;
    slot->expected_end = 0u;
""",
        """    slot->active = 0u;
    slot->editor_id = 0u;
    slot->request_id = 0xFFFFFFFFu;
    slot->expected_end = 0u;
""",
        "voice slot cleanup request reset",
    )

    source = replace_once(
        source,
        """            g_voice_slots[i].editor_id =
                editor_id;

            return &g_voice_slots[i];
""",
        """            g_voice_slots[i].editor_id =
                editor_id;
            g_voice_slots[i].request_id =
                0xFFFFFFFFu;

            return &g_voice_slots[i];
""",
        "voice slot unbound initialization",
    )

    helper_anchor = """static BOOL
external_voice_start(
"""

    helper_code = r"""static BOOL
external_voice_bind_request(
    DWORD editor_id,
    DWORD request_id)
{
    for (DWORD i = 0u; i < 8u; ++i) {
        ExternalVoiceSlot* slot =
            &g_voice_slots[i];

        if (
            slot->active &&
            slot->editor_id == editor_id &&
            slot->request_id == 0xFFFFFFFFu
        ) {
            slot->request_id = request_id;
            return TRUE;
        }
    }

    return 0;
}

static DWORD
external_voice_stop_request(
    DWORD request_id)
{
    DWORD stopped = 0u;
    DWORD now = GetTickCount();

    for (DWORD i = 0u; i < 8u; ++i) {
        ExternalVoiceSlot* slot =
            &g_voice_slots[i];

        if (
            !slot->active ||
            slot->request_id != request_id
        )
            continue;

        DWORD values[4] = {
            slot->editor_id,
            request_id,
            i,
            now
        };

        write_line(
            "waveout_stop_request",
            values,
            4u);

        external_voice_cleanup_slot(slot);
        ++stopped;
    }

    return stopped;
}

"""

    source = replace_once(
        source,
        helper_anchor,
        helper_code + helper_anchor,
        "external stop helpers",
    )

    bind_anchor = """        } else {
            typedef void (__cdecl *StopOriginal)(DWORD);
"""

    bind_code = """        } else {
            BOOL voice_bound =
                external_voice_bind_request(
                    editor_id,
                    (DWORD)result);

            DWORD bind_values[4] = {
                editor_id,
                (DWORD)result,
                (DWORD)voice_bound,
                now
            };

            write_line(
                voice_bound
                    ? "runtime_voice_bound"
                    : "runtime_voice_bind_failed",
                bind_values,
                4);

            typedef void (__cdecl *StopOriginal)(DWORD);
"""

    source = replace_once(
        source,
        bind_anchor,
        bind_code,
        "request-to-waveout binding",
    )

    stop_anchor = """extern "C"
__declspec(noinline)
BOOL __cdecl probe_is_playing(DWORD request_id)
"""

    stop_wrapper = r"""extern "C"
__declspec(noinline)
void __cdecl probe_stop_sound_request(DWORD request_id)
    __asm__("_probe_stop_sound_request");

extern "C"
__declspec(noinline)
void __cdecl probe_stop_sound_request(DWORD request_id)
{
    RuntimeRequestState* runtime_state =
        runtime_request_by_id(request_id);

    DWORD editor_id = runtime_state
        ? runtime_state->editor_id
        : 0xFFFFFFFFu;

    DWORD stopped =
        external_voice_stop_request(request_id);

    if (runtime_state) {
        DWORD values[4] = {
            editor_id,
            request_id,
            stopped,
            GetTickCount()
        };

        write_line(
            "runtime_stop_request",
            values,
            4);

        runtime_state->active = 0u;
        runtime_state->request_id = 0u;
        runtime_state->editor_id = 0xFFFFFFFFu;
        runtime_state->until = 0u;
        runtime_state->extend_logged = 0u;
    }

    typedef void (__cdecl *Original)(DWORD);

    Original original = (Original)GetProcAddress(
        original_module(),
        "SND_fn_vStopSoundRequest");

    if (original)
        original(request_id);
}

"""

    stop_anchor_count = source.count(stop_anchor)

    if stop_anchor_count != 2:
        raise SystemExit(
            "ERROR: V19 stop wrapper anchor expected declaration + "
            f"definition (2 matches), got {stop_anchor_count}"
        )

    # Insert before the forward declaration only. The second occurrence
    # is the actual probe_is_playing definition and must remain untouched.
    source = source.replace(
        stop_anchor,
        stop_wrapper + stop_anchor,
        1,
    )

    source = source.replace(
        "// V18: the Turkish duration is needed while DareAudio creates",
        "// V19 inherits V18 replay safety: Turkish duration is needed while DareAudio creates",
        1,
    )

    required_tokens = [
        "request_id;",
        "external_voice_bind_request",
        "external_voice_stop_request",
        "runtime_voice_bound",
        "runtime_voice_bind_failed",
        "probe_stop_sound_request",
        "runtime_stop_request",
        "waveout_stop_request",
        '"snd-waveout-fisher-lambert-v19.log"',
    ]

    for token in required_tokens:
        if token not in source:
            raise SystemExit(
                "ERROR: generated V19 source missing token: " + token
            )

    if source.count("// u") < 408:
        raise SystemExit(
            "ERROR: generated V19 source table row count check failed"
        )

    V19_SOURCE.write_text(source, encoding="utf-8")
    print("PASS: V19 stop-aware source generated")
    print("PASS: 408 runtime entries retained")


def patch_def(base_def: Path, out_def: Path):
    text = base_def.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    candidates = []

    for i, line in enumerate(lines):
        stripped = line.strip()

        if not stripped or stripped.startswith(";"):
            continue

        if "stopsoundrequest" in stripped.lower():
            candidates.append((i, line))

    if not candidates:
        print("===== STOP-LIKE DEF EXPORTS =====")

        stop_like = [
            line.strip()
            for line in lines
            if "stop" in line.lower()
        ]

        for line in stop_like[:80]:
            print(line)

        raise SystemExit(
            "ERROR: no StopSoundRequest-like export found in base DEF"
        )

    if len(candidates) != 1:
        print("===== STOP SOUND REQUEST DEF CANDIDATES =====")

        for _, line in candidates:
            print(line.strip())

        raise SystemExit(
            "ERROR: expected exactly one StopSoundRequest-like export, "
            f"got {len(candidates)}"
        )

    target_index, old_line = candidates[0]
    stripped = old_line.strip()
    indent = old_line[: len(old_line) - len(old_line.lstrip())]

    # Keep the exact public export name and ordinal from the existing
    # proxy DEF. Only replace its implementation target with our wrapper.
    # This handles plain, decorated and forwarded/aliased source forms.
    ordinal_match = re.search(r"(\\s+@\\d+\\b.*)$", stripped)
    suffix = ordinal_match.group(1) if ordinal_match else ""

    core = stripped[: ordinal_match.start()] if ordinal_match else stripped

    if "=" in core:
        public_name = core.split("=", 1)[0].strip()
    else:
        public_name = core.split(None, 1)[0].strip()

    if not public_name:
        raise SystemExit(
            "ERROR: could not parse StopSoundRequest public export name"
        )

    lines[target_index] = (
        indent
        + public_name
        + "=_probe_stop_sound_request"
        + suffix
    )

    out_def.write_text("\\n".join(lines) + "\\n", encoding="utf-8")

    check_lines = out_def.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines()

    routed = [
        line.strip()
        for line in check_lines
        if "_probe_stop_sound_request" in line
    ]

    if len(routed) != 1:
        raise SystemExit(
            "ERROR: V19 stop export DEF patch did not produce exactly "
            "one routed export"
        )

    print("PASS: stop-request export routed to V19 wrapper")
    print("DEF before:", old_line.strip())
    print("DEF after :", routed[0])


def compile_and_link(v18):
    print()
    print("===== BUILD V19 =====")

    base_def = v18.BASEOUT / "SNDDSound3DDLL_VBR.def"

    required = [
        V19_SOURCE,
        base_def,
        v18.BASEOUT / "kernel32.lib",
        v18.BASEOUT / "kernel32-time.lib",
        v18.BASEOUT / "winmm.lib",
        SYSTEM / "SNDDSound3DDLL_VBR_orig.dll",
    ]

    for path in required:
        if not path.is_file():
            raise SystemExit(f"ERROR: missing build input: {path}")

    V19_OUT.mkdir(parents=True, exist_ok=True)

    out_def = V19_OUT / "SNDDSound3DDLL_VBR.def"
    patch_def(base_def, out_def)

    obj = V19_OUT / "snd_waveout_fisher_lambert_v19.obj"
    dll = V19_OUT / "SNDDSound3DDLL_VBR.dll"

    for path in [
        obj,
        dll,
        V19_OUT / "SNDDSound3DDLL_VBR.lib",
        V19_OUT / "SNDDSound3DDLL_VBR.exp",
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
        str(V19_SOURCE),
    ])

    print("PASS: compile")

    print()
    print("===== OBJECT CHECK =====")

    nm = subprocess.check_output(
        ["llvm-nm", str(obj)],
        text=True,
    )

    if "_probe_stop_sound_request" not in nm:
        raise SystemExit(
            "ERROR: V19 stop wrapper symbol missing from object"
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
                "ERROR: unexpected CRT dependency: " + forbidden_crt
            )

    print("PASS: V19 stop wrapper object symbol present")
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
        f"/def:{out_def}",
        f"/out:{dll}",
        str(obj),
        str(v18.BASEOUT / "kernel32.lib"),
        str(v18.BASEOUT / "kernel32-time.lib"),
        str(v18.BASEOUT / "winmm.lib"),
    ])

    print("PASS: link")

    print()
    print("===== VERIFY EXPORT ABI =====")

    def exports(path: Path):
        output = subprocess.check_output(
            ["llvm-readobj", "--coff-exports", str(path)],
            text=True,
        )
        result = []

        for block in re.findall(
            r"Export \{(.*?)\n\}",
            output,
            re.S,
        ):
            ordinal = re.search(r"Ordinal: (\d+)", block)
            name = re.search(r"Name: (.+)", block)

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
            f"ERROR: V19 export count is {len(new_exports)}, expected 291"
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
            f"ERROR: V19 export ABI mismatch: {mismatch}"
        )

    print("PASS: 291/291 exports match")
    return dll


def stage_and_install(v18, rows, selected, dll: Path):
    print()
    print("===== BACKUP + STAGE + INSTALL =====")

    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = (
        PROJECT
        / "backups"
        / f"snd-waveout-fisher-lambert-v19-{stamp}"
    )
    backup.mkdir(parents=True)

    live_dll = SYSTEM / "SNDDSound3DDLL_VBR.dll"

    shutil.copy2(
        live_dll,
        backup / "SNDDSound3DDLL_VBR-pre-v19.dll",
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

    for row in rows:
        uid = row["id"]
        src = selected[uid]["source"]
        dst = TARGET_AUDIO / f"{uid}.wav"

        shutil.copy2(src, dst)

        if v18.sha256_file(dst) != selected[uid]["sha256"]:
            raise SystemExit(
                f"ERROR: staged WAV verification failed: {uid}"
            )

    shutil.copy2(dll, live_dll)

    if live_dll.read_bytes() != dll.read_bytes():
        raise SystemExit(
            "ERROR: installed V19 DLL verification failed"
        )

    log = SYSTEM / "snd-waveout-fisher-lambert-v19.log"
    log.write_bytes(b"")

    print("PASS: staged 408 Fisher/Lambert WAVs")
    print(f"Existing WAVs backed up: {overwritten}")
    print("PASS: V19 DLL installed")
    print("Backup:", backup)
    print("Log:", log)


def main():
    print("===== PRECHECK =====")

    if not V18_BUILDER.is_file():
        raise SystemExit(
            f"ERROR: missing V18 builder: {V18_BUILDER}"
        )

    v18 = load_v18_module()

    worklist_path = v18.choose_worklist()

    required = [
        v18.CORPUS,
        v18.AUTH,
        v18.V16_SOURCE,
        v18.FISHER_SELECTED,
        v18.LAMBERT_SELECTED,
        v18.V16_LOG,
    ]

    for path in required:
        if not path.is_file():
            raise SystemExit(
                f"ERROR: missing required file: {path}"
            )

    corpus = v18.load_csv(v18.CORPUS)
    work = v18.load_csv(worklist_path)
    auth = v18.load_csv(v18.AUTH)

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

    tolerance_ulps = v18.verify_v16_duration_preflight(
        corpus_by_id,
        auth_by_id,
    )

    selected = v18.load_selected_wavs(work_ids)

    rows = v18.build_runtime_identity(
        corpus,
        work,
        selected,
        tolerance_ulps,
        auth_by_id,
    )

    write_manifest(rows)

    # Reuse V18's already-validated 408-entry generator as the exact
    # baseline, then add only V19 lifecycle synchronization.
    v18.generate_v18_source(
        rows,
        tolerance_ulps,
    )

    build_v19_source(v18)

    dll = compile_and_link(v18)

    stage_and_install(
        v18,
        rows,
        selected,
        dll,
    )

    print()
    print("===== RESULT =====")
    print("PASS: Fisher 201 + Lambert 207 runtime V19 installed")
    print("Runtime entries: 408")
    print("Baseline: accepted V18 duration/replay/multi-request runtime")
    print("Lifecycle: SND_fn_vStopSoundRequest synchronized to waveOut")
    print("Binding: each external waveOut voice is tied to its SND request")
    print("Scope: request-level early stop only; actor-wide flush remains diagnostic work")


if __name__ == "__main__":
    main()
