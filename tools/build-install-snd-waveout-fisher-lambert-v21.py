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

V20_BUILDER = PROJECT / "tools/build-install-snd-waveout-fisher-lambert-v20.py"
V20_SOURCE = PROJECT / "gameplay-subtitle-poc/src/snd_waveout_fisher_lambert_v20.cpp"
V20_DLL = PROJECT / "build/snd-waveout-fisher-lambert-v20/SNDDSound3DDLL_VBR.dll"

V21_SOURCE = PROJECT / "gameplay-subtitle-poc/src/snd_waveout_fisher_lambert_v21.cpp"
V21_OUT = PROJECT / "build/snd-waveout-fisher-lambert-v21"


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
            f"ERROR: V21 patch {label!r} expected one match, got {count}"
        )

    return source.replace(old, new, 1)


def generate_v21_source():
    print()
    print("===== GENERATE V21 SOURCE =====")

    source = V20_SOURCE.read_text(encoding="utf-8")

    source = replace_once(
        source,
        '"snd-waveout-fisher-lambert-v20.log"',
        '"snd-waveout-fisher-lambert-v21.log"',
        "log filename",
    )

    source = replace_once(
        source,
        r'''typedef MMRESULT (WINAPI *WaveOutResetFn)(
    HWAVEOUT);
typedef MMRESULT (WINAPI *WaveOutUnprepareHeaderFn)(
''',
        r'''typedef MMRESULT (WINAPI *WaveOutResetFn)(
    HWAVEOUT);
typedef MMRESULT (WINAPI *WaveOutPauseFn)(
    HWAVEOUT);
typedef MMRESULT (WINAPI *WaveOutRestartFn)(
    HWAVEOUT);
typedef MMRESULT (WINAPI *WaveOutUnprepareHeaderFn)(
''',
        "waveOut pause/restart typedefs",
    )

    source = replace_once(
        source,
        r'''static WaveOutWriteFn g_wave_out_write = 0;
static WaveOutResetFn g_wave_out_reset = 0;
static WaveOutUnprepareHeaderFn g_wave_out_unprepare_header = 0;
''',
        r'''static WaveOutWriteFn g_wave_out_write = 0;
static WaveOutResetFn g_wave_out_reset = 0;
static WaveOutPauseFn g_wave_out_pause = 0;
static WaveOutRestartFn g_wave_out_restart = 0;
static WaveOutUnprepareHeaderFn g_wave_out_unprepare_header = 0;
''',
        "waveOut pause/restart globals",
    )

    source = replace_once(
        source,
        r'''    if (
        g_get_file_size &&
        g_read_file &&
        g_virtual_alloc &&
        g_virtual_free &&
        g_wave_out_open &&
        g_wave_out_prepare_header &&
        g_wave_out_write &&
        g_wave_out_reset &&
        g_wave_out_unprepare_header &&
        g_wave_out_close
    )
''',
        r'''    if (
        g_get_file_size &&
        g_read_file &&
        g_virtual_alloc &&
        g_virtual_free &&
        g_wave_out_open &&
        g_wave_out_prepare_header &&
        g_wave_out_write &&
        g_wave_out_reset &&
        g_wave_out_pause &&
        g_wave_out_restart &&
        g_wave_out_unprepare_header &&
        g_wave_out_close
    )
''',
        "waveOut resolver fast path",
    )

    source = replace_once(
        source,
        r'''    g_wave_out_reset =
        (WaveOutResetFn)GetProcAddress(
            winmm, "waveOutReset");

    g_wave_out_unprepare_header =
''',
        r'''    g_wave_out_reset =
        (WaveOutResetFn)GetProcAddress(
            winmm, "waveOutReset");

    g_wave_out_pause =
        (WaveOutPauseFn)GetProcAddress(
            winmm, "waveOutPause");

    g_wave_out_restart =
        (WaveOutRestartFn)GetProcAddress(
            winmm, "waveOutRestart");

    g_wave_out_unprepare_header =
''',
        "waveOut pause/restart resolver",
    )

    source = replace_once(
        source,
        r'''    return
        g_get_file_size &&
        g_read_file &&
        g_virtual_alloc &&
        g_virtual_free &&
        g_wave_out_open &&
        g_wave_out_prepare_header &&
        g_wave_out_write &&
        g_wave_out_reset &&
        g_wave_out_unprepare_header &&
        g_wave_out_close;
''',
        r'''    return
        g_get_file_size &&
        g_read_file &&
        g_virtual_alloc &&
        g_virtual_free &&
        g_wave_out_open &&
        g_wave_out_prepare_header &&
        g_wave_out_write &&
        g_wave_out_reset &&
        g_wave_out_pause &&
        g_wave_out_restart &&
        g_wave_out_unprepare_header &&
        g_wave_out_close;
''',
        "waveOut resolver final result",
    )

    source = replace_once(
        source,
        r'''    DWORD active;
    DWORD editor_id;
    DWORD request_id;
    DWORD expected_end;
''',
        r'''    DWORD active;
    DWORD editor_id;
    DWORD request_id;
    DWORD paused;
    DWORD pause_started;
    DWORD expected_end;
''',
        "external voice pause state",
    )

    source = replace_once(
        source,
        r'''    slot->request_id = 0xFFFFFFFFu;
    slot->expected_end = 0u;
''',
        r'''    slot->request_id = 0xFFFFFFFFu;
    slot->paused = 0u;
    slot->pause_started = 0u;
    slot->expected_end = 0u;
''',
        "external voice cleanup pause state",
    )

    source = replace_once(
        source,
        r'''            slot->active &&
            (LONG)(now - slot->expected_end) >= 0
''',
        r'''            slot->active &&
            !slot->paused &&
            (LONG)(now - slot->expected_end) >= 0
''',
        "skip paused voice collection",
    )

    source = replace_once(
        source,
        r'''    slot->active = 1u;
    slot->wave = wave;
    slot->file_memory = memory;
    slot->expected_end =
''',
        r'''    slot->active = 1u;
    slot->wave = wave;
    slot->file_memory = memory;
    slot->paused = 0u;
    slot->pause_started = 0u;
    slot->expected_end =
''',
        "external voice start pause state",
    )

    stop_all_end = r'''static DWORD
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

    pause_helpers = stop_all_end + r'''

static DWORD
external_voice_pause_all(DWORD reason)
{
    DWORD paused = 0u;
    DWORD now = GetTickCount();

    for (DWORD i = 0u; i < 8u; ++i) {
        ExternalVoiceSlot* slot =
            &g_voice_slots[i];

        if (
            !slot->active ||
            slot->paused ||
            !slot->wave
        )
            continue;

        MMRESULT result =
            g_wave_out_pause
            ? g_wave_out_pause(slot->wave)
            : 1u;

        DWORD values[6] = {
            slot->editor_id,
            slot->request_id,
            i,
            reason,
            (DWORD)result,
            now
        };

        write_line(
            "waveout_pause",
            values,
            6u);

        if (result == 0u) {
            slot->paused = 1u;
            slot->pause_started = now;
            ++paused;
        }
    }

    return paused;
}

static DWORD
external_voice_resume_all(DWORD reason)
{
    DWORD resumed = 0u;
    DWORD now = GetTickCount();

    for (DWORD i = 0u; i < 8u; ++i) {
        ExternalVoiceSlot* slot =
            &g_voice_slots[i];

        if (
            !slot->active ||
            !slot->paused ||
            !slot->wave
        )
            continue;

        DWORD paused_ms =
            now - slot->pause_started;

        MMRESULT result =
            g_wave_out_restart
            ? g_wave_out_restart(slot->wave)
            : 1u;

        DWORD values[7] = {
            slot->editor_id,
            slot->request_id,
            i,
            reason,
            (DWORD)result,
            paused_ms,
            now
        };

        write_line(
            "waveout_resume",
            values,
            7u);

        if (result == 0u) {
            slot->expected_end += paused_ms;
            slot->paused = 0u;
            slot->pause_started = 0u;
            ++resumed;
        }
    }

    return resumed;
}
'''

    source = replace_once(
        source,
        stop_all_end,
        pause_helpers,
        "external pause/resume helpers",
    )

    source = replace_once(
        source,
        r'''static RuntimeRequestState g_runtime_requests[32];
''',
        r'''static RuntimeRequestState g_runtime_requests[32];
static DWORD g_runtime_pause_active = 0u;
static DWORD g_runtime_pause_started = 0u;
''',
        "runtime pause globals",
    )

    clear_all_end = r'''    return cleared;
}
'''

    # V20 has exactly one runtime_request_clear_all return before the
    # lifecycle wrappers. Anchor on the full tail so we do not touch
    # unrelated helpers that also return a variable named cleared.
    clear_all_full = r'''static DWORD
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

    runtime_pause_helpers = r'''static DWORD
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

    g_runtime_pause_active = 0u;
    g_runtime_pause_started = 0u;

    return cleared;
}

static DWORD
runtime_request_pause_all()
{
    DWORD active = 0u;

    for (DWORD i = 0u; i < 32u; ++i) {
        if (g_runtime_requests[i].active)
            ++active;
    }

    if (
        active &&
        !g_runtime_pause_active
    ) {
        g_runtime_pause_active = 1u;
        g_runtime_pause_started = GetTickCount();
    }

    return active;
}

static DWORD
runtime_request_resume_all()
{
    if (!g_runtime_pause_active)
        return 0u;

    DWORD now = GetTickCount();
    DWORD paused_ms =
        now - g_runtime_pause_started;
    DWORD resumed = 0u;

    for (DWORD i = 0u; i < 32u; ++i) {
        RuntimeRequestState* state =
            &g_runtime_requests[i];

        if (!state->active)
            continue;

        state->until += paused_ms;
        ++resumed;
    }

    g_runtime_pause_active = 0u;
    g_runtime_pause_started = 0u;

    return resumed;
}
'''

    source = replace_once(
        source,
        clear_all_full,
        runtime_pause_helpers,
        "runtime pause/resume helpers",
    )

    lifecycle_anchor = r'''extern "C"
__declspec(noinline)
void __cdecl probe_kill_all_sound_object_types()
    __asm__("_probe_kill_all_sound_object_types");
'''

    pause_wrappers = r'''extern "C"
__declspec(noinline)
void __cdecl probe_pause_all_sound_object_types(
    DWORD a1, DWORD a2, DWORD a3, DWORD a4)
    __asm__("_probe_pause_all_sound_object_types");

extern "C"
__declspec(noinline)
void __cdecl probe_pause_all_sound_object_types(
    DWORD a1, DWORD a2, DWORD a3, DWORD a4)
{
    DWORD paused_voices =
        external_voice_pause_all(180u);

    DWORD paused_requests =
        runtime_request_pause_all();

    DWORD values[3] = {
        paused_voices,
        paused_requests,
        GetTickCount()
    };

    write_line(
        "runtime_pause_all_types",
        values,
        3u);

    typedef void (__cdecl *Original)(
        DWORD, DWORD, DWORD, DWORD);

    Original original = (Original)GetProcAddress(
        original_module(),
        "SND_fn_vPauseAllSoundObjectTypes");

    if (original)
        original(a1, a2, a3, a4);
}

extern "C"
__declspec(noinline)
void __cdecl probe_pause_all_sound_object_types_but_one(
    DWORD a1, DWORD a2, DWORD a3, DWORD a4)
    __asm__("_probe_pause_all_sound_object_types_but_one");

extern "C"
__declspec(noinline)
void __cdecl probe_pause_all_sound_object_types_but_one(
    DWORD a1, DWORD a2, DWORD a3, DWORD a4)
{
    DWORD paused_voices =
        external_voice_pause_all(181u);

    DWORD paused_requests =
        runtime_request_pause_all();

    DWORD values[4] = {
        paused_voices,
        paused_requests,
        a1,
        GetTickCount()
    };

    write_line(
        "runtime_pause_all_types_but_one",
        values,
        4u);

    typedef void (__cdecl *Original)(
        DWORD, DWORD, DWORD, DWORD);

    Original original = (Original)GetProcAddress(
        original_module(),
        "SND_fn_vPauseAllSoundObjectTypesButOne");

    if (original)
        original(a1, a2, a3, a4);
}

extern "C"
__declspec(noinline)
void __cdecl probe_resume_all_sound_object_types(
    DWORD a1, DWORD a2, DWORD a3, DWORD a4)
    __asm__("_probe_resume_all_sound_object_types");

extern "C"
__declspec(noinline)
void __cdecl probe_resume_all_sound_object_types(
    DWORD a1, DWORD a2, DWORD a3, DWORD a4)
{
    DWORD resumed_requests =
        runtime_request_resume_all();

    DWORD resumed_voices =
        external_voice_resume_all(207u);

    DWORD values[3] = {
        resumed_voices,
        resumed_requests,
        GetTickCount()
    };

    write_line(
        "runtime_resume_all_types",
        values,
        3u);

    typedef void (__cdecl *Original)(
        DWORD, DWORD, DWORD, DWORD);

    Original original = (Original)GetProcAddress(
        original_module(),
        "SND_fn_vResumeAllSoundObjectTypes");

    if (original)
        original(a1, a2, a3, a4);
}

extern "C"
__declspec(noinline)
void __cdecl probe_resume_all_sound_object_types_but_one(
    DWORD a1, DWORD a2, DWORD a3, DWORD a4)
    __asm__("_probe_resume_all_sound_object_types_but_one");

extern "C"
__declspec(noinline)
void __cdecl probe_resume_all_sound_object_types_but_one(
    DWORD a1, DWORD a2, DWORD a3, DWORD a4)
{
    DWORD resumed_requests =
        runtime_request_resume_all();

    DWORD resumed_voices =
        external_voice_resume_all(208u);

    DWORD values[4] = {
        resumed_voices,
        resumed_requests,
        a1,
        GetTickCount()
    };

    write_line(
        "runtime_resume_all_types_but_one",
        values,
        4u);

    typedef void (__cdecl *Original)(
        DWORD, DWORD, DWORD, DWORD);

    Original original = (Original)GetProcAddress(
        original_module(),
        "SND_fn_vResumeAllSoundObjectTypesButOne");

    if (original)
        original(a1, a2, a3, a4);
}

'''

    source = replace_once(
        source,
        lifecycle_anchor,
        pause_wrappers + lifecycle_anchor,
        "pause/resume wrappers",
    )

    required_tokens = [
        "WaveOutPauseFn",
        "WaveOutRestartFn",
        "g_wave_out_pause",
        "g_wave_out_restart",
        "external_voice_pause_all",
        "external_voice_resume_all",
        "runtime_request_pause_all",
        "runtime_request_resume_all",
        "probe_pause_all_sound_object_types",
        "probe_pause_all_sound_object_types_but_one",
        "probe_resume_all_sound_object_types",
        "probe_resume_all_sound_object_types_but_one",
        "runtime_pause_all_types",
        "runtime_resume_all_types",
        "waveout_pause",
        "waveout_resume",
        '"snd-waveout-fisher-lambert-v21.log"',
    ]

    for token in required_tokens:
        if token not in source:
            raise SystemExit(
                "ERROR: generated V21 source missing token: " + token
            )

    if source.count("// u") < 408:
        raise SystemExit(
            "ERROR: generated V21 source lost 408 runtime table"
        )

    V21_SOURCE.write_text(source, encoding="utf-8")

    print("PASS: V21 pause/resume source generated")
    print("PASS: V20 global kill lifecycle retained")
    print("PASS: V19 request-level stop retained")
    print("PASS: 408 runtime entries retained")


def patch_def(base_def: Path, out_def: Path):
    print()
    print("===== BUILD V21 DEF =====")

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
        "SND_fn_vPauseAllSoundObjectTypes": (
            180,
            "probe_pause_all_sound_object_types",
        ),
        "SND_fn_vPauseAllSoundObjectTypesButOne": (
            181,
            "probe_pause_all_sound_object_types_but_one",
        ),
        "SND_fn_vResumeAllSoundObjectTypes": (
            207,
            "probe_resume_all_sound_object_types",
        ),
        "SND_fn_vResumeAllSoundObjectTypesButOne": (
            208,
            "probe_resume_all_sound_object_types_but_one",
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
                f"ERROR: duplicate V21 export route: {public_name}"
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
            "ERROR: V21 DEF missing exact exports: "
            + ", ".join(missing)
        )

    out_def.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    export_lines = []

    for line in out_def.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines():
        stripped = line.strip()
        parts = stripped.rsplit(None, 1)

        if (
            len(parts) == 2
            and parts[1].startswith("@")
            and parts[1][1:].isdigit()
        ):
            export_lines.append(stripped)

    if len(export_lines) != 291:
        raise SystemExit(
            f"ERROR: V21 DEF expected 291 export lines, "
            f"got {len(export_lines)}"
        )

    expected_routes = {
        '"SND_fn_vKillAllSoundObjectTypes"='
        'probe_kill_all_sound_object_types @169',
        '"SND_fn_vKillAllSoundObjects"='
        'probe_kill_all_sound_objects @173',
        '"SND_fn_vPauseAllSoundObjectTypes"='
        'probe_pause_all_sound_object_types @180',
        '"SND_fn_vPauseAllSoundObjectTypesButOne"='
        'probe_pause_all_sound_object_types_but_one @181',
        '"SND_fn_vResumeAllSoundObjectTypes"='
        'probe_resume_all_sound_object_types @207',
        '"SND_fn_vResumeAllSoundObjectTypesButOne"='
        'probe_resume_all_sound_object_types_but_one @208',
        '"SND_fn_vStopSoundRequest"='
        'probe_stop_sound_request @247',
    }

    actual_routes = {
        line
        for line in export_lines
        if any(
            target in line
            for _, target in routes.values()
        )
    }

    if actual_routes != expected_routes:
        raise SystemExit(
            "ERROR: V21 DEF route mismatch: "
            + repr(sorted(actual_routes))
        )

    print("PASS: V21 DEF has 291 separate export lines")
    print("PASS: kill lifecycle routes retained: 169, 173")
    print("PASS: pause lifecycle routes installed: 180, 181")
    print("PASS: resume lifecycle routes installed: 207, 208")
    print("PASS: request stop retained: 247")


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


def compile_and_link(v18):
    print()
    print("===== BUILD V21 =====")

    V21_OUT.mkdir(parents=True, exist_ok=True)

    base_def = v18.BASEOUT / "SNDDSound3DDLL_VBR.def"
    out_def = V21_OUT / "SNDDSound3DDLL_VBR.def"
    obj = V21_OUT / "snd_waveout_fisher_lambert_v21.obj"
    dll = V21_OUT / "SNDDSound3DDLL_VBR.dll"

    required = [
        V21_SOURCE,
        base_def,
        v18.BASEOUT / "kernel32.lib",
        v18.BASEOUT / "kernel32-time.lib",
        v18.BASEOUT / "winmm.lib",
        SYSTEM / "SNDDSound3DDLL_VBR_orig.dll",
    ]

    for path in required:
        if not path.is_file():
            raise SystemExit(
                f"ERROR: missing V21 build input: {path}"
            )

    patch_def(base_def, out_def)

    for path in [
        obj,
        dll,
        V21_OUT / "SNDDSound3DDLL_VBR.lib",
        V21_OUT / "SNDDSound3DDLL_VBR.exp",
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
        str(V21_SOURCE),
    ])

    print("PASS: compile")

    print()
    print("===== OBJECT CHECK =====")

    nm = subprocess.check_output(
        ["llvm-nm", str(obj)],
        text=True,
    )

    required_symbols = [
        "_probe_stop_sound_request",
        "_probe_kill_all_sound_object_types",
        "_probe_kill_all_sound_objects",
        "_probe_pause_all_sound_object_types",
        "_probe_pause_all_sound_object_types_but_one",
        "_probe_resume_all_sound_object_types",
        "_probe_resume_all_sound_object_types_but_one",
    ]

    for symbol in required_symbols:
        rows = [
            parts
            for line in nm.splitlines()
            if (parts := line.split())
            and parts[-1] == symbol
        ]

        if len(rows) != 1 or "U" in rows[0][:-1]:
            raise SystemExit(
                f"ERROR: V21 object does not define {symbol} exactly once"
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

    print("PASS: all seven lifecycle wrapper symbols defined")
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

    original_exports = exports(
        SYSTEM / "SNDDSound3DDLL_VBR_orig.dll"
    )
    v21_exports = exports(dll)

    if len(original_exports) != 291:
        raise SystemExit(
            f"ERROR: original export count is "
            f"{len(original_exports)}, expected 291"
        )

    if len(v21_exports) != 291:
        raise SystemExit(
            f"ERROR: V21 export count is "
            f"{len(v21_exports)}, expected 291"
        )

    if v21_exports != original_exports:
        mismatch = next(
            (
                (index, expected, actual)
                for index, (expected, actual)
                in enumerate(
                    zip(original_exports, v21_exports),
                    start=1,
                )
                if expected != actual
            ),
            None,
        )

        raise SystemExit(
            f"ERROR: V21 export ABI mismatch: {mismatch}"
        )

    print("PASS: 291/291 exports match")
    return dll


def install_v21(dll: Path):
    print()
    print("===== INSTALL V21 DLL ONLY =====")

    live = SYSTEM / "SNDDSound3DDLL_VBR.dll"

    if live.read_bytes() != V20_DLL.read_bytes():
        raise SystemExit(
            "ERROR: live DLL is not exact accepted V20; "
            "refusing V21 install"
        )

    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = (
        PROJECT
        / "backups"
        / f"snd-waveout-fisher-lambert-v21-{stamp}"
    )
    backup.mkdir(parents=True)

    shutil.copy2(
        live,
        backup / "SNDDSound3DDLL_VBR-pre-v21.dll",
    )

    shutil.copy2(dll, live)

    if live.read_bytes() != dll.read_bytes():
        raise SystemExit(
            "ERROR: installed V21 DLL verification failed"
        )

    log = SYSTEM / "snd-waveout-fisher-lambert-v21.log"
    log.write_bytes(b"")

    print("PASS: live DLL was exact accepted V20")
    print("PASS: V21 DLL installed")
    print("PASS: 408 audio files left untouched")
    print("Backup:", backup)
    print("Log:", log)


def main():
    print("===== V21 PRECHECK =====")

    ensure_game_closed()

    required = [
        V20_BUILDER,
        V20_DLL,
        SYSTEM / "SNDDSound3DDLL_VBR.dll",
    ]

    for path in required:
        if not path.is_file():
            raise SystemExit(
                f"ERROR: missing V21 prerequisite: {path}"
            )

    live = SYSTEM / "SNDDSound3DDLL_VBR.dll"

    if live.read_bytes() != V20_DLL.read_bytes():
        raise SystemExit(
            "ERROR: live DLL is not exact accepted V20"
        )

    print("PASS: game is closed")
    print("PASS: live DLL is exact accepted V20")

    v20 = load_module(
        V20_BUILDER,
        "sc_v20_builder_for_v21",
    )

    # Recreate the exact accepted V20 generated source locally without
    # rebuilding or installing it, then layer V21 pause/resume on top.
    v20.generate_v20_source()

    if not V20_SOURCE.is_file():
        raise SystemExit(
            "ERROR: V20 generated source was not produced"
        )

    v18 = v20.load_module(
        v20.V19_BUILDER,
        "sc_v19_builder_for_v21",
    ).load_v18_module()

    print("PASS: exact V20 source baseline regenerated")

    generate_v21_source()

    dll = compile_and_link(v18)

    install_v21(dll)

    print()
    print("===== RESULT =====")
    print("PASS: Fisher/Lambert runtime V21 installed")
    print("Pause: waveOutPause + logical request freeze")
    print("Resume: waveOutRestart + duration extension")
    print("Global kill: V20 behavior retained")
    print("Request stop: V19 behavior retained")
    print("Scope: 408 Fisher/Lambert external voices")
    print("Audio payload: unchanged")


if __name__ == "__main__":
    main()
