#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

PROJECT = Path("/run/media/ereng/files/projects/splinter-cell-turkish")
BUILDER = PROJECT / "tools/build-install-snd-waveout-fisher-lambert-v22-diag.py"


def load_builder():
    spec = importlib.util.spec_from_file_location(
        "sc_v22_diag_builder",
        BUILDER,
    )

    if spec is None or spec.loader is None:
        raise SystemExit("ERROR: could not load V22 diagnostic builder")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(args):
    print("+", " ".join(map(str, args)))
    subprocess.run(args, check=True)


def main():
    print("===== V22 DIAGNOSTIC RESUME PRECHECK =====")

    if not BUILDER.is_file():
        raise SystemExit(f"ERROR: missing builder: {BUILDER}")

    v22 = load_builder()
    v22.ensure_game_closed()

    live = v22.SYSTEM / "SNDDSound3DDLL_VBR.dll"

    if live.read_bytes() != v22.V21_DLL.read_bytes():
        raise SystemExit(
            "ERROR: live DLL is not exact accepted V21; "
            "refusing V22 diagnostic resume"
        )

    helper_obj = (
        v22.V22_OUT
        / "snd_waveout_fisher_lambert_v22_diag_helper.obj"
    )
    asm_obj = (
        v22.V22_OUT
        / "snd_waveout_fisher_lambert_v22_diag_routes.obj"
    )
    out_def = v22.V22_OUT / "SNDDSound3DDLL_VBR.def"
    dll = v22.V22_OUT / "SNDDSound3DDLL_VBR.dll"
    base_def = v22.BASEOUT / "SNDDSound3DDLL_VBR.def"

    required = [
        v22.V21_OBJ,
        v22.V22_HELPER,
        v22.V22_ASM,
        helper_obj,
        asm_obj,
        base_def,
        v22.BASEOUT / "kernel32.lib",
        v22.BASEOUT / "kernel32-time.lib",
        v22.BASEOUT / "winmm.lib",
        v22.SYSTEM / "SNDDSound3DDLL_VBR_orig.dll",
    ]

    for path in required:
        if not path.is_file():
            raise SystemExit(
                f"ERROR: missing resume input: {path}"
            )

    if helper_obj.stat().st_mtime < v22.V22_HELPER.stat().st_mtime:
        raise SystemExit(
            "ERROR: diagnostic helper object is stale; full V22 build required"
        )

    if asm_obj.stat().st_mtime < v22.V22_ASM.stat().st_mtime:
        raise SystemExit(
            "ERROR: diagnostic ASM object is stale; full V22 build required"
        )

    helper_nm = subprocess.check_output(
        ["llvm-nm", str(helper_obj)],
        text=True,
    )
    asm_nm = subprocess.check_output(
        ["llvm-nm", str(asm_obj)],
        text=True,
    )

    if "_probe_pause_route_original" not in helper_nm:
        raise SystemExit(
            "ERROR: diagnostic helper symbol missing"
        )

    for symbol in [
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
    ]:
        if symbol not in asm_nm:
            raise SystemExit(
                f"ERROR: diagnostic ASM symbol missing: {symbol}"
            )

    print("PASS: game is closed")
    print("PASS: live DLL is exact accepted V21")
    print("PASS: existing diagnostic objects are current")

    print()
    print("===== REBUILD V22 DEF =====")

    v22.patch_def(base_def, out_def)

    print()
    print("===== LINK EXISTING OBJECTS =====")

    for path in [
        dll,
        v22.V22_OUT / "SNDDSound3DDLL_VBR.lib",
        v22.V22_OUT / "SNDDSound3DDLL_VBR.exp",
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
        "/safeseh:no",
        "/entry:DllMain@12",
        f"/def:{out_def}",
        f"/out:{dll}",
        str(v22.V21_OBJ),
        str(helper_obj),
        str(asm_obj),
        str(v22.BASEOUT / "kernel32.lib"),
        str(v22.BASEOUT / "kernel32-time.lib"),
        str(v22.BASEOUT / "winmm.lib"),
    ])

    print("PASS: link")

    print()
    print("===== VERIFY EXPORT ABI =====")

    original_exports = v22.exports(
        v22.SYSTEM / "SNDDSound3DDLL_VBR_orig.dll"
    )
    diag_exports = v22.exports(dll)

    if len(original_exports) != 291:
        raise SystemExit(
            f"ERROR: original export count is "
            f"{len(original_exports)}, expected 291"
        )

    if len(diag_exports) != 291:
        raise SystemExit(
            f"ERROR: V22 export count is "
            f"{len(diag_exports)}, expected 291"
        )

    if diag_exports != original_exports:
        mismatch = next(
            (
                (index, expected, actual)
                for index, (expected, actual)
                in enumerate(
                    zip(original_exports, diag_exports),
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

    v22.install(dll)

    print()
    print("===== RESULT =====")
    print("PASS: V22 diagnostic resume-link install complete")
    print("SafeSEH: disabled for diagnostic ASM object")
    print("Runtime: accepted V21 object retained")
    print("Diagnostic: 12 transparent pause/resume route probes")


if __name__ == "__main__":
    main()
