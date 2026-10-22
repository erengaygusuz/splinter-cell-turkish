#!/usr/bin/env python3
from __future__ import annotations

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

V19_BUILDER = PROJECT / "tools/build-install-snd-waveout-fisher-lambert-v19.py"
V19_SOURCE = PROJECT / "gameplay-subtitle-poc/src/snd_waveout_fisher_lambert_v19.cpp"
V19_DLL = PROJECT / "build/snd-waveout-fisher-lambert-v19/SNDDSound3DDLL_VBR.dll"

V20_SOURCE = PROJECT / "gameplay-subtitle-poc/src/snd_waveout_fisher_lambert_v20.cpp"
V20_OUT = PROJECT / "build/snd-waveout-fisher-lambert-v20"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)

    if spec is None or spec.loader is None:
        raise SystemExit(f"ERROR: could not load module: {path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(args):
    print("+", " ".join(map(str, args)))
    subprocess.run(args, check=True)


def ensure_game_closed():
    result = subprocess.run(
        ["pgrep", "-fi", r"[S]plinterCell\.exe"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )

    if result.returncode == 0 and result.stdout.strip():
        raise SystemExit(
            "ERROR: Splinter Cell is running; close the game before install"
        )


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)

    if count != 1:
        raise SystemExit(
            f"ERROR: V20 patch {label!r} expected one match, got {count}"
        )

    return source.replace(old, new, 1)


def generate_v20_source():
    print()
    print("===== GENERATE V20 SOURCE =====")

    source = V19_SOURCE.read_text(encoding="utf-8")

    source = replace_once(
        source,
        '"snd-waveout-fisher-lambert-v19.log"',
        '"snd-waveout-fisher-lambert-v20.log"',
        "log filename",
    )

    stop_request_end = r'''static DWORD
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
'''

    stop_all_helper = stop_request_end + r'''

static DWORD
external_voice_stop_all(DWORD reason)
{
    DWORD stopped = 0u;
    DWORD now = GetTickCount();

    for (DWORD i = 0u; i < 8u; ++i) {
        ExternalVoiceSlot* slot =
            &g_voice_slots[i];

        if (!slot->active)
            continue;

        DWORD values[5] = {
            slot->editor_id,
            slot->request_id,
            i,
            reason,
            now
        };

        write_line(
            "waveout_stop_all",
            values,
            5u);

        external_voice_cleanup_slot(slot);
        ++stopped;
    }

    return stopped;
}
'''

    source = replace_once(
        source,
        stop_request_end,
        stop_all_helper,
        "external stop-all helper",
    )

    request_acquire_end = r'''    return free_slot;
}
'''

    request_clear_helper = request_acquire_end + r'''

static DWORD
runtime_request_clear_all()
{
    DWORD cleared = 0u;

    for (DWORD i = 0u; i < 32u; ++i) {
        RuntimeRequestState* state =
            &g_runtime_requests[i];

        if (!state->active)
            continue;

        state->active = 0u;
        state->request_id = 0u;
        state->editor_id = 0xFFFFFFFFu;
        state->until = 0u;
        state->extend_logged = 0u;
        ++cleared;
    }

    return cleared;
}
'''

    source = replace_once(
        source,
        request_acquire_end,
        request_clear_helper,
        "logical request clear-all helper",
    )

    wrapper_anchor = r'''extern "C"
__declspec(noinline)
void __cdecl probe_stop_sound_request(DWORD request_id)
'''

    global_wrappers = r'''extern "C"
__declspec(noinline)
void __cdecl probe_kill_all_sound_object_types()
    __asm__("_probe_kill_all_sound_object_types");

extern "C"
__declspec(noinline)
void __cdecl probe_kill_all_sound_object_types()
{
    DWORD stopped =
        external_voice_stop_all(169u);

    DWORD cleared =
        runtime_request_clear_all();

    DWORD values[3] = {
        stopped,
        cleared,
        GetTickCount()
    };

    write_line(
        "runtime_global_stop_types",
        values,
        3u);

    typedef void (__cdecl *Original)();

    Original original = (Original)GetProcAddress(
        original_module(),
        "SND_fn_vKillAllSoundObjectTypes");

    if (original)
        original();
}

extern "C"
__declspec(noinline)
void __cdecl probe_kill_all_sound_objects()
    __asm__("_probe_kill_all_sound_objects");

extern "C"
__declspec(noinline)
void __cdecl probe_kill_all_sound_objects()
{
    DWORD stopped =
        external_voice_stop_all(173u);

    DWORD cleared =
        runtime_request_clear_all();

    DWORD values[3] = {
        stopped,
        cleared,
        GetTickCount()
    };

    write_line(
        "runtime_global_stop_objects",
        values,
        3u);

    typedef void (__cdecl *Original)();

    Original original = (Original)GetProcAddress(
        original_module(),
        "SND_fn_vKillAllSoundObjects");

    if (original)
        original();
}

'''

    source = replace_once(
        source,
        wrapper_anchor,
        global_wrappers + wrapper_anchor,
        "global kill wrappers",
    )

    required_tokens = [
        "external_voice_stop_all",
        "runtime_request_clear_all",
        "probe_kill_all_sound_object_types",
        "probe_kill_all_sound_objects",
        "runtime_global_stop_types",
        "runtime_global_stop_objects",
        "waveout_stop_all",
        '"snd-waveout-fisher-lambert-v20.log"',
    ]

    for token in required_tokens:
        if token not in source:
            raise SystemExit(
                "ERROR: generated V20 source missing token: " + token
            )

    if source.count("// u") < 408:
        raise SystemExit(
            "ERROR: generated V20 source lost 408 runtime table"
        )

    V20_SOURCE.write_text(source, encoding="utf-8")

    print("PASS: V20 global lifecycle source generated")
    print("PASS: V19 request-level stop retained")
    print("PASS: 408 runtime entries retained")


def patch_def(base_def: Path, out_def: Path):
    print()
    print("===== BUILD V20 DEF =====")

    lines = base_def.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines()

    routes = {
        "SND_fn_vKillAllSoundObjectTypes": (
            169,
            "probe_kill_all_sound_object_types",
        ),
        "SND_fn_vKillAllSoundObjects": (
            173,
            "probe_kill_all_sound_objects",
        ),
        "SND_fn_vStopSoundRequest": (
            247,
            "probe_stop_sound_request",
        ),
    }

    found = {}

    for i, line in enumerate(lines):
        stripped = line.strip()

        if not stripped or stripped.startswith(";"):
            continue

        lhs = stripped.split("=", 1)[0].strip()
        public_name = lhs.strip('"')

        if public_name not in routes:
            continue

        expected_ordinal, target = routes[public_name]

        ordinal_match = re.search(r"(\s+@(\d+)\b.*)$", stripped)

        if not ordinal_match:
            raise SystemExit(
                f"ERROR: {public_name} export has no ordinal"
            )

        actual_ordinal = int(ordinal_match.group(2))

        if actual_ordinal != expected_ordinal:
            raise SystemExit(
                f"ERROR: {public_name} expected ordinal "
                f"{expected_ordinal}, got {actual_ordinal}"
            )

        if public_name in found:
            raise SystemExit(
                f"ERROR: duplicate V20 export route: {public_name}"
            )

        suffix = ordinal_match.group(1)
        indent = line[: len(line) - len(line.lstrip())]

        found[public_name] = stripped
        lines[i] = (
            indent
            + lhs
            + "="
            + target
            + suffix
        )

    if set(found) != set(routes):
        missing = sorted(set(routes) - set(found))
        raise SystemExit(
            "ERROR: V20 DEF missing exact exports: "
            + ", ".join(missing)
        )

    out_def.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    check_lines = [
        line.strip()
        for line in out_def.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines()
    ]

    export_lines = []

    for line in check_lines:
        parts = line.rsplit(None, 1)

        if (
            len(parts) == 2
            and parts[1].startswith("@")
            and parts[1][1:].isdigit()
        ):
            export_lines.append(line)

    if len(export_lines) != 291:
        raise SystemExit(
            f"ERROR: V20 DEF expected 291 export lines, "
            f"got {len(export_lines)}"
        )

    expected_routes = {
        '"SND_fn_vKillAllSoundObjectTypes"='
        'probe_kill_all_sound_object_types @169',
        '"SND_fn_vKillAllSoundObjects"='
        'probe_kill_all_sound_objects @173',
        '"SND_fn_vStopSoundRequest"='
        'probe_stop_sound_request @247',
    }

    actual_routes = {
        line
        for line in export_lines
        if (
            "probe_kill_all_sound_object_types" in line
            or "probe_kill_all_sound_objects" in line
            or "probe_stop_sound_request" in line
        )
    }

    if actual_routes != expected_routes:
        raise SystemExit(
            "ERROR: V20 DEF route mismatch: "
            + repr(sorted(actual_routes))
        )

    untouched = {
        '"SND_fn_vKillAllSoundObjectTypesButOne"='
        '"SNDDSound3DDLL_VBR_orig.#170" @170',
        '"SND_fn_vKillAllSoundObjectTypesButOneWithFade"='
        '"SNDDSound3DDLL_VBR_orig.#171" @171',
        '"SND_fn_vKillAllSoundObjectTypesWithFade"='
        '"SNDDSound3DDLL_VBR_orig.#172" @172',
        '"SND_fn_vKillAllSoundObjectsWithFade"='
        '"SNDDSound3DDLL_VBR_orig.#174" @174',
        '"SND_fn_vStopSoundRequestWithFade"='
        '"SNDDSound3DDLL_VBR_orig.#248" @248',
    }

    missing_untouched = sorted(
        line
        for line in untouched
        if line not in export_lines
    )

    if missing_untouched:
        raise SystemExit(
            "ERROR: V20 unexpectedly changed neighboring lifecycle "
            "exports: " + repr(missing_untouched)
        )

    print("PASS: V20 DEF has 291 separate export lines")
    print("PASS: KillAllSoundObjectTypes routed at ordinal 169")
    print("PASS: KillAllSoundObjects routed at ordinal 173")
    print("PASS: StopSoundRequest retained at ordinal 247")
    print("PASS: fade/but-one neighbors remain original")


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


def compile_and_link(v19):
    print()
    print("===== BUILD V20 =====")

    V20_OUT.mkdir(parents=True, exist_ok=True)

    base_def = v19.BASEOUT / "SNDDSound3DDLL_VBR.def"
    out_def = V20_OUT / "SNDDSound3DDLL_VBR.def"
    obj = V20_OUT / "snd_waveout_fisher_lambert_v20.obj"
    dll = V20_OUT / "SNDDSound3DDLL_VBR.dll"

    required = [
        V20_SOURCE,
        base_def,
        v19.BASEOUT / "kernel32.lib",
        v19.BASEOUT / "kernel32-time.lib",
        v19.BASEOUT / "winmm.lib",
        SYSTEM / "SNDDSound3DDLL_VBR_orig.dll",
    ]

    for path in required:
        if not path.is_file():
            raise SystemExit(
                f"ERROR: missing V20 build input: {path}"
            )

    patch_def(base_def, out_def)

    for path in [
        obj,
        dll,
        V20_OUT / "SNDDSound3DDLL_VBR.lib",
        V20_OUT / "SNDDSound3DDLL_VBR.exp",
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
        str(V20_SOURCE),
    ])

    print("PASS: compile")

    print()
    print("===== OBJECT CHECK =====")

    nm = subprocess.check_output(
        ["llvm-nm", str(obj)],
        text=True,
    )

    for symbol in [
        "_probe_stop_sound_request",
        "_probe_kill_all_sound_object_types",
        "_probe_kill_all_sound_objects",
    ]:
        rows = [
            parts
            for line in nm.splitlines()
            if (parts := line.split())
            and parts[-1] == symbol
        ]

        if len(rows) != 1 or "U" in rows[0][:-1]:
            raise SystemExit(
                f"ERROR: V20 object does not define {symbol} exactly once"
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

    print("PASS: all three lifecycle wrapper symbols defined")
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
        str(v19.BASEOUT / "kernel32.lib"),
        str(v19.BASEOUT / "kernel32-time.lib"),
        str(v19.BASEOUT / "winmm.lib"),
    ])

    print("PASS: link")

    print()
    print("===== VERIFY EXPORT ABI =====")

    original_exports = exports(
        SYSTEM / "SNDDSound3DDLL_VBR_orig.dll"
    )
    v20_exports = exports(dll)

    if len(original_exports) != 291:
        raise SystemExit(
            f"ERROR: original export count is "
            f"{len(original_exports)}, expected 291"
        )

    if len(v20_exports) != 291:
        raise SystemExit(
            f"ERROR: V20 export count is "
            f"{len(v20_exports)}, expected 291"
        )

    if v20_exports != original_exports:
        mismatch = next(
            (
                (index, expected, actual)
                for index, (expected, actual)
                in enumerate(
                    zip(original_exports, v20_exports),
                    start=1,
                )
                if expected != actual
            ),
            None,
        )

        raise SystemExit(
            f"ERROR: V20 export ABI mismatch: {mismatch}"
        )

    print("PASS: 291/291 exports match")
    return dll


def install_v20(dll: Path):
    print()
    print("===== INSTALL V20 DLL ONLY =====")

    live = SYSTEM / "SNDDSound3DDLL_VBR.dll"

    if live.read_bytes() != V19_DLL.read_bytes():
        raise SystemExit(
            "ERROR: live DLL is not exact accepted V19; "
            "refusing V20 install"
        )

    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = (
        PROJECT
        / "backups"
        / f"snd-waveout-fisher-lambert-v20-{stamp}"
    )
    backup.mkdir(parents=True)

    shutil.copy2(
        live,
        backup / "SNDDSound3DDLL_VBR-pre-v20.dll",
    )

    shutil.copy2(dll, live)

    if live.read_bytes() != dll.read_bytes():
        raise SystemExit(
            "ERROR: installed V20 DLL verification failed"
        )

    log = SYSTEM / "snd-waveout-fisher-lambert-v20.log"
    log.write_bytes(b"")

    print("PASS: live DLL was exact accepted V19")
    print("PASS: V20 DLL installed")
    print("PASS: 408 audio files left untouched")
    print("Backup:", backup)
    print("Log:", log)


def main():
    print("===== V20 PRECHECK =====")

    ensure_game_closed()

    required = [
        V19_BUILDER,
        V19_SOURCE,
        V19_DLL,
        SYSTEM / "SNDDSound3DDLL_VBR.dll",
    ]

    for path in required:
        if not path.is_file():
            raise SystemExit(
                f"ERROR: missing V20 prerequisite: {path}"
            )

    live = SYSTEM / "SNDDSound3DDLL_VBR.dll"

    if live.read_bytes() != V19_DLL.read_bytes():
        raise SystemExit(
            "ERROR: live DLL is not exact accepted V19"
        )

    v19_source_text = V19_SOURCE.read_text(encoding="utf-8")

    for token in [
        '"snd-waveout-fisher-lambert-v19.log"',
        "probe_stop_sound_request",
        "runtime_voice_bound",
        "external_voice_stop_request",
    ]:
        if token not in v19_source_text:
            raise SystemExit(
                "ERROR: V19 source prerequisite missing: " + token
            )

    print("PASS: game is closed")
    print("PASS: live DLL is exact accepted V19")
    print("PASS: V19 generated source is present")

    v19 = load_module(
        V19_BUILDER,
        "sc_v19_builder_for_v20",
    )

    generate_v20_source()

    dll = compile_and_link(v19)

    install_v20(dll)

    print()
    print("===== RESULT =====")
    print("PASS: Fisher/Lambert runtime V20 installed")
    print("Request stop: ordinal 247 synchronized")
    print("Global kill types: ordinal 169 synchronized")
    print("Global kill objects: ordinal 173 synchronized")
    print("Scope: 408 Fisher/Lambert external voices")
    print("Audio payload: unchanged from accepted V18/V19")


if __name__ == "__main__":
    main()
