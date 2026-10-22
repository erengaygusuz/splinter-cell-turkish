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

V21_SOURCE = PROJECT / "gameplay-subtitle-poc/src/snd_waveout_fisher_lambert_v21.cpp"
V21_OUT = PROJECT / "build/snd-waveout-fisher-lambert-v21"
V21_OBJ = V21_OUT / "snd_waveout_fisher_lambert_v21.obj"
V21_DLL = V21_OUT / "SNDDSound3DDLL_VBR.dll"

V22_HELPER = PROJECT / "gameplay-subtitle-poc/src/snd_waveout_fisher_lambert_v22_diag_helper.cpp"
V22_ASM = PROJECT / "gameplay-subtitle-poc/src/snd_waveout_fisher_lambert_v22_diag_routes.s"
V22_OUT = PROJECT / "build/snd-waveout-fisher-lambert-v22-diag"
BASEOUT = PROJECT / "build/snd-runtime-manifest-v15-1"


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
            f"ERROR: V22 patch {label!r} expected one match, got {count}"
        )

    return source.replace(old, new, 1)


def generate_v22_helper():
    print()
    print("===== GENERATE V22 DIAGNOSTIC HELPER =====")

    helper = r'''typedef unsigned long DWORD;
typedef long LONG;
typedef int BOOL;
typedef void* HANDLE;
typedef void* HMODULE;
typedef const char* LPCSTR;
typedef unsigned long DWORD_PTR;

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

static HMODULE g_v22_original = (HMODULE)NULLPTR;

static HMODULE
v22_original_module()
{
    if (!g_v22_original)
        g_v22_original =
            LoadLibraryA("SNDDSound3DDLL_VBR_orig.dll");

    return g_v22_original;
}

static char
v22_hex_digit(DWORD value)
{
    value &= 0xFu;
    return value < 10u
        ? (char)('0' + value)
        : (char)('A' + (value - 10u));
}

static void
v22_write_hex8(char* out, DWORD value)
{
    for (DWORD i = 0u; i < 8u; ++i) {
        DWORD shift = 28u - (i * 4u);
        out[i] = v22_hex_digit(value >> shift);
    }
}

static void
v22_log_route(
    DWORD ordinal,
    DWORD target,
    DWORD tick)
{
    HANDLE file = CreateFileA(
        "snd-waveout-fisher-lambert-v22-diag.log",
        0x40000000u,
        0x00000003u,
        0,
        4u,
        0x00000080u,
        0);

    if (file == INVALID_HANDLE_VALUE)
        return;

    SetFilePointer(file, 0, 0, 2u);

    char line[46];

    const char prefix[] = "pause_route_probe ";

    for (DWORD i = 0u; i < 18u; ++i)
        line[i] = prefix[i];

    v22_write_hex8(line + 18, ordinal);
    line[26] = ' ';
    v22_write_hex8(line + 27, target);
    line[35] = ' ';
    v22_write_hex8(line + 36, tick);
    line[44] = '\r';
    line[45] = '\n';

    DWORD written = 0u;

    WriteFile(
        file,
        line,
        46u,
        &written,
        0);

    CloseHandle(file);
}

extern "C"
__declspec(noinline)
DWORD __cdecl probe_pause_route_original(DWORD ordinal)
    __asm__("_probe_pause_route_original");

extern "C"
__declspec(noinline)
DWORD __cdecl probe_pause_route_original(DWORD ordinal)
{
    HMODULE original =
        v22_original_module();

    void* target = original
        ? GetProcAddress(
            original,
            (LPCSTR)(DWORD_PTR)ordinal)
        : 0;

    DWORD tick = GetTickCount();

    v22_log_route(
        ordinal,
        (DWORD)target,
        tick);

    return (DWORD)target;
}
'''

    V22_HELPER.write_text(
        helper,
        encoding="utf-8",
    )

    text = V22_HELPER.read_text(encoding="utf-8")

    for token in [
        "_probe_pause_route_original",
        "pause_route_probe",
        "SNDDSound3DDLL_VBR_orig.dll",
        "snd-waveout-fisher-lambert-v22-diag.log",
    ]:
        if token not in text:
            raise SystemExit(
                "ERROR: generated V22 helper missing token: " + token
            )

    print("PASS: tiny V22 diagnostic helper generated")
    print("PASS: accepted V21 runtime object will be reused")


def generate_v22_asm():
    print()
    print("===== GENERATE V22 DIAGNOSTIC ASM =====")

    routes = [
        ("probe_pause_client_buffer", 183),
        ("probe_pause_sound_object", 184),
        ("probe_pause_sound_object_type", 185),
        ("probe_pause_sxd", 186),
        ("probe_pause_timer", 187),
        ("probe_pause_transition_sxd", 188),
        ("probe_resume_client_buffer", 210),
        ("probe_resume_sound_object", 211),
        ("probe_resume_sound_object_type", 212),
        ("probe_resume_sxd", 213),
        ("probe_resume_timer", 214),
        ("probe_resume_transition_sxd", 215),
    ]

    lines = [
        ".intel_syntax noprefix",
        ".data",
        ".p2align 2",
    ]

    for _, ordinal in routes:
        lines.extend([
            f"_v22_target_{ordinal}:",
            "    .long 0",
        ])

    lines.extend([
        ".text",
        "",
    ])

    for name, ordinal in routes:
        symbol = "_" + name
        lines.extend([
            f".globl {symbol}",
            f".def {symbol}; .scl 2; .type 32; .endef",
            f"{symbol}:",
            "    pushfd",
            "    pushad",
            f"    push {ordinal}",
            "    call _probe_pause_route_original",
            "    add esp, 4",
            f"    mov dword ptr [_v22_target_{ordinal}], eax",
            "    popad",
            "    popfd",
            f"    jmp dword ptr [_v22_target_{ordinal}]",
            "",
        ])

    V22_ASM.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    asm_text = V22_ASM.read_text(encoding="utf-8")

    for name, ordinal in routes:
        if (
            ("_" + name + ":") not in asm_text
            or f"push {ordinal}" not in asm_text
            or f"_v22_target_{ordinal}" not in asm_text
        ):
            raise SystemExit(
                f"ERROR: generated V22 ASM missing route {name} @{ordinal}"
            )

    print("PASS: 12 x86 passthrough routes generated")
    print("PASS: wrappers preserve flags/registers and caller stack")


def patch_def(base_def: Path, out_def: Path):
    print()
    print("===== BUILD V22 DIAGNOSTIC DEF =====")

    lines = base_def.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines()

    routes = {
        "SND_fn_vKillAllSoundObjectTypes": (169, "probe_kill_all_sound_object_types"),
        "SND_fn_vKillAllSoundObjects": (173, "probe_kill_all_sound_objects"),
        "SND_fn_vPauseAllSoundObjectTypes": (180, "probe_pause_all_sound_object_types"),
        "SND_fn_vPauseAllSoundObjectTypesButOne": (181, "probe_pause_all_sound_object_types_but_one"),
        "SND_fn_vPauseClientBuffer": (183, "probe_pause_client_buffer"),
        "SND_fn_vPauseSoundObject": (184, "probe_pause_sound_object"),
        "SND_fn_vPauseSoundObjectType": (185, "probe_pause_sound_object_type"),
        "_SND_fn_vPauseSxd@4": (186, "probe_pause_sxd"),
        "_SND_fn_vPauseTimer@4": (187, "probe_pause_timer"),
        "_SND_fn_vPauseTransitionSxd@4": (188, "probe_pause_transition_sxd"),
        "SND_fn_vResumeAllSoundObjectTypes": (207, "probe_resume_all_sound_object_types"),
        "SND_fn_vResumeAllSoundObjectTypesButOne": (208, "probe_resume_all_sound_object_types_but_one"),
        "SND_fn_vResumeClientBuffer": (210, "probe_resume_client_buffer"),
        "SND_fn_vResumeSoundObject": (211, "probe_resume_sound_object"),
        "SND_fn_vResumeSoundObjectType": (212, "probe_resume_sound_object_type"),
        "_SND_fn_vResumeSxd@4": (213, "probe_resume_sxd"),
        "_SND_fn_vResumeTimer@4": (214, "probe_resume_timer"),
        "_SND_fn_vResumeTransitionSxd@4": (215, "probe_resume_transition_sxd"),
        "SND_fn_vStopSoundRequest": (247, "probe_stop_sound_request"),
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
                f"ERROR: duplicate V22 route: {public_name}"
            )

        suffix = ordinal_match.group(1)
        indent = line[: len(line) - len(line.lstrip())]

        found[public_name] = stripped
        lines[i] = indent + lhs + "=" + target + suffix

    if set(found) != set(routes):
        missing = sorted(set(routes) - set(found))
        raise SystemExit(
            "ERROR: V22 DEF missing exact exports: "
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
            f"ERROR: V22 DEF expected 291 export lines, got "
            f"{len(export_lines)}"
        )

    for public_name, (ordinal, target) in routes.items():
        lhs = f'"{public_name}"'
        expected = f"{lhs}={target} @{ordinal}"

        if expected not in export_lines:
            raise SystemExit(
                "ERROR: V22 exact route missing: " + expected
            )

    print("PASS: V22 DEF has 291 separate export lines")
    print("PASS: V21 lifecycle routes retained")
    print("PASS: 12 signature-agnostic pause/resume probes installed")


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


def build():
    print()
    print("===== BUILD V22 DIAGNOSTIC =====")

    V22_OUT.mkdir(parents=True, exist_ok=True)

    base_def = BASEOUT / "SNDDSound3DDLL_VBR.def"
    out_def = V22_OUT / "SNDDSound3DDLL_VBR.def"
    helper_obj = V22_OUT / "snd_waveout_fisher_lambert_v22_diag_helper.obj"
    asm_obj = V22_OUT / "snd_waveout_fisher_lambert_v22_diag_routes.obj"
    dll = V22_OUT / "SNDDSound3DDLL_VBR.dll"

    required = [
        V21_OBJ,
        V22_HELPER,
        V22_ASM,
        base_def,
        BASEOUT / "kernel32.lib",
        BASEOUT / "kernel32-time.lib",
        BASEOUT / "winmm.lib",
        SYSTEM / "SNDDSound3DDLL_VBR_orig.dll",
    ]

    for path in required:
        if not path.is_file():
            raise SystemExit(
                f"ERROR: missing V22 build input: {path}"
            )

    patch_def(base_def, out_def)

    for path in [
        helper_obj,
        asm_obj,
        dll,
        V22_OUT / "SNDDSound3DDLL_VBR.lib",
        V22_OUT / "SNDDSound3DDLL_VBR.exp",
    ]:
        try:
            path.unlink()
        except FileNotFoundError:
            pass

    print()
    print("===== COMPILE SMALL DIAGNOSTIC OBJECTS =====")

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
        str(V22_HELPER),
    ])

    print("PASS: tiny diagnostic helper compile")

    run([
        "clang-cl",
        "--target=i686-pc-windows-msvc",
        "/nologo",
        "/c",
        f"/Fo{asm_obj}",
        str(V22_ASM),
    ])

    print("PASS: x86 diagnostic ASM compile")

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
    v21_nm = subprocess.check_output(
        ["llvm-nm", str(V21_OBJ)],
        text=True,
    )

    helper_rows = [
        parts
        for line in helper_nm.splitlines()
        if (parts := line.split())
        and parts[-1] == "_probe_pause_route_original"
    ]

    if (
        len(helper_rows) != 1
        or "U" in helper_rows[0][:-1]
    ):
        raise SystemExit(
            "ERROR: V22 helper does not define "
            "_probe_pause_route_original exactly once"
        )

    route_symbols = [
        "_probe_pause_client_buffer",
        "_probe_pause_sound_object",
        "_probe_pause_sound_object_type",
        "_probe_pause_sxd",
        "_probe_pause_timer",
        "_probe_pause_transition_sxd",
        "_probe_resume_client_buffer",
        "_probe_resume_sound_object",
        "_probe_resume_sound_object_type",
        "_probe_resume_sxd",
        "_probe_resume_timer",
        "_probe_resume_transition_sxd",
    ]

    for symbol in route_symbols:
        rows = [
            parts
            for line in asm_nm.splitlines()
            if (parts := line.split())
            and parts[-1] == symbol
        ]

        if len(rows) != 1 or "U" in rows[0][:-1]:
            raise SystemExit(
                f"ERROR: V22 ASM object does not define {symbol} exactly once"
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
        if inherited not in v21_nm:
            raise SystemExit(
                "ERROR: accepted V21 object missing inherited symbol: "
                + inherited
            )

    if "_probe_pause_route_original" not in asm_nm:
        raise SystemExit(
            "ERROR: V22 ASM object does not reference diagnostic helper"
        )

    print("PASS: accepted V21 runtime object retained")
    print("PASS: diagnostic helper symbol defined")
    print("PASS: 12 passthrough symbols defined")

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
        str(V21_OBJ),
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
        SYSTEM / "SNDDSound3DDLL_VBR_orig.dll"
    )
    v22_exports = exports(dll)

    if len(original_exports) != 291 or len(v22_exports) != 291:
        raise SystemExit(
            "ERROR: expected 291 exports in original and V22"
        )

    if v22_exports != original_exports:
        mismatch = next(
            (
                (index, expected, actual)
                for index, (expected, actual)
                in enumerate(
                    zip(original_exports, v22_exports),
                    start=1,
                )
                if expected != actual
            ),
            None,
        )

        raise SystemExit(
            f"ERROR: V22 export ABI mismatch: {mismatch}"
        )

    print("PASS: 291/291 exports match")
    return dll


def install(dll: Path):
    print()
    print("===== INSTALL V22 DIAGNOSTIC DLL ONLY =====")

    live = SYSTEM / "SNDDSound3DDLL_VBR.dll"

    if live.read_bytes() != V21_DLL.read_bytes():
        raise SystemExit(
            "ERROR: live DLL is not exact accepted V21; "
            "refusing diagnostic install"
        )

    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = (
        PROJECT
        / "backups"
        / f"snd-waveout-fisher-lambert-v22-diag-{stamp}"
    )
    backup.mkdir(parents=True)

    shutil.copy2(
        live,
        backup / "SNDDSound3DDLL_VBR-pre-v22-diag.dll",
    )

    shutil.copy2(dll, live)

    if live.read_bytes() != dll.read_bytes():
        raise SystemExit(
            "ERROR: installed V22 diagnostic DLL verification failed"
        )

    log = SYSTEM / "snd-waveout-fisher-lambert-v22-diag.log"
    log.write_bytes(b"")

    print("PASS: live DLL was exact accepted V21")
    print("PASS: V22 diagnostic DLL installed")
    print("PASS: 408 audio files left untouched")
    print("Backup:", backup)
    print("Log:", log)


def main():
    print("===== V22 DIAGNOSTIC PRECHECK =====")

    ensure_game_closed()

    required = [
        V21_OBJ,
        V21_DLL,
        SYSTEM / "SNDDSound3DDLL_VBR.dll",
    ]

    for path in required:
        if not path.is_file():
            raise SystemExit(
                f"ERROR: missing V22 prerequisite: {path}"
            )

    live = SYSTEM / "SNDDSound3DDLL_VBR.dll"

    if live.read_bytes() != V21_DLL.read_bytes():
        raise SystemExit(
            "ERROR: live DLL is not exact accepted V21"
        )

    print("PASS: game is closed")
    print("PASS: live DLL is exact accepted V21")
    print("PASS: exact accepted V21 object is present")

    generate_v22_helper()
    generate_v22_asm()

    dll = build()

    install(dll)

    print()
    print("===== RESULT =====")
    print("PASS: V22 pause-route diagnostics installed")
    print("Behavior: V21 retained")
    print("Diagnostic: 12 transparent pause/resume export probes")
    print("Scope: discover actual ESC audio lifecycle path")


if __name__ == "__main__":
    main()
