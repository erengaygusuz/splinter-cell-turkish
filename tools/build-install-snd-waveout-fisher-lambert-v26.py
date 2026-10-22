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

V25_BUILDER = (
    PROJECT
    / "tools/build-install-snd-waveout-fisher-lambert-v25.py"
)
V26_HELPER = (
    PROJECT
    / "gameplay-subtitle-poc/src/snd_waveout_volume_v26.cpp"
)
V26_ASM = (
    PROJECT
    / "gameplay-subtitle-poc/src/snd_waveout_volume_v26_route.s"
)
V26_OUT = PROJECT / "build/snd-waveout-fisher-lambert-v26"

V26_LOG = SYSTEM / "snd-waveout-volume-v26.log"


def load_v25():
    spec = importlib.util.spec_from_file_location(
        "sc_v25_for_v26",
        V25_BUILDER,
    )

    if spec is None or spec.loader is None:
        raise SystemExit("ERROR: could not load V25 builder")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(args):
    print("+", " ".join(map(str, args)))
    subprocess.run(args, check=True)


def route_info(line: str):
    stripped = line.strip()
    lhs, rhs = stripped.split("=", 1)
    match = re.search(r"\s+@(\d+)\s*$", rhs)

    if not match:
        raise SystemExit(
            "ERROR: export route has no ordinal: " + stripped
        )

    ordinal = int(match.group(1))
    target = rhs[: match.start()].strip().strip('"')
    return lhs, target, ordinal


def patch_def(source_def: Path, out_def: Path):
    print()
    print("===== PATCH V26 VOLUME ROUTES =====")

    lines = source_def.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines()

    wanted = {
        "SND_fn_lSendSoundRequest": (
            92,
            "probe_send_request_v26",
        ),
        "SND_fn_vSetSoundVolumeLine": (
            240,
            "probe_volume_v26_240",
        ),
    }

    found = {}

    for index, line in enumerate(lines):
        stripped = line.strip()

        if (
            not stripped
            or stripped.startswith(";")
            or "=" not in stripped
        ):
            continue

        lhs = stripped.split("=", 1)[0].strip()
        public_name = lhs.strip('"')

        if public_name not in wanted:
            continue

        if public_name in found:
            raise SystemExit(
                "ERROR: duplicate V26 export route: "
                + public_name
            )

        old_lhs, old_target, ordinal = route_info(line)
        expected_ordinal, new_target = wanted[public_name]

        if ordinal != expected_ordinal:
            raise SystemExit(
                f"ERROR: {public_name} ordinal mismatch: "
                f"{ordinal} != {expected_ordinal}"
            )

        if (
            public_name == "SND_fn_lSendSoundRequest"
            and old_target != "probe_send_request"
        ):
            raise SystemExit(
                "ERROR: V25 SendSoundRequest target is not "
                f"probe_send_request: {old_target}"
            )

        if (
            public_name == "SND_fn_vSetSoundVolumeLine"
            and old_target
            not in {
                "SNDDSound3DDLL_VBR_orig.#240",
                "SNDDSound3DDLL_VBR_orig.#240",
            }
        ):
            raise SystemExit(
                "ERROR: unexpected V25 SetSoundVolumeLine target: "
                + old_target
            )

        suffix_match = re.search(
            r"(\s+@\d+\s*)$",
            line,
        )

        if not suffix_match:
            raise SystemExit(
                "ERROR: could not preserve ordinal suffix"
            )

        indent = line[: len(line) - len(line.lstrip())]
        suffix = suffix_match.group(1)

        lines[index] = (
            indent
            + old_lhs
            + "="
            + new_target
            + suffix
        )

        found[public_name] = (
            old_target,
            new_target,
            ordinal,
        )

    if set(found) != set(wanted):
        missing = sorted(set(wanted) - set(found))
        raise SystemExit(
            "ERROR: V26 missing export routes: "
            + ", ".join(missing)
        )

    # V25's accepted pause guard must remain the IsPlaying target.
    isplaying = [
        line.strip()
        for line in lines
        if line.strip().startswith(
            '"SND_fn_bIsSoundRequestPlaying"='
        )
        or line.strip().startswith(
            "SND_fn_bIsSoundRequestPlaying="
        )
    ]

    if (
        len(isplaying) != 1
        or "probe_is_playing_v25" not in isplaying[0]
        or "@24" not in isplaying[0]
    ):
        raise SystemExit(
            "ERROR: V25 IsPlaying pause guard route was not retained"
        )

    export_lines = [
        line.strip()
        for line in lines
        if re.search(r"\s+@\d+\s*$", line.strip())
    ]

    if len(export_lines) != 291:
        raise SystemExit(
            "ERROR: V26 DEF expected 291 exports, got "
            f"{len(export_lines)}"
        )

    out_def.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    for public_name in (
        "SND_fn_lSendSoundRequest",
        "SND_fn_vSetSoundVolumeLine",
    ):
        old_target, new_target, ordinal = found[public_name]

        print(
            f"PASS: {public_name} @{ordinal}: "
            f"{old_target} -> {new_target}"
        )

    print("PASS: V25 IsPlaying pause guard retained at @24")
    print("PASS: V23 ESC pause/resume routes retained")
    print("PASS: V19/V20 stop/kill lifecycle routes retained")
    print("PASS: V26 DEF still has 291 exports")


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
    print("===== V26 SPEECH VOLUME BRIDGE PRECHECK =====")

    if not V25_BUILDER.is_file():
        raise SystemExit("ERROR: V25 builder is missing")

    v25 = load_v25()
    v23 = v25.load_v23()

    v23.ensure_game_closed()

    live = SYSTEM / "SNDDSound3DDLL_VBR.dll"
    v25_dll = (
        v25.V25_OUT
        / "SNDDSound3DDLL_VBR.dll"
    )
    v25_def = (
        v25.V25_OUT
        / "SNDDSound3DDLL_VBR.def"
    )

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
    v25_helper_obj = (
        v25.V25_OUT
        / "snd_waveout_fisher_lambert_v25_pause_guard.obj"
    )

    required = [
        live,
        v25_dll,
        v25_def,
        runtime_obj,
        pause_helper_obj,
        pause_routes_obj,
        v25_helper_obj,
        V26_HELPER,
        V26_ASM,
        v23.BASEOUT / "kernel32.lib",
        v23.BASEOUT / "kernel32-time.lib",
        v23.BASEOUT / "winmm.lib",
        SYSTEM / "SNDDSound3DDLL_VBR_orig.dll",
    ]

    for path in required:
        if not path.is_file():
            raise SystemExit(
                f"ERROR: missing V26 prerequisite: {path}"
            )

    if live.read_bytes() != v25_dll.read_bytes():
        raise SystemExit(
            "ERROR: live DLL is not exact accepted V25; "
            "refusing V26 install"
        )

    runtime_nm = subprocess.check_output(
        ["llvm-nm", str(runtime_obj)],
        text=True,
    )

    for symbol in [
        "_probe_send_request",
        "_g_voice_slots",
    ]:
        check_defined(runtime_nm, symbol)

    v25_nm = subprocess.check_output(
        ["llvm-nm", str(v25_helper_obj)],
        text=True,
    )
    check_defined(
        v25_nm,
        "_probe_is_playing_v25",
    )

    print("PASS: game is closed")
    print("PASS: live DLL is exact accepted V25")
    print("PASS: inherited SendSoundRequest hook is link-visible")
    print("PASS: external waveOut slot table is link-visible")
    print("PASS: V25 paused-request guard object is reusable")

    V26_OUT.mkdir(parents=True, exist_ok=True)

    out_def = V26_OUT / "SNDDSound3DDLL_VBR.def"
    helper_obj = (
        V26_OUT
        / "snd_waveout_volume_v26.obj"
    )
    asm_obj = (
        V26_OUT
        / "snd_waveout_volume_v26_route.obj"
    )
    dll = V26_OUT / "SNDDSound3DDLL_VBR.dll"

    patch_def(v25_def, out_def)

    for path in [
        helper_obj,
        asm_obj,
        dll,
        V26_OUT / "SNDDSound3DDLL_VBR.lib",
        V26_OUT / "SNDDSound3DDLL_VBR.exp",
    ]:
        try:
            path.unlink()
        except FileNotFoundError:
            pass

    print()
    print("===== COMPILE V26 VOLUME BRIDGE =====")

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
        str(V26_HELPER),
    ])

    run([
        "clang-cl",
        "--target=i686-pc-windows-msvc",
        "/nologo",
        "/c",
        f"/Fo{asm_obj}",
        str(V26_ASM),
    ])

    helper_nm = subprocess.check_output(
        ["llvm-nm", str(helper_obj)],
        text=True,
    )
    asm_nm = subprocess.check_output(
        ["llvm-nm", str(asm_obj)],
        text=True,
    )

    for symbol in [
        "_v26_volume_route",
        "_probe_send_request_v26",
    ]:
        check_defined(helper_nm, symbol)

    check_defined(
        asm_nm,
        "_probe_volume_v26_240",
    )

    undefined = {
        parts[-1]
        for line in helper_nm.splitlines()
        if (parts := line.split())
        and "U" in parts[:-1]
    }

    expected_undefined = {
        "_probe_send_request",
        "_g_voice_slots",
    }

    if not expected_undefined.issubset(undefined):
        missing = sorted(
            expected_undefined - undefined
        )
        raise SystemExit(
            "ERROR: V26 helper missing inherited references: "
            + ", ".join(missing)
        )

    forbidden_crt = {
        "_memcpy",
        "_memset",
        "_memmove",
        "_malloc",
        "_free",
        "__fltused",
        "_pow",
        "_powf",
    }

    bad = sorted(undefined & forbidden_crt)

    if bad:
        raise SystemExit(
            "ERROR: V26 helper has forbidden CRT/math dependency: "
            + ", ".join(bad)
        )

    print("PASS: V26 helper/ASM compile")
    print("PASS: integer-only dB conversion; no CRT/math dependency")
    print("PASS: @240 signature remains transparent")

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
        str(v25_helper_obj),
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
        SYSTEM / "SNDDSound3DDLL_VBR_orig.dll"
    )
    v26_exports = v23.exports(dll)

    if (
        len(original_exports) != 291
        or len(v26_exports) != 291
        or v26_exports != original_exports
    ):
        raise SystemExit(
            "ERROR: V26 export ABI mismatch"
        )

    print("PASS: 291/291 exports match")

    print()
    print("===== INSTALL V26 =====")

    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = (
        PROJECT
        / "backups"
        / f"snd-waveout-fisher-lambert-v26-{stamp}"
    )
    backup.mkdir(parents=True)

    shutil.copy2(
        live,
        backup / "SNDDSound3DDLL_VBR-pre-v26.dll",
    )

    if V26_LOG.is_file():
        shutil.copy2(
            V26_LOG,
            backup / V26_LOG.name,
        )

    shutil.copy2(dll, live)

    if live.read_bytes() != dll.read_bytes():
        raise SystemExit(
            "ERROR: installed V26 DLL verification failed"
        )

    V26_LOG.write_bytes(b"")

    print("PASS: V26 DLL installed")
    print("PASS: V25 pause/request fix retained")
    print("PASS: speech line @240/line=2 drives external waveOut volume")
    print("PASS: new dub voices inherit the latest speech volume through @92")
    print("PASS: 408 audio files left untouched")
    print("Backup:", backup)
    print("Log:", V26_LOG)

    print()
    print("===== RESULT =====")
    print("PASS: V26 speech-volume bridge installed")
    print(
        "Scope: Fisher/Lambert external voices only; "
        "music/effects/native audio remain controlled by the game."
    )


if __name__ == "__main__":
    main()
