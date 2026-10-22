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

V18_BUILDER = PROJECT / "tools/build-install-snd-waveout-fisher-lambert-v18.py"
V19_BUILDER = PROJECT / "tools/build-install-snd-waveout-fisher-lambert-v19.py"


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


def main():
    print("===== V19 RESUME PRECHECK =====")

    ensure_game_closed()

    for path in (V18_BUILDER, V19_BUILDER):
        if not path.is_file():
            raise SystemExit(f"ERROR: missing builder: {path}")

    v18 = load_module(V18_BUILDER, "sc_v18_builder_resume")
    v19 = load_module(V19_BUILDER, "sc_v19_builder_resume")

    source = v19.V19_SOURCE
    obj = v19.V19_OUT / "snd_waveout_fisher_lambert_v19.obj"
    dll = v19.V19_OUT / "SNDDSound3DDLL_VBR.dll"
    out_def = v19.V19_OUT / "SNDDSound3DDLL_VBR.def"
    base_def = v18.BASEOUT / "SNDDSound3DDLL_VBR.def"

    live = SYSTEM / "SNDDSound3DDLL_VBR.dll"
    v18_live_candidate = (
        PROJECT
        / "build/snd-waveout-fisher-lambert-v18/SNDDSound3DDLL_VBR.dll"
    )
    original = SYSTEM / "SNDDSound3DDLL_VBR_orig.dll"

    required = [
        source,
        obj,
        base_def,
        v18.BASEOUT / "kernel32.lib",
        v18.BASEOUT / "kernel32-time.lib",
        v18.BASEOUT / "winmm.lib",
        live,
        v18_live_candidate,
        original,
    ]

    for path in required:
        if not path.is_file():
            raise SystemExit(f"ERROR: missing resume input: {path}")

    if live.read_bytes() != v18_live_candidate.read_bytes():
        raise SystemExit(
            "ERROR: live DLL is not the accepted V18 build; "
            "refusing resume install"
        )

    if obj.stat().st_mtime < source.stat().st_mtime:
        raise SystemExit(
            "ERROR: V19 object is older than generated V19 source; "
            "full rebuild required"
        )

    nm = subprocess.check_output(
        ["llvm-nm", str(obj)],
        text=True,
    )

    stop_rows = []

    for line in nm.splitlines():
        parts = line.split()

        if parts and parts[-1] == "_probe_stop_sound_request":
            stop_rows.append(parts)

    if len(stop_rows) != 1:
        raise SystemExit(
            "ERROR: expected exactly one _probe_stop_sound_request "
            f"symbol in object, got {len(stop_rows)}"
        )

    if "U" in stop_rows[0][:-1]:
        raise SystemExit(
            "ERROR: _probe_stop_sound_request is undefined in V19 object"
        )

    print("PASS: game is closed")
    print("PASS: live DLL is still exact accepted V18")
    print("PASS: compiled V19 object is current")
    print("PASS: object defines _probe_stop_sound_request")

    print()
    print("===== REBUILD V19 DEF =====")

    v19.V19_OUT.mkdir(parents=True, exist_ok=True)
    v19.patch_def(base_def, out_def)

    expected_route = (
        '"SND_fn_vStopSoundRequest"=probe_stop_sound_request @247'
    )

    def_lines = out_def.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines()

    if expected_route not in [line.strip() for line in def_lines]:
        raise SystemExit(
            "ERROR: corrected undecorated V19 DEF route missing"
        )

    print("PASS: cdecl DEF target is undecorated probe_stop_sound_request")

    print()
    print("===== LINK EXISTING V19 OBJECT =====")

    for path in [
        dll,
        v19.V19_OUT / "SNDDSound3DDLL_VBR.lib",
        v19.V19_OUT / "SNDDSound3DDLL_VBR.exp",
    ]:
        try:
            path.unlink()
        except FileNotFoundError:
            pass

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

    original_exports = exports(original)
    v19_exports = exports(dll)

    if len(original_exports) != 291:
        raise SystemExit(
            f"ERROR: original export count is {len(original_exports)}, expected 291"
        )

    if len(v19_exports) != 291:
        raise SystemExit(
            f"ERROR: V19 export count is {len(v19_exports)}, expected 291"
        )

    if v19_exports != original_exports:
        mismatch = next(
            (
                (index, expected, actual)
                for index, (expected, actual)
                in enumerate(
                    zip(original_exports, v19_exports),
                    start=1,
                )
                if expected != actual
            ),
            None,
        )

        raise SystemExit(
            f"ERROR: V19 export ABI mismatch: {mismatch}"
        )

    print("PASS: 291/291 exports match")

    print()
    print("===== INSTALL V19 DLL ONLY =====")

    # V19 changes only runtime lifecycle behavior. The 408 WAV payload
    # is identical to accepted V18 and is intentionally not recopied here.
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = (
        PROJECT
        / "backups"
        / f"snd-waveout-fisher-lambert-v19-resume-{stamp}"
    )
    backup.mkdir(parents=True)

    shutil.copy2(
        live,
        backup / "SNDDSound3DDLL_VBR-pre-v19.dll",
    )

    shutil.copy2(dll, live)

    if live.read_bytes() != dll.read_bytes():
        raise SystemExit(
            "ERROR: installed V19 DLL verification failed"
        )

    log = SYSTEM / "snd-waveout-fisher-lambert-v19.log"
    log.write_bytes(b"")

    print("PASS: V19 DLL installed")
    print("PASS: 408 V18 audio files left untouched")
    print("Backup:", backup)
    print("Log:", log)

    print()
    print("===== RESULT =====")
    print("PASS: V19 resume-link install complete")
    print("Lifecycle: request-level StopSoundRequest -> waveOut stop")
    print("ABI: 291/291 exact")
    print("Rollback: accepted V18 DLL preserved in backup")


if __name__ == "__main__":
    main()
