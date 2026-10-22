#!/usr/bin/env python3
from __future__ import annotations

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

V21_OUT = PROJECT / "build/snd-waveout-fisher-lambert-v21"
V21_OBJ = V21_OUT / "snd_waveout_fisher_lambert_v21.obj"
V21_DLL = V21_OUT / "SNDDSound3DDLL_VBR.dll"

V22_OUT = PROJECT / "build/snd-waveout-fisher-lambert-v22-diag"
V22_DLL = V22_OUT / "SNDDSound3DDLL_VBR.dll"

BASEOUT = PROJECT / "build/snd-runtime-manifest-v15-1"

V23_HELPER = (
    PROJECT
    / "gameplay-subtitle-poc/src/"
    "snd_waveout_fisher_lambert_v23_pause_helper.cpp"
)
V23_ASM = (
    PROJECT
    / "gameplay-subtitle-poc/src/"
    "snd_waveout_fisher_lambert_v23_pause_routes.s"
)
V23_OUT = PROJECT / "build/snd-waveout-fisher-lambert-v23"


EXPOSED_SYMBOLS = [
    "_g_voice_slots",
    "_g_runtime_requests",
    "_g_runtime_pause_active",
    "_g_runtime_pause_started",
    "_g_wave_out_pause",
    "_g_wave_out_restart",
]


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


def generate_helper():
    print()
    print("===== GENERATE V23 PAUSE HELPER =====")

    helper = r'''typedef unsigned long DWORD;
typedef long LONG;
typedef int BOOL;
typedef void* HANDLE;
typedef void* HMODULE;
typedef const char* LPCSTR;
typedef unsigned long DWORD_PTR;
typedef unsigned long MMRESULT;
typedef void* HWAVEOUT;

#define WINAPI __stdcall
#define NULLPTR 0
#define INVALID_HANDLE_VALUE ((HANDLE)(LONG)-1)

extern "C" __declspec(dllimport)
HMODULE WINAPI LoadLibraryA(LPCSTR);

extern "C" __declspec(dllimport)
void* WINAPI GetProcAddress(HMODULE, LPCSTR);

extern "C" __declspec(dllimport)
DWORD WINAPI GetTickCount();

extern "C" __declspec(dllimport)
HANDLE WINAPI CreateFileA(
    LPCSTR,
    DWORD,
    DWORD,
    void*,
    DWORD,
    DWORD,
    HANDLE);

extern "C" __declspec(dllimport)
DWORD WINAPI SetFilePointer(
    HANDLE,
    LONG,
    LONG*,
    DWORD);

extern "C" __declspec(dllimport)
BOOL WINAPI WriteFile(
    HANDLE,
    const void*,
    DWORD,
    DWORD*,
    void*);

extern "C" __declspec(dllimport)
BOOL WINAPI CloseHandle(HANDLE);

struct SCWaveHeader
{
    char* data;
    DWORD buffer_length;
    DWORD bytes_recorded;
    DWORD_PTR user;
    DWORD flags;
    DWORD loops;
    SCWaveHeader* next;
    DWORD_PTR reserved;
};

struct ExternalVoiceSlot
{
    DWORD active;
    DWORD editor_id;
    DWORD request_id;
    DWORD paused;
    DWORD pause_started;
    DWORD expected_end;
    HWAVEOUT wave;
    void* file_memory;
    SCWaveHeader header;
};

struct RuntimeRequestState
{
    DWORD active;
    DWORD request_id;
    DWORD editor_id;
    DWORD until;
    DWORD extend_logged;
};

typedef MMRESULT (WINAPI *WaveOutPauseFn)(HWAVEOUT);
typedef MMRESULT (WINAPI *WaveOutRestartFn)(HWAVEOUT);

extern "C" {
extern ExternalVoiceSlot g_voice_slots[8]
    __asm__("_g_voice_slots");

extern RuntimeRequestState g_runtime_requests[32]
    __asm__("_g_runtime_requests");

extern DWORD g_runtime_pause_active
    __asm__("_g_runtime_pause_active");

extern DWORD g_runtime_pause_started
    __asm__("_g_runtime_pause_started");

extern WaveOutPauseFn g_wave_out_pause
    __asm__("_g_wave_out_pause");

extern WaveOutRestartFn g_wave_out_restart
    __asm__("_g_wave_out_restart");
}

typedef char V23AssertVoiceSlotSize[
    sizeof(ExternalVoiceSlot) == 64 ? 1 : -1
];

typedef char V23AssertRequestStateSize[
    sizeof(RuntimeRequestState) == 20 ? 1 : -1
];

static HMODULE g_v23_original = (HMODULE)NULLPTR;

static HMODULE
v23_original_module()
{
    if (!g_v23_original)
        g_v23_original =
            LoadLibraryA("SNDDSound3DDLL_VBR_orig.dll");

    return g_v23_original;
}

static char
v23_hex_digit(DWORD value)
{
    value &= 0xFu;

    return value < 10u
        ? (char)('0' + value)
        : (char)('A' + (value - 10u));
}

static void
v23_write_hex8(char* out, DWORD value)
{
    for (DWORD i = 0u; i < 8u; ++i) {
        DWORD shift = 28u - (i * 4u);
        out[i] = v23_hex_digit(value >> shift);
    }
}

static void
v23_log(
    const char* label,
    DWORD label_len,
    const DWORD* values,
    DWORD count)
{
    HANDLE file = CreateFileA(
        "snd-waveout-fisher-lambert-v23.log",
        0x40000000u,
        0x00000003u,
        0,
        4u,
        0x00000080u,
        0);

    if (file == INVALID_HANDLE_VALUE)
        return;

    SetFilePointer(file, 0, 0, 2u);

    char line[160];
    DWORD pos = 0u;

    for (
        DWORD i = 0u;
        i < label_len && pos < 150u;
        ++i
    ) {
        line[pos++] = label[i];
    }

    for (
        DWORD i = 0u;
        i < count && pos + 9u < 150u;
        ++i
    ) {
        line[pos++] = ' ';
        v23_write_hex8(line + pos, values[i]);
        pos += 8u;
    }

    line[pos++] = '\r';
    line[pos++] = '\n';

    DWORD written = 0u;

    WriteFile(
        file,
        line,
        pos,
        &written,
        0);

    CloseHandle(file);
}

static DWORD
v23_pause_external()
{
    DWORD now = GetTickCount();
    DWORD paused = 0u;
    DWORD failures = 0u;
    DWORD active_requests = 0u;

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

        if (result == 0u) {
            slot->paused = 1u;
            slot->pause_started = now;
            ++paused;
        } else {
            ++failures;
        }
    }

    for (DWORD i = 0u; i < 32u; ++i) {
        if (g_runtime_requests[i].active)
            ++active_requests;
    }

    if (
        active_requests &&
        !g_runtime_pause_active
    ) {
        g_runtime_pause_active = 1u;
        g_runtime_pause_started = now;
    }

    DWORD values[4] = {
        paused,
        active_requests,
        failures,
        now
    };

    v23_log(
        "v23_pause",
        9u,
        values,
        4u);

    return failures;
}

static DWORD
v23_resume_external()
{
    DWORD now = GetTickCount();
    DWORD resumed_requests = 0u;
    DWORD request_pause_ms = 0u;

    if (g_runtime_pause_active) {
        request_pause_ms =
            now - g_runtime_pause_started;

        for (DWORD i = 0u; i < 32u; ++i) {
            RuntimeRequestState* state =
                &g_runtime_requests[i];

            if (!state->active)
                continue;

            state->until += request_pause_ms;
            ++resumed_requests;
        }

        g_runtime_pause_active = 0u;
        g_runtime_pause_started = 0u;
    }

    DWORD resumed_voices = 0u;
    DWORD failures = 0u;

    for (DWORD i = 0u; i < 8u; ++i) {
        ExternalVoiceSlot* slot =
            &g_voice_slots[i];

        if (
            !slot->active ||
            !slot->paused ||
            !slot->wave
        )
            continue;

        DWORD voice_pause_ms =
            now - slot->pause_started;

        MMRESULT result =
            g_wave_out_restart
            ? g_wave_out_restart(slot->wave)
            : 1u;

        if (result == 0u) {
            slot->expected_end += voice_pause_ms;
            slot->paused = 0u;
            slot->pause_started = 0u;
            ++resumed_voices;
        } else {
            ++failures;
        }
    }

    DWORD values[5] = {
        resumed_voices,
        resumed_requests,
        failures,
        request_pause_ms,
        now
    };

    v23_log(
        "v23_resume",
        10u,
        values,
        5u);

    return failures;
}

extern "C"
__declspec(noinline)
DWORD __cdecl v23_pause_route(DWORD ordinal)
    __asm__("_v23_pause_route");

extern "C"
__declspec(noinline)
DWORD __cdecl v23_pause_route(DWORD ordinal)
{
    v23_pause_external();

    HMODULE original =
        v23_original_module();

    void* target = original
        ? GetProcAddress(
            original,
            (LPCSTR)(DWORD_PTR)ordinal)
        : 0;

    DWORD values[2] = {
        ordinal,
        (DWORD)target
    };

    v23_log(
        "v23_pause_route",
        15u,
        values,
        2u);

    return (DWORD)target;
}

extern "C"
__declspec(noinline)
DWORD __cdecl v23_resume_route(DWORD ordinal)
    __asm__("_v23_resume_route");

extern "C"
__declspec(noinline)
DWORD __cdecl v23_resume_route(DWORD ordinal)
{
    v23_resume_external();

    HMODULE original =
        v23_original_module();

    void* target = original
        ? GetProcAddress(
            original,
            (LPCSTR)(DWORD_PTR)ordinal)
        : 0;

    DWORD values[2] = {
        ordinal,
        (DWORD)target
    };

    v23_log(
        "v23_resume_route",
        16u,
        values,
        2u);

    return (DWORD)target;
}
'''

    V23_HELPER.write_text(
        helper,
        encoding="utf-8",
    )

    text = V23_HELPER.read_text(encoding="utf-8")

    for token in [
        "ExternalVoiceSlot",
        "RuntimeRequestState",
        "_g_voice_slots",
        "_g_runtime_requests",
        "_g_wave_out_pause",
        "_g_wave_out_restart",
        "_v23_pause_route",
        "_v23_resume_route",
        "snd-waveout-fisher-lambert-v23.log",
    ]:
        if token not in text:
            raise SystemExit(
                "ERROR: generated V23 helper missing token: "
                + token
            )

    print("PASS: V23 helper generated")
    print("PASS: external voice slot size asserted at 64 bytes")
    print("PASS: runtime request state size asserted at 20 bytes")


def generate_asm():
    print()
    print("===== GENERATE V23 ROUTE ASM =====")

    asm = r'''.intel_syntax noprefix

.data
.p2align 2

_v23_target_pause:
    .long 0

_v23_target_resume:
    .long 0

.text

.globl _probe_pause_sound_object_type
.def _probe_pause_sound_object_type; .scl 2; .type 32; .endef
_probe_pause_sound_object_type:
    pushfd
    pushad
    push 185
    call _v23_pause_route
    add esp, 4
    mov dword ptr [_v23_target_pause], eax
    popad
    popfd
    jmp dword ptr [_v23_target_pause]

.globl _probe_resume_sound_object_type
.def _probe_resume_sound_object_type; .scl 2; .type 32; .endef
_probe_resume_sound_object_type:
    pushfd
    pushad
    push 212
    call _v23_resume_route
    add esp, 4
    mov dword ptr [_v23_target_resume], eax
    popad
    popfd
    jmp dword ptr [_v23_target_resume]
'''

    V23_ASM.write_text(
        asm,
        encoding="utf-8",
    )

    text = V23_ASM.read_text(encoding="utf-8")

    for token in [
        "_probe_pause_sound_object_type",
        "_probe_resume_sound_object_type",
        "push 185",
        "push 212",
        "_v23_pause_route",
        "_v23_resume_route",
    ]:
        if token not in text:
            raise SystemExit(
                "ERROR: generated V23 ASM missing token: "
                + token
            )

    print("PASS: @185 pause passthrough generated")
    print("PASS: @212 resume passthrough generated")


def patch_def(base_def: Path, out_def: Path):
    print()
    print("===== BUILD V23 DEF =====")

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
        "SND_fn_vPauseSoundObjectType": (
            185,
            "probe_pause_sound_object_type",
        ),
        "SND_fn_vResumeAllSoundObjectTypes": (
            207,
            "probe_resume_all_sound_object_types",
        ),
        "SND_fn_vResumeAllSoundObjectTypesButOne": (
            208,
            "probe_resume_all_sound_object_types_but_one",
        ),
        "SND_fn_vResumeSoundObjectType": (
            212,
            "probe_resume_sound_object_type",
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

        ordinal_match = re.search(
            r"(\s+@(\d+)\b.*)$",
            stripped,
        )

        if not ordinal_match:
            raise SystemExit(
                f"ERROR: {public_name} export has no ordinal"
            )

        actual_ordinal = int(
            ordinal_match.group(2)
        )

        if actual_ordinal != expected_ordinal:
            raise SystemExit(
                f"ERROR: {public_name} expected ordinal "
                f"{expected_ordinal}, got {actual_ordinal}"
            )

        if public_name in found:
            raise SystemExit(
                f"ERROR: duplicate V23 route: {public_name}"
            )

        suffix = ordinal_match.group(1)
        indent = line[
            : len(line) - len(line.lstrip())
        ]

        found[public_name] = stripped
        lines[i] = (
            indent
            + lhs
            + "="
            + target
            + suffix
        )

    if set(found) != set(routes):
        missing = sorted(
            set(routes) - set(found)
        )
        raise SystemExit(
            "ERROR: V23 DEF missing exact exports: "
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
            f"ERROR: V23 DEF expected 291 export lines, "
            f"got {len(export_lines)}"
        )

    for public_name, (
        ordinal,
        target,
    ) in routes.items():
        expected = (
            f'"{public_name}"={target} @{ordinal}'
        )

        if expected not in export_lines:
            raise SystemExit(
                "ERROR: V23 exact route missing: "
                + expected
            )

    # V22 diagnostic routes that were not proven by ESC must no
    # longer be hooked in V23.
    for public_name in [
        "SND_fn_vPauseClientBuffer",
        "SND_fn_vPauseSoundObject",
        "_SND_fn_vPauseSxd@4",
        "_SND_fn_vPauseTimer@4",
        "_SND_fn_vPauseTransitionSxd@4",
        "SND_fn_vResumeClientBuffer",
        "SND_fn_vResumeSoundObject",
        "_SND_fn_vResumeSxd@4",
        "_SND_fn_vResumeTimer@4",
        "_SND_fn_vResumeTransitionSxd@4",
    ]:
        matches = [
            line
            for line in export_lines
            if line.startswith(
                f'"{public_name}"='
            )
        ]

        if (
            len(matches) != 1
            or "SNDDSound3DDLL_VBR_orig.#"
            not in matches[0]
        ):
            raise SystemExit(
                "ERROR: V23 unexpectedly retains "
                f"diagnostic hook for {public_name}: "
                + repr(matches)
            )

    print("PASS: V23 DEF has 291 separate export lines")
    print("PASS: proven ESC pause route installed at @185")
    print("PASS: proven ESC resume route installed at @212")
    print("PASS: V21 kill/request lifecycle routes retained")
    print("PASS: unproven V22 diagnostic routes removed")


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


def globalize_v21_state(out_obj: Path):
    print()
    print("===== EXPOSE V21 PAUSE STATE =====")

    data = bytearray(V21_OBJ.read_bytes())

    # IMAGE_FILE_HEADER is 20 bytes for a COFF object.
    # PointerToSymbolTable: offset 8, NumberOfSymbols: offset 12.
    if len(data) < 20:
        raise SystemExit(
            "ERROR: V21 object is too small for a COFF header"
        )

    pointer_to_symbols = int.from_bytes(
        data[8:12],
        "little",
    )
    number_of_symbols = int.from_bytes(
        data[12:16],
        "little",
    )

    symbol_size = 18
    symbol_table_end = (
        pointer_to_symbols
        + number_of_symbols * symbol_size
    )

    if (
        pointer_to_symbols < 20
        or number_of_symbols == 0
        or symbol_table_end + 4 > len(data)
    ):
        raise SystemExit(
            "ERROR: invalid V21 COFF symbol-table bounds"
        )

    string_table_size = int.from_bytes(
        data[symbol_table_end : symbol_table_end + 4],
        "little",
    )

    if (
        string_table_size < 4
        or symbol_table_end + string_table_size > len(data)
    ):
        raise SystemExit(
            "ERROR: invalid V21 COFF string-table bounds"
        )

    def symbol_name(entry_offset: int) -> str:
        raw_name = data[
            entry_offset : entry_offset + 8
        ]

        if raw_name[:4] == b"\x00\x00\x00\x00":
            string_offset = int.from_bytes(
                raw_name[4:8],
                "little",
            )

            if (
                string_offset < 4
                or string_offset >= string_table_size
            ):
                raise SystemExit(
                    "ERROR: invalid COFF long-name string offset"
                )

            start = symbol_table_end + string_offset
            end = data.find(b"\x00", start)

            if (
                end < 0
                or end >= symbol_table_end + string_table_size
            ):
                raise SystemExit(
                    "ERROR: unterminated COFF long symbol name"
                )

            raw = bytes(data[start:end])
        else:
            raw = bytes(raw_name).split(
                b"\x00",
                1,
            )[0]

        try:
            return raw.decode("ascii")
        except UnicodeDecodeError as exc:
            raise SystemExit(
                "ERROR: non-ASCII symbol name in V21 COFF object"
            ) from exc

    found = {
        symbol: []
        for symbol in EXPOSED_SYMBOLS
    }

    index = 0

    while index < number_of_symbols:
        entry_offset = (
            pointer_to_symbols
            + index * symbol_size
        )

        if entry_offset + symbol_size > symbol_table_end:
            raise SystemExit(
                "ERROR: truncated V21 COFF symbol entry"
            )

        name = symbol_name(entry_offset)
        storage_class = data[entry_offset + 16]
        aux_count = data[entry_offset + 17]

        if name in found:
            section_number = int.from_bytes(
                data[
                    entry_offset + 12 : entry_offset + 14
                ],
                "little",
                signed=True,
            )

            found[name].append(
                (
                    entry_offset,
                    storage_class,
                    section_number,
                    aux_count,
                )
            )

        index += 1 + aux_count

    for symbol, rows in found.items():
        if len(rows) != 1:
            raise SystemExit(
                f"ERROR: V23 expected exactly one COFF symbol "
                f"{symbol}, got {len(rows)}"
            )

        (
            entry_offset,
            storage_class,
            section_number,
            _aux_count,
        ) = rows[0]

        if storage_class != 3:
            raise SystemExit(
                f"ERROR: V23 expected local STATIC(3) for "
                f"{symbol}, got {storage_class}"
            )

        if section_number <= 0:
            raise SystemExit(
                f"ERROR: V23 symbol {symbol} is not a defined "
                f"section symbol: section={section_number}"
            )

        # IMAGE_SYM_CLASS_STATIC (3) -> IMAGE_SYM_CLASS_EXTERNAL (2).
        # Only the symbol storage class changes; section/value/name and
        # all relocation data remain byte-identical.
        data[entry_offset + 16] = 2

    out_obj.write_bytes(data)

    # Ensure source object was never modified.
    if V21_OBJ.read_bytes() == out_obj.read_bytes():
        raise SystemExit(
            "ERROR: V23 COFF globalization produced no object changes"
        )

    nm = subprocess.check_output(
        ["llvm-nm", str(out_obj)],
        text=True,
    )

    for symbol in EXPOSED_SYMBOLS:
        rows = [
            parts
            for line in nm.splitlines()
            if (parts := line.split())
            and parts[-1] == symbol
        ]

        if len(rows) != 1:
            raise SystemExit(
                f"ERROR: V23 exposed symbol count "
                f"for {symbol}: {len(rows)}"
            )

        symbol_type = rows[0][-2]

        if symbol_type.islower():
            raise SystemExit(
                f"ERROR: V23 symbol still local: "
                f"{symbol} type={symbol_type}"
            )

    original_nm = subprocess.check_output(
        ["llvm-nm", str(V21_OBJ)],
        text=True,
    )

    for symbol in EXPOSED_SYMBOLS:
        rows = [
            parts
            for line in original_nm.splitlines()
            if (parts := line.split())
            and parts[-1] == symbol
        ]

        if (
            len(rows) != 1
            or not rows[0][-2].islower()
        ):
            raise SystemExit(
                f"ERROR: original accepted V21 object was not "
                f"left local for {symbol}"
            )

    print("PASS: six V21 COFF symbols patched STATIC(3) -> EXTERNAL(2)")
    print("PASS: exposed object relocations/layout left intact")
    print("PASS: original accepted V21 object left untouched")


def build():
    print()
    print("===== BUILD V23 =====")

    V23_OUT.mkdir(
        parents=True,
        exist_ok=True,
    )

    base_def = (
        BASEOUT
        / "SNDDSound3DDLL_VBR.def"
    )
    out_def = (
        V23_OUT
        / "SNDDSound3DDLL_VBR.def"
    )
    runtime_obj = (
        V23_OUT
        / "snd_waveout_fisher_lambert_v21_exposed.obj"
    )
    helper_obj = (
        V23_OUT
        / "snd_waveout_fisher_lambert_v23_pause_helper.obj"
    )
    asm_obj = (
        V23_OUT
        / "snd_waveout_fisher_lambert_v23_pause_routes.obj"
    )
    dll = (
        V23_OUT
        / "SNDDSound3DDLL_VBR.dll"
    )

    required = [
        V21_OBJ,
        V23_HELPER,
        V23_ASM,
        base_def,
        BASEOUT / "kernel32.lib",
        BASEOUT / "kernel32-time.lib",
        BASEOUT / "winmm.lib",
        SYSTEM / "SNDDSound3DDLL_VBR_orig.dll",
    ]

    for path in required:
        if not path.is_file():
            raise SystemExit(
                f"ERROR: missing V23 build input: "
                f"{path}"
            )

    patch_def(
        base_def,
        out_def,
    )

    for path in [
        runtime_obj,
        helper_obj,
        asm_obj,
        dll,
        V23_OUT / "SNDDSound3DDLL_VBR.lib",
        V23_OUT / "SNDDSound3DDLL_VBR.exp",
    ]:
        try:
            path.unlink()
        except FileNotFoundError:
            pass

    globalize_v21_state(
        runtime_obj,
    )

    print()
    print("===== COMPILE SMALL V23 OBJECTS =====")

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
        f"/Fo{helper_obj}",
        str(V23_HELPER),
    ])

    print("PASS: V23 pause helper compile")

    run([
        "clang-cl",
        "--target=i686-pc-windows-msvc",
        "/nologo",
        "/c",
        f"/Fo{asm_obj}",
        str(V23_ASM),
    ])

    print("PASS: V23 route ASM compile")

    print()
    print("===== OBJECT CHECK =====")

    helper_nm = subprocess.check_output(
        ["llvm-nm", str(helper_obj)],
        text=True,
    )
    asm_nm = subprocess.check_output(
        ["llvm-nm", str(asm_obj)],
        text=True,
    )
    runtime_nm = subprocess.check_output(
        ["llvm-nm", str(runtime_obj)],
        text=True,
    )

    for symbol in [
        "_v23_pause_route",
        "_v23_resume_route",
    ]:
        rows = [
            parts
            for line in helper_nm.splitlines()
            if (parts := line.split())
            and parts[-1] == symbol
        ]

        if (
            len(rows) != 1
            or "U" in rows[0][:-1]
        ):
            raise SystemExit(
                "ERROR: V23 helper does not define "
                + symbol
            )

    for symbol in [
        "_probe_pause_sound_object_type",
        "_probe_resume_sound_object_type",
    ]:
        rows = [
            parts
            for line in asm_nm.splitlines()
            if (parts := line.split())
            and parts[-1] == symbol
        ]

        if (
            len(rows) != 1
            or "U" in rows[0][:-1]
        ):
            raise SystemExit(
                "ERROR: V23 ASM does not define "
                + symbol
            )

    for inherited in [
        "_probe_kill_all_sound_object_types",
        "_probe_kill_all_sound_objects",
        "_probe_pause_all_sound_object_types",
        "_probe_pause_all_sound_object_types_but_one",
        "_probe_resume_all_sound_object_types",
        "_probe_resume_all_sound_object_types_but_one",
        "_probe_stop_sound_request",
    ]:
        if inherited not in runtime_nm:
            raise SystemExit(
                "ERROR: V23 exposed V21 object "
                "missing inherited hook: "
                + inherited
            )

    print("PASS: V23 pause/resume route helpers defined")
    print("PASS: V21 inherited lifecycle hooks retained")

    print()
    print("===== LINK =====")

    run([
        "lld-link",
        "/dll",
        "/nodefaultlib",
        "/machine:x86",
        "/subsystem:windows,5.1",
        "/safeseh:no",
        "/entry:DllMain@12",
        f"/def:{out_def}",
        f"/out:{dll}",
        str(runtime_obj),
        str(helper_obj),
        str(asm_obj),
        str(BASEOUT / "kernel32.lib"),
        str(BASEOUT / "kernel32-time.lib"),
        str(BASEOUT / "winmm.lib"),
    ])

    print("PASS: link")

    print()
    print("===== VERIFY EXPORT ABI =====")

    original_exports = exports(
        SYSTEM
        / "SNDDSound3DDLL_VBR_orig.dll"
    )
    v23_exports = exports(dll)

    if len(original_exports) != 291:
        raise SystemExit(
            f"ERROR: original export count is "
            f"{len(original_exports)}, expected 291"
        )

    if len(v23_exports) != 291:
        raise SystemExit(
            f"ERROR: V23 export count is "
            f"{len(v23_exports)}, expected 291"
        )

    if v23_exports != original_exports:
        mismatch = next(
            (
                (
                    index,
                    expected,
                    actual,
                )
                for index, (
                    expected,
                    actual,
                )
                in enumerate(
                    zip(
                        original_exports,
                        v23_exports,
                    ),
                    start=1,
                )
                if expected != actual
            ),
            None,
        )

        raise SystemExit(
            "ERROR: V23 export ABI mismatch: "
            + repr(mismatch)
        )

    print("PASS: 291/291 exports match")
    return dll


def install(dll: Path):
    print()
    print("===== INSTALL V23 DLL ONLY =====")

    live = (
        SYSTEM
        / "SNDDSound3DDLL_VBR.dll"
    )

    predecessor = None

    for label, candidate in [
        ("V22 diagnostic", V22_DLL),
        ("V21", V21_DLL),
    ]:
        if (
            candidate.is_file()
            and live.read_bytes()
            == candidate.read_bytes()
        ):
            predecessor = label
            break

    if predecessor is None:
        raise SystemExit(
            "ERROR: live DLL is neither exact V22 "
            "diagnostic nor exact accepted V21; "
            "refusing V23 install"
        )

    stamp = time.strftime(
        "%Y%m%d-%H%M%S"
    )
    backup = (
        PROJECT
        / "backups"
        / f"snd-waveout-fisher-lambert-v23-{stamp}"
    )
    backup.mkdir(
        parents=True,
    )

    shutil.copy2(
        live,
        backup
        / "SNDDSound3DDLL_VBR-pre-v23.dll",
    )

    shutil.copy2(
        dll,
        live,
    )

    if live.read_bytes() != dll.read_bytes():
        raise SystemExit(
            "ERROR: installed V23 DLL verification failed"
        )

    log = (
        SYSTEM
        / "snd-waveout-fisher-lambert-v23.log"
    )
    log.write_bytes(b"")

    print(
        "PASS: predecessor verified:",
        predecessor,
    )
    print("PASS: V23 DLL installed")
    print("PASS: 408 audio files left untouched")
    print("Backup:", backup)
    print("Log:", log)


def main():
    print("===== V23 PRECHECK =====")

    ensure_game_closed()

    required = [
        V21_OBJ,
        V21_DLL,
        SYSTEM / "SNDDSound3DDLL_VBR.dll",
    ]

    for path in required:
        if not path.is_file():
            raise SystemExit(
                f"ERROR: missing V23 prerequisite: "
                f"{path}"
            )

    print("PASS: game is closed")
    print("PASS: accepted V21 runtime object is present")

    generate_helper()
    generate_asm()

    dll = build()

    install(dll)

    print()
    print("===== RESULT =====")
    print("PASS: Fisher/Lambert runtime V23 installed")
    print("ESC pause route: @185 PauseSoundObjectType")
    print("ESC resume route: @212 ResumeSoundObjectType")
    print("Pause action: waveOutPause + request freeze")
    print("Resume action: waveOutRestart + duration extension")
    print("V20 global kill behavior retained")
    print("V19 request-stop behavior retained")
    print("Scope: 408 Fisher/Lambert external voices")
    print("Audio payload: unchanged")


if __name__ == "__main__":
    main()
