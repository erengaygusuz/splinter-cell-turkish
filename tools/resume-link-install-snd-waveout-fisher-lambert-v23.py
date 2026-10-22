#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

PROJECT = Path("/run/media/ereng/files/projects/splinter-cell-turkish")
BUILDER = PROJECT / "tools/build-install-snd-waveout-fisher-lambert-v23.py"


def load_builder():
    spec = importlib.util.spec_from_file_location(
        "sc_v23_builder",
        BUILDER,
    )
    if spec is None or spec.loader is None:
        raise SystemExit("ERROR: could not load V23 builder")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(args):
    print("+", " ".join(map(str, args)))
    subprocess.run(args, check=True)


def main():
    print("===== V23 RESUME PRECHECK =====")

    v23 = load_builder()
    v23.ensure_game_closed()

    live = v23.SYSTEM / "SNDDSound3DDLL_VBR.dll"

    if not v23.V22_DLL.is_file():
        raise SystemExit(
            "ERROR: accepted V22 diagnostic DLL is missing"
        )

    if live.read_bytes() != v23.V22_DLL.read_bytes():
        raise SystemExit(
            "ERROR: live DLL is not exact V22 diagnostic; "
            "refusing V23 resume"
        )

    runtime_obj = (
        v23.V23_OUT
        / "snd_waveout_fisher_lambert_v21_exposed.obj"
    )
    helper_obj = (
        v23.V23_OUT
        / "snd_waveout_fisher_lambert_v23_pause_helper.obj"
    )
    asm_obj = (
        v23.V23_OUT
        / "snd_waveout_fisher_lambert_v23_pause_routes.obj"
    )
    out_def = v23.V23_OUT / "SNDDSound3DDLL_VBR.def"
    dll = v23.V23_OUT / "SNDDSound3DDLL_VBR.dll"

    required = [
        runtime_obj,
        asm_obj,
        out_def,
        v23.V23_HELPER,
        v23.BASEOUT / "kernel32.lib",
        v23.BASEOUT / "kernel32-time.lib",
        v23.BASEOUT / "winmm.lib",
        v23.SYSTEM / "SNDDSound3DDLL_VBR_orig.dll",
    ]

    for path in required:
        if not path.is_file():
            raise SystemExit(
                f"ERROR: missing V23 resume input: {path}"
            )

    runtime_nm = subprocess.check_output(
        ["llvm-nm", str(runtime_obj)],
        text=True,
    )

    for symbol in v23.EXPOSED_SYMBOLS:
        rows = [
            parts
            for line in runtime_nm.splitlines()
            if (parts := line.split())
            and parts[-1] == symbol
        ]

        if (
            len(rows) != 1
            or rows[0][-2].islower()
        ):
            raise SystemExit(
                f"ERROR: exposed runtime symbol invalid: {symbol}"
            )

    asm_nm = subprocess.check_output(
        ["llvm-nm", str(asm_obj)],
        text=True,
    )

    for symbol in [
        "_probe_pause_sound_object_type",
        "_probe_resume_sound_object_type",
    ]:
        if symbol not in asm_nm:
            raise SystemExit(
                f"ERROR: V23 route symbol missing: {symbol}"
            )

    print("PASS: game is closed")
    print("PASS: live DLL is exact V22 diagnostic")
    print("PASS: exposed V21 runtime object is reusable")
    print("PASS: V23 route ASM object is reusable")

    print()
    print("===== RECOMPILE V23 HELPER ONLY =====")

    try:
        helper_obj.unlink()
    except FileNotFoundError:
        pass

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
        str(v23.V23_HELPER),
    ])

    helper_nm = subprocess.check_output(
        ["llvm-nm", str(helper_obj)],
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
                f"ERROR: V23 helper does not define {symbol}"
            )

    helper_undefined = {
        parts[-1]
        for line in helper_nm.splitlines()
        if (parts := line.split())
        and "U" in parts[:-1]
    }

    forbidden_crt = {
        "_memcpy",
        "_memset",
        "_memmove",
        "_malloc",
        "_free",
        "__fltused",
    }

    bad_crt = sorted(
        helper_undefined & forbidden_crt
    )

    if bad_crt:
        raise SystemExit(
            "ERROR: V23 helper still has forbidden CRT dependency: "
            + ", ".join(bad_crt)
        )

    print("PASS: V23 helper compile")
    print("PASS: no forbidden CRT dependency")

    print()
    print("===== LINK EXISTING V23 OBJECTS =====")

    for path in [
        dll,
        v23.V23_OUT / "SNDDSound3DDLL_VBR.lib",
        v23.V23_OUT / "SNDDSound3DDLL_VBR.exp",
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
        str(runtime_obj),
        str(helper_obj),
        str(asm_obj),
        str(v23.BASEOUT / "kernel32.lib"),
        str(v23.BASEOUT / "kernel32-time.lib"),
        str(v23.BASEOUT / "winmm.lib"),
    ])

    print("PASS: link")

    print()
    print("===== VERIFY EXPORT ABI =====")

    original_exports = v23.exports(
        v23.SYSTEM / "SNDDSound3DDLL_VBR_orig.dll"
    )
    v23_exports = v23.exports(dll)

    if (
        len(original_exports) != 291
        or len(v23_exports) != 291
    ):
        raise SystemExit(
            "ERROR: expected 291 exports in original and V23"
        )

    if v23_exports != original_exports:
        mismatch = next(
            (
                (index, expected, actual)
                for index, (expected, actual)
                in enumerate(
                    zip(original_exports, v23_exports),
                    start=1,
                )
                if expected != actual
            ),
            None,
        )
        raise SystemExit(
            f"ERROR: V23 export ABI mismatch: {mismatch}"
        )

    print("PASS: 291/291 exports match")

    v23.install(dll)

    print()
    print("===== RESULT =====")
    print("PASS: V23 resume-link install complete")
    print("ESC pause route: @185")
    print("ESC resume route: @212")
    print("Runtime: accepted V21 object reused")


if __name__ == "__main__":
    main()
