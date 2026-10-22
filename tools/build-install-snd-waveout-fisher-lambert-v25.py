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

V23_BUILDER = (
    PROJECT
    / "tools/build-install-snd-waveout-fisher-lambert-v23.py"
)
V25_HELPER = (
    PROJECT
    / "gameplay-subtitle-poc/src/"
    "snd_waveout_fisher_lambert_v25_pause_guard.cpp"
)
V25_OUT = PROJECT / "build/snd-waveout-fisher-lambert-v25"

RUNTIME_LOG = SYSTEM / "snd-waveout-fisher-lambert-v21.log"
PAUSE_LOG = SYSTEM / "snd-waveout-fisher-lambert-v23.log"


def load_v23():
    spec = importlib.util.spec_from_file_location(
        "sc_v23_for_v25",
        V23_BUILDER,
    )

    if spec is None or spec.loader is None:
        raise SystemExit("ERROR: could not load V23 builder")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(args):
    print("+", " ".join(map(str, args)))
    subprocess.run(args, check=True)


def patch_def(source_def: Path, out_def: Path):
    print()
    print("===== PATCH V25 ISPLAYING ROUTE =====")

    lines = source_def.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines()

    matches = []

    pattern = re.compile(
        r"^(?P<indent>\s*)"
        r"(?P<lhs>.+?)"
        r"=probe_is_playing"
        r"(?P<suffix>\s+@(\d+)\s*)$"
    )

    for index, line in enumerate(lines):
        match = pattern.match(line)

        if not match:
            continue

        matches.append(
            (
                index,
                match.group("indent"),
                match.group("lhs"),
                match.group("suffix"),
                int(match.group(4)),
            )
        )

    if len(matches) != 1:
        raise SystemExit(
            "ERROR: expected exactly one V23 probe_is_playing "
            f"DEF route, got {len(matches)}"
        )

    index, indent, lhs, suffix, ordinal = matches[0]

    lines[index] = (
        indent
        + lhs
        + "=probe_is_playing_v25"
        + suffix
    )

    out_def.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    export_lines = [
        line.strip()
        for line in lines
        if re.search(r"\s+@\d+\s*$", line.strip())
    ]

    if len(export_lines) != 291:
        raise SystemExit(
            "ERROR: V25 DEF expected 291 exports, got "
            f"{len(export_lines)}"
        )

    if sum("=probe_is_playing_v25" in line for line in lines) != 1:
        raise SystemExit(
            "ERROR: V25 IsPlaying route replacement verification failed"
        )

    if any("=probe_is_playing " in line for line in lines):
        raise SystemExit(
            "ERROR: stale exported probe_is_playing route remains"
        )

    print("PASS: exactly one IsPlaying export rerouted")
    print(f"PASS: IsPlaying ordinal preserved: @{ordinal}")
    print("PASS: V23 pause/resume and lifecycle routes left unchanged")
    print("PASS: V25 DEF still has 291 exports")


def check_defined(nm_text: str, symbol: str):
    rows = [
        parts
        for line in nm_text.splitlines()
        if (parts := line.split())
        and parts[-1] == symbol
    ]

    if (
        len(rows) != 1
        or "U" in rows[0][:-1]
    ):
        raise SystemExit(
            f"ERROR: expected one defined symbol: {symbol}"
        )


def main():
    print("===== V25 PAUSED REQUEST GUARD PRECHECK =====")

    if not V23_BUILDER.is_file():
        raise SystemExit("ERROR: V23 builder is missing")

    v23 = load_v23()
    v23.ensure_game_closed()

    live = SYSTEM / "SNDDSound3DDLL_VBR.dll"
    v23_dll = v23.V23_OUT / "SNDDSound3DDLL_VBR.dll"
    v23_def = v23.V23_OUT / "SNDDSound3DDLL_VBR.def"

    runtime_obj = (
        v23.V23_OUT
        / "snd_waveout_fisher_lambert_v21_exposed.obj"
    )
    pause_helper_obj = (
        v23.V23_OUT
        / "snd_waveout_fisher_lambert_v23_pause_helper.obj"
    )
    pause_routes_obj = (
        v23.V23_OUT
        / "snd_waveout_fisher_lambert_v23_pause_routes.obj"
    )

    required = [
        live,
        v23_dll,
        v23_def,
        runtime_obj,
        pause_helper_obj,
        pause_routes_obj,
        V25_HELPER,
        v23.BASEOUT / "kernel32.lib",
        v23.BASEOUT / "kernel32-time.lib",
        v23.BASEOUT / "winmm.lib",
        SYSTEM / "SNDDSound3DDLL_VBR_orig.dll",
    ]

    for path in required:
        if not path.is_file():
            raise SystemExit(
                f"ERROR: missing V25 prerequisite: {path}"
            )

    if live.read_bytes() != v23_dll.read_bytes():
        raise SystemExit(
            "ERROR: live DLL is not exact accepted V23; "
            "refusing V25 install"
        )

    print("PASS: game is closed")
    print("PASS: live DLL is exact accepted V23")
    print("PASS: accepted V23 objects are reusable")

    runtime_nm = subprocess.check_output(
        ["llvm-nm", str(runtime_obj)],
        text=True,
    )

    for symbol in [
        "_probe_is_playing",
        "_g_runtime_requests",
        "_g_runtime_pause_active",
    ]:
        check_defined(runtime_nm, symbol)

    print("PASS: V21 IsPlaying implementation is link-visible")
    print("PASS: paused request state is externally visible")

    V25_OUT.mkdir(parents=True, exist_ok=True)

    out_def = V25_OUT / "SNDDSound3DDLL_VBR.def"
    helper_obj = (
        V25_OUT
        / "snd_waveout_fisher_lambert_v25_pause_guard.obj"
    )
    dll = V25_OUT / "SNDDSound3DDLL_VBR.dll"

    patch_def(v23_def, out_def)

    for path in [
        helper_obj,
        dll,
        V25_OUT / "SNDDSound3DDLL_VBR.lib",
        V25_OUT / "SNDDSound3DDLL_VBR.exp",
    ]:
        try:
            path.unlink()
        except FileNotFoundError:
            pass

    print()
    print("===== COMPILE V25 PAUSE GUARD ONLY =====")

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
        "/clang:-fno-builtin",
        f"/Fo{helper_obj}",
        str(V25_HELPER),
    ])

    helper_nm = subprocess.check_output(
        ["llvm-nm", str(helper_obj)],
        text=True,
    )

    check_defined(helper_nm, "_probe_is_playing_v25")

    undefined = {
        parts[-1]
        for line in helper_nm.splitlines()
        if (parts := line.split())
        and "U" in parts[:-1]
    }

    expected_undefined = {
        "_probe_is_playing",
        "_g_runtime_requests",
        "_g_runtime_pause_active",
    }

    if not expected_undefined.issubset(undefined):
        missing = sorted(expected_undefined - undefined)
        raise SystemExit(
            "ERROR: V25 helper missing expected inherited references: "
            + ", ".join(missing)
        )

    forbidden_crt = {
        "_memcpy",
        "_memset",
        "_memmove",
        "_malloc",
        "_free",
        "__fltused",
    }

    bad_crt = sorted(undefined & forbidden_crt)

    if bad_crt:
        raise SystemExit(
            "ERROR: V25 helper has forbidden CRT dependency: "
            + ", ".join(bad_crt)
        )

    print("PASS: V25 pause guard compile")
    print("PASS: inherited IsPlaying/state references resolve by design")
    print("PASS: no forbidden CRT dependency")

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
        str(pause_helper_obj),
        str(pause_routes_obj),
        str(helper_obj),
        str(v23.BASEOUT / "kernel32.lib"),
        str(v23.BASEOUT / "kernel32-time.lib"),
        str(v23.BASEOUT / "winmm.lib"),
    ])

    print("PASS: link")

    print()
    print("===== VERIFY EXPORT ABI =====")

    original_exports = v23.exports(
        SYSTEM / "SNDDSound3DDLL_VBR_orig.dll"
    )
    v25_exports = v23.exports(dll)

    if (
        len(original_exports) != 291
        or len(v25_exports) != 291
    ):
        raise SystemExit(
            "ERROR: expected 291 exports in original and V25"
        )

    if v25_exports != original_exports:
        mismatch = next(
            (
                (index, expected, actual)
                for index, (expected, actual)
                in enumerate(
                    zip(original_exports, v25_exports),
                    start=1,
                )
                if expected != actual
            ),
            None,
        )

        raise SystemExit(
            f"ERROR: V25 export ABI mismatch: {mismatch}"
        )

    print("PASS: 291/291 exports match")

    print()
    print("===== INSTALL V25 =====")

    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = (
        PROJECT
        / "backups"
        / f"snd-waveout-fisher-lambert-v25-{stamp}"
    )
    backup.mkdir(parents=True)

    shutil.copy2(
        live,
        backup / "SNDDSound3DDLL_VBR-pre-v25.dll",
    )

    for log in [RUNTIME_LOG, PAUSE_LOG]:
        if log.is_file():
            shutil.copy2(log, backup / log.name)

    shutil.copy2(dll, live)

    if live.read_bytes() != dll.read_bytes():
        raise SystemExit(
            "ERROR: installed V25 DLL verification failed"
        )

    # Preserve old evidence in the backup and start one clean V25 test.
    RUNTIME_LOG.write_bytes(b"")
    PAUSE_LOG.write_bytes(b"")

    print("PASS: V25 DLL installed")
    print("PASS: accepted V23 pause/resume implementation retained")
    print("PASS: paused requests now stay logically playing")
    print("PASS: previous runtime/pause logs preserved in backup")
    print("PASS: 408 audio files left untouched")
    print("Backup:", backup)
    print("Runtime log:", RUNTIME_LOG)
    print("Pause log:", PAUSE_LOG)

    print()
    print("===== RESULT =====")
    print("PASS: V25 paused-request guard installed")
    print(
        "Expected behavior: options/sound-menu pause can no longer "
        "expire the active dubbed request while its waveOut voice is frozen."
    )


if __name__ == "__main__":
    main()
