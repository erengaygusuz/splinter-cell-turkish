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

V23_BUILDER = PROJECT / "tools/build-install-snd-waveout-fisher-lambert-v23.py"
V24_HELPER = PROJECT / "gameplay-subtitle-poc/src/snd_volume_v24_diag_helper.cpp"
V24_ASM = PROJECT / "gameplay-subtitle-poc/src/snd_volume_v24_diag_routes.s"
V24_OUT = PROJECT / "build/snd-volume-v24-diag"

VOLUME_ROUTES = {
    "SND_fn_vChangeVolumeAllSoundObjectTypes": (140, "probe_volume_140"),
    "SND_fn_vChangeVolumeSoundObjectType": (146, "probe_volume_146"),
    "SND_fn_vSetSoundVolumeLine": (240, "probe_volume_240"),
}


def load_v23():
    spec = importlib.util.spec_from_file_location("sc_v23", V23_BUILDER)
    if spec is None or spec.loader is None:
        raise SystemExit("ERROR: could not load V23 builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(args):
    print("+", " ".join(map(str, args)))
    subprocess.run(args, check=True)


def patch_def(base_def: Path, out_def: Path):
    lines = base_def.read_text(encoding="utf-8", errors="replace").splitlines()

    routes = {
        "SND_fn_vKillAllSoundObjectTypes": (169, "probe_kill_all_sound_object_types"),
        "SND_fn_vKillAllSoundObjects": (173, "probe_kill_all_sound_objects"),
        "SND_fn_vPauseAllSoundObjectTypes": (180, "probe_pause_all_sound_object_types"),
        "SND_fn_vPauseAllSoundObjectTypesButOne": (181, "probe_pause_all_sound_object_types_but_one"),
        "SND_fn_vPauseSoundObjectType": (185, "probe_pause_sound_object_type"),
        "SND_fn_vResumeAllSoundObjectTypes": (207, "probe_resume_all_sound_object_types"),
        "SND_fn_vResumeAllSoundObjectTypesButOne": (208, "probe_resume_all_sound_object_types_but_one"),
        "SND_fn_vResumeSoundObjectType": (212, "probe_resume_sound_object_type"),
        "SND_fn_vStopSoundRequest": (247, "probe_stop_sound_request"),
        **VOLUME_ROUTES,
    }

    found = set()

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith(";"):
            continue

        lhs = stripped.split("=", 1)[0].strip()
        public_name = lhs.strip('"')

        if public_name not in routes:
            continue

        expected_ordinal, target = routes[public_name]
        match = re.search(r"(\s+@(\d+)\b.*)$", stripped)

        if not match:
            raise SystemExit(f"ERROR: {public_name} has no ordinal")

        if int(match.group(2)) != expected_ordinal:
            raise SystemExit(
                f"ERROR: {public_name} ordinal mismatch: "
                f"{match.group(2)} != {expected_ordinal}"
            )

        if public_name in found:
            raise SystemExit(f"ERROR: duplicate route: {public_name}")

        found.add(public_name)
        indent = line[: len(line) - len(line.lstrip())]
        lines[i] = indent + lhs + "=" + target + match.group(1)

    if found != set(routes):
        missing = sorted(set(routes) - found)
        raise SystemExit("ERROR: V24 missing routes: " + ", ".join(missing))

    out_def.write_text("\n".join(lines) + "\n", encoding="utf-8")

    export_lines = [
        line.strip()
        for line in lines
        if re.search(r"\s+@\d+\s*$", line.strip())
    ]

    if len(export_lines) != 291:
        raise SystemExit(
            f"ERROR: V24 DEF expected 291 exports, got {len(export_lines)}"
        )

    print("PASS: V24 DEF has 291 exports")
    print("PASS: accepted V23 lifecycle routes retained")
    print("PASS: focused volume probes @140, @146, @240 installed")


def main():
    print("===== V24 VOLUME DIAGNOSTIC PRECHECK =====")

    if not V23_BUILDER.is_file():
        raise SystemExit("ERROR: missing V23 builder")

    v23 = load_v23()
    v23.ensure_game_closed()

    live = SYSTEM / "SNDDSound3DDLL_VBR.dll"
    v23_dll = v23.V23_OUT / "SNDDSound3DDLL_VBR.dll"

    required = [
        v23_dll,
        v23.V23_OUT / "snd_waveout_fisher_lambert_v21_exposed.obj",
        v23.V23_OUT / "snd_waveout_fisher_lambert_v23_pause_helper.obj",
        v23.V23_OUT / "snd_waveout_fisher_lambert_v23_pause_routes.obj",
        V24_HELPER,
        V24_ASM,
        v23.BASEOUT / "SNDDSound3DDLL_VBR.def",
        v23.BASEOUT / "kernel32.lib",
        v23.BASEOUT / "kernel32-time.lib",
        v23.BASEOUT / "winmm.lib",
        SYSTEM / "SNDDSound3DDLL_VBR_orig.dll",
    ]

    for path in required:
        if not path.is_file():
            raise SystemExit(f"ERROR: missing V24 input: {path}")

    if live.read_bytes() != v23_dll.read_bytes():
        raise SystemExit(
            "ERROR: live DLL is not exact accepted V23; "
            "refusing V24 diagnostic install"
        )

    print("PASS: game is closed")
    print("PASS: live DLL is exact accepted V23")

    V24_OUT.mkdir(parents=True, exist_ok=True)

    out_def = V24_OUT / "SNDDSound3DDLL_VBR.def"
    helper_obj = V24_OUT / "snd_volume_v24_diag_helper.obj"
    asm_obj = V24_OUT / "snd_volume_v24_diag_routes.obj"
    dll = V24_OUT / "SNDDSound3DDLL_VBR.dll"

    patch_def(
        v23.BASEOUT / "SNDDSound3DDLL_VBR.def",
        out_def,
    )

    for path in [
        helper_obj,
        asm_obj,
        dll,
        V24_OUT / "SNDDSound3DDLL_VBR.lib",
        V24_OUT / "SNDDSound3DDLL_VBR.exp",
    ]:
        try:
            path.unlink()
        except FileNotFoundError:
            pass

    print()
    print("===== COMPILE SMALL V24 OBJECTS =====")

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
        str(V24_HELPER),
    ])

    run([
        "clang-cl",
        "--target=i686-pc-windows-msvc",
        "/nologo",
        "/c",
        f"/Fo{asm_obj}",
        str(V24_ASM),
    ])

    helper_nm = subprocess.check_output(["llvm-nm", str(helper_obj)], text=True)
    asm_nm = subprocess.check_output(["llvm-nm", str(asm_obj)], text=True)

    if "_v24_volume_route" not in helper_nm:
        raise SystemExit("ERROR: V24 helper symbol missing")

    for ordinal in (140, 146, 240):
        symbol = f"_probe_volume_{ordinal}"
        if symbol not in asm_nm:
            raise SystemExit(f"ERROR: V24 ASM symbol missing: {symbol}")

    forbidden = {"_memcpy", "_memset", "_memmove", "_malloc", "_free", "__fltused"}
    undefined = {
        parts[-1]
        for line in helper_nm.splitlines()
        if (parts := line.split()) and "U" in parts[:-1]
    }
    bad = sorted(undefined & forbidden)

    if bad:
        raise SystemExit(
            "ERROR: V24 helper has forbidden CRT dependency: "
            + ", ".join(bad)
        )

    print("PASS: V24 helper/ASM compile")
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
        str(v23.V23_OUT / "snd_waveout_fisher_lambert_v21_exposed.obj"),
        str(v23.V23_OUT / "snd_waveout_fisher_lambert_v23_pause_helper.obj"),
        str(v23.V23_OUT / "snd_waveout_fisher_lambert_v23_pause_routes.obj"),
        str(helper_obj),
        str(asm_obj),
        str(v23.BASEOUT / "kernel32.lib"),
        str(v23.BASEOUT / "kernel32-time.lib"),
        str(v23.BASEOUT / "winmm.lib"),
    ])

    print("PASS: link")

    original_exports = v23.exports(SYSTEM / "SNDDSound3DDLL_VBR_orig.dll")
    v24_exports = v23.exports(dll)

    if (
        len(original_exports) != 291
        or len(v24_exports) != 291
        or v24_exports != original_exports
    ):
        raise SystemExit("ERROR: V24 export ABI mismatch")

    print("PASS: 291/291 exports match")

    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = PROJECT / "backups" / f"snd-volume-v24-diag-{stamp}"
    backup.mkdir(parents=True)

    shutil.copy2(live, backup / "SNDDSound3DDLL_VBR-pre-v24-diag.dll")
    shutil.copy2(dll, live)

    if live.read_bytes() != dll.read_bytes():
        raise SystemExit("ERROR: V24 install verification failed")

    log = SYSTEM / "snd-volume-v24-diag.log"
    log.write_bytes(b"")

    print()
    print("===== RESULT =====")
    print("PASS: V24 focused volume diagnostics installed")
    print("PASS: accepted V23 pause/resume behavior retained")
    print("PASS: 408 audio files left untouched")
    print("Probes: @140, @146, @240")
    print("Backup:", backup)
    print("Log:", log)


if __name__ == "__main__":
    main()
